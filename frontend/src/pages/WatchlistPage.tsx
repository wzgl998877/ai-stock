import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Button, Modal, Input, Popconfirm, Empty, Spin, Tag, Alert,
  Table, Pagination, message, Select, Tooltip, Switch,
} from 'antd';
import {
  PlusOutlined, DeleteOutlined, EditOutlined, SearchOutlined,
  ReloadOutlined, ClockCircleOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useWatchlistStore, type WatchlistStock } from '../store/watchlistStore';
import { useEventRadarStore } from '../store/eventRadarStore';
import { stockDataService } from '../services/stockDataService';
import { eventRadarService } from '../services/eventRadarService';
import { isMarketOpen } from '../utils/marketTime';
import SignalBadge from '../components/strategy/SignalBadge';
import { useStrategyStore } from '../store/strategyStore';
import WatchlistImpactColumn from '../components/event-radar/WatchlistImpactColumn';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const formatNumber = (v: number | null | undefined, decimals = 2) => {
  if (v === undefined || v === null) return '--';
  return v.toFixed(decimals);
};

const formatDate = (v: string | null | undefined) => {
  if (!v) return '--';
  return v.slice(0, 10);
};

const getChangeColor = (value: number | null | undefined) => {
  if (value === undefined || value === null) return '#64748d';
  return value >= 0 ? '#cf1322' : '#389e0d';
};

const getChangeBg = (value: number | null | undefined) => {
  if (value === undefined || value === null) return 'transparent';
  if (value === 0) return 'transparent';
  return value > 0
    ? 'rgba(207, 19, 34, 0.06)'
    : 'rgba(56, 158, 13, 0.06)';
};

