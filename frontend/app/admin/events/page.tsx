"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import PackBadge from "@/components/packs/PackBadge";
import PageHeader from "@/components/pro/PageHeader";
import { useWorkspace } from "@/components/pro/WorkspaceProvider";
import { CalendarIcon, FacesIcon, PlusIcon, SearchIcon } from "@/components/pro/icons";
import { api, ApiError } from "@/lib/api-client";
import { useAuthStore } from "@/store/auth-store";
import type { EventListItem } from "@/types/api";

type Filter = "tous" | "direct" | "venir" | "fini";

const FILTERS: { id: Filter; label: string }[] = [
  { id: "tous", label: "Tous" },
  { id: "direct", label: "Aujourd'hui" },
  { id: "venir", label: "À venir" },
  { id: "fini", label: "Terminés" },
];

const DAY = 24 * 3600 * 1000;

function momentOf(date: string): Exclude<Filter, "tous"> {
  const diff = new Date(date).getTime() - Date.now();
  if (Math.abs(diff) <= 0.75 * DAY) return "direct";
  return diff > 0 ? "venir" : "fini";
}

const CHIP: Record<Exclude<Filter, "tous">, { label: string; cls: string }> = {
  direct: { label: "Aujourd'hui", cls: "bg-[#FDE7D9] text-[#9A3F06]" },
  venir: { label: "À venir", cls: "bg-[#E3EAEB] text-ink-900" },
  fini: { label: "Terminé", cls: "bg-[#EAE3D6] text-[#3F5156]" },
};

const inputClass =
  "w-full rounded-xl border border-[#E6DED0] bg-white px-3.5 py-2.5 text-[15px] outline-none transition focus:border-brand-accent focus:ring-2 focus:ring-brand-accent/20";

