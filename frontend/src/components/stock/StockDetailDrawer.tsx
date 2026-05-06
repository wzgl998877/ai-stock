import React, { useEffect } from 'react';
import { Drawer, Button } from 'antd';
import { useNavigate } from 'react-router-dom';
import { useStockDetailStore } from '../../store/stockDetailStore';
import PriceCard from './PriceCard';
import KLineChart from './KLineChart';

interface StockDetailDrawerProps {
  visible: boolean;
  stockCode: string | null;
  onClose: () => void;
}

const StockDetailDrawer: React.FC<StockDetailDrawerProps> = ({ visible, stockCode, onClose }) => {
  const navigate = useNavigate();
  const { basic, quote, klineData, minuteData, indicators, activePeriod, klineLoading, fetchStockDetail, fetchKlineData, clear } = useStockDetailStore();

  useEffect(() => {
    if (visible && stockCode) {
      fetchStockDetail(stockCode);
    }
    if (!visible) {
      clear();
    }
  }, [visible, stockCode]);

  const handleExpand = () => {
    if (stockCode) {
      onClose();
      navigate(`/market/stock/${stockCode}`);
    }
  };

  return (
    <Drawer
      title={basic ? `${basic.name} ${stockCode}` : '加载中...'}
      placement="right"
      width={480}
      open={visible}
      onClose={onClose}
      extra={
        <Button type="link" size="small" onClick={handleExpand}>
          展开完整页面
        </Button>
      }
    >
      {quote && (
        <PriceCard
          name={basic?.name || ''}
          code={stockCode || ''}
          price={quote.price}
          changeAmount={quote.change_amount}
          changePct={quote.change_pct}
          volume={quote.volume}
          amount={quote.amount}
        />
      )}
      <KLineChart
        data={klineData}
        minuteData={minuteData}
        indicators={indicators}
        showMA={true}
        showMACD={false}
        showKDJ={false}
        height={350}
        loading={klineLoading}
        period={activePeriod}
      />
      <div style={{ fontSize: 11, color: '#999', textAlign: 'center', marginTop: 8 }}>
        数据延迟15-30分钟 · 不构成投资建议
      </div>
    </Drawer>
  );
};

export default StockDetailDrawer;
