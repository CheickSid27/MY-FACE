"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import PageHeader from "@/components/pro/PageHeader";
import { api, ApiError } from "@/lib/api-client";
import type { ActivityPage } from "@/types/api";

// Volet Statistiques : toutes les actions realisees sur MYFACE (inscriptions,
// connexions, evenements, photos, selfies, telechargements, packs...),
// filtrables et exportables. Les paiements des invites sont dans Ventes.
type Period = "jour" | "7j" | "30j" | "tout" | "dates";

const PERIODS: { id: Period; label: string }[] = [
  { id: "jour", label: "Aujourd'hui" },
  { id: "7j", label: "7 jours" },
  { id: "30j", label: "30 jours" },
  { id: "tout", label: "Tout" },
  { id: "dates", label: "Dates…" },
];

function range(period: Period, from: string, to: string): { start?: string; end?: string } {
  const now = new Date();
  if (period === "jour") {
    const start = new Date(now);
    start.setHours(0, 0, 0, 0);
    return { start: start.toISOString() };
  }
  if (period === "7j") return { start: new Date(now.getTime() - 7 * 864e5).toISOString() };
  if (period === "30j") return { start: new Date(now.getTime() - 30 * 864e5).toISOString() };
  if (period === "dates") {
    return {
      start: from ? new Date(`${from}T00:00:00`).toISOString() : undefined,
      end: to ? new Date(new Date(`${to}T00:00:00`).getTime() + 864e5).toISOString() : undefined,
    };
  }
  return {};
}

function detailsText(details: Record<string, unknown> | null): string {
  if (!details) return "";
  return Object.entries(details)
    .map(([k, v]) => `${k.replace(/_/g, " ")} : ${Array.isArray(v) ? v.join(", ") : String(v)}`)
    .join(" · ");
}

const input =
  "min-h-[42px] rounded-xl border border-[#E6DED0] bg-white px-3 text-sm outline-none focus:border-brand-accent";

