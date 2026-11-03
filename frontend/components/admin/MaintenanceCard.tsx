"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api-client";
import type { MaintenanceAdmin } from "@/types/api";

const DEFAULT_HINT = "MYFACE est en maintenance. Revenez dans quelques minutes : vos photos vous attendent.";

/** Bouton du mode maintenance : les pages invites affichent le message tant
 * qu'il est actif. A l'activation, l'admin choisit si les photographes sont
 * aussi arretes ; l'admin, lui, garde toujours l'acces. */
export default function MaintenanceCard() {
  const [state, setState] = useState<MaintenanceAdmin | null>(null);
  const [message, setMessage] = useState("");
  const [photographers, setPhotographers] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getAdminMaintenance()
      .then((data) => {
        setState(data);
        setMessage(data.message ?? "");
        setPhotographers(data.photographers);
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Chargement impossible."));
  }, []);

  async function save(active: boolean) {
    setBusy(true);
    setError(null);
    try {
      const data = await api.setAdminMaintenance({ active, message: message.trim() || null, photographers: active && photographers });
      setState(data);
      setMessage(data.message ?? "");
      setPhotographers(data.photographers);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Enregistrement impossible.");
    } finally {
      setBusy(false);
    }
  }

  const active = state?.active ?? false;
  const since = state?.since ? new Date(state.since).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" }) : null;

  return (
    <section className={`glass mb-4 rounded-2xl p-5 ${active ? "ring-2 ring-amber-500" : ""}`}>
      <div className="mb-1 flex items-center justify-between gap-3">
        <h2 className="text-xl font-bold text-ink-900">Mode maintenance</h2>
        <span
          className={`rounded-full px-3 py-1 text-xs font-semibold ${
            active ? "bg-amber-100 text-amber-800" : "bg-emerald-50 text-emerald-700"
          }`}
        >
          {state === null ? "…" : active ? "Activé" : "Désactivé"}
        </span>
      </div>
      <p className="mb-4 text-xs text-ink-500">
        Pendant une mise à jour, les invités voient ce message à la place de la galerie, du scan et du panier, et les
        nouvelles commandes sont refusées. Vous choisissez si les photographes sont aussi arrêtés. Votre espace reste
        toujours ouvert. Tout se rouvre seul quand vous coupez le mode maintenance.
      </p>
      {active && since && <p className="mb-3 text-sm font-medium text-amber-800">Activé depuis le {since}.</p>}
      <label htmlFor="maintenance-message" className="mb-1 block text-sm font-medium text-ink-700">
        Message pour les invités (facultatif)
      </label>
      <textarea
        id="maintenance-message"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        maxLength={300}
        rows={2}
        placeholder={DEFAULT_HINT}
        className="mb-3 w-full rounded-xl border border-ink-900/10 bg-white/70 px-3.5 py-2.5 text-sm outline-none transition focus:border-brand-accent focus:ring-2 focus:ring-brand-accent/20"
      />
      <label className="mb-4 flex cursor-pointer items-start gap-3 rounded-xl border border-ink-900/10 bg-white/60 p-3">
        <input
          type="checkbox"
          checked={photographers}
          onChange={(e) => setPhotographers(e.target.checked)}
          className="mt-0.5 h-4 w-4 accent-amber-500"
        />
        <span className="text-sm text-ink-700">
          <span className="font-semibold text-ink-900">Arrêter aussi les photographes</span>
          <span className="block text-xs text-ink-500">
            Leur espace affiche le même message, et l&apos;envoi de photos et l&apos;achat de packs sont refusés.
            Sans cette case, ils continuent à travailler.
          </span>
        </span>
      </label>
      {active && (
        <p className="mb-3 text-sm text-ink-700">
          Photographes : <strong>{state?.photographers ? "arrêtés" : "continuent à travailler"}</strong>
          {photographers !== state?.photographers && " (cliquez « Mettre à jour » pour changer)"}
        </p>
      )}
      {error && <p className="mb-3 text-sm text-red-600">{error}</p>}
      <div className="flex flex-wrap gap-2">
        {active ? (
          <>
            <button type="button" disabled={busy} onClick={() => save(false)} className="btn-primary flex-1 disabled:opacity-50">
              {busy ? "Enregistrement..." : "Couper le mode maintenance"}
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => save(true)}
              className="flex-1 rounded-xl border border-ink-900/15 px-4 py-2.5 text-sm font-semibold text-ink-700 disabled:opacity-50"
            >
              Mettre à jour
            </button>
          </>
        ) : (
          <button
            type="button"
            disabled={busy || state === null}
            onClick={() => save(true)}
            className="w-full rounded-xl bg-amber-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-amber-600 disabled:opacity-50"
          >
            {busy ? "Activation..." : "Activer le mode maintenance"}
          </button>
        )}
      </div>
    </section>
  );
}
