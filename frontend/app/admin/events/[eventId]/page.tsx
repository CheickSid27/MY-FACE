"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import RequireAuth from "@/components/admin/RequireAuth";
import Pagination from "@/components/gallery/Pagination";
import BatchUploader from "@/components/upload/BatchUploader";
import { AlertIcon, CheckIcon, CrossIcon, PrinterIcon } from "@/components/icons";
import { api, ApiError } from "@/lib/api-client";
import type { Event, EventIndexingSummary, Photo, WatchedFolderRead } from "@/types/api";

const WATCHED_FOLDER_POLL_MS = 5000;
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
      <h2 className="mb-3 text-sm font-semibold text-ink-900">Informations de l&apos;evenement</h2>
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

  const [unitPrice, setUnitPrice] = useState(String(event.pricing.unit_price));
  const [printPrice, setPrintPrice] = useState(initialPrint);
  const [cashEnabled, setCashEnabled] = useState(event.cash_enabled);
  const [packs, setPacks] = useState<PackRow[]>(initialPacks);
  const [discounts, setDiscounts] = useState<DiscountRow[]>(initialDiscounts);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const dirty =
    unitPrice !== String(event.pricing.unit_price) ||
    printPrice !== initialPrint ||
    cashEnabled !== event.cash_enabled ||
    JSON.stringify(packs) !== JSON.stringify(initialPacks) ||
    JSON.stringify(discounts) !== JSON.stringify(initialDiscounts);

  const unit = Number(unitPrice);

  // Meme regles que le serveur (schemas/event.py), verifiees avant l'envoi
  // pour un message precis plutot qu'un refus generique.
  function validate(): string | null {
    if (!Number.isFinite(unit) || unit <= 0) return "Le prix par photo doit etre superieur a 0.";
    if (printPrice.trim() && (!Number.isFinite(Number(printPrice)) || Number(printPrice) < 0)) {
      return "Le prix d'impression est invalide.";
    }
    for (const p of packs) {
      const count = Number(p.count);
      if (!Number.isInteger(count) || count < 2) return "Un lot doit contenir au moins 2 photos.";
      if (!(Number(p.price) > 0)) return "Chaque lot doit avoir un prix superieur a 0.";
    }
    if (new Set(packs.map((p) => Number(p.count))).size !== packs.length) {
      return "Deux lots ne peuvent pas avoir le meme nombre de photos.";
    }
    for (const d of discounts) {
      const min = Number(d.min_quantity);
      const percent = Number(d.percent);
      if (!Number.isInteger(min) || min < 2) return "Une remise doit s'appliquer a partir de 2 photos au moins.";
      if (!(percent > 0 && percent < 100)) return "Le pourcentage de remise doit etre entre 1 et 99.";
    }
    if (new Set(discounts.map((d) => Number(d.min_quantity))).size !== discounts.length) {
      return "Deux remises ne peuvent pas avoir le meme seuil.";
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
          unit_price: unit,
          currency,
          print_unit_price: printPrice.trim() ? Number(printPrice) : null,
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
      <h2 className="mb-3 text-sm font-semibold text-ink-900">Tarifs et paiement en especes</h2>
      <div className="grid gap-3 sm:grid-cols-2">
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
            placeholder="Desactive"
            value={printPrice}
            onChange={(e) => setPrintPrice(e.target.value)}
            className={`${inputClass} mt-1`}
          />
        </label>
      </div>
      <p className="mt-1 text-xs text-ink-300">
        Laissez le prix d&apos;impression vide pour ne jamais proposer l&apos;impression papier sur
        la borne.
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
          <p className="text-xs text-ink-300">Aucune remise (ex : -15 % a partir de 20 photos).</p>
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
              <span>% a partir de</span>
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
        Accepter le paiement en especes (borne uniquement)
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

function CopyButton({ text }: { text: string }) {
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
      className="shrink-0 rounded-lg border border-ink-900/15 bg-white px-3 py-1.5 text-xs font-semibold text-ink-700 transition hover:bg-surface-alt"
    >
      {copied ? "Copie !" : "Copier"}
    </button>
  );
}

function ShareCard({ event }: { event: Event }) {
  const router = useRouter();
  const [showKiosk, setShowKiosk] = useState(false);
  const loadGuestQr = useCallback(() => api.getEventQrObjectUrl(event.id, "guest"), [event.id]);
  const loadKioskQr = useCallback(() => api.getEventQrObjectUrl(event.id, "kiosk"), [event.id]);
  const guestQr = useObjectUrl(loadGuestQr);
  const kioskQr = useObjectUrl(showKiosk ? loadKioskQr : null);
  // Liens construits sur APP_BASE_URL (backend .env) : s'il pointe encore
  // vers localhost, ni le QR ni le lien ne s'ouvriront sur un telephone.
  const isLocalUrl = /\/\/(localhost|127\.0\.0\.1)(:|\/|$)/.test(event.guest_url);

  return (
    <div className="glass mb-6 rounded-2xl p-5">
      <h2 className="mb-1 text-sm font-semibold text-ink-900">Partager avec les invites</h2>
      <p className="mb-4 text-xs text-ink-500">
        Imprimez ce QR code (affiche sur place, table, carton) ou envoyez le lien : chaque invite
        retrouve ses photos sur son propre telephone.
      </p>

      {isLocalUrl && (
        <div className="mb-4 flex gap-2 rounded-xl bg-amber-50 p-3 text-xs text-amber-800">
          <AlertIcon className="mt-0.5 shrink-0" />
          <p>
            L&apos;adresse publique de l&apos;application est encore <strong>{new URL(event.guest_url).origin}</strong> :
            ce lien et ce QR ne fonctionneront pas sur le telephone des invites. Renseignez l&apos;URL
            publique (tunnel ou nom de domaine) dans <code>APP_BASE_URL</code> du fichier <code>.env</code>,
            puis redemarrez le backend.
          </p>
        </div>
      )}

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
        <div className="flex h-36 w-36 shrink-0 items-center justify-center rounded-xl bg-white p-2 shadow-soft">
          {guestQr ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={guestQr} alt="QR code du lien invite" className="h-full w-full" />
          ) : (
            <div className="skeleton h-full w-full rounded-lg" />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <p className="mb-1 text-xs font-medium text-ink-500">Lien invite</p>
          <div className="mb-3 flex items-center gap-2">
            <code className="min-w-0 flex-1 truncate rounded-lg bg-surface-alt px-3 py-2 text-xs text-ink-900">
              {event.guest_url}
            </code>
            <CopyButton text={event.guest_url} />
          </div>
          <button
            type="button"
            onClick={() => router.push(`/admin/events/${event.id}/poster`)}
            className="btn-accent flex items-center gap-2 !px-4 !py-2.5 text-sm"
          >
            <PrinterIcon /> Imprimer l&apos;affiche QR
          </button>
        </div>
      </div>

      <div className="mt-5 border-t border-ink-900/5 pt-4">
        <button
          type="button"
          onClick={() => setShowKiosk((v) => !v)}
          className="text-xs font-semibold text-brand hover:underline"
        >
          {showKiosk ? "Masquer le lien borne" : "Afficher le lien borne (appareil physique uniquement)"}
        </button>
        {showKiosk && (
          <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center">
            <div className="flex h-28 w-28 shrink-0 items-center justify-center rounded-xl bg-white p-2 shadow-soft">
              {kioskQr ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={kioskQr} alt="QR code du lien borne" className="h-full w-full" />
              ) : (
                <div className="skeleton h-full w-full rounded-lg" />
              )}
            </div>
            <div className="min-w-0 flex-1">
              <p className="mb-1 text-xs text-ink-500">
                A ouvrir uniquement sur la borne (active especes, impression et apercus sans
                filigrane) : ne le diffusez pas aux invites.
              </p>
              <div className="flex items-center gap-2">
                <code className="min-w-0 flex-1 truncate rounded-lg bg-surface-alt px-3 py-2 text-xs text-ink-900">
                  {event.kiosk_url}
                </code>
                <CopyButton text={event.kiosk_url} />
              </div>
            </div>
          </div>
        )}
      </div>
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
            {summary.done}/{total} photo(s) analysee(s) &middot; {summary.faces} visage(s) detecte(s)
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
          {summary.done} analysee(s)
        </span>
        {unfinished > 0 && (
          <span className="rounded-full bg-amber-100 px-2.5 py-0.5 font-semibold text-amber-700">
            {unfinished} en cours / en attente
          </span>
        )}
        {summary.failed > 0 && (
          <span className="rounded-full bg-red-100 px-2.5 py-0.5 font-semibold text-red-700">
            {summary.failed} en echec
          </span>
        )}
      </div>
      {(unfinished > 0 || summary.failed > 0) && (
        <p className="mt-2 text-xs text-ink-500">
          Une photo non analysee n&apos;apparait pas dans les resultats du scan facial ni dans
          les personnes detectees.
        </p>
      )}
      {message && <p className="mt-2 text-xs text-ink-700">{message}</p>}
    </div>
  );
}

const STATUS_BADGES: Record<string, { label: string; className: string }> = {
  pending: { label: "En attente", className: "bg-amber-400/90 text-brand" },
  processing: { label: "Analyse...", className: "bg-amber-400/90 text-brand" },
  failed: { label: "Echec", className: "bg-red-600/90 text-white" },
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
    } catch {
      setError("Impossible de charger l'evenement.");
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

  async function handleDelete() {
    if (!confirm("Supprimer definitivement cet evenement, toutes ses photos et ses fichiers ?")) return;
    try {
      await api.deleteEvent(eventId);
      router.push("/admin/events");
    } catch (err) {
      alert(errorText(err, "Impossible de supprimer cet evenement."));
    }
  }

  async function handleReindex() {
    await api.reindexEvent(eventId);
    setIndexing(await api.getEventIndexing(eventId));
  }

  const [deletingPhotoId, setDeletingPhotoId] = useState<string | null>(null);

  async function handleDeletePhoto(photo: Photo) {
    if (!confirm(`Supprimer definitivement "${photo.original_filename}" ?`)) return;
    setDeletingPhotoId(photo.id);
    try {
      await api.deletePhoto(photo.id);
      setPhotos((prev) => prev.filter((p) => p.id !== photo.id));
      setTotal((t) => t - 1);
    } catch (err) {
      alert(errorText(err, "Impossible de supprimer cette photo."));
    } finally {
      setDeletingPhotoId(null);
    }
  }

  if (error) return <p className="p-6 text-red-600">{error}</p>;
  if (!event) return <p className="p-6 text-ink-500">Chargement...</p>;

  const totalPages = Math.max(1, Math.ceil(total / PHOTOS_PAGE_SIZE));

  return (
    <main className="min-h-screen bg-gradient-to-b from-surface-alt to-surface p-6">
      <div className="mx-auto max-w-3xl">
        <button
          type="button"
          onClick={() => router.push("/admin/events")}
          className="mb-4 text-sm font-medium text-ink-500 transition hover:text-brand"
        >
          &larr; Retour aux evenements
        </button>

        <div className="glass mb-6 flex items-start justify-between rounded-2xl p-5">
          <div>
            <h1 className="text-xl font-bold text-ink-900">{event.name}</h1>
            <p className="text-sm text-ink-500">
              {new Date(event.date).toLocaleDateString("fr-FR")} &middot; {event.location}
            </p>
            <p className="mt-1 text-sm text-ink-500">
              Prix unitaire : {event.pricing.unit_price.toLocaleString("fr-FR")} {event.pricing.currency}
            </p>
          </div>
          <button
            type="button"
            onClick={handleDelete}
            className="text-sm font-medium text-red-600 transition hover:text-red-800"
          >
            Supprimer
          </button>
        </div>

        <div className="mb-6 flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => router.push(`/admin/events/${eventId}/clusters`)}
            className="btn-primary !px-4 !py-2.5 text-sm"
          >
            Voir les personnes detectees
          </button>
          <button
            type="button"
            onClick={() => router.push(`/admin/events/${eventId}/stats`)}
            className="btn-accent !px-4 !py-2.5 text-sm"
          >
            Statistiques
          </button>
          <button
            type="button"
            onClick={() => router.push(`/admin/events/${eventId}/payments`)}
            className="btn-ghost !px-4 !py-2.5 text-sm"
          >
            Paiements
          </button>
        </div>

        <ShareCard event={event} />
        <EventInfoEditor key={`info-${event.updated_at}`} event={event} onSaved={setEvent} />
        <FrameCaptionEditor key={`frame-${event.updated_at}`} event={event} onSaved={setEvent} />
        <PricingEditor key={`pricing-${event.updated_at}`} event={event} onSaved={setEvent} />

        <div className="mb-6">
          <BatchUploader eventId={eventId} onUploaded={loadData} />
        </div>

        {watchedFolder && (
          <div className="glass mb-6 rounded-2xl p-5">
            <h2 className="mb-1 text-sm font-semibold text-ink-900">Dossier surveille</h2>
            <p className="mb-3 text-xs text-ink-500">
              Deposez les photos (ex: depuis la carte SD de l&apos;appareil) dans ce dossier sur le
              PC : elles sont ajoutees automatiquement, sans passer par l&apos;upload manuel.
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
                        ? "Ajoutee"
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

        {indexing && <IndexingCard summary={indexing} onReindex={handleReindex} />}

        <h2 className="mb-3 text-lg font-semibold text-ink-900">Photos ({total})</h2>
        <div className="grid grid-cols-3 gap-2 sm:grid-cols-4 md:grid-cols-6">
          {photos.map((photo) => {
            const badge = STATUS_BADGES[photo.indexing_status];
            return (
              <div key={photo.id} className="group relative overflow-hidden rounded-lg shadow-soft">
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
                  className="absolute right-1 top-1 flex h-6 w-6 items-center justify-center rounded-full bg-black/60 text-xs text-white transition-colors duration-150 hover:bg-red-600 disabled:cursor-wait"
                >
                  <CrossIcon />
                </button>
              </div>
            );
          })}
        </div>
        {photos.length === 0 && <p className="text-ink-500">Aucune photo uploadee.</p>}
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
    </main>
  );
}

export default function AdminEventDetailPage() {
  return (
    <RequireAuth>
      <AdminEventDetailContent />
    </RequireAuth>
  );
}
