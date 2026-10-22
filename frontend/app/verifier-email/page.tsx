"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import AuthCard from "@/components/auth/AuthCard";
import { api, ApiError } from "@/lib/api-client";
import { isAuthenticated } from "@/lib/auth";

/** Lien de confirmation recu par e-mail apres l'inscription d'un photographe.
 * Fonctionne sans etre connecte (lien ouvert sur un autre appareil). */
function VerifierEmail() {
  const token = useSearchParams().get("token");
  const [state, setState] = useState<"loading" | "ok" | "error">("loading");
  const [message, setMessage] = useState<string | null>(null);
  const [email, setEmail] = useState<string | null>(null);
  const done = useRef(false);

  useEffect(() => {
    // une seule fois (le mode strict de React lance les effets deux fois)
    if (done.current) return;
    done.current = true;
    if (!token) {
      setState("error");
      setMessage("Ce lien est incomplet : ouvrez-le directement depuis l'e-mail reçu.");
      return;
    }
    api
      .verifyEmail(token)
      .then((res) => {
        setEmail(res.email);
        setState("ok");
      })
      .catch((err) => {
        setState("error");
        setMessage(err instanceof ApiError ? err.message : "Vérification impossible, réessayez.");
      });
  }, [token]);

  const loggedIn = typeof window !== "undefined" && isAuthenticated();

  return (
    <AuthCard subtitle="Confirmation de l'adresse e-mail">
      {state === "loading" && <p className="text-sm text-ink-700">Vérification du lien...</p>}

      {state === "ok" && (
        <>
          <p className="mb-2 text-lg font-semibold text-ink-900">Adresse confirmée</p>
          <p className="mb-6 text-sm text-ink-700">
            {email ? `${email} est confirmée.` : "Votre adresse est confirmée."} Vous pouvez maintenant créer vos
            événements et envoyer vos photos.
          </p>
          <Link href={loggedIn ? "/admin" : "/admin/login"} className="btn-primary block w-full text-center">
            {loggedIn ? "Aller à mon espace" : "Se connecter"}
          </Link>
        </>
      )}

      {state === "error" && (
        <>
          <p className="mb-2 text-lg font-semibold text-ink-900">Lien non valable</p>
          <p className="mb-6 text-sm text-ink-700">{message}</p>
          <p className="text-sm text-ink-500">
            Connectez-vous : un bandeau en haut de votre espace permet de recevoir un nouveau lien.
          </p>
          <Link href="/admin/login" className="btn-primary mt-4 block w-full text-center">
            Se connecter
          </Link>
        </>
      )}
    </AuthCard>
  );
}

export default function VerifierEmailPage() {
  return (
    <Suspense>
      <VerifierEmail />
    </Suspense>
  );
}
