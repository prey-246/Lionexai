'use client';

import { useEffect, useRef } from 'react';
import { createChart, IChartApi, ISeriesApi, Time } from 'lightweight-charts';
import { toFiniteNumber, toChartTimestamp } from '@/lib/format';

interface ChartProps {
  data: { time: number | string; value: number }[];
  lineColor?: string;
}

export function SimpleTimeSeriesChart({ data, lineColor = '#D4AF37' }: ChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Area'> | null>(null);

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

      seriesRef.current = chartRef.current.addAreaSeries({
        lineColor: lineColor,
        topColor: `${lineColor}40`,
        bottomColor: `${lineColor}00`,
        lineWidth: 2,
      });
    }

    const formattedData = data.map(d => ({
      time: toChartTimestamp(d.time),
      value: toFiniteNumber(d.value),
    })).sort((a, b) => (a.time as number) - (b.time as number));

    seriesRef.current?.setData(formattedData);
    chartRef.current?.timeScale().fitContent();

  }, [data, lineColor]);

  return <div ref={chartContainerRef} className="w-full h-[300px]" />;
}