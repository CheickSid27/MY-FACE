"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";

// Fonctions reellement disponibles sur le serveur (GET /meta/features) : les
// pages n'annoncent un SMS que si un SMS peut vraiment partir (Africa's
// Talking configure, hors compte de test « sandbox »), et ne proposent le
// paiement en ligne que si Paystack est configure.
type Features = { sms: boolean; paystack?: boolean };
let cache: Promise<Features> | null = null;

function useFeature(key: keyof Features): boolean {
  const [enabled, setEnabled] = useState(false);
  useEffect(() => {
    cache ??= api.getFeatures().catch(() => ({ sms: false }));
    let alive = true;
    cache.then((features) => alive && setEnabled(Boolean(features[key])));
    return () => {
      alive = false;
    };
  }, [key]);
  return enabled;
}

export function useSmsEnabled(): boolean {
  return useFeature("sms");
}

export function usePaystackEnabled(): boolean {
  return useFeature("paystack");
}
