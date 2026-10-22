"use client";

import PageHeader from "@/components/pro/PageHeader";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import RequireAuth from "@/components/admin/RequireAuth";
import { api, ApiError } from "@/lib/api-client";
import { useAuthStore } from "@/store/auth-store";
import { formatFcfa, whatsappLink } from "@/lib/packs";
import { PASSWORD_HINT, passwordProblem } from "@/lib/password";
import type { UserAdmin, UserRole } from "@/types/api";

function UsersContent() {
  const router = useRouter();
  const currentUser = useAuthStore((s) => s.user);
  const [users, setUsers] = useState<UserAdmin[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("photographe");
  const [creating, setCreating] = useState(false);

  async function loadUsers() {
    setLoading(true);
    try {
      const data = await api.listUsers();
      setUsers(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Impossible de charger les utilisateurs.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadUsers();
  }, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    const problem = passwordProblem(password);
    if (problem) {
      setError(problem);
      return;
    }
    setCreating(true);
    setError(null);
    try {
      await api.createUser({ email, password, role });
      setEmail("");
      setPassword("");
      setRole("photographe");
      setShowForm(false);
      await loadUsers();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de la création.");
    } finally {
      setCreating(false);
    }
  }

  async function toggleActive(user: UserAdmin) {
    const suspend = user.is_active !== false;
    if (
      suspend &&
      !confirm(`Suspendre ${user.email} ? Le compte ne pourra plus se connecter (ses événements restent en ligne).`)
    )
      return;
    try {
      await api.updateUser(user.id, { is_active: !suspend });
      await loadUsers();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Action impossible.");
    }
  }

  // Sous-compte cree a la main dans le tableau de bord Paystack (Subaccounts) :
  // son code active le paiement en ligne sur les evenements du photographe.
  async function setPayoutCode(user: UserAdmin) {
    const code = window.prompt(
      "Code du sous-compte Paystack (commence par ACCT_), créé dans Paystack > Subaccounts :",
      user.paystack_subaccount_code ?? ""
    );
    if (!code) return;
    try {
      await api.adminSetPayoutCode(user.id, code.trim());
      await loadUsers();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Code refusé.");
    }
  }

  async function clearPayoutCode(user: UserAdmin) {
    if (!confirm("Désactiver le paiement en ligne de ce photographe ?")) return;
    await api.adminClearPayoutCode(user.id);
    await loadUsers();
  }

  async function confirmEmail(user: UserAdmin) {
    if (!confirm(`Confirmer l'adresse ${user.email} sans le lien envoyé par e-mail ?`)) return;
    try {
      await api.updateUser(user.id, { email_verified: true });
      await loadUsers();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Action impossible.");
    }
  }

  async function handleDelete(userId: string) {
    if (!confirm("Supprimer cet utilisateur ?")) return;
    try {
      await api.deleteUser(userId);
      await loadUsers();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Impossible de supprimer cet utilisateur.");
    }
  }

  return (
    <main>
      <div className="mx-auto max-w-2xl">
        <PageHeader title="Photographes et comptes" back="/admin/account" />

        <button type="button" onClick={() => setShowForm((v) => !v)} className="btn-primary mb-4 !px-5 !py-2.5 text-sm">
          {showForm ? "Annuler" : "+ Nouvel utilisateur"}
        </button>

        {showForm && (
          <form onSubmit={handleCreate} className="glass mb-6 rounded-2xl p-5">
            <div className="mb-3">
              <label className="mb-1 block text-sm font-medium text-ink-700">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-xl border border-ink-900/10 bg-white/70 px-3.5 py-2.5 outline-none transition focus:border-brand-accent focus:ring-2 focus:ring-brand-accent/20"
              />
            </div>
            <div className="mb-3">
              <label className="mb-1 block text-sm font-medium text-ink-700">Mot de passe</label>
              <input
                type="password"
                required
                minLength={8}
                maxLength={128}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-xl border border-ink-900/10 bg-white/70 px-3.5 py-2.5 outline-none transition focus:border-brand-accent focus:ring-2 focus:ring-brand-accent/20"
              />
              <p className="mt-1 text-xs text-ink-500">{PASSWORD_HINT}</p>
            </div>
            <div className="mb-4">
              <label className="mb-1 block text-sm font-medium text-ink-700">Role</label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value as UserRole)}
                className="w-full rounded-xl border border-ink-900/10 bg-white/70 px-3.5 py-2.5 outline-none transition focus:border-brand-accent focus:ring-2 focus:ring-brand-accent/20"
              >
                <option value="photographe">Photographe</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <button type="submit" disabled={creating} className="btn-accent !px-5 !py-2.5 text-sm disabled:opacity-50">
              {creating ? "Création..." : "Créer l'utilisateur"}
            </button>
          </form>
        )}

        {error && <p className="mb-4 text-red-600">{error}</p>}
        {loading && <p className="text-ink-500">Chargement...</p>}

        <ul className="space-y-2">
          {users.map((user) => {
            const wa = whatsappLink(user.phone);
            return (
              <li key={user.id} className={`glass flex flex-wrap items-start justify-between gap-3 rounded-2xl p-4 ${user.is_active === false ? "opacity-60" : ""}`}>
                <div className="min-w-0">
                  <p className="font-semibold text-ink-900">
                    {user.studio_name || user.display_name || user.email}
                    {user.is_active === false && (
                      <span className="ml-2 rounded-full bg-red-100 px-2 py-0.5 text-[11px] font-semibold text-red-700">
                        Suspendu
                      </span>
                    )}
                    {user.email_verified === false && (
                      <span className="ml-2 rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-800">
                        E-mail non confirmé
                      </span>
                    )}
                  </p>
                  <p className="text-sm text-ink-500">
                    {user.role === "admin" ? "Administrateur" : "Photographe"}
                    {user.id === currentUser?.id && " · vous"}
                    {(user.studio_name || user.display_name) && ` · ${user.email}`}
                  </p>
                  {user.role === "photographe" && (
                    <p className="mt-1 text-xs text-ink-500">
                      {user.display_name && user.studio_name ? `${user.display_name} · ` : ""}
                      {user.city ? `${user.city} · ` : ""}
                      {user.event_count} événement{user.event_count > 1 ? "s" : ""} · {user.photo_count} photos · packs
                      payés : {formatFcfa(user.packs_paid_total)}
                      {user.packs_pending > 0 && (
                        <span className="ml-1 font-semibold text-amber-700">· {user.packs_pending} paiement(s) à vérifier</span>
                      )}
                    </p>
                  )}
                  {user.role === "photographe" && (
                    <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
                      <span className={user.payout_enabled ? "font-semibold text-emerald-700" : "text-ink-500"}>
                        Paiement en ligne : {user.payout_enabled ? `actif (${user.paystack_subaccount_code})` : "inactif"}
                      </span>
                      <button type="button" onClick={() => setPayoutCode(user)} className="font-semibold text-brand hover:underline">
                        {user.payout_enabled ? "Changer le code Paystack" : "Coller un code Paystack"}
                      </button>
                      {user.payout_enabled && (
                        <button type="button" onClick={() => clearPayoutCode(user)} className="font-semibold text-ink-500 hover:underline">
                          Désactiver
                        </button>
                      )}
                    </p>
                  )}
                </div>
                <div className="flex shrink-0 items-center gap-4">
                  {wa && (
                    <a href={wa} target="_blank" rel="noreferrer" className="text-sm font-medium text-emerald-700 hover:underline">
                      WhatsApp
                    </a>
                  )}
                  {user.email_verified === false && (
                    <button
                      type="button"
                      onClick={() => confirmEmail(user)}
                      className="text-sm font-medium text-ink-500 transition hover:text-brand"
                    >
                      Confirmer l&apos;e-mail
                    </button>
                  )}
                  {user.id !== currentUser?.id && (
                    <button
                      type="button"
                      onClick={() => toggleActive(user)}
                      className="text-sm font-medium text-ink-500 transition hover:text-brand"
                    >
                      {user.is_active === false ? "Réactiver" : "Suspendre"}
                    </button>
                  )}
                  {/* Suppression de son propre compte refusee par l'API : bouton masque. */}
                  {user.id !== currentUser?.id && (
                    <button
                      type="button"
                      onClick={() => handleDelete(user.id)}
                      className="text-sm font-medium text-red-600 transition hover:text-red-800"
                    >
                      Supprimer
                    </button>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      </div>
    </main>
  );
}

export default function UsersPage() {
  return (
    <RequireAuth>
      <UsersContent />
    </RequireAuth>
  );
}
