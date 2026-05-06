import React, { useState, useCallback, useRef } from 'react';
import { AutoComplete, Input, Empty } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { stockDataService } from '../../services/stockDataService';

interface SearchResult {
  code: string;
  name: string;
  industry?: string;
  change_pct?: number;
  price?: number;
}

const StockSearch: React.FC = () => {
  const [options, setOptions] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const navigate = useNavigate();

  const handleSearch = useCallback((value: string) => {
    if (timerRef.current) clearTimeout(timerRef.current);

    if (!value || value.length < 2) {
      setOptions([]);
      setSearched(false);
      return;
    }

    timerRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await stockDataService.searchStocks(value, 10);
        const items: SearchResult[] = res.data?.items || [];
        setSearched(true);
        setOptions(
          items.map((item) => ({
            value: item.code,
            label: (
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>
                  <strong>{item.name}</strong>
                  <span style={{ color: '#999', marginLeft: 8 }}>{item.code}</span>
                </span>
                <span style={{ color: item.change_pct && item.change_pct >= 0 ? '#f5222d' : '#52c41a', fontSize: 12 }}>
                  {item.change_pct !== undefined ? `${item.change_pct > 0 ? '+' : ''}${item.change_pct.toFixed(2)}%` : ''}
                </span>
              </div>
            ),
          })),
        );
      } catch {
        setOptions([]);
      } finally {
        setLoading(false);
      }
    }, 300);
  }, []);

  const handleSelect = (code: string) => {
    navigate(`/market/stock/${code}`);
    setOptions([]);
  };

  return (
    <AutoComplete
      style={{ width: 240 }}
      options={options}
      onSearch={handleSearch}
      onSelect={handleSelect}
      notFoundContent={
        loading ? '搜索中...' : searched ? (
          <Empty
            description="搜索无结果"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            style={{ margin: '8px 0' }}
          />
        ) : undefined
      }
    >
      <Input
        prefix={<SearchOutlined />}
        placeholder="输入股票代码或名称"
        size="small"
        allowClear
      />
    </AutoComplete>
  );
};

export default StockSearch;
