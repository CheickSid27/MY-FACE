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
  EventIndexingSummary,
  EventListItem,
  EventPaymentMethodRead,
  EventPublicRead,
  EventStats,
  FaceScanResponse,
  OrderDetail,
  OrderRead,
  OrderStatus,
  PaymentInitResponse,
  PaymentMethod,
  PaymentStatusResponse,
  PhoneCountry,
  PhotoListResponse,
  PhotoUploadResult,
  PricingDiscount,
  PricingPack,
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

export interface PricingPayload {
  unit_price: number;
  currency?: string;
  packs?: PricingPack[];
  discounts?: PricingDiscount[];
  print_unit_price?: number | null;
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

// Erreurs de validation (422) : FastAPI renvoie une LISTE de details
// ({loc, msg, ...}), pas une chaine. Sans ce traitement, le message affiche
// a l'utilisateur etait "[object Object]".
function errorMessage(body: unknown, fallback: string): string {
  if (!body || typeof body !== "object" || !("detail" in body)) return fallback;
  const detail = (body as { detail: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((d) => (d && typeof d === "object" && "msg" in d ? String((d as { msg: unknown }).msg) : ""))
      .map((msg) => msg.replace(/^Value error, /, ""))
      .filter(Boolean);
    if (messages.length > 0) return messages.join(" · ");
  }
  return fallback;
}

async function rawRequest(path: string, options: RequestInit = {}, retry = true): Promise<Response> {
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
      return rawRequest(path, options, false);
    }
  }

  if (!resp.ok) {
    let message = `Erreur API (${resp.status})`;
    try {
      message = errorMessage(await resp.json(), message);
    } catch {
      // ignore parse errors
    }
    throw new ApiError(resp.status, message);
  }

  return resp;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const resp = await rawRequest(path, options);
  if (resp.status === 204) return undefined as T;
  return resp.json();
}

