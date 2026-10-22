// Regles communes a l'envoi de photos (glisser-deposer et dossier surveille).

// Lots de 10 photos au plus ET de 300 Mo au plus : les photos peuvent peser
// jusqu'a 70 Mo (originaux sans compression, RAW), et nginx refuse une
// requete de plus de 500 Mo (voir nginx/nginx.conf, /api/photos/upload).
export const CHUNK_SIZE = 10;
export const CHUNK_MAX_BYTES = 300 * 1024 * 1024;
export const MAX_FILE_BYTES = 70 * 1024 * 1024;
export const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"];
// RAW des boitiers : reconnus a l'extension (le navigateur ne connait pas
// leur type). Le serveur garde le RAW et en tire un JPEG pleine resolution.
export const RAW_EXTENSIONS = [
  ".3fr", ".arw", ".cr2", ".cr3", ".dng", ".erf", ".iiq", ".kdc", ".mef", ".mos", ".mrw",
  ".nef", ".nrw", ".orf", ".pef", ".raf", ".raw", ".rw2", ".rwl", ".sr2", ".srf", ".srw", ".x3f",
];
const IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"];

export function isAccepted(file: File): boolean {
  const name = file.name.toLowerCase();
  return (
    ACCEPTED_TYPES.includes(file.type) ||
    IMAGE_EXTENSIONS.some((ext) => name.endsWith(ext)) ||
    RAW_EXTENSIONS.some((ext) => name.endsWith(ext))
  );
}

export function rejectionReason(file: File): string | null {
  if (!isAccepted(file)) return "Format non pris en charge (JPEG, PNG, WebP ou RAW)";
  if (file.size > MAX_FILE_BYTES) return "Fichier trop volumineux (70 Mo maximum)";
  return null;
}

/** Message du serveur quand le pack de l'evenement est plein. */
export function isPackLimitError(message: string): boolean {
  return message.startsWith("Limite du pack");
}

/** Decoupe en lots de 10 fichiers et 300 Mo au plus. */
export function chunksOf(files: File[]): File[][] {
  const chunks: File[][] = [];
  let current: File[] = [];
  let bytes = 0;
  for (const file of files) {
    if (current.length > 0 && (current.length >= CHUNK_SIZE || bytes + file.size > CHUNK_MAX_BYTES)) {
      chunks.push(current);
      current = [];
      bytes = 0;
    }
    current.push(file);
    bytes += file.size;
  }
  if (current.length > 0) chunks.push(current);
  return chunks;
}
