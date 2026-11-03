"use client";

import { InputHTMLAttributes, useState } from "react";
import { EyeIcon, EyeOffIcon } from "@/components/icons";

/** Champ de mot de passe avec un bouton « œil » pour voir ce qu'on tape.
 * Les marges (mb-*) et la place dans une ligne (flex-1, min-w-0) du className
 * vont sur le conteneur, pour que l'œil reste centre dans le champ. tone="light" : champ sur fond sombre (page invite). */
export default function PasswordInput({
  className = "",
  tone = "dark",
  ...props
}: Omit<InputHTMLAttributes<HTMLInputElement>, "type"> & { tone?: "dark" | "light" }) {
  const [visible, setVisible] = useState(false);
  const classes = className.split(/\s+/).filter(Boolean);
  const outer = (c: string) => /^m[btyxlr]?-/.test(c) || /^(flex-1|min-w-0|grow|shrink-0)$/.test(c);
  const margins = classes.filter(outer).join(" ");
  const inputClasses = classes.filter((c) => !outer(c)).join(" ");
  const label = visible ? "Masquer le mot de passe" : "Afficher le mot de passe";

  return (
    <div className={`relative ${margins}`}>
      <input {...props} type={visible ? "text" : "password"} className={`${inputClasses} w-full !pr-11`} />
      <button
        type="button"
        onClick={() => setVisible((v) => !v)}
        aria-label={label}
        aria-pressed={visible}
        title={label}
        className={`absolute inset-y-0 right-0 flex w-11 items-center justify-center text-lg ${
          tone === "light" ? "text-white/70 hover:text-white" : "text-ink-500 hover:text-ink-900"
        }`}
      >
        {visible ? <EyeOffIcon /> : <EyeIcon />}
      </button>
    </div>
  );
}
