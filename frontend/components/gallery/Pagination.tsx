"use client";

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  disabled?: boolean;
}

const SIBLING_COUNT = 1;

function getPageItems(current: number, total: number): (number | "...")[] {
  const items: (number | "...")[] = [1];

  const rangeStart = Math.max(2, current - SIBLING_COUNT);
  const rangeEnd = Math.min(total - 1, current + SIBLING_COUNT);

  if (rangeStart > 2) items.push("...");
  for (let i = rangeStart; i <= rangeEnd; i++) items.push(i);
  if (rangeEnd < total - 1) items.push("...");

  if (total > 1) items.push(total);
  return items;
}

export default function Pagination({ currentPage, totalPages, onPageChange, disabled }: PaginationProps) {
  if (totalPages <= 1) return null;

  const items = getPageItems(currentPage, totalPages);

  return (
    <nav className="flex items-center justify-center gap-1.5 py-1" aria-label="Pagination">
      <button
        type="button"
        disabled={disabled || currentPage === 1}
        onClick={() => onPageChange(currentPage - 1)}
        aria-label="Page precedente"
        className="glass-pill flex h-9 w-9 items-center justify-center text-sm text-ink-700 transition hover:bg-brand/10 disabled:pointer-events-none disabled:opacity-30"
      >
        &larr;
      </button>

      {items.map((item, i) =>
        item === "..." ? (
          <span key={`ellipsis-${i}`} className="px-1 text-sm text-ink-300">
            &hellip;
          </span>
        ) : (
          <button
            key={item}
            type="button"
            disabled={disabled}
            onClick={() => onPageChange(item)}
            aria-current={item === currentPage ? "page" : undefined}
            className={`flex h-9 min-w-9 items-center justify-center rounded-full px-2 text-sm font-medium transition-all duration-200 disabled:pointer-events-none ${
              item === currentPage
                ? "!bg-brand !text-white shadow-soft"
                : "glass-pill text-ink-700 hover:bg-brand/10"
            }`}
          >
            {item}
          </button>
        )
      )}

      <button
        type="button"
        disabled={disabled || currentPage === totalPages}
        onClick={() => onPageChange(currentPage + 1)}
        aria-label="Page suivante"
        className="glass-pill flex h-9 w-9 items-center justify-center text-sm text-ink-700 transition hover:bg-brand/10 disabled:pointer-events-none disabled:opacity-30"
      >
        &rarr;
      </button>
    </nav>
  );
}
