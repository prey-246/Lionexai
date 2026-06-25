'use client';

import { useEffect, useState } from 'react';
import { PageHeader } from '@/components/ui/PageHeader';
import { institutionalAPI } from '@/lib/api';
import { Loader2, FlaskConical, CheckCircle, AlertTriangle, XCircle } from 'lucide-react';

const VERDICT_STYLE: Record<string, { icon: typeof CheckCircle; cls: string }> = {
  SUPPORTED: { icon: CheckCircle, cls: 'text-primary-emerald' },
  PARTIALLY_SUPPORTED: { icon: AlertTriangle, cls: 'text-warning' },
  NOT_SUPPORTED: { icon: XCircle, cls: 'text-danger' },
};

export default function AlphaEvidencePage() {
  const [loading, setLoading] = useState(true);
  const [evidence, setEvidence] = useState<any>(null);
  const [target, setTarget] = useState(20);

  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    institutionalAPI.getAlphaEvidenceFull('ALPHA', target)
      .then(setEvidence)
      .catch((e) => setError(e.message || 'Failed to load alpha evidence'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  if (loading && !evidence) {
    return <div className="flex justify-center items-center h-64"><Loader2 className="w-8 h-8 animate-spin text-primary-gold" /></div>;
  }

  const verdict = evidence?.verdict || 'NOT_SUPPORTED';
  const V = VERDICT_STYLE[verdict] || VERDICT_STYLE.NOT_SUPPORTED;
  const Icon = V.icon;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Alpha Evidence Dashboard"
        subtitle="Objective evaluation of 20% monthly target — historical, walk-forward, Monte Carlo, and paper-live. No marketing optimization."
      />

      {error && (
        <div className="card red p-4 text-[13px] text-danger">{error}</div>
      )}

      <div className="card gold p-6 flex items-start gap-4">
        <Icon className={`w-10 h-10 shrink-0 ${V.cls}`} />
        <div>
          <p className="font-mono text-[11px] uppercase text-text-muted">Verdict</p>
          <h2 className={`font-serif text-2xl ${V.cls}`}>{verdict.replace(/_/g, ' ')}</h2>
          <p className="text-[13px] text-text-secondary mt-2">{evidence?.rationale}</p>
        </div>
      </div>

      <div className="flex gap-3 items-end">
        <label className="text-[12px] text-text-muted">
          Target monthly %
          <input type="number" className="input ml-2 w-24" value={target} onChange={(e) => setTarget(Number(e.target.value))} />
        </label>
        <button type="button" className="btn primary" onClick={load}>Re-evaluate</button>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {[
          ['Historical Validation', evidence?.historical_validation, 'VALIDATED_HISTORICAL'],
          ['Walk Forward', evidence?.walk_forward, 'VALIDATED_HISTORICAL'],
          ['Monte Carlo', evidence?.monte_carlo, 'VALIDATED_HISTORICAL'],
          ['Paper Live', evidence?.paper_live, evidence?.paper_live?.provenance],
        ].map(([title, block, prov]) => (
          <div key={String(title)} className="card blue p-5">
            <div className="flex justify-between items-start mb-3">
              <h3 className="font-serif text-lg flex items-center gap-2"><FlaskConical className="w-4 h-4" />{title}</h3>
              <span className="tag blue text-[10px]">{prov}</span>
            </div>
            <pre className="text-[11px] font-mono text-text-secondary overflow-auto max-h-48 whitespace-pre-wrap">
              {JSON.stringify(block, null, 2)}
            </pre>
          </div>
        ))}
      </div>
    </div>
  );
}
