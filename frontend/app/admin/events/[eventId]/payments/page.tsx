"use client";

import { ChangeEvent, useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import OrderDetailDialog from "@/components/admin/OrderDetailDialog";
import OrderHistory from "@/components/admin/OrderHistory";
import RequireAuth from "@/components/admin/RequireAuth";
import { PrinterIcon } from "@/components/icons";
import MethodIcon, { METHOD_LABELS } from "@/components/payments/MethodIcon";
import { api, ApiError } from "@/lib/api-client";
import { ORDER_STATUS_LABELS } from "@/lib/order-labels";
import type { EventPaymentMethodRead, OrderRead, PaymentMethod } from "@/types/api";

const METHODS: PaymentMethod[] = ["wave", "orange_money", "mtn_money", "moov_money"];
// Nouvelles commandes a confirmer visibles sans recharger la page (en plus
// de la notification push, qui peut ne pas etre activee sur cet appareil).
const ORDERS_REFRESH_MS = 15_000;

function MethodCard({
  method,
  configured,
  onSaved,
}: {
  method: PaymentMethod;
  configured: EventPaymentMethodRead | undefined;
  onSaved: () => void;
}) {
  const { eventId } = useParams<{ eventId: string }>();
  const label = METHOD_LABELS[method];
  const [phone, setPhone] = useState(configured?.phone_number ?? "");
  const [file, setFile] = useState<File | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(!configured);

  function handleFile(e: ChangeEvent<HTMLInputElement>) {
    setFile(e.target.files?.[0] ?? null);
  }

  async function handleSave() {
    if (!phone.trim()) {
      setError("Numéro requis.");
      return;
    }
    // A la creation, le QR est obligatoire ; en modification, le QR deja
    // enregistre est conserve si aucun nouveau fichier n'est choisi.
    if (!file && !configured) {
      setError("Image du QR requise.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await api.upsertPaymentMethod(eventId, method, phone.trim(), file);
      setFile(null);
      setEditing(false);
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de l'enregistrement.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!confirm(`Retirer ${label} des moyens de paiement de cet événement ?`)) return;
    await api.deletePaymentMethod(eventId, method);
    onSaved();
  }

  return (
    <div className="glass rounded-2xl p-4">
      <div className="mb-3 flex items-center justify-between">
        <span className="flex items-center gap-2 font-semibold text-ink-900">
          <MethodIcon method={method} size={26} /> {label}
        </span>
        {configured && !editing && (
          <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-semibold text-emerald-700">
            Configure
          </span>
        )}
      </div>

      {configured && !editing ? (
        <div className="flex items-center gap-3">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={configured.qr_image_url} alt={`QR ${label}`} className="h-16 w-16 rounded-lg object-cover" />
          <div className="flex-1 text-sm text-ink-500">Numéro : {configured.phone_number}</div>
          <button type="button" onClick={() => setEditing(true)} className="text-xs font-semibold text-brand hover:underline">
            Modifier
          </button>
          <button type="button" onClick={handleDelete} className="text-xs font-semibold text-red-600 hover:underline">
            Retirer
          </button>
        </div>
      ) : (
        <div className="flex flex-col gap-2.5">
          <input
            type="tel"
            placeholder={`Numéro ${label}`}
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            className="rounded-lg border border-ink-900/10 bg-white/70 px-3 py-2 text-sm outline-none focus:border-brand-accent"
          />
          <input type="file" accept="image/*" onChange={handleFile} className="text-xs text-ink-500" />
          {configured && !file && (
            <p className="text-xs text-ink-300">Sans nouveau fichier, le QR actuel est conserve.</p>
          )}
          {error && <p className="text-xs text-red-600">{error}</p>}
          <div className="flex gap-2">
            <button
              type="button"
              disabled={saving}
              onClick={handleSave}
              className="btn-primary !px-4 !py-2 text-xs disabled:opacity-50"
            >
              {saving ? "Enregistrement..." : "Enregistrer"}
            </button>
            {configured && (
              <button
                type="button"
                onClick={() => {
                  setEditing(false);
                  setError(null);
                }}
                className="btn-ghost !px-4 !py-2 text-xs"
              >
                Annuler
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function OrderRow({
  order,
  actingId,
  onOpen,
  onDecision,
}: {
  order: OrderRead;
  actingId: string | null;
  onOpen: (orderId: string) => void;
  onDecision?: (orderId: string, approved: boolean) => void;
}) {
  return (
    <div className="glass flex flex-wrap items-center justify-between gap-4 rounded-2xl p-4">
      <button type="button" onClick={() => onOpen(order.id)} className="flex items-center gap-3 text-left">
        <MethodIcon method={order.payment_method} size={30} />
        <div>
          <p className="font-semibold text-ink-900">
            {order.total_amount.toLocaleString("fr-FR")} {order.currency}{" "}
            <span className="font-normal text-ink-500">&middot; {order.photo_count} photo(s)</span>
          </p>
          <p className="text-sm text-ink-500">
            {order.contact_phone} &middot; {METHOD_LABELS[order.payment_method] ?? order.payment_method}
          </p>
          <p className="flex flex-wrap items-center gap-x-2 text-xs text-ink-300">
            <span>{new Date(order.created_at).toLocaleString("fr-FR")}</span>
            <span>&middot; {ORDER_STATUS_LABELS[order.status]}</span>
            {order.print_count > 0 && (
              <span className="flex items-center gap-1 font-semibold text-brand">
                <PrinterIcon /> {order.print_count} tirage(s)
              </span>
            )}
          </p>
        </div>
      </button>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => onOpen(order.id)}
          className="rounded-lg border border-ink-900/15 bg-white px-3 py-2 text-xs font-semibold text-ink-700 transition hover:bg-surface-alt"
        >
          Details
        </button>
        {onDecision && (
          <>
            <button
              type="button"
              disabled={actingId === order.id}
              onClick={() => onDecision(order.id, true)}
              className="rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold text-white transition hover:bg-emerald-700 disabled:opacity-50"
            >
              Confirmer
            </button>
            <button
              type="button"
              disabled={actingId === order.id}
              onClick={() => onDecision(order.id, false)}
              className="rounded-lg bg-red-600 px-3 py-2 text-xs font-semibold text-white transition hover:bg-red-700 disabled:opacity-50"
            >
              Rejeter
            </button>
          </>
        )}
      </div>
    </div>
  );
}

function OrdersToHandle({ eventId }: { eventId: string }) {
  const [orders, setOrders] = useState<OrderRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [actingId, setActingId] = useState<string | null>(null);
  const [openOrderId, setOpenOrderId] = useState<string | null>(null);

  // Une seule requete pour toutes les commandes de l'evenement, reparties
  // ensuite en "a confirmer" et "en attente de paiement". Les commandes
  // jamais payees depuis trop longtemps sont annulees cote serveur a cette
  // occasion (voir backend services/orders.py).
  const load = useCallback(async () => {
    try {
      setOrders(await api.listOrders(eventId));
    } catch {
      // rafraichissement suivant
    } finally {
      setLoading(false);
    }
  }, [eventId]);

  useEffect(() => {
    load();
    const interval = setInterval(load, ORDERS_REFRESH_MS);
    return () => clearInterval(interval);
  }, [load]);

  async function handleDecision(orderId: string, approved: boolean) {
    setActingId(orderId);
    try {
      await api.confirmOrder(orderId, approved);
      await load();
    } finally {
      setActingId(null);
    }
  }

  if (loading) return <p className="text-sm text-ink-500">Chargement...</p>;

  const toConfirm = orders.filter((o) => o.status === "awaiting_confirmation");
  const awaitingPayment = orders.filter((o) => o.status === "pending" || o.status === "processing");
  // File d'impression : commandes payees dont les tirages papier n'ont pas
  // encore ete imprimes (a la borne ou depuis ce poste).
  const toPrint = orders.filter((o) => o.status === "success" && o.print_count > 0 && !o.printed_at);

  return (
    <>
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-500">
        Commandes à confirmer ({toConfirm.length})
      </h2>
      {toConfirm.length === 0 ? (
        <div className="glass mb-8 rounded-2xl p-5 text-sm text-ink-500">
          Aucune commande en attente de confirmation.
        </div>
      ) : (
        <div className="mb-8 flex flex-col gap-3">
          {toConfirm.map((order) => (
            <OrderRow
              key={order.id}
              order={order}
              actingId={actingId}
              onOpen={setOpenOrderId}
              onDecision={handleDecision}
            />
          ))}
        </div>
      )}

      <h2 className="mb-1 text-sm font-semibold uppercase tracking-wide text-ink-500">
        En attente de paiement ({awaitingPayment.length})
      </h2>
      <p className="mb-3 text-xs text-ink-500">
        Le client n&apos;a pas encore déclare avoir payé. Ces commandes sont annulées
        automatiquement si elles ne sont pas payées à temps (1 h par défaut) ; ouvrez-en une
        pour l&apos;annuler tout de suite ou la valider si vous avez reçu le paiement.
      </p>
      {awaitingPayment.length === 0 ? (
        <div className="glass mb-8 rounded-2xl p-5 text-sm text-ink-500">Aucune commande en attente de paiement.</div>
      ) : (
        <div className="mb-8 flex flex-col gap-3">
          {awaitingPayment.map((order) => (
            <OrderRow key={order.id} order={order} actingId={actingId} onOpen={setOpenOrderId} />
          ))}
        </div>
      )}

      <h2 className="mb-1 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-ink-500">
        <PrinterIcon /> Tirages à imprimer ({toPrint.length})
      </h2>
      <p className="mb-3 text-xs text-ink-500">
        Commandes payées avec des tirages papier pas encore imprimés. Normalement imprimées à la
        borne juste après le paiement ; sinon, imprimez-les d&apos;ici depuis un poste relié à
        l&apos;imprimante.
      </p>
      {toPrint.length === 0 ? (
        <div className="glass mb-8 rounded-2xl p-5 text-sm text-ink-500">Aucun tirage en attente.</div>
      ) : (
        <div className="mb-8 flex flex-col gap-3">
          {toPrint.map((order) => (
            <div key={order.id} className="glass flex flex-wrap items-center justify-between gap-3 rounded-2xl p-4">
              <button type="button" onClick={() => setOpenOrderId(order.id)} className="text-left">
                <p className="font-semibold text-ink-900">
                  {order.print_count} tirage(s){" "}
                  <span className="font-normal text-ink-500">
                    &middot; commande {order.id.slice(0, 8).toUpperCase()} &middot; {order.contact_phone}
                  </span>
                </p>
                <p className="text-xs text-ink-300">{new Date(order.created_at).toLocaleString("fr-FR")}</p>
              </button>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setOpenOrderId(order.id)}
                  className="rounded-lg border border-ink-900/15 bg-white px-3 py-2 text-xs font-semibold text-ink-700 transition hover:bg-surface-alt"
                >
                  Reçu
                </button>
                <a
                  href={`/order/${order.id}/print`}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 rounded-lg bg-brand-accent px-3 py-2 text-xs font-semibold text-brand transition hover:bg-brand-accent-light"
                >
                  <PrinterIcon /> Imprimer
                </a>
              </div>
            </div>
          ))}
        </div>
      )}

      <OrderHistory
        orders={orders}
        csvFilename={`paiements-${eventId}.csv`}
        onChanged={load}
        title="Historique des paiements"
      />

      {openOrderId && (
        <OrderDetailDialog orderId={openOrderId} onClose={() => setOpenOrderId(null)} onChanged={load} />
      )}
    </>
  );
}

function PaymentsContent() {
  const { eventId } = useParams<{ eventId: string }>();
  const router = useRouter();
  const [methods, setMethods] = useState<EventPaymentMethodRead[]>([]);
  const [loading, setLoading] = useState(true);

  const loadMethods = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getPaymentMethods(eventId);
      setMethods(data);
    } finally {
      setLoading(false);
    }
  }, [eventId]);

  useEffect(() => {
    loadMethods();
  }, [loadMethods]);

  return (
    <main className="min-h-screen bg-gradient-to-b from-surface-alt to-surface p-6">
      <div className="mx-auto max-w-3xl">
        <div className="glass mb-6 flex items-center rounded-2xl px-4 py-3">
          <button
            type="button"
            onClick={() => router.push(`/admin/events/${eventId}`)}
            className="text-sm font-medium text-ink-500 transition hover:text-brand"
          >
            &larr; Retour à l&apos;événement
          </button>
        </div>

        <h1 className="mb-1 text-xl font-bold text-ink-900">Paiements</h1>
        <p className="mb-6 text-sm text-ink-500">
          Aucun opérateur mobile money n&apos;est branche via API pour le moment. Configurez ici le
          QR code marchand et le numéro de chaque moyen de paiement que vous acceptez : le client
          scanne, paie hors-app, puis vous confirmez manuellement ci-dessous après vérification.
        </p>

        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-500">
          Moyens de paiement
        </h2>
        {loading ? (
          <p className="text-sm text-ink-500">Chargement...</p>
        ) : (
          <div className="mb-8 grid gap-3 sm:grid-cols-2">
            {METHODS.map((method) => (
              <MethodCard
                key={method}
                method={method}
                configured={methods.find((cm) => cm.method === method)}
                onSaved={loadMethods}
              />
            ))}
          </div>
        )}

        <OrdersToHandle eventId={eventId} />
      </div>
    </main>
  );
}

export default function PaymentsPage() {
  return (
    <RequireAuth>
      <PaymentsContent />
    </RequireAuth>
  );
}
