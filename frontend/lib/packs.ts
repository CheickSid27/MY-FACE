import type { PackKey, PackPaymentMethod, PackPurchaseStatus } from "@/types/api";

// Service photographe : memes tarifs que Fokevani (voir backend
// services/packs.py, qui fait foi). Ces libelles ne servent qu'a l'affichage.

export const PACK_NAMES: Record<PackKey, string> = {
  decouverte: "Découverte",
  evenement: "Événement",
  pro: "Pro",
  sur_mesure: "Sur mesure",
};

export const PACK_BADGE_CLASSES: Record<PackKey, string> = {
  decouverte: "bg-ink-900/10 text-ink-700",
  evenement: "bg-brand-accent/15 text-brand-accent",
  pro: "bg-brand text-white",
  sur_mesure: "bg-emerald-100 text-emerald-800",
};

export const PACK_PAYMENT_METHODS: { key: PackPaymentMethod; label: string }[] = [
  { key: "wave", label: "Wave" },
  { key: "orange", label: "Orange Money" },
  { key: "mtn", label: "MTN MoMo" },
  { key: "moov", label: "Moov Money" },
  { key: "djamo", label: "Djamo" },
];

export const PURCHASE_STATUS_LABELS: Record<PackPurchaseStatus, { label: string; className: string }> = {
  pending: { label: "En vérification", className: "bg-amber-100 text-amber-800" },
  paid: { label: "Payé", className: "bg-emerald-100 text-emerald-700" },
  rejected: { label: "Refusé", className: "bg-red-100 text-red-700" },
  cancelled: { label: "Annulé", className: "bg-ink-900/10 text-ink-500" },
};

export const FEATURE_LABELS: Record<string, string> = {
  gallery_password: "Mot de passe de galerie",
  custom_watermark: "Filigrane à votre nom",
  priority_support: "Assistance prioritaire le jour J",
};

export function formatFcfa(amount: number | null | undefined): string {
  if (amount === null || amount === undefined) return "Sur devis";
  if (amount === 0) return "Gratuit";
  return `${amount.toLocaleString("fr-FR")} F`;
}

export function paymentMethodLabel(key: string): string {
  if (key === "admin") return "Attribué par MYFACE";
  if (key === "paystack") return "Paiement en ligne";
  return PACK_PAYMENT_METHODS.find((m) => m.key === key)?.label ?? key;
}

/** Lien WhatsApp a partir d'un numero (+225..., 07...) : chiffres seulement. */
export function whatsappLink(phone: string | null | undefined, message?: string): string | null {
  if (!phone) return null;
  let digits = phone.replace(/\D/g, "");
  if (digits.length === 10 && digits.startsWith("0")) digits = `225${digits}`;
  const text = message ? `?text=${encodeURIComponent(message)}` : "";
  return `https://wa.me/${digits}${text}`;
}

/** Numero WhatsApp de MYFACE affiche quand l'admin n'en a pas encore saisi. */
export const MYFACE_WHATSAPP_FALLBACK = "+2250758509403";
