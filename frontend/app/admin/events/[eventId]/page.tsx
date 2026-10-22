"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import RequireAuth from "@/components/admin/RequireAuth";
import Pagination from "@/components/gallery/Pagination";
import EventRetentionCard from "@/components/admin/EventRetentionCard";
import GalleryOptionsCard from "@/components/packs/GalleryOptionsCard";
import PackCard from "@/components/packs/PackCard";
import BatchUploader from "@/components/upload/BatchUploader";
import PageHeader from "@/components/pro/PageHeader";
import { useWorkspace } from "@/components/pro/WorkspaceProvider";
import EventFacesPanel from "@/components/pro/event/EventFacesPanel";
import EventPaymentsPanel from "@/components/pro/event/EventPaymentsPanel";
import EventStatsPanel from "@/components/pro/event/EventStatsPanel";
import { useAuthStore } from "@/store/auth-store";
import { AlertIcon, CheckIcon, CrossIcon, PrinterIcon } from "@/components/icons";
import { api, ApiError } from "@/lib/api-client";
import type { Event, EventIndexingSummary, EventPack, Photo, WatchedFolderRead } from "@/types/api";

const WATCHED_FOLDER_POLL_MS = 5000;

// Onglets de l'evenement (prototype MYFACE Pro), gardes dans l'adresse
// (?onglet=...) pour les liens de l'accueil et des notifications.
type Tab = "photos" | "visages" | "ventes" | "reglages";
const TABS: { id: Tab; label: string }[] = [
  { id: "photos", label: "Photos" },
  { id: "visages", label: "Visages" },
  { id: "ventes", label: "Ventes" },
  { id: "reglages", label: "Réglages" },
];
const PHOTOS_PAGE_SIZE = 60;

const inputClass =
  "w-full rounded-xl border border-ink-900/10 bg-white/70 px-3.5 py-2.5 text-sm text-ink-900 outline-none transition focus:border-brand-accent focus:ring-2 focus:ring-brand-accent/20";

function errorText(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.message : fallback;
}

