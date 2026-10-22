// Code court des evenements (voir backend services/short_codes.py) :
// 8 caracteres sans 0/O ni 1/I/L, affiches en deux groupes « K7M2-QX9P ».

const ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ";
export const CODE_LENGTH = 8;

/** Code tape (minuscules, tiret, espaces) -> code, ou null s'il est impossible. */
export function normalizeEventCode(raw: string): string | null {
  const code = raw.toUpperCase().replace(/[\s\-._]/g, "");
  if (code.length !== CODE_LENGTH || [...code].some((ch) => !ALPHABET.includes(ch))) return null;
  return code;
}

export function formatEventCode(code: string): string {
  return code.length === CODE_LENGTH ? `${code.slice(0, 4)}-${code.slice(4)}` : code;
}
