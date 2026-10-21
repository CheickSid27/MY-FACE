import type { Metadata } from "next";
import Link from "next/link";
import MyfaceLogo from "@/components/brand/Logo";
import PricingTable from "@/components/packs/PricingTable";

export const metadata: Metadata = {
  title: "MYFACE pour les photographes",
  description:
    "Déposez les photos de vos événements, l'IA de reconnaissance faciale les trie, chaque invité retrouve les siennes avec un selfie. Dès 0 F.",
};

const STEPS = [
  {
    title: "Créez l'événement",
    text: "En une minute : nom, date, lieu. Vous obtenez un QR code et un lien à partager avec les invités.",
  },
  {
    title: "Déposez vos photos",
    text: "Glissez-déposez vos photos, même pendant la soirée. Notre IA de reconnaissance faciale détecte chaque visage et regroupe les photos de chaque invité.",
  },
  {
    title: "Chaque invité retrouve les siennes",
    text: "Il scanne le QR code, touche « Trouver mon visage » ou prend un selfie : toutes ses photos, en quelques secondes.",
  },
  {
    title: "Vendez ou offrez",
    text: "Fixez votre prix : les invités paient directement sur VOTRE Wave ou Orange Money. Ou offrez les photos, sans aucune page de paiement.",
  },
];

const FAQ = [
  {
    q: "Comment je paie un pack ?",
    a: "Une seule fois par événement, sans abonnement, par Mobile Money (Wave, Orange Money, MTN, Moov, Djamo). Vous déclarez votre paiement depuis la page de l'événement, MYFACE vérifie et active le pack.",
  },
  {
    q: "Qui encaisse l'argent des invités ?",
    a: "Vous. Les invités paient sur vos propres numéros Mobile Money, que vous configurez pour chaque événement. MYFACE ne prend aucune commission sur vos ventes.",
  },
  {
    q: "Le pack Découverte est vraiment gratuit ?",
    a: "Oui : 10 photos par événement, sans carte ni engagement, pour tester avec vos clients. Vous passez au pack supérieur quand vous voulez, en ne payant que la différence.",
  },
  {
    q: "Et les données des invités ?",
    a: "Le selfie d'un invité n'est jamais enregistré : il sert seulement à la recherche, puis il est effacé. Les invités donnent leur accord avant toute recherche.",
  },
  {
    q: "Et si je n'ai pas Internet sur le lieu ?",
    a: "Déposez vos photos dès que vous avez une connexion : les invités les retrouvent avec le même lien ou le même QR code, le soir même ou le lendemain.",
  },
];

export default function PhotographesPage() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-surface-alt to-surface">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-5 py-5">
        <Link href="/photographes" className="flex items-center gap-2">
          <MyfaceLogo size={34} />
          <span className="text-lg font-bold text-ink-900">
            MY<span className="text-brand-accent">FACE</span>
          </span>
        </Link>
        <div className="flex items-center gap-4 text-sm font-medium">
          <Link href="/admin/login" className="text-ink-700 hover:text-brand">
            Se connecter
          </Link>
          <Link href="/photographes/inscription" className="btn-accent !px-4 !py-2 text-sm">
            Créer mon compte
          </Link>
        </div>
      </header>

      <section className="mx-auto max-w-6xl px-5 pb-12 pt-6 text-center">
        <p className="mb-3 text-xs font-semibold uppercase tracking-[0.25em] text-brand-accent">Pour les photographes</p>
        <h1 className="mx-auto max-w-3xl text-4xl font-bold leading-tight text-ink-900 sm:text-5xl">
          Vos invités retrouvent leurs photos en un selfie. Vous vendez plus, sans rien trier.
        </h1>
        <p className="mx-auto mt-5 max-w-2xl text-lg text-ink-700">
          Déposez les photos de vos événements sur MYFACE : notre IA de reconnaissance faciale les range par invité,
          et chacun repart avec les siennes. Plus de tirages étalés par terre, plus de groupes WhatsApp flous.
        </p>
        <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Link href="/photographes/inscription" className="btn-accent !px-6 !py-3.5 text-base">
            Essayer gratuitement sur mon prochain événement
          </Link>
          <a href="#tarifs" className="btn-ghost !px-6 !py-3.5 text-base">
            Voir les tarifs
          </a>
        </div>
        <p className="mt-3 text-xs text-ink-500">Sans carte, sans engagement · 10 photos gratuites par événement</p>
      </section>

      <section className="mx-auto max-w-6xl px-5 pb-14">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((step, i) => (
            <div key={step.title} className="glass rounded-2xl p-5">
              <p className="mb-2 flex h-8 w-8 items-center justify-center rounded-full bg-brand text-sm font-bold text-white">
                {i + 1}
              </p>
              <p className="font-semibold text-ink-900">{step.title}</p>
              <p className="mt-1 text-sm text-ink-700">{step.text}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="tarifs" className="mx-auto max-w-6xl scroll-mt-6 px-5 pb-14">
        <h2 className="mb-2 text-center text-3xl font-bold text-ink-900">Des tarifs simples, par événement</h2>
        <p className="mb-8 text-center text-ink-700">Paiement unique par Mobile Money. Pas d&apos;abonnement.</p>
        <PricingTable />
      </section>

      <section className="mx-auto max-w-3xl px-5 pb-16">
        <h2 className="mb-6 text-center text-2xl font-bold text-ink-900">Questions fréquentes</h2>
        <div className="flex flex-col gap-3">
          {FAQ.map((item) => (
            <details key={item.q} className="glass rounded-2xl p-4">
              <summary className="cursor-pointer font-semibold text-ink-900">{item.q}</summary>
              <p className="mt-2 text-sm text-ink-700">{item.a}</p>
            </details>
          ))}
        </div>
      </section>

      <footer className="border-t border-ink-900/5 px-5 py-6 text-center text-xs text-ink-500">
        MYFACE, IA de reconnaissance faciale pour les photos d&apos;événements · Abidjan ·{" "}
        <Link href="/conditions-photographes" className="hover:underline">
          Conditions d&apos;utilisation
        </Link>
      </footer>
    </main>
  );
}
