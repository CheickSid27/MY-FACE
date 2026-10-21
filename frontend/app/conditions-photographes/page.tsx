import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Conditions d'utilisation photographes · MYFACE",
};

// Texte de travail : a faire relire par un juriste et a completer apres la
// creation de la societe (RCCM) et le depot du dossier ARTCI.
const SECTIONS: { title: string; body: string[] }[] = [
  {
    title: "1. Le service",
    body: [
      "MYFACE permet à un photographe ou à un organisateur de déposer les photos d'un événement, de les faire analyser par une IA de reconnaissance faciale, et de les mettre à disposition de ses invités par un lien ou un QR code.",
      "Chaque événement dispose d'un pack : Découverte (gratuit, 10 photos), Événement (10 000 F, 500 photos), Pro (25 000 F, 2 000 photos) ou Sur mesure. Le prix d'un pack est payé une seule fois par événement ; il n'y a pas d'abonnement.",
    ],
  },
  {
    title: "2. Paiement des packs",
    body: [
      "Le photographe envoie le montant du pack aux numéros Mobile Money indiqués par MYFACE, puis déclare la référence de la transaction. Le pack est activé après vérification de la réception du paiement.",
      "Pour passer à un pack supérieur, seule la différence avec les montants déjà payés pour l'événement est due. Un pack payé n'est pas remboursable une fois des photos déposées au-delà de la limite du pack précédent.",
    ],
  },
  {
    title: "3. Ventes aux invités",
    body: [
      "Le photographe fixe librement le prix de ses photos ou choisit de les offrir. Les invités paient directement sur les moyens de paiement configurés par le photographe : MYFACE n'encaisse pas ces sommes et ne prend pas de commission sur ces ventes.",
      "Le photographe est seul responsable de la livraison des photos achetées, des prix affichés et de ses obligations fiscales.",
    ],
  },
  {
    title: "4. Photos, droits et personnes photographiées",
    body: [
      "Le photographe garantit qu'il détient les droits sur les photos déposées et que les personnes photographiées, ou l'organisateur de l'événement, ont été informées que les photos seraient mises à disposition des invités et analysées par reconnaissance faciale.",
      "MYFACE n'acquiert aucun droit sur les photos et ne les utilise pas pour sa propre communication sans l'accord écrit du photographe.",
    ],
  },
  {
    title: "5. Données personnelles et reconnaissance faciale",
    body: [
      "L'analyse des visages sert uniquement à permettre à chaque invité de retrouver ses propres photos. Le selfie d'un invité n'est pas enregistré : il sert à la recherche puis il est effacé. L'invité donne son accord avant toute recherche.",
      "Pour toute demande d'accès ou de suppression, les invités et les photographes écrivent à contact@myfaceci.online. Le photographe peut supprimer à tout moment une photo ou un événement depuis son espace.",
    ],
  },
  {
    title: "6. Compte",
    body: [
      "Le photographe est responsable de la confidentialité de son mot de passe et des contenus déposés depuis son compte. MYFACE peut suspendre un compte en cas d'usage frauduleux, de contenu illicite ou de paiement déclaré mais non reçu.",
    ],
  },
  {
    title: "7. Contact",
    body: ["MYFACE, Abidjan, Côte d'Ivoire · contact@myfaceci.online"],
  },
];

export default function ConditionsPhotographesPage() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-surface-alt to-surface px-5 py-10">
      <article className="glass mx-auto max-w-3xl rounded-2xl p-6 sm:p-8">
        <Link href="/photographes" className="mb-4 inline-block text-sm font-medium text-ink-500 hover:text-brand">
          &larr; MYFACE pour les photographes
        </Link>
        <h1 className="mb-1 text-2xl font-bold text-ink-900">Conditions d&apos;utilisation, photographes et organisateurs</h1>
        <p className="mb-6 text-xs text-ink-500">Version du 21 octobre 2026</p>
        {SECTIONS.map((section) => (
          <section key={section.title} className="mb-5">
            <h2 className="mb-2 text-base font-semibold text-ink-900">{section.title}</h2>
            {section.body.map((paragraph) => (
              <p key={paragraph.slice(0, 40)} className="mb-2 text-sm leading-relaxed text-ink-700">
                {paragraph}
              </p>
            ))}
          </section>
        ))}
      </article>
    </main>
  );
}
