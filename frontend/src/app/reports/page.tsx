'use client';

import { useState, useEffect } from 'react';
import { portfolioAPI, reportsAPI } from '@/lib/api';
import type { Portfolio, Report, ReportGenerate } from '@/lib/types';
import { PageHeader } from '@/components/ui/PageHeader';
import { Loader2, FileText, Calendar, BarChart2, Download } from 'lucide-react';

export default function ReportsPage() {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [selectedPortfolio, setSelectedPortfolio] = useState<string>('');
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    const fetchPortfolios = async () => {
      try {
        const portfolioData = await portfolioAPI.listPortfolios();
        setPortfolios(portfolioData);
        if (portfolioData.length > 0) {
          setSelectedPortfolio(portfolioData[0].id);
        }
      } catch (error) {
        console.error("Failed to fetch portfolios", error);
      } finally {
        setLoading(false);
      }
    };
    fetchPortfolios();
  }, []);

  useEffect(() => {
    if (!selectedPortfolio) return;

    const fetchReports = async () => {
      setLoading(true);
      try {
        const reportData = await reportsAPI.getReports(selectedPortfolio);
        setReports(reportData);
      } catch (error) {
        console.error("Failed to fetch reports", error);
      } finally {
        setLoading(false);
      }
    };
    fetchReports();
  }, [selectedPortfolio]);

  const handleGenerateReport = async (reportType: 'WEEKLY' | 'MONTHLY') => {
    if (!selectedPortfolio) return;
    setGenerating(true);
    try {
      const payload: ReportGenerate = {
        portfolio_id: selectedPortfolio,
        report_type: reportType,
      };
      const newReport = await reportsAPI.generateReport(payload);
      setReports([newReport, ...reports]);
    } catch (error) {
      alert(`Failed to generate report: ${error}`);
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader title="Performance Reports" subtitle="Generate and review historical performance reports" />

      {/* Controls */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-end">
        <div className="md:col-span-1">
          <label className="block font-mono text-[11px] uppercase tracking-wider text-text-muted mb-1.5">Select Portfolio</label>
          <select
            value={selectedPortfolio}
            onChange={(e) => setSelectedPortfolio(e.target.value)}
            className="w-full bg-background-base border border-border-default rounded-lg px-3 py-2.5 text-[14px] focus:outline-none focus:border-primary-gold transition-colors"
            disabled={loading}
          >
            {portfolios.map(p => <option key={p.id} value={p.id}>{p.id}</option>)}
          </select>
        </div>
        <div className="md:col-span-2 flex gap-4">
          <button onClick={() => handleGenerateReport('WEEKLY')} disabled={generating || !selectedPortfolio} className="btn blue btn-full flex items-center justify-center gap-2">
            {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Calendar className="w-4 h-4" />}
            Generate Weekly
          </button>
          <button onClick={() => handleGenerateReport('MONTHLY')} disabled={generating || !selectedPortfolio} className="btn teal btn-full flex items-center justify-center gap-2">
            {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <BarChart2 className="w-4 h-4" />}
            Generate Monthly
          </button>
        </div>
      </div>

      {/* Report List */}
      <div className="card p-0 overflow-hidden">
        <div className="p-5 border-b border-border-default">
          <h3 className="sec-head mb-0">Generated Reports</h3>
        </div>
        {loading && <div className="p-8 text-center text-text-muted">Loading reports...</div>}
        {!loading && reports.length === 0 && (
          <div className="p-8 text-center text-text-muted">
            <FileText className="w-12 h-12 mx-auto mb-4 opacity-30" />
            No reports found for this portfolio.
          </div>
        )}
        {!loading && reports.length > 0 && (
          <ul className="divide-y divide-border-subtle">
            {reports.map(report => (
              <li key={report.id} className="p-5 hover:bg-background-panel/60 transition-colors">
                <div className="flex justify-between items-center gap-4">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="p-2.5 rounded-xl bg-system-gBg border border-system-gBd shrink-0">
                      <FileText className="w-5 h-5 text-primary-gold-bright" />
                    </div>
                    <div className="min-w-0">
                      <p className="font-semibold text-text-primary text-[15px]">{report.report_type} Report</p>
                      <p className="text-[12px] text-text-muted font-mono">
                        {new Date(report.period_start).toLocaleDateString()} - {new Date(report.period_end).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <div className="text-right flex items-center gap-4 shrink-0">
                    <div>
                      <p className={`font-mono font-bold text-[18px] ${report.performance_metrics?.total_pnl >= 0 ? 'text-success' : 'text-danger'}`}>
                        {report.performance_metrics?.total_pnl >= 0 ? '+' : ''}${report.performance_metrics?.total_pnl?.toLocaleString() ?? '0.00'}
                      </p>
                      <p className="text-[12px] text-text-muted">{report.performance_metrics?.win_rate_pct ?? 0}% Win Rate</p>
                    </div>
                    <button 
                      onClick={() => reportsAPI.downloadReport(report.id, `LionexAI_${selectedPortfolio}_${report.report_type}.pdf`)}
                      className="p-2.5 bg-background-panel hover:bg-system-gBg text-primary-gold-bright border border-border-default hover:border-system-gBd rounded-lg transition-colors"
                      title="Download PDF"
                    >
                      <Download className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}