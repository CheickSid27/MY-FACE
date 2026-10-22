"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api-client";
import { chunksOf, isAccepted, isPackLimitError, rejectionReason } from "@/lib/photo-files";

/** Dossier surveille, sur l'ordinateur du photographe : il choisit lui-meme
 * le dossier (ex : celui ou il vide sa carte SD, ou ou son logiciel exporte),
 * le navigateur le retient pour cet evenement, et chaque nouvelle photo qui
 * y arrive est envoyee toute seule, tant que la page reste ouverte. Les
 * regles du pack s'appliquent : rien n'est envoye au-dela de la limite, et
 * la proposition de pack superieur s'ouvre.
 * Fonctionne avec Chrome et Edge sur ordinateur (File System Access API). */

interface FileEntry {
  kind: "file";
  name: string;
  getFile(): Promise<File>;
}
interface DirEntry {
  kind: "directory";
  name: string;
  values(): AsyncIterable<FileEntry | DirEntry>;
  queryPermission?(d: { mode: "read" }): Promise<PermissionState>;
  requestPermission?(d: { mode: "read" }): Promise<PermissionState>;
}
type PickerWindow = Window & { showDirectoryPicker?: (o?: { mode?: "read" }) => Promise<DirEntry> };

interface SavedFolder {
  handle: DirEntry;
  sent: string[];
}

interface Recent {
  name: string;
  state: "ok" | "error";
  detail?: string;
}

const SCAN_EVERY_MS = 5000;
const MAX_DEPTH = 3; // carte SD : DCIM/100CANON/...
const SETTLED_AFTER_MS = 10_000; // fichier plus ancien : copie terminee

// --- Petit stockage IndexedDB : le dossier choisi et les photos deja envoyees
const DB_NAME = "myface-pro";
const STORE = "dossiers-surveilles";

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(STORE);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function idb<T>(mode: IDBTransactionMode, run: (store: IDBObjectStore) => IDBRequest): Promise<T> {
  const db = await openDb();
  return new Promise<T>((resolve, reject) => {
    const req = run(db.transaction(STORE, mode).objectStore(STORE));
    req.onsuccess = () => resolve(req.result as T);
    req.onerror = () => reject(req.error);
  }).finally(() => db.close());
}

const loadFolder = (eventId: string) => idb<SavedFolder | undefined>("readonly", (s) => s.get(eventId));
const saveFolder = (eventId: string, value: SavedFolder) => idb("readwrite", (s) => s.put(value, eventId));
const forgetFolder = (eventId: string) => idb("readwrite", (s) => s.delete(eventId));

async function listFiles(dir: DirEntry, prefix = "", depth = 0): Promise<{ path: string; file: File }[]> {
  const found: { path: string; file: File }[] = [];
  for await (const entry of dir.values()) {
    if (entry.name.startsWith(".")) continue;
    if (entry.kind === "directory") {
      if (depth < MAX_DEPTH) found.push(...(await listFiles(entry, `${prefix}${entry.name}/`, depth + 1)));
    } else {
      try {
        found.push({ path: `${prefix}${entry.name}`, file: await entry.getFile() });
      } catch {
        // fichier en cours d'ecriture ou retire entre-temps : prochain passage
      }
    }
  }
  return found;
}

const keyOf = (path: string, file: File) => `${path}|${file.size}|${file.lastModified}`;

interface LocalFolderSyncProps {
  eventId: string;
  /** Photos encore autorisees par le pack ; null = illimite. */
  remaining: number | null;
  onUploaded: () => void;
  onLimitReached: () => void;
}

