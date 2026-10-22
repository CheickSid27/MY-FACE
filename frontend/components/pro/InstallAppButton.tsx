"use client";

import { useEffect, useState } from "react";

// Installation de MYFACE Pro depuis le navigateur. Android et ordinateur :
// le navigateur propose l'installation (evenement beforeinstallprompt).
// iPhone : pas d'evenement, on explique le menu Partager.
interface InstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

export default function InstallAppButton() {
  const [promptEvent, setPromptEvent] = useState<InstallPromptEvent | null>(null);
  const [installed, setInstalled] = useState(false);
  const [ios, setIos] = useState(false);

  useEffect(() => {
    const standalone =
      window.matchMedia("(display-mode: standalone)").matches ||
      (navigator as Navigator & { standalone?: boolean }).standalone === true;
    setInstalled(standalone);
    setIos(/iphone|ipad|ipod/i.test(navigator.userAgent));
    function onPrompt(e: Event) {
      e.preventDefault();
      setPromptEvent(e as InstallPromptEvent);
    }
    function onInstalled() {
      setInstalled(true);
      setPromptEvent(null);
    }
    window.addEventListener("beforeinstallprompt", onPrompt);
    window.addEventListener("appinstalled", onInstalled);
    return () => {
      window.removeEventListener("beforeinstallprompt", onPrompt);
      window.removeEventListener("appinstalled", onInstalled);
    };
  }, []);

  if (installed) return null;

  if (promptEvent) {
    return (
      <button
        type="button"
        onClick={async () => {
          await promptEvent.prompt();
          await promptEvent.userChoice;
          setPromptEvent(null);
        }}
        className="flex min-h-[48px] items-center justify-center rounded-2xl bg-brand text-sm font-bold text-[#F4EFE6]"
      >
        Installer l&apos;application MYFACE Pro
      </button>
    );
  }

  if (ios) {
    return (
      <p className="rounded-2xl border border-[#E6DED0] bg-white p-4 text-[13px] text-ink-700">
        <b className="block text-ink-900">Installer MYFACE Pro sur l&apos;iPhone</b>
        Dans Safari, touchez Partager puis « Sur l&apos;écran d&apos;accueil ».
      </p>
    );
  }

  return null;
}
