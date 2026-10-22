"use client";

import { FormEvent, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api-client";
import type { PayoutMethod, PayoutRead } from "@/types/api";

const METHODS: { id: PayoutMethod; label: string }[] = [
  { id: "wave", label: "Wave" },
  { id: "orange", label: "Orange Money" },
  { id: "mtn", label: "MTN MoMo" },
  { id: "bank", label: "Compte bancaire" },
];

const inputClass =
  "w-full rounded-xl border border-[#E6DED0] bg-white px-3.5 py-2.5 text-[15px] outline-none transition focus:border-brand-accent focus:ring-2 focus:ring-brand-accent/20";

/** Paiement en ligne des ventes du photographe : Paystack lui verse l'argent
 * directement (partage des paiements), sans commission MYFACE. Inactif : ses
 * invites paient sur son Wave / Orange et il confirme chaque commande. */
export default function PayoutCard() {
  const [payout, setPayout] = useState<PayoutRead | null>(null);
  const [editing, setEditing] = useState(false);
  const [method, setMethod] = useState<PayoutMethod>("wave");
  const [account, setAccount] = useState("");
  const [name, setName] = useState("");
  const [bankCode, setBankCode] = useState("");
  const [banks, setBanks] = useState<{ code: string; name: string }[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getPayout().then(setPayout).catch(() => setPayout(null));
  }, []);

  useEffect(() => {
    if (method === "bank" && banks.length === 0) api.listPaystackBanks().then(setBanks).catch(() => {});
  }, [method, banks.length]);

  async function save(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setPayout(await api.savePayout({ method, account, name, bank_code: method === "bank" ? bankCode : null }));
      setEditing(false);
      setAccount("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Enregistrement impossible, réessayez.");
    } finally {
      setBusy(false);
    }
  }

  async function disable() {
    if (!confirm("Désactiver le paiement en ligne ? Vos invités paieront de nouveau sur votre Wave ou Orange, et vous confirmerez chaque commande.")) return;
    setBusy(true);
    try {
      setPayout(await api.disablePayout());
    } finally {
      setBusy(false);
    }
  }

  if (!payout || !payout.available) return null;
  const methodLabel = METHODS.find((m) => m.id === payout.method)?.label ?? "";

  return (
    <section className="rounded-3xl border border-[#E6DED0] bg-white p-4">
      <h2 className="font-pro text-[15px] font-semibold">Paiement en ligne de vos ventes</h2>
      <p className="mt-1 text-[13px] text-ink-500">
        Vos invités paient par Wave, Orange Money, MTN ou carte, et leurs photos sont débloquées tout de suite.
        Paystack vous verse l&apos;argent directement : MYFACE ne prend aucune commission, seuls les frais Paystack
        (1,95 %) sont déduits.
      </p>

      {payout.enabled && !editing ? (
        <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-2xl bg-emerald-50 p-3 text-sm text-emerald-900">
          <span>
            <b>Actif</b> · {methodLabel} {payout.account_masked} · {payout.name}
          </span>
          <span className="flex gap-3">
            <button type="button" onClick={() => setEditing(true)} className="font-semibold underline">
              Modifier
            </button>
            <button type="button" disabled={busy} onClick={disable} className="font-semibold text-emerald-800 underline">
              Désactiver
            </button>
          </span>
        </div>
      ) : !editing ? (
        <button
          type="button"
          onClick={() => setEditing(true)}
          className="mt-3 flex min-h-[46px] w-full items-center justify-center rounded-2xl bg-brand-accent text-sm font-bold text-brand"
        >
          Activer le paiement en ligne
        </button>
      ) : null}

      {editing && (
        <form onSubmit={save} className="mt-3 flex flex-col gap-3">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {METHODS.map((m) => (
              <button
                key={m.id}
                type="button"
                onClick={() => setMethod(m.id)}
                className={`min-h-[42px] rounded-xl border text-[13px] font-semibold ${
                  method === m.id ? "border-brand bg-brand text-[#F4EFE6]" : "border-[#E6DED0] bg-white"
                }`}
              >
                {m.label}
              </button>
            ))}
          </div>
          {method === "bank" && (
            <label className="block">
              <span className="mb-1 block text-sm font-medium text-ink-700">Banque</span>
              <select required value={bankCode} onChange={(e) => setBankCode(e.target.value)} className={inputClass}>
                <option value="">Choisir votre banque</option>
                {banks.map((b) => (
                  <option key={b.code} value={b.code}>
                    {b.name}
                  </option>
                ))}
              </select>
            </label>
          )}
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-ink-700">
              {method === "bank" ? "RIB (24 caractères, sans « CI » et les 2 chiffres de l'IBAN)" : "Numéro qui reçoit l'argent"}
            </span>
            <input
              required
              value={account}
              onChange={(e) => setAccount(e.target.value)}
              placeholder={method === "bank" ? "CI0320100111146500743385" : "07 01 02 03 04"}
              inputMode={method === "bank" ? "text" : "tel"}
              className={inputClass}
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-ink-700">Nom du titulaire</span>
            <input required minLength={2} value={name} onChange={(e) => setName(e.target.value)} placeholder="Comme sur le compte" className={inputClass} />
          </label>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <div className="flex gap-2.5">
            <button type="button" onClick={() => setEditing(false)} className="flex-1 rounded-xl border border-[#D9CFBF] bg-white py-3 text-sm font-semibold">
              Annuler
            </button>
            <button type="submit" disabled={busy} className="flex-1 rounded-xl bg-brand-accent py-3 text-sm font-bold text-brand disabled:opacity-50">
              {busy ? "Enregistrement..." : "Enregistrer"}
            </button>
          </div>
        </form>
      )}
    </section>
  );
}
