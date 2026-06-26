'use client';

import { useEffect, useRef } from 'react';
import { createChart, IChartApi, ISeriesApi, Time } from 'lightweight-charts';
import { toFiniteNumber, toChartTimestamp } from '@/lib/format';
import { CHART_TEXT_COLOR } from '@/lib/chartTheme';

interface ChartProps {
  data: { time: number | string; value: number }[];
  lineColor?: string;
}

export function SimpleTimeSeriesChart({ data, lineColor = '#CFA43B' }: ChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Area'> | null>(null);

  useEffect(() => {
    if (!chartContainerRef.current || data.length === 0) return;

    if (!chartRef.current) {
      chartRef.current = createChart(chartContainerRef.current, {
        autoSize: true,
        height: 320,
        layout: {
          background: { color: 'transparent' },
          textColor: CHART_TEXT_COLOR,
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

      seriesRef.current = chartRef.current.addAreaSeries({
        lineColor: lineColor,
        topColor: `${lineColor}40`,
        bottomColor: `${lineColor}00`,
        lineWidth: 2,
        priceLineVisible: false,
      });
    }

    const formattedData = data.map(d => ({
      time: toChartTimestamp(d.time),
      value: toFiniteNumber(d.value),
    })).sort((a, b) => (a.time as number) - (b.time as number));

    seriesRef.current?.setData(formattedData);
    chartRef.current?.timeScale().fitContent();

  }, [data, lineColor]);

  return <div ref={chartContainerRef} className="w-full h-[320px]" />;
}