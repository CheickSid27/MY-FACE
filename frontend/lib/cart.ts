function cartSessionKey(eventId: string): string {
  return `myface_cart_session_${eventId}`;
}

export function getCartSessionId(eventId: string): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(cartSessionKey(eventId));
}

export function setCartSessionId(eventId: string, sessionId: string): void {
  window.localStorage.setItem(cartSessionKey(eventId), sessionId);
}

export function clearCartSessionId(eventId: string): void {
  window.localStorage.removeItem(cartSessionKey(eventId));
}
