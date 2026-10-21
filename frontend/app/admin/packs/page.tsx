"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import RequireAuth from "@/components/admin/RequireAuth";
import PackBadge from "@/components/packs/PackBadge";
import { api, ApiError } from "@/lib/api-client";
import { PURCHASE_STATUS_LABELS, formatFcfa, paymentMethodLabel, whatsappLink } from "@/lib/packs";
import { useAuthStore } from "@/store/auth-store";
import type { PackPurchaseAdmin, PackPurchaseStatus } from "@/types/api";

const FILTERS: { key: PackPurchaseStatus | "all"; label: string }[] = [
  { key: "pending", label: "À vérifier" },
  { key: "paid", label: "Payés" },
  { key: "rejected", label: "Refusés" },
  { key: "all", label: "Tous" },
];

/** Packs des photographes a valider : verifier sur le compte Mobile Money de
 * MYFACE que le montant est bien arrive (reference, numero), puis valider
 * (le pack s'active tout de suite) ou refuser. */
function AdminPacksContent() {
  const user = useAuthStore((s) => s.user);
  const [filter, setFilter] = useState<PackPurchaseStatus | "all">("pending");
  const [purchases, setPurchases] = useState<PackPurchaseAdmin[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [acting, setActing] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setPurchases(await api.listPackPurchases(filter === "all" ? undefined : filter));
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Impossible de charger les packs.");
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    load();
  }, [load]);

  async function approve(p: PackPurchaseAdmin) {
    if (!confirm(`Confirmer la réception de ${formatFcfa(p.amount)} (réf. ${p.transaction_ref}) et activer le pack ?`)) return;
    setActing(p.id);
    try {
      await api.approvePackPurchase(p.id);
      await load();
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Validation impossible.");
    } finally {
      setActing(null);
    }
  }

  async function reject(p: PackPurchaseAdmin) {
    const note = prompt("Motif du refus (visible par le photographe) :", "Paiement introuvable sur notre compte");
    if (note === null) return;
    setActing(p.id);
    try {
      await api.rejectPackPurchase(p.id, note);
      await load();
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Refus impossible.");
    } finally {
      setActing(null);
    }
  }

  if (user && user.role !== "admin") {
    return <p className="p-6 text-ink-500">Page réservée à l&apos;équipe MYFACE.</p>;
  }

  const total = purchases.filter((p) => p.status === "paid").reduce((sum, p) => sum + p.amount, 0);

  return (
    <main className="min-h-screen bg-gradient-to-b from-surface-alt to-surface p-6">
      <div className="mx-auto max-w-3xl">
        <Link href="/admin/events" className="mb-4 inline-block text-sm font-medium text-ink-500 transition hover:text-brand">
          &larr; Retour aux événements
        </Link>
        <div className="glass mb-4 rounded-2xl px-5 py-4">
          <h1 className="text-xl font-bold text-ink-900">Packs des photographes</h1>
          <p className="text-xs text-ink-500">
            Vérifiez sur le compte Mobile Money de MYFACE que le paiement est arrivé (montant, référence, numéro),
            puis validez : le pack s&apos;active immédiatement sur l&apos;événement.
          </p>
        </div>

        <div className="mb-4 flex flex-wrap gap-2">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              type="button"
              onClick={() => setFilter(f.key)}
              className={`rounded-full px-3 py-1.5 text-sm font-medium transition ${
                filter === f.key ? "bg-brand text-white" : "bg-white/70 text-ink-700 hover:bg-white"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {filter === "paid" && purchases.length > 0 && (
          <p className="mb-3 text-sm text-ink-700">
            Encaissé (sur cette liste) : <strong>{formatFcfa(total)}</strong>
          </p>
        )}
        {error && <p className="mb-3 text-red-600">{error}</p>}
        {loading && <p className="text-ink-500">Chargement...</p>}
        {!loading && purchases.length === 0 && (
          <p className="text-center text-ink-500">
            {filter === "pending" ? "Aucun paiement à vérifier." : "Aucun achat pour ce filtre."}
          </p>
        )}

        <ul className="flex flex-col gap-3">
          {purchases.map((p) => {
            const wa = whatsappLink(p.photographer_phone, `Bonjour, à propos de votre pack ${p.pack} pour « ${p.event_name} »`);
            return (
              <li key={p.id} className="glass rounded-2xl p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <PackBadge pack={p.pack} />
                      <span className="text-lg font-bold text-ink-900">{formatFcfa(p.amount)}</span>
                      <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${PURCHASE_STATUS_LABELS[p.status].className}`}>
                        {PURCHASE_STATUS_LABELS[p.status].label}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-ink-900">
                      <Link href={`/admin/events/${p.event_id}`} className="font-semibold hover:underline">
                        {p.event_name}
                      </Link>{" "}
                      <span className="text-ink-500">· {new Date(p.event_date).toLocaleDateString("fr-FR")}</span>
                    </p>
                    <p className="text-xs text-ink-500">
                      {p.photographer_name ? `${p.photographer_name} · ` : ""}
                      {p.photographer_email}
                      {p.photographer_phone ? ` · ${p.photographer_phone}` : ""}
                    </p>
                    <p className="mt-1 text-xs text-ink-700">
                      {paymentMethodLabel(p.payment_method)}
                      {p.payer_phone ? ` depuis ${p.payer_phone}` : ""}
                      {p.transaction_ref ? ` · réf. ${p.transaction_ref}` : ""} · déclaré le{" "}
                      {new Date(p.created_at).toLocaleString("fr-FR")}
                    </p>
                    {p.admin_note && <p className="mt-1 text-xs text-ink-500">Note : {p.admin_note}</p>}
                  </div>
                  <div className="flex shrink-0 flex-col gap-2">
                    {p.status === "pending" && (
                      <>
                        <button
                          type="button"
                          onClick={() => approve(p)}
                          disabled={acting === p.id}
                          className="btn-accent !px-4 !py-2 text-sm disabled:opacity-50"
                        >
                          Paiement reçu
                        </button>
                        <button
                          type="button"
                          onClick={() => reject(p)}
                          disabled={acting === p.id}
                          className="btn-ghost !px-4 !py-2 text-sm"
                        >
                          Refuser
                        </button>
                      </>
                    )}
                    {wa && (
                      <a href={wa} target="_blank" rel="noreferrer" className="text-center text-xs font-semibold text-emerald-700 hover:underline">
                        WhatsApp
                      </a>
                    )}
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      </div>
    </main>
  );
}

export default function AdminPacksPage() {
  return (
    <RequireAuth>
      <AdminPacksContent />
    </RequireAuth>
  );
}
