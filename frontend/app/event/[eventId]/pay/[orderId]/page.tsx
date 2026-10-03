"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { AlertIcon, CardIcon, ClockIcon, CrossIcon } from "@/components/icons";
import MethodIcon from "@/components/payments/MethodIcon";
import { api, ApiError } from "@/lib/api-client";
import type { OrderStatus, PaymentStatusResponse } from "@/types/api";

const POLL_INTERVAL_MS = 3000;
// Statuts definitifs : plus rien a attendre, le polling s'arrete.
const FINAL_STATUSES: OrderStatus[] = ["success", "failed", "cancelled"];

export default function PaymentStatusPage() {
  const { eventId, orderId } = useParams<{ eventId: string; orderId: string }>();
  const router = useRouter();

  const [data, setData] = useState<PaymentStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Commande inexistante (lien errone/tronque) : distinct d'une simple
  // erreur reseau passagere, qui laisse le polling continuer.
  const [notFound, setNotFound] = useState(false);
  const [markingPaid, setMarkingPaid] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    intervalRef.current = null;
  }, []);

  const poll = useCallback(async () => {
    try {
      const result = await api.getPaymentStatus(orderId);
      setData(result);
      setError(null);
      if (result.status === "success") {
        stopPolling();
        router.push(`/order/${orderId}/download`);
      } else if (FINAL_STATUSES.includes(result.status)) {
        stopPolling();
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setNotFound(true);
        stopPolling();
        return;
      }
      setError("Connexion instable : nouvelle vérification automatique dans quelques secondes...");
    }
  }, [orderId, router, stopPolling]);

  const startPolling = useCallback(() => {
    stopPolling();
    poll();
    intervalRef.current = setInterval(poll, POLL_INTERVAL_MS);
  }, [poll, stopPolling]);

  useEffect(() => {
    startPolling();
    return stopPolling;
  }, [startPolling, stopPolling]);

  async function handleMarkPaid() {
    setMarkingPaid(true);
    try {
      const result = await api.markPaid(orderId);
      setData(result);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Impossible de confirmer votre paiement. Réessayez.");
      // Le statut a pu changer (ex: commande expiree) : on le relit.
      poll();
    } finally {
      setMarkingPaid(false);
    }
  }

  if (notFound) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-5 bg-gradient-to-br from-brand to-brand-light px-6 text-center text-white animate-fade-in">
        <div className="glass-pill flex h-16 w-16 items-center justify-center text-3xl">
          <AlertIcon />
        </div>
        <h1 className="text-xl font-bold">Commande introuvable</h1>
        <p className="max-w-sm text-sm text-ink-300">
          Ce lien de paiement n&apos;existe pas ou est incomplet. Vérifiez le lien, ou refaites
          votre sélection depuis la galerie.
        </p>
        <button type="button" onClick={() => router.push(`/event/${eventId}/gallery`)} className="btn-accent">
          Retour à la galerie
        </button>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-4 bg-gradient-to-br from-brand to-brand-light px-6 text-center text-white">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-accent border-t-transparent" />
        {error && <p className="max-w-sm text-sm text-red-200">{error}</p>}
      </main>
    );
  }

  if (data.status === "failed") {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-6 bg-gradient-to-br from-brand to-brand-light px-6 text-center text-white animate-fade-in">
        <div className="glass-pill flex h-16 w-16 items-center justify-center text-3xl">
          <CrossIcon />
        </div>
        <h1 className="text-xl font-bold">Paiement non confirmé</h1>
        <p className="max-w-sm text-ink-300">
          L&apos;organisateur n&apos;a pas pu vérifier la réception de ce paiement. Si vous avez
          bien payé, rapprochez-vous de l&apos;organisateur avec votre numéro de téléphone.
        </p>
        <button type="button" onClick={() => router.push(`/event/${eventId}/cart`)} className="btn-accent">
          Retour au panier
        </button>
      </main>
    );
  }

  if (data.status === "cancelled") {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-6 bg-gradient-to-br from-brand to-brand-light px-6 text-center text-white animate-fade-in">
        <div className="glass-pill flex h-16 w-16 items-center justify-center text-3xl">
          <ClockIcon />
        </div>
        <h1 className="text-xl font-bold">Commande expirée</h1>
        <p className="max-w-sm text-ink-300">
          Cette commande n&apos;a pas été payée à temps et a été annulée. Si vous avez déjà payé,
          rapprochez-vous de l&apos;organisateur avec votre numéro de téléphone : il peut la
          valider. Sinon, vous pouvez repasser commande depuis votre panier.
        </p>
        <button type="button" onClick={() => router.push(`/event/${eventId}/cart`)} className="btn-accent">
          Retour au panier
        </button>
      </main>
    );
  }

  // Flux QR : le client doit encore scanner + payer, puis declarer "j'ai paye"
  if (data.status === "pending" && data.qr_image_url) {
    return (
      <main className="flex min-h-screen flex-col items-center gap-5 bg-gradient-to-br from-brand to-brand-light px-6 py-10 text-center text-white animate-fade-in">
        <div className="glass-pill flex items-center gap-2 px-4 py-2">
          <MethodIcon method={data.payment_method} size={24} />
        </div>
        <h1 className="text-xl font-bold">
          Payez {data.total_amount.toLocaleString("fr-FR")} {data.currency}
        </h1>
        <p className="max-w-sm text-sm text-ink-300">
          Scannez ce QR code depuis votre application de paiement, effectuez le transfert, puis
          confirmez ci-dessous.
        </p>

        <div className="glass-strong rounded-2xl p-4">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={data.qr_image_url} alt="QR code de paiement" className="h-56 w-56 rounded-xl object-cover" />
        </div>

        {data.merchant_phone && (
          <p className="text-sm text-ink-300">
            Numéro marchand : <span className="font-semibold text-white">{data.merchant_phone}</span>
          </p>
        )}

        {error && <p className="max-w-sm text-sm text-red-200">{error}</p>}

        <button
          type="button"
          disabled={markingPaid}
          onClick={handleMarkPaid}
          className="btn-accent w-full max-w-xs"
        >
          {markingPaid ? "Confirmation..." : "J'ai payé"}
        </button>
        <p className="max-w-sm text-xs text-ink-300">
          Après vérification par l&apos;organisateur, vous recevrez vos photos par SMS et sur cette
          page.
        </p>
      </main>
    );
  }

  // En attente de verification manuelle par l'organisateur
  if (data.status === "awaiting_confirmation") {
    // Especes : le client n'a rien scanne, il doit se rendre au comptoir de la
    // borne avec le montant en liquide (voir backend payments.py, branche CASH).
    if (data.payment_method === "cash") {
      return (
        <main className="flex min-h-screen flex-col items-center justify-center gap-5 bg-gradient-to-br from-brand to-brand-light px-6 text-center text-white">
          <div className="glass-pill flex items-center gap-2 px-4 py-2">
            <MethodIcon method="cash" size={24} />
          </div>
          <h1 className="text-xl font-bold">
            Rendez-vous au comptoir avec {data.total_amount.toLocaleString("fr-FR")} {data.currency}
          </h1>
          <p className="max-w-sm text-sm text-ink-300">
            Un membre de l&apos;équipe va recevoir votre paiement en espèces et valider votre
            commande. Ne fermez pas cette page : vous serez redirige automatiquement des
            confirmation.
          </p>
          {error && <p className="text-sm text-red-200">{error}</p>}
        </main>
      );
    }

    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-5 bg-gradient-to-br from-brand to-brand-light px-6 text-center text-white">
        <div className="glass-pill relative flex h-16 w-16 items-center justify-center">
          <span className="absolute inset-0 rounded-full border-2 border-brand-accent animate-pulse-ring" />
          <ClockIcon className="text-2xl" />
        </div>
        <h1 className="text-xl font-bold">Paiement en cours de vérification...</h1>
        <p className="max-w-sm text-sm text-ink-300">
          L&apos;organisateur vérifie la réception de votre paiement. Ne fermez pas cette page :
          vous serez redirige automatiquement des confirmation.
        </p>
        {error && <p className="text-sm text-red-200">{error}</p>}
      </main>
    );
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-5 bg-gradient-to-br from-brand to-brand-light px-6 text-center text-white">
      <div className="glass-pill relative flex h-16 w-16 items-center justify-center">
        <span className="absolute inset-0 rounded-full border-2 border-brand-accent animate-pulse-ring" />
        <CardIcon className="text-2xl" />
      </div>
      <h1 className="text-xl font-bold">En attente de confirmation du paiement...</h1>
      <p className="max-w-sm text-sm text-ink-300">
        Ne fermez pas cette page. Vous recevrez un SMS avec votre lien de téléchargement des la
        confirmation.
      </p>
      {error && <p className="text-sm text-red-200">{error}</p>}
    </main>
  );
}
