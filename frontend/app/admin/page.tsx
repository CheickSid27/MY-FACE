"use client";

import Link from "next/link";
import NotificationSetup from "@/components/admin/NotificationSetup";
import PageHeader from "@/components/pro/PageHeader";
import { useWorkspace } from "@/components/pro/WorkspaceProvider";
import { CalendarIcon, ChevronRightIcon, ClockIcon, ImageIcon, ReceiptIcon, ShieldIcon, WalletIcon } from "@/components/pro/icons";
import { useAuthStore } from "@/store/auth-store";
import type { WorkspaceTodo } from "@/types/api";

const MOMENT_LABEL = { live: "Aujourd'hui", upcoming: "À venir", past: "Dernier événement" } as const;

function greeting(): string {
  const h = new Date().getHours();
  return h < 18 ? "Bonjour" : "Bonsoir";
}

function money(amount: number): string {
  return `${Math.round(amount).toLocaleString("fr-FR")} F`;
}

const TODO_STYLE: Record<string, { bg: string; fg: string; icon: React.ReactNode }> = {
  orders: { bg: "bg-[#FDE7D9]", fg: "text-[#9A3F06]", icon: <ReceiptIcon size={20} /> },
  packs: { bg: "bg-[#FDE7D9]", fg: "text-[#9A3F06]", icon: <ShieldIcon size={20} /> },
  pack_full: { bg: "bg-[#E3EAEB]", fg: "text-ink-900", icon: <ImageIcon size={20} /> },
  no_payment: { bg: "bg-[#FDE7D9]", fg: "text-[#9A3F06]", icon: <WalletIcon size={20} /> },
  deadline: { bg: "bg-[#EAE3D6]", fg: "text-ink-900", icon: <ClockIcon size={20} /> },
};

