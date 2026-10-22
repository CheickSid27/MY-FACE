"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";

// Ancienne page « Statistiques » : maintenant en haut de l'onglet Ventes de
// l'evenement (components/pro/event/EventStatsPanel.tsx).
export default function StatsRedirect() {
  const { eventId } = useParams<{ eventId: string }>();
  const router = useRouter();
  useEffect(() => {
    router.replace(`/admin/events/${eventId}?onglet=ventes`);
  }, [eventId, router]);
  return null;
}
