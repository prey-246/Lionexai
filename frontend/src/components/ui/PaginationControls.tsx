'use client';

import { useRouter, useSearchParams, usePathname } from 'next/navigation';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface PaginationControlsProps {
  totalItems: number;
  perPage: number;
}

export function PaginationControls({ totalItems, perPage }: PaginationControlsProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const page = searchParams.get('page') ?? '1';
  const currentPage = Number(page);
  const totalPages = Math.ceil(totalItems / perPage);

  const handleNav = (newPage: number) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set('page', String(newPage));
    router.push(`${pathname}?${params.toString()}`);
  };

  return (
    <div className="flex items-center justify-between gap-4 mt-6 flex-wrap">
      <p className="text-[13px] text-text-muted font-mono">
        Page <span className="text-text-primary font-bold">{currentPage}</span> of <span className="text-text-primary font-bold">{totalPages || 1}</span>
      </p>
      <div className="flex items-center gap-2">
        <button onClick={() => handleNav(currentPage - 1)} disabled={currentPage <= 1} className="flex items-center gap-2 px-4 py-2 text-[13px] font-medium rounded-lg border border-border-default bg-background-panel text-text-secondary hover:bg-background-elevated hover:text-text-primary hover:border-border-strong disabled:opacity-40 disabled:cursor-not-allowed transition-colors">
          <ChevronLeft className="w-4 h-4" />
          Previous
        </button>
        <button onClick={() => handleNav(currentPage + 1)} disabled={currentPage >= totalPages} className="flex items-center gap-2 px-4 py-2 text-[13px] font-medium rounded-lg border border-border-default bg-background-panel text-text-secondary hover:bg-background-elevated hover:text-text-primary hover:border-border-strong disabled:opacity-40 disabled:cursor-not-allowed transition-colors">
          Next
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}