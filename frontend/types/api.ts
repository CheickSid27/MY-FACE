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

export interface PricingPack {
  count: number;
  price: number;
}

export interface PricingDiscount {
  min_quantity: number;
  percent: number;
}

export interface PricingConfig {
  unit_price: number;
  currency: string;
  packs: PricingPack[];
  discounts: PricingDiscount[];
  print_unit_price: number | null;
  print_bundle_price?: number | null;
}

export interface Event {
  id: string;
  name: string;
  date: string;
  location: string;
  kiosk_token: string;
  pricing: PricingConfig;
  frame_caption: string | null;
  cash_enabled: boolean;
  organizer_id: string;
  created_at: string;
  updated_at: string;
  guest_url: string;
  kiosk_url: string;
}

export interface EventPublicRead {
  id: string;
  name: string;
  date: string;
  location: string;
  pricing: PricingConfig;
  frame_caption: string | null;
  cash_enabled: boolean;
  is_kiosk: boolean;
}

export interface EventListItem {
  id: string;
  name: string;
  date: string;
  location: string;
  photo_count: number;
  organizer_email: string | null;
}

export interface EventIndexingSummary {
  pending: number;
  processing: number;
  done: number;
  failed: number;
  faces: number;
}

export type IndexingStatus = "pending" | "processing" | "done" | "failed";

export interface Photo {
  id: string;
  event_id: string;
  thumbnail_url: string;
  preview_url: string;
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
  representative_face_url: string;
  photos: Photo[];
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
  print_count: number;
  print_total: number;
  total: number;
  currency: string;
  bundle?: boolean;
}

export interface CartItemRead {
  id: string;
  photo: Photo;
  print_requested: boolean;
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
  | "failed"
  | "cancelled";
export type PaymentMethod =
  | "wave"
  | "orange_money"
  | "mtn_money"
  | "moov_money"
  | "manual"
  | "cash"
  | "geniuspay";

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
  print_count: number;
  /** Impression des tirages papier (null = a imprimer, s'il y en a). */
  printed_at: string | null;
  created_at: string;
}

export interface OrderItemRead {
  photo: Photo;
  unit_price: number;
  print_requested: boolean;
  print_price: number | null;
}

/** Fiche commande / recu (admin). */
export interface OrderDetail extends OrderRead {
  event_id: string;
  event_name: string;
  event_date: string;
  updated_at: string;
  items: OrderItemRead[];
  photos_subtotal: number;
  prints_total: number;
  discount_amount: number;
  download_url: string;
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
  thumbnail_url: string;
  print_requested: boolean;
}

export interface DownloadResponse {
  order_id: string;
  event_id: string;
  photos: DownloadPhoto[];
  expires_in: number;
  printed_at: string | null;
}

export interface DailySales {
  date: string;
  revenue: number;
  order_count: number;
}

export interface WatchedFileRead {
  filename: string;
  status: "pending_write" | "ingested" | "error";
  detail: string | null;
}

export interface WatchedFolderRead {
  folder_path: string;
  files: WatchedFileRead[];
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
  orders_cancelled: number;
  total_revenue: number;
  currency: string;
  photos_sold: number;
  sales_by_day: DailySales[];
}

export interface PhoneCountry {
  iso: string;
  name: string;
  dial_code: string;
  pattern: string;
  example: string;
  hint: string;
  trunk_prefix: string | null;
}
