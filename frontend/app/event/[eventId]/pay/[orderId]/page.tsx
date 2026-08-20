"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { CardIcon, ClockIcon, CrossIcon } from "@/components/icons";
import MethodIcon from "@/components/payments/MethodIcon";
import { api } from "@/lib/api-client";
import type { PaymentStatusResponse } from "@/types/api";

const POLL_INTERVAL_MS = 3000;
const IS_MANUAL_PROVIDER = process.env.NEXT_PUBLIC_PAYMENT_PROVIDER === "manual";

export default function PaymentStatusPage() {
  const { eventId, orderId } = useParams<{ eventId: string; orderId: string }>();
  const router = useRouter();

  const [data, setData] = useState<PaymentStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [simulating, setSimulating] = useState(false);
  const [markingPaid, setMarkingPaid] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    async function poll() {
      try {
        const result = await api.getPaymentStatus(orderId);
        setData(result);
        if (result.status === "success") {
          if (intervalRef.current) clearInterval(intervalRef.current);
          router.push(`/order/${orderId}/download`);
        } else if (result.status === "failed") {
          if (intervalRef.current) clearInterval(intervalRef.current);
        }
      } catch {
        setError("Impossible de verifier le statut du paiement.");
      }
    }

    poll();
    intervalRef.current = setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [orderId, router]);

  async function simulate(result: "success" | "failed") {
    setSimulating(true);
    try {
      await api.simulatePayment(orderId, result);
    } catch {
      // le backend refusera si un vrai operateur est configure ; rien a faire ici
    } finally {
      setSimulating(false);
    }
  }

  async function handleMarkPaid() {
    setMarkingPaid(true);
    try {
      const result = await api.markPaid(orderId);
      setData(result);
    } catch {
      setError("Impossible de confirmer votre paiement. Reessayez.");
    } finally {
      setMarkingPaid(false);
    }
  }

  if (!data) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-gradient-to-br from-brand to-brand-light">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-accent border-t-transparent" />
      </main>
    );
  }

  if (data.status === "failed") {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-6 bg-gradient-to-br from-brand to-brand-light px-6 text-center text-white animate-fade-in">
        <div className="glass-pill flex h-16 w-16 items-center justify-center text-3xl">
          <CrossIcon />
        </div>
        <h1 className="text-xl font-bold">Le paiement a echoue</h1>
        <p className="text-ink-300">
          Aucun montant n&apos;a ete debite. Vous pouvez reessayer depuis votre panier.
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
            Numero marchand : <span className="font-semibold text-white">{data.merchant_phone}</span>
          </p>
        )}

        {error && <p className="text-sm text-red-300">{error}</p>}

        <button
          type="button"
          disabled={markingPaid}
          onClick={handleMarkPaid}
          className="btn-accent w-full max-w-xs"
        >
          {markingPaid ? "Confirmation..." : "J'ai paye"}
        </button>
        <p className="max-w-sm text-xs text-ink-300">
          Apres verification par l&apos;organisateur, vous recevrez vos photos par SMS et sur cette
          page.
        </p>
      </main>
    );
  }

  // En attente de verification manuelle par l'organisateur
  if (data.status === "awaiting_confirmation") {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-5 bg-gradient-to-br from-brand to-brand-light px-6 text-center text-white">
        <div className="glass-pill relative flex h-16 w-16 items-center justify-center">
          <span className="absolute inset-0 rounded-full border-2 border-brand-accent animate-pulse-ring" />
          <ClockIcon className="text-2xl" />
        </div>
        <h1 className="text-xl font-bold">Paiement en cours de verification...</h1>
        <p className="max-w-sm text-sm text-ink-300">
          L&apos;organisateur verifie la reception de votre paiement. Ne fermez pas cette page :
          vous serez redirige automatiquement des confirmation.
        </p>
        {error && <p className="text-sm text-red-300">{error}</p>}
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
        Ne fermez pas cette page. Vous recevrez un SMS avec votre lien de telechargement des la
        confirmation.
      </p>
      {error && <p className="text-sm text-red-300">{error}</p>}

      {IS_MANUAL_PROVIDER && (
        <div className="glass-dark mt-6 w-full max-w-sm rounded-2xl p-4">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-brand-accent">
            Mode test — aucun operateur reel connecte
          </p>
          <p className="mb-4 text-xs text-ink-300">
            Simulez la reponse de l&apos;operateur pour tester le parcours de bout en bout.
          </p>
          <div className="flex gap-3">
            <button
              type="button"
              disabled={simulating}
              onClick={() => simulate("success")}
              className="btn-accent flex-1 !py-2.5 text-sm"
            >
              Simuler succes
            </button>
            <button
              type="button"
              disabled={simulating}
              onClick={() => simulate("failed")}
              className="btn-ghost flex-1 !border-white/20 !bg-transparent !py-2.5 text-sm !text-white hover:!bg-white/10"
            >
              Simuler echec
            </button>
          </div>
        </div>
      )}
    </main>
  );
}
