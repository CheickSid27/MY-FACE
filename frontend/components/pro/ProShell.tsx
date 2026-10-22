"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import MyfaceLogo from "@/components/brand/Logo";
import UserAvatar from "@/components/pro/UserAvatar";
import { useWorkspace } from "@/components/pro/WorkspaceProvider";
import {
  BellIcon,
  CalendarIcon,
  HomeIcon,
  ImageIcon,
  LogoutIcon,
  PlusIcon,
  ReceiptIcon,
  SettingsIcon,
  ShieldIcon,
  UserIcon,
  UsersIcon,
} from "@/components/pro/icons";
import { useAuthStore } from "@/store/auth-store";

/** Structure de MYFACE Pro : barre de navigation en bas sur telephone et
 * tablette, menu lateral a gauche sur ordinateur. Le bouton central « + »
 * ajoute des photos a l'evenement du moment ou en cree un. */

type NavKey = "accueil" | "evenements" | "ventes" | "notifications" | "compte";

function activeKey(pathname: string): NavKey {
  if (pathname === "/admin") return "accueil";
  if (pathname.startsWith("/admin/events")) return "evenements";
  if (pathname.startsWith("/admin/ventes")) return "ventes";
  if (pathname.startsWith("/admin/notifications")) return "notifications";
  return "compte";
}

function Badge({ count }: { count: number }) {
  if (count <= 0) return null;
  return (
    <span className="absolute -right-2 -top-1.5 flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-brand-accent px-1 text-[10px] font-bold text-brand">
      {count > 99 ? "99+" : count}
    </span>
  );
}

function AddSheet({ onClose }: { onClose: () => void }) {
  const { summary } = useWorkspace();
  const event = summary?.event;
  const item =
    "flex min-h-[56px] items-center gap-4 rounded-2xl border border-[#E6DED0] bg-white px-4 py-3 text-left transition hover:border-brand-accent/50";
  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-brand/50 backdrop-blur-sm animate-fade-in sm:items-center"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-label="Ajouter"
        className="w-full max-w-md rounded-t-3xl bg-[#F7F3EC] p-5 pb-8 shadow-elevated animate-scale-in sm:rounded-3xl sm:pb-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mx-auto mb-4 h-1.5 w-10 rounded-full bg-ink-900/15 sm:hidden" />
        <h2 className="mb-4 font-pro text-base font-semibold text-ink-900">Que voulez-vous faire ?</h2>
        <div className="flex flex-col gap-2.5">
          {event && (
            <Link href={`/admin/events/${event.id}?onglet=photos&ajout=1`} onClick={onClose} className={item}>
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-accent text-brand">
                <ImageIcon size={20} />
              </span>
              <span className="min-w-0">
                <b className="block text-[15px] text-ink-900">Ajouter des photos</b>
                <span className="block truncate text-[13px] text-ink-500">à « {event.name} »</span>
              </span>
            </Link>
          )}
          <Link href="/admin/events?nouveau=1" onClick={onClose} className={item}>
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand text-white">
              <PlusIcon size={20} />
            </span>
            <span>
              <b className="block text-[15px] text-ink-900">Créer un événement</b>
              <span className="block text-[13px] text-ink-500">QR code et page invités en une minute</span>
            </span>
          </Link>
          <Link href="/admin/events" onClick={onClose} className={item}>
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#EAE3D6] text-ink-900">
              <CalendarIcon size={20} />
            </span>
            <span>
              <b className="block text-[15px] text-ink-900">Choisir un autre événement</b>
              <span className="block text-[13px] text-ink-500">Pour y ajouter des photos</span>
            </span>
          </Link>
        </div>
        <button type="button" onClick={onClose} className="mt-4 w-full rounded-2xl py-3 text-sm font-semibold text-ink-500">
          Fermer
        </button>
      </div>
    </div>
  );
}

