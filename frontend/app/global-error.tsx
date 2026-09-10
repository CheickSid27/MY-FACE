"use client";

// Uniquement declenche par une exception dans app/layout.tsx lui-meme (le
// error.tsx normal ne peut pas l'intercepter puisqu'il est rendu A
// L'INTERIEUR du layout racine) : doit donc fournir son propre <html>/<body>,
// Next.js remplace entierement le layout racine par ce fichier dans ce cas.
export default function GlobalError({ reset }: { reset: () => void }) {
  return (
    <html lang="fr">
      <body>
        <main
          style={{
            display: "flex",
            minHeight: "100vh",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: "1.25rem",
            padding: "1.5rem",
            textAlign: "center",
            background: "#14171f",
            color: "#fff",
            fontFamily: "system-ui, sans-serif",
          }}
        >
          <h1 style={{ fontSize: "1.25rem", fontWeight: 700 }}>Une erreur est survenue</h1>
          <p style={{ maxWidth: "24rem", fontSize: "0.875rem", color: "#a8adb8" }}>
            Quelque chose s&apos;est mal passe. Rechargez la page pour reessayer.
          </p>
          <button
            type="button"
            onClick={reset}
            style={{
              borderRadius: "1rem",
              background: "#c9a15a",
              padding: "0.75rem 1.5rem",
              fontWeight: 600,
              color: "#14171f",
              border: "none",
              cursor: "pointer",
            }}
          >
            Reessayer
          </button>
        </main>
      </body>
    </html>
  );
}
