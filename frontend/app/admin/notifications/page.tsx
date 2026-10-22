"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import NotificationSetup from "@/components/admin/NotificationSetup";
import PageHeader from "@/components/pro/PageHeader";
import { useWorkspace } from "@/components/pro/WorkspaceProvider";
import { BellIcon, ClockIcon, FacesIcon, ReceiptIcon, ShieldIcon, UserIcon } from "@/components/pro/icons";
import type { ActivityItem } from "@/types/api";

const STYLE: Record<string, { bg: string; fg: string; icon: React.ReactNode }> = {
  order_waiting: { bg: "bg-[#FDE7D9]", fg: "text-[#9A3F06]", icon: <ReceiptIcon size={20} /> },
  order_paid: { bg: "bg-[#E3EAEB]", fg: "text-ink-900", icon: <ReceiptIcon size={20} /> },
  pack_paid: { bg: "bg-[#EAE3D6]", fg: "text-ink-900", icon: <ShieldIcon size={20} /> },
  pack_rejected: { bg: "bg-red-50", fg: "text-red-700", icon: <ShieldIcon size={20} /> },
  pack_pending: { bg: "bg-[#FDE7D9]", fg: "text-[#9A3F06]", icon: <ShieldIcon size={20} /> },
  deadline: { bg: "bg-[#EAE3D6]", fg: "text-ink-900", icon: <ClockIcon size={20} /> },
  new_photographer: { bg: "bg-[#E3EAEB]", fg: "text-ink-900", icon: <UserIcon size={20} /> },
};

function when(iso: string): string {
  const d = new Date(iso);
  const minutes = Math.round((Date.now() - d.getTime()) / 60000);
  if (minutes < 1) return "à l'instant";
  if (minutes < 60) return `il y a ${minutes} min`;
  if (minutes < 24 * 60) return `il y a ${Math.round(minutes / 60)} h`;
  return d.toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "short" });
}

function group(items: ActivityItem[]): { title: string; items: ActivityItem[] }[] {
  const startOfDay = new Date();
  startOfDay.setHours(0, 0, 0, 0);
  const today = items.filter((i) => new Date(i.at) >= startOfDay);
  const earlier = items.filter((i) => new Date(i.at) < startOfDay);
  return [
    { title: "Aujourd'hui", items: today },
    { title: "Plus tôt", items: earlier },
  ].filter((g) => g.items.length > 0);
}

export default function ProNotificationsPage() {
  const { activity, seenAt, markAllSeen } = useWorkspace();
  // Ce qui etait non lu a l'ouverture reste en evidence pendant la visite,
  // la pastille de la cloche, elle, disparait tout de suite.
  const seenAtOpen = useRef<number | null>(null);
  if (seenAtOpen.current === null && activity) seenAtOpen.current = seenAt ? new Date(seenAt).getTime() : 0;

  useEffect(() => {
    if (activity) markAllSeen();
  }, [activity, markAllSeen]);

  return (
    <>
      <PageHeader title="Notifications" back="/admin" />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px] lg:items-start">
        <div>
          {!activity && <div className="skeleton h-48 rounded-3xl" />}
          {activity && activity.length === 0 && (
            <div className="flex flex-col items-center gap-2 rounded-3xl border border-dashed border-[#D9CFBF] bg-white p-8 text-center text-sm text-ink-500">
              <BellIcon size={28} />
              Rien de nouveau ces deux dernières semaines.
            </div>
          )}
          {activity &&
            group(activity).map((g) => (
              <section key={g.title} className="mb-5">
                <h2 className="mb-2 text-[13px] font-bold uppercase tracking-wider text-ink-500">{g.title}</h2>
                <div className="divide-y divide-[#EFE8DC] overflow-hidden rounded-3xl border border-[#E6DED0] bg-white">
                  {g.items.map((item) => {
                    const style = STYLE[item.kind] ?? { bg: "bg-[#E3EAEB]", fg: "text-ink-900", icon: <FacesIcon size={20} /> };
                    const unread = seenAtOpen.current !== null && new Date(item.at).getTime() > seenAtOpen.current;
                    return (
                      <Link
                        key={item.id}
                        href={item.href}
                        className={`flex min-h-[64px] items-start gap-3 px-4 py-3.5 transition hover:bg-[#FBF8F3] ${unread ? "bg-[#FFF8F2]" : ""}`}
                      >
                        <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${style.bg} ${style.fg}`}>
                          {style.icon}
                        </span>
                        <span className="min-w-0 flex-1">
                          <b className="block text-[15px] text-ink-900">{item.title}</b>
                          <span className="block text-sm text-[#3F5156]">{item.body}</span>
                          <span className="block text-xs text-ink-500">{when(item.at)}</span>
                        </span>
                        {unread && <span className="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full bg-brand-accent" aria-label="Non lue" />}
                      </Link>
                    );
                  })}
                </div>
              </section>
            ))}
        </div>

        <aside className="flex flex-col gap-3">
          <h2 className="text-[13px] font-bold uppercase tracking-wider text-ink-500">Sur ce téléphone</h2>
          <NotificationSetup />
          <p className="text-xs text-ink-500">
            Activez les notifications pour être prévenu d&apos;un paiement à confirmer même quand MYFACE Pro est fermé.
            Sur iPhone, installez d&apos;abord l&apos;application sur l&apos;écran d&apos;accueil (Partager, puis « Sur
            l&apos;écran d&apos;accueil »).
          </p>
        </aside>
      </div>
    </>
  );
}
