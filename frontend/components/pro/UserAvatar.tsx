"use client";

import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Adresse de la photo de profil (versionnee : change a chaque nouvelle photo). */
export function avatarUrl(userId: string, version: string | null | undefined): string | null {
  return version ? `${API_URL}/auth/avatars/${userId}?v=${encodeURIComponent(version)}` : null;
}

/** Photo de profil ronde, ou les initiales si aucune photo. */
export default function UserAvatar({
  userId,
  version,
  name,
  size = 40,
  className = "",
}: {
  userId: string;
  version: string | null | undefined;
  name: string;
  size?: number;
  className?: string;
}) {
  const url = avatarUrl(userId, version);
  const [broken, setBroken] = useState(false);
  const initials = name.trim().slice(0, 2).toUpperCase() || "MF";
  const style = { width: size, height: size, borderRadius: Math.round(size * 0.32) };

  if (url && !broken) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={url}
        alt={`Photo de profil de ${name}`}
        width={size}
        height={size}
        style={style}
        onError={() => setBroken(true)}
        className={`shrink-0 object-cover ${className}`}
      />
    );
  }
  return (
    <span
      style={{ ...style, fontSize: Math.max(11, Math.round(size * 0.32)) }}
      className={`flex shrink-0 items-center justify-center bg-brand font-pro font-bold text-brand-accent ${className}`}
      aria-hidden="true"
    >
      {initials}
    </span>
  );
}
