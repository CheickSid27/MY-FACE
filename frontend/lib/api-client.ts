import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  setAccessToken,
  setTokens,
} from "@/lib/auth";
import type {
  CartRead,
  ClusterListResponse,
  DownloadResponse,
  Event,
  EventListItem,
  EventPaymentMethodRead,
  EventPublicRead,
  EventStats,
  FaceScanResponse,
  OrderRead,
  OrderStatus,
  PaymentInitResponse,
  PaymentMethod,
  PaymentStatusResponse,
  PhotoListResponse,
  PhotoUploadResult,
  TokenResponse,
  User,
  UserCreate,
  WatchedFolderRead,
} from "@/types/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;

  const resp = await fetch(`${API_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!resp.ok) {
    clearTokens();
    return null;
  }

  const data = await resp.json();
  setAccessToken(data.access_token);
  return data.access_token as string;
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  retry = true
): Promise<T> {
  const token = getAccessToken();
  const headers = new Headers(options.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const resp = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (resp.status === 401 && retry) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      return request<T>(path, options, false);
    }
  }

  if (!resp.ok) {
    let message = `Erreur API (${resp.status})`;
    try {
      const errBody = await resp.json();
      message = errBody.detail || message;
    } catch {
      // ignore parse errors
    }
    throw new ApiError(resp.status, message);
  }

  if (resp.status === 204) return undefined as T;
  return resp.json();
}

export const api = {
  async login(email: string, password: string): Promise<TokenResponse> {
    const data = await request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setTokens(data.access_token, data.refresh_token);
    return data;
  },

  logout(): void {
    clearTokens();
  },

  listEvents(): Promise<EventListItem[]> {
    return request<EventListItem[]>("/events");
  },

  getEvent(eventId: string): Promise<Event> {
    return request<Event>(`/events/${eventId}`);
  },

  getEventPublic(eventId: string): Promise<EventPublicRead> {
    return request<EventPublicRead>(`/events/${eventId}/public`);
  },

  createEvent(payload: {
    name: string;
    date: string;
    location: string;
    pricing: { unit_price: number; currency?: string };
  }): Promise<Event> {
    return request<Event>("/events", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  deleteEvent(eventId: string): Promise<void> {
    return request<void>(`/events/${eventId}`, { method: "DELETE" });
  },

  listPhotos(eventId: string, page = 1, pageSize = 60): Promise<PhotoListResponse> {
    return request<PhotoListResponse>(
      `/events/${eventId}/photos?page=${page}&page_size=${pageSize}`
    );
  },

  uploadPhotos(eventId: string, files: File[]): Promise<PhotoUploadResult> {
    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));
    return request<PhotoUploadResult>(`/photos/upload?event_id=${eventId}`, {
      method: "POST",
      body: formData,
    });
  },

  deletePhoto(photoId: string): Promise<void> {
    return request<void>(`/photos/${photoId}`, { method: "DELETE" });
  },

  getVapidPublicKey(): Promise<{ public_key: string }> {
    return request<{ public_key: string }>(`/notifications/vapid-public-key`);
  },

  subscribeToPush(subscription: PushSubscriptionJSON): Promise<void> {
    return request<void>(`/notifications/subscribe`, {
      method: "POST",
      body: JSON.stringify(subscription),
    });
  },

  unsubscribeFromPush(endpoint: string): Promise<void> {
    return request<void>(`/notifications/unsubscribe`, {
      method: "POST",
      body: JSON.stringify({ endpoint }),
    });
  },

  scanFace(eventId: string, selfie: Blob, consent: boolean): Promise<FaceScanResponse> {
    const formData = new FormData();
    formData.append("consent", String(consent));
    formData.append("selfie", selfie, "selfie.jpg");
    return request<FaceScanResponse>(`/faces/scan?event_id=${eventId}`, {
      method: "POST",
      body: formData,
    });
  },

  getClusters(eventId: string): Promise<ClusterListResponse> {
    return request<ClusterListResponse>(`/events/${eventId}/clusters`);
  },

  getClustersPublic(eventId: string): Promise<ClusterListResponse> {
    return request<ClusterListResponse>(`/events/${eventId}/clusters/public`);
  },

  getWatchedFolder(eventId: string): Promise<WatchedFolderRead> {
    return request<WatchedFolderRead>(`/events/${eventId}/watched-folder`);
  },

  getPaymentMethods(eventId: string): Promise<EventPaymentMethodRead[]> {
    return request<EventPaymentMethodRead[]>(`/events/${eventId}/payment-methods`);
  },

  upsertPaymentMethod(
    eventId: string,
    method: PaymentMethod,
    phoneNumber: string,
    qrImage: File
  ): Promise<EventPaymentMethodRead> {
    const formData = new FormData();
    formData.append("phone_number", phoneNumber);
    formData.append("qr_image", qrImage);
    return request<EventPaymentMethodRead>(`/events/${eventId}/payment-methods/${method}`, {
      method: "PUT",
      body: formData,
    });
  },

  deletePaymentMethod(eventId: string, method: PaymentMethod): Promise<void> {
    return request<void>(`/events/${eventId}/payment-methods/${method}`, { method: "DELETE" });
  },

  addToCart(eventId: string, photoId: string, sessionId: string | null): Promise<CartRead> {
    return request<CartRead>("/cart/add", {
      method: "POST",
      body: JSON.stringify({ event_id: eventId, photo_id: photoId, session_id: sessionId }),
    });
  },

  getCart(sessionId: string): Promise<CartRead> {
    return request<CartRead>(`/cart/${sessionId}`);
  },

  removeCartItem(itemId: string): Promise<void> {
    return request<void>(`/cart/${itemId}`, { method: "DELETE" });
  },

  initPayment(
    sessionId: string,
    contactPhone: string,
    paymentMethod?: PaymentMethod
  ): Promise<PaymentInitResponse> {
    return request<PaymentInitResponse>("/payments/init", {
      method: "POST",
      body: JSON.stringify({
        session_id: sessionId,
        contact_phone: contactPhone,
        payment_method: paymentMethod ?? null,
      }),
    });
  },

  getPaymentStatus(orderId: string): Promise<PaymentStatusResponse> {
    return request<PaymentStatusResponse>(`/payments/status/${orderId}`);
  },

  markPaid(orderId: string): Promise<PaymentStatusResponse> {
    return request<PaymentStatusResponse>(`/payments/${orderId}/mark-paid`, { method: "POST" });
  },

  getDownload(orderId: string): Promise<DownloadResponse> {
    return request<DownloadResponse>(`/download/${orderId}`);
  },

  getEventStats(eventId: string): Promise<EventStats> {
    return request<EventStats>(`/admin/events/${eventId}/stats`);
  },

  listOrders(eventId: string, status?: OrderStatus): Promise<OrderRead[]> {
    const query = status ? `?order_status=${status}` : "";
    return request<OrderRead[]>(`/admin/events/${eventId}/orders${query}`);
  },

  confirmOrder(orderId: string, approved: boolean): Promise<void> {
    return request<void>(`/admin/orders/${orderId}/confirm`, {
      method: "POST",
      body: JSON.stringify({ approved }),
    });
  },

  listUsers(): Promise<User[]> {
    return request<User[]>("/admin/users");
  },

  createUser(payload: UserCreate): Promise<User> {
    return request<User>("/admin/users", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  deleteUser(userId: string): Promise<void> {
    return request<void>(`/admin/users/${userId}`, { method: "DELETE" });
  },
};
