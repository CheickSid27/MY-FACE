"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import RequireAuth from "@/components/admin/RequireAuth";
import { api } from "@/lib/api-client";
import type { EventStats, OrderRead } from "@/types/api";

const STATUS_LABELS: Record<string, string> = {
  pending: "En attente",
  processing: "En cours",
  awaiting_confirmation: "A confirmer",
  success: "Reussie",
  failed: "Echouee",
};

function ordersToCsv(orders: OrderRead[]): string {
  const header = [
    "Numero de commande",
    "Date",
    "Heure",
    "Telephone",
    "Nombre de photos",
    "Montant",
    "Devise",
    "Moyen de paiement",
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
      String(order.total_amount),
      order.currency,
      order.payment_method,
      STATUS_LABELS[order.status] ?? order.status,
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

function StatTile({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="glass rounded-2xl p-4">
      <p className="text-sm text-ink-500">{label}</p>
      <p className="mt-1 text-2xl font-bold text-brand">{value}</p>
    </div>
  );
}

function StatsContent() {
  const { eventId } = useParams<{ eventId: string }>();
  const router = useRouter();
  const [stats, setStats] = useState<EventStats | null>(null);
  const [orders, setOrders] = useState<OrderRead[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getEventStats(eventId)
      .then(setStats)
      .catch(() => setError("Impossible de charger les statistiques."));
    api
      .listOrders(eventId)
      .then(setOrders)
      .catch(() => {
        // l'historique des commandes est secondaire : ne bloque pas le reste de la page
      });
  }, [eventId]);

  if (error) return <p className="p-6 text-red-600">{error}</p>;
  if (!stats) return <p className="p-6 text-ink-500">Chargement...</p>;

  const chartData = stats.sales_by_day.map((d) => ({
    date: new Date(d.date).toLocaleDateString("fr-FR", { day: "numeric", month: "short" }),
    revenu: d.revenue,
  }));

  return (
    <main className="min-h-screen bg-gradient-to-b from-surface-alt to-surface p-6">
      <div className="mx-auto max-w-4xl">
        <button
          type="button"
          onClick={() => router.push(`/admin/events/${eventId}`)}
          className="mb-4 text-sm font-medium text-ink-500 transition hover:text-brand"
        >
          &larr; Retour a l&apos;evenement
        </button>

        <h1 className="mb-6 text-xl font-bold text-ink-900">Statistiques</h1>

        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatTile label="Photos" value={stats.photo_count} />
          <StatTile label="Photos indexees" value={stats.photos_indexed} />
          <StatTile label="Photos vendues" value={stats.photos_sold} />
          <StatTile
            label="Revenu total"
            value={`${stats.total_revenue.toLocaleString("fr-FR")} ${stats.currency}`}
          />
        </div>

        <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatTile label="Commandes reussies" value={stats.orders_success} />
          <StatTile label="A confirmer" value={stats.orders_awaiting_confirmation} />
          <StatTile label="Echouees" value={stats.orders_failed} />
          <StatTile label="Photos en cours d'indexation" value={stats.photos_pending} />
        </div>

        <div className="glass mt-8 rounded-2xl p-5">
          <h2 className="mb-4 text-lg font-semibold text-ink-900">Revenu par jour</h2>
          {chartData.length === 0 ? (
            <p className="text-ink-500">Aucune vente pour le moment.</p>
          ) : (
            <div style={{ width: "100%", height: 300 }}>
              <ResponsiveContainer>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(20,23,31,0.08)" />
                  <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip formatter={(value: number) => [`${value} ${stats.currency}`, "Revenu"]} />
                  <Bar dataKey="revenu" fill="#c9a15a" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        <div className="glass mt-8 rounded-2xl p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-ink-900">Historique des commandes</h2>
            <button
              type="button"
              disabled={orders.length === 0}
              onClick={() => downloadCsv(`commandes-${eventId}.csv`, ordersToCsv(orders))}
              className="btn-ghost !px-4 !py-2 text-xs disabled:opacity-40"
            >
              Telecharger le CSV
            </button>
          </div>

          {orders.length === 0 ? (
            <p className="text-ink-500">Aucune commande pour le moment.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] text-left text-sm">
                <thead>
                  <tr className="border-b border-ink-900/10 text-xs uppercase tracking-wide text-ink-500">
                    <th className="py-2 pr-4">N&deg; commande</th>
                    <th className="py-2 pr-4">Date</th>
                    <th className="py-2 pr-4">Heure</th>
                    <th className="py-2 pr-4">Telephone</th>
                    <th className="py-2 pr-4">Photos</th>
                    <th className="py-2 pr-4">Montant</th>
                    <th className="py-2 pr-4">Moyen</th>
                    <th className="py-2">Statut</th>
                  </tr>
                </thead>
                <tbody>
                  {orders.map((order) => {
                    const created = new Date(order.created_at);
                    return (
                      <tr key={order.id} className="border-b border-ink-900/5 text-ink-700">
                        <td className="py-2 pr-4 font-mono text-xs text-ink-500">{order.id.slice(0, 8)}</td>
                        <td className="py-2 pr-4">{created.toLocaleDateString("fr-FR")}</td>
                        <td className="py-2 pr-4">{created.toLocaleTimeString("fr-FR")}</td>
                        <td className="py-2 pr-4">{order.contact_phone}</td>
                        <td className="py-2 pr-4">{order.photo_count}</td>
                        <td className="py-2 pr-4 font-medium text-ink-900">
                          {order.total_amount.toLocaleString("fr-FR")} {order.currency}
                        </td>
                        <td className="py-2 pr-4">{order.payment_method}</td>
                        <td className="py-2">
                          <span
                            className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                              order.status === "success"
                                ? "bg-emerald-100 text-emerald-700"
                                : order.status === "failed"
                                  ? "bg-red-100 text-red-700"
                                  : "bg-amber-100 text-amber-700"
                            }`}
                          >
                            {STATUS_LABELS[order.status] ?? order.status}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}

export default function StatsPage() {
  return (
    <RequireAuth>
      <StatsContent />
    </RequireAuth>
  );
}
