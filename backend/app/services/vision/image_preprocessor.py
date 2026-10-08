"""
Document Image Preprocessing Service.

Provides controlled, non-destructive image enhancement:
- CLAHE (Contrast-Limited Adaptive Histogram Equalization)
- Bilateral filtering / Edge-preserving denoising
- Unsharp masking / Sharpening
- Deskew angle detection and correction
- Region-level micro-contrast adjustments
"""
from typing import Tuple

import cv2
import numpy as np
from PIL import Image

from app.core.logging import get_logger

logger = get_logger(__name__)


class ImagePreprocessor:
    """Non-destructive image enhancement for document OCR and micro-text recovery."""

    @classmethod
    def enhance_for_ocr(
        cls,
        image: np.ndarray,
        apply_clahe: bool = True,
        apply_denoise: bool = False,
        apply_sharpen: bool = True,
    ) -> np.ndarray:
        """
        Enhances document image for optimal text detection without degrading glyphs.
        Input image: RGB NumPy array (HxWx3).
        Output: Enhanced RGB NumPy array (HxWx3).
        """
        if image is None or image.size == 0:
            return image

        img = image.copy()

        # Convert to LAB color space for luminance-only operations
        lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)

        if apply_clahe:
            # Subtle CLAHE on luminance only (clipLimit 2.0 avoids noise amplification)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            l_channel = clahe.apply(l_channel)

        if apply_denoise:
            # Bilateral filter preserves sharp edges while smoothing background paper texture
            l_channel = cv2.bilateralFilter(l_channel, d=5, sigmaColor=50, sigmaSpace=50)

        # Merge back channels
        enhanced_lab = cv2.merge([l_channel, a_channel, b_channel])
        enhanced_rgb = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2RGB)

        if apply_sharpen:
            # Unsharp mask with gentle Gaussian blur subtraction
            gaussian = cv2.GaussianBlur(enhanced_rgb, (0, 0), sigmaX=2.0)
            enhanced_rgb = cv2.addWeighted(enhanced_rgb, 1.3, gaussian, -0.3, 0)

        return enhanced_rgb

    @classmethod
    def detect_and_deskew(cls, image: np.ndarray, max_angle: float = 15.0) -> Tuple[np.ndarray, float]:
        """
        Detects document skew angle via Hough Lines and rotates back to 0 degrees if needed.
        Returns (deskewed_image, detected_angle_degrees).
        """
        if image is None or image.size == 0:
            return image, 0.0

        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        # Otsu thresholding with inversion
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Find coordinates of all foreground pixels
        coords = np.column_stack(np.where(thresh > 0))
        if coords.shape[0] < 50:
            return image, 0.0

        # Compute minimum area rectangle
        rect = cv2.minAreaRect(coords)
        angle = rect[-1]

        # OpenCV minAreaRect returns angle in range [-90, 0)
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        # Only deskew if angle is significant (> 0.5 degrees) and within plausible range
        if abs(angle) < 0.5 or abs(angle) > max_angle:
            return image, 0.0

        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        rot_mat = cv2.getRotationMatrix2D(center, angle, 1.0)
        deskewed = cv2.warpAffine(
            image, rot_mat, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )
        logger.info("Deskew applied to document page", angle=round(angle, 2))
        return deskewed, angle

    @classmethod
    def preprocess_micro_crop(cls, crop: np.ndarray, scale_factor: float = 2.0) -> np.ndarray:
        """
        Targeted preprocessing for small/micro-text regions.
        1. High-quality bicubic upscaling.
        2. Local contrast enhancement.
        3. Subtle edge sharpening.
        """
        if crop is None or crop.size == 0:
            return crop

        h, w = crop.shape[:2]
        new_w, new_h = int(w * scale_factor), int(h * scale_factor)

        # Upscale using Lanczos interpolation
        upscaled = cv2.resize(crop, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

        # Convert to LAB for luminance enhancement
        lab = cv2.cvtColor(upscaled, cv2.COLOR_RGB2LAB)
        l_chan, a_chan, b_chan = cv2.split(lab)

        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(4, 4))
        l_chan = clahe.apply(l_chan)

        # Bilateral filter
        l_chan = cv2.bilateralFilter(l_chan, d=3, sigmaColor=30, sigmaSpace=30)

        enhanced = cv2.cvtColor(cv2.merge([l_chan, a_chan, b_chan]), cv2.COLOR_LAB2RGB)

        # Sharpen
        kernel = np.array([[-0.5, -0.5, -0.5],
                           [-0.5,  5.0, -0.5],
                           [-0.5, -0.5, -0.5]], dtype=np.float32)
        sharpened = cv2.filter2D(enhanced, -1, kernel)
        return np.clip(sharpened, 0, 255).astype(np.uint8)
