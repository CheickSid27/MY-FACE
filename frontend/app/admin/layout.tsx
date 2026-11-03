"use client";

import { usePathname } from "next/navigation";
import RequireAuth from "@/components/admin/RequireAuth";
import MaintenanceGate from "@/components/maintenance/MaintenanceGate";
import ProShell from "@/components/pro/ProShell";
import WorkspaceProvider from "@/components/pro/WorkspaceProvider";
import { useAuthStore } from "@/store/auth-store";

// Pages sans la structure MYFACE Pro : connexion, et pages faites pour
// l'impression (affiche QR, recu) qui doivent occuper toute la feuille.
function isBare(pathname: string): boolean {
  return (
    pathname === "/admin/login" ||
    pathname === "/admin/confirmation" ||
    /^\/admin\/events\/[^/]+\/poster/.test(pathname) ||
    /^\/admin\/orders\/[^/]+\/receipt/.test(pathname)
  );
}

// Mode maintenance avec les photographes inclus : leur espace affiche le
// message ; l'admin garde toujours l'acces pour reparer et couper le mode.
function PhotographerMaintenance({ children }: { children: React.ReactNode }) {
  const isAdmin = useAuthStore((s) => s.user?.role === "admin");
  if (isAdmin) return <>{children}</>;
  return <MaintenanceGate audience="photographers">{children}</MaintenanceGate>;
}

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  if (isBare(pathname)) return <>{children}</>;
  return (
    <RequireAuth bannerClassName="lg:pl-64">
      <PhotographerMaintenance>
        <WorkspaceProvider>
          <ProShell>{children}</ProShell>
        </WorkspaceProvider>
      </PhotographerMaintenance>
    </RequireAuth>
  );
}
