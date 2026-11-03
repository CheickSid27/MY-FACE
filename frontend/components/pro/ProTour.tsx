"use client";

import { useCallback, useEffect, useLayoutEffect, useState } from "react";
import { useRouter } from "next/navigation";
import MyfaceLogo from "@/components/brand/Logo";
import { useAuthStore } from "@/store/auth-store";

/** Visite guidee de MYFACE Pro. A sa premiere arrivee, un nouveau compte se
 * voit proposer la visite : il accepte ou refuse, et on ne redemande plus (sur
 * cet appareil). La visite eclaire tour a tour les boutons du menu
 * (data-tour="...") ; une etape dont le bouton n'est pas affiche (menu du
 * telephone plus court) est passee. « Revoir la visite guidee » (page Compte)
 * la relance avec startProTour(). */

// Comptes crees avant la visite (03/11/2026) : pas de proposition automatique.
const TOUR_START = Date.parse("2026-11-03T00:00:00Z");
const START_EVENT = "myface:visite";

export function startProTour() {
  window.dispatchEvent(new Event(START_EVENT));
}

interface Step {
  target?: string;
  title: string;
  text: string;
}

const STEPS: Step[] = [
  {
    target: "ajouter",
    title: "Le bouton « Ajouter »",
    text: "Créez un événement (mariage, soutenance, anniversaire…) ou ajoutez des photos à votre événement en cours.",
  },
  {
    target: "evenements",
    title: "Vos événements",
    text: "Dans chaque événement : envoyez vos photos, une par une ou en choisissant un dossier de votre ordinateur qui s'envoie tout seul. Rangez-les par parties (Mairie, Réception…) et récupérez le QR code à afficher le jour J.",
  },
  {
    title: "La reconnaissance faciale",
    text: "Les invités scannent le QR code, prennent un selfie ou touchent « Trouver mon visage ». Notre IA leur montre en quelques secondes toutes les photos où ils apparaissent.",
  },
  {
    target: "ventes",
    title: "Vos ventes",
    text: "Les invités achètent leurs photos par Mobile Money. Ici, vous confirmez les paiements reçus et suivez chaque commande.",
  },
  {
    target: "statistiques",
    title: "Statistiques",
    text: "Visites, photos vues, ventes : voyez ce qui marche à chaque événement.",
  },
  {
    target: "notifications",
    title: "Notifications",
    text: "Nouvelle commande, paiement à confirmer : vous êtes prévenu ici.",
  },
  {
    target: "compte",
    title: "Votre compte",
    text: "Votre profil, votre photo, vos numéros Mobile Money pour être payé et votre mot de passe. Vous pourrez revoir cette visite depuis cette page.",
  },
];

function storageKey(userId: string) {
  return `myface-visite-${userId}`;
}

function readChoice(userId: string): string | null {
  try {
    return window.localStorage.getItem(storageKey(userId));
  } catch {
    return null;
  }
}

function saveChoice(userId: string, choice: "faite" | "refusee") {
  try {
    window.localStorage.setItem(storageKey(userId), choice);
  } catch {
    // stockage indisponible (navigation privee) : la question reviendra
  }
}

function visibleTarget(name: string): HTMLElement | null {
  const nodes = Array.from(document.querySelectorAll<HTMLElement>(`[data-tour="${name}"]`));
  return nodes.find((n) => n.getClientRects().length > 0 && n.getBoundingClientRect().width > 0) ?? null;
}

type Mode = "closed" | "ask" | "tour" | "end";

