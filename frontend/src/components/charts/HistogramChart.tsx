'use client';

import { useEffect, useRef } from 'react';
import { createChart, IChartApi, ISeriesApi, Time } from 'lightweight-charts';
import { toFiniteNumber, toChartTimestamp } from '@/lib/format';

interface ChartProps {
  data: { time: number | string; value: number }[];
  positiveColor?: string;
  negativeColor?: string;
}

export function HistogramChart({ data, positiveColor = '#1ED6A6', negativeColor = '#FF4D67' }: ChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);

  useEffect(() => {
    if (!chartContainerRef.current || data.length === 0) return;

    if (!chartRef.current) {
      chartRef.current = createChart(chartContainerRef.current, {
        autoSize: true,
        height: 320,
        layout: {
          background: { color: 'transparent' },
          textColor: '#8A94A6',
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 11,
        },
        grid: {
          vertLines: { color: 'rgba(255, 255, 255, 0.04)' },
          horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
        },
        crosshair: {
          vertLine: { color: 'rgba(207, 164, 59, 0.4)', labelBackgroundColor: '#CFA43B' },
          horzLine: { color: 'rgba(207, 164, 59, 0.4)', labelBackgroundColor: '#CFA43B' },
        },
        timeScale: {
          borderColor: 'rgba(255, 255, 255, 0.08)',
          timeVisible: true,
          secondsVisible: false,
        },
        rightPriceScale: { borderColor: 'rgba(255, 255, 255, 0.08)' },
      });

      seriesRef.current = chartRef.current.addHistogramSeries({
        base: 0,
      });
    }

    const formattedData = data.map(d => {
      const value = toFiniteNumber(d.value);
      return {
        time: toChartTimestamp(d.time),
        value: value,
        color: value >= 0 ? positiveColor : negativeColor,
      };
    }).sort((a, b) => (a.time as number) - (b.time as number));

    seriesRef.current?.setData(formattedData);
    chartRef.current?.timeScale().fitContent();

  }, [data, positiveColor, negativeColor]);

  return <div ref={chartContainerRef} className="w-full h-[320px]" />;
}