import type { Metadata } from "next";
import { Cormorant_Garamond, Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";

const jakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

// Reserve au cadre decoratif photobooth (voir components/photo/FramedPhoto.tsx)
const cormorant = Cormorant_Garamond({
  subsets: ["latin"],
  weight: ["500", "600"],
  variable: "--font-display",
  display: "swap",
});

export const metadata: Metadata = {
  title: "MYFACE",
  description: "Retrouvez, achetez et téléchargez vos photos d'événement",
  manifest: "/manifest.json",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr" className={`${jakarta.variable} ${cormorant.variable}`}>
      <body>{children}</body>
    </html>
  );
}
