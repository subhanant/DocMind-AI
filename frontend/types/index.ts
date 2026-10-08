export type DocumentStatus =
  | "uploaded"
  | "queued"
  | "processing"
  | "completed"
  | "failed"
  | "needs_review";

export type DocumentType =
  | "bill_of_lading"
  | "commercial_invoice"
  | "packing_list"
  | "purchase_order"
  | "certificate_of_origin"
  | "delivery_challan"
  | "contract"
  | "receipt"
  | "customs_document"
  | "shipping_document"
  | "general_document"
  | "unknown";

export type NotificationType =
  | "upload_complete"
  | "processing_complete"
  | "processing_failed"
  | "needs_review"
  | "system";

export type UserRole = "admin" | "user" | "viewer";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface DocumentItem {
  id: string;
  user_id: string;
  original_filename: string;
  file_type: string;
  mime_type: string;
  file_size: number;
  storage_path: string;
  document_type: DocumentType;
  processing_status: DocumentStatus;
  extraction_confidence: number | null;
  uploaded_at: string;
  processed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExtractedField<T = string> {
  value: T | null;
  confidence: number;
  source_text?: string;
  page?: number;
}

export interface BillOfLadingSchema {
  document_metadata?: {
    bl_number?: ExtractedField<string>;
    bl_type?: ExtractedField<string>;
    bl_status?: ExtractedField<string>;
    bl_date?: ExtractedField<string>;
    place_of_issue?: ExtractedField<string>;
    original_copies?: ExtractedField<string>;
  };
  parties?: {
    shipper?: ExtractedField<string>;
    consignee?: ExtractedField<string>;
    notify_party?: ExtractedField<string>;
    additional_notify_party?: ExtractedField<string>;
  };
  shipment?: {
    booking_number?: ExtractedField<string>;
    shipping_line?: ExtractedField<string>;
    carrier?: ExtractedField<string>;
    vessel_name?: ExtractedField<string>;
    voyage_number?: ExtractedField<string>;
    place_of_receipt?: ExtractedField<string>;
    port_of_loading?: ExtractedField<string>;
    port_of_discharge?: ExtractedField<string>;
    place_of_delivery?: ExtractedField<string>;
    final_destination?: ExtractedField<string>;
    country_of_origin?: ExtractedField<string>;
  };
  dates?: {
    issue_date?: ExtractedField<string>;
    on_board_date?: ExtractedField<string>;
    estimated_departure_date?: ExtractedField<string>;
    estimated_arrival_date?: ExtractedField<string>;
    actual_departure_date?: ExtractedField<string>;
    actual_arrival_date?: ExtractedField<string>;
  };
  cargo?: {
    description?: ExtractedField<string>;
    commodity?: ExtractedField<string>;
    hs_code?: ExtractedField<string>;
    marks_and_numbers?: ExtractedField<string>;
    number_of_packages?: ExtractedField<string>;
    package_type?: ExtractedField<string>;
    gross_weight?: ExtractedField<string>;
    net_weight?: ExtractedField<string>;
    volume?: ExtractedField<string>;
  };
  containers?: Array<{
    container_number?: ExtractedField<string>;
    container_type?: ExtractedField<string>;
    container_size?: ExtractedField<string>;
    seal_number?: ExtractedField<string>;
    packages?: ExtractedField<string>;
    gross_weight?: ExtractedField<string>;
    volume?: ExtractedField<string>;
  }>;
  freight?: {
    freight_terms?: ExtractedField<string>;
    freight_status?: ExtractedField<string>;
    freight_amount?: ExtractedField<string>;
    freight_currency?: ExtractedField<string>;
    prepaid_amount?: ExtractedField<string>;
    collect_amount?: ExtractedField<string>;
    payment_location?: ExtractedField<string>;
  };
  references?: {
    invoice_number?: ExtractedField<string>;
    purchase_order_number?: ExtractedField<string>;
    customer_reference?: ExtractedField<string>;
    booking_reference?: ExtractedField<string>;
  };
  special_instructions?: {
    handling_instructions?: ExtractedField<string>;
    temperature_control?: ExtractedField<string>;
    dangerous_goods?: ExtractedField<string>;
    special_cargo?: ExtractedField<string>;
  };
  dangerous_goods?: {
    un_number?: ExtractedField<string>;
    proper_shipping_name?: ExtractedField<string>;
    imo_class?: ExtractedField<string>;
    packing_group?: ExtractedField<string>;
    flash_point?: ExtractedField<string>;
    marine_pollutant?: ExtractedField<string>;
  };
}

export interface ExtractionResult {
  id: string;
  document_id: string;
  schema_version: string;
  extracted_json: Record<string, any> | null;
  confidence_score: number | null;
  validation_status: "pending" | "valid" | "invalid" | "partial";
  field_evidence?: Record<string, ExtractedField<any>>;
  edit_history?: Array<Record<string, any>>;
  processing_metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface NotificationItem {
  id: string;
  user_id: string;
  document_id: string | null;
  type: NotificationType;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
}

export interface DashboardStats {
  total_documents: number;
  processed_today: number;
  processing: number;
  needs_review: number;
  completed: number;
  failed: number;
  by_type: Record<string, number>;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  error?: {
    code: string;
    message: string;
    details?: unknown;
  };
}
