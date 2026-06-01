"use client";

import React, { useState, useEffect } from "react";
import { reportsAPI, portfolioAPI } from "@/lib/api";
import { FileText, Download } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";

export default function ReportsPage() {
  const [reports, setReports] = useState<any[]>([]);
  const [portfolioId, setPortfolioId] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [generatingReport, setGeneratingReport] = useState(false);

  useEffect(() => {
    const loadPortfolio = async () => {
      try {
        const portfolios = await portfolioAPI.listPortfolios();
        if (portfolios.length > 0) {
          setPortfolioId(portfolios[0].id);
          const reportsData = await reportsAPI.getReports(portfolios[0].id);
          setReports(reportsData);
        }
      } catch (err) {
        console.error("Failed to load reports", err);
      } finally {
        setLoading(false);
      }
    };

    loadPortfolio();
  }, []);

  const handleGenerateReport = async (type: string) => {
    setGeneratingReport(true);
    try {
      await reportsAPI.generateReport({
        portfolio_id: portfolioId,
        report_type: type
      });
      const updated = await reportsAPI.getReports(portfolioId, type);
      setReports(updated);
    } catch (err) {
      console.error("Failed to generate report", err);
    } finally {
      setGeneratingReport(false);
    }
  };

  if (loading) return <div className="p-6 text-center text-gray-400">Loading reports...</div>;

  return (
    <main className="min-h-screen p-6 md:p-8 max-w-7xl mx-auto space-y-8">
      <header className="border-b border-gray-800 pb-6">
        <h1 className="text-3xl font-semibold tracking-tight text-white flex items-center gap-3">
          <FileText className="w-8 h-8 text-[#5EEAD4]" />
          Performance Reports
        </h1>
        <p className="text-gray-400 text-sm mt-1">Weekly & Monthly performance analysis</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <GlassCard className="p-6">
          <button
            onClick={() => handleGenerateReport("WEEKLY")}
            disabled={generatingReport}
            className="w-full bg-blue-600/20 hover:bg-blue-600/30 border border-blue-600/30 text-blue-300 py-4 rounded-lg font-medium transition-all disabled:opacity-50"
          >
            Generate Weekly Report
          </button>
        </GlassCard>
        <GlassCard className="p-6">
          <button
            onClick={() => handleGenerateReport("MONTHLY")}
            disabled={generatingReport}
            className="w-full bg-purple-600/20 hover:bg-purple-600/30 border border-purple-600/30 text-purple-300 py-4 rounded-lg font-medium transition-all disabled:opacity-50"
          >
            Generate Monthly Report
          </button>
        </GlassCard>
      </div>

      <section className="space-y-4">
        <div className="border-b border-gray-800 pb-2">
          <h2 className="text-lg font-medium tracking-tight text-white">Generated Reports</h2>
        </div>
        <div className="grid gap-4">
          {reports.length === 0 ? (
            <GlassCard className="p-8 text-center text-gray-500">No reports generated yet</GlassCard>
          ) : (
            reports.map((report) => (
              <GlassCard key={report.id} className="p-6 flex justify-between items-start border border-gray-800">
                <div>
                  <div className="font-semibold text-white">{report.report_type} Report</div>
                  <div className="text-sm text-gray-400 mt-1">
                    {new Date(report.period_start).toLocaleDateString()} - {new Date(report.period_end).toLocaleDateString()}
                  </div>
                  {report.performance_metrics && (
                    <div className="grid grid-cols-3 gap-4 mt-4 text-sm">
                      <div>
                        <div className="text-gray-400">Return</div>
                        <div className={`font-semibold ${report.performance_metrics.total_return_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {report.performance_metrics.total_return_pct}%
                        </div>
                      </div>
                      <div>
                        <div className="text-gray-400">Win Rate</div>
                        <div className="font-semibold text-white">{report.performance_metrics.win_rate}%</div>
                      </div>
                      <div>
                        <div className="text-gray-400">Trades</div>
                        <div className="font-semibold text-white">{report.performance_metrics.winning_trades}/{report.performance_metrics.total_trades}</div>
                      </div>
                    </div>
                  )}
                </div>
                <button className="p-2 hover:bg-white/10 rounded transition-all">
                  <Download className="w-5 h-5 text-gray-400" />
                </button>
              </GlassCard>
            ))
          )}
        </div>
      </section>
    </main>
  );
}
