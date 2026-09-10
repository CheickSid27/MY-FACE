import Link from "next/link";
import { AlertIcon } from "@/components/icons";

export default function NotFound() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-5 bg-gradient-to-br from-brand to-brand-light px-6 text-center text-white">
      <div className="glass-pill flex h-16 w-16 items-center justify-center text-3xl">
        <AlertIcon />
      </div>
      <h1 className="text-xl font-bold">Page introuvable</h1>
      <p className="max-w-sm text-sm text-ink-300">
        Cette page n&apos;existe pas ou plus. Verifiez le lien, ou revenez a l&apos;accueil.
      </p>
      <Link href="/" className="btn-accent">
        Retour a l&apos;accueil
      </Link>
    </main>
  );
}
