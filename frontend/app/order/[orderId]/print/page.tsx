"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { AlertIcon, PrinterIcon } from "@/components/icons";
import { api, ApiError } from "@/lib/api-client";
import { getKioskToken, isKioskMode } from "@/lib/kiosk";
import type { DownloadResponse } from "@/types/api";

type Orientation = "portrait" | "landscape";

// Page d'impression des tirages papier d'une commande payee (voir
// OrderItem.print_requested). Ouverte depuis la borne (bouton "Imprimer mes
// photos" de la page de telechargement) ou depuis l'admin (fiche commande,
// file "Tirages a imprimer") sur un PC relie a l'imprimante.
//
// window.print() envoie au pilote d'impression du systeme ; si Chrome est
// lance avec --kiosk-printing, l'impression part directement sur
// l'imprimante par defaut, sans boite de dialogue. Une photo par page, sans
// marge, dans l'orientation de la photo, jamais recadree (object-fit:
// contain : sur un papier au meme format que la photo, ex. 10x15 pour du
// 3:2, elle occupe toute la page ; sinon de fines bandes blanches plutot
// qu'une tete coupee).
export default function PrintOrderPage() {
  const { orderId } = useParams<{ orderId: string }>();
  const router = useRouter();
  const [data, setData] = useState<DownloadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [printing, setPrinting] = useState(false);
  const [orientations, setOrientations] = useState<Record<string, Orientation>>({});
  const [printedAt, setPrintedAt] = useState<string | null>(null);
  const [failedIds, setFailedIds] = useState<string[]>([]);
  const printRequestedRef = useRef(false);

  useEffect(() => {
    api
      .getDownload(orderId)
      .then((result) => {
        setData(result);
        setPrintedAt(result.printed_at);
      })
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : "Impossible de charger la commande.")
      );
  }, [orderId]);

  const printPhotos = data?.photos.filter((p) => p.print_requested) ?? [];
  // Originaux (jusqu'a 25 Mo) : lancer l'impression avant leur chargement
  // complet donnait des pages blanches. Le bouton attend qu'ils soient tous prets.
  const loadedCount = printPhotos.filter((p) => orientations[p.photo_id]).length;
  const allLoaded = printPhotos.length > 0 && loadedCount === printPhotos.length && failedIds.length === 0;

  useEffect(() => {
    function handleAfterPrint() {
      setPrinting(false);
      if (!printRequestedRef.current || !data) return;
      printRequestedRef.current = false;
      // Borne : autorisee par son jeton ; admin : par sa session.
      api
        .markOrderPrinted(orderId, getKioskToken(data.event_id))
        .then((res) => setPrintedAt(res.printed_at))
        .catch(() => {
          // enregistrement best-effort : l'impression elle-meme a eu lieu
        });
    }
    window.addEventListener("afterprint", handleAfterPrint);
    return () => window.removeEventListener("afterprint", handleAfterPrint);
  }, [data, orderId]);

  function handlePrint() {
    setPrinting(true);
    printRequestedRef.current = true;
    // Laisse le temps au navigateur de peindre l'etat "impression en
    // cours..." avant d'ouvrir le pilote d'impression (bloquant tant que la
    // boite de dialogue ou --kiosk-printing n'a pas rendu la main).
    window.setTimeout(() => window.print(), 150);
  }

  function handleBack() {
    if (data && isKioskMode(data.event_id)) {
      router.push(`/event/${data.event_id}/gallery`);
    } else if (window.history.length > 1) {
      router.back();
    } else {
      window.close();
    }
  }

  if (error) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-gradient-to-br from-brand to-brand-light px-6 text-center text-white print:hidden">
        <p className="text-lg">{error}</p>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-gradient-to-br from-brand to-brand-light text-white print:hidden">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-accent border-t-transparent" />
      </main>
    );
  }

  return (
    <>
      <style>{`
        @page { margin: 0; }
        @page photo-portrait { size: portrait; margin: 0; }
        @page photo-landscape { size: landscape; margin: 0; }
        @media print {
          html, body { margin: 0 !important; padding: 0 !important; background: #fff !important; }
          .print-sheet {
            width: 100vw;
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            break-after: page;
          }
          .print-sheet:last-child { break-after: auto; }
          .print-sheet.portrait { page: photo-portrait; }
          .print-sheet.landscape { page: photo-landscape; }
          .print-sheet img { width: 100%; height: 100%; object-fit: contain; }
        }
      `}</style>

      <main className="flex min-h-screen flex-col items-center gap-6 bg-gradient-to-b from-surface-alt to-surface px-6 py-12 text-center print:hidden">
        <div className="glass-pill flex h-16 w-16 items-center justify-center text-3xl">
          <PrinterIcon />
        </div>
        <div>
          <h1 className="text-xl font-bold text-brand">Impression papier</h1>
          <p className="mt-1 text-ink-500">
            {printPhotos.length} photo(s) a imprimer &middot; commande{" "}
            <span className="font-mono text-sm">{orderId.slice(0, 8)}</span>
          </p>
        </div>

        {failedIds.length > 0 && (
          <div className="flex max-w-sm items-start gap-2 rounded-xl bg-red-50 p-3 text-left text-sm text-red-700">
            <AlertIcon className="mt-0.5 shrink-0" />
            <p>
              {failedIds.length} photo(s) n&apos;ont pas pu etre chargees. Verifiez la connexion puis
              rechargez la page avant d&apos;imprimer.
            </p>
          </div>
        )}

        {printedAt && (
          <div className="flex max-w-sm items-start gap-2 rounded-xl bg-amber-50 p-3 text-left text-sm text-amber-800">
            <AlertIcon className="mt-0.5 shrink-0" />
            <p>
              Deja imprimees le {new Date(printedAt).toLocaleString("fr-FR")}. Relancez seulement
              si le premier tirage a echoue.
            </p>
          </div>
        )}

        <div className="grid w-full max-w-2xl grid-cols-3 gap-3 sm:grid-cols-4">
          {printPhotos.map((photo) => (
            <div key={photo.photo_id} className="glass overflow-hidden rounded-xl">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={photo.thumbnail_url}
                alt={photo.filename}
                className="aspect-square w-full object-cover"
              />
              <p className="truncate px-1.5 py-1 text-[10px] text-ink-500">{photo.filename}</p>
            </div>
          ))}
        </div>

        <button
          type="button"
          disabled={printing || !allLoaded}
          onClick={handlePrint}
          className="btn-accent w-full max-w-sm !py-4 text-base"
        >
          {printing
            ? "Envoi a l'imprimante..."
            : !allLoaded
              ? `Preparation des photos en qualite originale (${loadedCount}/${printPhotos.length})...`
              : printedAt
                ? "Reimprimer"
                : "Lancer l'impression"}
        </button>
        <button type="button" onClick={handleBack} className="btn-ghost w-full max-w-sm">
          Retour
        </button>
      </main>

      {/* Contenu reellement imprime (originaux, pleine qualite) : invisible a
          l'ecran, une photo par page dans son orientation. */}
      <div className="hidden print:block">
        {printPhotos.map((photo) => (
          <div key={photo.photo_id} className={`print-sheet ${orientations[photo.photo_id] ?? "portrait"}`}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={photo.url}
              alt={photo.filename}
              onLoad={(e) => {
                const img = e.currentTarget;
                const orientation: Orientation = img.naturalWidth > img.naturalHeight ? "landscape" : "portrait";
                setOrientations((prev) => ({ ...prev, [photo.photo_id]: orientation }));
              }}
              onError={() => setFailedIds((prev) => (prev.includes(photo.photo_id) ? prev : [...prev, photo.photo_id]))}
            />
          </div>
        ))}
      </div>
    </>
  );
}
