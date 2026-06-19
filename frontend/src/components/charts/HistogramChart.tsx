'use client';

import { useEffect, useRef } from 'react';
import { createChart, IChartApi, ISeriesApi, Time } from 'lightweight-charts';
import { toFiniteNumber, toChartTimestamp } from '@/lib/format';

interface ChartProps {
  data: { time: number | string; value: number }[];
  positiveColor?: string;
  negativeColor?: string;
}

export function HistogramChart({ data, positiveColor = '#22c55e', negativeColor = '#ef4444' }: ChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);

  useEffect(() => {
    if (!chartContainerRef.current || data.length === 0) return;

    if (!chartRef.current) {
      chartRef.current = createChart(chartContainerRef.current, {
        width: chartContainerRef.current.clientWidth,
        height: 300,
        layout: {
          background: { color: 'transparent' },
          textColor: '#A0A0A0',
        },
        grid: {
          vertLines: { color: '#2A2A2A' },
          horzLines: { color: '#2A2A2A' },
        },
        timeScale: {
          borderColor: '#4A4A4A',
          timeVisible: true,
          secondsVisible: false,
        },
        rightPriceScale: {
          borderColor: '#4A4A4A',
        },
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

  return <div ref={chartContainerRef} className="w-full h-[300px]" />;
}