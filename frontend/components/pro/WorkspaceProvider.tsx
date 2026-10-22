"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api-client";
import type { ActivityItem, WorkspaceSummary } from "@/types/api";

// Donnees partagees par toute la structure MYFACE Pro : resume de l'accueil
// (badge Ventes, evenement du moment pour le bouton « + ») et fil des
// notifications (pastille de la cloche). Rafraichies regulierement et quand
// l'application revient au premier plan.
const SUMMARY_REFRESH_MS = 60_000;
const ACTIVITY_REFRESH_MS = 120_000;
// « Lu » est garde par l'appareil : rien a stocker cote serveur.
const SEEN_KEY = "myface-pro-notifications-vues";

interface WorkspaceState {
  summary: WorkspaceSummary | null;
  activity: ActivityItem[] | null;
  unread: number;
  seenAt: string | null;
  refresh: () => Promise<void>;
  markAllSeen: () => void;
}

const WorkspaceContext = createContext<WorkspaceState>({
  summary: null,
  activity: null,
  unread: 0,
  seenAt: null,
  refresh: async () => {},
  markAllSeen: () => {},
});

export function useWorkspace(): WorkspaceState {
  return useContext(WorkspaceContext);
}

function readSeen(): string | null {
  try {
    return localStorage.getItem(SEEN_KEY);
  } catch {
    return null;
  }
}

export default function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const [summary, setSummary] = useState<WorkspaceSummary | null>(null);
  const [activity, setActivity] = useState<ActivityItem[] | null>(null);
  const [seenAt, setSeenAt] = useState<string | null>(null);

  const loadSummary = useCallback(async () => {
    try {
      setSummary(await api.getWorkspaceSummary());
    } catch {
      // nouvel essai au prochain rafraichissement
    }
  }, []);

  const loadActivity = useCallback(async () => {
    try {
      setActivity(await api.getWorkspaceActivity());
    } catch {
      // idem
    }
  }, []);

  const refresh = useCallback(async () => {
    await Promise.all([loadSummary(), loadActivity()]);
  }, [loadSummary, loadActivity]);

  useEffect(() => {
    setSeenAt(readSeen());
    refresh();
    const s = setInterval(loadSummary, SUMMARY_REFRESH_MS);
    const a = setInterval(loadActivity, ACTIVITY_REFRESH_MS);
    function onVisible() {
      if (document.visibilityState === "visible") refresh();
    }
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      clearInterval(s);
      clearInterval(a);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [refresh, loadSummary, loadActivity]);

  const markAllSeen = useCallback(() => {
    const now = new Date().toISOString();
    try {
      localStorage.setItem(SEEN_KEY, now);
    } catch {
      // stockage indisponible : la pastille reviendra au prochain chargement
    }
    setSeenAt(now);
  }, []);

  const unread = useMemo(() => {
    if (!activity) return 0;
    const seen = seenAt ? new Date(seenAt).getTime() : 0;
    return activity.filter((item) => new Date(item.at).getTime() > seen).length;
  }, [activity, seenAt]);

  const value = useMemo(
    () => ({ summary, activity, unread, seenAt, refresh, markAllSeen }),
    [summary, activity, unread, seenAt, refresh, markAllSeen]
  );

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}
