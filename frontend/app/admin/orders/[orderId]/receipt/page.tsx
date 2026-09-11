"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import OrderReceipt from "@/components/admin/OrderReceipt";
import RequireAuth from "@/components/admin/RequireAuth";
import { PrinterIcon } from "@/components/icons";
import { api, ApiError } from "@/lib/api-client";
import type { OrderDetail } from "@/types/api";

// Recu imprimable d'une commande (A4), ouvert depuis la fiche commande de
// l'admin : a imprimer ou enregistrer en PDF pour le remettre a un client.
function ReceiptContent() {
  const { orderId } = useParams<{ orderId: string }>();
  const [order, setOrder] = useState<OrderDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getOrder(orderId)
      .then(setOrder)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Impossible de charger la commande."));
  }, [orderId]);

  if (error) return <p className="p-6 text-red-600">{error}</p>;
  if (!order) return <p className="p-6 text-ink-500">Chargement...</p>;

  return (
    <>
      <style>{`
        @page { size: A4 portrait; margin: 12mm; }
        @media print { html, body { background: #fff !important; } }
      `}</style>
      <div className="flex items-center justify-between gap-3 p-4 print:hidden">
        <p className="text-sm text-ink-500">Recu de la commande {order.id.slice(0, 8).toUpperCase()}</p>
        <button type="button" onClick={() => window.print()} className="btn-accent flex items-center gap-2 !px-5 !py-2.5 text-sm">
          <PrinterIcon /> Imprimer
        </button>
      </div>
      <main className="mx-auto max-w-[190mm] bg-white p-8 shadow-card print:p-0 print:shadow-none">
        <OrderReceipt order={order} />
        <p className="mt-6 text-center text-[10px] text-ink-300">
          Document genere le {new Date().toLocaleString("fr-FR")} depuis l&apos;espace organisateur MYFACE.
        </p>
      </main>
    </>
  );
}

export default function ReceiptPage() {
  return (
    <RequireAuth>
      <ReceiptContent />
    </RequireAuth>
  );
}
