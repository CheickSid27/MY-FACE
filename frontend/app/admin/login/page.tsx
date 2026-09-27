"use client";
import MyfaceLogo from "@/components/brand/Logo";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth-store";

export default function AdminLoginPage() {
  const router = useRouter();
  const login = useAuthStore((s) => s.login);
  const isLoading = useAuthStore((s) => s.isLoading);
  const error = useAuthStore((s) => s.error);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const success = await login(email, password);
    if (success) {
      router.push("/admin/events");
    }
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-gradient-to-br from-brand to-brand-light px-4">
      <div
        className="pointer-events-none absolute inset-0 opacity-40"
        style={{
          background:
            "radial-gradient(circle at 20% 20%, rgba(201,161,90,0.25), transparent 45%), radial-gradient(circle at 80% 70%, rgba(201,161,90,0.15), transparent 40%)",
        }}
      />

      <form onSubmit={handleSubmit} className="glass-strong relative z-10 w-full max-w-sm rounded-2xl p-8 animate-scale-in">
        <div className="mb-6 flex items-center gap-3">
          <MyfaceLogo size={44} />
          <div>
            <p className="text-lg font-bold leading-tight text-ink-900">
              MY<span className="text-[#F26A1B]">FACE</span>
            </p>
            <p className="text-xs text-ink-500">Espace organisateur</p>
          </div>
        </div>

        <label className="mb-1 block text-sm font-medium text-ink-700">Email</label>
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="mb-4 w-full rounded-xl border border-ink-900/10 bg-white/70 px-3.5 py-2.5 text-ink-900 outline-none transition focus:border-brand-accent focus:ring-2 focus:ring-brand-accent/20"
        />

        <label className="mb-1 block text-sm font-medium text-ink-700">Mot de passe</label>
        <input
          type="password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mb-6 w-full rounded-xl border border-ink-900/10 bg-white/70 px-3.5 py-2.5 text-ink-900 outline-none transition focus:border-brand-accent focus:ring-2 focus:ring-brand-accent/20"
        />

        {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

        <button type="submit" disabled={isLoading} className="btn-primary w-full">
          {isLoading ? "Connexion..." : "Se connecter"}
        </button>
      </form>
    </main>
  );
}
