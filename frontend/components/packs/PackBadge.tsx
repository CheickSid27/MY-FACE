import { PACK_BADGE_CLASSES, PACK_NAMES } from "@/lib/packs";
import type { PackKey } from "@/types/api";

export default function PackBadge({ pack, className = "" }: { pack: PackKey; className?: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold ${PACK_BADGE_CLASSES[pack] ?? PACK_BADGE_CLASSES.decouverte} ${className}`}
    >
      Pack {PACK_NAMES[pack] ?? pack}
    </span>
  );
}
