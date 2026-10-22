"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";

// Ancienne page « Paiements » : son contenu est maintenant l'onglet Ventes de
// l'evenement (components/pro/event/EventPaymentsPanel.tsx).
export default function PaymentsRedirect() {
  const { eventId } = useParams<{ eventId: string }>();
  const router = useRouter();
  useEffect(() => {
    router.replace(`/admin/events/${eventId}?onglet=ventes`);
  }, [eventId, router]);
  return null;
}
