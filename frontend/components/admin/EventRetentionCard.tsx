"use client";

import { useState } from "react";
import { api, ApiError } from "@/lib/api-client";
import type { Event } from "@/types/api";

function frDate(iso: string): string {
  return new Date(iso).toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" });
}

/** Date de suppression automatique des photos de l'evenement (conservation
 * declaree a l'ARTCI). Un admin peut exempter un evenement de demonstration. */
export default function EventRetentionCard({
  event,
  isAdmin,
  onChanged,
}: {
  event: Event;
  isAdmin: boolean;
  onChanged: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function toggle() {
    const exempt = !event.retention_exempt;
    if (exempt && !confirm("Conserver les photos de cet événement sans limite de durée ? À réserver à un événement de démonstration.")) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.setEventRetentionExempt(event.id, exempt);
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Action impossible.");
    } finally {
      setBusy(false);
    }
  }

  let text: string;
  if (event.photos_purged_at) {
    text = `Photos et visages supprimés le ${frDate(event.photos_purged_at)} (fin de la durée de conservation).`;
  } else if (event.photos_available_until) {
    const days = Math.round((Date.parse(event.photos_available_until) - Date.parse(event.date)) / 86_400_000);
    text = `Photos et visages supprimés automatiquement le ${frDate(event.photos_available_until)}, ${days} jours après l'événement : prévenez vos clients de télécharger leurs photos avant.`;
  } else {
    text = "Événement conservé sans limite de durée (démonstration).";
  }

  return (
    <div className="glass mb-6 rounded-2xl p-5">
      <h2 className="mb-1 text-sm font-semibold text-ink-900">Durée de conservation</h2>
      <p className="text-xs text-ink-500">{text}</p>
      {isAdmin && !event.photos_purged_at && (
        <button
          type="button"
          disabled={busy}
          onClick={toggle}
          className="mt-3 text-xs font-semibold text-brand hover:underline disabled:opacity-50"
        >
          {event.retention_exempt ? "Appliquer la durée normale" : "Conserver sans limite (démo, admin)"}
        </button>
      )}
      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
    </div>
  );
}
