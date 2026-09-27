"use client";

import { useEffect, useState } from "react";
import PhotoLightbox from "@/components/gallery/PhotoLightbox";
import { CheckIcon, UsersIcon } from "@/components/icons";
import { api } from "@/lib/api-client";
import { getKioskToken } from "@/lib/kiosk";
import type { FaceCluster, Photo } from "@/types/api";

interface FindFacesDialogProps {
  eventId: string;
  open: boolean;
  onClose: () => void;
  selectedPhotoIds: Set<string>;
  onToggleSelect: (photo: Photo) => void;
  onBulkSelect: (photos: Photo[]) => void;
  addingPhotoId?: string | null;
}

export default function FindFacesDialog({
  eventId,
  open,
  onClose,
  selectedPhotoIds,
  onToggleSelect,
  onBulkSelect,
  addingPhotoId,
}: FindFacesDialogProps) {
  const [clusters, setClusters] = useState<FaceCluster[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCluster, setSelectedCluster] = useState<FaceCluster | null>(null);

  useEffect(() => {
    if (!open) {
      setSelectedCluster(null);
      return;
    }
    setLoading(true);
    setError(null);
    api
      .getClustersPublic(eventId, getKioskToken(eventId))
      .then((clusterData) => setClusters(clusterData.clusters))
      .catch(() => setError("Impossible de charger les visages detectes."))
      .finally(() => setLoading(false));
  }, [open, eventId]);

  if (!open) return null;

  // Chaque cluster embarque deja ses photos completes (voir backend
  // schemas/face.py) : plus besoin de recouper avec une liste paginee a
  // part, qui tronquait silencieusement les clusters au-dela des 200
  // premieres photos de l'evenement.
  const clusterPhotos = selectedCluster?.photos ?? [];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-brand/70 p-4 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="glass-strong relative flex max-h-[92vh] w-full max-w-xl flex-col overflow-hidden rounded-2xl shadow-elevated animate-scale-in"
      >
        <button
          type="button"
          onClick={onClose}
          className="glass-pill absolute right-4 top-4 z-10 flex h-9 w-9 items-center justify-center text-ink-700 transition hover:bg-white/40"
          aria-label="Fermer"
        >
          &times;
        </button>

        <div className="border-b border-ink-900/5 px-6 py-5">
          <h2 className="text-lg font-bold text-ink-900">Trouver mon visage</h2>
          <p className="mt-1 text-sm text-ink-500">
            Voici les visages detectes sur les photos de l&apos;evenement, regroupes par
            ressemblance. Cliquez sur celui qui vous correspond.
          </p>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {loading && (
            <div className="grid grid-cols-3 gap-3 sm:grid-cols-4">
              {Array.from({ length: 9 }).map((_, i) => (
                <div key={i} className="aspect-square animate-pulse rounded-xl bg-surface-alt" />
              ))}
            </div>
          )}
          {error && <p className="text-center text-sm text-red-600">{error}</p>}

          {!loading && !error && clusters.length === 0 && (
            <div className="flex flex-col items-center gap-2 py-10 text-center text-ink-500">
              <UsersIcon className="text-3xl" />
              <p>Aucun visage detecte pour le moment.</p>
            </div>
          )}

          {!loading && !error && clusters.length > 0 && (
            <div className="grid grid-cols-3 gap-3 sm:grid-cols-4">
              {clusters.map((cluster) => (
                <button
                  key={cluster.cluster_id}
                  type="button"
                  onClick={() => setSelectedCluster(cluster)}
                  className="group relative overflow-hidden rounded-xl shadow-soft transition-all duration-200 hover:-translate-y-0.5 hover:shadow-card"
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={cluster.representative_face_url}
                    alt={`Personne ${cluster.cluster_id}`}
                    className="aspect-square w-full object-cover transition-transform duration-300 group-hover:scale-105"
                  />
                  <span className="absolute bottom-1.5 right-1.5 glass-pill px-2 py-0.5 text-[10px] font-semibold text-white">
                    {cluster.photo_count}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Les clics a l'interieur de la vue d'une personne (fond, bouton
          fermer de la visionneuse...) ne doivent pas remonter jusqu'au fond
          de CE dialogue, dont le onClick ferme tout "Trouver mon visage". */}
      {selectedCluster && (
        <div onClick={(e) => e.stopPropagation()}>
          <ClusterLightbox
            cluster={selectedCluster}
            photos={clusterPhotos}
            onClose={() => setSelectedCluster(null)}
            selectedPhotoIds={selectedPhotoIds}
            onToggleSelect={onToggleSelect}
            onBulkSelect={onBulkSelect}
            addingPhotoId={addingPhotoId}
          />
        </div>
      )}
    </div>
  );
}

function ClusterLightbox({
  cluster,
  photos,
  onClose,
  selectedPhotoIds,
  onToggleSelect,
  onBulkSelect,
  addingPhotoId,
}: {
  cluster: FaceCluster;
  photos: Photo[];
  onClose: () => void;
  selectedPhotoIds: Set<string>;
  onToggleSelect: (photo: Photo) => void;
  onBulkSelect: (photos: Photo[]) => void;
  addingPhotoId?: string | null;
}) {
  const [index, setIndex] = useState<number | null>(null);
  const allSelected = photos.length > 0 && photos.every((p) => selectedPhotoIds.has(p.id));

  if (index === null) {
    return (
      <div
        className="fixed inset-0 z-[55] flex items-center justify-center bg-brand/80 p-4 backdrop-blur-sm animate-fade-in"
        onClick={onClose}
      >
        <div
          className="glass-strong max-h-[80vh] w-full max-w-xl overflow-y-auto rounded-2xl p-5 shadow-elevated animate-scale-in"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="mb-4 flex items-center justify-between gap-3">
            <h3 className="font-semibold text-ink-900">
              Personne {cluster.cluster_id}, {cluster.photo_count} photo(s)
            </h3>
            <button
              type="button"
              onClick={onClose}
              className="glass-pill flex h-8 w-8 shrink-0 items-center justify-center text-ink-500 transition hover:text-ink-900"
            >
              &times;
            </button>
          </div>
          <button
            type="button"
            disabled={allSelected}
            onClick={() => onBulkSelect(photos)}
            className="btn-accent mb-4 w-full !py-2.5 text-sm disabled:cursor-default disabled:opacity-60"
          >
            {allSelected ? "Toutes ces photos sont dans le panier" : `Tout selectionner (${photos.length})`}
          </button>
          <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
            {photos.map((photo, i) => {
              const isSelected = selectedPhotoIds.has(photo.id);
              return (
                <div key={photo.id} className="group relative aspect-square overflow-hidden rounded-lg">
                  {/* Bouton pleine vignette = ouvrir la visionneuse. Bouton
                      distinct en coin = selectionner/deselectionner sans
                      quitter la grille (stopPropagation pour ne pas aussi
                      ouvrir la visionneuse), l'un remplacait l'autre avant
                      ce correctif, rendant la selection individuelle
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
      addingPhotoId={addingPhotoId}
    />
  );
}
