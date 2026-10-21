"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import RequireAuth from "@/components/admin/RequireAuth";
import { CheckIcon } from "@/components/icons";
import { api, ApiError } from "@/lib/api-client";
import { useAuthStore } from "@/store/auth-store";

const MIN_PASSWORD_LENGTH = 8;

const inputClass =
  "w-full rounded-xl border border-ink-900/10 bg-white/70 px-3.5 py-2.5 outline-none transition focus:border-brand-accent focus:ring-2 focus:ring-brand-accent/20";

function ProfileForm() {
  const user = useAuthStore((s) => s.user);
  const setUser = useAuthStore((s) => s.setUser);
  const [displayName, setDisplayName] = useState(user?.display_name ?? "");
  const [studioName, setStudioName] = useState(user?.studio_name ?? "");
  const [phone, setPhone] = useState(user?.phone ?? "");
  const [city, setCity] = useState(user?.city ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  useEffect(() => {
    setDisplayName(user?.display_name ?? "");
    setStudioName(user?.studio_name ?? "");
    setPhone(user?.phone ?? "");
    setCity(user?.city ?? "");
  }, [user]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setDone(false);
    try {
      const updated = await api.updateMe({
        ...(displayName.trim().length >= 2 ? { display_name: displayName.trim() } : {}),
        studio_name: studioName.trim() || null,
        phone: phone.trim() || null,
        city: city.trim() || null,
      });
      setUser(updated);
      setDone(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Enregistrement impossible.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="glass mb-6 rounded-2xl p-5">
      <h2 className="mb-1 text-sm font-semibold text-ink-900">Mon profil</h2>
      <p className="mb-4 text-xs text-ink-500">
        Le nom du studio s&apos;affiche aux invités sur la page de vos événements, et dans le filigrane des packs
        Événement et Pro.
      </p>
      <label className="mb-1 block text-sm font-medium text-ink-700">Nom et prénom</label>
      <input value={displayName} onChange={(e) => setDisplayName(e.target.value)} maxLength={120} className={`${inputClass} mb-3`} />
      <label className="mb-1 block text-sm font-medium text-ink-700">Nom du studio (facultatif)</label>
      <input value={studioName} onChange={(e) => setStudioName(e.target.value)} maxLength={120} className={`${inputClass} mb-3`} />
      <label className="mb-1 block text-sm font-medium text-ink-700">Téléphone (WhatsApp, format +225...)</label>
      <input value={phone} onChange={(e) => setPhone(e.target.value)} maxLength={32} className={`${inputClass} mb-3`} />
      <label className="mb-1 block text-sm font-medium text-ink-700">Ville</label>
      <input value={city} onChange={(e) => setCity(e.target.value)} maxLength={120} className={`${inputClass} mb-4`} />
      {error && <p className="mb-3 text-sm text-red-600">{error}</p>}
      {done && (
        <p className="mb-3 flex items-center gap-1.5 text-sm text-emerald-700">
          <CheckIcon /> Profil enregistré.
        </p>
      )}
      <button type="submit" disabled={saving} className="btn-accent w-full !py-3 text-sm">
        {saving ? "Enregistrement..." : "Enregistrer mon profil"}
      </button>
    </form>
  );
}

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

        <ProfileForm />

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
