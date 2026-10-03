import { PrinterIcon } from "@/components/icons";
import MyfaceLogo from "@/components/brand/Logo";
import { METHOD_LABELS } from "@/components/payments/MethodIcon";
import { ORDER_STATUS_LABELS, orderStatusBadgeClass } from "@/lib/order-labels";
import type { OrderDetail } from "@/types/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function money(amount: number, currency: string): string {
  return `${amount.toLocaleString("fr-FR")} ${currency}`;
}

/**
 * Recu d'une commande (fiche detaillee) : de quoi repondre a un client qui
 * revient avec un probleme ("je n'ai pas recu mes photos", "il manque une
 * photo", "j'ai paye deux fois"...). Liste nominative de toutes les photos
 * achetees, tirages papier, detail du prix, et pour une commande payee le
 * lien + QR de sa page de telechargement. Utilise dans la fiche commande
 * de l'admin et sur la page imprimable /admin/orders/[id]/receipt.
 */
export default function OrderReceipt({ order }: { order: OrderDetail }) {
  const paid = order.status === "success";
  const unitPrices = Array.from(new Set(order.items.map((item) => item.unit_price)));

  return (
    <div className="text-left text-ink-900">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3 border-b border-ink-900/10 pb-4">
        <div className="flex items-start gap-3">
          <MyfaceLogo size={38} />
          <div>
          <p className="text-xs font-semibold uppercase tracking-[0.25em] text-brand-accent">MYFACE &middot; Reçu de commande</p>
          <h2 className="mt-1 text-lg font-bold">{order.event_name}</h2>
          <p className="text-xs text-ink-500">
            Événement du {new Date(order.event_date).toLocaleDateString("fr-FR")}
          </p>
          </div>
        </div>
        <div className="text-right">
          <p className="font-mono text-sm font-bold">N&deg; {order.id.slice(0, 8).toUpperCase()}</p>
          <p className="break-all font-mono text-[10px] text-ink-300">{order.id}</p>
          <span className={`mt-1 inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${orderStatusBadgeClass(order.status)}`}>
            {ORDER_STATUS_LABELS[order.status]}
          </span>
        </div>
      </div>

      <dl className="mb-4 grid grid-cols-2 gap-x-4 gap-y-2 text-sm sm:grid-cols-4">
        <div>
          <dt className="text-xs text-ink-500">Date</dt>
          <dd className="font-medium">{new Date(order.created_at).toLocaleString("fr-FR")}</dd>
        </div>
        <div>
          <dt className="text-xs text-ink-500">Client</dt>
          <dd className="font-medium">{order.contact_phone}</dd>
        </div>
        <div>
          <dt className="text-xs text-ink-500">Paiement</dt>
          <dd className="font-medium">{METHOD_LABELS[order.payment_method] ?? order.payment_method}</dd>
        </div>
        <div>
          <dt className="text-xs text-ink-500">Référence</dt>
          <dd className="break-all font-mono text-xs">{order.payment_reference ?? "-"}</dd>
        </div>
      </dl>

      <div className="mb-4 overflow-x-auto">
        <table className="w-full min-w-[420px] text-left text-sm">
          <thead>
            <tr className="border-b border-ink-900/10 text-xs uppercase tracking-wide text-ink-500">
              <th className="py-1.5 pr-2">#</th>
              <th className="py-1.5 pr-2">Photo</th>
              <th className="py-1.5 pr-2">Nom du fichier</th>
              <th className="py-1.5 pr-2 text-right">Prix</th>
              <th className="py-1.5 text-right">Tirage papier</th>
            </tr>
          </thead>
          <tbody>
            {order.items.map((item, i) => (
              <tr key={item.photo.id} className="border-b border-ink-900/5 align-middle">
                <td className="py-1.5 pr-2 text-ink-500">{i + 1}</td>
                <td className="py-1.5 pr-2">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={item.photo.thumbnail_url}
                    alt={item.photo.original_filename}
                    className="h-10 w-10 rounded object-cover"
                  />
                </td>
                <td className="break-all py-1.5 pr-2 font-medium">{item.photo.original_filename}</td>
                <td className="whitespace-nowrap py-1.5 pr-2 text-right">{money(item.unit_price, order.currency)}</td>
                <td className="whitespace-nowrap py-1.5 text-right">
                  {item.print_requested ? (
                    <span className="inline-flex items-center gap-1 font-semibold text-brand">
                      <PrinterIcon /> {money(item.print_price ?? 0, order.currency)}
                    </span>
                  ) : (
                    <span className="text-ink-300">-</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mb-4 ml-auto w-full max-w-xs space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-ink-500">
            {order.photo_count} photo(s)
            {unitPrices.length === 1 && <> &times; {money(unitPrices[0], order.currency)}</>}
          </span>
          <span>{money(order.photos_subtotal, order.currency)}</span>
        </div>
        {order.print_count > 0 && (
          <div className="flex justify-between">
            <span className="text-ink-500">{order.print_count} tirage(s) papier</span>
            <span>+{money(order.prints_total, order.currency)}</span>
          </div>
        )}
        {order.discount_amount > 0 && (
          <div className="flex justify-between text-emerald-700">
            <span>Lots / remises</span>
            <span>-{money(order.discount_amount, order.currency)}</span>
          </div>
        )}
        <div className="flex justify-between border-t border-ink-900/10 pt-1 text-base font-bold">
          <span>{paid ? "Total payé" : "Total"}</span>
          <span>{money(order.total_amount, order.currency)}</span>
        </div>
      </div>

      {order.print_count > 0 && (
        <p className="mb-4 flex items-center gap-1.5 text-sm">
          <PrinterIcon />
          {order.printed_at ? (
            <span>Tirages imprimés le {new Date(order.printed_at).toLocaleString("fr-FR")}</span>
          ) : (
            <span className="font-semibold text-amber-700">
              {paid ? "Tirages à imprimer" : "Tirages à imprimer après paiement"}
            </span>
          )}
        </p>
      )}

      {paid && (
        <div className="flex items-center gap-4 rounded-xl bg-surface-alt p-3">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={`${API_URL}/download/${order.id}/qr.png`}
            alt="QR code de téléchargement du client"
            className="h-24 w-24 shrink-0 rounded bg-white"
          />
          <div className="min-w-0 text-xs">
            <p className="font-semibold text-ink-900">Téléchargement du client (permanent)</p>
            <p className="break-all text-ink-500">{order.download_url}</p>
            <p className="mt-1 text-ink-500">
              Le client peut scanner ce QR code pour récupérer ses photos à tout moment.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
