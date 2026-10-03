"use client";

import { useEffect } from "react";
import { AlertIcon } from "@/components/icons";

// Filet de securite global : sans ce fichier, toute exception de rendu
// inattendue tombe sur l'overlay d'erreur brut de Next.js (tres verbeux en
// dev, generique en prod) au lieu d'un ecran de secours coherent avec le
// reste de l'app.
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-5 bg-gradient-to-br from-brand to-brand-light px-6 text-center text-white">
      <div className="glass-pill flex h-16 w-16 items-center justify-center text-3xl">
        <AlertIcon />
      </div>
      <h1 className="text-xl font-bold">Une erreur est survenue</h1>
      <p className="max-w-sm text-sm text-ink-300">
        Quelque chose s&apos;est mal passé de notre côté. Réessayez, et si le problème persiste,
        revenez à l&apos;accueil.
      </p>
      <div className="flex flex-col gap-3 sm:flex-row">
        <button type="button" onClick={reset} className="btn-accent">
          Réessayer
        </button>
        <button
          type="button"
          onClick={() => (window.location.href = "/")}
          className="btn-ghost !border-white/20 !bg-white/5 !text-white hover:!bg-white/10"
        >
          Retour à l&apos;accueil
        </button>
      </div>
    </main>
  );
}
