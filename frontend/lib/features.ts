"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";

// Fonctions reellement disponibles sur le serveur (GET /meta/features) : les
// pages n'annoncent un SMS que si un SMS peut vraiment partir (Africa's
// Talking configure, hors compte de test « sandbox »).
let cache: Promise<{ sms: boolean }> | null = null;

export function useSmsEnabled(): boolean {
  const [sms, setSms] = useState(false);
  useEffect(() => {
    cache ??= api.getFeatures().catch(() => ({ sms: false }));
    let alive = true;
    cache.then((features) => alive && setSms(features.sms));
    return () => {
      alive = false;
    };
  }, []);
  return sms;
}
