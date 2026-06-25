'use client';

import { useEffect, useState } from 'react';
import { PageHeader } from '@/components/ui/PageHeader';
import { GlobalMarketIntelligence } from '@/components/intelligence/GlobalMarketIntelligence';
import { marketIntelligenceAPI, intelligenceAPI } from '@/lib/api';
import type { AssetItem } from '@/lib/api';
import { Loader2, Globe, Newspaper } from 'lucide-react';

export default function MarketIntelligencePage() {
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState<any>(null);
  const [assets, setAssets] = useState<AssetItem[]>([]);
  const [sentiments, setSentiments] = useState<Record<string, any>>({});

  useEffect(() => {
    Promise.all([
      marketIntelligenceAPI.getDashboard(),
      intelligenceAPI.getSentimentPulse(12),
    ]).then(([dash, pulseList]) => {
      setDashboard(dash);
      const results: Record<string, any> = {};
      (pulseList || []).forEach((s) => { results[s.symbol] = s; });
      setSentiments(results);
      setAssets((pulseList || []).map((s) => ({
        symbol: s.symbol,
        asset_class: (s.contributing_factors as any)?.asset_class ?? '—',
      })) as AssetItem[]);
    }).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex justify-center items-center h-64"><Loader2 className="w-8 h-8 animate-spin text-primary-gold" /></div>;

  return (
    <div className="space-y-8">
      <PageHeader title="Global Market Intelligence" subtitle="Multi-asset pulse, regimes, and cross-region news feeds." />

      <GlobalMarketIntelligence />

      <div className="g2">
        <div className="card gold p-6">
          <div className="flex items-center gap-2 mb-4">
            <Globe className="w-4 h-4 text-primary-gold" />
            <h3 className="sec-head mb-0">Asset Pulse</h3>
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            {assets.map((a) => {
              const s = sentiments[a.symbol];
              return (
                <div key={a.symbol} className="flex justify-between items-center border border-border-default rounded-lg px-3 py-2">
                  <div>
                    <span className="font-mono font-bold text-[12px]">{a.symbol}</span>
                    <span className="font-sans text-[11px] text-text-muted ml-2">{a.asset_class}</span>
                  </div>
                  {s ? <span className={`tag ${s.score > 0.2 ? 'teal' : s.score < -0.2 ? 'red' : 'grey'}`}>{s.score}</span> : <span className="tag grey">—</span>}
                </div>
              );
            })}
          </div>
        </div>

        <div className="card blue p-6">
          <div className="flex items-center gap-2 mb-4">
            <Newspaper className="w-4 h-4 text-primary-blue" />
            <h3 className="sec-head mb-0">Latest Intelligence</h3>
          </div>
          <ul className="space-y-3 max-h-[400px] overflow-y-auto">
            {(dashboard?.news || []).map((n: any) => (
              <li key={n.id} className="border-b border-border-default pb-2">
                <p className="font-sans text-[13px] text-text-primary">{n.title}</p>
                <p className="font-mono text-[10px] text-text-muted mt-1">{n.source} · {n.region || 'GLOBAL'} · {new Date(n.published_at).toLocaleDateString()}</p>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
