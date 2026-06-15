'use client';

import { useEffect, useRef } from 'react';
import { createChart, ColorType, Time } from 'lightweight-charts';

interface EquityCurveChartProps {
  // Accept both API response formats: 
  // 1. Portfolio API: { timestamp: string, equity: number }
  // 2. Backtest API: { time: number, value: number }
  data: any[];
}

export function EquityCurveChart({ data }: EquityCurveChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!chartContainerRef.current || !data || !Array.isArray(data)) return;

    const chart = createChart(chartContainerRef.current, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#D1D5DB',
      },
      grid: {
        vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
        horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
      },
      timeScale: {
        borderColor: 'rgba(255, 255, 255, 0.1)',
      },
      rightPriceScale: {
        borderColor: 'rgba(255, 255, 255, 0.1)',
      },
    });

    const areaSeries = chart.addAreaSeries({
      lineColor: '#00C896',
      topColor: 'rgba(0, 200, 150, 0.4)',
      bottomColor: 'rgba(0, 200, 150, 0.0)',
      lineWidth: 2,
    });

    // Format, deduplicate, and sort the data for the chart:
    const dataMap = new Map<number, number>();
    
    if (data.length > 0) {
      data.forEach(point => {
        let timeKey: number;
        let val: number;

        if (point.timestamp != null && point.equity != null) {
          timeKey = Math.floor(new Date(point.timestamp).getTime() / 1000);
          val = Number(point.equity);
        } else if (point.time != null && point.value != null) {
          timeKey = Math.floor(Number(point.time));
          val = Number(point.value);
        } else {
          return;
        }

        if (!Number.isFinite(timeKey) || !Number.isFinite(val)) return;

        dataMap.set(timeKey, val);
      });
    }

    const formattedData = Array.from(dataMap.entries())
      .map(([time, value]) => ({ time: time as Time, value }))
      .sort((a, b) => (a.time as number) - (b.time as number));

    // Lightweight charts requires at least 2 points to draw an area/line.
    // If a portfolio is brand new, duplicate the point 1 hour into the future to draw a flat line.
    if (formattedData.length === 1) {
      formattedData.push({
        time: ((formattedData[0].time as number) + 3600) as Time,
        value: formattedData[0].value,
      });
    }

    if (formattedData.length > 0) {
      areaSeries.setData(formattedData);
      chart.timeScale().fitContent();
    }

    return () => chart.remove();
  }, [data]);

  if (!data || data.length === 0) {
    return <div className="flex justify-center items-center h-[300px] w-full border border-border-default rounded-[3px] text-text-muted text-[13px] font-sans italic">No equity data available for this portfolio yet.</div>;
  }

  return <div ref={chartContainerRef} className="w-full h-[300px] card gold p-4" />;
}
