"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import MyfaceLogo from "@/components/brand/Logo";
import EventCodeForm from "@/components/event/EventCodeForm";
import { api, ApiError } from "@/lib/api-client";
import { formatEventCode, normalizeEventCode } from "@/lib/event-code";

/** Adresse courte d'un evenement (app.myfaceci.online/e/K7M2QX9P), celle
 * du QR code et du lien invites : ouvre la page d'accueil de l'evenement,
 * comme l'ancienne adresse longue. Code inconnu : on propose de le retaper. */
export default function EventCodePage() {
  const { code } = useParams<{ code: string }>();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const normalized = normalizeEventCode(decodeURIComponent(code));
    if (!normalized) {
      setError("Ce code n'est pas valide.");
      return;
    }
    api
      .findEventByCode(normalized)
      .then(({ id }) => router.replace(`/event/${id}${window.location.search}`))
      .catch((err) =>
        setError(
          err instanceof ApiError && err.status === 429
            ? "Trop d'essais. Réessayez dans quelques minutes."
            : err instanceof ApiError && err.status === 404
              ? "Aucun événement avec ce code. Vérifiez-le et réessayez."
              : "Connexion impossible. Réessayez dans un instant."
        )
      );
  }, [code, router]);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 bg-brand px-6 text-center text-white">
      <MyfaceLogo size={72} tone="light" />
      {!error ? (
        <p className="text-gray-300" aria-live="polite">
          Ouverture de l&apos;événement {formatEventCode(decodeURIComponent(code).toUpperCase())}...
        </p>
      ) : (
        <>
          <p className="max-w-sm text-gray-200">{error}</p>
          <EventCodeForm />
        </>
      )}
    </main>
  );
}
