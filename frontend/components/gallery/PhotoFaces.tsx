"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";
import { getKioskToken } from "@/lib/kiosk";
import type { FaceCluster, Photo, PhotoFace } from "@/types/api";

// Charge a la demande (la vue d'une personne contient elle-meme une visionneuse).
const PersonPhotos = dynamic(() => import("@/components/faces/PersonPhotos"), { ssr: false });

// Au-dela de 3 visages : 3 bulles a moitie superposees, puis une 4e avec une fleche.
const VISIBLES = 3;

interface PhotoFacesProps {
  eventId: string;
  photoId: string;
  selectedPhotoIds: Set<string>;
  onToggleSelect: (photo: Photo) => void;
  onBulkSelect?: (photos: Photo[]) => void;
  addingPhotoId?: string | null;
  /** Une boite est ouverte par-dessus la visionneuse (clavier de la visionneuse en pause). */
  onOverlayChange?: (open: boolean) => void;
}

function Fleche() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  );
}

/** Bulles des visages de la photo ouverte, sous la photo : toucher un visage
 * ouvre toutes les photos de la personne, comme « Trouver mon visage ». */
export default function PhotoFaces({
  eventId,
  photoId,
  selectedPhotoIds,
  onToggleSelect,
  onBulkSelect,
  addingPhotoId,
  onOverlayChange,
}: PhotoFacesProps) {
  const [faces, setFaces] = useState<PhotoFace[] | null>(null);
  const [tous, setTous] = useState(false);
  const [personne, setPersonne] = useState<{ cluster: FaceCluster; numero: number } | null>(null);
  const [groupes, setGroupes] = useState<FaceCluster[] | null>(null);

  useEffect(() => {
    let annule = false;
    setFaces(null);
    api
      .getPhotoFaces(photoId, eventId, getKioskToken(eventId))
      .then((r) => !annule && setFaces(r.faces))
      .catch(() => !annule && setFaces([]));
    return () => {
      annule = true;
    };
  }, [photoId, eventId]);

  useEffect(() => {
    onOverlayChange?.(tous || personne !== null);
  }, [tous, personne, onOverlayChange]);

  async function ouvrirPersonne(face: PhotoFace) {
    if (face.cluster_id === null) return;
    let liste = groupes;
    if (!liste) {
      try {
        liste = (await api.getClustersPublic(eventId, getKioskToken(eventId))).clusters;
        setGroupes(liste);
      } catch {
        return;
      }
    }
    const i = liste.findIndex((c) => c.cluster_id === face.cluster_id);
    if (i >= 0) {
      setTous(false);
      setPersonne({ cluster: liste[i], numero: i + 1 });
    }
  }

  if (!faces || faces.length === 0) return <div className="h-9" aria-hidden />;

  const deborde = faces.length > VISIBLES;
  const visibles = deborde ? faces.slice(0, VISIBLES) : faces;

  return (
    <>
      <div className="flex h-9 items-center" aria-label="Visages sur cette photo">
        {visibles.map((face, i) => (
          <button
            key={face.id}
            type="button"
            onClick={() => ouvrirPersonne(face)}
            aria-label="Voir toutes les photos de cette personne"
            style={{ zIndex: i + 1 }}
            className={`relative h-9 w-9 shrink-0 overflow-hidden rounded-full ring-2 ring-white/80 transition active:scale-95 ${
              i === 0 ? "" : deborde ? "-ml-[18px]" : "ml-1.5"
            }`}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={face.face_url} alt="" className="h-full w-full object-cover" />
          </button>
        ))}
        {deborde && (
          <button
            type="button"
            onClick={() => setTous(true)}
            aria-label={`Voir les ${faces.length} visages de cette photo`}
            style={{ zIndex: VISIBLES + 1 }}
            className="relative -ml-[18px] flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-accent text-brand ring-2 ring-white/80 transition active:scale-95"
          >
            <Fleche />
          </button>
        )}
      </div>

      {tous && (
        <div
          className="fixed inset-0 z-[70] flex items-center justify-center bg-brand/70 p-4 backdrop-blur-sm animate-fade-in"
          onClick={() => setTous(false)}
        >
          <div
            className="glass-strong max-h-[80vh] w-full max-w-md overflow-y-auto rounded-2xl p-5 shadow-elevated animate-scale-in"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-4 flex items-center justify-between gap-3">
              <h3 className="font-semibold text-ink-900">Les visages de cette photo</h3>
              <button
                type="button"
                onClick={() => setTous(false)}
                aria-label="Fermer"
                className="glass-pill flex h-8 w-8 shrink-0 items-center justify-center text-ink-500 transition hover:text-ink-900"
              >
                &times;
              </button>
            </div>
            <div className="grid grid-cols-4 gap-2">
              {faces.map((face) => (
                <button
                  key={face.id}
                  type="button"
                  onClick={() => ouvrirPersonne(face)}
                  aria-label="Voir toutes les photos de cette personne"
                  className="aspect-square overflow-hidden rounded-xl transition active:scale-95"
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={face.face_url} alt="" className="h-full w-full object-cover" />
                </button>
              ))}
            </div>
            <p className="mt-4 text-center text-sm text-ink-500">
              Toucher un visage&nbsp;: toutes ses photos, comme «&nbsp;Trouver mon visage&nbsp;».
            </p>
          </div>
        </div>
      )}

      {personne && (
        <div onClick={(e) => e.stopPropagation()}>
          <PersonPhotos
            cluster={personne.cluster}
            numero={personne.numero}
            photos={personne.cluster.photos}
            onClose={() => setPersonne(null)}
            selectedPhotoIds={selectedPhotoIds}
            onToggleSelect={onToggleSelect}
            onBulkSelect={onBulkSelect}
            addingPhotoId={addingPhotoId}
            eventId={eventId}
            zClass="z-[75]"
          />
        </div>
      )}
    </>
  );
}
