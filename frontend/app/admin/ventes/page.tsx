"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import OrderDetailDialog from "@/components/admin/OrderDetailDialog";
import MethodIcon, { METHOD_LABELS } from "@/components/payments/MethodIcon";
import PageHeader from "@/components/pro/PageHeader";
import { useWorkspace } from "@/components/pro/WorkspaceProvider";
import { CheckIcon } from "@/components/pro/icons";
import { api, ApiError } from "@/lib/api-client";
import { formatPhone } from "@/lib/phone";
import type { WorkspaceOrder } from "@/types/api";

// Ventes de tous les evenements : paiements a confirmer (Wave / Orange Money
// directs) et commandes payees des 7 derniers jours.
const REFRESH_MS = 15_000;

function money(amount: number, currency = "F"): string {
  return `${Math.round(amount).toLocaleString("fr-FR")} ${currency === "XOF" ? "F" : currency}`;
}

function ago(iso: string): string {
  const minutes = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (minutes < 1) return "à l'instant";
  if (minutes < 60) return `il y a ${minutes} min`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `il y a ${hours} h`;
  return new Date(iso).toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
}

export default function ProSalesPage() {
  const { refresh } = useWorkspace();
  const [toConfirm, setToConfirm] = useState<WorkspaceOrder[] | null>(null);
  const [paid, setPaid] = useState<WorkspaceOrder[] | null>(null);
  const [acting, setActing] = useState<string | null>(null);
  const [openId, setOpenId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [waiting, done] = await Promise.all([api.listWorkspaceOrders("to_confirm"), api.listWorkspaceOrders("paid", 7)]);
      setToConfirm(waiting);
      setPaid(done);
      setError(null);
    } catch {
      setError("Connexion instable : nouvelle tentative dans quelques secondes.");
    }
  }, []);

  useEffect(() => {
    load();
    const interval = setInterval(load, REFRESH_MS);
    return () => clearInterval(interval);
  }, [load]);

  async function decide(order: WorkspaceOrder, approved: boolean) {
    if (!approved && !confirm("Refuser ce paiement ? L'invité ne recevra pas ses photos.")) return;
    setActing(order.id);
    try {
      await api.confirmOrder(order.id, approved);
      await Promise.all([load(), refresh()]);
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Action impossible, réessayez.");
    } finally {
      setActing(null);
    }
  }

  const weekTotal = (paid ?? []).reduce((sum, o) => sum + o.total_amount, 0);

  return (
    <>
      <PageHeader title="Ventes" subtitle="Tous vos événements" />

      <section className="mb-6 grid grid-cols-2 gap-3 rounded-3xl bg-brand p-5 text-[#F4EFE6] lg:max-w-2xl">
        <div>
          <p className="text-[13px] text-[#A9BABD]">7 derniers jours</p>
          <p className="font-pro text-2xl font-semibold">{paid ? money(weekTotal) : "…"}</p>
        </div>
        <div>
          <p className="text-[13px] text-[#A9BABD]">Commandes payées</p>
          <p className="font-pro text-2xl font-semibold">{paid ? paid.length : "…"}</p>
        </div>
        <p className="col-span-2 text-[13px] text-[#A9BABD]">
          Les invités vous paient directement sur votre Wave ou votre Orange Money : MYFACE ne prend aucune commission.
        </p>
      </section>

      {error && <p className="mb-4 text-sm text-amber-700">{error}</p>}

      <div className="grid gap-6 lg:grid-cols-2 lg:items-start">
        <section>
          <div className="mb-3 flex items-baseline justify-between gap-3">
            <h2 className="font-pro text-[15px] font-semibold">À confirmer ({toConfirm?.length ?? "…"})</h2>
            <span className="text-right text-[12px] text-ink-500">Vérifiez la réception sur votre téléphone</span>
          </div>
          {!toConfirm && <div className="skeleton h-32 rounded-3xl" />}
          {toConfirm && toConfirm.length === 0 && (
            <div className="rounded-3xl border border-dashed border-[#D9CFBF] bg-white p-6 text-center text-sm text-ink-500">
              Tout est confirmé. Les invités reçoivent leurs photos tout de suite.
            </div>
          )}
          <div className="flex flex-col gap-3">
            {toConfirm?.map((order) => (
              <article key={order.id} className="flex flex-col gap-3 rounded-3xl border border-[#E6DED0] bg-white p-4">
                <button type="button" onClick={() => setOpenId(order.id)} className="flex items-center gap-3 text-left">
                  <MethodIcon method={order.payment_method} size={40} />
                  <span className="min-w-0 flex-1">
                    <b className="block text-[15px]">
                      {money(order.total_amount, order.currency)} · {METHOD_LABELS[order.payment_method] ?? order.payment_method}
                    </b>
                    <span className="block truncate text-[13px] text-ink-500">
                      {formatPhone(order.contact_phone)} · {order.photo_count} photo{order.photo_count > 1 ? "s" : ""}
                      {order.print_count > 0 ? ` + ${order.print_count} tirage${order.print_count > 1 ? "s" : ""}` : ""}
                    </span>
                    <span className="block truncate text-[12px] text-ink-500">{order.event_name}</span>
                  </span>
                  <span className="shrink-0 text-[12px] text-ink-500">{ago(order.created_at)}</span>
                </button>
                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={acting === order.id}
                    onClick={() => decide(order, false)}
                    className="min-h-[44px] flex-1 rounded-[13px] border border-[#D9CFBF] bg-white text-sm font-bold disabled:opacity-50"
                  >
                    Refuser
                  </button>
                  <button
                    type="button"
                    disabled={acting === order.id}
                    onClick={() => decide(order, true)}
                    className="min-h-[44px] flex-1 rounded-[13px] bg-brand-accent text-sm font-bold text-brand disabled:opacity-50"
                  >
                    {acting === order.id ? "..." : "Confirmer"}
                  </button>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section>
          <h2 className="mb-3 font-pro text-[15px] font-semibold">Payées ces 7 derniers jours</h2>
          {!paid && <div className="skeleton h-32 rounded-3xl" />}
          {paid && paid.length === 0 && (
            <div className="rounded-3xl border border-dashed border-[#D9CFBF] bg-white p-6 text-center text-sm text-ink-500">
              Aucune vente sur les 7 derniers jours.
            </div>
          )}
          {paid && paid.length > 0 && (
            <div className="divide-y divide-[#EFE8DC] overflow-hidden rounded-3xl border border-[#E6DED0] bg-white">
              {paid.map((order) => (
                <button
                  key={order.id}
                  type="button"
                  onClick={() => setOpenId(order.id)}
                  className="flex w-full items-center gap-3 px-4 py-3 text-left transition hover:bg-[#FBF8F3]"
                >
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#E3EAEB]">
                    <CheckIcon size={15} />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm">
                      {formatPhone(order.contact_phone)} · {order.photo_count} photo{order.photo_count > 1 ? "s" : ""}
                    </span>
                    <span className="block truncate text-[12px] text-ink-500">
                      {order.event_name} · {ago(order.created_at)}
                    </span>
                  </span>
                  <b className="shrink-0 text-sm">{money(order.total_amount, order.currency)}</b>
                </button>
              ))}
            </div>
          )}
          <Link href="/admin/events" className="mt-3 block text-center text-[13px] font-semibold text-[#B34A08]">
            Historique complet : ouvrez un événement, onglet Ventes
          </Link>
        </section>
      </div>

      {openId && (
        <OrderDetailDialog
          orderId={openId}
          onClose={() => setOpenId(null)}
          onChanged={() => {
            load();
            refresh();
          }}
        />
      )}
    </>
  );
}
