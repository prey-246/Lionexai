'use client';

import { useState, useEffect, useRef } from 'react';
import { PageHeader } from '@/components/ui/PageHeader';
import { MetricDisplay } from '@/components/ui/MetricDisplay';
import { createChart, ColorType, Time } from 'lightweight-charts';
import { Calculator, TrendingUp, AlertTriangle, Target, Zap, Activity, BarChart3, Percent, Plus, Minus, Download, Loader2 } from 'lucide-react';
import { validationAPI } from '@/lib/api/validation';

export default function SimulatorPage() {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const seriesRef = useRef<any>(null);

  const [fundType, setFundType] = useState('ALPHA');
  const [deposit, setDeposit] = useState(10000);
  const [monthlyContribution, setMonthlyContribution] = useState(0);
  const [months, setMonths] = useState(12);
  const [scenario, setScenario] = useState('AGGRESSIVE');

  const [metrics, setMetrics] = useState({
    projectedCapital: 0,
    totalYield: 0,
    yieldPct: 0,
    totalContributions: 0,
  });

  const [withdrawalSchedule, setWithdrawalSchedule] = useState<Record<number, number>>({});
  const [withdrawalMonth, setWithdrawalMonth] = useState(1);
  const [downloading, setDownloading] = useState(false);

  const depositPresets = [1000, 5000, 10000, 50000, 100000];

  useEffect(() => {
    if (withdrawalMonth > months) {
      setWithdrawalMonth(months);
    }
  }, [months, withdrawalMonth]);

  useEffect(() => {
    if (fundType === 'PRESERVE') setScenario('CONSERVATIVE');
    if (fundType === 'BALANCE') setScenario('BALANCED');
    if (fundType === 'ALPHA') setScenario('AGGRESSIVE');
  }, [fundType]);

  // Calculation and Charting Engine
  useEffect(() => {
    if (!chartContainerRef.current) return;

    // Initialize chart if it doesn't exist
    if (!chartRef.current) {
      chartRef.current = createChart(chartContainerRef.current, {
        layout: {
          background: { type: ColorType.Solid, color: 'transparent' },
          textColor: '#8A94A6',
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 11,
        },
        grid: {
          vertLines: { color: 'rgba(255, 255, 255, 0.04)' },
          horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
        },
        height: 350,
        crosshair: {
          vertLine: { color: 'rgba(207, 164, 59, 0.4)', labelBackgroundColor: '#CFA43B' },
          horzLine: { color: 'rgba(207, 164, 59, 0.4)', labelBackgroundColor: '#CFA43B' },
        },
        rightPriceScale: { borderVisible: false },
        timeScale: { borderVisible: false },
      });

      seriesRef.current = chartRef.current.addAreaSeries({
        lineColor: '#CFA43B',
        topColor: 'rgba(207, 164, 59, 0.4)',
        bottomColor: 'rgba(207, 164, 59, 0.0)',
        lineWidth: 2,
        priceLineVisible: false,
      });
    }

    // Calculate growth
    const weeklyRates: Record<string, number> = {
      'CONSERVATIVE': 0.005, // 0.5% per week
      'BALANCED': 0.010,     // 1.0% per week
      'AGGRESSIVE': 0.015,   // 1.5% per week
    };

    const weeklyRate = weeklyRates[scenario] || 0.01;
    const totalWeeks = months * 4;
    
    let currentCapital = deposit;
    const localChartData = [];
    const now = new Date();
    let totalContributions = 0;

    for (let i = 0; i <= totalWeeks; i++) {
      const stepDate = new Date(now.getTime());
      stepDate.setDate(stepDate.getDate() + (i * 7));
      const timeStr = stepDate.toISOString().split('T')[0];
      const projectionMonth = Math.floor(i / 4);

      localChartData.push({
        time: timeStr as Time,
        value: currentCapital
      });

      if (i > 0 && i % 4 === 0) {
        currentCapital += monthlyContribution;
        totalContributions += monthlyContribution;

        const withdrawPct = withdrawalSchedule[projectionMonth];
        if (withdrawPct && withdrawPct > 0) {
          currentCapital *= (1 - withdrawPct / 100);
        }
      }

      if (i < totalWeeks) {
        currentCapital = currentCapital * (1 + weeklyRate);
      }
    }

    seriesRef.current.setData(localChartData);
    chartRef.current.timeScale().fitContent();

    const finalCapital = localChartData[localChartData.length - 1].value;
    const totalYield = finalCapital - deposit - totalContributions;
    
    setMetrics({
      projectedCapital: finalCapital,
      totalYield: totalYield,
      yieldPct: (totalYield / (deposit + totalContributions)) * 100,
      totalContributions: totalContributions,
    });

    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [deposit, months, scenario, monthlyContribution, withdrawalSchedule]);

  // Institutional Projection Metrics based on Scenario
  const scenarioMetrics = {
    'CONSERVATIVE': { winRate: 68.5, maxDrawdown: 4.2, sharpe: 1.45 },
    'BALANCED':     { winRate: 59.2, maxDrawdown: 11.5, sharpe: 1.82 },
    'AGGRESSIVE':   { winRate: 54.1, maxDrawdown: 24.8, sharpe: 2.15 }
  }[scenario] || { winRate: 50, maxDrawdown: 10, sharpe: 1.0 };

  const handleWithdraw = (percentage: number) => {
    const monthIndex = withdrawalMonth - 1;
    setWithdrawalSchedule(prev => ({
      ...prev,
      [monthIndex]: percentage * 100,
    }));
  };

  const handleDownloadReport = async () => {
    setDownloading(true);
    try {
      // This assumes you add a new function to your api lib
      await validationAPI.downloadSimulationReport({
        deposit,
        monthly_contribution: monthlyContribution,
        months,
        scenario,
        fund_type: fundType,
      });
    } catch (err: any) {
      alert(`Failed to download report: ${err.message}`);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="space-y-8 pb-10">
      <PageHeader 
        title="Growth Simulator" 
        subtitle="Project internal ecosystem growth targets based on historical algorithmic capabilities." 
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column: Inputs */}
        <div className="col-span-1 space-y-6">
          <div className="card grey p-5 space-y-6">
            <h3 className="font-serif text-[18px] text-text-primary border-b border-border-subtle pb-3">Projection Parameters</h3>
            
            <div>
              <label className="block font-mono text-[10px] uppercase tracking-wider text-text-muted mb-2">Select Fund Profile</label>
              <div className="grid grid-cols-3 gap-2">
                <button onClick={() => setFundType('PRESERVE')} className={`py-2 text-[12px] rounded-[3px] border transition-colors ${fundType === 'PRESERVE' ? 'bg-primary-emerald/10 border-primary-emerald text-primary-emerald' : 'border-border-default text-text-secondary hover:bg-background-panel'}`}>Preserve</button>
                <button onClick={() => setFundType('BALANCE')} className={`py-2 text-[12px] rounded-[3px] border transition-colors ${fundType === 'BALANCE' ? 'bg-primary-blue/10 border-primary-blue text-primary-blue' : 'border-border-default text-text-secondary hover:bg-background-panel'}`}>Balance</button>
                <button onClick={() => setFundType('ALPHA')} className={`py-2 text-[12px] rounded-[3px] border transition-colors ${fundType === 'ALPHA' ? 'bg-primary-gold/10 border-primary-gold text-primary-gold' : 'border-border-default text-text-secondary hover:bg-background-panel'}`}>Alpha</button>
              </div>
            </div>

            <div>
              <label className="block font-mono text-[10px] uppercase tracking-wider text-text-muted mb-2">Initial Capital Deposit ($)</label>
              <div className="flex flex-wrap gap-2 mb-2">
                {depositPresets.map((preset) => (
                  <button
                    key={preset}
                    type="button"
                    onClick={() => setDeposit(preset)}
                    className={`px-2 py-1 text-[11px] rounded-[3px] border ${deposit === preset ? 'border-primary-gold text-primary-gold bg-primary-gold/10' : 'border-border-default text-text-secondary'}`}
                  >
                    ${preset.toLocaleString()}
                  </button>
                ))}
              </div>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Calculator className="h-4 w-4 text-text-muted" />
                </div>
                <input 
                  type="number" 
                  min="1000"
                  step="1000"
                  value={deposit}
                  onChange={(e) => setDeposit(Number(e.target.value))}
                  className="block w-full pl-9 pr-3 py-2 bg-background-base border border-border-default rounded-[3px] text-text-primary text-[14px] focus:outline-none focus:border-primary-gold"
                />
              </div>
            </div>

            <div>
              <label className="block font-mono text-[10px] uppercase tracking-wider text-text-muted mb-2">Optional Monthly Contribution ($)</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Plus className="h-4 w-4 text-text-muted" />
                </div>
                <input 
                  type="number" 
                  min="0"
                  step="100"
                  value={monthlyContribution}
                  onChange={(e) => setMonthlyContribution(Number(e.target.value))}
                  className="block w-full pl-9 pr-3 py-2 bg-background-base border border-border-default rounded-[3px] text-text-primary text-[14px] focus:outline-none focus:border-primary-gold"
                />
              </div>
            </div>

            <div>
              <label className="block font-mono text-[10px] uppercase tracking-wider text-text-muted mb-2">Projection Period</label>
              <select 
                value={months}
                onChange={(e) => setMonths(Number(e.target.value))}
                className="block w-full px-3 py-2 bg-background-base border border-border-default rounded-[3px] text-text-primary text-[14px] focus:outline-none focus:border-primary-gold"
              >
                <option value={1}>1 Month</option>
                <option value={3}>3 Months</option>
                <option value={6}>6 Months</option>
                <option value={12}>12 Months</option>
                <option value={24}>24 Months</option>
                <option value={36}>36 Months</option>
              </select>
            </div>

            <div>
              <label className="block font-mono text-[10px] uppercase tracking-wider text-text-muted mb-2">Scenario Engine</label>
              <select 
                value={scenario}
                onChange={(e) => setScenario(e.target.value)}
                className="block w-full px-3 py-2 bg-background-base border border-border-default rounded-[3px] text-text-primary text-[14px] focus:outline-none focus:border-primary-gold"
              >
                <option value="CONSERVATIVE">Conservative (Est. ~0.5% Weekly Growth)</option>
                <option value="BALANCED">Balanced (Est. ~1.0% Weekly Growth)</option>
                <option value="AGGRESSIVE">Aggressive (Est. ~1.5% Weekly Growth)</option>
              </select>
            </div>

            <div>
              <label className="block font-mono text-[10px] uppercase tracking-wider text-text-muted mb-2">Withdrawal Simulation</label>
              <select
                value={withdrawalMonth}
                onChange={(e) => setWithdrawalMonth(Number(e.target.value))}
                className="block w-full px-3 py-2 mb-2 bg-background-base border border-border-default rounded-[3px] text-text-primary text-[14px]"
              >
                {Array.from({ length: months }, (_, i) => i + 1).map((m) => (
                  <option key={m} value={m}>Withdraw at month {m}</option>
                ))}
              </select>
              <div className="grid grid-cols-4 gap-2">
                <button type="button" onClick={() => handleWithdraw(0.10)} className="btn-sm grey flex items-center justify-center gap-1"><Minus className="w-3 h-3"/> 10%</button>
                <button type="button" onClick={() => handleWithdraw(0.25)} className="btn-sm grey flex items-center justify-center gap-1"><Minus className="w-3 h-3"/> 25%</button>
                <button type="button" onClick={() => handleWithdraw(0.50)} className="btn-sm grey flex items-center justify-center gap-1"><Minus className="w-3 h-3"/> 50%</button>
                <button type="button" onClick={() => handleWithdraw(1.00)} className="btn-sm red flex items-center justify-center gap-1"><Minus className="w-3 h-3"/> All</button>
              </div>
              <p className="text-[10px] text-text-muted mt-2">
                Applies a one-time withdrawal at the selected projection month and recalculates future growth.
              </p>
            </div>

          </div>
        </div>

        {/* Right Column: Visualization */}
        <div className="col-span-1 lg:col-span-2 space-y-6">
          <div className="flex justify-end">
            <button onClick={handleDownloadReport} className="btn gold flex items-center gap-2" disabled={downloading}>
              {downloading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
              Download PDF Report
            </button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-2">
             <MetricDisplay 
                label="Projected Final Capital" 
                value={`$${metrics.projectedCapital.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`} 
                icon={Target} 
                trend="up" 
             />
             <MetricDisplay 
                label="Projected Yield ($)" 
                value={`+$${metrics.totalYield.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`} 
                icon={TrendingUp} 
             />
             <MetricDisplay 
                label="Net Return (Compounded)" 
                value={`+${metrics.yieldPct.toFixed(2)}%`} 
                icon={Zap} 
             />
          </div>
          
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
             <MetricDisplay 
                label="Est. Win Rate" 
                value={`${scenarioMetrics.winRate}%`} 
                icon={Percent} 
             />
             <MetricDisplay 
                label="Est. Max Drawdown" 
                value={`-${scenarioMetrics.maxDrawdown}%`} 
                icon={Activity} 
             />
             <MetricDisplay 
                label="Target Sharpe Ratio" 
                value={scenarioMetrics.sharpe.toFixed(2)} 
                icon={BarChart3} 
             />
          </div>

          <div className="card bg-background-base border border-border-default p-5">
            <h3 className="font-mono text-[10px] uppercase tracking-wider text-text-muted mb-4">Capital Growth Projection Chart</h3>
            <div ref={chartContainerRef} className="w-full" />
          </div>

          {/* Compliance Disclaimer */}
          <div className="flex items-start gap-3 bg-primary-blue/5 border border-primary-blue/20 p-4 rounded-[3px]">
            <AlertTriangle className="w-5 h-5 text-primary-blue mt-0.5 shrink-0" />
            <div>
              <h4 className="font-sans text-[13px] font-bold text-text-primary mb-1">Visualization Purpose Only</h4>
              <p className="font-sans text-[12px] text-text-secondary leading-relaxed">
                This tool provides projections for the internal ecosystem index based on historical algorithmic capabilities. It is not an offer or solicitation for investment. Displayed yields represent compounded target metrics and do not guarantee future returns or real-world execution fidelity.
              </p>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}