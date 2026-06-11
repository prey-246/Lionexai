'use client';

import { useState, useEffect } from 'react';
import { PageHeader } from '@/components/ui/PageHeader';
import { systemAPI, portfolioAPI } from '@/lib/api';
import { Shield, Zap, Target, Loader2, ArrowRight, Briefcase, Landmark } from 'lucide-react';
import type { RiskMandate } from '@/lib/types';
import Link from 'next/link';

export default function FundsPage() {
  const [mandates, setMandates] = useState<RiskMandate[]>([]);
  const [portfolios, setPortfolios] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  
  const [allocateModal, setAllocateModal] = useState<{isOpen: boolean, mandate: RiskMandate | null, amount: number}>({ isOpen: false, mandate: null, amount: 100000 });
  const [allocating, setAllocating] = useState(false);
  const [allocatedPortfolioId, setAllocatedPortfolioId] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      systemAPI.getMandates(),
      portfolioAPI.listPortfolios()
    ])
      .then(([mandatesData, portfoliosData]) => {
        setMandates(mandatesData || []);
        setPortfolios(portfoliosData || []);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleAllocate = async () => {
    if (!allocateModal.mandate) return;
    setAllocating(true);
    try {
      const newPortfolioId = `PORT-${Math.floor(Math.random() * 90000) + 10000}`;
      await portfolioAPI.createPortfolio({
        id: newPortfolioId,
        mandate_pk_id: allocateModal.mandate.pk_id.toString(),
        total_equity: allocateModal.amount
      });
      
      setAllocatedPortfolioId(newPortfolioId);
      
      // Refresh portfolio data to show updated Total Allocated on the card
      const updatedPortfolios = await portfolioAPI.listPortfolios();
      setPortfolios(updatedPortfolios || []);
      
    } catch (err: any) {
      alert(err.message || 'Failed to allocate capital.');
    } finally {
      setAllocating(false);
    }
  };

  const closeAllocateModal = () => {
    setAllocateModal({ isOpen: false, mandate: null, amount: 100000 });
    setAllocatedPortfolioId(null);
  };

  if (loading) return <div className="flex justify-center items-center h-64"><Loader2 className="w-8 h-8 animate-spin text-primary-gold" /></div>;

  const getFundMarketing = (id: string) => {
    switch(id) {
      case 'PRESERVE': return { name: 'Lion Preserve Fund', target: '8-12% APY', color: 'teal', btnColor: 'teal', desc: 'Capital preservation first. Minimal volatility exposure with strict downside protection mechanisms.', icon: Shield };
      case 'BALANCE': return { name: 'Lion Balance Fund', target: '15-25% APY', color: 'blue', btnColor: 'gold', desc: 'Optimized risk-adjusted returns. Balanced allocation across core digital assets.', icon: Target };
      case 'ALPHA': return { name: 'Lion Alpha Fund', target: '40%+ APY', color: 'gold', btnColor: 'gold', desc: 'Aggressive algorithmic yield generation. High volatility tolerance for maximum capital growth.', icon: Zap };
      default: return { name: `${id} Fund`, target: 'Variable', color: 'grey', btnColor: 'blue', desc: 'Custom institutional mandate.', icon: Briefcase };
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader title="Lionex Funds" subtitle="Institutional-grade digital asset products powered by the NEXA Risk Engine." />
      
      <div className="g3">
        {mandates.map(mandate => {
          const marketing = getFundMarketing(mandate.id);
          const Icon = marketing.icon;
          const iconColorClass = marketing.color === 'grey' ? 'text-primary-blue' : marketing.color === 'teal' ? 'text-primary-emerald' : `text-primary-${marketing.color}`;

          const totalAllocated = portfolios.filter(p => p.mandate_pk_id === mandate.pk_id).reduce((sum, p) => sum + (p.total_equity || 0), 0);

          return (
            <div key={mandate.id} className={`card ${marketing.color} shadow-lg flex flex-col justify-between`}>
              <div>
                <div className="flex items-center gap-3 mb-6 border-b border-border-default pb-4">
                  <div className="p-3 bg-background-base rounded-[3px] border border-border-default">
                    <Icon className={`w-6 h-6 ${iconColorClass}`} />
                  </div>
                  <div>
                    <h3 className="font-serif text-[24px] font-bold text-text-primary leading-none">{marketing.name}</h3>
                    <span className="font-mono text-[9px] text-text-muted uppercase tracking-wider mt-1 block">Powered by: {mandate.id}</span>
                  </div>
                </div>
                
                <p className="font-sans text-[13px] text-text-secondary leading-relaxed mb-6 h-12">
                  {marketing.desc}
                </p>

                <div className="space-y-3 mb-8">
                  <div className="flex justify-between items-center border-b border-border-subtle pb-2">
                    <span className="font-mono text-[10px] text-text-muted uppercase tracking-wider">Target Return</span>
                    <span className="font-mono font-bold text-primary-emerald">{marketing.target}</span>
                  </div>
                  <div className="flex justify-between items-center border-b border-border-subtle pb-2">
                    <span className="font-mono text-[10px] text-text-muted uppercase tracking-wider">Max Drawdown</span>
                    <span className="font-mono font-bold text-danger">{mandate.max_drawdown_pct}%</span>
                  </div>
                  <div className="flex justify-between items-center border-b border-border-subtle pb-2">
                    <span className="font-mono text-[10px] text-text-muted uppercase tracking-wider">Max Leverage</span>
                    <span className="font-mono font-bold text-text-primary">{mandate.max_leverage}x</span>
                  </div>
                  <div className="flex justify-between items-center pt-2">
                    <span className="font-mono text-[10px] text-text-muted uppercase tracking-wider flex items-center gap-1.5"><Landmark className="w-3 h-3 text-primary-gold" /> Total Allocated</span>
                    <span className="font-mono font-bold text-text-primary">${totalAllocated.toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
                  </div>
                </div>
              </div>

              <button onClick={() => setAllocateModal({ isOpen: true, mandate, amount: 100000 })} className={`btn ${marketing.btnColor} btn-full flex items-center justify-center gap-2 shadow-lg`}>
                Allocate Capital <ArrowRight className="w-3 h-3" />
              </button>
            </div>
          );
        })}
      </div>

      {/* Allocation Modal Overlay */}
      {allocateModal.isOpen && allocateModal.mandate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4">
           <div className="card gold w-full max-w-lg shadow-2xl">
              <h3 className="font-serif text-[24px] text-text-primary mb-2">Allocate Capital</h3>
              <p className="font-sans text-[13px] text-text-secondary mb-6">You are creating a new portfolio governed by the <strong>{allocateModal.mandate.id}</strong> mandate.</p>
              
              {!allocatedPortfolioId ? (
                <>
                  <div className="space-y-4">
                    <div>
                      <label className="block font-mono text-[9px] uppercase tracking-wider text-text-muted mb-1.5">Initial Capital Deposit ($)</label>
                      <input type="number" step="10000" min="1000" className="w-full border border-border-default rounded-[3px] px-3 py-2 font-sans text-[13px] focus:outline-none focus:border-primary-gold" value={allocateModal.amount} onChange={e => setAllocateModal({...allocateModal, amount: Number(e.target.value)})} />
                    </div>
                  </div>
                  <div className="flex justify-end gap-3 mt-8 pt-4 border-t border-border-default">
                     <button onClick={closeAllocateModal} className="btn grey">Cancel</button>
                     <button onClick={handleAllocate} className="btn teal" disabled={allocating || allocateModal.amount <= 0}>{allocating ? <Loader2 className="w-4 h-4 animate-spin mr-1"/> : null} Confirm Allocation</button>
                  </div>
                </>
              ) : (
                <div className="text-center py-6">
                  <div className="w-16 h-16 bg-system-success/10 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Shield className="w-8 h-8 text-primary-emerald" />
                  </div>
                  <h4 className="text-[18px] text-text-primary font-bold mb-2">Capital Deployed Successfully</h4>
                  <p className="text-[13px] text-text-secondary mb-6">New Portfolio <span className="font-mono text-primary-gold">{allocatedPortfolioId}</span> has been created and funded.</p>
                  <div className="flex justify-center gap-3">
                    <button onClick={closeAllocateModal} className="btn grey">Close</button>
                    <Link href={`/portfolios`} className="btn gold">View Portfolio</Link>
                  </div>
                </div>
              )}
           </div>
        </div>
      )}
    </div>
  );
}