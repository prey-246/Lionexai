'use client';

import { useState, useEffect } from 'react';
import { PageHeader } from '@/components/ui/PageHeader';
import { MetricDisplay } from '@/components/ui/MetricDisplay';
import { treasuryAPI } from '@/lib/api';
import { Landmark, ArrowRightLeft, Loader2, Database, Shield, Activity, TrendingUp } from 'lucide-react';
import { useUser } from '@/contexts/UserContext';

export default function TreasuryDashboard() {
  const { user } = useUser();
  const [loading, setLoading] = useState(true);
  const [pools, setPools] = useState<any[]>([]);
  const [transactions, setTransactions] = useState<any[]>([]);

  const [isTransferModalOpen, setIsTransferModalOpen] = useState(false);
  const [transferForm, setTransferForm] = useState({ source: '', target: '', amount: '', description: '' });
  const [transferring, setTransferring] = useState(false);

  const fetchTreasuryData = async () => {
    try {
      setLoading(true);
      const [poolsData, txData] = await Promise.all([
        treasuryAPI.getPools(),
        treasuryAPI.getTransactions(15)
      ]);
      setPools(poolsData || []);
      setTransactions(txData || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTreasuryData();
  }, []);

  const handleSeed = async () => {
    try {
      setLoading(true);
      await treasuryAPI.seedTreasury();
      await fetchTreasuryData();
    } catch (err: any) {
      alert(`Failed to seed treasury: ${err.message}`);
      setLoading(false);
    }
  };

  const handleTransfer = async () => {
    if (!transferForm.source || !transferForm.target || !transferForm.amount) return alert("Fill all required fields");
    if (transferForm.source === transferForm.target) return alert("Source and Target cannot be the same");
    setTransferring(true);
    try {
      await treasuryAPI.transferFunds({
        source_pool_id: transferForm.source,
        target_pool_id: transferForm.target,
        amount: parseFloat(transferForm.amount),
        description: transferForm.description || "Manual Admin Transfer"
      });
      setIsTransferModalOpen(false);
      setTransferForm({ source: '', target: '', amount: '', description: '' });
      await fetchTreasuryData();
    } catch (err: any) {
      alert(`Transfer failed: ${err.message}`);
    } finally {
      setTransferring(false);
    }
  };

  const handleSweep = async () => {
    setLoading(true);
    try {
      const res = await treasuryAPI.sweepYield();
      alert(res.message);
      await fetchTreasuryData();
    } catch (err: any) {
      alert(`Sweep failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="flex justify-center items-center h-64"><Loader2 className="w-8 h-8 animate-spin text-primary-gold" /></div>;

  if (pools.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-96 text-center space-y-6">
        <Landmark className="w-16 h-16 text-primary-gold opacity-50" />
        <div>
          <h2 className="font-serif text-[30px] font-light text-text-primary">Ecosystem Treasury Uninitialized</h2>
          <p className="font-sans text-[13px] text-text-secondary mt-2">The institutional reserve and yield pools have not been generated yet.</p>
        </div>
        {user?.role_tier === 'admin' && (
          <button onClick={handleSeed} className="btn gold px-6 py-3 text-[11px]">Seed Institutional Treasury Foundation</button>
        )}
      </div>
    );
  }

  const totalNav = pools.reduce((acc, pool) => acc + pool.balance, 0);
  const reservePool = pools.find(p => p.id === 'RESERVE');
  const reserveRatio = reservePool ? (reservePool.balance / totalNav) * 100 : 0;
  
  // Calculate total yield successfully swept from the ledger
  const totalYieldSwept = transactions
    .filter(tx => tx.transaction_type === 'YIELD_SWEEP' && tx.amount > 0)
    .reduce((sum, tx) => sum + tx.amount, 0);

  return (
    <div className="space-y-8">
      <PageHeader title="Ecosystem Treasury" subtitle="Macro-level oversight of institutional capital, reserves, and yield distribution." />

      <div className="g4">
        <MetricDisplay label="Total Treasury NAV" value={`$${totalNav.toLocaleString(undefined, {minimumFractionDigits: 2})}`} icon={Landmark} />
        <MetricDisplay label="Reserve Ratio" value={`${reserveRatio.toFixed(2)}%`} trend={reserveRatio >= 20 ? 'up' : 'down'} icon={Shield} />
        <MetricDisplay label="Total Yield Generated" value={`$${totalYieldSwept.toLocaleString(undefined, {minimumFractionDigits: 2})}`} icon={TrendingUp} trend="up" />
        <MetricDisplay label="Total Active Pools" value={pools.length} icon={Database} />
      </div>

      <div className="g21">
        {/* Active Pools */}
        <div className="card gold shadow-lg p-0 overflow-hidden">
          <div className="p-6 border-b border-border-default bg-background-base flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Database className="w-4 h-4 text-primary-gold" />
              <h3 className="sec-head mb-0">Active Treasury Pools</h3>
            </div>
            {user?.role_tier === 'admin' && (
              <div className="flex items-center gap-3">
                <button onClick={handleSweep} className="btn grey">Sweep Yield</button>
                <button onClick={() => setIsTransferModalOpen(true)} className="btn gold">Transfer Capital</button>
              </div>
            )}
          </div>
          <div className="overflow-x-auto">
            <table className="nexa-table">
              <thead><tr><th>Pool ID</th><th>Name</th><th>Target Alloc.</th><th>Current Balance</th></tr></thead>
              <tbody>
                {pools.map(pool => (
                  <tr key={pool.pk_id}>
                    <td className="font-mono font-bold text-primary-gold">{pool.id}</td>
                    <td className="font-sans font-semibold text-text-primary">{pool.name}</td>
                    <td className="font-mono">{pool.target_allocation_pct.toFixed(1)}%</td>
                    <td className="font-mono font-bold text-primary-emerald">${pool.balance.toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Recent Ledger */}
        <div className="card blue shadow-lg p-0 overflow-hidden">
          <div className="p-6 border-b border-border-default bg-background-base flex items-center gap-2">
            <ArrowRightLeft className="w-4 h-4 text-primary-blue" />
            <h3 className="sec-head mb-0">Treasury Ledger</h3>
          </div>
          <div className="overflow-x-auto max-h-[350px] overflow-y-auto">
            {transactions.length > 0 ? (
              <table className="nexa-table">
                <thead><tr><th>Time</th><th>Amount</th><th>Type</th><th>Desc</th></tr></thead>
                <tbody>
                  {transactions.map(tx => (
                    <tr key={tx.id}>
                      <td className="font-mono whitespace-nowrap text-[10px]">{new Date(tx.timestamp).toLocaleString(undefined, {month: 'short', day:'numeric', hour:'2-digit', minute:'2-digit'})}</td>
                      <td className={`font-mono font-bold ${tx.amount > 0 ? 'text-primary-emerald' : 'text-danger'}`}>{tx.amount > 0 ? '+' : ''}{tx.amount.toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
                      <td><span className={`tag ${tx.amount > 0 ? 'teal' : 'red'}`}>{tx.transaction_type}</span></td>
                      <td className="font-sans text-[11px] text-text-secondary">{tx.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="p-8 text-center flex flex-col items-center justify-center min-h-[250px]">
                <Activity className="w-8 h-8 text-text-muted mb-4 opacity-50" />
                <p className="font-sans text-[13px] text-text-muted mb-2">No capital movement events yet.</p>
                <p className="font-mono text-[11px] uppercase tracking-wider text-text-muted">Awaiting yield sweeps or rebalancing.</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Transfer Modal Overlay */}
      {isTransferModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4">
           <div className="card gold w-full max-w-lg shadow-2xl">
              <h3 className="font-display text-[22px] font-bold text-text-primary mb-6">Transfer Treasury Capital</h3>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block font-mono text-[11px] uppercase tracking-wider text-text-muted mb-1.5">Source Pool</label>
                    <select className="w-full border border-border-default rounded-lg px-3 py-2 font-sans text-[13px] focus:outline-none focus:border-primary-gold" value={transferForm.source} onChange={e => setTransferForm({...transferForm, source: e.target.value})}>
                      <option value="">Select Source...</option>
                      {pools.map(p => <option key={`src-${p.id}`} value={p.id}>{p.id} (${p.balance.toLocaleString()})</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block font-mono text-[11px] uppercase tracking-wider text-text-muted mb-1.5">Target Pool</label>
                    <select className="w-full border border-border-default rounded-lg px-3 py-2 font-sans text-[13px] focus:outline-none focus:border-primary-gold" value={transferForm.target} onChange={e => setTransferForm({...transferForm, target: e.target.value})}>
                      <option value="">Select Target...</option>
                      {pools.map(p => <option key={`tgt-${p.id}`} value={p.id}>{p.id}</option>)}
                    </select>
                  </div>
                </div>
                <div>
                  <label className="block font-mono text-[11px] uppercase tracking-wider text-text-muted mb-1.5">Transfer Amount ($)</label>
                  <input type="number" step="1000" min="0" className="w-full border border-border-default rounded-lg px-3 py-2 font-sans text-[13px] focus:outline-none focus:border-primary-gold" value={transferForm.amount} onChange={e => setTransferForm({...transferForm, amount: e.target.value})} placeholder="e.g. 50000" />
                </div>
                <div>
                  <label className="block font-mono text-[11px] uppercase tracking-wider text-text-muted mb-1.5">Description / Reason</label>
                  <input type="text" className="w-full border border-border-default rounded-lg px-3 py-2 font-sans text-[13px] focus:outline-none focus:border-primary-gold" value={transferForm.description} onChange={e => setTransferForm({...transferForm, description: e.target.value})} placeholder="e.g. Rebalancing reserves" />
                </div>
              </div>
              <div className="flex justify-end gap-3 mt-8 pt-4 border-t border-border-default">
                 <button onClick={() => setIsTransferModalOpen(false)} className="btn grey">Cancel</button>
                 <button onClick={handleTransfer} className="btn teal" disabled={transferring || !transferForm.source || !transferForm.target || !transferForm.amount}>{transferring ? <Loader2 className="w-4 h-4 animate-spin mr-1"/> : null} Confirm Transfer</button>
              </div>
           </div>
        </div>
      )}
    </div>
  );
}