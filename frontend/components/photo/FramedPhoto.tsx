import type { ReactNode } from "react";

interface FramedPhotoProps {
  /** Texte affiche sous la photo, style photobooth (ex: "LE FABULEUX MARIAGE
   * D'ANTHONY & SOPHIA"). Vide/absent = pas de cadre (opt-in par evenement,
   * voir Event.frame_caption cote backend) : le contenu est alors rendu tel
   * quel, sans wrapper. */
  caption?: string | null;
  children: ReactNode;
  className?: string;
}

export default function FramedPhoto({ caption, children, className = "" }: FramedPhotoProps) {
  if (!caption) return <>{children}</>;

  return (
    <div className={`inline-flex flex-col items-center bg-[#faf7f2] p-3 pb-5 shadow-elevated sm:p-4 sm:pb-6 ${className}`}>
      <div className="relative overflow-hidden border border-ink-900/10">{children}</div>
      <p className="mt-4 max-w-xs font-display text-sm uppercase tracking-[0.22em] text-ink-900 sm:max-w-sm sm:text-base">
        {caption}
      </p>
    </div>
  );
}
