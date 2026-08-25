"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";

// Web Push exige la cle VAPID publique en Uint8Array, pas en base64 brut.
function urlBase64ToUint8Array(base64: string): Uint8Array {
  const padding = "=".repeat((4 - (base64.length % 4)) % 4);
  const base64Safe = (base64 + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = window.atob(base64Safe);
  return Uint8Array.from([...raw].map((char) => char.charCodeAt(0)));
}

type Status = "unsupported" | "checking" | "off" | "on" | "denied";

export default function NotificationSetup() {
  const [status, setStatus] = useState<Status>("checking");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function check() {
      if (typeof window === "undefined" || !("serviceWorker" in navigator) || !("PushManager" in window)) {
        setStatus("unsupported");
        return;
      }
      if (Notification.permission === "denied") {
        setStatus("denied");
        return;
      }
      const registration = await navigator.serviceWorker.getRegistration();
      const existing = await registration?.pushManager.getSubscription();
      setStatus(existing ? "on" : "off");
    }
    check();
  }, []);

  async function handleEnable() {
    setBusy(true);
    setError(null);
    try {
      const permission = await Notification.requestPermission();
      if (permission !== "granted") {
        setStatus(permission === "denied" ? "denied" : "off");
        return;
      }

      const registration = await navigator.serviceWorker.register("/sw.js");
      await navigator.serviceWorker.ready;

      const { public_key: vapidPublicKey } = await api.getVapidPublicKey();
      if (!vapidPublicKey) {
        setError("Notifications non configurees cote serveur.");
        return;
      }

      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(vapidPublicKey),
      });

      await api.subscribeToPush(subscription.toJSON() as never);
      setStatus("on");
    } catch {
      setError("Impossible d'activer les notifications.");
    } finally {
      setBusy(false);
    }
  }

  async function handleDisable() {
    setBusy(true);
    try {
      const registration = await navigator.serviceWorker.getRegistration();
      const subscription = await registration?.pushManager.getSubscription();
      if (subscription) {
        await api.unsubscribeFromPush(subscription.endpoint).catch(() => {});
        await subscription.unsubscribe();
      }
      setStatus("off");
    } finally {
      setBusy(false);
    }
  }

  if (status === "unsupported" || status === "checking") return null;

  if (status === "denied") {
    return (
      <div className="glass mb-4 rounded-2xl p-4 text-sm text-ink-500">
        Notifications bloquees pour ce site. Autorisez-les dans les reglages de votre navigateur pour
        recevoir une alerte a chaque commande a confirmer.
      </div>
    );
  }

  return (
    <div className="glass mb-4 flex items-center justify-between gap-3 rounded-2xl p-4">
      <div>
        <p className="text-sm font-semibold text-ink-900">
          {status === "on" ? "Notifications activees" : "Recevoir une alerte par commande"}
        </p>
        <p className="text-xs text-ink-500">
          {status === "on"
            ? "Vous serez notifie sur cet appareil des qu'un client declare avoir paye."
            : "Installez cette page sur votre telephone et activez les notifications."}
        </p>
        {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
      </div>
      <button
        type="button"
        disabled={busy}
        onClick={status === "on" ? handleDisable : handleEnable}
        className={status === "on" ? "btn-ghost !px-4 !py-2 text-xs" : "btn-primary !px-4 !py-2 text-xs"}
      >
        {busy ? "..." : status === "on" ? "Desactiver" : "Activer"}
      </button>
    </div>
  );
}
