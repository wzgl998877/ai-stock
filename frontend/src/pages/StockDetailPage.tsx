import React, { useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Tabs, Skeleton, Alert, Card } from 'antd';
import { useStockDetailStore, isMarketOpen } from '../store/stockDetailStore';
import PriceCard from '../components/stock/PriceCard';
import KLineChart from '../components/stock/KLineChart';
import PeriodSelector from '../components/stock/PeriodSelector';
import IndicatorToggle from '../components/stock/IndicatorToggle';
import FinancialTab from '../components/stock/FinancialTab';
import RelatedAnalysisTab from '../components/stock/RelatedAnalysisTab';
import IndustryComparison from '../components/stock/IndustryComparison';
import AddToWatchlistButton from '../components/stock/AddToWatchlistButton';
import SyncKlineButton from '../components/stock/SyncKlineButton';

/** 分时轮询间隔（毫秒） */
const MINUTE_POLL_INTERVAL = 30_000;

const StockDetailPage: React.FC = () => {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const {
    basic, quote, financial, klineData, minuteData, indicators,
    relatedArticles, loading, klineLoading, error,
    activePeriod, showMACD, showKDJ,
    fetchStockDetail, setActivePeriod, toggleMACD, toggleKDJ, clear,
    fetchKlineData, refreshMinuteData,
  } = useStockDetailStore();

  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // --- 分时轮询控制 ---
  const startPolling = useCallback(() => {
    if (pollTimerRef.current) return;
    pollTimerRef.current = setInterval(() => {
      const c = useStockDetailStore.getState().stockCode;
      if (c && isMarketOpen()) {
        refreshMinuteData(c);
      }
    }, MINUTE_POLL_INTERVAL);
  }, [refreshMinuteData]);

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (code) {
      fetchStockDetail(code);
    }
    return () => {
      stopPolling();
      clear();
    };
  }, [code]);

  // 当 activePeriod 变化时，控制轮询启停
  useEffect(() => {
    if (activePeriod === 'minute' && code && isMarketOpen()) {
      startPolling();
    } else {
      stopPolling();
    }
  }, [activePeriod, code, startPolling, stopPolling]);

  if (loading) {
    return (
      <div style={{ padding: 16 }}>
        {/* PriceCard skeleton */}
        <Card size="small" style={{ marginBottom: 12 }}>
          <Skeleton.Input active size="small" style={{ width: 120 }} />
          <Skeleton.Input active size="default" style={{ width: 100, marginLeft: 16 }} />
          <Skeleton.Input active size="small" style={{ width: 80, marginLeft: 16 }} />
        </Card>

        {/* KLineChart skeleton */}
        <Card size="small" style={{ marginBottom: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <Skeleton.Input active size="small" style={{ width: 200 }} />
            <Skeleton.Input active size="small" style={{ width: 120 }} />
          </div>
          <Skeleton.Image active style={{ width: '100%', height: 450 }} styles={{ image: { height: 450 } }} />
        </Card>

        {/* Tabs skeleton */}
        <Card size="small">
          <Skeleton.Input active size="small" style={{ width: 300, marginBottom: 16 }} />
          <Skeleton active paragraph={{ rows: 4 }} />
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <Alert
        type="error"
        message={error}
        showIcon
        style={{ margin: 24 }}
        action={<a onClick={() => code && fetchStockDetail(code)}>重试</a>}
      />
    );
  }

  const handleArticleClick = (articleId: string) => {
    navigate(`/knowledge/articles/${articleId}`);
  };

  const tabItems = [
    {
      key: 'basic',
      label: '基本信息',
      children: basic ? (
        <div style={{ fontSize: 14, color: '#666' }}>
          <p>交易所：{basic.exchange}</p>
          <p>行业：{basic.industry_name || '--'}</p>
          <p>上市日期：{basic.list_date || '--'}</p>
          <p>总市值：{formatCap(basic.total_market_cap)}</p>
          <p>流通市值：{formatCap(basic.float_market_cap)}</p>
        </div>
      ) : <div>暂无基本信息</div>,
    },
    {
      key: 'financial',
      label: '财务数据',
      children: <FinancialTab financial={financial ? { ...financial, pe_ttm: quote?.pe_ttm, pb: quote?.pb } : null} />,
    },
    {
      key: 'comparison',
      label: '同行对比',
      children: basic?.industry_code ? <IndustryComparison industryCode={basic.industry_code} /> : <div>暂无行业数据</div>,
    },
    {
      key: 'analysis',
      label: '相关分析',
      children: <RelatedAnalysisTab articles={relatedArticles} onClick={handleArticleClick} />,
    },
  ];

  return (
    <div style={{ padding: 16 }}>
      {/* 顶部价格卡 + 操作 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ flex: 1 }}>
          {quote && (
            <PriceCard
              name={basic?.name || ''}
              code={code || ''}
              price={quote.price}
              changeAmount={quote.change_amount}
              changePct={quote.change_pct}
              volume={quote.volume}
              amount={quote.amount}
            />
          )}
        </div>
        {code && basic && <AddToWatchlistButton stockCode={code} stockName={basic.name} />}
      </div>

      {/* K线图区域 */}
      <Card size="small" style={{ marginBottom: 12 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <PeriodSelector activePeriod={activePeriod} onChange={setActivePeriod} />
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <IndicatorToggle
              showMACD={showMACD}
              showKDJ={showKDJ}
              onToggleMACD={toggleMACD}
              onToggleKDJ={toggleKDJ}
            />
            {activePeriod !== 'minute' && code && (
              <SyncKlineButton
                code={code}
                period={activePeriod as 'daily' | 'weekly' | 'monthly'}
                onSuccess={() => fetchKlineData(code, activePeriod)}
              />
            )}
          </div>
        </div>
        <KLineChart
          data={klineData}
          minuteData={minuteData}
          indicators={indicators}
          showMA={true}
          showMACD={showMACD}
          showKDJ={showKDJ}
          height={450}
          loading={klineLoading}
          period={activePeriod}
        />
      </Card>

      {/* 底部标签页 */}
      <Card size="small">
        <Tabs items={tabItems} />
      </Card>

      {/* 免责声明 */}
      <div style={{ textAlign: 'center', color: '#999', fontSize: 12, marginTop: 12 }}>
        数据延迟15-30分钟 · 不构成投资建议
      </div>
    </div>
  );
};

function formatCap(v: number | undefined | null): string {
  if (!v) return '--';
  if (v >= 10000) return (v / 10000).toFixed(2) + ' 万亿';
  return v.toFixed(2) + ' 亿';
}

export default StockDetailPage;
