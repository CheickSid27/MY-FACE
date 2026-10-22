"use client";

import { usePathname } from "next/navigation";
import RequireAuth from "@/components/admin/RequireAuth";
import ProShell from "@/components/pro/ProShell";
import WorkspaceProvider from "@/components/pro/WorkspaceProvider";

// Pages sans la structure MYFACE Pro : connexion, et pages faites pour
// l'impression (affiche QR, recu) qui doivent occuper toute la feuille.
function isBare(pathname: string): boolean {
  return (
    pathname === "/admin/login" ||
    /^\/admin\/events\/[^/]+\/poster/.test(pathname) ||
    /^\/admin\/orders\/[^/]+\/receipt/.test(pathname)
  );
}

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  if (isBare(pathname)) return <>{children}</>;
  return (
    <RequireAuth bannerClassName="lg:pl-64">
      <WorkspaceProvider>
        <ProShell>{children}</ProShell>
      </WorkspaceProvider>
    </RequireAuth>
  );
}
