import Link from "next/link";

export default function RootPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 bg-brand px-6 text-center text-white">
      <h1 className="text-3xl font-bold">MYFACE</h1>
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
