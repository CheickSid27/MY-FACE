// ID pose sur l'icone panier (dans les en-tetes galerie/scan) pour que
// n'importe quel ecran puisse y "envoyer" une photo, meme depuis une modale
// ouverte par-dessus (ScanDialog, FindFacesDialog) : le DOM de la galerie
// reste monte en arriere-plan, donc l'icone est toujours trouvable.
export const CART_ICON_ID = "cart-icon-target";

/**
 * Anime un clone de `sourceEl` qui "vole" jusqu'a l'icone panier, avec la
 * direction et la distance calculees a partir des positions reelles a
 * l'ecran (getBoundingClientRect) : ca marche donc quelle que soit la
 * position du panier (en haut, en bas, a droite...), sans valeur en dur.
 */
export function flyToCart(sourceEl: HTMLElement | null): void {
  if (!sourceEl || typeof document === "undefined") return;
  const targetEl = document.getElementById(CART_ICON_ID);
  if (!targetEl) return;

  const sourceRect = sourceEl.getBoundingClientRect();
  const targetRect = targetEl.getBoundingClientRect();
  if (sourceRect.width === 0 || sourceRect.height === 0) return;

  const img = sourceEl.querySelector("img") as HTMLImageElement | null;
  const src = img?.src;

  const clone = document.createElement("div");
  clone.style.position = "fixed";
  clone.style.left = `${sourceRect.left}px`;
  clone.style.top = `${sourceRect.top}px`;
  clone.style.width = `${sourceRect.width}px`;
  clone.style.height = `${sourceRect.height}px`;
  clone.style.borderRadius = "14px";
  clone.style.overflow = "hidden";
  clone.style.zIndex = "9999";
  clone.style.pointerEvents = "none";
  clone.style.boxShadow = "0 12px 30px rgba(20,23,31,0.35)";
  clone.style.transition = "transform 0.62s cubic-bezier(0.34, 1.15, 0.4, 1), opacity 0.62s ease-in";
  clone.style.willChange = "transform, opacity";
  if (src) {
    clone.style.backgroundImage = `url(${src})`;
    clone.style.backgroundSize = "cover";
    clone.style.backgroundPosition = "center";
  } else {
    clone.style.background = "rgba(201,161,90,0.9)";
  }

  document.body.appendChild(clone);

  const dx = targetRect.left + targetRect.width / 2 - (sourceRect.left + sourceRect.width / 2);
  const dy = targetRect.top + targetRect.height / 2 - (sourceRect.top + sourceRect.height / 2);

  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      clone.style.transform = `translate(${dx}px, ${dy}px) scale(0.12) rotate(8deg)`;
      clone.style.opacity = "0.15";
    });
  });

  window.setTimeout(() => {
    clone.remove();
    targetEl.dispatchEvent(new CustomEvent("cart-landed"));
  }, 640);
}
