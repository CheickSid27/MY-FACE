import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Palette de la marque (voir /marque et components/brand/Logo.tsx) :
        // encre lagune + orange MYFACE. Le vert de la marque reste reserve
        // au logo, l'interface n'en a pas besoin.
        brand: {
          DEFAULT: "#0e2429",
          light: "#17343b",
          accent: "#f26a1b",
          "accent-light": "#ff8a3d",
        },
        surface: "#f9f6f0",
        "surface-alt": "#f0ebe0",
        ink: {
          900: "#0e2429",
          700: "#33484d",
          500: "#5e7378",
          300: "#9dafb2",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        // Serif elegant reserve au cadre decoratif photobooth (voir
        // components/photo/FramedPhoto.tsx) : distinct de la police
        // d'interface, pour un rendu "carton d'invitation".
        display: ["var(--font-display)", "Georgia", "serif"],
      },
      boxShadow: {
        soft: "0 2px 12px 0 rgb(14 36 41 / 0.07)",
        card: "0 4px 20px 0 rgb(14 36 41 / 0.09)",
        elevated: "0 12px 40px 0 rgb(14 36 41 / 0.18)",
      },
      borderRadius: {
        xl2: "1.25rem",
      },
      keyframes: {
        "fade-in": {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "scale-in": {
          "0%": { opacity: "0", transform: "scale(0.96)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        "pulse-ring": {
          "0%": { transform: "scale(0.9)", opacity: "0.6" },
          "100%": { transform: "scale(1.6)", opacity: "0" },
        },
      },
      animation: {
        "fade-in": "fade-in 0.35s ease-out",
        "scale-in": "scale-in 0.25s cubic-bezier(0.16, 1, 0.3, 1)",
        "pulse-ring": "pulse-ring 1.6s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      },
    },
  },
  plugins: [],
};

export default config;
