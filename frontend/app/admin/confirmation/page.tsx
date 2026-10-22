"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import AuthCard from "@/components/auth/AuthCard";
import RequireAuth from "@/components/admin/RequireAuth";
import { api, ApiError } from "@/lib/api-client";
import { useAuthStore } from "@/store/auth-store";

// Delai pour confirmer l'adresse (serveur : UNVERIFIED_ACCOUNT_TTL_MINUTES) :
// au-dela, l'inscription est annulee et le compte supprime. Les comptes
// anciens (verification_deadline nul) sont gardes : pas de compte a rebours.
const CHECK_EVERY_MS = 4000;

function WaitingContent() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const setUser = useAuthStore((s) => s.setUser);
  const logout = useAuthStore((s) => s.logout);
  const [now, setNow] = useState(() => Date.now());
  const [sent, setSent] = useState<string | null>(null);
  const [cancelled, setCancelled] = useState(false);

  const deadline = user?.verification_deadline ? new Date(user.verification_deadline).getTime() : null;
  const left = deadline ? Math.max(0, Math.round((deadline - now) / 1000)) : null;

  // Le lien peut etre ouvert sur un autre appareil : on revérifie
  // regulierement, et on entre dans l'espace des que c'est confirme.
  const check = useCallback(async () => {
    try {
      const me = await api.me();
      setUser(me);
      if (!me.must_verify_email) router.replace("/admin");
    } catch (err) {
      if (err instanceof ApiError && (err.status === 401 || err.status === 404)) setCancelled(true);
    }
  }, [router, setUser]);

  useEffect(() => {
    const tick = setInterval(() => setNow(Date.now()), 1000);
    const poll = setInterval(check, CHECK_EVERY_MS);
    return () => {
      clearInterval(tick);
      clearInterval(poll);
    };
  }, [check]);

  useEffect(() => {
    if (left === 0) setCancelled(true);
  }, [left]);

  async function resend() {
    setSent(null);
    try {
      await api.resendVerification();
      setSent("Nouveau lien envoyé. Regardez aussi dans les courriers indésirables.");
    } catch (err) {
      setSent(err instanceof ApiError ? err.message : "Envoi impossible, réessayez dans un instant.");
    }
  }

  if (cancelled) {
    return (
      <AuthCard subtitle="Inscription annulée">
        <h1 className="mb-2 text-xl font-bold text-ink-900">Inscription annulée</h1>
        <p className="mb-5 text-sm text-ink-700">
          L&apos;adresse e-mail n&apos;a pas été confirmée à temps : l&apos;inscription a été annulée et rien n&apos;a été
          gardé. Vous pouvez recommencer, avec la même adresse.
        </p>
        <Link
          href="/photographes/inscription"
          onClick={() => logout()}
          className="btn-accent block w-full !py-3 text-center text-sm"
        >
          Recommencer l&apos;inscription
        </Link>
      </AuthCard>
    );
  }

  const minutes = left !== null ? Math.floor(left / 60) : 0;
  const seconds = left !== null ? left % 60 : 0;

  return (
    <AuthCard subtitle="Dernière étape" wide>
      <h1 className="mb-2 text-xl font-bold text-ink-900">Confirmez votre adresse e-mail</h1>
      <p className="mb-4 text-sm text-ink-700">
        Nous avons envoyé un lien à <strong>{user?.email}</strong>. Ouvrez-le pour accéder à votre espace : cette page
        s&apos;ouvrira toute seule.
      </p>
      {left !== null && (
      <div className="mb-4 rounded-2xl bg-white/70 p-4 text-center">
        <p className="text-xs uppercase tracking-wider text-ink-500">Temps restant</p>
        <p className="font-pro text-3xl font-semibold text-ink-900" aria-live="polite">
          {minutes}:{String(seconds).padStart(2, "0")}
        </p>
        <p className="mt-1 text-xs text-ink-500">Sans confirmation, l&apos;inscription est annulée et tout est supprimé.</p>
      </div>
      )}
      <button type="button" onClick={resend} className="btn-primary mb-2 w-full !py-3 text-sm">
        Renvoyer le lien
      </button>
      <button type="button" onClick={check} className="mb-3 w-full py-2 text-sm font-semibold text-brand">
        J&apos;ai confirmé, continuer
      </button>
      {sent && <p className="mb-3 text-center text-xs text-ink-700">{sent}</p>}
      <button
        type="button"
        onClick={() => {
          logout();
          router.replace("/photographes/inscription");
        }}
        className="w-full py-2 text-xs text-ink-500 underline"
      >
        Mauvaise adresse ? Se déconnecter et recommencer
      </button>
    </AuthCard>
  );
}

export default function WaitingForConfirmationPage() {
  return (
    <RequireAuth>
      <WaitingContent />
    </RequireAuth>
  );
}
