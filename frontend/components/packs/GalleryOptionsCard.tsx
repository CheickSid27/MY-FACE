"use client";

import { useState } from "react";
import { api, ApiError } from "@/lib/api-client";
import type { Event } from "@/types/api";

interface GalleryOptionsCardProps {
  event: Event;
  /** Options du pack (voir services/packs.py) : gallery_password, custom_watermark */
  features: string[];
  studioName: string | null;
  onSaved: (event: Event) => void;
}

/** Options des packs Evenement et Pro : galerie protegee par mot de passe et
 * filigrane au nom du photographe. Visibles mais verrouillees au pack
 * Decouverte, pour montrer ce que le pack superieur apporte. */
export default function GalleryOptionsCard({ event, features, studioName, onSaved }: GalleryOptionsCardProps) {
  const canPassword = features.includes("gallery_password");
  const canWatermark = features.includes("custom_watermark");
  const [password, setPassword] = useState("");
  const [watermark, setWatermark] = useState(event.watermark_text ?? "");
  const [saving, setSaving] = useState<"password" | "watermark" | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function save(kind: "password" | "watermark", payload: { gallery_password?: string; watermark_text?: string | null }) {
    setSaving(kind);
    setError(null);
    setMessage(null);
    try {
      const updated = await api.updateEvent(event.id, payload);
      onSaved(updated);
      if (kind === "password") {
        setPassword("");
        setMessage(payload.gallery_password ? "Mot de passe enregistré." : "Galerie de nouveau ouverte à tous.");
      } else {
        setMessage("Filigrane enregistré : les aperçus sont mis à jour en arrière-plan.");
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Enregistrement impossible.");
    } finally {
      setSaving(null);
    }
  }

  const lockNote = <p className="mt-1 text-[11px] font-medium text-brand-accent">Disponible à partir du pack Événement</p>;
  const inputClass =
    "w-full rounded-xl border border-ink-900/10 bg-white/70 px-3.5 py-2.5 text-sm outline-none transition focus:border-brand-accent focus:ring-2 focus:ring-brand-accent/20 disabled:opacity-50";

  return (
    <div className="glass mb-6 rounded-2xl p-5">
      <h2 className="mb-3 text-sm font-semibold text-ink-900">Galerie privée et filigrane</h2>

      <div className="mb-5">
        <p className="text-sm font-medium text-ink-900">Mot de passe de la galerie</p>
        <p className="mb-2 text-xs text-ink-500">
          {event.has_gallery_password
            ? "La galerie est protégée : les invités saisissent le mot de passe sur la page d'accueil (la borne passe sans)."
            : "Sans mot de passe, toute personne qui a le lien ou le QR code voit la galerie."}
        </p>
        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            type="text"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={event.has_gallery_password ? "Nouveau mot de passe" : "Ex : mariage2026"}
            disabled={!canPassword || saving !== null}
            minLength={4}
            maxLength={64}
            className={inputClass}
          />
          <button
            type="button"
            onClick={() => save("password", { gallery_password: password.trim() })}
            disabled={!canPassword || password.trim().length < 4 || saving !== null}
            className="btn-primary shrink-0 !px-4 !py-2.5 text-sm disabled:opacity-50"
          >
            {saving === "password" ? "..." : "Protéger"}
          </button>
          {event.has_gallery_password && (
            <button
              type="button"
              onClick={() => save("password", { gallery_password: "" })}
              disabled={saving !== null}
              className="btn-ghost shrink-0 !px-4 !py-2.5 text-sm"
            >
              Retirer
            </button>
          )}
        </div>
        {!canPassword && lockNote}
      </div>

      <div>
        <p className="text-sm font-medium text-ink-900">Filigrane des aperçus</p>
        <p className="mb-2 text-xs text-ink-500">
          Texte incrusté sur les aperçus que voient les invités sur leur téléphone (jamais sur les photos achetées
          ou offertes). Vide : {canWatermark && studioName ? `« ${studioName} »` : "« MYFACE »"}.
        </p>
        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            type="text"
            value={watermark}
            onChange={(e) => setWatermark(e.target.value)}
            placeholder={studioName ?? "Nom de votre studio"}
            maxLength={40}
            disabled={!canWatermark || saving !== null}
            className={inputClass}
          />
          <button
            type="button"
            onClick={() => save("watermark", { watermark_text: watermark.trim() || null })}
            disabled={!canWatermark || saving !== null || watermark.trim() === (event.watermark_text ?? "")}
            className="btn-primary shrink-0 !px-4 !py-2.5 text-sm disabled:opacity-50"
          >
            {saving === "watermark" ? "..." : "Enregistrer"}
          </button>
        </div>
        {!canWatermark && lockNote}
      </div>

      {message && <p className="mt-3 text-sm text-emerald-700">{message}</p>}
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
    </div>
  );
}
