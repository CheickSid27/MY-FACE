export type UserRole = "admin" | "photographe";

export interface User {
  id: string;
  email: string;
  role: UserRole;
  created_at: string;
  // Profil photographe (service photographe)
  display_name?: string | null;
  studio_name?: string | null;
  phone?: string | null;
  city?: string | null;
  is_active?: boolean;
  // Adresse confirmee par le lien recu par e-mail (photographes)
  email_verified?: boolean;
  // Photographe bloque tant qu'il n'a pas confirme (envoi d'e-mails en place)
  must_verify_email?: boolean;
  // Photo de profil (components/pro/UserAvatar.tsx), null = initiales
  avatar_version?: string | null;
}

export interface UserAdmin extends User {
  event_count: number;
  photo_count: number;
  packs_paid_total: number;
  packs_pending: number;
}

export interface RegisterPayload {
  email: string;
  password: string;
  display_name: string;
  studio_name?: string | null;
  phone: string;
  city?: string | null;
  accept_terms: boolean;
}

export interface ProfileUpdate {
  display_name?: string;
  studio_name?: string | null;
  phone?: string | null;
  city?: string | null;
}

// --- Service photographe : packs par evenement (memes tarifs que Fokevani)
export type PackKey = "decouverte" | "evenement" | "pro" | "sur_mesure";

export interface Pack {
  key: PackKey;
  name: string;
  price: number | null;
  photo_limit: number | null;
  tagline: string;
  highlights: string[];
  features: string[];
  purchasable: boolean;
}

export type PackPurchaseStatus = "pending" | "paid" | "rejected" | "cancelled";
export type PackPaymentMethod = "wave" | "orange" | "mtn" | "moov" | "djamo";

export interface PackPurchase {
  id: string;
  event_id: string;
  pack: PackKey;
  amount: number;
  currency: string;
  status: PackPurchaseStatus;
  payment_method: string;
  payer_phone: string | null;
  transaction_ref: string | null;
  admin_note: string | null;
  created_at: string;
  decided_at: string | null;
}

export interface PackPurchaseAdmin extends PackPurchase {
  event_name: string;
  event_date: string;
  current_pack: PackKey;
  photographer_email: string;
  photographer_name: string | null;
  photographer_phone: string | null;
}

export interface PackUpgradeOption {
  key: PackKey;
  name: string;
  price: number;
  photo_limit: number | null;
  amount_due: number;
}

export interface EventPack {
  event_id: string;
  pack: Pack;
  unlimited: boolean;
  photo_limit: number | null;
  photo_count: number;
  remaining: number | null;
  amount_paid: number;
  features: string[];
  upgrades: PackUpgradeOption[];
  pending_purchase: PackPurchase | null;
  purchases: PackPurchase[];
}

export interface PackPaymentInfo {
  wave?: string | null;
  orange?: string | null;
  mtn?: string | null;
  moov?: string | null;
  djamo?: string | null;
  whatsapp?: string | null;
  instructions?: string | null;
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
  // Photos offertes par l'organisateur : pas de paiement pour les invités
  offert?: boolean;
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
  pack: PackKey;
  photo_limit_override: number | null;
  watermark_text: string | null;
  has_gallery_password: boolean;
  // Conservation des donnees : evenement exempte de la suppression
  // automatique (demo), date de suppression des photos
  retention_exempt: boolean;
  photos_purged_at: string | null;
  photos_available_until: string | null;
}

export interface EventPublicRead {
  id: string;
  name: string;
  date: string;
  location: string;
  pricing: PricingConfig;
  frame_caption: string | null;
  cash_enabled: boolean;
  /** Paiement en ligne par Paystack propose (evenements de MYFACE). */
  photographer_id?: string | null;
  photographer_avatar_version?: string | null;
  online_payment?: boolean;
  is_kiosk: boolean;
  photographer_name: string | null;
  password_required: boolean;
  gallery_access: boolean;
  // Photos en ligne jusqu'a cette date (null = pas de suppression prevue)
  photos_available_until: string | null;
  photos_purged: boolean;
}

export interface EventListItem {
  id: string;
  name: string;
  date: string;
  location: string;
  photo_count: number;
  organizer_email: string | null;
  pack: PackKey;
  photo_limit: number | null;
  pack_pending: boolean;
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
  | "geniuspay"
  | "offert"
  | "paystack";

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
  offert?: boolean;
  photos_available_until?: string | null;
  photos_purged?: boolean;
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

export interface ExpiredEvent {
  event_id: string;
  name: string;
  date: string;
  photo_count: number;
}

/** Ce que la suppression automatique supprime (ou supprimerait en simulation). */
export interface RetentionReport {
  enabled: boolean;
  photo_days: number;
  order_days: number;
  events: ExpiredEvent[];
  orders_to_anonymize: number;
  photos_deleted: number;
  orders_anonymized: number;
}

// --- MYFACE Pro : accueil, ventes et notifications (routers/workspace.py) ---
export interface WorkspaceLiveEvent {
  id: string;
  name: string;
  date: string;
  location: string;
  pack: PackKey;
  photo_count: number;
  photo_limit: number | null;
  indexed: number;
  to_index: number;
  moment: "live" | "upcoming" | "past";
}

export interface WorkspaceTodo {
  kind: string;
  title: string;
  detail: string;
  href: string;
}

export interface WorkspaceSummary {
  event: WorkspaceLiveEvent | null;
  events_count: number;
  sales_today: number;
  paid_orders_today: number;
  orders_to_confirm: number;
  currency: string;
  todo: WorkspaceTodo[];
}

export interface WorkspaceOrder extends OrderRead {
  event_id: string;
  event_name: string;
}

export interface ActivityItem {
  id: string;
  kind: string;
  title: string;
  body: string;
  href: string;
  at: string;
}