function NewEventDialog({ onClose, onCreated }: { onClose: () => void; onCreated: (id: string) => void }) {
  const [name, setName] = useState("");
  const [date, setDate] = useState("");
  const [location, setLocation] = useState("");
  const [unitPrice, setUnitPrice] = useState("500");
  // Photos offertes par l'organisateur : pas de prix, pas de page de paiement
  const [offert, setOffert] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setCreating(true);
    setError(null);
    try {
      const event = await api.createEvent({
        name,
        date: new Date(date).toISOString(),
        location,
        pricing: offert ? { unit_price: 0, offert: true } : { unit_price: Number(unitPrice) },
      });
      onCreated(event.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Création impossible, réessayez.");
      setCreating(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-brand/50 backdrop-blur-sm animate-fade-in sm:items-center sm:p-4"
      onClick={onClose}
    >
      <form
        onSubmit={handleCreate}
        className="max-h-[92vh] w-full max-w-lg overflow-y-auto rounded-t-3xl bg-[#F7F3EC] p-5 pb-8 shadow-elevated animate-scale-in sm:rounded-3xl sm:pb-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mx-auto mb-4 h-1.5 w-10 rounded-full bg-ink-900/15 sm:hidden" />
        <h2 className="mb-4 font-pro text-lg font-semibold">Nouvel événement</h2>
        <label className="mb-3 block">
          <span className="mb-1 block text-sm font-medium text-ink-700">Nom</span>
          <input required value={name} onChange={(e) => setName(e.target.value)} className={inputClass} placeholder="Mariage Aya et Koffi" />
        </label>
        <div className="mb-3 grid gap-3 sm:grid-cols-2">
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-ink-700">Date et heure</span>
            <input type="datetime-local" required value={date} onChange={(e) => setDate(e.target.value)} className={inputClass} />
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-ink-700">Lieu</span>
            <input required value={location} onChange={(e) => setLocation(e.target.value)} className={inputClass} placeholder="Abidjan, Cocody" />
          </label>
        </div>
        <label className="mb-3 flex items-start gap-3 rounded-xl border border-[#E6DED0] bg-white px-3.5 py-3 text-sm text-ink-700">
          <input type="checkbox" checked={offert} onChange={(e) => setOffert(e.target.checked)} className="mt-0.5 h-4 w-4 accent-brand-accent" />
          <span>
            <span className="font-medium text-ink-900">Photos offertes aux invités</span>
            <br />
            Ils téléchargent leurs photos sans payer.
          </span>
        </label>
        {!offert && (
          <label className="mb-4 block">
            <span className="mb-1 block text-sm font-medium text-ink-700">Prix d&apos;une photo (F CFA)</span>
            <input type="number" min={1} required value={unitPrice} onChange={(e) => setUnitPrice(e.target.value)} className={inputClass} />
          </label>
        )}
        {error && <p className="mb-3 text-sm text-red-600">{error}</p>}
        <div className="flex gap-2.5">
          <button type="button" onClick={onClose} className="flex-1 rounded-xl border border-[#D9CFBF] bg-white py-3 text-sm font-semibold">
            Annuler
          </button>
          <button type="submit" disabled={creating} className="flex-1 rounded-xl bg-brand-accent py-3 text-sm font-bold text-brand disabled:opacity-50">
            {creating ? "Création..." : "Créer"}
          </button>
        </div>
      </form>
    </div>
  );
}

export default function ProEventsPage() {
  const router = useRouter();
  const { refresh } = useWorkspace();
  const user = useAuthStore((s) => s.user);
  const isAdmin = user?.role === "admin";
  const [events, setEvents] = useState<EventListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<Filter>("tous");
  const [query, setQuery] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    api
      .listEvents()
      .then(setEvents)
      .catch(() => setError("Impossible de charger les événements."));
    // Lien « Créer un événement » du bouton « + » ou de l'accueil
    if (new URLSearchParams(window.location.search).get("nouveau")) {
      setCreating(true);
      window.history.replaceState(null, "", "/admin/events");
    }
  }, []);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (events ?? []).filter(
      (e) =>
        (filter === "tous" || momentOf(e.date) === filter) &&
        (!q || e.name.toLowerCase().includes(q) || e.location.toLowerCase().includes(q))
    );
  }, [events, filter, query]);

  return (
    <>
      <PageHeader
        title="Événements"
        subtitle={events ? `${events.length} événement${events.length > 1 ? "s" : ""}` : undefined}
        actions={
          <button
            type="button"
            onClick={() => setCreating(true)}
            className="flex min-h-[44px] items-center gap-1.5 rounded-[14px] bg-brand px-3.5 text-sm font-bold text-[#F4EFE6]"
          >
            <PlusIcon size={18} /> <span className="hidden sm:inline">Nouvel événement</span>
            <span className="sm:hidden">Nouveau</span>
          </button>
        }
      />

      <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center">
        <label className="relative block lg:w-80">
          <span className="sr-only">Chercher un événement</span>
          <SearchIcon size={18} className="absolute left-3.5 top-3 text-ink-500" />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Chercher un événement"
            className="min-h-[44px] w-full rounded-[14px] border border-[#E6DED0] bg-white pl-10 pr-3.5 text-[15px] outline-none focus:border-brand-accent"
          />
        </label>
        <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 lg:mx-0 lg:px-0">
          {FILTERS.map((f) => (
            <button
              key={f.id}
              type="button"
              onClick={() => setFilter(f.id)}
              className={`min-h-[38px] whitespace-nowrap rounded-full border px-4 text-sm font-semibold transition ${
                filter === f.id ? "border-brand bg-brand text-[#F4EFE6]" : "border-[#E6DED0] bg-white text-ink-900"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
      {!events && !error && (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="skeleton h-24 rounded-3xl" />
          ))}
        </div>
      )}

      {events && visible.length === 0 && (
        <div className="flex flex-col items-center gap-3 rounded-3xl border border-dashed border-[#D9CFBF] bg-white p-8 text-center text-sm text-ink-500">
          <CalendarIcon size={28} />
          {events.length === 0 ? "Aucun événement pour le moment." : "Aucun événement ne correspond."}
          {events.length === 0 && (
            <button type="button" onClick={() => setCreating(true)} className="btn-accent !px-5 !py-2.5 text-sm">
              Créer mon premier événement
            </button>
          )}
        </div>
      )}

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {visible.map((event) => {
          const moment = momentOf(event.date);
          const chip = CHIP[moment];
          return (
            <Link
              key={event.id}
              href={`/admin/events/${event.id}`}
              className="flex items-center gap-3.5 rounded-3xl border border-[#E6DED0] bg-white p-3 transition hover:-translate-y-0.5 hover:shadow-card"
            >
              <span
                className={`flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl ${
                  moment === "direct" ? "bg-brand text-brand-accent" : moment === "venir" ? "bg-[#FDE7D9] text-[#9A3F06]" : "bg-[#EAE3D6] text-ink-900"
                }`}
              >
                {moment === "venir" ? <CalendarIcon size={26} /> : <FacesIcon size={26} />}
              </span>
              <span className="flex min-w-0 flex-1 flex-col gap-1">
                <span className="flex items-center justify-between gap-2">
                  <b className="truncate text-[15px]">{event.name}</b>
                  <span className={`shrink-0 rounded-lg px-2 py-1 text-[11px] font-bold uppercase tracking-wide ${chip.cls}`}>
                    {chip.label}
                  </span>
                </span>
                <span className="truncate text-[13px] text-ink-500">
                  {new Date(event.date).toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" })} ·{" "}
                  {event.location}
                </span>
                <span className="flex flex-wrap items-center gap-2 text-[13px]">
                  <span>
                    {event.photo_count.toLocaleString("fr-FR")}
                    {event.photo_limit !== null ? ` / ${event.photo_limit.toLocaleString("fr-FR")}` : ""} photos
                  </span>
                  <PackBadge pack={event.pack} />
                  {event.pack_pending && (
                    <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-800">
                      Paiement du pack en cours
                    </span>
                  )}
                </span>
                {isAdmin && event.organizer_email && event.organizer_email !== user?.email && (
                  <span className="truncate text-xs text-ink-500">Photographe : {event.organizer_email}</span>
                )}
              </span>
            </Link>
          );
        })}
      </div>

      {creating && (
        <NewEventDialog
          onClose={() => setCreating(false)}
          onCreated={(id) => {
            refresh();
            router.push(`/admin/events/${id}?onglet=photos&ajout=1`);
          }}
        />
      )}
    </>
  );
}
