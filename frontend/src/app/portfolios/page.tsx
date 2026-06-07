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
      <div className="bg-background-panel-1 border border-border-secondary rounded-lg p-6">
        <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
          <PlusCircle className="w-5 h-5 text-primary-blue" />
          Create New Portfolio
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
          <div>
            <label className="block text-xs font-medium text-text-muted mb-1">Portfolio ID</label>
            <input 
              type="text" 
              value={newPortfolioId}
              onChange={(e) => setNewPortfolioId(e.target.value)}
              className="w-full bg-background-panel-2 border border-border-secondary rounded-md px-3 py-2 text-sm focus:outline-none focus:border-primary-blue transition-colors"
              placeholder="e.g., my-algo-portfolio"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-text-muted mb-1">Risk Mandate</label>
            <select
              value={selectedMandate}
              onChange={(e) => setSelectedMandate(e.target.value)}
              className="w-full bg-background-panel-2 border border-border-secondary rounded-md px-3 py-2 text-sm focus:outline-none focus:border-primary-blue transition-colors"
            >
              {mandates.map(m => <option key={m.pk_id} value={m.pk_id}>{m.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-text-muted mb-1">Initial Capital</label>
            <input 
              type="number" 
              value={initialEquity}
              onChange={(e) => setInitialEquity(Number(e.target.value))}
              className="w-full bg-background-panel-2 border border-border-secondary rounded-md px-3 py-2 text-sm focus:outline-none focus:border-primary-blue transition-colors"
              step={10000}
              min={1000}
            />
          </div>
          <button onClick={handleCreate} className="w-full flex items-center justify-center gap-2 bg-primary-blue hover:bg-primary-blue/80 text-white font-semibold py-2 px-4 rounded-md transition-colors">
            Create Portfolio
          </button>
        </div>
      </div>

      {/* Portfolio List */}
      <div className="bg-background-panel-1 border border-border-secondary rounded-lg">
        <ul className="divide-y divide-border-secondary">
          {portfolios.length > 0 ? portfolios.map(p => (
            <li key={p.id}>
              <Link href={`/portfolios/${p.id}`} className="p-4 flex justify-between items-center hover:bg-white/5 transition-colors group">
                <div>
                  <p className="font-mono text-primary-gold group-hover:text-primary-teal">{p.id}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <MandateBadge mandateId={p.mandate_id} />
                    <span className="text-xs text-text-muted">|</span>
                    <p className="text-xs text-text-muted">Equity: ${p.total_equity.toLocaleString()}</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <button onClick={(e) => { e.preventDefault(); handleDelete(p.id); }} className="text-danger/50 hover:text-danger transition-colors z-10">
                    <Trash2 className="w-4 h-4" />
                  </button>
                  <ArrowRight className="w-4 h-4 text-text-muted group-hover:translate-x-1 transition-transform" />
                </div>
              </Link>
            </li>
          )) : (
            <li className="p-4 text-center text-text-muted">No portfolios found. Create one to get started.</li>
          )}
        </ul>
      </div>
    </div>
  );
}