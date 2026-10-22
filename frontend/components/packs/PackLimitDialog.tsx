"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import PackPurchaseDialog from "@/components/packs/PackPurchaseDialog";
import { MYFACE_WHATSAPP_FALLBACK, PACK_NAMES, formatFcfa, whatsappLink } from "@/lib/packs";
import type { EventPack, PackUpgradeOption } from "@/types/api";

interface PackLimitDialogProps {
  eventId: string;
  eventName: string;
  pack: EventPack;
  onClose: () => void;
  /** Achat declare ou paye : recharger le pack. */
  onPurchased: () => void;
}

/** Boite ouverte quand le pack de l'evenement est plein et qu'on essaie
 * d'ajouter des photos : propose directement le pack superieur. */
export default function PackLimitDialog({ eventId, eventName, pack, onClose, onPurchased }: PackLimitDialogProps) {
  const [buying, setBuying] = useState<PackUpgradeOption | null>(null);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && !buying) onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, buying]);

  if (buying) {
    return (
      <PackPurchaseDialog
        eventId={eventId}
        eventName={eventName}
        option={buying}
        onClose={() => setBuying(null)}
        onDone={() => {
          setBuying(null);
          onPurchased();
          onClose();
        }}
      />
    );
  }

  const limit = pack.photo_limit?.toLocaleString("fr-FR");
  const pending = pack.pending_purchase;

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-brand/70 p-3 backdrop-blur-sm animate-fade-in sm:items-center sm:p-4"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="pack-limit-title"
        className="max-h-[92vh] w-full max-w-lg overflow-y-auto rounded-3xl bg-white p-5 shadow-elevated animate-scale-in"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-[#FDE7D9] text-2xl">📸</div>
        <h2 id="pack-limit-title" className="mb-1 font-pro text-xl font-semibold text-ink-900">
          Votre pack {pack.pack.name} est plein
        </h2>
        <p className="mb-5 text-sm text-ink-700">
          Cet événement a déjà ses {limit} photos. Pour en ajouter d&apos;autres, passez au niveau supérieur : vos
          photos et vos réglages sont gardés, vous ne payez que la différence.
        </p>

        {pending ? (
          <p className="mb-4 rounded-2xl bg-amber-50 p-4 text-sm text-amber-900">
            Votre paiement du pack {PACK_NAMES[pending.pack]} est en cours de vérification. Le pack
            s&apos;active dès qu&apos;il est confirmé, puis vous pourrez ajouter vos photos.
          </p>
        ) : pack.upgrades.length > 0 ? (
          <div className="mb-4 flex flex-col gap-3">
            {pack.upgrades.map((option) => (
              <div
                key={option.key}
                className={`flex items-center gap-3 rounded-2xl border p-4 ${
                  option.key === "pro" ? "border-brand-accent bg-[#FFF7F1]" : "border-[#E6DED0]"
                }`}
              >
                <div className="min-w-0 flex-1">
                  <p className="font-semibold text-ink-900">
                    Pack {option.name}
                    {option.key === "pro" && (
                      <span className="ml-2 rounded-full bg-brand-accent px-2 py-0.5 text-[11px] font-bold text-brand">
                        Le plus complet
                      </span>
                    )}
                  </p>
                  <p className="text-xs text-ink-500">
                    {option.photo_limit?.toLocaleString("fr-FR")} photos
                    {option.key === "pro" ? " · assistance le jour J" : " · mot de passe · filigrane"}
                  </p>
                  <p className="mt-1 text-lg font-bold text-ink-900">
                    {formatFcfa(option.amount_due)}
                    {option.amount_due < option.price && (
                      <span className="ml-1 text-xs font-normal text-ink-500 line-through">{formatFcfa(option.price)}</span>
                    )}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setBuying(option)}
                  className={`${option.key === "pro" ? "btn-accent" : "btn-primary"} shrink-0 !px-4 !py-2.5 text-sm`}
                >
                  Passer au {option.name}
                </button>
              </div>
            ))}
          </div>
        ) : (
          <p className="mb-4 rounded-2xl bg-[#F7F3EC] p-4 text-sm text-ink-700">
            Vous avez déjà le plus grand pack. Pour un événement encore plus grand, écrivez-nous :{" "}
            <a
              href={whatsappLink(MYFACE_WHATSAPP_FALLBACK, `Bonjour MYFACE, le pack de « ${eventName} » est plein.`) ?? undefined}
              target="_blank"
              rel="noreferrer"
              className="font-semibold text-[#B34A08] underline"
            >
              discuter sur WhatsApp
            </a>
            .
          </p>
        )}

        <button type="button" onClick={onClose} className="w-full py-2.5 text-sm font-semibold text-ink-500">
          Plus tard
        </button>
      </div>
    </div>,
    document.body
  );
}
