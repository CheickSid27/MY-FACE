import MyfaceLogo from "@/components/brand/Logo";

/** Fond et carte communs aux pages de compte (connexion, inscription, e-mail,
 * mot de passe) : un seul endroit a modifier pour garder le meme style. */
export default function AuthCard({
  subtitle,
  wide = false,
  children,
}: {
  subtitle: string;
  wide?: boolean;
  children: React.ReactNode;
}) {
  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-gradient-to-br from-brand to-brand-light px-4 py-10">
      <div
        className="pointer-events-none absolute inset-0 opacity-40"
        style={{
          background:
            "radial-gradient(circle at 20% 20%, rgba(201,161,90,0.25), transparent 45%), radial-gradient(circle at 80% 70%, rgba(201,161,90,0.15), transparent 40%)",
        }}
      />
      <div
        className={`glass-strong relative z-10 w-full rounded-2xl p-7 animate-scale-in sm:p-8 ${wide ? "max-w-md" : "max-w-sm"}`}
      >
        <div className="mb-6 flex items-center gap-3">
          <MyfaceLogo size={44} />
          <div>
            <p className="text-lg font-bold leading-tight text-ink-900">
              MY<span className="text-[#F26A1B]">FACE</span>
            </p>
            <p className="text-xs text-ink-500">{subtitle}</p>
          </div>
        </div>
        {children}
      </div>
    </main>
  );
}

export const authInputClass =
  "w-full rounded-xl border border-ink-900/10 bg-white/70 px-3.5 py-2.5 text-ink-900 outline-none transition focus:border-brand-accent focus:ring-2 focus:ring-brand-accent/20";
