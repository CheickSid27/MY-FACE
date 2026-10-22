import Link from "next/link";
import MyfaceLogo from "@/components/brand/Logo";
import EventCodeForm from "@/components/event/EventCodeForm";

export default function RootPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 bg-brand px-6 text-center text-white">
      <MyfaceLogo size={96} tone="light" />
      <h1 className="text-3xl font-bold">
        MY<span className="text-[#F26A1B]">FACE</span>
      </h1>
      <p className="-mt-3 text-sm text-gray-400">Scanne. Retrouve. Repars avec.</p>
      <p className="max-w-md text-gray-300">
        Vous êtes invité ? Scannez le QR code de l&apos;événement, ou tapez son code ci-dessous.
      </p>
      <EventCodeForm />
      <Link
        href="/admin/login"
        className="mt-4 rounded-xl border border-white/25 px-6 py-3 font-semibold text-white hover:bg-white/10"
      >
        Espace organisateur
      </Link>
      <Link href="/photographes" className="text-sm font-medium text-gray-300 underline-offset-4 hover:underline">
        Vous êtes photographe ? Découvrez MYFACE pour vos événements
      </Link>
    </main>
  );
}
