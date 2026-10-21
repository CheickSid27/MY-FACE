"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import AuthCard, { authInputClass } from "@/components/auth/AuthCard";
import { api, ApiError } from "@/lib/api-client";

/** Demande d'un lien pour choisir un nouveau mot de passe. La reponse est la
 * meme que l'adresse ait un compte ou non (on ne revele pas qui est inscrit). */
export default function MotDePasseOubliePage() {
  const [email, setEmail] = useState("");
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSending(true);
    try {
      const res = await api.forgotPassword(email.trim());
      setSent(res.detail);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Envoi impossible, réessayez.");
    } finally {
      setSending(false);
    }
  }

  return (
    <AuthCard subtitle="Mot de passe oublié">
      {sent ? (
        <>
          <p className="mb-4 text-sm text-ink-700">{sent}</p>
          <p className="mb-6 text-xs text-ink-500">
            Le lien est valable une heure. Pensez à regarder dans les courriers indésirables.
          </p>
          <Link href="/admin/login" className="btn-primary block w-full text-center">
            Retour à la connexion
          </Link>
        </>
      ) : (
        <form onSubmit={handleSubmit}>
          <p className="mb-4 text-sm text-ink-700">
            Indiquez l&apos;adresse e-mail de votre compte : vous recevrez un lien pour choisir un nouveau mot de passe.
          </p>
          <label className="mb-1 block text-sm font-medium text-ink-700">Email</label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            className={`${authInputClass} mb-4`}
          />
          {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
          <button type="submit" disabled={sending} className="btn-primary w-full disabled:opacity-50">
            {sending ? "Envoi..." : "Recevoir le lien"}
          </button>
          <p className="mt-5 text-center text-sm text-ink-500">
            <Link href="/admin/login" className="font-semibold text-brand hover:underline">
              Retour à la connexion
            </Link>
          </p>
        </form>
      )}
    </AuthCard>
  );
}
