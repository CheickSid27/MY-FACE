"use client";

import { useMemo, useState } from "react";
import OrderDetailDialog from "@/components/admin/OrderDetailDialog";
import { PrinterIcon, SearchIcon } from "@/components/icons";
import { METHOD_LABELS } from "@/components/payments/MethodIcon";
import { ORDER_STATUS_LABELS, orderStatusBadgeClass } from "@/lib/order-labels";
import type { OrderRead } from "@/types/api";

function ordersToCsv(orders: OrderRead[]): string {
  const header = [
    "Numero de commande",
    "Date",
    "Heure",
    "Telephone",
    "Nombre de photos",
    "Tirages papier",
    "Tirages imprimes le",
    "Montant",
    "Devise",
    "Moyen de paiement",
    "Reference",
    "Statut",
  ];
  const escape = (value: string) => `"${value.replace(/"/g, '""')}"`;
  const rows = orders.map((order) => {
    const created = new Date(order.created_at);
    return [
      order.id,
      created.toLocaleDateString("fr-FR"),
      created.toLocaleTimeString("fr-FR"),
      order.contact_phone,
      String(order.photo_count),
      String(order.print_count),
      order.printed_at ? new Date(order.printed_at).toLocaleString("fr-FR") : "",
      String(order.total_amount),
      order.currency,
      METHOD_LABELS[order.payment_method] ?? order.payment_method,
      order.payment_reference ?? "",
      ORDER_STATUS_LABELS[order.status] ?? order.status,
    ]
      .map(escape)
      .join(",");
  });
  return [header.map(escape).join(","), ...rows].join("\r\n");
}

function downloadCsv(filename: string, csv: string) {
  // BOM UTF-8 : Excel (tres utilise localement) affiche sinon les accents
  // francais (Telephone, Reussie...) comme des caracteres corrompus.
  const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

/** Recherche tolerante : "07 01 02 03 04" retrouve "+2250701020304",
 * "0f43" retrouve la commande 0f43c034..., "CASH-ebb" sa reference. */
function matches(order: OrderRead, query: string): boolean {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  const digits = q.replace(/\D/g, "");
  if (digits.length >= 4 && order.contact_phone.replace(/\D/g, "").includes(digits)) return true;
  return (
    order.id.toLowerCase().startsWith(q) ||
    (order.payment_reference ?? "").toLowerCase().includes(q) ||
    order.contact_phone.toLowerCase().includes(q)
  );
}

interface OrderHistoryProps {
  orders: OrderRead[];
  csvFilename: string;
  /** Rechargement de la liste apres une action dans la fiche commande. */
  onChanged: () => void;
  title?: string;
}

/**
 * Historique des paiements/commandes d'un evenement : recherche par
 * telephone, numero de commande ou reference, export CSV, et fiche detaillee
 * (recu) de chaque commande en un clic.
 */
export default function OrderHistory({ orders, csvFilename, onChanged, title = "Historique des commandes" }: OrderHistoryProps) {
  const [query, setQuery] = useState("");
  const [openOrderId, setOpenOrderId] = useState<string | null>(null);
  const filtered = useMemo(() => orders.filter((order) => matches(order, query)), [orders, query]);

  return (
    <div className="glass rounded-2xl p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-ink-900">
          {title} <span className="text-sm font-normal text-ink-500">({orders.length})</span>
        </h2>
        <button
          type="button"
          disabled={orders.length === 0}
          onClick={() => downloadCsv(csvFilename, ordersToCsv(filtered))}
          className="btn-ghost !px-4 !py-2 text-xs disabled:opacity-40"
        >
          Telecharger le CSV
        </button>
      </div>

      {orders.length > 0 && (
        <label className="mb-4 flex items-center gap-2 rounded-xl border border-ink-900/10 bg-white/70 px-3 py-2 focus-within:border-brand-accent focus-within:ring-2 focus-within:ring-brand-accent/20">
          <SearchIcon className="shrink-0 text-ink-500" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Rechercher : telephone du client, numero de commande, reference..."
            className="min-w-0 flex-1 bg-transparent text-sm text-ink-900 outline-none"
          />
          {query && (
            <button type="button" onClick={() => setQuery("")} className="text-xs font-semibold text-ink-500 hover:text-ink-900">
              Effacer
            </button>
          )}
        </label>
      )}

      {orders.length === 0 ? (
        <p className="text-ink-500">Aucune commande pour le moment.</p>
      ) : filtered.length === 0 ? (
        <p className="text-ink-500">Aucune commande ne correspond a &laquo; {query} &raquo;.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead>
              <tr className="border-b border-ink-900/10 text-xs uppercase tracking-wide text-ink-500">
                <th className="py-2 pr-4">N&deg; commande</th>
                <th className="py-2 pr-4">Date</th>
                <th className="py-2 pr-4">Telephone</th>
                <th className="py-2 pr-4">Photos</th>
                <th className="py-2 pr-4">Montant</th>
                <th className="py-2 pr-4">Moyen</th>
                <th className="py-2 pr-4">Statut</th>
                <th className="py-2" />
              </tr>
            </thead>
            <tbody>
              {filtered.map((order) => {
                const created = new Date(order.created_at);
                return (
                  <tr
                    key={order.id}
                    onClick={() => setOpenOrderId(order.id)}
                    className="cursor-pointer border-b border-ink-900/5 text-ink-700 transition hover:bg-white/60"
                    title="Voir la fiche detaillee (recu)"
                  >
                    <td className="py-2 pr-4 font-mono text-xs text-ink-500">{order.id.slice(0, 8).toUpperCase()}</td>
                    <td className="whitespace-nowrap py-2 pr-4">
                      {created.toLocaleDateString("fr-FR")}{" "}
                      <span className="text-xs text-ink-500">{created.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })}</span>
                    </td>
                    <td className="py-2 pr-4">{order.contact_phone}</td>
                    <td className="py-2 pr-4">
                      {order.photo_count}
                      {order.print_count > 0 && (
                        <span
                          className={`ml-1.5 inline-flex items-center gap-0.5 text-xs ${
                            order.printed_at ? "text-ink-500" : "font-semibold text-amber-700"
                          }`}
                          title={order.printed_at ? "Tirages imprimes" : "Tirages a imprimer"}
                        >
                          <PrinterIcon /> {order.print_count}
                          {order.printed_at ? " ✓" : ""}
                        </span>
                      )}
                    </td>
                    <td className="whitespace-nowrap py-2 pr-4 font-medium text-ink-900">
                      {order.total_amount.toLocaleString("fr-FR")} {order.currency}
                    </td>
                    <td className="py-2 pr-4">{METHOD_LABELS[order.payment_method] ?? order.payment_method}</td>
                    <td className="py-2 pr-4">
                      <span className={`whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-semibold ${orderStatusBadgeClass(order.status)}`}>
                        {ORDER_STATUS_LABELS[order.status] ?? order.status}
                      </span>
                    </td>
                    <td className="py-2 text-right">
                      <span className="whitespace-nowrap rounded-lg border border-ink-900/15 bg-white px-2.5 py-1 text-xs font-semibold text-ink-700">
                        Recu &rarr;
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {openOrderId && (
        <OrderDetailDialog orderId={openOrderId} onClose={() => setOpenOrderId(null)} onChanged={onChanged} />
      )}
    </div>
  );
}
