"use client";

import { ChangeEvent, FormEvent, useEffect, useRef, useState } from "react";
import Link from "next/link";
import RequireAuth from "@/components/admin/RequireAuth";
import InstallAppButton from "@/components/pro/InstallAppButton";
import PayoutCard from "@/components/pro/PayoutCard";
import UserAvatar from "@/components/pro/UserAvatar";
import PageHeader from "@/components/pro/PageHeader";
import {
  BellIcon,
  CalendarIcon,
  CameraIcon,
  ChatIcon,
  ChevronRightIcon,
  LockIcon,
  LogoutIcon,
  ReceiptIcon,
  SettingsIcon,
  ShieldIcon,
  UsersIcon,
} from "@/components/pro/icons";
import { CheckIcon } from "@/components/icons";
import { api, ApiError } from "@/lib/api-client";
import { PASSWORD_HINT, PASSWORD_MIN_LENGTH, passwordProblem } from "@/lib/password";
import { useAuthStore } from "@/store/auth-store";

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
    setError(null);
    setDone(false);
    if (displayName.trim().length < 2) {
      setError("Indiquez votre nom et prénom (2 caractères minimum).");
      return;
    }
    setSaving(true);
    try {
      const updated = await api.updateMe({
        display_name: displayName.trim(),
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
      <input value={displayName} onChange={(e) => setDisplayName(e.target.value)} required minLength={2} maxLength={120} autoComplete="name" className={`${inputClass} mb-3`} />
      <label className="mb-1 block text-sm font-medium text-ink-700">Nom du studio (facultatif)</label>
      <input value={studioName} onChange={(e) => setStudioName(e.target.value)} maxLength={120} className={`${inputClass} mb-3`} />
      <label className="mb-1 block text-sm font-medium text-ink-700">Téléphone (WhatsApp)</label>
      <input type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} maxLength={32} placeholder="07 01 02 03 04 ou +225 07..." autoComplete="tel" className={`${inputClass} mb-3`} />
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

/** Photo de profil : toucher la photo pour la changer, « Retirer » pour
 * revenir aux initiales. Le serveur la recadre en carre. */
function AvatarEditor() {
  const user = useAuthStore((s) => s.user);
  const setUser = useAuthStore((s) => s.setUser);
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  if (!user) return null;
  const name = user.studio_name || user.display_name || user.email;

  async function onFile(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    if (file.size > 8 * 1024 * 1024) {
      setError("Photo trop lourde (8 Mo maximum).");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      setUser(await api.uploadAvatar(file));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Envoi impossible, réessayez.");
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    setBusy(true);
    try {
      setUser(await api.deleteAvatar());
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex shrink-0 flex-col items-center gap-1">
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={busy}
        aria-label="Changer la photo de profil"
        className="relative rounded-[18px] disabled:opacity-60"
      >
        <UserAvatar userId={user.id} version={user.avatar_version} name={name} size={64} />
        <span className="absolute -bottom-1 -right-1 flex h-6 w-6 items-center justify-center rounded-full border-2 border-white bg-brand-accent text-brand">
          <CameraIcon size={13} />
        </span>
      </button>
      <input ref={inputRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={onFile} />
      {user.avatar_version && (
        <button type="button" onClick={remove} disabled={busy} className="text-[11px] font-semibold text-ink-500 hover:underline">
          Retirer
        </button>
      )}
      {busy && <span className="text-[11px] text-ink-500">Envoi...</span>}
      {error && <span className="max-w-[90px] text-center text-[11px] text-red-600">{error}</span>}
    </div>
  );
}

function AccountContent() {
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
    const problem = passwordProblem(next, confirmation);
    if (problem) {
      setError(problem);
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

  const logout = useAuthStore((s) => s.logout);
  const isAdmin = user?.role === "admin";
  const name = user?.studio_name || user?.display_name || user?.email || "";
  const row =
    "flex min-h-[52px] items-center gap-3 px-4 py-2.5 text-[15px] transition hover:bg-[#FBF8F3]";
  const ic = "flex h-9 w-9 shrink-0 items-center justify-center rounded-[11px] bg-[#F1EBE1] text-ink-900";

  return (
    <>
      <PageHeader title="Compte" />
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:items-start">
        <div className="flex flex-col gap-4">
          <section className="flex items-center gap-4 rounded-3xl border border-[#E6DED0] bg-white p-4">
            {user && <AvatarEditor />}
            <div className="min-w-0 flex-1">
              <b className="block truncate text-base">{name}</b>
              <span className="block truncate text-[13px] text-ink-500">{user?.email}</span>
              <span className="mt-1 inline-block rounded-lg bg-[#E3EAEB] px-2 py-0.5 text-[11px] font-bold">
                {isAdmin ? "Équipe MYFACE" : user?.must_verify_email ? "Adresse à confirmer" : "Photographe"}
              </span>
            </div>
          </section>

          {!isAdmin && <PayoutCard />}

          <section>
            <h2 className="mb-2 text-[13px] font-bold uppercase tracking-wider text-ink-500">Mon activité</h2>
            <div className="divide-y divide-[#EFE8DC] overflow-hidden rounded-3xl border border-[#E6DED0] bg-white">
              <Link href="/admin/events" className={row}>
                <span className={ic}><CalendarIcon size={18} /></span>
                <span className="flex-1">Mes événements</span>
                <ChevronRightIcon size={18} className="text-ink-500" />
              </Link>
              <Link href="/admin/ventes" className={row}>
                <span className={ic}><ReceiptIcon size={18} /></span>
                <span className="flex-1">Ventes</span>
                <ChevronRightIcon size={18} className="text-ink-500" />
              </Link>
              <Link href="/admin/notifications" className={row}>
                <span className={ic}><BellIcon size={18} /></span>
                <span className="flex-1">Notifications</span>
                <ChevronRightIcon size={18} className="text-ink-500" />
              </Link>
              <a href="#securite" className={row}>
                <span className={ic}><LockIcon size={18} /></span>
                <span className="flex-1">Mot de passe et sécurité</span>
                <ChevronRightIcon size={18} className="text-ink-500" />
              </a>
            </div>
          </section>

          {isAdmin && (
            <section>
              <h2 className="mb-2 text-[13px] font-bold uppercase tracking-wider text-ink-500">Espace MYFACE · équipe</h2>
              <div className="divide-y divide-[#EFE8DC] overflow-hidden rounded-3xl border border-[#E6DED0] bg-white">
                <Link href="/admin/packs" className={row}>
                  <span className={`${ic} !bg-[#FDE7D9] !text-[#9A3F06]`}><ShieldIcon size={18} /></span>
                  <span className="flex-1">Packs à valider</span>
                  <ChevronRightIcon size={18} className="text-ink-500" />
                </Link>
                <Link href="/admin/users" className={row}>
                  <span className={ic}><UsersIcon size={18} /></span>
                  <span className="flex-1">Photographes et comptes</span>
                  <ChevronRightIcon size={18} className="text-ink-500" />
                </Link>
                <Link href="/admin/settings" className={row}>
                  <span className={ic}><SettingsIcon size={18} /></span>
                  <span className="flex-1">Réglages de MYFACE et conservation des données</span>
                  <ChevronRightIcon size={18} className="text-ink-500" />
                </Link>
              </div>
            </section>
          )}

          <div className="flex flex-col gap-2">
            <InstallAppButton />
            <a
              href="https://wa.me/2250758509403"
              target="_blank"
              rel="noreferrer"
              className="flex min-h-[48px] items-center justify-center gap-2 rounded-2xl border border-[#D9CFBF] bg-white text-sm font-bold"
            >
              <ChatIcon size={18} /> Aide sur WhatsApp
            </a>
            <button type="button" onClick={logout} className="flex min-h-[48px] items-center justify-center gap-2 text-sm font-semibold text-ink-500">
              <LogoutIcon size={18} /> Se déconnecter
            </button>
          </div>
        </div>

        <div className="flex flex-col">
          <div id="profil">
            <ProfileForm />
          </div>

          <form id="securite" onSubmit={handleSubmit} className="glass rounded-2xl p-5">
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
              minLength={PASSWORD_MIN_LENGTH}
              maxLength={128}
              autoComplete="new-password"
              value={next}
              onChange={(e) => setNext(e.target.value)}
              className={`${inputClass} mb-1`}
            />
            <p className="mb-3 text-xs text-ink-500">{PASSWORD_HINT}</p>

            <label className="mb-1 block text-sm font-medium text-ink-700">Confirmer le nouveau mot de passe</label>
            <input
              type="password"
              required
              minLength={PASSWORD_MIN_LENGTH}
              maxLength={128}
              autoComplete="new-password"
              value={confirmation}
              onChange={(e) => setConfirmation(e.target.value)}
              className={`${inputClass} mb-4`}
            />

            {error && <p className="mb-3 text-sm text-red-600">{error}</p>}
            {done && (
              <p className="mb-3 flex items-center gap-1.5 text-sm text-emerald-700">
                <CheckIcon /> Mot de passe modifié. Vos autres appareils ont été déconnectés.
              </p>
            )}

            <button type="submit" disabled={saving} className="btn-primary w-full !py-3 text-sm">
              {saving ? "Enregistrement..." : "Changer le mot de passe"}
            </button>
          </form>
        </div>
      </div>
    </>
  );
}

export default function AccountPage() {
  return (
    <RequireAuth>
      <AccountContent />
    </RequireAuth>
  );
}
