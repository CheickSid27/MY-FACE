"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api-client";
import type { PhoneCountry } from "@/types/api";

// Liste de secours si /meta/phone-countries ne repond pas : au minimum la
// Cote d'Ivoire, avec la meme regle que le serveur (services/phone.py).
const FALLBACK_COUNTRIES: PhoneCountry[] = [
  {
    iso: "CI",
    name: "Cote d'Ivoire",
    dial_code: "225",
    pattern: "0[157]\\d{8}",
    example: "0701020304",
    hint: "10 chiffres commencant par 01, 05 ou 07",
    trunk_prefix: null,
  },
];

let countriesCache: PhoneCountry[] | null = null;

function flagEmoji(iso: string): string {
  return iso
    .toUpperCase()
    .split("")
    .map((char) => String.fromCodePoint(0x1f1e6 + char.charCodeAt(0) - 65))
    .join("");
}

/** "0701020304" -> "07 01 02 03 04" : plus lisible pour verifier sa saisie. */
function groupDigits(digits: string): string {
  return digits.replace(/(\d{2})(?=\d)/g, "$1 ");
}

/** Numero national valide pour ce pays (prefixe 0 de sortie retire si le
 * pays en a un, ex: France 06... -> 6...), ou null. */
function nationalNumber(country: PhoneCountry, raw: string): string | null {
  const digits = raw.replace(/\D/g, "");
  const pattern = new RegExp(`^(?:${country.pattern})$`);
  if (pattern.test(digits)) return digits;
  if (country.trunk_prefix && digits.startsWith(country.trunk_prefix)) {
    const stripped = digits.slice(country.trunk_prefix.length);
    if (pattern.test(stripped)) return stripped;
  }
  return null;
}

interface PhoneInputProps {
  /** Appele a chaque saisie : numero international (+225...) si valide, sinon null. */
  onChange: (e164: string | null) => void;
  disabled?: boolean;
  className?: string;
}

export default function PhoneInput({ onChange, disabled, className = "" }: PhoneInputProps) {
  const [countries, setCountries] = useState<PhoneCountry[]>(countriesCache ?? FALLBACK_COUNTRIES);
  const [iso, setIso] = useState(countries[0].iso);
  const [raw, setRaw] = useState("");
  const [touched, setTouched] = useState(false);

  useEffect(() => {
    if (countriesCache) return;
    api
      .getPhoneCountries()
      .then((list) => {
        if (list.length === 0) return;
        countriesCache = list;
        setCountries(list);
      })
      .catch(() => {
        // liste de secours conservee
      });
  }, []);

  const country = useMemo(() => countries.find((c) => c.iso === iso) ?? countries[0], [countries, iso]);
  const national = raw ? nationalNumber(country, raw) : null;
  const e164 = national ? `+${country.dial_code}${national}` : null;

  useEffect(() => {
    onChange(e164);
  }, [e164, onChange]);

  const showError = touched && raw.length > 0 && !national;

  return (
    <div className={className}>
      <div className="flex gap-2">
        {/* Select natif invisible par-dessus un affichage compact (drapeau +
            indicatif) : la liste deroulante garde les noms complets des
            pays, sans tronquer le champ ferme sur petit ecran. */}
        <div className="relative w-[6.5rem] shrink-0">
          <select
            value={iso}
            disabled={disabled}
            onChange={(e) => setIso(e.target.value)}
            aria-label="Pays"
            className="peer absolute inset-0 h-full w-full cursor-pointer opacity-0 disabled:cursor-not-allowed"
          >
            {countries.map((c) => (
              <option key={c.iso} value={c.iso}>
                {flagEmoji(c.iso)} +{c.dial_code} {c.name}
              </option>
            ))}
          </select>
          <div
            aria-hidden
            className="pointer-events-none flex h-full items-center justify-between gap-1 rounded-xl border border-ink-900/10 bg-white px-3 py-3 text-sm text-ink-900 transition peer-focus:border-brand-accent peer-focus:ring-2 peer-focus:ring-brand-accent/20"
          >
            <span className="truncate">
              {flagEmoji(country.iso)} +{country.dial_code}
            </span>
            <span className="text-xs text-ink-300">&#9662;</span>
          </div>
        </div>
        <input
          type="tel"
          inputMode="tel"
          autoComplete="tel-national"
          required
          disabled={disabled}
          placeholder={groupDigits(country.example)}
          value={raw}
          onChange={(e) => setRaw(e.target.value)}
          onBlur={() => setTouched(true)}
          aria-invalid={showError}
          className={`min-w-0 flex-1 rounded-xl border px-4 py-3 text-ink-900 outline-none transition focus:ring-2 ${
            showError
              ? "border-red-400 focus:border-red-500 focus:ring-red-200"
              : "border-ink-900/10 focus:border-brand-accent focus:ring-brand-accent/20"
          }`}
        />
      </div>
      <p className={`mt-1.5 text-xs ${showError ? "text-red-600" : "text-ink-500"}`}>
        {showError
          ? `Numero invalide pour ${country.name} : ${country.hint}.`
          : e164
            ? `Numero enregistre : +${country.dial_code} ${groupDigits(national ?? "")}`
            : `Format : ${country.hint}.`}
      </p>
    </div>
  );
}
