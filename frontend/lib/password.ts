// Meme regle que le serveur (backend/app/schemas/auth.py, check_new_password) :
// verifiee pendant la saisie pour ne pas attendre un refus du serveur.

export const PASSWORD_MIN_LENGTH = 8;
export const PASSWORD_HINT = "8 caractères minimum, avec au moins une lettre et un chiffre";

/** Probleme du mot de passe choisi, ou null s'il convient. */
export function passwordProblem(password: string, confirmation?: string): string | null {
  if (password.length < PASSWORD_MIN_LENGTH) return `Le mot de passe doit faire au moins ${PASSWORD_MIN_LENGTH} caractères.`;
  if (!/[A-Za-zÀ-ÿ]/.test(password) || !/\d/.test(password)) {
    return "Le mot de passe doit contenir au moins une lettre et un chiffre.";
  }
  if (confirmation !== undefined && password !== confirmation) return "Les deux mots de passe ne sont pas identiques.";
  return null;
}
