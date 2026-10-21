"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import RequireAuth from "@/components/admin/RequireAuth";
import RetentionCard from "@/components/admin/RetentionCard";
import { api, ApiError } from "@/lib/api-client";
import { PACK_PAYMENT_METHODS } from "@/lib/packs";
import { useAuthStore } from "@/store/auth-store";
import type { PackPaymentInfo } from "@/types/api";

/** Reglages MYFACE : numeros Mobile Money ou les photographes envoient le
 * paiement de leurs packs, numero WhatsApp de contact, et conservation des
 * donnees (suppression automatique). */
function AdminSettingsContent() {
  const user = useAuthStore((s) => s.user);
  const [info, setInfo] = useState<PackPaymentInfo>({});
  const [loaded, setLoaded] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getAdminPackPayment()
      .then((data) => setInfo(data))
      .catch((err) => setError(err instanceof ApiError ? err.message : "Chargement impossible."))
      .finally(() => setLoaded(true));
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      setInfo(await api.setAdminPackPayment(info));
      setMessage("Réglages enregistrés : les photographes voient ces numéros au moment de payer un pack.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Enregistrement impossible.");
    } finally {
      setSaving(false);
    }
  }

  if (user && user.role !== "admin") {
    return <p className="p-6 text-ink-500">Page réservée à l&apos;équipe MYFACE.</p>;
  }

  const inputClass =
    "w-full rounded-xl border border-ink-900/10 bg-white/70 px-3.5 py-2.5 text-sm outline-none transition focus:border-brand-accent focus:ring-2 focus:ring-brand-accent/20";

  return (
    <main className="min-h-screen bg-gradient-to-b from-surface-alt to-surface p-6">
      <div className="mx-auto max-w-xl">
        <Link href="/admin/events" className="mb-4 inline-block text-sm font-medium text-ink-500 transition hover:text-brand">
          &larr; Retour aux événements
        </Link>
        <form onSubmit={handleSubmit} className="glass rounded-2xl p-5">
          <h1 className="mb-1 text-xl font-bold text-ink-900">Paiement des packs</h1>
          <p className="mb-4 text-xs text-ink-500">
            Numéros Mobile Money de MYFACE affichés aux photographes quand ils achètent un pack. Laissez vide un
            moyen que vous n&apos;utilisez pas.
          </p>
          {!loaded && <p className="text-sm text-ink-500">Chargement...</p>}
          {PACK_PAYMENT_METHODS.map((m) => (
            <div key={m.key} className="mb-3">
              <label className="mb-1 block text-sm font-medium text-ink-700">{m.label}</label>
              <input
                type="tel"
                maxLength={32}
                value={info[m.key] ?? ""}
                onChange={(e) => setInfo((prev) => ({ ...prev, [m.key]: e.target.value }))}
                placeholder="Ex : 07 00 00 00 00"
                className={inputClass}
              />
            </div>
          ))}
          <div className="mb-3">
            <label className="mb-1 block text-sm font-medium text-ink-700">WhatsApp de contact</label>
            <input
              type="tel"
              maxLength={32}
              value={info.whatsapp ?? ""}
              onChange={(e) => setInfo((prev) => ({ ...prev, whatsapp: e.target.value }))}
              placeholder="+225 07 00 00 00 00"
              className={inputClass}
            />
          </div>
          <div className="mb-4">
            <label className="mb-1 block text-sm font-medium text-ink-700">Consigne (facultatif)</label>
            <textarea
              value={info.instructions ?? ""}
              onChange={(e) => setInfo((prev) => ({ ...prev, instructions: e.target.value }))}
              maxLength={500}
              rows={3}
              placeholder="Ex : indiquez le nom de votre événement dans le motif du transfert."
              className={inputClass}
            />
          </div>
          {message && <p className="mb-3 text-sm text-emerald-700">{message}</p>}
          {error && <p className="mb-3 text-sm text-red-600">{error}</p>}
          <button type="submit" disabled={saving} className="btn-primary w-full disabled:opacity-50">
            {saving ? "Enregistrement..." : "Enregistrer"}
          </button>
        </form>
        <RetentionCard />
      </div>
    </main>
  );
}

export default function AdminSettingsPage() {
  return (
    <RequireAuth>
      <AdminSettingsContent />
    </RequireAuth>
  );
}
