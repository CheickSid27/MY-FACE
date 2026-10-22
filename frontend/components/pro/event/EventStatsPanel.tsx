"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "@/lib/api-client";
import type { EventStats } from "@/types/api";

function StatTile({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl border border-[#E6DED0] bg-white p-4">
      <p className="text-xs text-ink-500">{label}</p>
      <p className="mt-1 font-pro text-lg font-semibold text-ink-900">{value}</p>
    </div>
  );
}

/** Chiffres de l'evenement (haut de l'onglet Ventes) : ventes, commandes
 * et revenu par jour. L'historique detaille est dans le volet paiements. */
export default function EventStatsPanel({ eventId }: { eventId: string }) {
  const [stats, setStats] = useState<EventStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api
      .getEventStats(eventId)
      .then(setStats)
      .catch(() => setError("Impossible de charger les statistiques."));
  }, [eventId]);

  useEffect(() => {
    load();
  }, [load]);

  if (error) return <p className="mb-6 text-sm text-red-600">{error}</p>;
  if (!stats) return <div className="skeleton mb-6 h-24 rounded-2xl" />;

  const chartData = stats.sales_by_day.map((d) => ({
    date: new Date(d.date).toLocaleDateString("fr-FR", { day: "numeric", month: "short" }),
    revenu: d.revenue,
  }));

  return (
    <div className="mb-8">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatTile label="Revenu total" value={`${stats.total_revenue.toLocaleString("fr-FR")} ${stats.currency}`} />
        <StatTile label="Commandes payées" value={stats.orders_success} />
        <StatTile label="Photos vendues" value={stats.photos_sold} />
        <StatTile label="À confirmer" value={stats.orders_awaiting_confirmation} />
      </div>
      {chartData.length > 0 && (
        <div className="mt-3 rounded-2xl border border-[#E6DED0] bg-white p-4">
          <h3 className="mb-3 text-sm font-semibold text-ink-900">Revenu par jour</h3>
          <div style={{ width: "100%", height: 220 }}>
            <ResponsiveContainer>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(20,23,31,0.08)" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip formatter={(value: number) => [`${value} ${stats.currency}`, "Revenu"]} />
                <Bar dataKey="revenu" fill="#f26a1b" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}
