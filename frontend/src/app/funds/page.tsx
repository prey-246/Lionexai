'use client';

import { useState, useEffect } from 'react';
import { PageHeader } from '@/components/ui/PageHeader';
import { GlobalMarketIntelligence } from '@/components/intelligence/GlobalMarketIntelligence';
import { fundsAPI, portfolioAPI, type FundProduct } from '@/lib/api';
import { Shield, Zap, Target, Loader2, ArrowRight, Briefcase, Landmark, Layers, RefreshCw, Wallet, BrainCircuit } from 'lucide-react';
import Link from 'next/link';

const FUND_VISUALS: Record<string, { color: string; btnColor: string; icon: any }> = {
  PRESERVE: { color: 'teal', btnColor: 'teal', icon: Shield },
  BALANCE: { color: 'blue', btnColor: 'gold', icon: Target },
  ALPHA: { color: 'gold', btnColor: 'gold', icon: Zap },
};

const CLASS_COLORS: Record<string, string> = {
  CRYPTO: 'text-primary-gold-bright border-system-gBd bg-system-gBg',
  METAL: 'text-primary-emerald-bright border-system-tBd bg-system-tBg',
  ENERGY: 'text-danger border-system-rBd bg-system-rBg',
  EQUITY_INDEX: 'text-primary-blue border-border-default bg-background-panel',
  FX: 'text-text-secondary border-border-default bg-background-panel',
};

