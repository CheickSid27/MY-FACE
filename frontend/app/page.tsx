import Link from "next/link";
import MyfaceLogo from "@/components/brand/Logo";

export default function RootPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 bg-brand px-6 text-center text-white">
      <MyfaceLogo size={96} tone="light" />
      <h1 className="text-3xl font-bold">
        MY<span className="text-[#F26A1B]">FACE</span>
      </h1>
      <p className="-mt-3 text-sm text-gray-400">Un selfie. Toutes tes photos.</p>
      <p className="max-w-md text-gray-300">
        Cette application se consulte via le lien specifique a un evenement
        (borne ou QR code), ou via l&apos;espace organisateur.
      </p>
      <Link
        href="/admin/login"
        className="rounded-xl bg-brand-accent px-6 py-3 font-semibold text-brand hover:brightness-110"
      >
        Espace organisateur
      </Link>
    </main>
  );
}
