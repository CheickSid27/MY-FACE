"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated } from "@/lib/auth";

export default function RequireAuth({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  // `mounted` evite un mismatch d'hydratation : le rendu serveur ne peut pas
  // savoir si l'utilisateur est authentifie (localStorage n'existe que cote
  // client), donc le premier rendu client doit rester identique au rendu
  // serveur (rien) avant de decider quoi afficher.
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    if (!isAuthenticated()) {
      router.replace("/admin/login");
    }
  }, [router]);

  if (!mounted || !isAuthenticated()) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
      </div>
    );
  }

  return <>{children}</>;
}
