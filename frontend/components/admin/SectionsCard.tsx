"use client";

import { FormEvent, useState } from "react";
import { api, ApiError } from "@/lib/api-client";
import { sectionDetails } from "@/components/gallery/SectionTabs";
import type { EventSection } from "@/types/api";

const inputClass =
  "w-full rounded-xl border border-ink-900/10 bg-white/70 px-3 py-2 text-sm outline-none transition focus:border-brand-accent focus:ring-2 focus:ring-brand-accent/20";

function toLocalInput(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function errorText(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.message : fallback;
}

function SectionForm({
  initial,
  submitLabel,
  onSubmit,
  onCancel,
}: {
  initial?: EventSection;
  submitLabel: string;
  onSubmit: (data: { name: string; starts_at: string | null; location: string | null }) => Promise<void>;
  onCancel?: () => void;
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [startsAt, setStartsAt] = useState(toLocalInput(initial?.starts_at ?? null));
  const [location, setLocation] = useState(initial?.location ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handle(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await onSubmit({
        name: name.trim(),
        starts_at: startsAt ? new Date(startsAt).toISOString() : null,
        location: location.trim() || null,
      });
      if (!initial) {
        setName("");
        setStartsAt("");
        setLocation("");
      }
    } catch (err) {
      setError(errorText(err, "Enregistrement impossible."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={handle} className="flex flex-col gap-2">
      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        maxLength={120}
        placeholder="Nom de la partie (ex : Mairie, Réception)"
        aria-label="Nom de la partie"
        className={inputClass}
      />
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        <input
          type="datetime-local"
          value={startsAt}
          onChange={(e) => setStartsAt(e.target.value)}
          aria-label="Date et heure (facultatif)"
          className={inputClass}
        />
        <input
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          maxLength={255}
          placeholder="Lieu (facultatif)"
          aria-label="Lieu (facultatif)"
          className={inputClass}
        />
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div className="flex gap-2">
        <button type="submit" disabled={busy || !name.trim()} className="btn-primary flex-1 !py-2 text-sm disabled:opacity-50">
          {busy ? "Enregistrement..." : submitLabel}
        </button>
        {onCancel && (
          <button type="button" onClick={onCancel} className="rounded-xl border border-ink-900/15 px-4 text-sm font-semibold text-ink-700">
            Annuler
          </button>
        )}
      </div>
    </form>
  );
}

/** Parties de l'evenement (mairie, eglise, reception...) : un seul evenement,
 * un seul QR code et un seul pack ; les invites voient des onglets. */
export default function SectionsCard({
  eventId,
  sections,
  onChange,
  uploadSectionId,
  onUploadSectionChange,
}: {
  eventId: string;
  sections: EventSection[];
  onChange: (sections: EventSection[]) => void;
  uploadSectionId: string | null;
  onUploadSectionChange: (sectionId: string | null) => void;
}) {
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function reload() {
    onChange(await api.listSections(eventId));
  }

  async function move(section: EventSection, delta: number) {
    setError(null);
    try {
      onChange(await api.updateSection(eventId, section.id, { position: section.position + delta }));
    } catch (err) {
      setError(errorText(err, "Déplacement impossible."));
    }
  }

  async function remove(section: EventSection) {
    const photos = section.photo_count
      ? ` Ses ${section.photo_count} photo${section.photo_count > 1 ? "s restent" : " reste"} dans l'événement, sans partie.`
      : "";
    if (!confirm(`Supprimer la partie « ${section.name} » ?${photos}`)) return;
    setError(null);
    try {
      await api.deleteSection(eventId, section.id);
      if (uploadSectionId === section.id) onUploadSectionChange(null);
      await reload();
    } catch (err) {
      setError(errorText(err, "Suppression impossible."));
    }
  }

  return (
    <section className="glass mb-5 rounded-2xl p-5">
      <h2 className="mb-1 text-sm font-semibold text-ink-900">Parties de l&apos;événement</h2>
      <p className="mb-3 text-xs text-ink-500">
        Mairie, église, réception… Un seul événement, un seul QR code et un seul pack : les invités voient un onglet par
        partie, et la recherche par visage couvre toutes les parties.
      </p>

      {sections.length > 0 && (
        <ul className="mb-3 flex flex-col gap-2">
          {sections.map((s, i) => (
            <li key={s.id} className="rounded-xl border border-ink-900/10 bg-white/60 p-3">
              {editing === s.id ? (
                <SectionForm
                  initial={s}
                  submitLabel="Enregistrer"
                  onCancel={() => setEditing(null)}
                  onSubmit={async (data) => {
                    onChange(await api.updateSection(eventId, s.id, data));
                    setEditing(null);
                  }}
                />
              ) : (
                <div className="flex items-start gap-2">
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold text-ink-900">
                      {s.name} <span className="font-normal text-ink-500">· {s.photo_count} photo{s.photo_count > 1 ? "s" : ""}</span>
                    </p>
                    {sectionDetails(s) && <p className="text-xs text-ink-500">{sectionDetails(s)}</p>}
                  </div>
                  <div className="flex shrink-0 items-center gap-1">
                    <button type="button" aria-label={`Monter ${s.name}`} disabled={i === 0} onClick={() => move(s, -1)}
                      className="h-8 w-8 rounded-lg border border-ink-900/10 text-sm disabled:opacity-30">↑</button>
                    <button type="button" aria-label={`Descendre ${s.name}`} disabled={i === sections.length - 1} onClick={() => move(s, 1)}
                      className="h-8 w-8 rounded-lg border border-ink-900/10 text-sm disabled:opacity-30">↓</button>
                    <button type="button" onClick={() => setEditing(s.id)} className="h-8 rounded-lg border border-ink-900/10 px-2 text-xs font-semibold">
                      Modifier
                    </button>
                    <button type="button" onClick={() => remove(s)} className="h-8 rounded-lg border border-red-200 px-2 text-xs font-semibold text-red-600">
                      Supprimer
                    </button>
                  </div>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}

      {adding ? (
        <SectionForm
          submitLabel="Ajouter la partie"
          onCancel={() => setAdding(false)}
          onSubmit={async (data) => {
            const created = await api.createSection(eventId, data);
            await reload();
            if (sections.length === 0) onUploadSectionChange(created.id);
            setAdding(false);
          }}
        />
      ) : (
        <button type="button" onClick={() => setAdding(true)} className="w-full rounded-xl border border-dashed border-brand/30 py-2 text-sm font-semibold text-brand">
          + Ajouter une partie
        </button>
      )}

      {sections.length > 0 && (
        <div className="mt-4">
          <label htmlFor="upload-section" className="mb-1 block text-sm font-medium text-ink-700">
            Ranger les nouvelles photos dans
          </label>
          <select
            id="upload-section"
            value={uploadSectionId ?? ""}
            onChange={(e) => onUploadSectionChange(e.target.value || null)}
            className={inputClass}
          >
            <option value="">Aucune partie</option>
            {sections.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>
      )}
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </section>
  );
}
