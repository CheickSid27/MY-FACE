"use client";

import { useState } from "react";
import { api, ApiError } from "@/lib/api-client";
import type { Event } from "@/types/api";

/** Le photographe autorise l'equipe MYFACE a gerer son evenement pour
 * l'aider (photos, parties, reglages), jusqu'a ce qu'il retire l'acces. Sans
 * cette autorisation, l'equipe ne voit qu'un resume et la galerie invite. */
export default function AdminAccessCard({ event, onSaved }: { event: Event; onSaved: (event: Event) => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const granted = event.admin_access;

  async function toggle() {
    if (!granted && !confirm("Autoriser l'équipe MYFACE à gérer cet événement (photos, parties, réglages) jusqu'à ce que vous retiriez l'accès ?")) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      onSaved(await api.setAdminAccess(event.id, !granted));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Enregistrement impossible.");
    } finally {
      setBusy(false);
    }
  }

  const since = event.admin_access_since
    ? new Date(event.admin_access_since).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" })
    : null;

  return (
    <section className="glass mb-6 rounded-2xl p-5">
      <div className="mb-1 flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold text-ink-900">Aide de l&apos;équipe MYFACE</h2>
        <span
          className={`rounded-full px-3 py-1 text-xs font-semibold ${
            granted ? "bg-emerald-50 text-emerald-700" : "bg-ink-900/5 text-ink-500"
          }`}
        >
          {granted ? "Accès accordé" : "Pas d'accès"}
        </span>
      </div>
      <p className="mb-3 text-xs text-ink-500">
        Votre événement est à vous : l&apos;équipe MYFACE ne voit que son résumé (nombre de photos, ventes) et la
        galerie des invités. Si vous avez besoin d&apos;aide, donnez-lui l&apos;accès ; vous pourrez le retirer à
        tout moment.
      </p>
      {granted && since && <p className="mb-3 text-xs text-emerald-700">Accès accordé depuis le {since}.</p>}
      {error && <p className="mb-3 text-sm text-red-600">{error}</p>}
      <button
        type="button"
        disabled={busy}
        onClick={toggle}
        className={`w-full rounded-xl px-4 py-2.5 text-sm font-semibold disabled:opacity-50 ${
          granted ? "border border-ink-900/15 text-ink-700" : "btn-primary"
        }`}
      >
        {busy ? "Enregistrement..." : granted ? "Retirer l'accès" : "Autoriser MYFACE à m'aider"}
      </button>
    </section>
  );
}