const formatRefreshTime = (ts: number | null) => {
  if (!ts) return '';
  const d = new Date(ts);
  return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}:${d.getSeconds().toString().padStart(2, '0')}`;
};

// isMarketOpen 由 utils/marketTime 提供（北京时区 A 股时段判断）

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/** 逐股逐周期监控开关（T055）：关闭后徽标显示「停用」。 */
const MonitorToggle: React.FC<{
  stockCode: string;
  dailyStatus?: string;
  m30Status?: string;
}> = ({ stockCode, dailyStatus, m30Status }) => {
  const updateConfig = useStrategyStore((s) => s.updateConfig);
  const [loading, setLoading] = useState<null | 'daily' | 'm30'>(null);

  const toggle = async (period: 'daily' | 'm30', enabled: boolean) => {
    setLoading(period);
    try {
      await updateConfig(stockCode, { [`${period}_enabled`]: enabled });
      message.success(`${period === 'daily' ? '日 K' : '30 分钟'}监控已${enabled ? '开启' : '关闭'}`);
    } catch (e: any) {
      message.error(e?.message || '更新监控配置失败');
    } finally {
      setLoading(null);
    }
  };

  return (
    <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginTop: 4, fontSize: 11 }}>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3, color: '#999' }}>
        日
        <Switch
          size="small"
          checked={dailyStatus !== 'disabled'}
          loading={loading === 'daily'}
          onChange={(v) => toggle('daily', v)}
        />
      </span>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3, color: '#999' }}>
        30m
        <Switch
          size="small"
          checked={m30Status !== 'disabled'}
          loading={loading === 'm30'}
          onChange={(v) => toggle('m30', v)}
        />
      </span>
    </div>
  );
};

const WatchlistPage: React.FC = () => {
  const navigate = useNavigate();
  const {
    groups, loading, refreshing, error, lastRefreshTime,
    fetchGroups, createGroup, renameGroup,
    deleteGroup, removeStock, addStock, refreshQuotes,
  } = useWatchlistStore();

  const { stockImpacts, setStockImpacts } = useEventRadarStore();
  const { watchlistSignals, fetchWatchlistSignals } = useStrategyStore();
  const [signalFilter, setSignalFilter] = useState<'all' | 'has_buy' | 'has_sell' | 'none'>('all');

  const [selectedGroupId, setSelectedGroupId] = useState<number | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [newGroupName, setNewGroupName] = useState('');
  const [renameModalOpen, setRenameModalOpen] = useState<{ id: number; name: string } | null>(null);
  const [searchText, setSearchText] = useState('');
  const [addModalOpen, setAddModalOpen] = useState(false);

  const refreshTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    fetchGroups();
    fetchWatchlistSignals();
  }, []);

  // 加载自选股事件影响数据
  useEffect(() => {
    const loadStockImpacts = async () => {
      try {
        const res = await eventRadarService.getStockImpacts();
        setStockImpacts(res?.data ?? []);
      } catch {
        // 静默失败，不影响自选股页面主流程
      }
    };
    loadStockImpacts();
  }, [groups, setStockImpacts]);

  // Auto-select first group
  useEffect(() => {
    if (groups.length > 0 && !selectedGroupId) {
      setSelectedGroupId(groups[0].id);
    }
  }, [groups]);

  // Reset selectedGroupId if group was deleted
  useEffect(() => {
    if (selectedGroupId && !groups.find((g) => g.id === selectedGroupId)) {
      setSelectedGroupId(groups.length > 0 ? groups[0].id : null);
    }
  }, [groups, selectedGroupId]);

  // Auto-refresh: trading hours 30s, off-hours stop
  useEffect(() => {
    const tick = () => {
      if (isMarketOpen()) {
        refreshQuotes();
        fetchWatchlistSignals();
      } else if (refreshTimerRef.current) {
        clearInterval(refreshTimerRef.current);
        refreshTimerRef.current = null;
      }
    };

    // Start immediately if market open
    if (isMarketOpen()) {
      refreshTimerRef.current = setInterval(tick, 30000);
    }

    // Re-check every 60s to resume when market opens
    const guard = setInterval(() => {
      if (isMarketOpen() && !refreshTimerRef.current) {
        refreshTimerRef.current = setInterval(tick, 30000);
      }
    }, 60000);

    return () => {
      if (refreshTimerRef.current) clearInterval(refreshTimerRef.current);
      clearInterval(guard);
    };
  }, [refreshQuotes]);

  const handleCreate = async () => {
    if (!newGroupName.trim()) return;
    await createGroup(newGroupName.trim());
    setNewGroupName('');
    setCreateModalOpen(false);
    message.success('分组创建成功');
  };

  const handleRename = async () => {
    if (!renameModalOpen || !renameModalOpen.name.trim()) return;
    await renameGroup(renameModalOpen.id, renameModalOpen.name.trim());
    setRenameModalOpen(null);
    message.success('重命名成功');
  };

  const handleRemoveStock = useCallback(async (groupId: number, stockCode: string, stockName: string) => {
    await removeStock(groupId, stockCode);
    message.success(`已将 ${stockName} 移出分组`);
  }, [removeStock]);

  const handleAddStock = useCallback(async (groupId: number, stockCode: string, stockName: string) => {
    await addStock(groupId, stockCode, stockName);
    message.success(`已添加 ${stockName}`);
  }, [addStock]);

  const handleManualRefresh = useCallback(() => {
    refreshQuotes();
  }, [refreshQuotes]);

  // -----------------------------------------------------------------------
  // Derived data
  // -----------------------------------------------------------------------

  const selectedGroup = groups.find((g) => g.id === selectedGroupId) ?? null;
  const stocks = selectedGroup?.stocks ?? [];

  const searched = searchText
    ? stocks.filter(
        (s) =>
          s.code.includes(searchText) ||
          s.name.toLowerCase().includes(searchText.toLowerCase()),
      )
    : stocks;

  // 信号筛选：有买点 / 有卖点 / 无信号 / 全部
  const filteredStocks = searched.filter((s) => {
    if (signalFilter === 'all') return true;
    const sig = watchlistSignals.find((w) => w.stock_code === s.code);
    const dt = sig?.daily?.signal_type;
    const mt = sig?.m30?.signal_type;
    if (signalFilter === 'none') return !dt && !mt;
    if (signalFilter === 'has_buy') return !!dt?.startsWith('buy') || !!mt?.startsWith('buy');
    if (signalFilter === 'has_sell') return !!dt?.startsWith('sell') || !!mt?.startsWith('sell');
    return true;
  });

  const total = filteredStocks.length;
  const pagedStocks = filteredStocks.slice((page - 1) * pageSize, page * pageSize);

  useEffect(() => {
    setPage(1);
  }, [selectedGroupId, searchText]);

  // Check if quotes data is available
  const hasQuotes = stocks.some((s) => s.price != null);

  // -----------------------------------------------------------------------
  // Table columns
  // -----------------------------------------------------------------------

  const linkStyle = { color: '#533afd', textDecoration: 'none', cursor: 'pointer' };

  const numStyle: React.CSSProperties = {
    fontVariantNumeric: 'tabular-nums',
    letterSpacing: '-0.01em',
  };

  const columns: ColumnsType<WatchlistStock> = [
    {
      title: '序号',
      key: 'index',
      width: 52,
      align: 'center',
      render: (_: unknown, _record: WatchlistStock, index: number) => (
        <span style={{ color: '#999', fontSize: 12 }}>{(page - 1) * pageSize + index + 1}</span>
      ),
    },
    {
      title: '代码',
      dataIndex: 'code',
      key: 'code',
      width: 88,
      fixed: 'left',
      align: 'center',
      render: (code: string) => (
        <a onClick={() => navigate(`/market/stock/${code}`)} style={linkStyle}>
          {code}
        </a>
      ),
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 100,
      fixed: 'left',
      align: 'center',
      render: (name: string, record) => (
        <a onClick={() => navigate(`/market/stock/${record.code}`)} style={linkStyle}>
          {name}
        </a>
      ),
    },
    {
      title: '最新价',
      dataIndex: 'price',
      key: 'price',
      width: 96,
      align: 'center',
      render: (v: number | undefined) => {
        const hasValue = v !== undefined && v !== null;
        return (
          <span style={{
            ...numStyle,
            fontWeight: 600,
            fontSize: 14,
            color: hasValue ? '#061b31' : '#bfbfbf',
          }}>
            {formatNumber(v)}
          </span>
        );
      },
    },
    {
      title: '涨跌幅',
      dataIndex: 'change_pct',
      key: 'change_pct',
      width: 100,
      align: 'center',
      render: (v: number | undefined) => {
        const hasValue = v !== undefined && v !== null;
        return (
          <span style={{
            ...numStyle,
            fontWeight: 600,
            fontSize: 13,
            color: getChangeColor(v),
            background: getChangeBg(v),
            padding: '2px 8px',
            borderRadius: 4,
          }}>
            {hasValue ? `${v > 0 ? '+' : ''}${v.toFixed(2)}%` : '--'}
          </span>
        );
      },
      sorter: (a, b) => (a.change_pct ?? -999) - (b.change_pct ?? -999),
    },
    {
      title: '影响',
      key: 'event_impact',
      width: 100,
      align: 'center',
      render: (_: unknown, record: WatchlistStock) => {
        const impact = stockImpacts.find((s) => s.code === record.code);
        return (
          <WatchlistImpactColumn
            impactCount={impact?.impact_count_24h ?? 0}
            direction={impact?.direction ?? 'neutral'}
            recentImpacts={impact?.recent_impacts ?? []}
          />
        );
      },
    },
    {
      title: '信号',
      key: 'chanlun_signal',
      width: 150,
      align: 'center',
      render: (_: unknown, record: WatchlistStock) => {
        const sig = watchlistSignals.find((w) => w.stock_code === record.code);
        return (
          <div>
            <SignalBadge
              stockCode={record.code}
              stockName={record.name}
              daily={sig?.daily ?? null}
              dailyStatus={sig?.daily_status}
              m30={sig?.m30 ?? null}
              m30Status={sig?.m30_status}
              onAnalyze={(code) => navigate(`/stock-analysis?code=${code}`)}
            />
            <MonitorToggle
              stockCode={record.code}
              dailyStatus={sig?.daily_status}
              m30Status={sig?.m30_status}
            />
          </div>
        );
      },
    },
    {
      title: '涨跌额',
      dataIndex: 'change_amount',
      key: 'change_amount',
      width: 88,
      align: 'center',
      render: (v: number | undefined) => {
        const hasValue = v !== undefined && v !== null;
        return (
          <span style={{
            ...numStyle,
            fontSize: 13,
            fontWeight: 500,
            color: getChangeColor(v),
          }}>
            {hasValue ? `${v > 0 ? '+' : ''}${v.toFixed(2)}` : '--'}
          </span>
        );
      },
    },
    {
      title: '所属行业',
      dataIndex: 'industry',
      key: 'industry',
      width: 100,
      align: 'center',
      render: (v: string | undefined) => (
        v
          ? <Tag style={{ margin: 0, fontSize: 12, borderRadius: 4, color: '#273951', borderColor: '#e5edf5', background: '#f5f7fa' }}>{v}</Tag>
          : <span style={{ color: '#bfbfbf', fontSize: 12 }}>--</span>
      ),
    },
    {
      title: '自选日',
      dataIndex: 'add_time',
      key: 'add_time',
      width: 100,
      align: 'center',
      render: (v: string | undefined) => (
        <span style={{ color: '#061b31', fontSize: 13 }}>{formatDate(v)}</span>
      ),
    },
    {
      title: '自选价',
      dataIndex: 'add_price',
      key: 'add_price',
      width: 88,
      align: 'center',
      render: (v: number | undefined) => (
        <span style={{ ...numStyle, color: '#061b31', fontSize: 14, fontWeight: 500 }}>
          {formatNumber(v)}
        </span>
      ),
    },
    {
      title: '自选涨幅',
      key: 'watchlist_change_pct',
      width: 100,
      align: 'center',
      render: (_: unknown, record) => {
        if (record.price == null || record.add_price == null) {
          return <span style={{ color: '#bfbfbf', fontSize: 12 }}>--</span>;
        }
        const pct = ((record.price - record.add_price) / record.add_price) * 100;
        return (
          <span style={{
            ...numStyle,
            fontWeight: 600,
            fontSize: 13,
            color: getChangeColor(pct),
            background: getChangeBg(pct),
            padding: '2px 8px',
            borderRadius: 4,
          }}>
            {pct > 0 ? '+' : ''}{pct.toFixed(2)}%
          </span>
        );
      },
      sorter: (a, b) => {
        const pctA = (a.price != null && a.add_price != null) ? ((a.price - a.add_price) / a.add_price) : -999;
        const pctB = (b.price != null && b.add_price != null) ? ((b.price - b.add_price) / b.add_price) : -999;
        return pctA - pctB;
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 64,
      fixed: 'right',
      align: 'center',
      render: (_: unknown, record) => (
        <Popconfirm
          title={`确定将 ${record.name} 移出分组？`}
          onConfirm={() => handleRemoveStock(selectedGroupId!, record.code, record.name)}
        >
          <Button type="link" size="small" danger style={{ padding: 0, fontSize: 12 }}>
            移除
          </Button>
        </Popconfirm>
      ),
    },
  ];

  // -----------------------------------------------------------------------
  // Add stock modal
  // -----------------------------------------------------------------------

  const [addSearchOptions, setAddSearchOptions] = useState<any[]>([]);
  const [addSearchLoading, setAddSearchLoading] = useState(false);
  const [addSearchValue, setAddSearchValue] = useState('');
  const [selectedStock, setSelectedStock] = useState<{ code: string; name: string } | null>(null);
  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleAddStockSearch = useCallback((value: string) => {
    setAddSearchValue(value);
    setSelectedStock(null);
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);

    if (!value || value.length < 2) {
      setAddSearchOptions([]);
      return;
    }

    searchTimerRef.current = setTimeout(async () => {
      setAddSearchLoading(true);
      try {
        const res = await stockDataService.searchStocks(value, 10);
        const items = res.data?.items || [];
        setAddSearchOptions(
          items.map((item: any) => ({
            value: item.code,
            label: `${item.code}  ${item.name}${item.industry ? `  |  ${item.industry}` : ''}`,
            stockName: item.name,
          })),
        );
      } catch {
        setAddSearchOptions([]);
      } finally {
        setAddSearchLoading(false);
      }
    }, 1000);
  }, []);

  const handleConfirmAddStock = useCallback(async () => {
    if (!selectedGroupId || !selectedStock) return;
    await handleAddStock(selectedGroupId, selectedStock.code, selectedStock.name);
    setAddSearchValue('');
    setAddSearchOptions([]);
    setSelectedStock(null);
    await refreshQuotes();
  }, [selectedGroupId, selectedStock, handleAddStock, refreshQuotes]);

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------

  if (loading && groups.length === 0) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 'calc(100vh - 64px)', background: '#f5f7fa' }}>
        <Spin tip="加载自选股..." />
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 64px)', background: '#f5f7fa' }}>
      {/* ---- Left: Group navigation ---- */}
      <div style={{
        width: 220, background: '#fff', borderRight: '1px solid #e5edf5',
        display: 'flex', flexDirection: 'column', flexShrink: 0,
        boxShadow: 'rgba(23,23,23,0.06) 3px 0 6px',
      }}>
        <div style={{
          padding: '16px 16px', borderBottom: '1px solid #e5edf5',
          display: 'flex', alignItems: 'center', gap: 8,
        }}>
          <span style={{ fontWeight: 600, fontSize: 15, color: '#061b31' }}>自选分组</span>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: '8px 0' }}>
          {groups.map((group) => (
            <div
              key={group.id}
              onClick={() => setSelectedGroupId(group.id)}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '10px 16px', cursor: 'pointer',
                background: group.id === selectedGroupId ? '#f0f1ff' : 'transparent',
                borderLeft: group.id === selectedGroupId ? '3px solid #533afd' : '3px solid transparent',
                transition: 'all 0.15s',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1, minWidth: 0 }}>
                <span style={{
                  fontSize: 14, color: group.id === selectedGroupId ? '#533afd' : '#061b31',
                  fontWeight: group.id === selectedGroupId ? 500 : 400,
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}>
                  {group.name}
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexShrink: 0 }}>
                <Tag style={{ margin: 0, fontSize: 11, lineHeight: '16px', borderRadius: 4 }}>{group.stock_count}</Tag>
                {!group.is_default && (
                  <>
                    <EditOutlined
                      style={{ color: '#533afd', cursor: 'pointer', fontSize: 12 }}
                      onClick={(e) => {
                        e.stopPropagation();
                        setRenameModalOpen({ id: group.id, name: group.name });
                      }}
                    />
                    <Popconfirm
                      title={`确定删除分组"${group.name}"？组内股票将移入"观察股"`}
                      onConfirm={() => deleteGroup(group.id)}
                    >
                      <DeleteOutlined
                        style={{ color: '#ff4d4f', cursor: 'pointer', fontSize: 12, marginLeft: 4 }}
                        onClick={(e) => e.stopPropagation()}
                      />
                    </Popconfirm>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>

        <div style={{ padding: '12px 16px', borderTop: '1px solid #e5edf5' }}>
          <Button
            type="dashed" block icon={<PlusOutlined />}
            onClick={() => setCreateModalOpen(true)}
            style={{ borderRadius: 4 }}
          >
            新增分组
          </Button>
        </div>
      </div>

      {/* ---- Right: Stock table ---- */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* Header bar */}
        <div style={{
          padding: '12px 20px', background: '#fff', borderBottom: '1px solid #e5edf5',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          boxShadow: 'rgba(23,23,23,0.06) 0 3px 6px',
          position: 'relative', zIndex: 10,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <h3 style={{ margin: 0, fontSize: 16, color: '#061b31', fontWeight: 600 }}>
              {selectedGroup?.name ?? '自选股'}
            </h3>
            <span style={{ color: '#999', fontSize: 13 }}>
              共 {filteredStocks.length} 只
            </span>
            {!hasQuotes && stocks.length > 0 && (
              <Tag color="warning" style={{ fontSize: 11, borderRadius: 4 }}>暂无行情</Tag>
            )}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {lastRefreshTime && (
              <Tooltip title="行情刷新时间">
                <span style={{ color: '#999', fontSize: 12, display: 'flex', alignItems: 'center', gap: 4 }}>
                  <ClockCircleOutlined style={{ fontSize: 12 }} />
                  {formatRefreshTime(lastRefreshTime)}
                </span>
              </Tooltip>
            )}
            <Tooltip title="刷新行情">
              <Button
                type="text"
                icon={<ReloadOutlined spin={refreshing} />}
                onClick={handleManualRefresh}
                size="small"
                style={{ color: '#533afd' }}
              >
                刷新
              </Button>
            </Tooltip>
            <Input
              placeholder="搜索代码/名称"
              prefix={<SearchOutlined style={{ color: '#999' }} />}
              style={{ width: 200 }}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              allowClear
              size="small"
            />
            <Select
              size="small"
              style={{ width: 120 }}
              value={signalFilter}
              onChange={(v) => setSignalFilter(v)}
              options={[
                { value: 'all', label: '全部信号' },
                { value: 'has_buy', label: '有买点' },
                { value: 'has_sell', label: '有卖点' },
                { value: 'none', label: '无信号' },
              ]}
            />
          </div>
        </div>

        {/* Error alert */}
        {error && (
          <div style={{ padding: '8px 20px' }}>
            <Alert
              type="error" message={error} showIcon closable
              action={<a onClick={() => fetchGroups()}>重试</a>}
            />
          </div>
        )}

        {/* Table */}
        <div style={{ flex: 1, overflow: 'auto', padding: '12px 20px' }}>
          {pagedStocks.length === 0 ? (
            <Empty
              description={searchText ? '未找到匹配的股票' : '暂无股票'}
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            >
              {!searchText && (
                <Button type="primary" icon={<PlusOutlined />} onClick={() => setAddModalOpen(true)} style={{ borderRadius: 4 }}>
                  添加股票
                </Button>
              )}
            </Empty>
          ) : (
            <>
              <Table
                columns={columns}
                dataSource={pagedStocks}
                rowKey="code"
                size="middle"
                pagination={false}
                scroll={{ x: 1000 }}
                tableLayout="fixed"
                style={{ background: '#fff', borderRadius: 6, overflow: 'hidden' }}
                loading={refreshing}
                rowClassName={(_, index) =>
                  index % 2 === 0 ? '' : 'watchlist-row-alt'
                }
              />
              <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0',
              }}>
                <Button
                  type="dashed"
                  icon={<PlusOutlined />}
                  size="small"
                  onClick={() => setAddModalOpen(true)}
                  style={{ borderRadius: 4 }}
                >
                  添加股票
                </Button>
                <Pagination
                  current={page}
                  pageSize={pageSize}
                  total={total}
                  showSizeChanger
                  pageSizeOptions={['10', '20', '50', '100']}
                  showTotal={(t) => `共 ${t} 条`}
                  onChange={(p, ps) => { setPage(p); setPageSize(ps); }}
                />
              </div>
            </>
          )}
        </div>
      </div>

      {/* ---- Modals ---- */}
      <Modal
        title="新增分组" open={createModalOpen} onOk={handleCreate}
        onCancel={() => setCreateModalOpen(false)}
      >
        <Input
          placeholder="分组名称（最多10个字）" maxLength={10} value={newGroupName}
          onChange={(e) => setNewGroupName(e.target.value)}
          onPressEnter={handleCreate}
        />
      </Modal>

      <Modal
        title="重命名分组" open={!!renameModalOpen} onOk={handleRename}
        onCancel={() => setRenameModalOpen(null)}
      >
        <Input
          maxLength={10} value={renameModalOpen?.name || ''}
          onChange={(e) => setRenameModalOpen(renameModalOpen ? { ...renameModalOpen, name: e.target.value } : null)}
          onPressEnter={handleRename}
        />
      </Modal>

      <Modal
        title="添加股票" open={addModalOpen}
        onCancel={() => { setAddModalOpen(false); setAddSearchValue(''); setAddSearchOptions([]); setSelectedStock(null); if (searchTimerRef.current) clearTimeout(searchTimerRef.current); }}
        footer={
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
            <Button
              onClick={() => { setAddModalOpen(false); setAddSearchValue(''); setAddSearchOptions([]); setSelectedStock(null); }}
            >
              取消
            </Button>
            <Button
              type="primary"
              disabled={!selectedStock}
              loading={addSearchLoading}
              onClick={handleConfirmAddStock}
            >
              确认添加
            </Button>
          </div>
        }
      >
        <p style={{ color: '#64748d', fontSize: 13, marginBottom: 8 }}>
          搜索并添加股票到「{selectedGroup?.name}」
        </p>
        <Select
          value={selectedStock?.code}
          showSearch
          allowClear
          filterOption={false}
          onSearch={handleAddStockSearch}
          onChange={(_value: string, option: any) => {
            if (_value) {
              setSelectedStock({ code: _value, name: option?.stockName ?? '' });
            } else {
              setSelectedStock(null);
            }
          }}
          onClear={() => { setSelectedStock(null); setAddSearchOptions([]); setAddSearchValue(''); }}
          options={addSearchOptions}
          placeholder="输入股票代码或名称"
          style={{ width: '100%' }}
          size="large"
          loading={addSearchLoading}
          notFoundContent={addSearchLoading ? '搜索中...' : addSearchValue.length >= 2 ? '未找到匹配结果' : undefined}
        />
      </Modal>
    </div>
  );
};

export default WatchlistPage;