function TodoRow({ item }: { item: WorkspaceTodo }) {
  const style = TODO_STYLE[item.kind] ?? TODO_STYLE.deadline;
  return (
    <Link href={item.href} className="flex min-h-[64px] items-center gap-3.5 px-4 py-3 transition hover:bg-[#FBF8F3]">
      <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${style.bg} ${style.fg}`}>
        {style.icon}
      </span>
      <span className="min-w-0 flex-1">
        <b className="block text-[15px] text-ink-900">{item.title}</b>
        <span className="block text-[13px] text-ink-500">{item.detail}</span>
      </span>
      <ChevronRightIcon size={18} className="shrink-0 text-ink-500" />
    </Link>
  );
}

export default function ProHomePage() {
  const { summary } = useWorkspace();
  const user = useAuthStore((s) => s.user);
  const name = user?.studio_name || user?.display_name || "";
  const event = summary?.event;
  const progress = event && event.to_index > 0 ? Math.round((event.indexed / event.to_index) * 100) : 0;

  return (
    <>
      <PageHeader title={`${greeting()}${name ? `, ${name}` : ""}`} subtitle="Votre activité MYFACE" />
      <NotificationSetup onlyWhenOff />

      {!summary ? (
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="skeleton h-48 rounded-3xl lg:col-span-2" />
          <div className="skeleton h-48 rounded-3xl" />
        </div>
      ) : (
        <div className="grid gap-5 lg:grid-cols-3 lg:items-start">
          <div className="flex flex-col gap-5 lg:col-span-2">
            {event ? (
              <section className="flex flex-col gap-4 rounded-3xl bg-brand p-5 text-[#F4EFE6] lg:p-6">
                <div className="flex items-center justify-between gap-3">
                  <span className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#FFB27D]">
                    {event.moment === "live" && (
                      <span className="h-2 w-2 rounded-full bg-brand-accent shadow-[0_0_0_4px_rgba(242,106,27,0.25)]" />
                    )}
                    {MOMENT_LABEL[event.moment]}
                  </span>
                  <span className="text-[13px] text-[#A9BABD]">
                    {new Date(event.date).toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long" })}
                  </span>
                </div>
                <div>
                  <h2 className="font-pro text-xl font-semibold leading-snug lg:text-2xl">{event.name}</h2>
                  <p className="mt-1 text-[13px] text-[#A9BABD]">{event.location}</p>
                </div>
                <div className="flex flex-col gap-2">
                  <div className="flex justify-between text-[13px] text-[#A9BABD]">
                    <span>Analyse des visages</span>
                    <span className="font-semibold text-[#F4EFE6]">
                      {event.indexed} / {event.to_index} photo{event.to_index > 1 ? "s" : ""}
                      {event.photo_limit ? ` · pack de ${event.photo_limit.toLocaleString("fr-FR")}` : ""}
                    </span>
                  </div>
                  <div className="h-2 overflow-hidden rounded bg-white/15">
                    <div className="h-full rounded bg-brand-accent transition-all" style={{ width: `${progress}%` }} />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2.5 sm:max-w-md">
                  <Link
                    href={`/admin/events/${event.id}?onglet=photos&ajout=1`}
                    className="flex min-h-[46px] items-center justify-center rounded-[14px] bg-brand-accent text-sm font-bold text-brand"
                  >
                    Ajouter des photos
                  </Link>
                  <Link
                    href={`/admin/events/${event.id}`}
                    className="flex min-h-[46px] items-center justify-center rounded-[14px] border border-white/30 text-sm font-semibold"
                  >
                    Ouvrir l&apos;événement
                  </Link>
                </div>
              </section>
            ) : (
              <section className="flex flex-col items-start gap-3 rounded-3xl bg-brand p-6 text-[#F4EFE6]">
                <h2 className="font-pro text-xl font-semibold">Votre premier événement</h2>
                <p className="text-sm text-[#A9BABD]">
                  Créez-le en une minute : vous obtenez un QR code à partager, et vos invités retrouvent leurs photos
                  avec un selfie.
                </p>
                <Link href="/admin/events?nouveau=1" className="btn-accent !px-5 !py-2.5 text-sm">
                  Créer un événement
                </Link>
              </section>
            )}

            <section className="grid grid-cols-3 gap-2.5">
              <div className="flex flex-col gap-1 rounded-2xl border border-[#E6DED0] bg-white p-3.5">
                <span className="font-pro text-base font-semibold lg:text-xl">{money(summary.sales_today)}</span>
                <span className="text-xs leading-snug text-ink-500">ventes aujourd&apos;hui</span>
              </div>
              <Link
                href="/admin/ventes"
                className={`flex flex-col gap-1 rounded-2xl border p-3.5 ${
                  summary.orders_to_confirm > 0 ? "border-[#F8CBAE] bg-[#FDE7D9]" : "border-[#E6DED0] bg-white"
                }`}
              >
                <span className={`font-pro text-base font-semibold lg:text-xl ${summary.orders_to_confirm > 0 ? "text-[#9A3F06]" : ""}`}>
                  {summary.orders_to_confirm}
                </span>
                <span className="text-xs leading-snug text-ink-500">paiement{summary.orders_to_confirm > 1 ? "s" : ""} à confirmer</span>
              </Link>
              <div className="flex flex-col gap-1 rounded-2xl border border-[#E6DED0] bg-white p-3.5">
                <span className="font-pro text-base font-semibold lg:text-xl">{summary.paid_orders_today}</span>
                <span className="text-xs leading-snug text-ink-500">commande{summary.paid_orders_today > 1 ? "s" : ""} payée{summary.paid_orders_today > 1 ? "s" : ""} aujourd&apos;hui</span>
              </div>
            </section>
          </div>

          <section className="flex flex-col gap-2.5">
            <h2 className="font-pro text-[15px] font-semibold">À faire</h2>
            {summary.todo.length === 0 ? (
              <div className="rounded-3xl border border-dashed border-[#D9CFBF] bg-white p-5 text-sm text-ink-500">
                Rien à faire pour le moment. Tout est à jour.
              </div>
            ) : (
              <div className="divide-y divide-[#EFE8DC] overflow-hidden rounded-3xl border border-[#E6DED0] bg-white">
                {summary.todo.map((item, i) => (
                  <TodoRow key={`${item.kind}-${i}`} item={item} />
                ))}
              </div>
            )}
            <Link
              href="/admin/events"
              className="mt-1 flex min-h-[48px] items-center gap-3 rounded-2xl border border-[#E6DED0] bg-white px-4 text-sm font-semibold"
            >
              <CalendarIcon size={18} /> Tous mes événements ({summary.events_count})
              <ChevronRightIcon size={18} className="ml-auto text-ink-500" />
            </Link>
          </section>
        </div>
      )}
    </>
  );
}
