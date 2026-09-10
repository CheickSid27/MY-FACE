"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { PrinterIcon } from "@/components/icons";
import { api, ApiError } from "@/lib/api-client";
import type { DownloadResponse } from "@/types/api";

// Page d'impression physique des photos commandees sur la borne (voir
// OrderItem.print_requested). Aucune imprimante n'est encore branchee au
// moment ou ce code est ecrit, mais le flux est concu pour fonctionner tel
// quel des qu'une imprimante par defaut sera configuree sur le PC de la
// borne : window.print() envoie directement au pilote d'impression du
// systeme, et si Chrome est lance avec le flag --kiosk-printing, l'impression
// part automatiquement sur l'imprimante par defaut sans boite de dialogue.
// Une photo par page, plein cadre, sans marge (voir le <style> @page ci-dessous).
export default function PrintOrderPage() {
  const { orderId } = useParams<{ orderId: string }>();
  const router = useRouter();
  const [data, setData] = useState<DownloadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [printing, setPrinting] = useState(false);

  useEffect(() => {
    api
      .getDownload(orderId)
      .then(setData)
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : "Impossible de charger la commande.")
      );
  }, [orderId]);

  useEffect(() => {
    function handleAfterPrint() {
      setPrinting(false);
    }
    window.addEventListener("afterprint", handleAfterPrint);
    return () => window.removeEventListener("afterprint", handleAfterPrint);
  }, []);

  function handlePrint() {
    setPrinting(true);
    // Laisse le temps au navigateur de peindre l'etat "impression en
    // cours..." avant d'ouvrir le pilote d'impression (bloquant tant que la
    // boite de dialogue ou --kiosk-printing n'a pas rendu la main).
    window.setTimeout(() => window.print(), 150);
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

  const printPhotos = data.photos.filter((p) => p.print_requested);

  return (
    <>
      <style>{`
        @page { size: auto; margin: 0; }
        @media print {
          html, body { margin: 0; padding: 0; }
        }
      `}</style>

      <main className="flex min-h-screen flex-col items-center gap-6 bg-gradient-to-b from-surface-alt to-surface px-6 py-12 text-center print:hidden">
        <div className="glass-pill flex h-16 w-16 items-center justify-center text-3xl">
          <PrinterIcon />
        </div>
        <div>
          <h1 className="text-xl font-bold text-brand">Impression papier</h1>
          <p className="mt-1 text-ink-500">
            {printPhotos.length} photo(s) a imprimer sur l&apos;imprimante de la borne.
          </p>
        </div>

        <div className="grid w-full max-w-2xl grid-cols-3 gap-3 sm:grid-cols-4">
          {printPhotos.map((photo) => (
            <div key={photo.photo_id} className="glass overflow-hidden rounded-xl">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={photo.url}
                alt={photo.filename}
                className="aspect-square w-full object-cover"
              />
            </div>
          ))}
        </div>

        <button
          type="button"
          disabled={printing || printPhotos.length === 0}
          onClick={handlePrint}
          className="btn-accent w-full max-w-sm !py-4 text-base"
        >
          {printing ? "Envoi a l'imprimante..." : "Lancer l'impression"}
        </button>
        <button
          type="button"
          onClick={() => router.push(`/event/${data.event_id}/gallery`)}
          className="btn-ghost w-full max-w-sm"
        >
          Retour a la galerie
        </button>
      </main>

      {/* Contenu reellement imprime : invisible a l'ecran (voir screen:hidden
          plus bas), une photo plein cadre par page. */}
      <div className="hidden print:block">
        {printPhotos.map((photo) => (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            key={photo.photo_id}
            src={photo.url}
            alt={photo.filename}
            style={{
              width: "100vw",
              height: "100vh",
              objectFit: "cover",
              display: "block",
              pageBreakAfter: "always",
            }}
          />
        ))}
      </div>
    </>
  );
}
