"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";
import { getKioskToken } from "@/lib/kiosk";
import type { EventSection } from "@/types/api";

/** Parties de l'evenement (mairie, reception...), lues dans la vue publique
 * deja en memoire de la visite : aucun aller-retour de plus. */
export function useEventSections(eventId: string): EventSection[] {
  const [sections, setSections] = useState<EventSection[]>([]);
  useEffect(() => {
    let alive = true;
    api
      .getEventPublic(eventId, getKioskToken(eventId))
      .then((event) => alive && setSections(event.sections ?? []))
      .catch(() => {
        // sans parties : pas d'onglets
      });
    return () => {
      alive = false;
    };
  }, [eventId]);
  return sections;
}

export function sectionDetails(section: EventSection): string {
  const parts: string[] = [];
  if (section.starts_at) {
    parts.push(
      new Date(section.starts_at).toLocaleString("fr-FR", {
        weekday: "short",
        day: "numeric",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
      })
    );
  }
  if (section.location) parts.push(section.location);
  return parts.join(" · ");
}

/** Onglets « Toutes » | Mairie | Reception... ; rien si l'evenement n'a pas de parties.
 * `counts` : nombre de photos par partie a afficher (sinon celui de la partie). */
export default function SectionTabs({
  sections,
  active,
  onChange,
  counts,
  allCount,
  tone = "light",
}: {
  sections: EventSection[];
  active: string | null;
  onChange: (sectionId: string | null) => void;
  counts?: Record<string, number>;
  allCount?: number;
  tone?: "light" | "dark";
}) {
  if (sections.length === 0) return null;
  const base = "shrink-0 rounded-full px-3.5 py-1.5 text-xs font-semibold transition whitespace-nowrap";
  const on = tone === "dark" ? "bg-white text-brand" : "bg-brand text-white";
  const off =
    tone === "dark" ? "bg-white/10 text-white hover:bg-white/20" : "border border-brand/15 bg-white/70 text-brand hover:bg-white";
  const visible = counts ? sections.filter((s) => (counts[s.id] ?? 0) > 0) : sections;
  if (counts && visible.length === 0) return null;

  return (
    <div role="tablist" aria-label="Parties de l'événement" className="flex gap-2 overflow-x-auto px-4 py-2 [scrollbar-width:none]">
      <button type="button" role="tab" aria-selected={active === null} onClick={() => onChange(null)} className={`${base} ${active === null ? on : off}`}>
        Toutes{allCount !== undefined ? ` · ${allCount}` : ""}
      </button>
      {visible.map((s) => {
        const n = counts ? counts[s.id] ?? 0 : s.photo_count;
        return (
          <button
            key={s.id}
            type="button"
            role="tab"
            aria-selected={active === s.id}
            onClick={() => onChange(s.id)}
            className={`${base} ${active === s.id ? on : off}`}
          >
            {s.name} · {n}
          </button>
        );
      })}
    </div>
  );
}
