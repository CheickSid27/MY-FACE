"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { CartIcon } from "@/components/icons";
import MethodIcon, { METHOD_LABELS } from "@/components/payments/MethodIcon";
import PaymentProgressOverlay from "@/components/payments/PaymentProgressOverlay";
import PhoneInput from "@/components/payments/PhoneInput";
import { api, ApiError } from "@/lib/api-client";
import { getCartSessionId } from "@/lib/cart";
import { getKioskToken, isKioskMode } from "@/lib/kiosk";
import { useKioskInactivityReset } from "@/lib/kiosk-inactivity-reset";
import type { CartRead, EventPaymentMethodRead, PaymentMethod } from "@/types/api";

export default function CartPage() {
  const { eventId } = useParams<{ eventId: string }>();
  const router = useRouter();

  const [cart, setCart] = useState<CartRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Numero au format international (+225...), null tant que la saisie
  // n'est pas un numero valide pour le pays choisi (voir PhoneInput).
  const [phone, setPhone] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [paymentReady, setPaymentReady] = useState(false);
  const [removingId, setRemovingId] = useState<string | null>(null);
  const [togglingPrintId, setTogglingPrintId] = useState<string | null>(null);
  const [paymentMethods, setPaymentMethods] = useState<EventPaymentMethodRead[]>([]);
  // "error" : chargement des moyens de paiement impossible. Plus aucun repli
  // silencieux dans ce cas (l'ancien repli "manual" creait des commandes que
  // personne ne pouvait ni payer ni confirmer).
  const [methodsState, setMethodsState] = useState<"loading" | "ready" | "error">("loading");
  const [selectedMethod, setSelectedMethod] = useState<PaymentMethod | null>(null);
  // Impression et especes n'ont de sens que physiquement sur la borne
  // (quelqu'un pour recevoir l'argent, une imprimante branchee a cote) :
  // jamais propose sur le telephone personnel d'un invite. Voir lib/kiosk.ts.
  const [kiosk, setKiosk] = useState(false);
  const [printUnitPrice, setPrintUnitPrice] = useState<number | null>(null);
  // Prix « photo + tirage » tout compris (borne), hors lots et remises.
  const [bundlePrice, setBundlePrice] = useState<number | null>(null);
  const [cashEnabled, setCashEnabled] = useState(false);

  const loadCart = useCallback(async () => {
    const sessionId = getCartSessionId(eventId);
    if (!sessionId) {
      setLoading(false);
      return;
    }
    try {
      const data = await api.getCart(sessionId);
      setCart(data);
    } catch {
      setCart(null);
    } finally {
      setLoading(false);
    }
  }, [eventId]);

  useEffect(() => {
    loadCart();
  }, [loadCart]);

  useEffect(() => {
    setKiosk(isKioskMode(eventId));
  }, [eventId]);

  // Desactive pendant un paiement en cours (submitting) : le serveur peut
  // prendre plusieurs secondes a repondre sans aucune interaction utilisateur
  // entre-temps, on ne veut surtout pas renvoyer le client a l'accueil au
  // milieu de son propre paiement.
  useKioskInactivityReset(eventId, kiosk && !submitting);

  const loadPaymentOptions = useCallback(() => {
    setMethodsState("loading");
    Promise.all([api.getPaymentMethods(eventId), api.getEventPublic(eventId)])
      .then(([methods, event]) => {
        setPaymentMethods(methods);
        setPrintUnitPrice(event.pricing.print_unit_price ?? null);
        setBundlePrice(event.pricing.print_bundle_price ?? null);
        setCashEnabled(event.cash_enabled);
        if (methods.length === 1) setSelectedMethod(methods[0].method);
        setMethodsState("ready");
      })
      .catch(() => setMethodsState("error"));
  }, [eventId]);

  useEffect(() => {
    loadPaymentOptions();
  }, [loadPaymentOptions]);

  async function handleRemove(itemId: string) {
    setRemovingId(itemId);
    try {
      await api.removeCartItem(itemId);
      await loadCart();
    } catch {
      setError("Impossible de retirer cette photo.");
    } finally {
      setRemovingId(null);
    }
  }

  async function handleTogglePrint(itemId: string, printRequested: boolean) {
    setTogglingPrintId(itemId);
    try {
      const updated = await api.setCartItemPrint(itemId, printRequested, getKioskToken(eventId));
      setCart(updated);
    } catch {
      setError("Impossible de mettre à jour l'impression.");
    } finally {
      setTogglingPrintId(null);
    }
  }

  const showCashOption = kiosk && cashEnabled;
  const hasBundle = bundlePrice != null && bundlePrice > 0;
  const printOffered = hasBundle || (printUnitPrice != null && printUnitPrice > 0);
  const digitalCount = cart ? cart.pricing.photo_count - cart.pricing.print_count : 0;
  const hasMethodChoice = paymentMethods.length > 0 || showCashOption;
  const noPaymentAvailable = methodsState === "ready" && !hasMethodChoice;

  async function handleCheckout(e: FormEvent) {
    e.preventDefault();
    if (!cart) return;
    if (!selectedMethod) {
      setError("Choisissez un moyen de paiement.");
      return;
    }
    if (!phone) {
      setError("Saisissez un numéro de téléphone valide.");
      return;
    }
    setSubmitting(true);
    setPaymentReady(false);
    setError(null);
    try {
      const result = await api.initPayment(cart.session_id, phone, selectedMethod, getKioskToken(eventId));
      setPaymentReady(true);
      // Laisse la barre de progression atteindre 100% a l'ecran avant de
      // quitter la page, sinon le saut a 100% n'est jamais visible.
      await new Promise((resolve) => setTimeout(resolve, 300));
      router.push(`/event/${eventId}/pay/${result.order_id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de l'initialisation du paiement.");
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-surface">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
      </main>
    );
  }

  if (!cart || cart.items.length === 0) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-5 bg-surface px-6 text-center animate-fade-in">
        <CartIcon className="text-4xl text-ink-500" />
        <p className="text-lg text-ink-700">Votre panier est vide.</p>
        <button
          type="button"
          onClick={() => router.push(`/event/${eventId}/gallery`)}
          className="btn-primary"
        >
          Parcourir la galerie
        </button>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen flex-col bg-gradient-to-b from-surface-alt to-surface">
      <header className="glass-strong sticky top-0 z-20 flex items-center justify-between px-4 py-3.5">
        <button
          type="button"
          onClick={() => router.push(`/event/${eventId}/gallery`)}
          className="text-sm font-medium text-ink-500 transition hover:text-brand"
        >
          &larr; Continuer mes achats
        </button>
        <h1 className="text-sm font-semibold">Mon panier</h1>
        <div className="w-32" />
      </header>

      <div className="mx-auto w-full max-w-2xl flex-1 p-4 animate-fade-in">
        <div className="grid grid-cols-3 gap-3 sm:grid-cols-4">
          {cart.items.map((item) => (
            <div key={item.id} className="group relative overflow-hidden rounded-xl shadow-soft">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={item.photo.thumbnail_url}
                alt={item.photo.original_filename}
                className="aspect-square w-full object-cover"
              />
              <button
                type="button"
                disabled={removingId === item.id}
                onClick={() => handleRemove(item.id)}
                className="glass-pill absolute right-1.5 top-1.5 flex h-6 w-6 items-center justify-center text-xs text-white transition hover:bg-white/30 disabled:opacity-50"
              >
                &times;
              </button>
              {/* Impression papier : uniquement propose sur la borne (une
                  imprimante physique n'existe pas sur le téléphone d'un
                  invité), et seulement si l'organisateur a fixe un prix. */}
              {kiosk && printOffered && (
                <button
                  type="button"
                  disabled={togglingPrintId === item.id}
                  onClick={() => handleTogglePrint(item.id, !item.print_requested)}
                  className={`glass-pill absolute inset-x-1.5 bottom-1.5 flex items-center justify-center gap-1 rounded-lg px-1.5 py-1 text-[11px] font-semibold transition-all duration-150 disabled:opacity-50 ${
                    item.print_requested ? "!bg-brand-accent !text-brand" : "text-white"
                  }`}
                >
                  {item.print_requested
                    ? "✓ Imprimer"
                    : hasBundle
                      ? `+ Imprimer (${bundlePrice!.toLocaleString("fr-FR")} le tout)`
                      : `+ Imprimer (+${printUnitPrice!.toLocaleString("fr-FR")})`}
                </button>
              )}
            </div>
          ))}
        </div>

        {kiosk && hasBundle && (
          <p className="mt-4 rounded-xl bg-brand-accent/10 px-4 py-3 text-center text-sm text-ink-700">
            Photo + tirage 10×15 : <strong>{bundlePrice!.toLocaleString("fr-FR")} {cart.pricing.currency}</strong> la
            photo, tout compris. Ce prix ne change pas avec les lots et remises.
          </p>
        )}

        <div className="glass mt-6 rounded-2xl p-5">
          <div className="flex justify-between text-sm text-ink-500">
            <span>
              {cart.pricing.bundle
                ? `${digitalCount} photo${digitalCount > 1 ? "s" : ""} numérique${digitalCount > 1 ? "s" : ""}`
                : `${cart.pricing.photo_count} photo${cart.pricing.photo_count > 1 ? "s" : ""}`}
            </span>
            <span>
              {cart.pricing.subtotal.toLocaleString("fr-FR")} {cart.pricing.currency}
            </span>
          </div>
          {cart.pricing.discount_amount > 0 && (
            <div className="mt-1 flex justify-between text-sm text-emerald-600">
              <span>Remise ({cart.pricing.discount_percent}%)</span>
              <span>
                -{cart.pricing.discount_amount.toLocaleString("fr-FR")} {cart.pricing.currency}
              </span>
            </div>
          )}
          {cart.pricing.print_count > 0 && (
            <div className="mt-1 flex justify-between text-sm text-ink-500">
              <span>
                {cart.pricing.bundle
                  ? `Photo + tirage (${cart.pricing.print_count})`
                  : `Impression (${cart.pricing.print_count} photo${cart.pricing.print_count > 1 ? "s" : ""})`}
              </span>
              <span>
                +{cart.pricing.print_total.toLocaleString("fr-FR")} {cart.pricing.currency}
              </span>
            </div>
          )}
          <div className="mt-3 flex items-baseline justify-between border-t border-ink-900/5 pt-3">
            <span className="font-semibold text-ink-900">Total</span>
            <span className="text-2xl font-bold text-brand">
              {cart.pricing.total.toLocaleString("fr-FR")}{" "}
              <span className="text-base font-medium text-ink-500">{cart.pricing.currency}</span>
            </span>
          </div>
        </div>

        {methodsState === "error" && (
          <div className="glass mt-6 flex flex-col items-center gap-3 rounded-2xl p-5 text-center">
            <p className="text-sm text-ink-700">
              Impossible de charger les moyens de paiement. Vérifiez votre connexion.
            </p>
            <button type="button" onClick={loadPaymentOptions} className="btn-ghost !px-5 !py-2.5 text-sm">
              Réessayer
            </button>
          </div>
        )}

        {noPaymentAvailable && (
          <div className="glass mt-6 rounded-2xl p-5 text-center text-sm text-ink-700">
            Le paiement n&apos;est pas encore disponible pour cet événement. Rapprochez-vous de
            l&apos;organisateur.
          </div>
        )}

        {methodsState === "ready" && hasMethodChoice && (
          <form onSubmit={handleCheckout} className="glass mt-6 rounded-2xl p-5">
            <div className="mb-4">
              <label className="mb-1.5 block text-sm font-medium text-ink-700">Moyen de paiement</label>
              <div className="grid grid-cols-2 gap-2">
                {paymentMethods.map((pm) => {
                  const isSelected = selectedMethod === pm.method;
                  return (
                    <button
                      key={pm.method}
                      type="button"
                      onClick={() => setSelectedMethod(pm.method)}
                      className={`flex items-center gap-2 rounded-xl border-2 px-3 py-2.5 text-sm font-semibold transition-all duration-150 ${
                        isSelected
                          ? "border-brand-accent bg-brand-accent/10 text-brand"
                          : "border-ink-900/10 bg-white/60 text-ink-700 hover:border-ink-900/20"
                      }`}
                    >
                      <MethodIcon method={pm.method} size={22} /> {METHOD_LABELS[pm.method]}
                    </button>
                  );
                })}
                {/* Especes : uniquement sur la borne, jamais propose sur le
                    téléphone personnel d'un invité (personne physiquement la
                    pour recevoir l'argent), voir Event.cash_enabled. */}
                {showCashOption && (
                  <button
                    type="button"
                    onClick={() => setSelectedMethod("cash")}
                    className={`flex items-center gap-2 rounded-xl border-2 px-3 py-2.5 text-sm font-semibold transition-all duration-150 ${
                      selectedMethod === "cash"
                        ? "border-brand-accent bg-brand-accent/10 text-brand"
                        : "border-ink-900/10 bg-white/60 text-ink-700 hover:border-ink-900/20"
                    }`}
                  >
                    <MethodIcon method="cash" size={22} /> {METHOD_LABELS.cash}
                  </button>
                )}
              </div>
            </div>
            <label className="mb-1.5 block text-sm font-medium text-ink-700">
              Numéro de téléphone{" "}
              <span className="font-normal text-ink-500">(pour recevoir vos photos par SMS)</span>
            </label>
            <PhoneInput onChange={setPhone} disabled={submitting} className="mb-4" />
            {error && <p className="mb-3 text-sm text-red-600">{error}</p>}
            <button type="submit" disabled={submitting || !phone || !selectedMethod} className="btn-accent w-full">
              {submitting ? "Initialisation..." : "Continuer vers le paiement"}
            </button>
          </form>
        )}
      </div>

      {submitting && <PaymentProgressOverlay done={paymentReady} />}
    </main>
  );
}