export default function FundsPage() {
  const [funds, setFunds] = useState<FundProduct[]>([]);
  const [portfolios, setPortfolios] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const [investModal, setInvestModal] = useState<{ isOpen: boolean; fund: FundProduct | null; amount: number }>({ isOpen: false, fund: null, amount: 100000 });
  const [investing, setInvesting] = useState(false);
  const [investedPortfolioId, setInvestedPortfolioId] = useState<string | null>(null);

  const loadData = () => {
    Promise.all([fundsAPI.listFunds(), portfolioAPI.listPortfolios()])
      .then(([fundsData, portfoliosData]) => {
        setFunds(fundsData || []);
        setPortfolios(portfoliosData || []);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(loadData, []);

  const handleInvest = async () => {
    if (!investModal.fund) return;
    setInvesting(true);
    try {
      const portfolio = await fundsAPI.invest(investModal.fund.id, investModal.amount);
      setInvestedPortfolioId(portfolio.id);
      const updated = await portfolioAPI.listPortfolios();
      setPortfolios(updated || []);
    } catch (err: any) {
      alert(err.message || 'Failed to invest in fund.');
    } finally {
      setInvesting(false);
    }
  };

  const closeModal = () => {
    setInvestModal({ isOpen: false, fund: null, amount: 100000 });
    setInvestedPortfolioId(null);
  };

  if (loading) return <div className="flex justify-center items-center h-64"><Loader2 className="w-8 h-8 animate-spin text-primary-gold" /></div>;

  return (
    <div className="space-y-8">
      <PageHeader
        title="LionexAI Funds"
        subtitle="Autonomous, AI-managed multi-asset investment products. Pick a mandate, deposit capital — the engine allocates, rebalances and manages risk for you."
      />

      <GlobalMarketIntelligence />

      <div className="g3">
        {funds.map((fund) => {
          const visuals = FUND_VISUALS[fund.id] ?? { color: 'grey', btnColor: 'blue', icon: Briefcase };
          const Icon = visuals.icon;
          const iconColorClass = visuals.color === 'grey' ? 'text-primary-blue' : visuals.color === 'teal' ? 'text-primary-emerald' : `text-primary-${visuals.color}`;
          const policy = fund.allocation_policy || {};
          const totalInvested = portfolios
            .filter((p) => p.mandate_id === fund.mandate_id)
            .reduce((sum, p) => sum + (p.total_equity || 0), 0);

          return (
            <div key={fund.id} className={`card ${visuals.color} shadow-lg flex flex-col justify-between`}>
              <div>
                <div className="flex items-center gap-3 mb-5 border-b border-border-default pb-4">
                  <div className="p-3 bg-background-base rounded-xl border border-border-default">
                    <Icon className={`w-6 h-6 ${iconColorClass}`} />
                  </div>
                  <div className="min-w-0">
                    <h3 className="font-display text-[21px] font-bold text-text-primary leading-tight">{fund.name}</h3>
                    <span className="font-mono text-[10px] text-text-muted uppercase tracking-wider mt-1 block">
                      {fund.risk_label} risk · Mandate {fund.mandate_id}
                    </span>
                  </div>
                </div>

                <p className="font-sans text-[13px] text-text-secondary leading-relaxed mb-5 min-h-[60px]">
                  {fund.description}
                </p>

                {/* Asset universe */}
                <div className="mb-5">
                  <span className="font-mono text-[10px] text-text-muted uppercase tracking-wider flex items-center gap-1.5 mb-2">
                    <Layers className="w-3 h-3" /> Asset Universe ({fund.asset_universe.length})
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {fund.asset_universe.map((a) => (
                      <span key={a.symbol} className={`font-mono text-[10px] px-2 py-0.5 rounded-md border ${CLASS_COLORS[a.asset_class] ?? CLASS_COLORS.FX}`} title={`${a.display_name} (${a.asset_class})`}>
                        {a.symbol}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="space-y-2.5 mb-6">
                  <div className="flex justify-between items-center border-b border-border-subtle pb-2">
                    <span className="font-mono text-[10px] text-text-muted uppercase tracking-wider">Target Weekly</span>
                    <span className="font-mono font-bold text-primary-emerald-bright">
                      {fund.target_weekly_return_pct != null ? `${fund.target_weekly_return_pct}%` : '—'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center border-b border-border-subtle pb-2">
                    <span className="font-mono text-[10px] text-text-muted uppercase tracking-wider">Target Monthly</span>
                    <span className="font-mono font-bold text-primary-emerald-bright">
                      {fund.target_monthly_return_pct != null ? `${fund.target_monthly_return_pct}%` : '—'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center border-b border-border-subtle pb-2">
                    <span className="font-mono text-[10px] text-text-muted uppercase tracking-wider flex items-center gap-1.5"><BrainCircuit className="w-3 h-3" /> Strategy</span>
                    <span className="font-mono font-bold text-text-primary capitalize">{(policy.method || 'auto').toString().replace('_', ' ')}</span>
                  </div>
                  <div className="flex justify-between items-center border-b border-border-subtle pb-2">
                    <span className="font-mono text-[10px] text-text-muted uppercase tracking-wider flex items-center gap-1.5"><RefreshCw className="w-3 h-3" /> Rebalance</span>
                    <span className="font-mono font-bold text-text-primary">Every {policy.rebalance_freq_days ?? 7}d</span>
                  </div>
                  <div className="flex justify-between items-center border-b border-border-subtle pb-2">
                    <span className="font-mono text-[10px] text-text-muted uppercase tracking-wider">Cash Floor</span>
                    <span className="font-mono font-bold text-text-primary">{policy.cash_floor_pct ?? 0}%</span>
                  </div>
                  <div className="flex justify-between items-center pt-1">
                    <span className="font-mono text-[10px] text-text-muted uppercase tracking-wider flex items-center gap-1.5"><Landmark className="w-3 h-3 text-primary-gold" /> Total Invested</span>
                    <span className="font-mono font-bold text-text-primary">${totalInvested.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                  </div>
                </div>
              </div>

              <button onClick={() => setInvestModal({ isOpen: true, fund, amount: 100000 })} className={`btn ${visuals.btnColor} btn-full flex items-center justify-center gap-2 shadow-lg`}>
                <Wallet className="w-4 h-4" /> Invest in {fund.id} <ArrowRight className="w-3 h-3" />
              </button>
            </div>
          );
        })}
      </div>

      {/* Invest Modal */}
      {investModal.isOpen && investModal.fund && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4">
          <div className="card gold w-full max-w-lg shadow-2xl animate-fade-in-up">
            <h3 className="font-display text-[22px] font-bold text-text-primary mb-2">Invest in {investModal.fund.name}</h3>
            <p className="font-sans text-[13px] text-text-secondary mb-6">
              You are deploying capital into the AI-managed <strong className="text-primary-gold-bright">{investModal.fund.id}</strong> fund.
              The engine will automatically allocate across {investModal.fund.asset_universe.length} assets and manage risk under the {investModal.fund.mandate_id} mandate.
            </p>

            {!investedPortfolioId ? (
              <>
                <div className="space-y-4">
                  <div>
                    <label className="block font-mono text-[11px] uppercase tracking-wider text-text-muted mb-1.5">Capital Deposit ($)</label>
                    <input
                      type="number"
                      step="10000"
                      min="1000"
                      className="w-full rounded-lg px-3 py-2.5 font-sans text-[14px]"
                      value={investModal.amount}
                      onChange={(e) => setInvestModal({ ...investModal, amount: Number(e.target.value) })}
                    />
                  </div>
                  <div className="rounded-lg bg-background-base border border-border-subtle px-3 py-2.5 text-[12px] text-text-muted">
                    A fully autonomous portfolio is created instantly. No manual strategy selection required — the AllocationEngine sets target weights from current market regime and asset signals.
                  </div>
                </div>
                <div className="flex justify-end gap-3 mt-8 pt-4 border-t border-border-default">
                  <button onClick={closeModal} className="btn grey">Cancel</button>
                  <button onClick={handleInvest} className="btn teal" disabled={investing || investModal.amount <= 0}>
                    {investing ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : null} Confirm Investment
                  </button>
                </div>
              </>
            ) : (
              <div className="text-center py-6">
                <div className="w-16 h-16 bg-system-tBg border border-system-tBd rounded-full flex items-center justify-center mx-auto mb-4">
                  <BrainCircuit className="w-8 h-8 text-primary-emerald-bright" />
                </div>
                <h4 className="text-[18px] text-text-primary font-bold mb-2">Capital Deployed</h4>
                <p className="text-[13px] text-text-secondary mb-6">
                  Auto-managed portfolio <span className="font-mono text-primary-gold-bright">{investedPortfolioId}</span> created. The AI has set its initial allocation.
                </p>
                <div className="flex justify-center gap-3">
                  <button onClick={closeModal} className="btn grey">Close</button>
                  <Link href={`/portfolios/${investedPortfolioId}`} className="btn gold">View Allocation</Link>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