export default function ProTour() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const [mode, setMode] = useState<Mode>("closed");
  const [steps, setSteps] = useState<Step[]>([]);
  const [index, setIndex] = useState(0);
  const [rect, setRect] = useState<DOMRect | null>(null);

  // Premiere arrivee d'un nouveau compte : on propose la visite.
  useEffect(() => {
    if (!user || user.must_verify_email) return;
    if (Date.parse(user.created_at) < TOUR_START) return;
    if (readChoice(user.id) === null) setMode("ask");
  }, [user]);

  const begin = useCallback(() => {
    setSteps(STEPS.filter((s) => !s.target || visibleTarget(s.target)));
    setIndex(0);
    setMode("tour");
  }, []);

  useEffect(() => {
    window.addEventListener(START_EVENT, begin);
    return () => window.removeEventListener(START_EVENT, begin);
  }, [begin]);

  const step = mode === "tour" ? steps[index] : undefined;

  useLayoutEffect(() => {
    if (!step?.target) {
      setRect(null);
      return;
    }
    const measure = () => {
      const el = visibleTarget(step.target!);
      setRect(el ? el.getBoundingClientRect() : null);
    };
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, [step]);

  useEffect(() => {
    if (mode === "closed") return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") finish();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  function finish(choice: "faite" | "refusee" = "faite") {
    if (user) saveChoice(user.id, choice);
    setMode("closed");
  }

  if (mode === "closed" || !user) return null;

  const firstName = (user.display_name || "").split(" ")[0];
  const primary = "btn-primary w-full !py-3 text-sm";
  const secondary = "w-full rounded-2xl py-3 text-sm font-semibold text-ink-500 hover:text-ink-900";

  if (mode === "ask" || mode === "end") {
    return (
      <div className="fixed inset-0 z-[60] flex items-end justify-center bg-brand/60 p-4 backdrop-blur-sm animate-fade-in sm:items-center">
        <div role="dialog" aria-modal="true" aria-labelledby="visite-titre" className="w-full max-w-sm rounded-3xl bg-[#F7F3EC] p-6 text-center shadow-elevated animate-scale-in">
          <div className="mb-3 flex justify-center">
            <MyfaceLogo size={56} />
          </div>
          {mode === "ask" ? (
            <>
              <h2 id="visite-titre" className="mb-2 font-pro text-lg font-bold text-ink-900">
                Bienvenue{firstName ? ` ${firstName}` : ""} sur MYFACE Pro
              </h2>
              <p className="mb-5 text-sm text-ink-700">
                Voulez-vous une petite visite pour découvrir comment tout marche ? Cela prend une minute.
              </p>
              <div className="flex flex-col gap-1">
                <button type="button" onClick={begin} className={primary} autoFocus>
                  Oui, montrez-moi
                </button>
                <button type="button" onClick={() => finish("refusee")} className={secondary}>
                  Non merci
                </button>
              </div>
              <p className="mt-2 text-xs text-ink-500">Vous pourrez la lancer plus tard depuis la page Compte.</p>
            </>
          ) : (
            <>
              <h2 id="visite-titre" className="mb-2 font-pro text-lg font-bold text-ink-900">
                C&apos;est parti !
              </h2>
              <p className="mb-5 text-sm text-ink-700">
                Commencez par créer votre premier événement : le QR code et la page des invités sont prêts en une minute.
              </p>
              <div className="flex flex-col gap-1">
                <button
                  type="button"
                  autoFocus
                  onClick={() => {
                    finish();
                    router.push("/admin/events?nouveau=1");
                  }}
                  className={primary}
                >
                  Créer mon événement
                </button>
                <button type="button" onClick={() => finish()} className={secondary}>
                  Plus tard
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    );
  }

  if (!step) return null;

  const last = index === steps.length - 1;
  const pad = 6;
  const cardWidth = 320;
  let cardStyle: React.CSSProperties;
  if (rect) {
    const viewW = window.innerWidth;
    const viewH = window.innerHeight;
    const left = Math.min(Math.max(12, rect.left + rect.width / 2 - cardWidth / 2), viewW - cardWidth - 12);
    if (rect.right + cardWidth + 24 < viewW && rect.left < viewW / 3) {
      // menu lateral (ordinateur) : la carte a droite du bouton
      cardStyle = { left: rect.right + 16, top: Math.min(Math.max(12, rect.top - 20), viewH - 260) };
    } else if (rect.top > viewH / 2) {
      // barre du bas (telephone) : la carte au-dessus
      cardStyle = { left, bottom: viewH - rect.top + 16 };
    } else {
      cardStyle = { left, top: rect.bottom + 16 };
    }
  } else {
    cardStyle = { left: "50%", top: "50%", transform: "translate(-50%, -50%)" };
  }

  return (
    <div className="fixed inset-0 z-[60]" role="dialog" aria-modal="true" aria-labelledby="visite-etape">
      {rect ? (
        <div
          className="pointer-events-none fixed rounded-2xl ring-2 ring-brand-accent transition-all duration-300"
          style={{
            left: rect.left - pad,
            top: rect.top - pad,
            width: rect.width + pad * 2,
            height: rect.height + pad * 2,
            boxShadow: "0 0 0 9999px rgba(14,36,41,0.62)",
          }}
        />
      ) : (
        <div className="fixed inset-0 bg-brand/60" />
      )}
      <div className="fixed rounded-3xl bg-[#F7F3EC] p-5 shadow-elevated animate-scale-in" style={{ ...cardStyle, width: cardWidth, maxWidth: "calc(100vw - 24px)" }}>
        <p className="mb-1 text-xs font-semibold text-ink-500">
          {index + 1} / {steps.length}
        </p>
        <h2 id="visite-etape" className="mb-1.5 font-pro text-base font-bold text-ink-900">
          {step.title}
        </h2>
        <p className="mb-4 text-sm text-ink-700">{step.text}</p>
        <div className="flex items-center gap-2">
          <button type="button" onClick={() => finish()} className="mr-auto text-xs font-semibold text-ink-500 hover:text-ink-900">
            Passer la visite
          </button>
          {index > 0 && (
            <button type="button" onClick={() => setIndex(index - 1)} className="rounded-xl border border-ink-900/15 px-3 py-2 text-sm font-semibold text-ink-700">
              Retour
            </button>
          )}
          <button
            type="button"
            autoFocus
            onClick={() => (last ? setMode("end") : setIndex(index + 1))}
            className="btn-primary !px-4 !py-2 text-sm"
          >
            {last ? "Terminer" : "Suivant"}
          </button>
        </div>
      </div>
    </div>
  );
}