function withQuery(path: string, params: Record<string, string | number | undefined | null>): string {
  const query = Object.entries(params)
    .filter(([, value]) => value !== undefined && value !== null && value !== "")
    .map(([key, value]) => `${key}=${encodeURIComponent(String(value))}`)
    .join("&");
  return query ? `${path}?${query}` : path;
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

  me(): Promise<User> {
    return request<User>("/auth/me");
  },

  changePassword(currentPassword: string, newPassword: string): Promise<void> {
    return request<void>("/auth/password", {
      method: "POST",
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    });
  },

  listEvents(): Promise<EventListItem[]> {
    return request<EventListItem[]>("/events");
  },

  getEvent(eventId: string): Promise<Event> {
    return request<Event>(`/events/${eventId}`);
  },

  getEventPublic(eventId: string, kioskToken?: string | null): Promise<EventPublicRead> {
    return request<EventPublicRead>(withQuery(`/events/${eventId}/public`, { kiosk_token: kioskToken }));
  },

  createEvent(payload: {
    name: string;
    date: string;
    location: string;
    pricing: PricingPayload;
    frame_caption?: string | null;
  }): Promise<Event> {
    return request<Event>("/events", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  updateEvent(
    eventId: string,
    payload: Partial<{
      name: string;
      date: string;
      location: string;
      pricing: PricingPayload;
      frame_caption: string | null;
      cash_enabled: boolean;
    }>
  ): Promise<Event> {
    return request<Event>(`/events/${eventId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },

  deleteEvent(eventId: string): Promise<void> {
    return request<void>(`/events/${eventId}`, { method: "DELETE" });
  },

  /** QR code (PNG) du lien invite ou du lien borne, reserve a l'organisateur :
   * charge avec le jeton d'authentification puis expose en URL locale. */
  async getEventQrObjectUrl(eventId: string, kind: "guest" | "kiosk"): Promise<string> {
    const resp = await rawRequest(withQuery(`/events/${eventId}/qr.png`, { kind }));
    return URL.createObjectURL(await resp.blob());
  },

  getEventIndexing(eventId: string): Promise<EventIndexingSummary> {
    return request<EventIndexingSummary>(`/events/${eventId}/indexing`);
  },

  reindexEvent(eventId: string): Promise<{ queued: number }> {
    return request<{ queued: number }>(`/events/${eventId}/reindex`, { method: "POST" });
  },

  listPhotos(
    eventId: string,
    page = 1,
    pageSize = 60,
    kioskToken?: string | null
  ): Promise<PhotoListResponse> {
    return request<PhotoListResponse>(
      withQuery(`/events/${eventId}/photos`, { page, page_size: pageSize, kiosk_token: kioskToken })
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

  scanFace(
    eventId: string,
    selfie: Blob,
    consent: boolean,
    kioskToken?: string | null
  ): Promise<FaceScanResponse> {
    const formData = new FormData();
    formData.append("consent", String(consent));
    formData.append("selfie", selfie, "selfie.jpg");
    return request<FaceScanResponse>(withQuery("/faces/scan", { event_id: eventId, kiosk_token: kioskToken }), {
      method: "POST",
      body: formData,
    });
  },

  getClusters(eventId: string): Promise<ClusterListResponse> {
    return request<ClusterListResponse>(`/events/${eventId}/clusters`);
  },

  getClustersPublic(eventId: string, kioskToken?: string | null): Promise<ClusterListResponse> {
    return request<ClusterListResponse>(
      withQuery(`/events/${eventId}/clusters/public`, { kiosk_token: kioskToken })
    );
  },

  getWatchedFolder(eventId: string): Promise<WatchedFolderRead> {
    return request<WatchedFolderRead>(`/events/${eventId}/watched-folder`);
  },

  getPaymentMethods(eventId: string): Promise<EventPaymentMethodRead[]> {
    return request<EventPaymentMethodRead[]>(`/events/${eventId}/payment-methods`);
  },

  /** `qrImage` facultatif pour une modification : le QR deja enregistre
   * est conserve si seul le numero change. */
  upsertPaymentMethod(
    eventId: string,
    method: PaymentMethod,
    phoneNumber: string,
    qrImage: File | null
  ): Promise<EventPaymentMethodRead> {
    const formData = new FormData();
    formData.append("phone_number", phoneNumber);
    if (qrImage) formData.append("qr_image", qrImage);
    return request<EventPaymentMethodRead>(`/events/${eventId}/payment-methods/${method}`, {
      method: "PUT",
      body: formData,
    });
  },

  deletePaymentMethod(eventId: string, method: PaymentMethod): Promise<void> {
    return request<void>(`/events/${eventId}/payment-methods/${method}`, { method: "DELETE" });
  },

  getPhoneCountries(): Promise<PhoneCountry[]> {
    return request<PhoneCountry[]>("/meta/phone-countries");
  },

  addToCart(eventId: string, photoId: string, sessionId: string | null): Promise<CartRead> {
    return request<CartRead>("/cart/add", {
      method: "POST",
      body: JSON.stringify({ event_id: eventId, photo_id: photoId, session_id: sessionId }),
    });
  },

  addToCartBulk(
    eventId: string,
    photoIds: string[],
    sessionId: string | null
  ): Promise<CartRead> {
    return request<CartRead>("/cart/add-bulk", {
      method: "POST",
      body: JSON.stringify({ event_id: eventId, photo_ids: photoIds, session_id: sessionId }),
    });
  },

  getCart(sessionId: string): Promise<CartRead> {
    return request<CartRead>(`/cart/${sessionId}`);
  },

  removeCartItem(itemId: string): Promise<void> {
    return request<void>(`/cart/${itemId}`, { method: "DELETE" });
  },

  /** Cocher un tirage papier exige le jeton de la borne (verifie serveur). */
  setCartItemPrint(itemId: string, printRequested: boolean, kioskToken?: string | null): Promise<CartRead> {
    return request<CartRead>(`/cart/${itemId}`, {
      method: "PATCH",
      body: JSON.stringify({ print_requested: printRequested, kiosk_token: kioskToken ?? null }),
    });
  },

  /** `contactPhone` au format international (+225...), voir PhoneInput.
   * Le paiement en especes exige le jeton de la borne (verifie serveur). */
  initPayment(
    sessionId: string,
    contactPhone: string,
    paymentMethod: PaymentMethod,
    kioskToken?: string | null
  ): Promise<PaymentInitResponse> {
    return request<PaymentInitResponse>("/payments/init", {
      method: "POST",
      body: JSON.stringify({
        session_id: sessionId,
        contact_phone: contactPhone,
        payment_method: paymentMethod,
        kiosk_token: kioskToken ?? null,
      }),
    });
  },

  /** Enregistre l'impression des tirages : autorise a la borne (jeton) ou a
   * l'organisateur connecte (jeton d'authentification ajoute automatiquement). */
  markOrderPrinted(orderId: string, kioskToken?: string | null): Promise<{ printed_at: string }> {
    return request<{ printed_at: string }>(withQuery(`/download/${orderId}/printed`, { kiosk_token: kioskToken }), {
      method: "POST",
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
    return request<OrderRead[]>(withQuery(`/admin/events/${eventId}/orders`, { order_status: status }));
  },

  getOrder(orderId: string): Promise<OrderDetail> {
    return request<OrderDetail>(`/admin/orders/${orderId}`);
  },

  /** Valider (paiement verifie, meme apres expiration) ou rejeter. */
  confirmOrder(orderId: string, approved: boolean): Promise<void> {
    return request<void>(`/admin/orders/${orderId}/confirm`, {
      method: "POST",
      body: JSON.stringify({ approved }),
    });
  },

  cancelOrder(orderId: string): Promise<void> {
    return request<void>(`/admin/orders/${orderId}/cancel`, { method: "POST" });
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
