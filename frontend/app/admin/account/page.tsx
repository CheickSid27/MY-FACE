"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import RequireAuth from "@/components/admin/RequireAuth";
import { CheckIcon } from "@/components/icons";
import { api, ApiError } from "@/lib/api-client";
import { useAuthStore } from "@/store/auth-store";

const MIN_PASSWORD_LENGTH = 8;

const inputClass =
  "w-full rounded-xl border border-ink-900/10 bg-white/70 px-3.5 py-2.5 outline-none transition focus:border-brand-accent focus:ring-2 focus:ring-brand-accent/20";

function AccountContent() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setDone(false);
    if (next.length < MIN_PASSWORD_LENGTH) {
      setError(`Le nouveau mot de passe doit contenir au moins ${MIN_PASSWORD_LENGTH} caracteres.`);
      return;
    }
    if (next !== confirmation) {
      setError("La confirmation ne correspond pas au nouveau mot de passe.");
      return;
    }
    if (next === current) {
      setError("Le nouveau mot de passe doit être différent de l'actuel.");
      return;
    }
    setSaving(true);
    try {
      await api.changePassword(current, next);
      setCurrent("");
      setNext("");
      setConfirmation("");
      setDone(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Impossible de changer le mot de passe.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="min-h-screen bg-gradient-to-b from-surface-alt to-surface p-6">
      <div className="mx-auto max-w-md">
        <button
          type="button"
          onClick={() => router.push("/admin/events")}
          className="mb-4 text-sm font-medium text-ink-500 transition hover:text-brand"
        >
          &larr; Retour aux événements
        </button>

        <div className="glass mb-6 rounded-2xl p-5">
          <h1 className="text-xl font-bold text-ink-900">Mon compte</h1>
          {user && (
            <p className="mt-1 text-sm text-ink-500">
              {user.email} &middot; {user.role === "admin" ? "Administrateur" : "Photographe"}
            </p>
          )}
        </div>

        <form onSubmit={handleSubmit} className="glass rounded-2xl p-5">
          <h2 className="mb-4 text-sm font-semibold text-ink-900">Changer mon mot de passe</h2>

          <label className="mb-1 block text-sm font-medium text-ink-700">Mot de passe actuel</label>
          <input
            type="password"
            required
            autoComplete="current-password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            className={`${inputClass} mb-3`}
          />

          <label className="mb-1 block text-sm font-medium text-ink-700">Nouveau mot de passe</label>
          <input
            type="password"
            required
            minLength={MIN_PASSWORD_LENGTH}
            autoComplete="new-password"
            value={next}
            onChange={(e) => setNext(e.target.value)}
            className={`${inputClass} mb-3`}
          />

          <label className="mb-1 block text-sm font-medium text-ink-700">Confirmer le nouveau mot de passe</label>
          <input
            type="password"
            required
            minLength={MIN_PASSWORD_LENGTH}
            autoComplete="new-password"
            value={confirmation}
            onChange={(e) => setConfirmation(e.target.value)}
            className={`${inputClass} mb-4`}
          />

          {error && <p className="mb-3 text-sm text-red-600">{error}</p>}
          {done && (
            <p className="mb-3 flex items-center gap-1.5 text-sm text-emerald-700">
              <CheckIcon /> Mot de passe modifié.
            </p>
          )}

          <button type="submit" disabled={saving} className="btn-primary w-full !py-3 text-sm">
            {saving ? "Enregistrement..." : "Changer le mot de passe"}
          </button>
        </form>
      </div>
    </main>
  );
}

export default function AccountPage() {
  return (
    <RequireAuth>
      <AccountContent />
    </RequireAuth>
  );
}
