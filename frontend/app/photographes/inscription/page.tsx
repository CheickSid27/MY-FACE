"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import MyfaceLogo from "@/components/brand/Logo";
import PhoneInput from "@/components/payments/PhoneInput";
import { api, ApiError } from "@/lib/api-client";
import { useAuthStore } from "@/store/auth-store";

const inputClass =
  "w-full rounded-xl border border-ink-900/10 bg-white/70 px-3.5 py-2.5 text-ink-900 outline-none transition focus:border-brand-accent focus:ring-2 focus:ring-brand-accent/20";

/** Inscription libre d'un photographe : compte cree et connecte tout de
 * suite, chaque evenement demarre au pack Decouverte (10 photos gratuites). */
export default function InscriptionPhotographePage() {
  const router = useRouter();
  const [displayName, setDisplayName] = useState("");
  const [studioName, setStudioName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState<string | null>(null);
  const [city, setCity] = useState("");
  const [password, setPassword] = useState("");
  const [acceptTerms, setAcceptTerms] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!phone) {
      setError("Indiquez un numéro de téléphone valide (WhatsApp).");
      return;
    }
    if (!acceptTerms) {
      setError("Acceptez les conditions d'utilisation pour créer votre compte.");
      return;
    }
    setSending(true);
    try {
      await api.register({
        email: email.trim(),
        password,
        display_name: displayName.trim(),
        studio_name: studioName.trim() || null,
        phone,
        city: city.trim() || null,
        accept_terms: acceptTerms,
      });
      // la session est ouverte : l'espace photographe charge le profil
      useAuthStore.setState({ isLoggedIn: true });
      router.push("/admin/events");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Inscription impossible, réessayez.");
      setSending(false);
    }
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-gradient-to-br from-brand to-brand-light px-4 py-10">
      <div
        className="pointer-events-none absolute inset-0 opacity-40"
        style={{
          background:
            "radial-gradient(circle at 20% 20%, rgba(201,161,90,0.25), transparent 45%), radial-gradient(circle at 80% 70%, rgba(201,161,90,0.15), transparent 40%)",
        }}
      />

      <form onSubmit={handleSubmit} className="glass-strong relative z-10 w-full max-w-md rounded-2xl p-7 animate-scale-in">
        <div className="mb-5 flex items-center gap-3">
          <MyfaceLogo size={44} />
          <div>
            <p className="text-lg font-bold leading-tight text-ink-900">
              MY<span className="text-[#F26A1B]">FACE</span>
            </p>
            <p className="text-xs text-ink-500">Créer mon compte photographe</p>
          </div>
        </div>
        <p className="mb-5 rounded-xl bg-brand-accent/10 px-3 py-2 text-xs text-ink-700">
          Gratuit pour commencer : 10 photos par événement. Packs Événement (10 000 F) et Pro (25 000 F) quand vous
          voulez, paiement unique par événement.
        </p>

        <label className="mb-1 block text-sm font-medium text-ink-700">Nom et prénom</label>
        <input required minLength={2} maxLength={120} value={displayName} onChange={(e) => setDisplayName(e.target.value)} autoComplete="name" className={`${inputClass} mb-3`} />

        <label className="mb-1 block text-sm font-medium text-ink-700">Nom du studio (facultatif)</label>
        <input maxLength={120} value={studioName} onChange={(e) => setStudioName(e.target.value)} placeholder="Affiché aux invités et dans votre filigrane" className={`${inputClass} mb-3`} />

        <label className="mb-1 block text-sm font-medium text-ink-700">Email</label>
        <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" className={`${inputClass} mb-3`} />

        <label className="mb-1 block text-sm font-medium text-ink-700">Téléphone (WhatsApp)</label>
        <PhoneInput onChange={setPhone} disabled={sending} className="mb-3" />

        <label className="mb-1 block text-sm font-medium text-ink-700">Ville</label>
        <input maxLength={120} value={city} onChange={(e) => setCity(e.target.value)} placeholder="Abidjan" className={`${inputClass} mb-3`} />

        <label className="mb-1 block text-sm font-medium text-ink-700">Mot de passe (8 caractères minimum)</label>
        <input type="password" required minLength={8} maxLength={128} value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" className={`${inputClass} mb-4`} />

        <label className="mb-4 flex items-start gap-3 text-sm text-ink-700">
          <input type="checkbox" checked={acceptTerms} onChange={(e) => setAcceptTerms(e.target.checked)} className="mt-0.5 h-4 w-4 accent-brand-accent" />
          <span>
            J&apos;accepte les{" "}
            <Link href="/conditions-photographes" target="_blank" className="font-semibold text-brand hover:underline">
              conditions d&apos;utilisation
            </Link>{" "}
            et je m&apos;engage à informer mes clients que leurs invités pourront retrouver leurs photos par
            reconnaissance faciale.
          </span>
        </label>

        {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

        <button type="submit" disabled={sending} className="btn-accent w-full !py-3 disabled:opacity-50">
          {sending ? "Création du compte..." : "Créer mon compte gratuitement"}
        </button>
        <p className="mt-4 text-center text-sm text-ink-500">
          Déjà un compte ?{" "}
          <Link href="/admin/login" className="font-semibold text-brand hover:underline">
            Se connecter
          </Link>
        </p>
      </form>
    </main>
  );
}
