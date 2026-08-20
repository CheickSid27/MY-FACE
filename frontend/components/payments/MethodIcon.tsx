import type { PaymentMethod } from "@/types/api";

const LOGO_SRC: Partial<Record<PaymentMethod, string>> = {
  wave: "/logos/wave.svg",
  orange_money: "/logos/orange-money.svg",
  mtn_money: "/logos/mtn-money.svg",
};

export const METHOD_LABELS: Record<PaymentMethod, string> = {
  wave: "Wave",
  orange_money: "Orange Money",
  mtn_money: "MTN Money",
  moov_money: "Moov Money",
  manual: "Test",
};

interface MethodIconProps {
  method: PaymentMethod;
  size?: number;
  className?: string;
}

export default function MethodIcon({ method, size = 22, className = "" }: MethodIconProps) {
  const src = LOGO_SRC[method];

  if (src) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={src}
        alt={METHOD_LABELS[method]}
        width={size}
        height={size}
        className={`inline-block shrink-0 rounded-md object-contain ${className}`}
      />
    );
  }

  // Pas encore de logo officiel fourni pour ce moyen (ex. Moov Money) :
  // monogramme sobre en attendant, jamais d'emoji.
  return (
    <span
      style={{ width: size, height: size }}
      className={`inline-flex shrink-0 items-center justify-center rounded-md bg-ink-900/10 text-[0.6em] font-bold text-ink-700 ${className}`}
    >
      {METHOD_LABELS[method].slice(0, 2).toUpperCase()}
    </span>
  );
}
