import React, { useRef, useEffect, useMemo } from 'react';
import * as echarts from 'echarts';
import { Skeleton, Empty } from 'antd';

interface KLineChartProps {
  data: any[];
  indicators?: any[];
  showMA?: boolean;
  showMACD?: boolean;
  showKDJ?: boolean;
  height?: number;
  loading?: boolean;
  period?: string;
  minuteData?: any[];
}

const KLineChart: React.FC<KLineChartProps> = ({
  data,
  indicators = [],
  showMA = true,
  showMACD = false,
  showKDJ = false,
  height = 500,
  loading = false,
  period = 'daily',
  minuteData = [],
}) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  const hasData = period === 'minute' ? minuteData.length > 0 : (data && data.length > 0);

  const option = useMemo(() => {
    if (period === 'minute' && minuteData.length > 0) {
      return buildMinuteOption(minuteData);
    }
    if (!data || data.length === 0) return null;
    return buildDailyOption(data, indicators, showMA, showMACD, showKDJ);
  }, [data, indicators, showMA, showMACD, showKDJ, period, minuteData]);

  useEffect(() => {
    if (!chartRef.current) return;
    // 每次都重新 init，避免 DOM 被替换后旧实例失效
    if (chartInstance.current) {
      chartInstance.current.dispose();
      chartInstance.current = null;
    }
    if (option) {
      chartInstance.current = echarts.init(chartRef.current);
      chartInstance.current.setOption(option, true);
    }
  }, [option]);

  useEffect(() => {
    const handleResize = () => chartInstance.current?.resize();
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      chartInstance.current?.dispose();
      chartInstance.current = null;
    };
  }, []);

  if (loading) {
    return (
      <Skeleton.Image
        active
        style={{ width: '100%', height }}
        styles={{ image: { height } }}
      />
    );
  }

  if (!hasData) {
    return (
      <div style={{ width: '100%', height, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#fafafa', borderRadius: 4 }}>
        <Empty description={`暂无${period === 'minute' ? '分时' : period === 'daily' ? '日K' : period === 'weekly' ? '周K' : '月K'}数据`} />
      </div>
    );
  }

  return <div ref={chartRef} style={{ width: '100%', height }} />;
};

function buildMinuteOption(data: any[]) {
  const times = data.map((d) => d.time);
  const prices = data.map((d) => d.price);
  const volumes = data.map((d) => d.volume);
  const avgPrices = data.map((d) => d.avg_price);

  return {
    animation: false,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
    },
    grid: [
      { left: 60, right: 20, top: 20, height: '60%' },
      { left: 60, right: 20, top: '72%', height: '20%' },
    ],
    xAxis: [
      { type: 'category', data: times, gridIndex: 0, boundaryGap: false },
      { type: 'category', data: times, gridIndex: 1, boundaryGap: false },
    ],
    yAxis: [
      { type: 'value', gridIndex: 0, scale: true },
      { type: 'value', gridIndex: 1, scale: true },
    ],
    series: [
      {
        name: '价格',
        type: 'line',
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: prices,
        lineStyle: { color: '#533afd', width: 1.5 },
        symbol: 'none',
      },
      {
        name: '均价',
        type: 'line',
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: avgPrices,
        lineStyle: { color: '#faad14', width: 1 },
        symbol: 'none',
      },
      {
        name: '成交量',
        type: 'bar',
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: volumes,
      },
    ],
  };
}

