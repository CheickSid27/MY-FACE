export type UserRole = "admin" | "photographe";

export interface User {
  id: string;
  email: string;
  role: UserRole;
  created_at: string;
}

export interface UserCreate {
  email: string;
  password: string;
  role: UserRole;
}

export interface PricingConfig {
  unit_price: number;
  currency: string;
  packs: Record<string, unknown>[];
  discounts: Record<string, unknown>[];
}

export interface Event {
  id: string;
  name: string;
  date: string;
  location: string;
  kiosk_token: string;
  pricing: PricingConfig;
  organizer_id: string;
  created_at: string;
  updated_at: string;
}

export interface EventPublicRead {
  id: string;
  name: string;
  date: string;
  location: string;
  pricing: PricingConfig;
}

export interface EventListItem {
  id: string;
  name: string;
  date: string;
  location: string;
  photo_count: number;
}

export type IndexingStatus = "pending" | "processing" | "done" | "failed";

export interface Photo {
  id: string;
  event_id: string;
  thumbnail_url: string;
  original_filename: string;
  indexing_status: IndexingStatus;
  uploaded_at: string;
}

export interface PhotoListResponse {
  items: Photo[];
  total: number;
  page: number;
  page_size: number;
}

export interface PhotoUploadError {
  filename: string;
  error: string;
}

export interface PhotoUploadResult {
  uploaded: Photo[];
  errors: PhotoUploadError[];
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface FaceScanMatch {
  photo: Photo;
  similarity: number;
}

export interface FaceScanResponse {
  matches: FaceScanMatch[];
  faces_detected_in_selfie: number;
}

export interface FaceCluster {
  cluster_id: number;
  photo_count: number;
  representative_photo: Photo;
  photo_ids: string[];
}

export interface ClusterListResponse {
  clusters: FaceCluster[];
  unclustered_count: number;
}

export interface PricingBreakdown {
  photo_count: number;
  subtotal: number;
  discount_percent: number;
  discount_amount: number;
  total: number;
  currency: string;
}

export interface CartItemRead {
  id: string;
  photo: Photo;
}

export interface CartRead {
  session_id: string;
  event_id: string;
  items: CartItemRead[];
  pricing: PricingBreakdown;
  expires_at: string;
}

export type OrderStatus =
  | "pending"
  | "processing"
  | "awaiting_confirmation"
  | "success"
  | "failed";
export type PaymentMethod = "wave" | "orange_money" | "mtn_money" | "moov_money" | "manual";

export interface PaymentInitResponse {
  order_id: string;
  status: OrderStatus;
  payment_method: PaymentMethod;
  total_amount: number;
  currency: string;
  redirect_url: string | null;
  instructions: string | null;
  qr_image_url: string | null;
  merchant_phone: string | null;
}

export interface EventPaymentMethodRead {
  id: string;
  method: PaymentMethod;
  phone_number: string;
  qr_image_url: string;
}

export interface OrderRead {
  id: string;
  contact_phone: string;
  total_amount: number;
  currency: string;
  status: OrderStatus;
  payment_method: PaymentMethod;
  payment_reference: string | null;
  photo_count: number;
  created_at: string;
}

export interface PaymentStatusResponse {
  order_id: string;
  status: OrderStatus;
  total_amount: number;
  currency: string;
  payment_method: PaymentMethod;
  qr_image_url: string | null;
  merchant_phone: string | null;
}

export interface DownloadPhoto {
  photo_id: string;
  filename: string;
  url: string;
}

export interface DownloadResponse {
  order_id: string;
  photos: DownloadPhoto[];
  expires_in: number;
}

export interface DailySales {
  date: string;
  revenue: number;
  order_count: number;
}

export interface EventStats {
  event_id: string;
  photo_count: number;
  photos_indexed: number;
  photos_pending: number;
  orders_pending: number;
  orders_processing: number;
  orders_awaiting_confirmation: number;
  orders_success: number;
  orders_failed: number;
  total_revenue: number;
  currency: string;
  photos_sold: number;
  sales_by_day: DailySales[];
}
