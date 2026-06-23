'use client';

import { useState, useEffect } from 'react';
import { PageHeader } from '@/components/ui/PageHeader';
import { intelligenceAPI } from '@/lib/api';
import type { MarketNewsArticle, MarketSensitivityScore } from '@/lib/types';
import { BrainCircuit, Newspaper, Calendar, Loader2, Activity, TrendingUp, TrendingDown, Minus } from 'lucide-react';

export default function IntelligenceHubPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [news, setNews] = useState<MarketNewsArticle[]>([]);
  const [events, setEvents] = useState<any[]>([]);
  const [sentiments, setSentiments] = useState<Record<string, MarketSensitivityScore>>({});

  useEffect(() => {
    const fetchIntelligence = async () => {
      try {
        setLoading(true);
        // Fetch news and economic events in parallel
        const [newsData, eventsData] = await Promise.all([
          intelligenceAPI.getNews(15).catch(() => []),
          intelligenceAPI.getEconomicEvents(8).catch(() => [])
        ]);
        setNews(newsData);
        setEvents(eventsData);

        // Fetch sentiment for core assets
        const symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT'];
        const sentimentData: Record<string, MarketSensitivityScore> = {};
        
        await Promise.all(symbols.map(async (sym) => {
          try {
            const data = await intelligenceAPI.getSentiment(sym);
            sentimentData[sym] = data;
          } catch (e) {
            // Gracefully ignore if a symbol doesn't have sentiment data yet
          }
        }));
        setSentiments(sentimentData);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchIntelligence();
  }, []);

  if (loading) return <div className="flex justify-center items-center h-64"><Loader2 className="w-8 h-8 animate-spin text-primary-gold" /></div>;
  if (error) return <div className="text-center text-danger">{error}</div>;

  const getSentimentColor = (score: number) => {
    if (score > 0.2) return 'teal';
    if (score < -0.2) return 'red';
    return 'grey';
  };

  const getSentimentLabel = (score: number) => {
    if (score > 0.2) return 'BULLISH';
    if (score < -0.2) return 'BEARISH';
    return 'NEUTRAL';
  };

  return (
    <div className="space-y-8">
      <PageHeader title="Intelligence Hub" subtitle="AI-driven market sentiment and alternative data analysis." />

      {/* AI Market Pulse Grid */}
      <div className="g3">
        {['BTC/USDT', 'ETH/USDT', 'SOL/USDT'].map((symbol) => {
          const data = sentiments[symbol];
          const score = data?.score || 0;
          const color = getSentimentColor(score);
          const label = getSentimentLabel(score);
          const iconColorClass = score > 0.2 ? 'text-success' : score < -0.2 ? 'text-danger' : 'text-primary-blue';
          
          // Calculate a mock confidence/probability score based on signal strength (50% to 99%)
          const confidence = Math.min(99.9, 50 + (Math.abs(score) * 45)).toFixed(1);

          return (
            <div key={symbol} className={`card ${color} shadow-lg p-6`}>
              <div className="flex items-center justify-between mb-4 border-b border-border-default pb-4">
                <div className="flex items-center gap-2">
                  <BrainCircuit className={`w-4 h-4 ${iconColorClass}`} />
                  <h3 className="sec-head mb-0">{symbol} AI Pulse</h3>
                </div>
                <span className={`tag ${color}`}>{label}</span>
              </div>
              <div className="flex items-baseline gap-3">
                <span className="font-serif text-[32px] font-bold text-text-primary">
                  {score > 0 ? '+' : ''}{score.toFixed(2)}
                </span>
                <span className="font-mono text-[9px] uppercase tracking-wider text-text-muted">
                  Sensitivity Score
                </span>
              </div>
              
              <div className="mt-5 space-y-1.5">
                <div className="flex justify-between items-center font-mono text-[8.5px] uppercase tracking-wider text-text-muted">
                  <span>AI Confidence</span>
                  <span className="text-text-primary font-bold">{confidence}%</span>
                </div>
                <div className="h-1.5 w-full bg-background-base rounded-full overflow-hidden border border-border-default">
                  <div className={`h-full ${score > 0.2 ? 'bg-success' : score < -0.2 ? 'bg-danger' : 'bg-primary-blue'}`} style={{ width: `${confidence}%` }}></div>
                </div>
                <p className="font-sans text-[10px] text-text-muted mt-2 pt-2">Analyzed from {data?.contributing_factors?.article_count || 0} global sources.</p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Alt-Data Feeds */}
      <div className="g212 items-start">
        {/* News Feed */}
        <div className="card blue shadow-lg p-0 overflow-hidden">
          <div className="p-6 border-b border-border-default bg-background-base flex items-center gap-2">
            <Newspaper className="w-4 h-4 text-primary-blue" />
            <h3 className="sec-head mb-0">Global News Feed</h3>
          </div>
          <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
            <table className="nexa-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Source</th>
                  <th>Headline</th>
                </tr>
              </thead>
              <tbody>
                {news.length > 0 ? news.map((article) => (
                  <tr key={article.id}>
                    <td className="whitespace-nowrap font-mono text-[10px]">{new Date(article.published_at).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</td>
                    <td className="whitespace-nowrap"><span className="tag teal">{article.source}</span></td>
                    <td>
                      <a href={article.url} target="_blank" rel="noopener noreferrer" className="hover:text-primary-blue transition-colors font-semibold">
                        {article.title}
                      </a>
                    </td>
                  </tr>
                )) : (
                  <tr><td colSpan={3} className="text-center py-8 text-text-muted">No recent news available.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Economic Calendar Shell */}
        <div className="card gold shadow-lg p-0 overflow-hidden">
          <div className="p-6 border-b border-border-default bg-background-base flex items-center gap-2">
            <Calendar className="w-4 h-4 text-primary-gold" />
            <h3 className="sec-head mb-0">Economic Calendar</h3>
          </div>
          <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
            <table className="nexa-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Country</th>
                  <th>Impact</th>
                  <th>Event</th>
                  <th>Forecast</th>
                </tr>
              </thead>
              <tbody>
                {events.length > 0 ? events.map((event) => (
                  <tr key={event.id}>
                    <td className="whitespace-nowrap font-mono text-[10px]">{new Date(event.timestamp).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</td>
                    <td className="font-mono font-bold text-text-primary">{event.country}</td>
                    <td>
                      <span className={`tag ${event.impact === 'High' ? 'red' : event.impact === 'Medium' ? 'gold' : 'grey'}`}>
                        {event.impact}
                      </span>
                    </td>
                    <td className="font-semibold text-text-primary">{event.event_name}</td>
                    <td className="font-mono text-[11px]">
                      {event.forecast_value ? (
                        <span className="text-primary-blue">{event.forecast_value}</span>
                      ) : (
                        <span className="text-text-muted">--</span>
                      )}
                    </td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan={5} className="p-8 text-center flex flex-col items-center justify-center min-h-[200px]">
                      <Activity className="w-6 h-6 text-text-muted mb-3 opacity-50" />
                      <p className="font-sans text-[13px] text-text-muted mb-1">No upcoming macro events.</p>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}