"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import AuthCard, { authInputClass } from "@/components/auth/AuthCard";
import PhoneInput from "@/components/payments/PhoneInput";
import { api, ApiError } from "@/lib/api-client";
import { PASSWORD_HINT, passwordProblem } from "@/lib/password";
import { useAuthStore } from "@/store/auth-store";

/** Inscription libre d'un photographe : compte cree et connecte tout de
 * suite, chaque evenement demarre au pack Decouverte (10 photos gratuites).
 * Un e-mail de confirmation part aussitot : tant que l'adresse n'est pas
 * confirmee, l'espace photographe affiche un bandeau et bloque la creation
 * d'evenements. */
export default function InscriptionPhotographePage() {
  const router = useRouter();
  const [displayName, setDisplayName] = useState("");
  const [studioName, setStudioName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState<string | null>(null);
  const [city, setCity] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [acceptTerms, setAcceptTerms] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (displayName.trim().length < 2) {
      setError("Indiquez votre nom et prénom.");
      return;
    }
    if (!phone) {
      setError("Indiquez un numéro de téléphone valide (WhatsApp).");
      return;
    }
    const problem = passwordProblem(password, confirmation);
    if (problem) {
      setError(problem);
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
      // la session est ouverte : l'espace photographe charge le profil et
      // affiche le bandeau « confirmez votre adresse »
      useAuthStore.setState({ isLoggedIn: true });
      router.push("/admin/confirmation");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Inscription impossible, réessayez.");
      setSending(false);
    }
  }

  return (
    <AuthCard subtitle="Créer mon compte photographe" wide>
      <form onSubmit={handleSubmit}>
        <p className="mb-5 rounded-xl bg-brand-accent/10 px-3 py-2 text-xs text-ink-700">
          Gratuit pour commencer : 10 photos par événement. Packs Événement (10 000 F) et Pro (25 000 F) quand vous
          voulez, paiement unique par événement.
        </p>

        <label className="mb-1 block text-sm font-medium text-ink-700">Nom et prénom</label>
        <input required minLength={2} maxLength={120} value={displayName} onChange={(e) => setDisplayName(e.target.value)} autoComplete="name" className={`${authInputClass} mb-3`} />

        <label className="mb-1 block text-sm font-medium text-ink-700">Nom du studio (facultatif)</label>
        <input maxLength={120} value={studioName} onChange={(e) => setStudioName(e.target.value)} placeholder="Affiché aux invités et dans votre filigrane" className={`${authInputClass} mb-3`} />

        <label className="mb-1 block text-sm font-medium text-ink-700">Email</label>
        <input type="email" required maxLength={255} value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" className={`${authInputClass} mb-1`} />
        <p className="mb-3 text-xs text-ink-500">Un lien de confirmation y sera envoyé.</p>

        <label className="mb-1 block text-sm font-medium text-ink-700">Téléphone (WhatsApp)</label>
        <PhoneInput onChange={setPhone} disabled={sending} className="mb-3" />

        <label className="mb-1 block text-sm font-medium text-ink-700">Ville</label>
        <input maxLength={120} value={city} onChange={(e) => setCity(e.target.value)} placeholder="Abidjan" autoComplete="address-level2" className={`${authInputClass} mb-3`} />

        <label className="mb-1 block text-sm font-medium text-ink-700">Mot de passe</label>
        <input type="password" required minLength={8} maxLength={128} value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" className={`${authInputClass} mb-1`} />
        <p className="mb-3 text-xs text-ink-500">{PASSWORD_HINT}</p>

        <label className="mb-1 block text-sm font-medium text-ink-700">Confirmer le mot de passe</label>
        <input type="password" required maxLength={128} value={confirmation} onChange={(e) => setConfirmation(e.target.value)} autoComplete="new-password" className={`${authInputClass} mb-4`} />

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
    </AuthCard>
  );
}
