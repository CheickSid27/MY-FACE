"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import AuthCard, { authInputClass } from "@/components/auth/AuthCard";
import { useAuthStore } from "@/store/auth-store";

export default function AdminLoginPage() {
  const router = useRouter();
  const login = useAuthStore((s) => s.login);
  const isLoading = useAuthStore((s) => s.isLoading);
  const error = useAuthStore((s) => s.error);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const success = await login(email.trim(), password);
    if (success) {
      router.push("/admin/events");
    }
  }

  return (
    <AuthCard subtitle="Espace organisateur et photographe">
      <form onSubmit={handleSubmit}>
        <label className="mb-1 block text-sm font-medium text-ink-700">Email</label>
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="email"
          className={`${authInputClass} mb-4`}
        />

        <label className="mb-1 block text-sm font-medium text-ink-700">Mot de passe</label>
        <input
          type="password"
          required
          maxLength={128}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
          className={`${authInputClass} mb-2`}
        />
        <p className="mb-5 text-right text-xs">
          <Link href="/mot-de-passe-oublie" className="font-medium text-brand hover:underline">
            Mot de passe oublié ?
          </Link>
        </p>

        {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

        <button type="submit" disabled={isLoading} className="btn-primary w-full">
          {isLoading ? "Connexion..." : "Se connecter"}
        </button>
        <p className="mt-5 text-center text-sm text-ink-500">
          Photographe, pas encore de compte ?{" "}
          <Link href="/photographes/inscription" className="font-semibold text-brand hover:underline">
            Créer mon compte gratuitement
          </Link>
        </p>
      </form>
    </AuthCard>
  );
}
