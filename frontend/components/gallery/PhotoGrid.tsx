"use client";

import { memo, useEffect, useMemo, useRef, useState } from "react";
import { FixedSizeGrid as Grid, type GridChildComponentProps } from "react-window";
import { CheckIcon, ImageIcon } from "@/components/icons";
import { flyToCart } from "@/lib/fly-to-cart";
import type { Photo } from "@/types/api";

interface PhotoGridProps {
  photos: Photo[];
  onPhotoOpen?: (index: number) => void;
  onToggleSelect?: (photo: Photo) => void;
  selectedPhotoIds?: Set<string>;
  addingPhotoId?: string | null;
  bottomOffset?: number;
}

interface CellData {
  photos: Photo[];
  columnCount: number;
  selectedPhotoIds?: Set<string>;
  addingPhotoId?: string | null;
  onPhotoOpen?: (index: number) => void;
  onToggleSelect?: (photo: Photo) => void;
}

const GAP = 10;
const MIN_COLUMN_WIDTH = 160;
const RESIZE_DEBOUNCE_MS = 200;

export default function PhotoGrid({
  photos,
  onPhotoOpen,
  onToggleSelect,
  selectedPhotoIds,
  addingPhotoId,
  bottomOffset = 160,
}: PhotoGridProps) {
  const [size, setSize] = useState({ width: 0, height: 0 });

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | null = null;

    function updateSize() {
      setSize((prev) => {
        const next = { width: window.innerWidth, height: window.innerHeight - bottomOffset };
        // Sur mobile, taper un bouton peut declencher un micro-resize (barre
        // d'adresse qui se replie/deplie) : on ignore les variations
        // negligeables pour ne pas relayouter toute la grille virtualisee a
        // chaque tap, ce qui donnait l'impression que toutes les photos
        // "rechargeaient".
        if (Math.abs(next.width - prev.width) < 4 && Math.abs(next.height - prev.height) < 4) {
          return prev;
        }
        return next;
      });
    }

    function debouncedUpdateSize() {
      if (timer) clearTimeout(timer);
      timer = setTimeout(updateSize, RESIZE_DEBOUNCE_MS);
    }

    updateSize();
    window.addEventListener("resize", debouncedUpdateSize);
    return () => {
      window.removeEventListener("resize", debouncedUpdateSize);
      if (timer) clearTimeout(timer);
    };
  }, [bottomOffset]);

  // Deriveable a partir de `size`, mais calcule inconditionnellement (avant
  // tout retour anticipe) : les Hooks doivent s'executer dans le meme ordre
  // a chaque rendu. Avec size.width===0, columnCount vaut simplement 2
  // (jamais utilise, Grid n'est pas rendue dans ce cas).
  const columnCount = Math.max(2, Math.floor(size.width / (MIN_COLUMN_WIDTH + GAP)));
  const columnWidth = size.width > 0 ? Math.floor(size.width / columnCount) : 0;
  const rowHeight = columnWidth;
  const rowCount = Math.ceil(photos.length / columnCount);

  // IMPORTANT (bug corrige) : react-window utilise la fonction passee en
  // `children` comme un vrai TYPE de composant React
  // (React.createElement(children, {...})), pas comme un simple callback.
  // Si cette fonction change de reference d'un rendu a l'autre, React voit
  // un type different a chaque cellule et la DEMONTE/REMONTE entierement,
  // meme avec une key stable ("rowIndex:columnIndex") — c'etait le cas ici
  // avec une fonction inline recreee au moindre changement d'etat du parent
  // (ex: selectionner UNE photo), rendant impossible d'en selectionner
  // plusieurs a la suite (la grille se "reconstruisait" sous le doigt entre
  // deux clics). Solution : un composant Cell stable au niveau module (type
  // fixe pour toujours) qui lit ses donnees via la prop `itemData` de Grid —
  // seule cette donnee change de reference, jamais le composant lui-meme.
  const itemData = useMemo<CellData>(
    () => ({ photos, columnCount, selectedPhotoIds, addingPhotoId, onPhotoOpen, onToggleSelect }),
    [photos, columnCount, selectedPhotoIds, addingPhotoId, onPhotoOpen, onToggleSelect]
  );

  if (size.width === 0) return null;

  if (photos.length === 0) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-2 text-ink-500">
        <ImageIcon className="text-3xl" />
        <p>Aucune photo pour le moment.</p>
      </div>
    );
  }

  return (
    <Grid
      columnCount={columnCount}
      columnWidth={columnWidth}
      rowCount={rowCount}
      rowHeight={rowHeight}
      width={size.width}
      height={size.height}
      itemData={itemData}
      className="!overflow-x-hidden"
    >
      {GridCell}
    </Grid>
  );
}

