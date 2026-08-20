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
import type { EventStats } from "@/types/api";

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
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getEventStats(eventId)
      .then(setStats)
      .catch(() => setError("Impossible de charger les statistiques."));
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
