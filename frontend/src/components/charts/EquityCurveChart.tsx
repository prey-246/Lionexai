'use client';

import { useEffect, useRef } from 'react';
import { createChart, ColorType, Time } from 'lightweight-charts';
import type { EquityDataPoint } from '@/lib/types';

interface EquityCurveChartProps {
  data: EquityDataPoint[];
}

export function EquityCurveChart({ data }: EquityCurveChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!chartContainerRef.current || data.length === 0) return;

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 300,
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
      lineColor: '#22D3EE',
      topColor: 'rgba(34, 211, 238, 0.4)',
      bottomColor: 'rgba(34, 211, 238, 0.0)',
      lineWidth: 2,
    });

    // Cast the numerical timestamp to the strictly expected Time type
    areaSeries.setData(data.map(point => ({
      ...point, time: point.time as Time
    })));
    chart.timeScale().fitContent();

    return () => chart.remove();
  }, [data]);

  return <div ref={chartContainerRef} />;
}
