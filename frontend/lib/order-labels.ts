import type { OrderStatus } from "@/types/api";

export const ORDER_STATUS_LABELS: Record<OrderStatus, string> = {
  pending: "En attente de paiement",
  processing: "En cours",
  awaiting_confirmation: "A confirmer",
  success: "Payee",
  failed: "Rejetee",
  cancelled: "Annulee / expiree",
};

export function orderStatusBadgeClass(status: OrderStatus): string {
  switch (status) {
    case "success":
      return "bg-emerald-100 text-emerald-700";
    case "failed":
      return "bg-red-100 text-red-700";
    case "cancelled":
      return "bg-ink-900/10 text-ink-500";
    case "awaiting_confirmation":
      return "bg-brand-accent/20 text-brand";
    default:
      return "bg-amber-100 text-amber-700";
  }
}
