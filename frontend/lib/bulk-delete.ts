// Message apres une suppression de plusieurs photos (selection ou personne).

export function bulkDeleteMessage(result: { deleted: number; kept_sold: string[] }): string {
  const parts = [`${result.deleted} photo${result.deleted > 1 ? "s" : ""} supprimée${result.deleted > 1 ? "s" : ""}.`];
  if (result.kept_sold.length > 0) {
    const n = result.kept_sold.length;
    parts.push(
      `${n} photo${n > 1 ? "s" : ""} gardée${n > 1 ? "s" : ""} car déjà vendue${n > 1 ? "s" : ""} (le client doit pouvoir la retélécharger) : ${result.kept_sold.join(", ")}.`
    );
  }
  return parts.join(" ");
}
