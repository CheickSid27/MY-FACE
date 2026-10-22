"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { normalizeEventCode } from "@/lib/event-code";

/** Saisie du code d'un evenement (« K7M2-QX9P ») : ouvre sa page invites. */
export default function EventCodeForm({ initial = "", tone = "dark" }: { initial?: string; tone?: "dark" | "light" }) {
  const router = useRouter();
  const [value, setValue] = useState(initial);
  const [error, setError] = useState<string | null>(null);

  function submit(e: FormEvent) {
    e.preventDefault();
    const code = normalizeEventCode(value);
    if (!code) {
      setError("Le code a 8 caractères, par exemple K7M2-QX9P.");
      return;
    }
    router.push(`/e/${code}`);
  }

  const dark = tone === "dark";
  return (
    <form onSubmit={submit} className="flex w-full max-w-sm flex-col gap-2">
      <label htmlFor="event-code" className={`text-sm font-semibold ${dark ? "text-gray-200" : "text-ink-900"}`}>
        Code de l&apos;événement
      </label>
      <div className="flex gap-2">
        <input
          id="event-code"
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            setError(null);
          }}
          placeholder="K7M2-QX9P"
          autoCapitalize="characters"
          autoComplete="off"
          spellCheck={false}
          maxLength={12}
          className={`min-h-[48px] min-w-0 flex-1 rounded-xl px-4 text-center font-mono text-lg uppercase tracking-[0.2em] outline-none ${
            dark
              ? "border border-white/20 bg-white/10 text-white placeholder:text-white/30 focus:border-brand-accent"
              : "border border-[#E6DED0] bg-white text-ink-900 placeholder:text-ink-500/40 focus:border-brand-accent"
          }`}
        />
        <button type="submit" className="min-h-[48px] rounded-xl bg-brand-accent px-5 font-semibold text-brand hover:brightness-110">
          Ouvrir
        </button>
      </div>
      {error && <p className={`text-sm ${dark ? "text-red-300" : "text-red-600"}`}>{error}</p>}
    </form>
  );
}
