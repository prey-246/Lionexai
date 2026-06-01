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
    <div className="flex items-center justify-between mt-6">
      <p className="text-sm text-text-muted">
        Page {currentPage} of {totalPages}
      </p>
      <div className="flex items-center gap-2">
        <button onClick={() => handleNav(currentPage - 1)} disabled={currentPage <= 1} className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md border border-border-secondary bg-background-panel-1 text-text-primary hover:bg-background-panel-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
          <ChevronLeft className="w-4 h-4" />
          Previous
        </button>
        <button onClick={() => handleNav(currentPage + 1)} disabled={currentPage >= totalPages} className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md border border-border-secondary bg-background-panel-1 text-text-primary hover:bg-background-panel-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
          Next
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}