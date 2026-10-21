"use client";

import { FormEvent, Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import AuthCard, { authInputClass } from "@/components/auth/AuthCard";
import { api, ApiError } from "@/lib/api-client";
import { PASSWORD_HINT, passwordProblem } from "@/lib/password";

/** Lien recu par e-mail apres « mot de passe oublie » : choix du nouveau mot
 * de passe. Le lien ne sert qu'une fois et ferme les sessions ouvertes. */
function Reinitialiser() {
  const token = useSearchParams().get("token");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [sending, setSending] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const problem = passwordProblem(password, confirmation);
    if (problem) {
      setError(problem);
      return;
    }
    if (!token) {
      setError("Ce lien est incomplet : ouvrez-le directement depuis l'e-mail reçu.");
      return;
    }
    setError(null);
    setSending(true);
    try {
      await api.resetPassword(token, password);
      setDone(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Changement impossible, réessayez.");
    } finally {
      setSending(false);
    }
  }

  if (done) {
    return (
      <AuthCard subtitle="Nouveau mot de passe">
        <p className="mb-2 text-lg font-semibold text-ink-900">Mot de passe changé</p>
        <p className="mb-6 text-sm text-ink-700">
          Connectez-vous avec votre nouveau mot de passe. Les autres appareils connectés à votre compte ont été
          déconnectés.
        </p>
        <Link href="/admin/login" className="btn-primary block w-full text-center">
          Se connecter
        </Link>
      </AuthCard>
    );
  }

  return (
    <AuthCard subtitle="Nouveau mot de passe">
      <form onSubmit={handleSubmit}>
        <label className="mb-1 block text-sm font-medium text-ink-700">Nouveau mot de passe</label>
        <input
          type="password"
          required
          minLength={8}
          maxLength={128}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="new-password"
          className={`${authInputClass} mb-1`}
        />
        <p className="mb-3 text-xs text-ink-500">{PASSWORD_HINT}</p>
        <label className="mb-1 block text-sm font-medium text-ink-700">Confirmer le mot de passe</label>
        <input
          type="password"
          required
          maxLength={128}
          value={confirmation}
          onChange={(e) => setConfirmation(e.target.value)}
          autoComplete="new-password"
          className={`${authInputClass} mb-4`}
        />
        {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
        <button type="submit" disabled={sending} className="btn-primary w-full disabled:opacity-50">
          {sending ? "Enregistrement..." : "Changer le mot de passe"}
        </button>
        <p className="mt-5 text-center text-sm text-ink-500">
          Lien expiré ?{" "}
          <Link href="/mot-de-passe-oublie" className="font-semibold text-brand hover:underline">
            En demander un nouveau
          </Link>
        </p>
      </form>
    </AuthCard>
  );
}

export default function ReinitialiserMotDePassePage() {
  return (
    <Suspense>
      <Reinitialiser />
    </Suspense>
  );
}