export default function LocalFolderSync({ eventId, remaining, onUploaded, onLimitReached }: LocalFolderSyncProps) {
  const [supported, setSupported] = useState<boolean | null>(null);
  const [handle, setHandle] = useState<DirEntry | null>(null);
  const [needsPermission, setNeedsPermission] = useState(false);
  const [paused, setPaused] = useState(false);
  const [sending, setSending] = useState(0);
  const [waiting, setWaiting] = useState(0);
  const [sentCount, setSentCount] = useState(0);
  const [full, setFull] = useState(false);
  const [recent, setRecent] = useState<Recent[]>([]);
  const [lastCheck, setLastCheck] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);

  const sentRef = useRef<Set<string>>(new Set());
  const seenRef = useRef<Map<string, string>>(new Map()); // chemin -> taille|date au passage precedent
  const busyRef = useRef(false);
  const budgetRef = useRef<number | null>(remaining);
  const limitShownRef = useRef(false);

  // Le pack change (achat d'un pack superieur) : nouveau quota.
  useEffect(() => {
    budgetRef.current = remaining;
    if (remaining === null || remaining > 0) {
      setFull(false);
      limitShownRef.current = false;
    }
  }, [remaining]);

  useEffect(() => {
    const ok = typeof window !== "undefined" && typeof (window as PickerWindow).showDirectoryPicker === "function";
    setSupported(ok);
    if (!ok) return;
    let cancelled = false;
    loadFolder(eventId)
      .then(async (saved) => {
        if (cancelled || !saved) return;
        sentRef.current = new Set(saved.sent);
        setSentCount(saved.sent.length);
        setHandle(saved.handle);
        const state = (await saved.handle.queryPermission?.({ mode: "read" })) ?? "granted";
        if (!cancelled) setNeedsPermission(state !== "granted");
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [eventId]);

  const persist = useCallback(
    (dir: DirEntry) => saveFolder(eventId, { handle: dir, sent: Array.from(sentRef.current) }).catch(() => {}),
    [eventId]
  );

  const pushRecent = (items: Recent[]) => setRecent((prev) => [...items, ...prev].slice(0, 8));

  const scan = useCallback(async () => {
    if (!handle || busyRef.current) return;
    busyRef.current = true;
    try {
      const files = await listFiles(handle);
      const now = Date.now();
      const ready: { key: string; file: File }[] = [];
      let pending = 0;
      const rejected: Recent[] = [];
      for (const { path, file } of files) {
        if (!isAccepted(file)) continue; // .xmp, videos... : ignores
        const key = keyOf(path, file);
        if (sentRef.current.has(key)) continue;
        // Copie terminee : meme taille qu'au passage precedent, ou fichier ancien.
        const stamp = `${file.size}|${file.lastModified}`;
        const settled = seenRef.current.get(path) === stamp || now - file.lastModified > SETTLED_AFTER_MS;
        seenRef.current.set(path, stamp);
        if (!settled) {
          pending += 1;
          continue;
        }
        const reason = rejectionReason(file);
        if (reason) {
          sentRef.current.add(key); // signale une fois, pas renvoye en boucle
          rejected.push({ name: file.name, state: "error", detail: reason });
          continue;
        }
        ready.push({ key, file });
      }
      if (rejected.length) pushRecent(rejected);

      // Regles du pack : rien au-dela de la limite.
      const budget = budgetRef.current;
      const batch = budget === null ? ready : ready.slice(0, Math.max(0, budget));
      const blocked = ready.length - batch.length;
      setWaiting(pending + blocked);

      let limitRefused = 0;
      if (batch.length > 0) {
        setSending(batch.length);
        let limitHit = false;
        for (const chunk of chunksOf(batch.map((r) => r.file))) {
          const entries = batch.filter((r) => chunk.includes(r.file));
          try {
            const result = await api.uploadPhotos(eventId, chunk);
            const failed = new Map(result.errors.map((e) => [e.filename, e.error]));
            const done: Recent[] = [];
            for (const { key, file } of entries) {
              const err = failed.get(file.name);
              if (err && isPackLimitError(err)) {
                limitHit = true; // gardee pour apres le passage au pack superieur
                limitRefused += 1;
                continue;
              }
              sentRef.current.add(key);
              done.push(err ? { name: file.name, state: "error", detail: err } : { name: file.name, state: "ok" });
            }
            pushRecent(done);
            if (budgetRef.current !== null) budgetRef.current = Math.max(0, budgetRef.current - result.uploaded.length);
            setSentCount(sentRef.current.size);
            setSending((n) => Math.max(0, n - chunk.length));
            await persist(handle);
          } catch (err) {
            // Reseau ou serveur indisponible : on reessaiera au prochain passage.
            setError(err instanceof Error ? err.message : "Envoi interrompu, nouvel essai dans un instant.");
            break;
          }
          if (limitHit) break;
        }
        setSending(0);
        onUploaded();
        if (limitHit) budgetRef.current = 0;
      }

      if (budgetRef.current === 0 && blocked + limitRefused > 0) {
        setWaiting(pending + blocked + limitRefused);
        setFull(true);
        if (!limitShownRef.current) {
          limitShownRef.current = true;
          onLimitReached();
        }
      }
      setLastCheck(new Date());
      if (batch.length > 0) setError(null);
    } catch {
      // Dossier deplace, renomme ou autorisation retiree.
      setError("Dossier inaccessible : choisissez-le de nouveau.");
      setNeedsPermission(true);
    } finally {
      busyRef.current = false;
    }
  }, [handle, eventId, onUploaded, onLimitReached, persist]);

  useEffect(() => {
    if (!handle || needsPermission || paused) return;
    scan();
    const timer = setInterval(scan, SCAN_EVERY_MS);
    return () => clearInterval(timer);
  }, [handle, needsPermission, paused, scan]);

  async function choose() {
    setError(null);
    try {
      const dir = await (window as PickerWindow).showDirectoryPicker!({ mode: "read" });
      seenRef.current.clear();
      setHandle(dir);
      setNeedsPermission(false);
      setPaused(false);
      await persist(dir);
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return; // fenetre fermee
      setError("Impossible d'ouvrir ce dossier. Choisissez-en un autre (pas un dossier système).");
    }
  }

  async function resume() {
    if (!handle) return;
    const state = (await handle.requestPermission?.({ mode: "read" })) ?? "granted";
    setNeedsPermission(state !== "granted");
    if (state === "granted") setError(null);
  }

  async function stop() {
    await forgetFolder(eventId).catch(() => {});
    sentRef.current = new Set();
    seenRef.current.clear();
    setHandle(null);
    setSentCount(0);
    setWaiting(0);
    setRecent([]);
    setFull(false);
  }

  return (
    <div className="glass mb-6 rounded-2xl p-5">
      <div className="mb-1 flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-ink-900">Dossier surveillé</h2>
        {handle && !needsPermission && (
          <span
            className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${
              full ? "bg-[#FDE7D9] text-[#9A3F06]" : paused ? "bg-ink-900/10 text-ink-700" : "bg-emerald-100 text-emerald-700"
            }`}
          >
            {full ? "Pack plein" : paused ? "En pause" : "Actif"}
          </span>
        )}
      </div>

      {supported === false && (
        <p className="text-xs text-ink-500">
          Sur ordinateur, avec Google Chrome ou Microsoft Edge, choisissez un dossier de votre PC (celui où vous videz la
          carte SD, ou où votre logiciel exporte) : chaque nouvelle photo qui y arrive est ajoutée toute seule. Sur ce
          navigateur, utilisez « Ajouter des photos ».
        </p>
      )}

      {supported && !handle && (
        <>
          <p className="mb-3 text-xs text-ink-500">
            Choisissez un dossier de cet ordinateur (celui où vous videz la carte SD, ou où votre logiciel exporte) :
            chaque nouvelle photo qui y arrive est ajoutée toute seule à l&apos;événement, dans la limite de votre pack.
          </p>
          <button type="button" onClick={choose} className="btn-primary w-full !py-2.5 text-sm">
            Choisir le dossier à surveiller
          </button>
        </>
      )}

      {supported && handle && (
        <>
          <p className="mb-3 text-xs text-ink-500">
            Les photos déposées dans ce dossier (et ses sous-dossiers) sont ajoutées toutes seules. Laissez cette page
            ouverte pendant l&apos;événement.
          </p>
          <div className="mb-3 flex items-center gap-2 rounded-xl bg-surface-alt px-3 py-2">
            <span aria-hidden>📁</span>
            <code className="min-w-0 flex-1 truncate text-xs text-ink-900">{handle.name}</code>
          </div>

          {needsPermission ? (
            <button type="button" onClick={resume} className="btn-accent mb-2 w-full !py-2.5 text-sm">
              Reprendre la surveillance
            </button>
          ) : (
            <div className="mb-3 grid grid-cols-3 gap-2 text-center">
              <div className="rounded-xl bg-white/70 p-2">
                <p className="font-pro text-lg font-semibold">{sentCount.toLocaleString("fr-FR")}</p>
                <p className="text-[11px] text-ink-500">envoyées</p>
              </div>
              <div className="rounded-xl bg-white/70 p-2">
                <p className="font-pro text-lg font-semibold">{sending}</p>
                <p className="text-[11px] text-ink-500">en cours</p>
              </div>
              <div className="rounded-xl bg-white/70 p-2">
                <p className="font-pro text-lg font-semibold">{waiting}</p>
                <p className="text-[11px] text-ink-500">{full ? "bloquées" : "en attente"}</p>
              </div>
            </div>
          )}

          {full && (
            <button
              type="button"
              onClick={onLimitReached}
              className="mb-3 w-full rounded-xl bg-[#FDE7D9] px-3 py-2 text-left text-xs font-semibold text-[#9A3F06]"
            >
              Le pack est plein : les nouvelles photos restent dans le dossier. Passer au pack supérieur →
            </button>
          )}

          {error && <p className="mb-3 text-xs text-red-600">{error}</p>}

          {recent.length > 0 && (
            <ul className="mb-3 flex flex-col gap-1.5">
              {recent.map((r, i) => (
                <li key={`${r.name}-${i}`} className="flex items-center justify-between gap-3 text-xs">
                  <span className="truncate text-ink-700">{r.name}</span>
                  <span
                    className={`shrink-0 rounded-full px-2 py-0.5 font-medium ${
                      r.state === "ok" ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-700"
                    }`}
                    title={r.detail}
                  >
                    {r.state === "ok" ? "Ajoutée" : "Refusée"}
                  </span>
                </li>
              ))}
            </ul>
          )}

          <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs">
            {!needsPermission && (
              <button type="button" onClick={() => setPaused((p) => !p)} className="font-semibold text-brand">
                {paused ? "Reprendre" : "Mettre en pause"}
              </button>
            )}
            <button type="button" onClick={choose} className="font-semibold text-brand">
              Changer de dossier
            </button>
            <button type="button" onClick={stop} className="text-ink-500 underline">
              Arrêter
            </button>
            {lastCheck && !needsPermission && (
              <span className="ml-auto text-ink-500">
                Vérifié à {lastCheck.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
              </span>
            )}
          </div>
        </>
      )}
    </div>
  );
}
