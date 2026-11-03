"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import MyfaceLogo from "@/components/brand/Logo";
import { api } from "@/lib/api-client";

const RECHECK_MS = 30_000;

/** Pages invites (accueil, evenement, galerie, panier, commande) : quand un
 * admin active le mode maintenance (/admin/settings), on affiche son message
 * a la place de la page, et on revient tout seul a la page des qu'il est
 * coupe. Si le statut ne repond pas, la page s'affiche normalement : une
 * panne du statut ne doit jamais bloquer les invites.
 *
 * audience="photographers" (espace MYFACE Pro d'un photographe) : ferme
 * seulement si l'admin a inclus les photographes dans la maintenance. */
export default function MaintenanceGate({
  children,
  audience = "guests",
}: {
  children: React.ReactNode;
  audience?: "guests" | "photographers";
}) {
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    let stopped = false;
    async function check() {
      try {
        const status = await api.getPlatformStatus();
        const closed = status.maintenance && (audience === "guests" || status.photographers);
        if (!stopped) setMessage(closed ? status.message : null);
      } catch {
        // statut injoignable : on laisse la page
      }
    }
    check();
    const timer = setInterval(check, RECHECK_MS);
    return () => {
      stopped = true;
      clearInterval(timer);
    };
  }, [audience]);

  if (!message) return <>{children}</>;

  return (
    <main
      role="status"
      className="flex min-h-screen flex-col items-center justify-center gap-5 bg-brand px-6 text-center text-white"
    >
      <MyfaceLogo size={88} tone="light" />
      <h1 className="text-2xl font-bold">Maintenance en cours</h1>
      <p className="max-w-sm text-gray-300">{message}</p>
      <p className="text-xs text-gray-400">Cette page se met à jour toute seule dès que MYFACE est de retour.</p>
      {audience === "guests" && (
        <Link href="/admin/login" className="mt-4 text-sm font-medium text-gray-300 underline-offset-4 hover:underline">
          Espace organisateur
        </Link>
      )}
    </main>
  );
}
