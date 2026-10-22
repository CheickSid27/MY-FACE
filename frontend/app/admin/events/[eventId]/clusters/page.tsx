"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";

// Ancienne page « Personnes detectees » : maintenant l'onglet Visages de
// l'evenement (components/pro/event/EventFacesPanel.tsx).
export default function ClustersRedirect() {
  const { eventId } = useParams<{ eventId: string }>();
  const router = useRouter();
  useEffect(() => {
    router.replace(`/admin/events/${eventId}?onglet=visages`);
  }, [eventId, router]);
  return null;
}
