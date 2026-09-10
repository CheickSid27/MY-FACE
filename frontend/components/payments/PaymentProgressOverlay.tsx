"use client";

import { useEffect, useState } from "react";
import { CardIcon } from "@/components/icons";

const STEPS = [
  "Verification du panier...",
  "Creation de la commande...",
  "Preparation du paiement...",
];

// Barre de progression chiffree pendant l'initialisation du paiement : la
// requete peut prendre plusieurs secondes (base de donnees distante, voir
// notes de latence reseau), un simple texte statique "Initialisation..."
// donnait l'impression que la borne etait bloquee. On progresse jusqu'a 90%
// de facon animee (pas de vraie mesure d'avancement cote serveur) puis on
// saute a 100% juste avant la redirection reelle, pilotee par le parent via
// `done`.
export default function PaymentProgressOverlay({ done }: { done: boolean }) {
  const [progress, setProgress] = useState(0);
  const [stepIndex, setStepIndex] = useState(0);

  useEffect(() => {
    if (done) {
      setProgress(100);
      return;
    }
    const interval = setInterval(() => {
      setProgress((p) => (p >= 90 ? 90 : p + (90 - p) * 0.15 + 1));
    }, 200);
    return () => clearInterval(interval);
  }, [done]);

  useEffect(() => {
    if (done) return;
    const interval = setInterval(() => {
      setStepIndex((i) => Math.min(i + 1, STEPS.length - 1));
    }, 1100);
    return () => clearInterval(interval);
  }, [done]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-brand/80 p-4 backdrop-blur-sm animate-fade-in">
      <div className="glass-strong flex w-full max-w-sm flex-col items-center gap-5 rounded-2xl p-8 text-center">
        <div className="glass-pill relative flex h-16 w-16 items-center justify-center text-2xl text-brand">
          <span className="absolute inset-0 rounded-full border-2 border-brand-accent animate-pulse-ring" />
          <CardIcon />
        </div>
        <p className="text-3xl font-bold tabular-nums text-brand">{Math.round(progress)}%</p>
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-ink-900/10">
          <div
            className="h-full rounded-full bg-brand-accent transition-[width] duration-200 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>
        <p className="text-sm font-medium text-ink-700">{STEPS[stepIndex]}</p>
      </div>
    </div>
  );
}