// Type de composant STABLE (defini une seule fois au niveau module) : c'est
// ce qui garantit a react-window de toujours reconcilier la meme identite de
// composant par cellule, quelle que soit la frequence de re-rendu de
// PhotoGrid. Toutes les donnees dynamiques passent par `data` (itemData).
function GridCell({ columnIndex, rowIndex, style, data }: GridChildComponentProps<CellData>) {
  const { photos, columnCount, selectedPhotoIds, addingPhotoId, onPhotoOpen, onToggleSelect } = data;
  const index = rowIndex * columnCount + columnIndex;
  const photo = photos[index];
  if (!photo) return null;

  const isSelected = selectedPhotoIds?.has(photo.id) ?? false;
  const isAdding = addingPhotoId === photo.id;

  return (
    <div style={style} className="p-1.5">
      <PhotoCell
        photo={photo}
        index={index}
        isSelected={isSelected}
        isAdding={isAdding}
        onPhotoOpen={onPhotoOpen}
        onToggleSelect={onToggleSelect}
      />
    </div>
  );
}

const PhotoCell = memo(
  function PhotoCell({
    photo,
    index,
    isSelected,
    isAdding,
    onPhotoOpen,
    onToggleSelect,
  }: {
    photo: Photo;
    index: number;
    isSelected: boolean;
    isAdding: boolean;
    onPhotoOpen?: (index: number) => void;
    onToggleSelect?: (photo: Photo) => void;
  }) {
    const cellRef = useRef<HTMLDivElement>(null);

    function handleToggle(e: React.MouseEvent) {
      e.stopPropagation();
      if (!isSelected) flyToCart(cellRef.current);
      onToggleSelect?.(photo);
    }

    return (
      <div
        ref={cellRef}
        className={`group relative h-full w-full overflow-hidden rounded-xl bg-surface-alt shadow-soft ${
          isSelected ? "ring-2 ring-brand-accent ring-offset-2 ring-offset-surface" : ""
        }`}
      >
        <button
          type="button"
          onClick={() => onPhotoOpen?.(index)}
          className="block h-full w-full"
          aria-label={`Agrandir ${photo.original_filename}`}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={photo.thumbnail_url}
            alt={photo.original_filename}
            loading="lazy"
            className={`h-full w-full object-cover ${isSelected ? "scale-105" : ""}`}
          />
        </button>

        {onToggleSelect && (
          <button
            type="button"
            disabled={isAdding}
            onClick={handleToggle}
            aria-label={isSelected ? "Retirer du panier" : "Ajouter au panier"}
            className={`glass-pill absolute right-1.5 top-1.5 flex h-7 w-7 items-center justify-center text-xs font-bold shadow active:scale-90 disabled:opacity-60 ${
              isSelected ? "!bg-brand-accent !text-brand" : "text-white"
            }`}
          >
            {isAdding ? (
              <span className="h-2.5 w-2.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
            ) : isSelected ? (
              <CheckIcon />
            ) : null}
          </button>
        )}
      </div>
    );
  },
  (prev, next) =>
    prev.photo.id === next.photo.id &&
    prev.index === next.index &&
    prev.isSelected === next.isSelected &&
    prev.isAdding === next.isAdding &&
    prev.onPhotoOpen === next.onPhotoOpen &&
    prev.onToggleSelect === next.onToggleSelect
);
