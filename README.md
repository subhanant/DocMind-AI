# DocuMind AI

> AI-Powered Document Intelligence SaaS Platform for Automated Document Processing and Extraction.

---

## Overview

DocuMind AI is a production-grade SaaS web application built to process incoming logistics and business documents (such as Bills of Lading, Commercial Invoices, Packing Lists, Certificates of Origin, and Arrival Notices).

The system performs multi-stage file validation, storage persistence, OCR layout parsing (via PyMuPDF & fallback engines), document classification, structured data extraction, confidence scoring, real-time status routing, user notifications, and interactive side-by-side verification with in-browser document streaming.

---

## System Architecture

```
[Incoming Documents: PDF / Scans / Images / Office]
                         │
                         ▼
             FastAPI Document Processing Pipeline
 ┌────────────────────────────────────────────────────────┐
 │ Stage 1: FileValidator (Magic bytes, MIME, size check) │
 │ Stage 2: StorageService (Local / Cloud isolation)      │
 │ Stage 3: OCRService (PyMuPDF layout & text parsing)    │
 │ Stage 4: DocumentClassifier (BL, Invoice, Packing List)│
 │ Stage 5: Structured Extractor (Fields, tables, terms)  │
 │ Stage 6: ConfidenceEngine & Status Router (Auto/Review)│
 └────────────────────────────────────────────────────────┘
                         │
        ┌────────────────┴────────────────┐
        ▼                                 ▼
   SQLite / PostgreSQL               Event Notifications
  (Models & Migrations)             (Review Alerts & Status)
        │                                 │
        └────────────────┬────────────────┘
                         ▼
        Next.js App Router (Turbopack)
 ┌────────────────────────────────────────────────────────┐
 │ • Dashboard Analytics & KPI Metrics                   │
 │ • Interactive Document Upload & Drag-and-Drop Dropzone │
 │ • Side-by-Side Live Document Preview & Stream Viewer  │
 │ • Structured Extraction Editor & Field Validator       │
 │ • In-App Notification Center                           │
 └────────────────────────────────────────────────────────┘
```

---

## Technology Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 16 (App Router, Turbopack), TypeScript, Tailwind CSS, Lucide Icons |
| **Backend** | Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2.x (Asyncio), Alembic |
| **OCR & Parsing** | PyMuPDF (`fitz`), Pillow, PyPDF |
| **Database** | SQLite + `aiosqlite` (Zero-config local dev) / PostgreSQL 16 (Production) |
| **Authentication** | Argon2 password hashing, JWT Access Tokens, HttpOnly cookies + URL Token streaming |
| **Storage** | Local disk abstraction with path traversal protection (Cloud S3/GCS ready) |
| **Orchestration** | Native PowerShell (`start-dev.ps1`), Windows CMD (`start-dev.bat`), Docker Compose |

---

## Monorepo Folder Structure

```
documind-ai/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py              # Auth dependencies & token extraction
│   │   │   └── routes/              # FastAPI route handlers
│   │   │       ├── auth.py          # Register, login, logout, me
│   │   │       ├── dashboard.py     # KPI stats, recent documents
│   │   │       ├── documents.py     # Upload, list, detail, file stream, reprocess
│   │   │       ├── health.py        # System health and checks
│   │   │       └── notifications.py # Notification retrieval and read receipts
│   │   ├── core/                    # Config, security, logging
│   │   ├── db/                      # SQLAlchemy models & migrations
│   │   ├── schemas/                 # Pydantic v2 validation models
│   │   └── services/                # Business logic
│   │       ├── classifier_service.py # Document classification engine
│   │       ├── document_service.py   # 6-Stage processing pipeline
│   │       ├── extraction_service.py # Extraction persistence & formatting
│   │       ├── llm_extractor_service.py # Structured logistics field extraction
│   │       ├── notification_service.py # Alert generation
│   │       ├── ocr_service.py        # PyMuPDF text and layout extraction
│   │       └── storage_service.py    # File storage & security
│   ├── tests/
│   │   ├── test_api.py              # 19 core API contract tests
│   │   ├── test_extraction.py       # 3 structured extraction tests
│   │   ├── test_ocr.py              # 4 OCR and layout parsing tests
│   │   └── verify_live_api.py       # 13-step live end-to-end verification
│   ├── .env                         # Backend environment variables
│   └── requirements.txt             # Python dependencies
│
├── frontend/
│   ├── app/
│   │   ├── (auth)/                  # Login and register pages
│   │   ├── (dashboard)/             # Authenticated dashboard views
│   │   │   ├── page.tsx             # Analytics & dashboard overview
│   │   │   ├── documents/page.tsx   # Document library & filter view
│   │   │   ├── documents/[id]/page.tsx # Side-by-side preview & extraction editor
│   │   │   ├── notifications/page.tsx # Notification alerts list
│   │   │   └── upload/page.tsx      # Multi-file drag-and-drop uploader
│   │   └── layout.tsx               # Root app layout & providers
│   ├── components/                  # UI components (shadcn/ui + custom)
│   ├── lib/                         # Client API library & utilities
│   ├── types/                       # TypeScript interfaces
│   └── .env.local                   # Frontend API endpoint config
│
├── start-dev.ps1                    # One-click PowerShell dev launcher
├── start-dev.bat                    # One-click Windows CMD launcher
├── docker-compose.yml               # Container deployment configuration
└── README.md                        # Project documentation
```

