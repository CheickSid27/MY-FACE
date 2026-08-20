"use client";

import { ChangeEvent, useRef, useState } from "react";
import { api } from "@/lib/api-client";
import type { PhotoUploadError } from "@/types/api";

interface BatchUploaderProps {
  eventId: string;
  onUploaded: () => void;
}

const CHUNK_SIZE = 20;

export default function BatchUploader({ eventId, onUploaded }: BatchUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState({ done: 0, total: 0 });
  const [errors, setErrors] = useState<PhotoUploadError[]>([]);

  async function handleFiles(e: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;

    setUploading(true);
    setErrors([]);
    setProgress({ done: 0, total: files.length });

    const allErrors: PhotoUploadError[] = [];

    for (let i = 0; i < files.length; i += CHUNK_SIZE) {
      const chunk = files.slice(i, i + CHUNK_SIZE);
      try {
        const result = await api.uploadPhotos(eventId, chunk);
        allErrors.push(...result.errors);
      } catch (err) {
        chunk.forEach((file) =>
          allErrors.push({
            filename: file.name,
            error: err instanceof Error ? err.message : "Echec de l'upload",
          })
        );
      }
      setProgress((p) => ({ ...p, done: Math.min(p.total, i + chunk.length) }));
    }

    setErrors(allErrors);
    setUploading(false);
    if (inputRef.current) inputRef.current.value = "";
    onUploaded();
  }

  return (
    <div className="glass rounded-2xl p-4">
      <label className="mb-2 block text-sm font-medium text-ink-700">Ajouter des photos (batch)</label>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept="image/jpeg,image/png,image/webp"
        onChange={handleFiles}
        disabled={uploading}
        className="block w-full text-sm text-ink-700"
      />

      {uploading && (
        <p className="mt-2 text-sm text-ink-500">
          Upload en cours : {progress.done}/{progress.total}
        </p>
      )}

      {errors.length > 0 && (
        <div className="mt-3 rounded-lg bg-red-50 p-3 text-sm text-red-700">
          <p className="mb-1 font-medium">{errors.length} fichier(s) rejete(s) :</p>
          <ul className="list-disc pl-5">
            {errors.map((err) => (
              <li key={err.filename}>
                {err.filename} — {err.error}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
