"use client";

import { useCallback, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import OrderReceipt from "@/components/admin/OrderReceipt";
import { PrinterIcon } from "@/components/icons";
import { api, ApiError } from "@/lib/api-client";
import type { OrderDetail } from "@/types/api";

interface OrderDetailDialogProps {
  orderId: string;
  onClose: () => void;
  /** Appele apres une action (validation, rejet, annulation) pour que la
   * liste parente se rafraichisse. */
  onChanged: () => void;
}

type Action = "approve" | "reject" | "cancel";

const ACTION_CONFIRMATIONS: Record<Action, string> = {
  approve: "Valider cette commande ? Le client recevra ses photos (et un SMS).",
  reject: "Rejeter cette commande ? Le paiement annonce n'est pas arrive.",
  cancel: "Annuler cette commande jamais payée ?",
};

const secondaryButton =
  "inline-flex items-center gap-1.5 rounded-lg border border-ink-900/15 bg-white px-3 py-2 text-xs font-semibold text-ink-700 transition hover:bg-surface-alt";

/** Fiche commande de l'admin : le recu complet (voir OrderReceipt) + les
 * actions possibles selon le statut. */
export default function OrderDetailDialog({ orderId, onClose, onChanged }: OrderDetailDialogProps) {
  const [order, setOrder] = useState<OrderDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [acting, setActing] = useState<Action | null>(null);

  const load = useCallback(() => {
    api
      .getOrder(orderId)
      .then(setOrder)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Impossible de charger la commande."));
  }, [orderId]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onClose]);

  // Impression des tirages faite dans un autre onglet : au retour sur cette
  // fenetre, la fiche et la liste parente sont relues (statut "imprime").
  useEffect(() => {
    function handleFocus() {
      load();
      onChanged();
    }
    window.addEventListener("focus", handleFocus);
    return () => window.removeEventListener("focus", handleFocus);
  }, [load, onChanged]);

  async function run(action: Action) {
    if (!confirm(ACTION_CONFIRMATIONS[action])) return;
    setActing(action);
    setError(null);
    try {
      if (action === "cancel") await api.cancelOrder(orderId);
      else await api.confirmOrder(orderId, action === "approve");
      load();
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Action impossible.");
    } finally {
      setActing(null);
    }
  }

  const status = order?.status;
  const canApprove = status !== undefined && status !== "success";
  const canReject = status === "awaiting_confirmation" || status === "pending" || status === "processing";
  const canCancel = status === "pending" || status === "processing";
  // Libelle adapte : pour une commande que le client n'a pas declaree payee
  // (ou expiree), valider = l'organisateur a constate le paiement lui-meme.
  const approveLabel = status === "awaiting_confirmation" ? "Confirmer le paiement" : "Valider quand même (paiement reçu)";

  // Rendu dans <body> (portail) : ouvert depuis une carte "verre depoli"
  // (backdrop-filter), le dialogue en position fixe se retrouvait
  // positionne et coupe par rapport a cette carte au lieu de l'ecran.
  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-brand/70 p-4 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
    >
      <div
        className="glass-strong max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl p-5 shadow-elevated animate-scale-in"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            aria-label="Fermer"
            className="glass-pill flex h-8 w-8 shrink-0 items-center justify-center text-ink-500 transition hover:text-ink-900"
          >
            &times;
          </button>
        </div>

        {!order && !error && <p className="text-sm text-ink-500">Chargement...</p>}
        {error && <p className="mb-3 text-sm text-red-600">{error}</p>}

        {order && (
          <>
            <div className="rounded-xl bg-white/70 p-4">
              <OrderReceipt order={order} />
            </div>

            <div className="mt-4 flex flex-wrap gap-2">
              {canApprove && (
                <button
                  type="button"
                  disabled={acting !== null}
                  onClick={() => run("approve")}
                  className="rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold text-white transition hover:bg-emerald-700 disabled:opacity-50"
                >
                  {acting === "approve" ? "..." : approveLabel}
                </button>
              )}
              {canReject && (
                <button
                  type="button"
                  disabled={acting !== null}
                  onClick={() => run("reject")}
                  className="rounded-lg bg-red-600 px-3 py-2 text-xs font-semibold text-white transition hover:bg-red-700 disabled:opacity-50"
                >
                  {acting === "reject" ? "..." : "Rejeter"}
                </button>
              )}
              {canCancel && (
                <button
                  type="button"
                  disabled={acting !== null}
                  onClick={() => run("cancel")}
                  className={`${secondaryButton} disabled:opacity-50`}
                >
                  {acting === "cancel" ? "..." : "Annuler la commande"}
                </button>
              )}
              <a href={`/admin/orders/${order.id}/receipt`} target="_blank" rel="noreferrer" className={secondaryButton}>
                <PrinterIcon /> Imprimer le reçu
              </a>
              {order.status === "success" && order.print_count > 0 && (
                <a
                  href={`/order/${order.id}/print`}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 rounded-lg bg-brand-accent px-3 py-2 text-xs font-semibold text-brand transition hover:bg-brand-accent-light"
                >
                  <PrinterIcon /> {order.printed_at ? "Reimprimer les tirages" : "Imprimer les tirages"} ({order.print_count})
                </a>
              )}
              {order.status === "success" && (
                <a href={`/order/${order.id}/download`} target="_blank" rel="noreferrer" className={secondaryButton}>
                  Page de téléchargement du client
                </a>
              )}
            </div>
          </>
        )}
      </div>
    </div>,
    document.body
  );
}
