// Logo MYFACE. Le carre de detection (comme celui que l'app dessine autour
// d'un visage reconnu), un visage souriant, un coin en vert : voir le dossier
// /marque a la racine du projet pour les fichiers sources et les variantes.
// Dessine en SVG inline pour rester net a l'impression (affiche, recu) et
// pouvoir changer de couleurs selon le fond.

type Tone = "dark" | "light" | "mono";

const TONES: Record<Tone, { plate: string | null; frame: string; corner: string; face: string; word: string }> = {
  // Pastille sombre (fond clair ou sombre, usage par defaut)
  dark: { plate: "#0E2429", frame: "#F26A1B", corner: "#00854B", face: "#F4EFE6", word: "currentColor" },
  // Pastille sable (fond sombre)
  light: { plate: "#F4EFE6", frame: "#F26A1B", corner: "#00854B", face: "#0E2429", word: "currentColor" },
  // Une seule couleur, heritee du texte : impression noir et blanc, gravure
  mono: { plate: null, frame: "currentColor", corner: "currentColor", face: "currentColor", word: "currentColor" },
};

const X0 = 120;
const Y0 = 124;
const X1 = 392;
const Y1 = 396;
const ARM = 66;

const SMILE =
  "M304.3,282.1 L302.0,285.9 L299.3,289.5 L296.4,292.7 L293.2,295.7 L289.7,298.3 L286.0,300.6 " +
  "L282.1,302.5 L278.0,304.0 L273.8,305.1 L269.5,305.8 L265.1,306.0 L260.7,305.9 L256.3,305.3 " +
  "L252.0,304.3 L247.8,302.9 L243.8,301.1 L239.9,298.9 L236.3,296.4 L232.9,293.5 L229.8,290.4 " +
  "L227.0,286.9 L224.6,283.3";

export default function MyfaceLogo({
  size = 40,
  tone = "dark",
  withWordmark = false,
  className,
}: {
  size?: number;
  tone?: Tone;
  withWordmark?: boolean;
  className?: string;
}) {
  const c = TONES[tone];
  const icon = (
    <svg
      viewBox="0 0 512 512"
      width={size}
      height={size}
      role="img"
      aria-label="MYFACE"
      style={{ borderRadius: size * 0.22, flex: "0 0 auto" }}
    >
      {c.plate && <rect width="512" height="512" rx="116" fill={c.plate} />}
      <g fill="none" strokeWidth="26" strokeLinecap="round" strokeLinejoin="round">
        <path d={`M${X0},${Y0 + ARM} L${X0},${Y0} L${X0 + ARM},${Y0}`} stroke={c.frame} />
        <path d={`M${X1 - ARM},${Y0} L${X1},${Y0} L${X1},${Y0 + ARM}`} stroke={c.frame} />
        <path d={`M${X0 + ARM},${Y1} L${X0},${Y1} L${X0},${Y1 - ARM}`} stroke={c.frame} />
        <path d={`M${X1},${Y1 - ARM} L${X1},${Y1} L${X1 - ARM},${Y1}`} stroke={c.corner} />
      </g>
      <circle cx="208" cy="226" r="15" fill={c.face} />
      <circle cx="304" cy="226" r="15" fill={c.face} />
      <path d={SMILE} fill="none" stroke={c.face} strokeWidth="22" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );

  if (!withWordmark) return className ? <span className={className}>{icon}</span> : icon;

  return (
    <span className={className} style={{ display: "inline-flex", alignItems: "center", gap: size * 0.3 }}>
      {icon}
      <span
        style={{
          fontSize: size * 0.62,
          fontWeight: 800,
          letterSpacing: "-0.02em",
          lineHeight: 1,
          color: c.word,
        }}
      >
        MY<span style={{ color: "#F26A1B" }}>FACE</span>
      </span>
    </span>
  );
}
