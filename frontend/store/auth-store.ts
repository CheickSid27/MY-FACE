import { create } from "zustand";
import { clearTokens, isAuthenticated } from "@/lib/auth";
import { api } from "@/lib/api-client";
import type { User } from "@/types/api";

interface AuthState {
  user: User | null;
  isLoggedIn: boolean;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<boolean>;
  logout: () => void;
  setUser: (user: User) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isLoggedIn: typeof window !== "undefined" ? isAuthenticated() : false,
  isLoading: false,
  error: null,

  login: async (email: string, password: string) => {
    set({ isLoading: true, error: null });
    try {
      await api.login(email, password);
      set({ isLoggedIn: true, isLoading: false });
      return true;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erreur de connexion";
      set({ isLoading: false, error: message, isLoggedIn: false });
      return false;
    }
  },

  // N'efface que la session : RequireAuth (components/admin/RequireAuth.tsx)
  // detecte le changement et renvoie vers /admin/login. Avant, l'ecran admin
  // restait affiche apres deconnexion.
  logout: () => {
    clearTokens();
    set({ isLoggedIn: false, user: null });
  },

  // Renseigne par RequireAuth une fois le jeton verifie (GET /auth/me) : role
  // et email disponibles pour toutes les pages admin.
  setUser: (user: User) => set({ user, isLoggedIn: true }),
}));
