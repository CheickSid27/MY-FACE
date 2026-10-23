"use client";

import { useState } from "react";
import PhotoLightbox from "@/components/gallery/PhotoLightbox";
import { CheckIcon } from "@/components/icons";
import type { FaceCluster, Photo } from "@/types/api";

/** Les photos d'une personne (« Personne N, X photos ») : utilisee par
 * « Trouver mon visage » et par les bulles des visages de la visionneuse. */
export default function PersonPhotos({
  cluster,
  numero,
  photos,
  onClose,
  selectedPhotoIds,
  onToggleSelect,
  onBulkSelect,
  addingPhotoId,
  eventId,
  zClass = "z-[55]",
}: {
  cluster: FaceCluster;
  // numero d'affichage, a partir de 1 (cluster_id commence a 0 et peut sauter)
  numero: number;
  photos: Photo[];
  onClose: () => void;
  selectedPhotoIds: Set<string>;
  onToggleSelect: (photo: Photo) => void;
  onBulkSelect?: (photos: Photo[]) => void;
  addingPhotoId?: string | null;
  // evenement : bulles des visages dans la visionneuse
  eventId?: string;
  zClass?: string;
}) {
  const [index, setIndex] = useState<number | null>(null);
  const allSelected = photos.length > 0 && photos.every((p) => selectedPhotoIds.has(p.id));

  if (index === null) {
    return (
      <div
        className={`fixed inset-0 ${zClass} flex items-center justify-center bg-brand/80 p-4 backdrop-blur-sm animate-fade-in`}
        onClick={onClose}
      >
        <div
          className="glass-strong max-h-[80vh] w-full max-w-xl overflow-y-auto rounded-2xl p-5 shadow-elevated animate-scale-in"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="mb-4 flex items-center justify-between gap-3">
            <h3 className="font-semibold text-ink-900">
              Personne {numero}, {cluster.photo_count} photo{cluster.photo_count > 1 ? "s" : ""}
            </h3>
            <button
              type="button"
              onClick={onClose}
              className="glass-pill flex h-8 w-8 shrink-0 items-center justify-center text-ink-500 transition hover:text-ink-900"
            >
              &times;
            </button>
          </div>
          {onBulkSelect && (
            <button
              type="button"
              disabled={allSelected}
              onClick={() => onBulkSelect(photos)}
              className="btn-accent mb-4 w-full !py-2.5 text-sm disabled:cursor-default disabled:opacity-60"
            >
              {allSelected ? "Toutes ces photos sont dans le panier" : `Tout sélectionner (${photos.length})`}
            </button>
          )}
          <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
            {photos.map((photo, i) => {
              const isSelected = selectedPhotoIds.has(photo.id);
              return (
                <div key={photo.id} className="group relative aspect-square overflow-hidden rounded-lg">
                  {/* Bouton pleine vignette = ouvrir la visionneuse. Bouton
                      distinct en coin = sélectionner/deselectionner sans
                      quitter la grille (stopPropagation pour ne pas aussi
                      ouvrir la visionneuse), l'un remplacait l'autre avant
                      ce correctif, rendant la sélection individuelle
                      impossible depuis cette vue. */}
                  <button type="button" onClick={() => setIndex(i)} className="block h-full w-full">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={photo.thumbnail_url}
                      alt={photo.original_filename}
                      className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
                    />
                  </button>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onToggleSelect(photo);
                    }}
                    aria-label={isSelected ? "Retirer du panier" : "Ajouter au panier"}
                    className={`glass-pill absolute right-1.5 top-1.5 flex h-7 w-7 items-center justify-center text-xs font-bold shadow transition-all duration-200 active:scale-90 ${
                      isSelected ? "!bg-brand-accent !text-brand" : "text-white"
                    }`}
                  >
                    {isSelected ? <CheckIcon /> : null}
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  }

  // Fermer la visionneuse ramene aux photos de CETTE personne (et non a la
  // liste de tous les visages, qu'il fallait alors re-parcourir en entier).
  return (
    <PhotoLightbox
      photos={photos}
      index={index}
      onClose={() => setIndex(null)}
      onNavigate={setIndex}
      selectedPhotoIds={selectedPhotoIds}
      onToggleSelect={onToggleSelect}
      onBulkSelect={onBulkSelect}
      addingPhotoId={addingPhotoId}
      eventId={eventId}
    />
  );
}
