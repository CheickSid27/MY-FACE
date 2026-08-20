"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import RequireAuth from "@/components/admin/RequireAuth";
import { api } from "@/lib/api-client";
import { useAuthStore } from "@/store/auth-store";
import type { EventListItem } from "@/types/api";

function AdminEventsContent() {
  const [events, setEvents] = useState<EventListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const logout = useAuthStore((s) => s.logout);

  const [name, setName] = useState("");
  const [date, setDate] = useState("");
  const [location, setLocation] = useState("");
  const [unitPrice, setUnitPrice] = useState("1000");
  const [creating, setCreating] = useState(false);

  async function loadEvents() {
    setLoading(true);
    try {
      const data = await api.listEvents();
      setEvents(data);
    } catch {
      setError("Impossible de charger les evenements.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadEvents();
  }, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setCreating(true);
    setError(null);
    try {
      await api.createEvent({
        name,
        date: new Date(date).toISOString(),
        location,
        pricing: { unit_price: Number(unitPrice) },
      });
      setName("");
      setDate("");
      setLocation("");
      setUnitPrice("1000");
      setShowForm(false);
      await loadEvents();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors de la creation.");
    } finally {
      setCreating(false);
    }
  }

  return (
    <main className="min-h-screen bg-gradient-to-b from-surface-alt to-surface p-6">
      <div className="mx-auto max-w-3xl">
        <div className="glass mb-6 flex items-center justify-between rounded-2xl px-5 py-4">
          <h1 className="text-xl font-bold text-ink-900">Evenements</h1>
          <div className="flex items-center gap-4">
            <Link href="/admin/users" className="text-sm font-medium text-ink-500 transition hover:text-brand">
              Utilisateurs
            </Link>
            <button
              type="button"
              onClick={logout}
              className="text-sm font-medium text-ink-500 transition hover:text-brand"
            >
              Deconnexion
            </button>
          </div>
        </div>

        <button type="button" onClick={() => setShowForm((v) => !v)} className="btn-primary mb-4 !px-5 !py-2.5 text-sm">
          {showForm ? "Annuler" : "+ Nouvel evenement"}
        </button>

        {showForm && (
          <form onSubmit={handleCreate} className="glass mb-6 rounded-2xl p-5">
            <div className="mb-3">
              <label className="mb-1 block text-sm font-medium text-ink-700">Nom</label>
              <input
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full rounded-xl border border-ink-900/10 bg-white/70 px-3.5 py-2.5 outline-none transition focus:border-brand-accent focus:ring-2 focus:ring-brand-accent/20"
              />
            </div>
            <div className="mb-3">
              <label className="mb-1 block text-sm font-medium text-ink-700">Date</label>
              <input
                type="datetime-local"
                required
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className="w-full rounded-xl border border-ink-900/10 bg-white/70 px-3.5 py-2.5 outline-none transition focus:border-brand-accent focus:ring-2 focus:ring-brand-accent/20"
              />
            </div>
            <div className="mb-3">
              <label className="mb-1 block text-sm font-medium text-ink-700">Lieu</label>
              <input
                required
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                className="w-full rounded-xl border border-ink-900/10 bg-white/70 px-3.5 py-2.5 outline-none transition focus:border-brand-accent focus:ring-2 focus:ring-brand-accent/20"
              />
            </div>
            <div className="mb-4">
              <label className="mb-1 block text-sm font-medium text-ink-700">Prix unitaire (XOF)</label>
              <input
                type="number"
                min={1}
                required
                value={unitPrice}
                onChange={(e) => setUnitPrice(e.target.value)}
                className="w-full rounded-xl border border-ink-900/10 bg-white/70 px-3.5 py-2.5 outline-none transition focus:border-brand-accent focus:ring-2 focus:ring-brand-accent/20"
              />
            </div>
            <button type="submit" disabled={creating} className="btn-accent !px-5 !py-2.5 text-sm disabled:opacity-50">
              {creating ? "Creation..." : "Creer l'evenement"}
            </button>
          </form>
        )}

        {error && <p className="mb-4 text-red-600">{error}</p>}
        {loading && <p className="text-ink-500">Chargement...</p>}

        <ul className="space-y-2">
          {events.map((event) => (
            <li key={event.id}>
              <Link
                href={`/admin/events/${event.id}`}
                className="glass block rounded-2xl p-4 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-card"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-semibold text-ink-900">{event.name}</p>
                    <p className="text-sm text-ink-500">
                      {new Date(event.date).toLocaleDateString("fr-FR")} &middot; {event.location}
                    </p>
                  </div>
                  <span className="text-sm text-ink-300">{event.photo_count} photos</span>
                </div>
              </Link>
            </li>
          ))}
        </ul>

        {!loading && events.length === 0 && (
          <p className="text-center text-ink-500">Aucun evenement pour le moment.</p>
        )}
      </div>
    </main>
  );
}

export default function AdminEventsPage() {
  return (
    <RequireAuth>
      <AdminEventsContent />
    </RequireAuth>
  );
}
