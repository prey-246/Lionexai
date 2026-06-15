'use client';

import { useState } from 'react';
import { PageHeader } from '@/components/ui/PageHeader';
import { ShieldAlert, Play, CheckCircle2, XCircle, Terminal as TerminalIcon, AlertTriangle, Loader2 } from 'lucide-react';
import { stressTestAPI } from '@/lib/api';

type ScenarioStatus = 'IDLE' | 'RUNNING' | 'PASSED' | 'FAILED';

interface StressScenario {
  id: string;
  title: string;
  description: string;
  trigger: string;
  expectedOutcome: string;
}

const scenarios: StressScenario[] = [
  {
    id: 'SCENARIO_A',
    title: 'Leverage Violation',
    description: 'Attempts to execute a trade whose notional value exceeds the mandate\'s maximum permitted leverage multiplier.',
    trigger: 'BUY 10.0 BTC/USDT ($650,000) on a portfolio with limited equity (Max Leverage: 3x).',
    expectedOutcome: 'REJECTED — Leverage Limit Exceeded',
  },
  {
    id: 'SCENARIO_B',
    title: 'AI Sentiment Gatekeeper',
    description: 'Attempts to execute a buy order during extremely bearish alternative data conditions.',
    trigger: 'BUY 1.0 ETH/USDT while MarketSensitivityScore is -0.85 (Extreme Fear).',
    expectedOutcome: 'REJECTED — Extreme Bearish Sentiment',
  },
  {
    id: 'SCENARIO_C',
    title: 'Mandate Kill Switch',
    description: 'Evaluates rejection when the mandate-level kill switch is manually activated.',
    trigger: 'Mandate kill_switch_active=True. Autonomous engine attempts to trade.',
    expectedOutcome: 'REJECTED — Mandate Kill Switch Active',
  },
  {
    id: 'SCENARIO_D',
    title: 'Global Kill Switch',
    description: 'System-wide evaluation of the Executive Global Kill Switch during a black swan event.',
    trigger: 'Admin engages global_kill_switch_active=True. Trade execution attempted.',
    expectedOutcome: 'REJECTED — Global Kill Switch Active',
  },
  {
    id: 'SCENARIO_E',
    title: 'Daily Loss Breach',
    description: 'Tests portfolio-level rejection when daily loss exceeds the mandate\'s defined limit.',
    trigger: 'Portfolio PnL for the day drops below the daily loss limit threshold.',
    expectedOutcome: 'REJECTED — Daily Loss Limit Breached',
  },
];

export default function StressTestPage() {
  const [runStatus, setRunStatus] = useState<Record<string, ScenarioStatus>>({});
  const [results, setResults] = useState<Record<string, any>>({});

  const runScenario = async (id: string) => {
    setRunStatus(prev => ({ ...prev, [id]: 'RUNNING' }));
    try {
      const result = await stressTestAPI.runScenario(id);
      setResults(prev => ({ ...prev, [id]: result }));
      setRunStatus(prev => ({ ...prev, [id]: result.passed ? 'PASSED' : 'FAILED' }));
    } catch (error: any) {
      setRunStatus(prev => ({ ...prev, [id]: 'FAILED' }));
      setResults(prev => ({ ...prev, [id]: { passed: false, rejection_reason: error.message } }));
    }
  };

  return (
    <div className="space-y-8 pb-10">
      <PageHeader 
        title="Risk Validation Suite" 
        subtitle="Simulate and validate the NEXA Risk Engine's response to adverse market conditions and critical parameter breaches." 
      />

      <div className="flex items-start gap-3 bg-system-warning/10 border border-system-warning/20 p-4 rounded-[3px] mb-6">
        <AlertTriangle className="w-5 h-5 text-primary-gold mt-0.5 shrink-0" />
        <div>
          <h4 className="font-sans text-[13px] font-bold text-text-primary mb-1">Institutional Proof of Execution</h4>
          <p className="font-sans text-[12px] text-text-secondary leading-relaxed">
            These scenarios validate the core governance mechanisms of the platform. By running these stress tests, we demonstrate mathematical proof that client capital is unconditionally protected by the mandate architecture, even during catastrophic market failures or erroneous algorithmic signals.
          </p>
        </div>
      </div>

      <div className="space-y-6">
        {scenarios.map((scenario) => {
          const status = runStatus[scenario.id] || 'IDLE';
          const result = results[scenario.id];
          
          return (
            <div key={scenario.id} className="card grey p-6 shadow-md border-l-4 border-l-primary-blue">
              <div className="flex flex-col md:flex-row md:items-start justify-between gap-6">
                <div className="space-y-4 flex-1">
                  <div>
                    <h3 className="font-serif text-[20px] text-text-primary mb-1">{scenario.title}</h3>
                    <p className="font-sans text-[13px] text-text-secondary">{scenario.description}</p>
                  </div>
                  
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="bg-background-base p-3 rounded-[3px] border border-border-default">
                      <span className="block font-mono text-[9px] uppercase tracking-wider text-text-muted mb-1">Trigger Event</span>
                      <span className="font-sans text-[13px] text-text-primary">{scenario.trigger}</span>
                    </div>
                    <div className="bg-background-base p-3 rounded-[3px] border border-border-default">
                      <span className="block font-mono text-[9px] uppercase tracking-wider text-text-muted mb-1">Expected Engine Response</span>
                      <span className="font-sans text-[13px] text-primary-emerald">{scenario.expectedOutcome}</span>
                    </div>
                  </div>
                </div>

                <div className="shrink-0 flex flex-col items-center justify-center w-full md:w-48 space-y-3 bg-background-base p-4 rounded-[3px] border border-border-default">
                  <button 
                    onClick={() => runScenario(scenario.id)}
                    disabled={status === 'RUNNING' || status === 'PASSED'}
                    className={`btn w-full flex items-center justify-center gap-2 ${status === 'PASSED' ? 'border-primary-emerald text-primary-emerald bg-primary-emerald/10' : status === 'FAILED' ? 'border-danger text-danger bg-danger/10' : 'blue'}`}
                  >
                    {status === 'IDLE' && <><Play className="w-4 h-4" /> Run Scenario</>}
                    {status === 'RUNNING' && <><Loader2 className="w-4 h-4 animate-spin" /> Validating...</>}
                    {status === 'PASSED' && <><CheckCircle2 className="w-4 h-4" /> REJECTED ✓</>}
                    {status === 'FAILED' && <><XCircle className="w-4 h-4" /> Test Failed</>}
                  </button>
                </div>
              </div>

              {/* Simulated Output Terminal */}
              {result && (
                <div className="mt-6 bg-[#0D1117] border border-[#1F2937] rounded-[3px] overflow-hidden">
                  <div className="bg-[#1F2937] px-4 py-2 flex items-center gap-2">
                    <TerminalIcon className="w-4 h-4 text-text-muted" />
                    <span className="font-mono text-[10px] text-text-muted uppercase tracking-wider">Engine Response</span>
                  </div>
                  <div className="p-4 overflow-x-auto">
                    <pre className={`font-mono text-[11px] leading-relaxed ${result.passed ? 'text-primary-emerald' : 'text-danger'}`}>
                      {JSON.stringify(result, null, 2)}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}