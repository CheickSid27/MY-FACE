"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { CartIcon } from "@/components/icons";
import MethodIcon, { METHOD_LABELS } from "@/components/payments/MethodIcon";
import { api, ApiError } from "@/lib/api-client";
import { getCartSessionId } from "@/lib/cart";
import type { CartRead, EventPaymentMethodRead, PaymentMethod } from "@/types/api";

export default function CartPage() {
  const { eventId } = useParams<{ eventId: string }>();
  const router = useRouter();

  const [cart, setCart] = useState<CartRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [phone, setPhone] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [removingId, setRemovingId] = useState<string | null>(null);
  const [paymentMethods, setPaymentMethods] = useState<EventPaymentMethodRead[]>([]);
  const [selectedMethod, setSelectedMethod] = useState<PaymentMethod | null>(null);

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
    api
      .getPaymentMethods(eventId)
      .then((methods) => {
        setPaymentMethods(methods);
        if (methods.length === 1) setSelectedMethod(methods[0].method);
      })
      .catch(() => {
        // pas de moyen de paiement configure : on garde le flux de test existant
      });
  }, [eventId]);

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

  async function handleCheckout(e: FormEvent) {
    e.preventDefault();
    if (!cart) return;
    if (paymentMethods.length > 0 && !selectedMethod) {
      setError("Choisissez un moyen de paiement.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const result = await api.initPayment(cart.session_id, phone, selectedMethod ?? undefined);
      router.push(`/event/${eventId}/pay/${result.order_id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de l'initialisation du paiement.");
    } finally {
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
            </div>
          ))}
        </div>

        <div className="glass mt-6 rounded-2xl p-5">
          <div className="flex justify-between text-sm text-ink-500">
            <span>{cart.pricing.photo_count} photo(s)</span>
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
          <div className="mt-3 flex items-baseline justify-between border-t border-ink-900/5 pt-3">
            <span className="font-semibold text-ink-900">Total</span>
            <span className="text-2xl font-bold text-brand">
              {cart.pricing.total.toLocaleString("fr-FR")}{" "}
              <span className="text-base font-medium text-ink-500">{cart.pricing.currency}</span>
            </span>
          </div>
        </div>

        <form onSubmit={handleCheckout} className="glass mt-6 rounded-2xl p-5">
          {paymentMethods.length > 0 && (
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
              </div>
            </div>
          )}
          <label className="mb-1.5 block text-sm font-medium text-ink-700">Numero de telephone</label>
          <input
            type="tel"
            required
            placeholder="+225 07 00 00 00 00"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            className="mb-4 w-full rounded-xl border border-ink-900/10 px-4 py-3 text-ink-900 outline-none transition focus:border-brand-accent focus:ring-2 focus:ring-brand-accent/20"
          />
          {error && <p className="mb-3 text-sm text-red-600">{error}</p>}
          <button type="submit" disabled={submitting} className="btn-accent w-full">
            {submitting
              ? "Initialisation..."
              : paymentMethods.length > 0
                ? "Continuer vers le paiement"
                : `Payer ${cart.pricing.total.toLocaleString("fr-FR")} ${cart.pricing.currency}`}
          </button>
        </form>
      </div>
    </main>
  );
}