export default function ProShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const current = activeKey(pathname);
  const { summary, unread } = useWorkspace();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const isAdmin = user?.role === "admin";
  const [adding, setAdding] = useState(false);
  const toConfirm = summary?.orders_to_confirm ?? 0;
  const name = user?.studio_name || user?.display_name || user?.email || "";

  const side = (key: NavKey) =>
    `flex min-h-[44px] items-center gap-3 rounded-xl px-3 text-[15px] font-semibold transition ${
      current === key ? "bg-brand text-white" : "text-ink-700 hover:bg-[#EFE8DC]"
    }`;
  const sideSmall = (href: string) =>
    `flex min-h-[40px] items-center gap-3 rounded-xl px-3 text-sm font-medium transition ${
      pathname.startsWith(href) ? "bg-[#EFE8DC] text-ink-900" : "text-ink-500 hover:bg-[#EFE8DC] hover:text-ink-900"
    }`;
  const tab = (key: NavKey) =>
    `relative flex min-h-[48px] min-w-[56px] flex-col items-center justify-center gap-1 text-[11px] font-semibold ${
      current === key ? "text-[#B34A08]" : "text-ink-500"
    }`;

  return (
    <div className="min-h-screen bg-[#F7F3EC] text-ink-900">
      {/* Ordinateur : menu lateral */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-[#E6DED0] bg-white/80 px-4 py-6 backdrop-blur lg:flex">
        <Link href="/admin" className="mb-7 flex items-center gap-2.5 px-2">
          <MyfaceLogo size={34} />
          <span className="font-pro text-[15px] font-bold tracking-wide">
            MY<span className="text-brand-accent">FACE</span> <span className="font-semibold text-ink-500">Pro</span>
          </span>
        </Link>
        <button
          type="button"
          onClick={() => setAdding(true)}
          className="mb-6 flex min-h-[46px] items-center justify-center gap-2 rounded-xl bg-brand-accent text-sm font-bold text-brand shadow-[0_8px_20px_rgba(242,106,27,0.3)] transition hover:bg-brand-accent-light"
        >
          <PlusIcon size={18} /> Ajouter
        </button>
        <nav className="flex flex-col gap-1" aria-label="Navigation principale">
          <Link href="/admin" className={side("accueil")} aria-current={current === "accueil" ? "page" : undefined}>
            <HomeIcon size={20} /> Accueil
          </Link>
          <Link href="/admin/events" className={side("evenements")}>
            <CalendarIcon size={20} /> Événements
          </Link>
          <Link href="/admin/ventes" className={side("ventes")}>
            <ReceiptIcon size={20} /> Ventes
            {toConfirm > 0 && (
              <span className="ml-auto rounded-full bg-brand-accent px-2 py-0.5 text-[11px] font-bold text-brand">
                {toConfirm}
              </span>
            )}
          </Link>
          <Link href="/admin/notifications" className={side("notifications")}>
            <BellIcon size={20} /> Notifications
            {unread > 0 && (
              <span className="ml-auto rounded-full bg-brand-accent px-2 py-0.5 text-[11px] font-bold text-brand">
                {unread}
              </span>
            )}
          </Link>
          <Link href="/admin/account" className={side("compte")}>
            <UserIcon size={20} /> Compte
          </Link>
        </nav>
        {isAdmin && (
          <div className="mt-6 flex flex-col gap-0.5">
            <p className="mb-1 px-3 text-[11px] font-bold uppercase tracking-wider text-ink-500">Équipe MYFACE</p>
            <Link href="/admin/packs" className={sideSmall("/admin/packs")}>
              <ShieldIcon size={18} /> Packs à valider
            </Link>
            <Link href="/admin/users" className={sideSmall("/admin/users")}>
              <UsersIcon size={18} /> Photographes
            </Link>
            <Link href="/admin/settings" className={sideSmall("/admin/settings")}>
              <SettingsIcon size={18} /> Réglages
            </Link>
          </div>
        )}
        <div className="mt-auto flex items-center gap-3 rounded-xl border border-[#E6DED0] bg-white p-3">
          {user && <UserAvatar userId={user.id} version={user.avatar_version} name={name} size={36} />}
          <span className="min-w-0 flex-1 truncate text-sm font-semibold">{name}</span>
          <button type="button" onClick={logout} aria-label="Se déconnecter" className="text-ink-500 hover:text-ink-900">
            <LogoutIcon size={18} />
          </button>
        </div>
      </aside>

      <div className="lg:pl-64">
        <div className="mx-auto w-full max-w-6xl px-4 pb-32 pt-5 sm:px-6 lg:px-10 lg:pb-12 lg:pt-8">{children}</div>
      </div>

      {/* Telephone et tablette : barre du bas */}
      <nav
        className="fixed inset-x-3 bottom-3 z-40 flex h-[68px] items-center justify-around rounded-3xl bg-white px-1.5 shadow-[0_10px_30px_rgba(14,36,41,0.16)] lg:hidden"
        style={{ marginBottom: "env(safe-area-inset-bottom)" }}
        aria-label="Navigation principale"
      >
        <Link href="/admin" className={tab("accueil")}>
          <HomeIcon />
          Accueil
        </Link>
        <Link href="/admin/events" className={tab("evenements")}>
          <CalendarIcon />
          Événements
        </Link>
        <button
          type="button"
          onClick={() => setAdding(true)}
          aria-label="Ajouter des photos ou un événement"
          className="-mt-9 flex h-14 w-14 items-center justify-center rounded-[18px] bg-brand-accent text-white shadow-[0_10px_22px_rgba(242,106,27,0.42)]"
        >
          <PlusIcon size={26} />
        </button>
        <Link href="/admin/ventes" className={tab("ventes")}>
          <span className="relative">
            <ReceiptIcon />
            <Badge count={toConfirm} />
          </span>
          Ventes
        </Link>
        <Link href="/admin/account" className={tab("compte")}>
          <UserIcon />
          Compte
        </Link>
      </nav>

      {adding && <AddSheet onClose={() => setAdding(false)} />}
    </div>
  );
}
