"use client";

import { FormEvent, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import PhoneInput from "@/components/payments/PhoneInput";
import { api, ApiError } from "@/lib/api-client";
import {
  MYFACE_WHATSAPP_FALLBACK,
  PACK_PAYMENT_METHODS,
  formatFcfa,
  whatsappLink,
} from "@/lib/packs";
import type { PackPaymentInfo, PackPaymentMethod, PackUpgradeOption } from "@/types/api";

interface PackPurchaseDialogProps {
  eventId: string;
  eventName: string;
  option: PackUpgradeOption;
  onClose: () => void;
  onDone: () => void;
}

/** Achat d'un pack : le photographe envoie le montant au numero Mobile Money
 * de MYFACE, puis declare la transaction. Le pack est active des que MYFACE
 * a verifie la reception (validation dans /admin/packs). */
export default function PackPurchaseDialog({ eventId, eventName, option, onClose, onDone }: PackPurchaseDialogProps) {
  const [info, setInfo] = useState<PackPaymentInfo | null>(null);
  const [method, setMethod] = useState<PackPaymentMethod | "">("");
  const [payerPhone, setPayerPhone] = useState<string | null>(null);
  const [reference, setReference] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  useEffect(() => {
    api
      .getPackPaymentInfo()
      .then((data) => {
        setInfo(data);
        const first = PACK_PAYMENT_METHODS.find((m) => data[m.key]);
        if (first) setMethod(first.key);
      })
      .catch(() => setInfo({}));
  }, []);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const configured = PACK_PAYMENT_METHODS.filter((m) => info?.[m.key]);
  const whatsapp = whatsappLink(
    info?.whatsapp || MYFACE_WHATSAPP_FALLBACK,
    `Bonjour MYFACE, je souhaite payer le pack ${option.name} (${formatFcfa(option.amount_due)}) pour « ${eventName} ».`
  );

  async function copy(value: string) {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(value);
      setTimeout(() => setCopied(null), 1500);
    } catch {
      // presse-papiers indisponible : le numero reste lisible a l'ecran
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!method) {
      setError("Choisissez le moyen de paiement utilisé.");
      return;
    }
    if (!payerPhone) {
      setError("Indiquez le numéro qui a payé.");
      return;
    }
    setSending(true);
    setError(null);
    try {
      await api.createPackPurchase(eventId, {
        pack: option.key,
        payment_method: method,
        payer_phone: payerPhone,
        transaction_ref: reference.trim(),
      });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Envoi impossible, réessayez.");
    } finally {
      setSending(false);
    }
  }

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-brand/70 p-4 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
    >
      <div
        className="glass-strong max-h-[92vh] w-full max-w-lg overflow-y-auto rounded-2xl p-5 shadow-elevated animate-scale-in"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-brand-accent">Pack {option.name}</p>
            <h2 className="text-xl font-bold text-ink-900">{formatFcfa(option.amount_due)}</h2>
            <p className="text-xs text-ink-500">
              {option.photo_limit?.toLocaleString("fr-FR")} photos pour « {eventName} » · paiement unique, sans abonnement
              {option.amount_due < option.price && " · vous ne payez que la différence avec votre pack actuel"}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Fermer"
            className="glass-pill flex h-8 w-8 shrink-0 items-center justify-center text-ink-500 transition hover:text-ink-900"
          >
            &times;
          </button>
        </div>

        <div className="mb-4 rounded-xl bg-white/70 p-4">
          <p className="mb-2 text-sm font-semibold text-ink-900">1. Envoyez {formatFcfa(option.amount_due)} à MYFACE</p>
          {info === null && <p className="text-xs text-ink-500">Chargement des numéros...</p>}
          {info !== null && configured.length === 0 && (
            <p className="text-xs text-ink-700">
              Les numéros de paiement ne sont pas encore affichés ici : écrivez-nous sur WhatsApp, nous vous
              les envoyons tout de suite.
            </p>
          )}
          {configured.length > 0 && (
            <ul className="flex flex-col gap-2">
              {configured.map((m) => (
                <li key={m.key} className="flex items-center justify-between gap-3 rounded-lg bg-surface-alt px-3 py-2">
                  <span className="text-sm text-ink-700">{m.label}</span>
                  <span className="flex items-center gap-2">
                    <code className="text-sm font-semibold text-ink-900">{info?.[m.key]}</code>
                    <button
                      type="button"
                      onClick={() => copy(String(info?.[m.key]))}
                      className="text-xs font-semibold text-brand hover:underline"
                    >
                      {copied === info?.[m.key] ? "Copié" : "Copier"}
                    </button>
                  </span>
                </li>
              ))}
            </ul>
          )}
          {info?.instructions && <p className="mt-2 text-xs text-ink-500">{info.instructions}</p>}
          {whatsapp && (
            <a
              href={whatsapp}
              target="_blank"
              rel="noreferrer"
              className="mt-3 inline-block text-xs font-semibold text-emerald-700 hover:underline"
            >
              Une question ? Discuter sur WhatsApp
            </a>
          )}
        </div>

        <form onSubmit={handleSubmit} className="rounded-xl bg-white/70 p-4">
          <p className="mb-3 text-sm font-semibold text-ink-900">2. Déclarez votre paiement</p>

          <label className="mb-1 block text-xs font-medium text-ink-700">Moyen utilisé</label>
          <select
            value={method}
            onChange={(e) => setMethod(e.target.value as PackPaymentMethod)}
            required
            className="mb-3 w-full rounded-xl border border-ink-900/10 bg-white px-3 py-2.5 text-sm outline-none focus:border-brand-accent"
          >
            <option value="" disabled>
              Choisir...
            </option>
            {PACK_PAYMENT_METHODS.map((m) => (
              <option key={m.key} value={m.key}>
                {m.label}
              </option>
            ))}
          </select>

          <label className="mb-1 block text-xs font-medium text-ink-700">Numéro qui a payé</label>
          <PhoneInput onChange={setPayerPhone} disabled={sending} className="mb-3" />

          <label className="mb-1 block text-xs font-medium text-ink-700">Référence de la transaction</label>
          <input
            required
            minLength={3}
            maxLength={80}
            value={reference}
            onChange={(e) => setReference(e.target.value)}
            placeholder="Ex : l'identifiant affiché dans le SMS de confirmation"
            className="mb-3 w-full rounded-xl border border-ink-900/10 bg-white px-3 py-2.5 text-sm outline-none focus:border-brand-accent"
          />

          {error && <p className="mb-3 text-sm text-red-600">{error}</p>}

          <button type="submit" disabled={sending} className="btn-accent w-full !py-3 text-sm disabled:opacity-50">
            {sending ? "Envoi..." : "J'ai payé, activer mon pack"}
          </button>
          <p className="mt-2 text-center text-[11px] text-ink-500">
            Le pack est activé dès que MYFACE a vérifié la réception du paiement.
          </p>
        </form>
      </div>
    </div>,
    document.body
  );
}
