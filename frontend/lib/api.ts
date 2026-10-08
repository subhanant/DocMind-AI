import {
  ApiResponse,
  DashboardStats,
  DocumentItem,
  DocumentStatus,
  DocumentType,
  ExtractionResult,
  NotificationItem,
  PaginatedResponse,
  User,
} from "@/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_REQUEST_TIMEOUT_MS = 120_000;

class ApiError extends Error {
  code: string;
  details?: unknown;
  status: number;

  constructor(message: string, code: string, status: number, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("documind_access_token");
}

export function setStoredToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) {
    localStorage.setItem("documind_access_token", token);
  } else {
    localStorage.removeItem("documind_access_token");
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const token = getStoredToken();
  const timeoutController = new AbortController();
  const timeoutId = window.setTimeout(
    () => timeoutController.abort(),
    API_REQUEST_TIMEOUT_MS
  );

  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  // Include credentials for HttpOnly cookie support
  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
      credentials: "include",
      signal: options.signal ?? timeoutController.signal,
    });
  } catch (error) {
    if (timeoutController.signal.aborted) {
      throw new ApiError(
        "The server took too long to respond. Please try again.",
        "REQUEST_TIMEOUT",
        504
      );
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }

  const data = (await response.json()) as ApiResponse<T>;

  if (!response.ok || !data.success) {
    const errorMsg = data.error?.message || response.statusText || "Request failed";
    const errorCode = data.error?.code || `HTTP_${response.status}`;
    throw new ApiError(errorMsg, errorCode, response.status, data.error?.details);
  }

  return data.data as T;
}

export const api = {
  // Auth
  auth: {
    async register(data: { email: string; password: string; full_name: string }) {
      const res = await request<{ access_token: string; user: User; expires_in: number }>(
        "/api/auth/register",
        {
          method: "POST",
          body: JSON.stringify(data),
        }
      );
      setStoredToken(res.access_token);
      return res;
    },

    async login(data: { email: string; password: string }) {
      const res = await request<{ access_token: string; user: User; expires_in: number }>(
        "/api/auth/login",
        {
          method: "POST",
          body: JSON.stringify(data),
        }
      );
      setStoredToken(res.access_token);
      return res;
    },

    async logout() {
      try {
        await request("/api/auth/logout", { method: "POST" });
      } finally {
        setStoredToken(null);
      }
    },

    async me(): Promise<User> {
      return request<User>("/api/auth/me");
    },
  },

  // Dashboard
  dashboard: {
    async getStats(): Promise<DashboardStats> {
      return request<DashboardStats>("/api/dashboard/stats");
    },

    async getRecentDocuments(limit = 5): Promise<DocumentItem[]> {
      return request<DocumentItem[]>(`/api/dashboard/recent-documents?limit=${limit}`);
    },
  },

  // Documents
  documents: {
    async list(params: {
      page?: number;
      size?: number;
      search?: string;
      document_type?: DocumentType;
      status?: DocumentStatus;
      date_from?: string;
      date_to?: string;
    }): Promise<PaginatedResponse<DocumentItem>> {
      const query = new URLSearchParams();
      if (params.page) query.set("page", params.page.toString());
      if (params.size) query.set("size", params.size.toString());
      if (params.search) query.set("search", params.search);
      if (params.document_type) query.set("document_type", params.document_type);
      if (params.status) query.set("status", params.status);
      if (params.date_from) query.set("date_from", params.date_from);
      if (params.date_to) query.set("date_to", params.date_to);

      return request<PaginatedResponse<DocumentItem>>(`/api/documents?${query.toString()}`);
    },

    async get(id: string): Promise<DocumentItem> {
      return request<DocumentItem>(`/api/documents/${id}`);
    },

    async upload(
      files: File[],
      documentType?: DocumentType
    ): Promise<DocumentItem[]> {
      const formData = new FormData();
      files.forEach((file) => formData.append("files", file));
      if (documentType) {
        formData.append("document_type", documentType);
      }

      const res = await request<{ document: DocumentItem; message: string }>(
        "/api/documents/upload",
        {
          method: "POST",
          body: formData,
        }
      );
      return [res.document];
    },

    async delete(id: string): Promise<void> {
      await request(`/api/documents/${id}`, { method: "DELETE" });
    },

    async getExtraction(id: string): Promise<ExtractionResult | null> {
      return request<ExtractionResult | null>(`/api/documents/${id}/extraction`);
    },

    async updateExtraction(
      id: string,
      updatedData: Record<string, unknown>
    ): Promise<ExtractionResult> {
      return request<ExtractionResult>(`/api/documents/${id}/extraction`, {
        method: "PUT",
        body: JSON.stringify(updatedData),
      });
    },

    async reprocess(id: string): Promise<ExtractionResult> {
      return request<ExtractionResult>(`/api/documents/${id}/reprocess`, {
        method: "POST",
      });
    },

    getFileUrl(id: string): string {
      const token = getStoredToken();
      const base = `${API_BASE_URL}/api/documents/${id}/file`;
      return token ? `${base}?token=${encodeURIComponent(token)}` : base;
    },
  },

  // Notifications
  notifications: {
    async list(params?: {
      page?: number;
      size?: number;
      unread_only?: boolean;
    }): Promise<PaginatedResponse<NotificationItem>> {
      const query = new URLSearchParams();
      if (params?.page) query.set("page", params.page.toString());
      if (params?.size) query.set("size", params.size.toString());
      if (params?.unread_only !== undefined) {
        query.set("unread_only", params.unread_only.toString());
      }

      return request<PaginatedResponse<NotificationItem>>(
        `/api/notifications?${query.toString()}`
      );
    },

    async markAsRead(id: string): Promise<NotificationItem> {
      return request<NotificationItem>(`/api/notifications/${id}/read`, {
        method: "PATCH",
      });
    },

    async markAllAsRead(): Promise<{ marked_read: number }> {
      return request<{ marked_read: number }>("/api/notifications/read-all", {
        method: "PATCH",
      });
    },
  },

  // Health
  health: {
    async check(): Promise<{ status: string; environment: string; version: string }> {
      return request<{ status: string; environment: string; version: string }>(
        "/api/health"
      );
    },
  },
};

export { ApiError };
