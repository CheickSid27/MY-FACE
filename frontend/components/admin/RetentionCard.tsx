"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api-client";
import type { RetentionReport } from "@/types/api";

/** Conservation des donnees (declaree a l'ARTCI) : ce que la suppression
 * automatique supprime a son prochain passage. En simulation tant que
 * RETENTION_ENABLED n'est pas a true dans .env. */
export default function RetentionCard() {
  const [report, setReport] = useState<RetentionReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    try {
      setReport(await api.getRetentionReport());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Chargement impossible.");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function keep(eventId: string, name: string) {
    if (!confirm(`Conserver les photos de « ${name} » sans limite de durée ? À réserver à un événement de démonstration.`)) {
      return;
    }
    setBusy(true);
    try {
      await api.setEventRetentionExempt(eventId, true);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Action impossible.");
    } finally {
      setBusy(false);
    }
  }

  async function runNow() {
    if (!confirm("Supprimer maintenant les photos et numéros listés ? C'est définitif.")) return;
    setBusy(true);
    setMessage(null);
    try {
      const done = await api.runRetention();
      setMessage(`${done.photos_deleted} photo(s) supprimée(s), ${done.orders_anonymized} numéro(s) effacé(s).`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Suppression impossible.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="glass mt-6 rounded-2xl p-5">
      <h2 className="mb-1 text-xl font-bold text-ink-900">Conservation des données</h2>
      {report && (
        <p className="mb-4 text-xs text-ink-500">
          Photos et empreintes des visages supprimées {report.photo_days} jours après l&apos;événement, numéro de
          téléphone des commandes effacé après {report.order_days} jours (durées déclarées à l&apos;ARTCI). Le selfie
          n&apos;est jamais enregistré.
        </p>
      )}
      {error && <p className="mb-3 text-sm text-red-600">{error}</p>}
      {!report && !error && <p className="text-sm text-ink-500">Chargement...</p>}

      {report && (
        <>
          <p
            className={`mb-4 rounded-xl px-3 py-2 text-sm ${
              report.enabled ? "bg-emerald-50 text-emerald-800" : "bg-amber-50 text-amber-900"
            }`}
          >
            {report.enabled
              ? "Suppression automatique active : un passage chaque jour."
              : "Mode simulation : rien n'est supprimé. Pour activer, mettre RETENTION_ENABLED=true dans le fichier .env puis redémarrer MYFACE."}
          </p>

          <h3 className="mb-2 text-sm font-semibold text-ink-900">
            Événements dont les photos {report.enabled ? "seront supprimées" : "seraient supprimées"} au prochain passage
          </h3>
          {report.events.length === 0 ? (
            <p className="mb-4 text-sm text-ink-500">Aucun.</p>
          ) : (
            <ul className="mb-4 space-y-2">
              {report.events.map((e) => (
                <li key={e.event_id} className="flex items-center justify-between gap-3 rounded-xl bg-white/60 px-3 py-2 text-sm">
                  <span>
                    <span className="font-medium text-ink-900">{e.name}</span>
                    <span className="text-ink-500">
                      {" "}
                      · {new Date(e.date).toLocaleDateString("fr-FR")} · {e.photo_count} photo{e.photo_count > 1 ? "s" : ""}
                    </span>
                  </span>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => keep(e.event_id, e.name)}
                    className="shrink-0 text-xs font-semibold text-brand hover:underline disabled:opacity-50"
                  >
                    Conserver (démo)
                  </button>
                </li>
              ))}
            </ul>
          )}
          <p className="mb-4 text-sm text-ink-700">
            Commandes dont le numéro {report.enabled ? "sera" : "serait"} effacé : {report.orders_to_anonymize}
          </p>

          {message && <p className="mb-3 text-sm text-emerald-700">{message}</p>}
          {report.enabled && (report.events.length > 0 || report.orders_to_anonymize > 0) && (
            <button type="button" disabled={busy} onClick={runNow} className="btn-primary w-full disabled:opacity-50">
              {busy ? "Suppression..." : "Supprimer maintenant"}
            </button>
          )}
        </>
      )}
    </section>
  );
}