function buildDailyOption(
  data: any[],
  indicators: any[],
  showMA: boolean,
  showMACD: boolean,
  showKDJ: boolean,
) {
  const dates = data.map((d) => d.trade_date);
  const ohlc = data.map((d) => [d.open, d.close, d.low, d.high]);
  const volumes = data.map((d) => ({
    value: d.volume,
    itemStyle: {
      color: d.close >= d.open ? '#f5222d' : '#52c41a',
    },
  }));

  // 布局：K线主图 + 成交量 + (MACD?) + (KDJ?)
  const subHeight = 10;
  const gap = 2;
  const volHeight = 10;
  let currentTop = 30;
  const mainHeight = Math.max(30, 60 - (showMACD ? subHeight + gap : 0) - (showKDJ ? subHeight + gap : 0));

  // Grid 0: K线主图
  const grids: any[] = [{ left: 70, right: 20, top: currentTop, height: `${mainHeight}%` }];
  const xAxes: any[] = [{ type: 'category', data: dates, gridIndex: 0, boundaryGap: true, axisLabel: { show: false } }];
  const yAxes: any[] = [{ type: 'value', gridIndex: 0, scale: true, splitLine: { lineStyle: { color: '#f0f0f0' } } }];

  // K线
  const series: any[] = [
    {
      name: 'K线',
      type: 'candlestick',
      xAxisIndex: 0,
      yAxisIndex: 0,
      data: ohlc,
      itemStyle: {
        color: '#f5222d',
        color0: '#52c41a',
        borderColor: '#f5222d',
        borderColor0: '#52c41a',
      },
    },
  ];

  // MA 均线（K线主图上叠加）
  if (showMA && indicators.length > 0) {
    series.push(
      { name: 'MA5', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: indicators.map((d) => d.ma5), smooth: true, symbol: 'none', lineStyle: { width: 1 } },
      { name: 'MA10', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: indicators.map((d) => d.ma10), smooth: true, symbol: 'none', lineStyle: { width: 1 } },
      { name: 'MA20', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: indicators.map((d) => d.ma20), smooth: true, symbol: 'none', lineStyle: { width: 1 } },
    );
  }

  currentTop += mainHeight + gap;

  // Grid 1: 成交量（独立 grid + y 轴）
  grids.push({ left: 70, right: 20, top: `${currentTop}%`, height: `${volHeight}%` });
  xAxes.push({ type: 'category', data: dates, gridIndex: 1, boundaryGap: true, axisLabel: { show: false } });
  yAxes.push({ type: 'value', gridIndex: 1, scale: true, splitNumber: 2, axisLabel: { fontSize: 10 } });
  series.push({
    name: '成交量',
    type: 'bar',
    xAxisIndex: 1,
    yAxisIndex: 1,
    data: volumes,
    barMaxWidth: 6,
  });

  currentTop += volHeight + gap;

  // MACD 副图
  if (showMACD && indicators.length > 0) {
    const gridIdx = grids.length;
    grids.push({ left: 70, right: 20, top: `${currentTop}%`, height: `${subHeight}%` });
    xAxes.push({ type: 'category', data: dates, gridIndex: gridIdx, boundaryGap: true, axisLabel: { show: false } });
    yAxes.push({ type: 'value', gridIndex: gridIdx, scale: true, splitNumber: 2 });

    const bar = indicators.map((d) => ({
      value: d.macd_bar,
      itemStyle: { color: d.macd_bar >= 0 ? '#f5222d' : '#52c41a' },
    }));

    series.push(
      { name: 'DIF', type: 'line', xAxisIndex: gridIdx, yAxisIndex: gridIdx, data: indicators.map((d) => d.macd_dif), symbol: 'none', lineStyle: { width: 1 } },
      { name: 'DEA', type: 'line', xAxisIndex: gridIdx, yAxisIndex: gridIdx, data: indicators.map((d) => d.macd_dea), symbol: 'none', lineStyle: { width: 1 } },
      { name: 'MACD', type: 'bar', xAxisIndex: gridIdx, yAxisIndex: gridIdx, data: bar, barMaxWidth: 4 },
    );
    currentTop += subHeight + gap;
  }

  // KDJ 副图
  if (showKDJ && indicators.length > 0) {
    const gridIdx = grids.length;
    grids.push({ left: 70, right: 20, top: `${currentTop}%`, height: `${subHeight}%` });
    xAxes.push({ type: 'category', data: dates, gridIndex: gridIdx, boundaryGap: true });
    yAxes.push({ type: 'value', gridIndex: gridIdx, scale: true, min: 0, max: 100 });

    series.push(
      { name: 'K', type: 'line', xAxisIndex: gridIdx, yAxisIndex: gridIdx, data: indicators.map((d) => d.kdj_k), symbol: 'none', lineStyle: { width: 1 } },
      { name: 'D', type: 'line', xAxisIndex: gridIdx, yAxisIndex: gridIdx, data: indicators.map((d) => d.kdj_d), symbol: 'none', lineStyle: { width: 1 } },
      { name: 'J', type: 'line', xAxisIndex: gridIdx, yAxisIndex: gridIdx, data: indicators.map((d) => d.kdj_j), symbol: 'none', lineStyle: { width: 1, type: 'dashed' } },
    );
  }

  // 默认展示最近6个月（约120个交易日）
  const defaultStart = Math.max(0, ((dates.length - 120) / dates.length) * 100);

  return {
    animation: false,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (params: any) => {
        if (!params || params.length === 0) return '';
        const idx = params[0].dataIndex;
        const d = data[idx];
        if (!d) return '';
        let html = `<div style="font-size:12px">${d.trade_date}<br/>`;
        html += `开: ${d.open} 收: ${d.close}<br/>`;
        html += `高: ${d.high} 低: ${d.low}<br/>`;
        html += `量: ${formatVolume(d.volume)}</div>`;
        return html;
      },
    },
    legend: { top: 5, textStyle: { fontSize: 11 } },
    grid: grids,
    xAxis: xAxes,
    yAxis: yAxes,
    dataZoom: [
      { type: 'inside', xAxisIndex: xAxes.map((_, i) => i), start: defaultStart, end: 100 },
      { type: 'slider', xAxisIndex: xAxes.map((_, i) => i), start: defaultStart, end: 100, top: 'bottom', height: 20 },
    ],
    series,
  };
}

function formatVolume(v: number | null): string {
  if (!v) return '--';
  if (v >= 100000000) return (v / 100000000).toFixed(2) + '亿';
  if (v >= 10000) return (v / 10000).toFixed(2) + '万';
  return v.toString();
}

export default KLineChart;
