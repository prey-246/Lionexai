'use client';

import { useState, useEffect } from 'react';
import { PageHeader } from '@/components/ui/PageHeader';
import { MetricDisplay } from '@/components/ui/MetricDisplay';
import { treasuryAPI } from '@/lib/api';
import { Coins, Loader2, Shield, TrendingUp, Activity, Lock, ArrowRightLeft } from 'lucide-react';

export default function LNXEcosystemPage() {
  const [loading, setLoading] = useState(true);
  const [pools, setPools] = useState<any[]>([]);

  useEffect(() => {
    treasuryAPI.getPools()
      .then(data => setPools(data || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex justify-center items-center h-64"><Loader2 className="w-8 h-8 animate-spin text-primary-gold" /></div>;

  const reservePool = pools.find(p => p.id === 'RESERVE');
  const yieldPool = pools.find(p => p.id === 'YIELD');
  
  const totalSupply = 100000000; // 100M LNX Fixed Supply
  const reserveBalance = reservePool?.balance || 0;
  const yieldBalance = yieldPool?.balance || 0;
  
  // NAV (Net Asset Value) per token based purely on Reserve Backing
  const lnxPrice = reserveBalance > 0 ? (reserveBalance / totalSupply) : 0;
  const marketCap = totalSupply * lnxPrice;
  
  // Projected Yield Distribution (APY) based on Yield Pool vs Reserve Backing
  const estimatedApy = reserveBalance > 0 ? (yieldBalance / reserveBalance) * 100 : 0;

  return (
    <div className="space-y-8">
      <PageHeader title="LNX Digital Asset" subtitle="The Lionex Native Index. Platform-native representation of ecosystem growth." />

      <div className="g4">
        <MetricDisplay label="LNX Price (NAV)" value={`$${lnxPrice.toFixed(4)}`} icon={Coins} trend="up" />
        <MetricDisplay label="Total Supply" value={(totalSupply / 1000000).toFixed(0) + 'M'} icon={Activity} />
        <MetricDisplay label="Reserve Backing" value={`$${reserveBalance.toLocaleString(undefined, {minimumFractionDigits: 2})}`} icon={Shield} />
        <MetricDisplay label="Market Cap" value={`$${marketCap.toLocaleString(undefined, {minimumFractionDigits: 2})}`} icon={TrendingUp} />
      </div>

      <div className="g3">
        <MetricDisplay label="Current Est. APY" value={`${estimatedApy.toFixed(2)}%`} icon={TrendingUp} trend="up" />
        <MetricDisplay label="Total Yield Captured" value={`$${yieldBalance.toLocaleString(undefined, {minimumFractionDigits: 2})}`} icon={Activity} />
        <MetricDisplay label="Distributions (All-Time)" value={`$0.00`} icon={ArrowRightLeft} />
      </div>

      <div className="g21">
        <div className="card gold shadow-lg p-6">
          <h3 className="sec-head">Tokenomics & Backing</h3>
          <p className="font-sans text-[13px] text-text-secondary leading-relaxed mb-4">
            LNX (Lionex Native Index) is currently implemented as an internal accounting asset. It is strictly backed by the institutional <strong>Reserve Pool</strong>. As excess platform profits and yield are swept into the Reserve, the NAV of LNX deterministically increases.
          </p>
          <div className="space-y-3 mt-6">
            <div className="flex justify-between items-center border-b border-border-default pb-2">
              <span className="font-mono text-[10px] text-text-muted uppercase tracking-wider">Asset Class</span>
              <span className="tag grey">Internal Platform Index</span>
            </div>
            <div className="flex justify-between items-center border-b border-border-default pb-2">
              <span className="font-mono text-[10px] text-text-muted uppercase tracking-wider">Blockchain Status</span>
              <span className="tag grey">Pre-Tokenization (V1)</span>
            </div>
            <div className="flex justify-between items-center border-b border-border-default pb-2">
              <span className="font-mono text-[10px] text-text-muted uppercase tracking-wider">Current Yield Pool</span>
              <span className="font-mono font-bold text-primary-emerald">${yieldBalance.toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
            </div>
          </div>
        </div>

        <div className="card blue shadow-lg p-6 flex flex-col items-center justify-center text-center">
          <Lock className="w-12 h-12 text-primary-blue mb-4 opacity-50" />
          <h3 className="font-serif text-[20px] font-light text-text-primary mb-2">Smart Contract Integration</h3>
          <p className="font-sans text-[13px] text-text-muted">
            The platform architecture is fully prepared for Phase 2 Web3 integration. Future updates will mint LNX as an ERC-20/SPL token, enabling on-chain verifiability and decentralized yield distribution.
          </p>
          <button disabled className="btn grey mt-6 cursor-not-allowed">Web3 Bridge Locked</button>
        </div>
      </div>
    </div>
  );
}