'use client';

import { useRouter, useSearchParams, usePathname } from 'next/navigation';

const filterOptions = [
  { value: 'ALL', label: 'All Event Types' },
  { value: 'RISK_REJECTION', label: 'Risk Rejection' },
  { value: 'KILL_SWITCH_TRIGGERED', label: 'Kill Switch' },
  { value: 'TRADE_EXECUTED', label: 'Trade Executed' },
  { value: 'REPORT_GENERATED', label: 'Report Generated' },
];

export function FilterControls() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const currentFilter = searchParams.get('filter') || 'ALL';

  const handleFilterChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newFilter = e.target.value;
    const params = new URLSearchParams(searchParams.toString());
    
    if (newFilter === 'ALL') {
      params.delete('filter');
    } else {
      params.set('filter', newFilter);
    }
    // Reset to page 1 when filter changes
    params.set('page', '1');
    router.push(`${pathname}?${params.toString()}`);
  };

  return (
    <select
      id="action-filter"
      aria-label="Filter event types"
      className="block w-full max-w-xs pl-3 pr-10 py-2.5 text-[13px] rounded-lg border border-border-default bg-background-panel text-text-primary"
      onChange={handleFilterChange}
      value={currentFilter}
    >
      {filterOptions.map(option => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  );
}