export default function StatisticsPage() {
  const [period, setPeriod] = useState<Period>("7j");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [action, setAction] = useState("");
  const [q, setQ] = useState("");
  const [data, setData] = useState<ActivityPage | null>(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const filters = useMemo(() => ({ ...range(period, from, to), action: action || undefined, q: q || undefined }), [period, from, to, action, q]);

  const load = useCallback(
    async (nextPage: number) => {
      setLoading(true);
      setError(null);
      try {
        const result = await api.listActivity({ ...filters, page: nextPage });
        setData((prev) => (nextPage > 1 && prev ? { ...result, items: [...prev.items, ...result.items] } : result));
        setPage(nextPage);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Chargement impossible.");
      } finally {
        setLoading(false);
      }
    },
    [filters]
  );

  useEffect(() => {
    const timer = setTimeout(() => load(1), 250);
    return () => clearTimeout(timer);
  }, [load]);

  const counts = data ? Object.entries(data.counts).sort((a, b) => b[1] - a[1]) : [];
  const totalAll = counts.reduce((sum, [, n]) => sum + n, 0);

  return (
    <>
      <PageHeader
        title="Statistiques"
        subtitle="Toutes les actions réalisées sur MYFACE"
        actions={
          <a
            href={api.activityExportUrl(filters)}
            onClick={async (e) => {
              e.preventDefault();
              try {
                await api.downloadActivityCsv(filters);
              } catch {
                alert("Export impossible, réessayez.");
              }
            }}
            className="flex min-h-[44px] items-center rounded-[14px] bg-brand px-3.5 text-sm font-bold text-[#F4EFE6]"
          >
            Exporter
          </a>
        }
      />

      <div className="mb-4 flex flex-col gap-3">
        <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 lg:mx-0 lg:px-0">
          {PERIODS.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => setPeriod(p.id)}
              className={`min-h-[38px] whitespace-nowrap rounded-full border px-4 text-sm font-semibold ${
                period === p.id ? "border-brand bg-brand text-[#F4EFE6]" : "border-[#E6DED0] bg-white"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {period === "dates" && (
            <>
              <label className="flex flex-col gap-1 text-xs text-ink-500">
                Du
                <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} className={input} />
              </label>
              <label className="flex flex-col gap-1 text-xs text-ink-500">
                Au
                <input type="date" value={to} onChange={(e) => setTo(e.target.value)} className={input} />
              </label>
            </>
          )}
          <label className="flex flex-col gap-1 text-xs text-ink-500">
            Type d&apos;action
            <select value={action} onChange={(e) => setAction(e.target.value)} className={input}>
              <option value="">Toutes les actions</option>
              {data &&
                Object.entries(data.actions).map(([key, label]) => (
                  <option key={key} value={key}>
                    {label}
                  </option>
                ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-xs text-ink-500">
            Personne ou événement
            <input
              type="search"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Nom, e-mail, événement"
              className={input}
            />
          </label>
        </div>
      </div>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

      {data && (
        <section className="mb-5 grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-5">
          <div className="rounded-2xl bg-brand p-3.5 text-[#F4EFE6]">
            <p className="font-pro text-xl font-semibold">{totalAll.toLocaleString("fr-FR")}</p>
            <p className="text-xs text-[#A9BABD]">actions sur la période</p>
          </div>
          {counts.slice(0, 9).map(([key, n]) => (
            <button
              key={key}
              type="button"
              onClick={() => setAction(action === key ? "" : key)}
              className={`rounded-2xl border p-3.5 text-left transition ${
                action === key ? "border-brand-accent bg-[#FDE7D9]" : "border-[#E6DED0] bg-white hover:border-brand-accent/50"
              }`}
            >
              <p className="font-pro text-xl font-semibold">{n.toLocaleString("fr-FR")}</p>
              <p className="text-xs leading-snug text-ink-500">{data.actions[key] ?? key}</p>
            </button>
          ))}
        </section>
      )}

      {!data && loading && <div className="skeleton h-64 rounded-3xl" />}

      {data && (
        <section className="overflow-hidden rounded-3xl border border-[#E6DED0] bg-white">
          <div className="hidden grid-cols-[150px_220px_minmax(0,1fr)_minmax(0,1fr)] gap-3 border-b border-[#EFE8DC] px-4 py-2.5 text-xs font-bold uppercase tracking-wider text-ink-500 lg:grid">
            <span>Quand</span>
            <span>Action</span>
            <span>Qui</span>
            <span>Événement et détails</span>
          </div>
          {data.items.length === 0 && <p className="p-6 text-center text-sm text-ink-500">Aucune action sur cette période.</p>}
          <ul className="divide-y divide-[#EFE8DC]">
            {data.items.map((item) => (
              <li
                key={item.id}
                className="flex flex-col gap-0.5 px-4 py-3 text-sm lg:grid lg:grid-cols-[150px_220px_minmax(0,1fr)_minmax(0,1fr)] lg:gap-3"
              >
                <span className="text-xs text-ink-500 lg:text-sm">
                  {new Date(item.at).toLocaleString("fr-FR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" })}
                </span>
                <b className="text-ink-900">{item.label}</b>
                <span className="truncate text-ink-700">{item.actor}</span>
                <span className="text-xs text-ink-500 lg:text-sm">
                  {item.event_name ? <span className="font-medium text-ink-700">{item.event_name}</span> : null}
                  {item.event_name && item.details ? " · " : ""}
                  {detailsText(item.details)}
                </span>
              </li>
            ))}
          </ul>
          {data.items.length < data.total && (
            <button
              type="button"
              disabled={loading}
              onClick={() => load(page + 1)}
              className="w-full border-t border-[#EFE8DC] py-3 text-sm font-semibold text-[#B34A08] disabled:opacity-50"
            >
              {loading ? "Chargement..." : `Voir plus (${data.items.length} sur ${data.total.toLocaleString("fr-FR")})`}
            </button>
          )}
        </section>
      )}
    </>
  );
}
