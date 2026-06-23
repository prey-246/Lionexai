'use client';

import { useState, useEffect } from 'react';
import { portfolioAPI, systemAPI } from '@/lib/api';
import type { Portfolio, RiskMandate } from '@/lib/types';
import { PageHeader } from '@/components/ui/PageHeader';
import { Loader2, PlusCircle, Trash2, Wallet, ArrowRight } from 'lucide-react';
import Link from 'next/link';
import MandateBadge from '@/components/ui/MandateBadge';

export default function PortfoliosPage() {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [mandates, setMandates] = useState<RiskMandate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newPortfolioId, setNewPortfolioId] = useState('');
  const [initialEquity, setInitialEquity] = useState(100000);
  const [selectedMandate, setSelectedMandate] = useState('');

  useEffect(() => {
    const fetchInitialData = async () => {
      setLoading(true);
      try {
        const [portfolioData, mandateData] = await Promise.all([
          portfolioAPI.listPortfolios(),
          systemAPI.getMandates(),
        ]);
        setPortfolios(portfolioData);
        setMandates(mandateData);
        if (mandateData.length > 0) {
          setSelectedMandate(mandateData[0].pk_id.toString());
        }
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchInitialData();
  }, []);

  const handleCreate = async () => {
    if (!newPortfolioId || !selectedMandate) return;
    try {
      const newPortfolio = await portfolioAPI.createPortfolio({ id: newPortfolioId, mandate_pk_id: selectedMandate, total_equity: initialEquity });
      setPortfolios([...portfolios, newPortfolio]);
      setNewPortfolioId('');
    } catch (err: any) {
      alert(`Failed to create portfolio: ${err.message}`);
    }
  };

  const handleDelete = async (id: string) => {
    if (confirm(`Are you sure you want to delete portfolio "${id}"?`)) {
      try {
        await portfolioAPI.deletePortfolio(id);
        setPortfolios(portfolios.filter(p => p.id !== id));
      } catch (err: any) {
        alert(`Failed to delete portfolio: ${err.message}`);
      }
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader title="Portfolio Management" subtitle="Create and manage your trading portfolios" />

      {/* Create Portfolio Form */}
      <div className="card">
        <h3 className="text-[15px] font-semibold text-text-primary mb-5 flex items-center gap-2">
          <PlusCircle className="w-5 h-5 text-primary-blue" />
          Create New Portfolio
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
          <div>
            <label className="block text-[12px] font-medium text-text-muted mb-1.5">Portfolio ID</label>
            <input 
              type="text" 
              value={newPortfolioId}
              onChange={(e) => setNewPortfolioId(e.target.value)}
              className="w-full px-3 py-2.5 text-[14px] rounded-lg"
              placeholder="e.g., my-algo-portfolio"
            />
          </div>
          <div>
            <label className="block text-[12px] font-medium text-text-muted mb-1.5">Risk Mandate</label>
            <select
              value={selectedMandate}
              onChange={(e) => setSelectedMandate(e.target.value)}
              className="w-full px-3 py-2.5 text-[14px] rounded-lg"
            >
              {mandates.map(m => <option key={m.pk_id} value={m.pk_id}>{m.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-[12px] font-medium text-text-muted mb-1.5">Initial Capital</label>
            <input 
              type="number" 
              value={initialEquity}
              onChange={(e) => setInitialEquity(Number(e.target.value))}
              className="w-full px-3 py-2.5 text-[14px] rounded-lg"
              step={10000}
              min={1000}
            />
          </div>
          <button onClick={handleCreate} className="btn primary btn-full">
            <PlusCircle className="w-4 h-4" /> Create Portfolio
          </button>
        </div>
      </div>

      {/* Portfolio List */}
      <div>
        <h3 className="sec-head">All Portfolios</h3>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {portfolios.length > 0 ? portfolios.map(p => (
            <div key={p.id} className="card group relative flex flex-col gap-3">
              <Link href={`/portfolios/${p.id}`} className="absolute inset-0 z-0" aria-label={`Open portfolio ${p.id}`} />
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2.5">
                  <span className="grid place-items-center w-9 h-9 rounded-lg bg-system-gBg border border-system-gBd text-primary-gold-bright">
                    <Wallet className="w-4 h-4" />
                  </span>
                  <span className="font-mono text-[14px] font-bold text-primary-gold-bright group-hover:text-primary-emerald-bright transition-colors">{p.id}</span>
                </div>
                <button onClick={(e) => { e.preventDefault(); handleDelete(p.id); }} className="relative z-10 text-text-muted hover:text-danger transition-colors" aria-label={`Delete ${p.id}`}>
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
              <MandateBadge mandateId={p.mandate_id} />
              <div className="flex items-end justify-between pt-2 border-t border-border-subtle">
                <div>
                  <div className="font-mono text-[10px] uppercase tracking-wider text-text-muted">Equity</div>
                  <div className="font-display text-[22px] font-bold text-text-primary tabular-nums">${p.total_equity.toLocaleString()}</div>
                </div>
                <ArrowRight className="w-4 h-4 text-text-muted group-hover:translate-x-1 group-hover:text-primary-emerald-bright transition-all" />
              </div>
            </div>
          )) : (
            <div className="card text-center text-text-muted col-span-full py-10">No portfolios found. Create one to get started.</div>
          )}
        </div>
      </div>
    </div>
  );
}