/** ISO (UTC) -> valeur d'un <input type="datetime-local"> en heure locale. */
function toLocalInputValue(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function EventInfoEditor({ event, onSaved }: { event: Event; onSaved: (event: Event) => void }) {
  const [name, setName] = useState(event.name);
  const [date, setDate] = useState(toLocalInputValue(event.date));
  const [location, setLocation] = useState(event.location);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const dirty =
    name !== event.name || date !== toLocalInputValue(event.date) || location !== event.location;

  async function handleSave() {
    if (!name.trim() || !location.trim() || !date) {
      setError("Nom, date et lieu sont obligatoires.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const updated = await api.updateEvent(event.id, {
        name: name.trim(),
        date: new Date(date).toISOString(),
        location: location.trim(),
      });
      onSaved(updated);
    } catch (err) {
      setError(errorText(err, "Impossible d'enregistrer."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="glass mb-6 rounded-2xl p-5">
      <h2 className="mb-3 text-sm font-semibold text-ink-900">Informations de l&apos;événement</h2>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="text-xs font-medium text-ink-500 sm:col-span-2">
          Nom
          <input value={name} maxLength={255} onChange={(e) => setName(e.target.value)} className={`${inputClass} mt-1`} />
        </label>
        <label className="text-xs font-medium text-ink-500">
          Date
          <input
            type="datetime-local"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className={`${inputClass} mt-1`}
          />
        </label>
        <label className="text-xs font-medium text-ink-500">
          Lieu
          <input
            value={location}
            maxLength={255}
            onChange={(e) => setLocation(e.target.value)}
            className={`${inputClass} mt-1`}
          />
        </label>
      </div>
      <div className="mt-3">
        <button
          type="button"
          disabled={!dirty || saving}
          onClick={handleSave}
          className="btn-primary !px-5 !py-2.5 text-sm disabled:opacity-40"
        >
          {saving ? "Enregistrement..." : "Enregistrer"}
        </button>
      </div>
      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
    </div>
  );
}

function FrameCaptionEditor({ event, onSaved }: { event: Event; onSaved: (event: Event) => void }) {
  const [value, setValue] = useState(event.frame_caption ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dirty = value !== (event.frame_caption ?? "");

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const updated = await api.updateEvent(event.id, { frame_caption: value.trim() || null });
      onSaved(updated);
    } catch (err) {
      setError(errorText(err, "Impossible d'enregistrer."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="glass mb-6 rounded-2xl p-5">
      <h2 className="mb-1 text-sm font-semibold text-ink-900">Cadre decoratif (borne + visionneuse)</h2>
      <p className="mb-3 text-xs text-ink-500">
        Texte affiche sous la photo dans un cadre style photobooth, ex : &laquo; LE FABULEUX MARIAGE
        D&apos;ANTHONY &amp; SOPHIA &raquo;. Laissez vide pour ne pas afficher de cadre.
      </p>
      <div className="flex flex-col gap-2 sm:flex-row">
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Ex : Le fabuleux mariage d'Anthony & Sophia"
          maxLength={255}
          className={`${inputClass} flex-1`}
        />
        <button
          type="button"
          disabled={!dirty || saving}
          onClick={handleSave}
          className="btn-primary !px-5 !py-2.5 text-sm disabled:opacity-40"
        >
          {saving ? "Enregistrement..." : "Enregistrer"}
        </button>
      </div>
      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
    </div>
  );
}

interface PackRow {
  count: string;
  price: string;
}

interface DiscountRow {
  min_quantity: string;
  percent: string;
}

function PricingEditor({ event, onSaved }: { event: Event; onSaved: (event: Event) => void }) {
  const currency = event.pricing.currency;
  const initialPacks: PackRow[] = (event.pricing.packs ?? []).map((p) => ({
    count: String(p.count),
    price: String(p.price),
  }));
  const initialDiscounts: DiscountRow[] = (event.pricing.discounts ?? []).map((d) => ({
    min_quantity: String(d.min_quantity),
    percent: String(d.percent),
  }));
  const initialPrint = event.pricing.print_unit_price != null ? String(event.pricing.print_unit_price) : "";
  const initialBundle = event.pricing.print_bundle_price != null ? String(event.pricing.print_bundle_price) : "";

  const [unitPrice, setUnitPrice] = useState(String(event.pricing.unit_price));
  const [printPrice, setPrintPrice] = useState(initialPrint);
  const [bundlePrice, setBundlePrice] = useState(initialBundle);
  const [offert, setOffert] = useState(Boolean(event.pricing.offert));
  const [cashEnabled, setCashEnabled] = useState(event.cash_enabled);
  const [packs, setPacks] = useState<PackRow[]>(initialPacks);
  const [discounts, setDiscounts] = useState<DiscountRow[]>(initialDiscounts);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const dirty =
    unitPrice !== String(event.pricing.unit_price) ||
    printPrice !== initialPrint ||
    bundlePrice !== initialBundle ||
    offert !== Boolean(event.pricing.offert) ||
    cashEnabled !== event.cash_enabled ||
    JSON.stringify(packs) !== JSON.stringify(initialPacks) ||
    JSON.stringify(discounts) !== JSON.stringify(initialDiscounts);

  const unit = Number(unitPrice);

  // Meme regles que le serveur (schemas/event.py), verifiees avant l'envoi
  // pour un message precis plutot qu'un refus generique.
  function validate(): string | null {
    if (!offert && (!Number.isFinite(unit) || unit <= 0)) return "Le prix par photo doit être supérieur à 0.";
    if (printPrice.trim() && (!Number.isFinite(Number(printPrice)) || Number(printPrice) < 0)) {
      return "Le prix d'impression est invalide.";
    }
    if (bundlePrice.trim() && (!Number.isFinite(Number(bundlePrice)) || Number(bundlePrice) < 0)) {
      return "Le prix photo + tirage est invalide.";
    }
    for (const p of packs) {
      const count = Number(p.count);
      if (!Number.isInteger(count) || count < 2) return "Un lot doit contenir au moins 2 photos.";
      if (!(Number(p.price) > 0)) return "Chaque lot doit avoir un prix supérieur à 0.";
    }
    if (new Set(packs.map((p) => Number(p.count))).size !== packs.length) {
      return "Deux lots ne peuvent pas avoir le même nombre de photos.";
    }
    for (const d of discounts) {
      const min = Number(d.min_quantity);
      const percent = Number(d.percent);
      if (!Number.isInteger(min) || min < 2) return "Une remise doit s'appliquer à partir de 2 photos au moins.";
      if (!(percent > 0 && percent < 100)) return "Le pourcentage de remise doit être entre 1 et 99.";
    }
    if (new Set(discounts.map((d) => Number(d.min_quantity))).size !== discounts.length) {
      return "Deux remises ne peuvent pas avoir le même seuil.";
    }
    return null;
  }

  async function handleSave() {
    const invalid = validate();
    if (invalid) {
      setError(invalid);
      return;
    }
    setSaving(true);
    setError(null);
    try {
      // La grille est toujours envoyee complete (prix, lots, remises) : le
      // serveur la remplace en entier. Avant, seuls prix et impression
      // etaient envoyes, ce qui effacait les lots et remises existants.
      const updated = await api.updateEvent(event.id, {
        pricing: {
          unit_price: offert ? (Number.isFinite(unit) && unit > 0 ? unit : 0) : unit,
          offert,
          currency,
          print_unit_price: printPrice.trim() ? Number(printPrice) : null,
          print_bundle_price: bundlePrice.trim() ? Number(bundlePrice) : null,
          packs: packs.map((p) => ({ count: Number(p.count), price: Number(p.price) })),
          discounts: discounts.map((d) => ({ min_quantity: Number(d.min_quantity), percent: Number(d.percent) })),
        },
        cash_enabled: cashEnabled,
      });
      onSaved(updated);
    } catch (err) {
      setError(errorText(err, "Impossible d'enregistrer."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="glass mb-6 rounded-2xl p-5">
      <h2 className="mb-3 text-sm font-semibold text-ink-900">Tarifs et paiement en espèces</h2>
      <label className="mb-4 flex items-start gap-3 rounded-xl border border-ink-900/10 bg-white/60 px-3.5 py-3 text-sm text-ink-700">
        <input
          type="checkbox"
          checked={offert}
          onChange={(e) => setOffert(e.target.checked)}
          className="mt-0.5 h-4 w-4 accent-brand-accent"
        />
        <span>
          <span className="font-medium text-ink-900">Photos offertes par l&apos;organisateur</span>
          <br />
          Les invités téléchargent leurs photos sans payer. Les prix ci-dessous ne s&apos;appliquent pas.
        </span>
      </label>
      <div className={`grid gap-3 sm:grid-cols-2 ${offert ? "opacity-50" : ""}`}>
        <label className="text-xs font-medium text-ink-500">
          Prix par photo ({currency})
          <input
            type="number"
            min={1}
            value={unitPrice}
            onChange={(e) => setUnitPrice(e.target.value)}
            className={`${inputClass} mt-1`}
          />
        </label>
        <label className="text-xs font-medium text-ink-500">
          Prix d&apos;impression par photo ({currency})
          <input
            type="number"
            min={0}
            placeholder="Désactivé"
            value={printPrice}
            onChange={(e) => setPrintPrice(e.target.value)}
            className={`${inputClass} mt-1`}
          />
        </label>
        <label className="text-xs font-medium text-ink-500">
          Prix photo + tirage, à la borne ({currency})
          <input
            type="number"
            min={0}
            placeholder="Ex : 700"
            value={bundlePrice}
            onChange={(e) => setBundlePrice(e.target.value)}
            className={`${inputClass} mt-1`}
          />
        </label>
      </div>
      <p className="mt-1 text-xs text-ink-300">
        Laissez les deux prix d&apos;impression vides pour ne jamais proposer le tirage papier sur
        la borne. Le prix photo + tirage remplace le prix photo + impression pour chaque photo
        imprimée ; ces photos ne comptent pas dans les lots ni dans les remises.
      </p>

      <div className="mt-5">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-500">Lots a prix fixe</h3>
          <button
            type="button"
            onClick={() => setPacks((rows) => [...rows, { count: "", price: "" }])}
            className="text-xs font-semibold text-brand hover:underline"
          >
            + Ajouter un lot
          </button>
        </div>
        {packs.length === 0 && <p className="text-xs text-ink-300">Aucun lot (ex : 10 photos pour 8 000 {currency}).</p>}
        <div className="flex flex-col gap-2">
          {packs.map((pack, i) => {
            const count = Number(pack.count);
            const price = Number(pack.price);
            const saving_ = count > 0 && price > 0 && unit > 0 ? count * unit - price : 0;
            return (
              <div key={i} className="flex flex-wrap items-center gap-2 text-sm text-ink-700">
                <input
                  type="number"
                  min={2}
                  value={pack.count}
                  onChange={(e) => setPacks((rows) => rows.map((r, j) => (j === i ? { ...r, count: e.target.value } : r)))}
                  className={`${inputClass} !w-24`}
                  aria-label="Nombre de photos du lot"
                />
                <span>photos pour</span>
                <input
                  type="number"
                  min={1}
                  value={pack.price}
                  onChange={(e) => setPacks((rows) => rows.map((r, j) => (j === i ? { ...r, price: e.target.value } : r)))}
                  className={`${inputClass} !w-32`}
                  aria-label="Prix du lot"
                />
                <span>{currency}</span>
                {saving_ > 0 && (
                  <span className="text-xs text-emerald-600">
                    (-{saving_.toLocaleString("fr-FR")} {currency} vs prix unitaire)
                  </span>
                )}
                <button
                  type="button"
                  onClick={() => setPacks((rows) => rows.filter((_, j) => j !== i))}
                  aria-label="Retirer ce lot"
                  className="ml-auto text-ink-300 transition hover:text-red-600"
                >
                  <CrossIcon />
                </button>
              </div>
            );
          })}
        </div>
      </div>

      <div className="mt-5">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-500">Remises de volume</h3>
          <button
            type="button"
            onClick={() => setDiscounts((rows) => [...rows, { min_quantity: "", percent: "" }])}
            className="text-xs font-semibold text-brand hover:underline"
          >
            + Ajouter une remise
          </button>
        </div>
        {discounts.length === 0 && (
          <p className="text-xs text-ink-300">Aucune remise (ex : -15 % à partir de 20 photos).</p>
        )}
        <div className="flex flex-col gap-2">
          {discounts.map((discount, i) => (
            <div key={i} className="flex flex-wrap items-center gap-2 text-sm text-ink-700">
              <span>-</span>
              <input
                type="number"
                min={1}
                max={99}
                value={discount.percent}
                onChange={(e) =>
                  setDiscounts((rows) => rows.map((r, j) => (j === i ? { ...r, percent: e.target.value } : r)))
                }
                className={`${inputClass} !w-20`}
                aria-label="Pourcentage de remise"
              />
              <span>% à partir de</span>
              <input
                type="number"
                min={2}
                value={discount.min_quantity}
                onChange={(e) =>
                  setDiscounts((rows) => rows.map((r, j) => (j === i ? { ...r, min_quantity: e.target.value } : r)))
                }
                className={`${inputClass} !w-24`}
                aria-label="Nombre minimum de photos"
              />
              <span>photos</span>
              <button
                type="button"
                onClick={() => setDiscounts((rows) => rows.filter((_, j) => j !== i))}
                aria-label="Retirer cette remise"
                className="ml-auto text-ink-300 transition hover:text-red-600"
              >
                <CrossIcon />
              </button>
            </div>
          ))}
        </div>
        <p className="mt-2 text-xs text-ink-300">
          Les lots s&apos;appliquent d&apos;abord (du plus grand au plus petit), puis la meilleure
          remise de volume sur le sous-total.
        </p>
      </div>

      <label className="mt-5 flex items-center gap-2 text-sm text-ink-700">
        <input
          type="checkbox"
          checked={cashEnabled}
          onChange={(e) => setCashEnabled(e.target.checked)}
          className="h-4 w-4 rounded border-ink-900/20 text-brand-accent focus:ring-brand-accent/40"
        />
        Accepter le paiement en espèces (borne uniquement)
      </label>
      <div className="mt-3">
        <button
          type="button"
          disabled={!dirty || saving}
          onClick={handleSave}
          className="btn-primary !px-5 !py-2.5 text-sm disabled:opacity-40"
        >
          {saving ? "Enregistrement..." : "Enregistrer"}
        </button>
      </div>
      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
    </div>
  );
}

function useObjectUrl(load: (() => Promise<string>) | null): string | null {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!load) return;
    let created: string | null = null;
    let cancelled = false;
    load()
      .then((u) => {
        created = u;
        if (!cancelled) setUrl(u);
      })
      .catch(() => {
        // QR indisponible : le lien texte reste utilisable
      });
    return () => {
      cancelled = true;
      if (created) URL.revokeObjectURL(created);
    };
  }, [load]);
  return url;
}

function CopyButton({ text, dark = false }: { text: string; dark?: boolean }) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      window.prompt("Copiez le lien :", text);
    }
  }
  return (
    <button
      type="button"
      onClick={copy}
      className={
        dark
          ? "flex min-h-[42px] items-center justify-center rounded-xl border border-white/30 px-4 text-[13px] font-semibold text-[#F4EFE6]"
          : "shrink-0 rounded-lg border border-ink-900/15 bg-white px-3 py-1.5 text-xs font-semibold text-ink-700 transition hover:bg-surface-alt"
      }
    >
      {copied ? "Lien copié" : dark ? "Copier le lien" : "Copier"}
    </button>
  );
}

/** Haut de l'evenement : QR code et lien des invites, affiche a imprimer. */
function EventHero({ event, pack }: { event: Event; pack: EventPack | null }) {
  const loadGuestQr = useCallback(() => api.getEventQrObjectUrl(event.id, "guest"), [event.id]);
  const guestQr = useObjectUrl(loadGuestQr);
  // Liens construits sur APP_BASE_URL (backend .env) : s'il pointe encore
  // vers localhost, ni le QR ni le lien ne s'ouvriront sur un telephone.
  const isLocalUrl = /\/\/(localhost|127\.0\.0\.1)(:|\/|$)/.test(event.guest_url);
  const used = pack && pack.photo_limit ? Math.min(100, Math.round((pack.photo_count / pack.photo_limit) * 100)) : null;

  return (
    <section className="mb-5 flex flex-col gap-4 rounded-3xl bg-brand p-4 text-[#F4EFE6] sm:flex-row sm:items-center sm:p-5">
      <div className="flex items-center gap-4 sm:contents">
        <div className="flex h-24 w-24 shrink-0 items-center justify-center rounded-2xl bg-white p-2 sm:h-28 sm:w-28">
          {guestQr ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={guestQr} alt="QR code des invités" className="h-full w-full" />
          ) : (
            <div className="h-full w-full animate-pulse rounded-lg bg-ink-900/10" />
          )}
        </div>
        <div className="min-w-0 flex-1 sm:hidden">
          <p className="text-[13px] text-[#A9BABD]">Les invités scannent ce code pour retrouver leurs photos.</p>
        </div>
      </div>
      <div className="flex min-w-0 flex-1 flex-col gap-3">
        <p className="hidden text-[13px] text-[#A9BABD] sm:block">
          Les invités scannent ce code ou ouvrent le lien pour retrouver leurs photos.
        </p>
        {isLocalUrl && (
          <p className="rounded-xl bg-amber-50 p-2.5 text-xs text-amber-900">
            L&apos;adresse publique de l&apos;application n&apos;est pas configurée (APP_BASE_URL) : ce lien ne marche
            pas sur un téléphone.
          </p>
        )}
        <div className="grid grid-cols-2 gap-2 sm:flex sm:flex-wrap">
          <Link
            href={`/admin/events/${event.id}/poster`}
            className="flex min-h-[42px] items-center justify-center gap-2 rounded-xl bg-brand-accent px-4 text-[13px] font-bold text-brand"
          >
            <PrinterIcon /> Affiche QR
          </Link>
          <CopyButton text={event.guest_url} dark />
          <a
            href={event.guest_url}
            target="_blank"
            rel="noreferrer"
            className="col-span-2 flex min-h-[42px] items-center justify-center rounded-xl border border-white/30 px-4 text-[13px] font-semibold sm:col-span-1"
          >
            Voir la page invités
          </a>
        </div>
        {pack && (
          <div className="flex flex-col gap-1.5">
            <div className="flex justify-between text-[12px] text-[#A9BABD]">
              <span>Pack {pack.pack.name}</span>
              <span>
                {pack.photo_count.toLocaleString("fr-FR")}
                {pack.photo_limit ? ` / ${pack.photo_limit.toLocaleString("fr-FR")}` : ""} photo
                {(pack.photo_limit ?? pack.photo_count) > 1 ? "s" : ""}
              </span>
            </div>
            {used !== null && (
              <div className="h-1.5 overflow-hidden rounded bg-white/15">
                <div className="h-full rounded bg-brand-accent" style={{ width: `${used}%` }} />
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}

/** Lien de la borne (appareil physique de l'evenement) : dans Reglages. */
function KioskCard({ event }: { event: Event }) {
  const [show, setShow] = useState(false);
  const loadKioskQr = useCallback(() => api.getEventQrObjectUrl(event.id, "kiosk"), [event.id]);
  const kioskQr = useObjectUrl(show ? loadKioskQr : null);
  return (
    <div className="glass mb-6 rounded-2xl p-5">
      <h2 className="mb-1 text-sm font-semibold text-ink-900">Borne de l&apos;événement</h2>
      <p className="mb-3 text-xs text-ink-500">
        À ouvrir uniquement sur la borne (espèces, impression, aperçus sans filigrane) : ne le diffusez pas aux
        invités.
      </p>
      <button type="button" onClick={() => setShow((v) => !v)} className="text-xs font-semibold text-brand hover:underline">
        {show ? "Masquer le lien borne" : "Afficher le lien borne"}
      </button>
      {show && (
        <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="flex h-28 w-28 shrink-0 items-center justify-center rounded-xl bg-white p-2 shadow-soft">
            {kioskQr ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={kioskQr} alt="QR code du lien borne" className="h-full w-full" />
            ) : (
              <div className="skeleton h-full w-full rounded-lg" />
            )}
          </div>
          <div className="flex min-w-0 flex-1 items-center gap-2">
            <code className="min-w-0 flex-1 truncate rounded-lg bg-surface-alt px-3 py-2 text-xs text-ink-900">
              {event.kiosk_url}
            </code>
            <CopyButton text={event.kiosk_url} />
          </div>
        </div>
      )}
    </div>
  );
}

function IndexingCard({
  summary,
  onReindex,
}: {
  summary: EventIndexingSummary;
  onReindex: () => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const unfinished = summary.pending + summary.processing;
  const toRetry = unfinished + summary.failed;
  const total = unfinished + summary.failed + summary.done;

  async function handleReindex() {
    setBusy(true);
    setMessage(null);
    try {
      await onReindex();
      setMessage("Indexation relancee.");
    } catch (err) {
      setMessage(errorText(err, "Impossible de relancer l'indexation."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="glass mb-6 rounded-2xl p-5">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-ink-900">Reconnaissance faciale</h2>
          <p className="text-xs text-ink-500">
            {summary.done}/{total} photo(s) analysée(s) &middot; {summary.faces} visage(s) détecté(s)
          </p>
        </div>
        {toRetry > 0 && (
          <button
            type="button"
            disabled={busy}
            onClick={handleReindex}
            className="btn-primary !px-4 !py-2 text-xs disabled:opacity-50"
          >
            {busy ? "..." : `Relancer l'indexation (${toRetry})`}
          </button>
        )}
      </div>
      <div className="flex flex-wrap gap-2 text-xs">
        <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 font-semibold text-emerald-700">
          {summary.done} analysée(s)
        </span>
        {unfinished > 0 && (
          <span className="rounded-full bg-amber-100 px-2.5 py-0.5 font-semibold text-amber-700">
            {unfinished} en cours / en attente
          </span>
        )}
        {summary.failed > 0 && (
          <span className="rounded-full bg-red-100 px-2.5 py-0.5 font-semibold text-red-700">
            {summary.failed} en échec
          </span>
        )}
      </div>
      {(unfinished > 0 || summary.failed > 0) && (
        <p className="mt-2 text-xs text-ink-500">
          Une photo non analysée n&apos;apparaît pas dans les résultats du scan facial ni dans
          les personnes détectées.
        </p>
      )}
      {message && <p className="mt-2 text-xs text-ink-700">{message}</p>}
    </div>
  );
}

const STATUS_BADGES: Record<string, { label: string; className: string }> = {
  pending: { label: "En attente", className: "bg-amber-400/90 text-brand" },
  processing: { label: "Analyse...", className: "bg-amber-400/90 text-brand" },
  failed: { label: "Échec", className: "bg-red-600/90 text-white" },
};

function AdminEventDetailContent() {
  const { eventId } = useParams<{ eventId: string }>();
  const router = useRouter();
  const [event, setEvent] = useState<Event | null>(null);
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [watchedFolder, setWatchedFolder] = useState<WatchedFolderRead | null>(null);
  const [indexing, setIndexing] = useState<EventIndexingSummary | null>(null);
  // Service photographe : pack de l'evenement (limite de photos, options)
  const user = useAuthStore((s) => s.user);
  const isAdmin = user?.role === "admin";
  const [eventPack, setEventPack] = useState<EventPack | null>(null);
  const [packRefresh, setPackRefresh] = useState(0);
  const { refresh: refreshWorkspace } = useWorkspace();
  const [tab, setTab] = useState<Tab>("photos");
  const uploaderRef = useRef<HTMLDivElement | null>(null);
  const [scrollToUploader, setScrollToUploader] = useState(false);

  // Onglet demande par l'adresse ; retour de Paystack (?paystack=) : le
  // volet Reglages contient le pack, qui verifie le paiement.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const wanted = params.get("onglet");
    if (params.get("paystack")) setTab("reglages");
    else if (wanted && TABS.some((x) => x.id === wanted)) setTab(wanted as Tab);
    if (params.get("ajout")) setScrollToUploader(true);
  }, []);

  function selectTab(next: Tab) {
    setTab(next);
    const params = new URLSearchParams(window.location.search);
    params.set("onglet", next);
    params.delete("ajout");
    window.history.replaceState(null, "", `${window.location.pathname}?${params.toString()}`);
  }

  const loadPhotos = useCallback(
    async (pageToLoad: number) => {
      const data = await api.listPhotos(eventId, pageToLoad, PHOTOS_PAGE_SIZE);
      setPhotos(data.items);
      setTotal(data.total);
      setPage(pageToLoad);
    },
    [eventId]
  );

  const pageRef = useRef(page);
  pageRef.current = page;

  const loadData = useCallback(async () => {
    try {
      const [eventData] = await Promise.all([api.getEvent(eventId), loadPhotos(pageRef.current)]);
      setEvent(eventData);
      setPackRefresh((n) => n + 1);
    } catch {
      setError("Impossible de charger l'événement.");
    }
  }, [eventId, loadPhotos]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Dossier surveille + etat de l'indexation : rafraichis periodiquement pour
  // que l'organisateur voie en direct les photos deposees depuis la carte SD
  // se faire ingerer puis analyser, sans recharger la page. Quand l'etat de
  // l'indexation change, la page de photos courante est rechargee (badges).
  const indexingKeyRef = useRef<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    function poll() {
      api
        .getWatchedFolder(eventId)
        .then((data) => {
          if (!cancelled) setWatchedFolder(data);
        })
        .catch(() => {
          // dossier surveille indisponible (ex: pas encore configure) : silencieux
        });
      api
        .getEventIndexing(eventId)
        .then((summary) => {
          if (cancelled) return;
          setIndexing(summary);
          const key = JSON.stringify(summary);
          if (indexingKeyRef.current !== null && indexingKeyRef.current !== key) {
            loadPhotos(pageRef.current).catch(() => {});
          }
          indexingKeyRef.current = key;
        })
        .catch(() => {});
    }
    poll();
    const interval = setInterval(poll, WATCHED_FOLDER_POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [eventId, loadPhotos]);

  useEffect(() => {
    if (scrollToUploader && tab === "photos" && event && uploaderRef.current) {
      uploaderRef.current.scrollIntoView({ behavior: "smooth", block: "center" });
      setScrollToUploader(false);
    }
  }, [scrollToUploader, tab, event]);

  async function handleDelete() {
    if (!confirm("Supprimer définitivement cet événement, toutes ses photos et ses fichiers ?")) return;
    try {
      await api.deleteEvent(eventId);
      router.push("/admin/events");
    } catch (err) {
      alert(errorText(err, "Impossible de supprimer cet événement."));
    }
  }

  async function handleReindex() {
    await api.reindexEvent(eventId);
    setIndexing(await api.getEventIndexing(eventId));
  }

  const [deletingPhotoId, setDeletingPhotoId] = useState<string | null>(null);

  async function handleDeletePhoto(photo: Photo) {
    if (!confirm(`Supprimer définitivement "${photo.original_filename}" ?`)) return;
    setDeletingPhotoId(photo.id);
    try {
      await api.deletePhoto(photo.id);
      setPhotos((prev) => prev.filter((p) => p.id !== photo.id));
      setTotal((t) => t - 1);
      setPackRefresh((n) => n + 1);
    } catch (err) {
      alert(errorText(err, "Impossible de supprimer cette photo."));
    } finally {
      setDeletingPhotoId(null);
    }
  }

  if (error) return <p className="p-2 text-red-600">{error}</p>;
  if (!event)
    return (
      <div className="flex flex-col gap-4">
        <div className="skeleton h-12 w-2/3 rounded-xl" />
        <div className="skeleton h-40 rounded-3xl" />
      </div>
    );

  const totalPages = Math.max(1, Math.ceil(total / PHOTOS_PAGE_SIZE));
  const priceLine = event.pricing.offert
    ? "Photos offertes"
    : `${event.pricing.unit_price.toLocaleString("fr-FR")} ${event.pricing.currency} la photo`;

  return (
    <>
      <PageHeader
        title={event.name}
        subtitle={`${new Date(event.date).toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" })} · ${event.location} · ${priceLine}`}
        back="/admin/events"
      />

      <EventHero event={event} pack={eventPack} />

      <div
        className="sticky top-2 z-20 mb-5 flex gap-1 rounded-2xl bg-[#EAE3D6] p-1 shadow-[0_4px_14px_rgba(14,36,41,0.06)] lg:max-w-xl"
        role="tablist"
        aria-label="Volets de l'événement"
      >
        {TABS.map((x) => (
          <button
            key={x.id}
            type="button"
            role="tab"
            aria-selected={tab === x.id}
            onClick={() => selectTab(x.id)}
            className={`min-h-[42px] flex-1 rounded-xl text-[13px] font-semibold transition sm:text-sm ${
              tab === x.id ? "bg-white text-ink-900 shadow-[0_2px_8px_rgba(14,36,41,0.1)]" : "text-ink-500"
            }`}
          >
            {x.label}
          </button>
        ))}
      </div>

      {tab === "photos" && (
        <div className="lg:grid lg:grid-cols-[minmax(0,360px)_minmax(0,1fr)] lg:items-start lg:gap-6">
          <div className="lg:sticky lg:top-20">
            <div ref={uploaderRef} className="mb-5">
              <BatchUploader
                eventId={eventId}
                onUploaded={() => {
                  loadData();
                  refreshWorkspace();
                }}
                remaining={eventPack && !eventPack.unlimited ? eventPack.remaining : null}
              />
            </div>
            {indexing && <IndexingCard summary={indexing} onReindex={handleReindex} />}
            {watchedFolder && (
              <div className="glass mb-6 rounded-2xl p-5">
                <h2 className="mb-1 text-sm font-semibold text-ink-900">Dossier surveillé</h2>
                <p className="mb-3 text-xs text-ink-500">
                  Déposez les photos (ex : depuis la carte SD de l&apos;appareil) dans ce dossier sur le PC : elles sont
                  ajoutées automatiquement.
                </p>
                <code className="mb-3 block break-all rounded-lg bg-surface-alt px-3 py-2 text-xs text-ink-900">
                  {watchedFolder.folder_path}
                </code>
                {watchedFolder.files.length > 0 && (
                  <ul className="flex flex-col gap-1.5">
                    {watchedFolder.files.map((f) => (
                      <li key={f.filename} className="flex items-center justify-between gap-3 text-xs">
                        <span className="truncate text-ink-700">{f.filename}</span>
                        <span
                          className={`shrink-0 rounded-full px-2 py-0.5 font-medium ${
                            f.status === "ingested"
                              ? "bg-emerald-100 text-emerald-700"
                              : f.status === "error"
                                ? "bg-red-100 text-red-700"
                                : "bg-amber-100 text-amber-700"
                          }`}
                        >
                          {f.status === "ingested"
                            ? "Ajoutée"
                            : f.status === "error"
                              ? `Erreur${f.detail ? ` : ${f.detail}` : ""}`
                              : "Copie en cours..."}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>

          <div>
            <div className="mb-3 flex items-baseline justify-between">
              <h2 className="font-pro text-[15px] font-semibold text-ink-900">
                {total.toLocaleString("fr-FR")} photo{total > 1 ? "s" : ""}
              </h2>
              <span className="text-[13px] text-ink-500">Les plus récentes</span>
            </div>
            <div className="grid grid-cols-3 gap-1.5 sm:grid-cols-4 xl:grid-cols-5">
              {photos.map((photo) => {
                const badge = STATUS_BADGES[photo.indexing_status];
                return (
                  <div key={photo.id} className="group relative overflow-hidden rounded-xl">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={photo.thumbnail_url}
                      alt={photo.original_filename}
                      loading="lazy"
                      className="aspect-square w-full object-cover"
                    />
                    {badge && (
                      <span
                        className={`absolute bottom-1 left-1 rounded-full px-1.5 py-0.5 text-[10px] font-bold ${badge.className}`}
                      >
                        {badge.label}
                      </span>
                    )}
                    {photo.indexing_status === "done" && (
                      <span className="absolute bottom-1 left-1 hidden rounded-full bg-emerald-600/90 px-1.5 py-0.5 text-[10px] font-bold text-white group-hover:flex">
                        <CheckIcon />
                      </span>
                    )}
                    <button
                      type="button"
                      onClick={() => handleDeletePhoto(photo)}
                      disabled={deletingPhotoId === photo.id}
                      aria-label={`Supprimer ${photo.original_filename}`}
                      className="absolute right-1 top-1 flex h-7 w-7 items-center justify-center rounded-full bg-black/55 text-xs text-white transition-colors duration-150 hover:bg-red-600 disabled:cursor-wait"
                    >
                      <CrossIcon />
                    </button>
                  </div>
                );
              })}
            </div>
            {photos.length === 0 && (
              <div className="rounded-3xl border border-dashed border-[#D9CFBF] bg-white p-6 text-center text-sm text-ink-500">
                Aucune photo pour le moment. Ajoutez-en avec le bouton d&apos;envoi.
              </div>
            )}
            {totalPages > 1 && (
              <div className="mt-4 flex justify-center">
                <Pagination
                  currentPage={page}
                  totalPages={totalPages}
                  onPageChange={(p) => {
                    loadPhotos(p).catch(() => setError("Impossible de charger les photos."));
                  }}
                />
              </div>
            )}
          </div>
        </div>
      )}

      {tab === "visages" && (
        <>
          {indexing && <IndexingCard summary={indexing} onReindex={handleReindex} />}
          <EventFacesPanel eventId={eventId} />
        </>
      )}

      {tab === "ventes" && (
        <>
          <EventStatsPanel eventId={eventId} />
          <EventPaymentsPanel eventId={eventId} />
        </>
      )}

      {/* Monte en permanence (masque hors Reglages) : le pack verifie le
          retour d'un paiement Paystack et alimente le haut de la page. */}
      <div className={tab === "reglages" ? "lg:grid lg:grid-cols-2 lg:items-start lg:gap-x-6" : "hidden"}>
        <div>
          <PackCard
            eventId={eventId}
            eventName={event.name}
            isAdmin={isAdmin}
            refreshKey={packRefresh}
            onLoaded={setEventPack}
          />
          <EventInfoEditor key={`info-${event.updated_at}`} event={event} onSaved={setEvent} />
          <PricingEditor key={`pricing-${event.updated_at}`} event={event} onSaved={setEvent} />
        </div>
        <div>
          {eventPack && (
            <GalleryOptionsCard
              key={`options-${event.updated_at}`}
              event={event}
              features={eventPack.features}
              studioName={user?.studio_name || user?.display_name || null}
              onSaved={setEvent}
            />
          )}
          <FrameCaptionEditor key={`frame-${event.updated_at}`} event={event} onSaved={setEvent} />
          <KioskCard event={event} />
          <EventRetentionCard event={event} isAdmin={isAdmin} onChanged={loadData} />
          <button
            type="button"
            onClick={handleDelete}
            className="mb-6 flex min-h-[48px] w-full items-center justify-center rounded-2xl border border-red-200 bg-white text-sm font-semibold text-red-700 transition hover:bg-red-50"
          >
            Supprimer l&apos;événement
          </button>
        </div>
      </div>
    </>
  );
}

export default function AdminEventDetailPage() {
  return (
    <RequireAuth>
      <AdminEventDetailContent />
    </RequireAuth>
  );
}
