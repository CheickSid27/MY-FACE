"use client";

import Link from "next/link";
import { useWorkspace } from "@/components/pro/WorkspaceProvider";
import { BackIcon, BellIcon } from "@/components/pro/icons";

/** En-tete des ecrans MYFACE Pro : titre, retour eventuel, actions, et la
 * cloche des notifications sur telephone (sur ordinateur, elle est dans le
 * menu lateral). */
export default function PageHeader({
  title,
  subtitle,
  back,
  actions,
}: {
  title: string;
  subtitle?: React.ReactNode;
  back?: string;
  actions?: React.ReactNode;
}) {
  const { unread } = useWorkspace();
  return (
    <header className="mb-5 flex items-center gap-3 lg:mb-7">
      {back && (
        <Link
          href={back}
          aria-label="Retour"
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[14px] border border-[#E6DED0] bg-white text-ink-900"
        >
          <BackIcon />
        </Link>
      )}
      <div className="min-w-0 flex-1">
        <h1 className="truncate font-pro text-[22px] font-semibold leading-tight text-ink-900 lg:text-[26px]">{title}</h1>
        {subtitle && <div className="mt-0.5 truncate text-sm text-ink-500">{subtitle}</div>}
      </div>
      {actions}
      <Link
        href="/admin/notifications"
        aria-label={unread > 0 ? `Notifications, ${unread} non lues` : "Notifications"}
        className="relative flex h-11 w-11 shrink-0 items-center justify-center rounded-[14px] border border-[#E6DED0] bg-white text-ink-900 lg:hidden"
      >
        <BellIcon />
        {unread > 0 && (
          <span className="absolute right-2.5 top-2.5 h-2.5 w-2.5 rounded-full border-2 border-white bg-brand-accent" />
        )}
      </Link>
    </header>
  );
}