---

## Quick Start (Local Development)

### 1. One-Click Launch (Recommended on Windows)

In PowerShell, simply run:
```powershell
.\start-dev.ps1
```
Or double-click `start-dev.bat`. This automatically:
- Starts the FastAPI backend server on `http://127.0.0.1:8000` with hot-reload.
- Starts the Next.js development server on `http://localhost:3000`.

### 2. Manual Startup

**Backend:**
```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Open:
- **Frontend App**: `http://localhost:3000`
- **Swagger API Docs**: `http://127.0.0.1:8000/docs`
- **ReDoc**: `http://127.0.0.1:8000/redoc`

---

## Automated Testing & Live Verification

### 1. Pytest Test Suite (26 Tests)

Run the full automated test suite:
```bash
cd backend
python -m pytest
```
Output:
```
============================= 26 passed in 6.36s ==============================
- tests/test_api.py (19 passed)
- tests/test_extraction.py (3 passed)
- tests/test_ocr.py (4 passed)
```

### 2. Live End-to-End API Audit (13 Steps)

With the backend running, execute:
```bash
python tests/verify_live_api.py
```
Validates:
1. Health check endpoint (`GET /api/health`)
2. User account registration (`POST /api/auth/register`)
3. User authentication & JWT issuance (`POST /api/auth/login`)
4. Current profile retrieval (`GET /api/auth/me`)
5. Real-time KPI statistics (`GET /api/dashboard/stats`)
6. Multi-part file upload with pipeline execution (`POST /api/documents/upload`)
7. Document listing with pagination (`GET /api/documents`)
8. Document metadata & details query (`GET /api/documents/{id}`)
9. Structured extraction retrieval (`GET /api/documents/{id}/extraction`)
10. Event-driven review notifications (`GET /api/notifications`)
11. Notification read acknowledgement (`PATCH /api/notifications/{id}/read`)
12. Document & storage purge (`DELETE /api/documents/{id}`)
13. Storage verification after deletion

---

## Available API Endpoints

### Authentication & User
- `POST /api/auth/register` — Create a new user account (Argon2 hashed)
- `POST /api/auth/login` — Authenticate and receive JWT + HttpOnly cookie
- `POST /api/auth/logout` — Clear session
- `GET /api/auth/me` — Retrieve authenticated user profile

### Documents & Extraction
- `POST /api/documents/upload` — Upload files for automated OCR & extraction
- `GET /api/documents` — Search, sort, and paginate user documents
- `GET /api/documents/{id}` — Fetch document metadata
- `DELETE /api/documents/{id}` — Delete document and stored file
- `GET /api/documents/{id}/file` — Stream or download raw file (supports `?token=`)
- `GET /api/documents/{id}/extraction` — Fetch structured fields and layout JSON
- `PUT /api/documents/{id}/extraction` — Manually review/edit extracted fields
- `POST /api/documents/{id}/reprocess` — Re-run OCR and extraction pipeline

### Dashboard & Notifications
- `GET /api/dashboard/stats` — KPI counters (Total, Completed, Pending, Failed)
- `GET /api/dashboard/recent-documents` — Quick-access recent uploads
- `GET /api/notifications` — Notification feed
- `PATCH /api/notifications/{id}/read` — Mark notification as read
- `PATCH /api/notifications/read-all` — Mark all notifications as read
- `GET /api/health` — Service readiness probe

---

## Phase 2 & Beyond Roadmap

1. **Email Inbox Ingestion (Phase 6–8)**:
   - Microsoft 365 / Outlook Graph API OAuth integration.
   - Gmail API OAuth integration.
   - Automatic webhook/polling listener for incoming logistics attachments.
2. **Cloud Object Storage (Phase 10)**:
   - Pluggable AWS S3, Google Cloud Storage, or Azure Blob storage drivers.
3. **Async Queue & Distributed Workers**:
   - Redis + Celery worker task execution for long-running document queues.
4. **LLM Vision Integration**:
   - OpenAI GPT-4o / Google Gemini 2.5 multimodal integration for complex handwriting and low-DPI bill of lading stamps.
