import MaintenanceGate from "@/components/maintenance/MaintenanceGate";

/** Pages invites : message du mode maintenance quand il est actif. */
export default function GuestLayout({ children }: { children: React.ReactNode }) {
  return <MaintenanceGate>{children}</MaintenanceGate>;
}
