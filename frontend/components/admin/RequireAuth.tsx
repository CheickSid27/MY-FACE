"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api-client";
import { isAuthenticated } from "@/lib/auth";
import { useAuthStore } from "@/store/auth-store";

export default function RequireAuth({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  // "checking" pendant la validation reelle du token, puis "ok"/"denied".
  // Se contenter de la presence d'un token (ancien comportement) laissait un
  // admin dont le token a expire (et le refresh aussi) coince sur un ecran
  // casse, chaque appel API echouait silencieusement en arriere-plan sans
  // jamais renvoyer vers /admin/login. Ici on verifie activement auprès du
  // serveur (GET /auth/me, qui declenche le meme refresh automatique que
  // n'importe quel autre appel via lib/api-client.ts) avant d'afficher quoi
  // que ce soit.
  const [status, setStatus] = useState<"checking" | "ok" | "denied">("checking");
  const setUser = useAuthStore((s) => s.setUser);
  const isLoggedIn = useAuthStore((s) => s.isLoggedIn);

  useEffect(() => {
    if (!isAuthenticated()) {
      setStatus("denied");
      router.replace("/admin/login");
      return;
    }
    api
      .me()
      .then((user) => {
        setUser(user);
        setStatus("ok");
      })
      .catch(() => {
        setStatus("denied");
        router.replace("/admin/login");
      });
  }, [router, setUser]);

  // Deconnexion depuis une page deja affichee : on quitte immediatement
  // l'ecran admin au lieu de le laisser visible sans session.
  useEffect(() => {
    if (status === "ok" && !isLoggedIn) {
      setStatus("denied");
      router.replace("/admin/login");
    }
  }, [status, isLoggedIn, router]);

  if (status !== "ok") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
      </div>
    );
  }

  return <>{children}</>;
}
