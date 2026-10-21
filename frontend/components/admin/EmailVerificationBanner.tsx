"use client";

import { useState } from "react";
import { api, ApiError } from "@/lib/api-client";
import type { User } from "@/types/api";

/** Photographe dont l'adresse n'est pas encore confirmee : rappel en haut de
 * son espace, avec un bouton pour recevoir un nouveau lien. Le serveur
 * refuse la creation d'evenements et l'envoi de photos tant que ce n'est pas
 * fait (quand l'envoi d'e-mails est en place). */
export default function EmailVerificationBanner({ user }: { user: User }) {
  const [state, setState] = useState<"idle" | "sending" | "sent">("idle");
  const [error, setError] = useState<string | null>(null);

  if (!user.must_verify_email) return null;

  async function resend() {
    setState("sending");
    setError(null);
    try {
      await api.resendVerification();
      setState("sent");
    } catch (err) {
      setState("idle");
      setError(err instanceof ApiError ? err.message : "Envoi impossible, réessayez plus tard.");
    }
  }

  return (
    <div className="border-b border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
      <div className="mx-auto flex max-w-5xl flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <p>
          <span className="font-semibold">Confirmez votre adresse e-mail.</span> Un lien a été envoyé à{" "}
          <span className="font-medium">{user.email}</span> (pensez aux courriers indésirables). Sans cette
          confirmation, vous ne pouvez ni créer d&apos;événement ni envoyer de photos.
        </p>
        <div className="shrink-0">
          {state === "sent" ? (
            <span className="font-medium text-emerald-700">Nouveau lien envoyé</span>
          ) : (
            <button
              type="button"
              onClick={resend}
              disabled={state === "sending"}
              className="rounded-lg border border-amber-300 bg-white px-3 py-1.5 font-medium hover:bg-amber-100 disabled:opacity-50"
            >
              {state === "sending" ? "Envoi..." : "Renvoyer le lien"}
            </button>
          )}
          {error && <p className="mt-1 text-xs text-red-700">{error}</p>}
        </div>
      </div>
    </div>
  );
}
