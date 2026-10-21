"use client";

import { useCallback, useEffect, useState } from "react";
import PackBadge from "@/components/packs/PackBadge";
import PackPurchaseDialog from "@/components/packs/PackPurchaseDialog";
import { api, ApiError } from "@/lib/api-client";
import {
  FEATURE_LABELS,
  PACK_NAMES,
  PURCHASE_STATUS_LABELS,
  formatFcfa,
  paymentMethodLabel,
} from "@/lib/packs";
import type { EventPack, PackKey, PackUpgradeOption } from "@/types/api";

interface PackCardProps {
  eventId: string;
  eventName: string;
  isAdmin: boolean;
  /** Change a chaque ajout/suppression de photos : le compteur est relu. */
  refreshKey: number;
  onLoaded?: (pack: EventPack) => void;
}

/** Pack de l'evenement (service photographe) : photos utilisees, options,
 * passage au pack superieur, et attribution directe par un admin MYFACE. */
export default function PackCard({ eventId, eventName, isAdmin, refreshKey, onLoaded }: PackCardProps) {
  const [pack, setPack] = useState<EventPack | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [buying, setBuying] = useState<PackUpgradeOption | null>(null);
  const [showHistory, setShowHistory] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await api.getEventPack(eventId);
      setPack(data);
      onLoaded?.(data);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Impossible de charger le pack.");
    }
  }, [eventId, onLoaded]);

  useEffect(() => {
    load();
  }, [load, refreshKey]);

  async function cancelPending() {
    if (!pack?.pending_purchase) return;
    if (!confirm("Annuler cette déclaration de paiement ?")) return;
    try {
      await api.cancelPackPurchase(pack.pending_purchase.id);
      await load();
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Annulation impossible.");
    }
  }

  if (error) return <p className="mb-6 text-sm text-red-600">{error}</p>;
  if (!pack) return <div className="skeleton mb-6 h-28 rounded-2xl" />;

  const limit = pack.photo_limit;
  const percent = limit ? Math.min(100, Math.round((pack.photo_count / limit) * 100)) : 0;
  const full = limit !== null && pack.remaining === 0;
  const lastDecided = pack.purchases.find((p) => p.status !== "pending");
  const rejected = lastDecided?.status === "rejected" ? lastDecided : null;

  return (
    <div className="glass mb-6 rounded-2xl p-5">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-ink-900">Pack de l&apos;événement</h2>
          <PackBadge pack={pack.pack.key} />
        </div>
        {pack.amount_paid > 0 && (
          <span className="text-xs text-ink-500">Payé : {formatFcfa(pack.amount_paid)}</span>
        )}
      </div>

      {pack.unlimited ? (
        <p className="text-sm text-ink-700">
          Événement MYFACE : aucune limite de photos, toutes les options sont incluses.
        </p>
      ) : (
        <>
          <div className="mb-1 flex justify-between text-xs text-ink-500">
            <span>
              {pack.photo_count.toLocaleString("fr-FR")} / {limit?.toLocaleString("fr-FR") ?? "∞"} photos
            </span>
            {limit !== null && (
              <span className={full ? "font-semibold text-red-600" : ""}>
                {full ? "Limite atteinte" : `${pack.remaining?.toLocaleString("fr-FR")} restantes`}
              </span>
            )}
          </div>
          {limit !== null && (
            <div className="mb-3 h-2 w-full overflow-hidden rounded-full bg-ink-900/10">
              <div
                className={`h-full rounded-full transition-[width] duration-300 ${full ? "bg-red-500" : "bg-brand-accent"}`}
                style={{ width: `${percent}%` }}
              />
            </div>
          )}

          {pack.features.length > 0 && (
            <p className="mb-3 text-xs text-ink-500">
              Inclus : {pack.features.map((f) => FEATURE_LABELS[f] ?? f).join(" · ")}
            </p>
          )}

          {pack.pending_purchase && (
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-xl bg-amber-50 p-3 text-xs text-amber-900">
              <p>
                Paiement du pack <strong>{PACK_NAMES[pack.pending_purchase.pack]}</strong> (
                {formatFcfa(pack.pending_purchase.amount)}, {paymentMethodLabel(pack.pending_purchase.payment_method)},
                réf. {pack.pending_purchase.transaction_ref}) en cours de vérification par MYFACE.
              </p>
              <button type="button" onClick={cancelPending} className="font-semibold text-amber-900 underline">
                Annuler
              </button>
            </div>
          )}

          {rejected && !pack.pending_purchase && (
            <div className="mb-3 rounded-xl bg-red-50 p-3 text-xs text-red-800">
              Le paiement du pack {PACK_NAMES[rejected.pack]} (réf. {rejected.transaction_ref}) n&apos;a pas été
              trouvé{rejected.admin_note ? ` : ${rejected.admin_note}` : ""}. Vérifiez la référence puis réessayez.
            </div>
          )}

          {pack.upgrades.length > 0 && !pack.pending_purchase && (
            <div className="grid gap-3 sm:grid-cols-2">
              {pack.upgrades.map((option) => (
                <div key={option.key} className="flex flex-col rounded-xl border border-ink-900/10 bg-white/60 p-3">
                  <p className="text-sm font-semibold text-ink-900">Pack {option.name}</p>
                  <p className="text-xs text-ink-500">
                    {option.photo_limit?.toLocaleString("fr-FR")} photos
                    {option.key === "pro" ? " · assistance le jour J" : " · mot de passe · filigrane"}
                  </p>
                  <p className="mt-2 text-lg font-bold text-ink-900">
                    {formatFcfa(option.amount_due)}
                    {option.amount_due < option.price && (
                      <span className="ml-1 text-xs font-normal text-ink-500 line-through">{formatFcfa(option.price)}</span>
                    )}
                  </p>
                  <button
                    type="button"
                    onClick={() => setBuying(option)}
                    className={`${option.key === "pro" ? "btn-primary" : "btn-accent"} mt-2 !py-2 text-sm`}
                  >
                    Passer au pack {option.name}
                  </button>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {pack.purchases.length > 0 && (
        <div className="mt-3">
          <button
            type="button"
            onClick={() => setShowHistory((v) => !v)}
            className="text-xs font-semibold text-brand hover:underline"
          >
            {showHistory ? "Masquer l'historique" : `Historique des paiements (${pack.purchases.length})`}
          </button>
          {showHistory && (
            <ul className="mt-2 flex flex-col gap-1.5">
              {pack.purchases.map((p) => (
                <li key={p.id} className="flex flex-wrap items-center justify-between gap-2 text-xs text-ink-700">
                  <span>
                    {new Date(p.created_at).toLocaleDateString("fr-FR")} · Pack {PACK_NAMES[p.pack]} ·{" "}
                    {formatFcfa(p.amount)} · {paymentMethodLabel(p.payment_method)}
                    {p.transaction_ref ? ` · réf. ${p.transaction_ref}` : ""}
                  </span>
                  <span className={`rounded-full px-2 py-0.5 font-medium ${PURCHASE_STATUS_LABELS[p.status].className}`}>
                    {PURCHASE_STATUS_LABELS[p.status].label}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {isAdmin && !pack.unlimited && <AdminPackControl eventId={eventId} current={pack} onSaved={load} />}

      {buying && (
        <PackPurchaseDialog
          eventId={eventId}
          eventName={eventName}
          option={buying}
          onClose={() => setBuying(null)}
          onDone={() => {
            setBuying(null);
            load();
          }}
        />
      )}
    </div>
  );
}

function AdminPackControl({
  eventId,
  current,
  onSaved,
}: {
  eventId: string;
  current: EventPack;
  onSaved: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [packKey, setPackKey] = useState<PackKey>(current.pack.key);
  const [limit, setLimit] = useState(current.pack.key === "sur_mesure" && current.photo_limit ? String(current.photo_limit) : "");
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      await api.adminSetEventPack(eventId, {
        pack: packKey,
        photo_limit_override: limit.trim() ? Number(limit) : null,
        note: note.trim() || null,
      });
      setOpen(false);
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Attribution impossible.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mt-4 border-t border-ink-900/5 pt-3">
      <button type="button" onClick={() => setOpen((v) => !v)} className="text-xs font-semibold text-brand hover:underline">
        {open ? "Fermer" : "Admin : attribuer un pack sans paiement (offert, sur mesure)"}
      </button>
      {open && (
        <div className="mt-3 grid gap-2 sm:grid-cols-3">
          <select
            value={packKey}
            onChange={(e) => setPackKey(e.target.value as PackKey)}
            className="rounded-xl border border-ink-900/10 bg-white px-3 py-2 text-sm"
          >
            {(Object.keys(PACK_NAMES) as PackKey[]).map((key) => (
              <option key={key} value={key}>
                {PACK_NAMES[key]}
              </option>
            ))}
          </select>
          <input
            type="number"
            min={1}
            value={limit}
            onChange={(e) => setLimit(e.target.value)}
            placeholder="Limite de photos (facultatif)"
            className="rounded-xl border border-ink-900/10 bg-white px-3 py-2 text-sm"
          />
          <input
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Note (ex : pack offert)"
            className="rounded-xl border border-ink-900/10 bg-white px-3 py-2 text-sm"
          />
          {error && <p className="text-sm text-red-600 sm:col-span-3">{error}</p>}
          <button type="button" onClick={save} disabled={saving} className="btn-primary !py-2 text-sm sm:col-span-3">
            {saving ? "Enregistrement..." : "Attribuer ce pack"}
          </button>
        </div>
      )}
    </div>
  );
}
