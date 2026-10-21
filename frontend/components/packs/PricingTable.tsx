"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api-client";
import { MYFACE_WHATSAPP_FALLBACK, formatFcfa, whatsappLink } from "@/lib/packs";
import type { Pack } from "@/types/api";

// Affiche tout de suite (avant la reponse du serveur, ou s'il ne repond pas) ;
// le serveur (services/packs.py) fait foi et remplace ces valeurs.
const FALLBACK_PACKS: Pack[] = [
  {
    key: "decouverte",
    name: "Découverte",
    price: 0,
    photo_limit: 10,
    tagline: "Pour essayer MYFACE sur un petit événement",
    highlights: [
      "10 photos par événement",
      "IA de reconnaissance faciale",
      "QR code et page invités",
      "Galerie, « Trouver mon visage » et selfie",
      "Vente aux invités ou photos offertes",
    ],
    features: [],
    purchasable: false,
  },
  {
    key: "evenement",
    name: "Événement",
    price: 10000,
    photo_limit: 500,
    tagline: "Mariages, anniversaires, conférences",
    highlights: ["500 photos par événement", "Tout le pack Découverte", "Mot de passe de galerie", "Filigrane à votre nom"],
    features: ["custom_watermark", "gallery_password"],
    purchasable: true,
  },
  {
    key: "pro",
    name: "Pro",
    price: 25000,
    photo_limit: 2000,
    tagline: "Photographes et grands événements",
    highlights: ["2 000 photos par événement", "Tout le pack Événement", "Assistance prioritaire le jour J"],
    features: ["custom_watermark", "gallery_password", "priority_support"],
    purchasable: true,
  },
  {
    key: "sur_mesure",
    name: "Sur mesure",
    price: null,
    photo_limit: null,
    tagline: "Studios, agences et organisateurs réguliers",
    highlights: [
      "Carnet d'événements prépayés à prix réduit",
      "Limite de photos adaptée",
      "Assistance le jour J",
      "Facture au nom de votre entreprise",
    ],
    features: [],
    purchasable: false,
  },
];

export default function PricingTable({ signupHref = "/photographes/inscription" }: { signupHref?: string }) {
  const [packs, setPacks] = useState<Pack[]>(FALLBACK_PACKS);

  useEffect(() => {
    api
      .listPacks()
      .then((data) => {
        if (data.length) setPacks(data);
      })
      .catch(() => {
        // valeurs de secours deja affichees
      });
  }, []);

  const contact = whatsappLink(MYFACE_WHATSAPP_FALLBACK, "Bonjour MYFACE, je souhaite une offre sur mesure pour mes événements.");

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {packs.map((pack) => {
        const featured = pack.key === "evenement";
        return (
          <div
            key={pack.key}
            className={`relative flex flex-col rounded-2xl p-5 ${
              featured ? "bg-brand text-white shadow-elevated" : "glass text-ink-900"
            }`}
          >
            {featured && (
              <span className="absolute -top-3 left-5 rounded-full bg-brand-accent px-3 py-1 text-[11px] font-bold text-white">
                Le plus choisi
              </span>
            )}
            <p className={`text-sm font-semibold ${featured ? "text-brand-accent" : "text-brand-accent"}`}>{pack.name}</p>
            <p className="mt-1 text-3xl font-bold">{formatFcfa(pack.price)}</p>
            <p className={`text-xs ${featured ? "text-white/70" : "text-ink-500"}`}>
              {pack.price ? "par événement, paiement unique" : pack.price === 0 ? "pour toujours" : "selon vos volumes"}
            </p>
            <p className={`mt-3 text-sm ${featured ? "text-white/90" : "text-ink-700"}`}>{pack.tagline}</p>
            <ul className="mt-3 flex flex-1 flex-col gap-1.5 text-sm">
              {pack.highlights.map((h) => (
                <li key={h} className="flex gap-2">
                  <span className="text-brand-accent">✓</span>
                  <span>{h}</span>
                </li>
              ))}
            </ul>
            {pack.key === "sur_mesure" ? (
              <a
                href={contact ?? "#"}
                target="_blank"
                rel="noreferrer"
                className="btn-ghost mt-5 !py-2.5 text-center text-sm"
              >
                Discuter sur WhatsApp
              </a>
            ) : (
              <Link
                href={signupHref}
                className={`${featured ? "btn-accent" : "btn-primary"} mt-5 !py-2.5 text-center text-sm`}
              >
                {pack.price === 0 ? "Essayer gratuitement" : "Créer mon compte"}
              </Link>
            )}
          </div>
        );
      })}
    </div>
  );
}
