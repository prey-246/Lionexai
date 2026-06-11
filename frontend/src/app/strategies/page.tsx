'use client';

import { useState, useEffect } from 'react';
import { PageHeader } from '@/components/ui/PageHeader';
import { strategiesAPI, portfolioAPI } from '@/lib/api';
import { Loader2, FlaskConical, Play, Settings2, Database, Wallet } from 'lucide-react';
import Link from 'next/link';

export default function StrategyRegistryPage() {
  const [strategies, setStrategies] = useState<any[]>([]);
  const [portfolios, setPortfolios] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  
  const [isAssignModalOpen, setIsAssignModalOpen] = useState(false);
  const [assignForm, setAssignForm] = useState({ strategyId: '', portfolioId: '' });
  const [assigning, setAssigning] = useState(false);

  useEffect(() => {
    Promise.all([
      strategiesAPI.listStrategies(),
      portfolioAPI.listPortfolios()
    ])
      .then(([stratsData, portsData]) => {
        setStrategies(stratsData || []);
        setPortfolios(portsData || []);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleAssign = async () => {
    if (!assignForm.portfolioId) return alert("Please select a portfolio.");
    setAssigning(true);
    try {
      const strat = strategies.find(s => s.id === assignForm.strategyId);
      const updatedParams = { ...strat.parameters, assigned_portfolio_id: assignForm.portfolioId };
      
      await strategiesAPI.updateStrategy(strat.id, {
        parameters: updatedParams,
        is_active: true
      });
      
      alert(`Strategy ${strat.name} assigned and activated!`);
      setIsAssignModalOpen(false);
      const updatedStrats = await strategiesAPI.listStrategies();
      setStrategies(updatedStrats || []);
    } catch (err: any) {
      alert(err.message || 'Failed to assign strategy.');
    } finally {
      setAssigning(false);
    }
  };

  if (loading) return <div className="flex justify-center items-center h-64"><Loader2 className="w-8 h-8 animate-spin text-primary-gold" /></div>;

  return (
    <div className="space-y-8">
      <PageHeader title="Strategy Registry" subtitle="Repository of quantitative models and algorithmic parameters for review and deployment." />

      {strategies.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-64 text-center space-y-4">
          <FlaskConical className="w-12 h-12 text-primary-gold opacity-50" />
          <div>
            <h3 className="font-serif text-[20px] text-text-primary">No Strategies Found</h3>
            <p className="font-sans text-[13px] text-text-secondary mt-1">Execute a backtest and save a winning model to populate the registry.</p>
          </div>
          <Link href="/backtest" className="btn gold mt-4">Go to Strategy Engine</Link>
        </div>
      ) : (
        <div className="g3">
          {strategies.map((strategy: any) => (
            <div key={strategy.id} className="card grey shadow-lg flex flex-col justify-between">
              <div>
                <div className="flex items-center gap-3 mb-4 border-b border-border-default pb-4">
                  <div className="p-2 bg-background-base rounded-[3px] border border-border-default">
                    <Database className="w-5 h-5 text-primary-gold" />
                  </div>
                  <div>
                    <h3 className="font-serif text-[20px] font-bold text-text-primary leading-none">{strategy.name}</h3>
                    <span className="font-mono text-[9px] text-text-muted uppercase tracking-wider mt-1 block">ID: {strategy.id}</span>
                  </div>
                </div>
                
                <p className="font-sans text-[13px] text-text-secondary leading-relaxed mb-6 h-10 overflow-hidden text-ellipsis">
                  {strategy.description || "No description provided."}
                </p>

                <div className="space-y-3 mb-6">
                  <div className="flex justify-between items-center border-b border-border-subtle pb-2">
                    <span className="font-mono text-[10px] text-text-muted uppercase tracking-wider">Algorithm</span>
                    <span className="tag blue">{strategy.parameters?.strategy_type || "UNKNOWN"}</span>
                  </div>
                  <div className="flex justify-between items-center border-b border-border-subtle pb-2">
                    <span className="font-mono text-[10px] text-text-muted uppercase tracking-wider">Status</span>
                    {strategy.is_active ? <span className="tag teal">Active</span> : <span className="tag grey">Pending Review</span>}
                  </div>
                  {strategy.parameters?.assigned_portfolio_id && (
                    <div className="flex justify-between items-center border-b border-border-subtle pb-2">
                      <span className="font-mono text-[10px] text-text-muted uppercase tracking-wider">Assigned To</span>
                      <span className="font-mono font-bold text-primary-gold flex items-center gap-1"><Wallet className="w-3 h-3"/> {strategy.parameters.assigned_portfolio_id}</span>
                    </div>
                  )}
                </div>
                
                <div className="mb-6">
                   <span className="block font-mono text-[9px] uppercase tracking-wider text-text-muted mb-2">Key Parameters</span>
                   <div className="bg-background-base border border-border-subtle rounded-[3px] p-3 overflow-x-auto">
                     <pre className="font-mono text-[10px] text-text-secondary whitespace-pre-wrap">
                       {JSON.stringify(Object.keys(strategy.parameters || {}).filter(k => !['strategy_type', 'assigned_portfolio_id'].includes(k)).reduce((obj, key) => { obj[key] = strategy.parameters[key]; return obj; }, {} as any), null, 2)}
                     </pre>
                   </div>
                </div>
              </div>

              <div className="flex gap-3 pt-4 border-t border-border-default">
                <button onClick={() => { setAssignForm({ strategyId: strategy.id, portfolioId: '' }); setIsAssignModalOpen(true); }} className="btn teal btn-full flex items-center justify-center gap-2 shadow-lg">
                   <Play className="w-3 h-3" /> Assign to Portfolio
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Assign Modal Overlay */}
      {isAssignModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4">
           <div className="card gold w-full max-w-lg shadow-2xl">
              <h3 className="font-serif text-[24px] text-text-primary mb-6">Assign Strategy to Portfolio</h3>
              <p className="font-sans text-[13px] text-text-secondary mb-6">Link this quantitative strategy to an active paper trading portfolio to begin simulated autonomous execution.</p>
              <div className="space-y-4">
                <div>
                  <label className="block font-mono text-[9px] uppercase tracking-wider text-text-muted mb-1.5">Select Target Portfolio</label>
                  <select className="w-full border border-border-default rounded-[3px] px-3 py-2 font-sans text-[13px] focus:outline-none focus:border-primary-gold" value={assignForm.portfolioId} onChange={e => setAssignForm({...assignForm, portfolioId: e.target.value})}>
                    <option value="">-- Choose Portfolio --</option>
                    {portfolios.map(p => <option key={p.id} value={p.id}>{p.id} (Equity: ${p.total_equity?.toLocaleString()})</option>)}
                  </select>
                </div>
              </div>
              <div className="flex justify-end gap-3 mt-8 pt-4 border-t border-border-default">
                 <button onClick={() => setIsAssignModalOpen(false)} className="btn grey">Cancel</button>
                 <button onClick={handleAssign} className="btn teal" disabled={assigning || !assignForm.portfolioId}>{assigning ? <Loader2 className="w-4 h-4 animate-spin mr-1"/> : null} Confirm Assignment</button>
              </div>
           </div>
        </div>
      )}
    </div>
  );
}