import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Button, Modal, Input, Popconfirm, Empty, Spin, Tag, Alert,
  Table, Pagination, message, Select,
} from 'antd';
import { PlusOutlined, DeleteOutlined, EditOutlined, SearchOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useWatchlistStore, type WatchlistStock } from '../store/watchlistStore';
import { stockDataService } from '../services/stockDataService';

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
  if (value === undefined || value === null) return '#999';
  return value >= 0 ? '#f5222d' : '#52c41a';
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const WatchlistPage: React.FC = () => {
  const navigate = useNavigate();
  const {
    groups, loading, error, fetchGroups, createGroup, renameGroup,
    deleteGroup, removeStock, addStock, loadQuotes,
  } = useWatchlistStore();

  // Selected group
  const [selectedGroupId, setSelectedGroupId] = useState<number | null>(null);

  // Pagination
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  // Modals
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [newGroupName, setNewGroupName] = useState('');
  const [renameModalOpen, setRenameModalOpen] = useState<{ id: number; name: string } | null>(null);

  // Search within group
  const [searchText, setSearchText] = useState('');

  // Add stock modal
  const [addModalOpen, setAddModalOpen] = useState(false);

  useEffect(() => {
    fetchGroups();
  }, []);

  // Auto-select first group when groups load
  useEffect(() => {
    if (groups.length > 0 && !selectedGroupId) {
      setSelectedGroupId(groups[0].id);
    }
  }, [groups]);

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

  // -----------------------------------------------------------------------
  // Derived data
  // -----------------------------------------------------------------------

  const selectedGroup = groups.find((g) => g.id === selectedGroupId) ?? null;
  const stocks = selectedGroup?.stocks ?? [];

  // Filter by search
  const filteredStocks = searchText
    ? stocks.filter(
        (s) =>
          s.code.includes(searchText) ||
          s.name.toLowerCase().includes(searchText.toLowerCase()),
      )
    : stocks;

  // Paginate
  const total = filteredStocks.length;
  const pagedStocks = filteredStocks.slice((page - 1) * pageSize, page * pageSize);

  // Reset page when group or search changes
  useEffect(() => {
    setPage(1);
  }, [selectedGroupId, searchText]);

  // -----------------------------------------------------------------------
  // Table columns
  // -----------------------------------------------------------------------

  const linkStyle = { color: '#533afd', textDecoration: 'none' };

  const columns: ColumnsType<WatchlistStock> = [
    {
      title: '序号',
      key: 'index',
      width: 60,
      align: 'center',
      render: (_: unknown, _record: WatchlistStock, index: number) => (
        <span style={{ color: '#999' }}>{(page - 1) * pageSize + index + 1}</span>
      ),
    },
    {
      title: '代码',
      dataIndex: 'code',
      key: 'code',
      width: 90,
      fixed: 'left',
      align: 'center',
      render: (code: string) => (
        <a onClick={() => navigate(`/market/stock/${code}`)} style={linkStyle}>
          <span style={{ fontFamily: 'monospace', fontWeight: 500 }}>{code}</span>
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
      width: 90,
      align: 'center',
      render: (v: number | undefined) => (
        <span style={{ fontFamily: 'monospace', fontVariantNumeric: 'tabular-nums' }}>
          {formatNumber(v)}
        </span>
      ),
    },
    {
      title: '涨跌幅',
      dataIndex: 'change_pct',
      key: 'change_pct',
      width: 90,
      align: 'center',
      render: (v: number | undefined) => (
        <span
          style={{
            fontFamily: 'monospace',
            fontVariantNumeric: 'tabular-nums',
            color: getChangeColor(v),
            fontWeight: 500,
          }}
        >
          {v === undefined || v === null ? '--' : `${v > 0 ? '+' : ''}${v.toFixed(2)}%`}
        </span>
      ),
    },
    {
      title: '涨跌额',
      dataIndex: 'change_amount',
      key: 'change_amount',
      width: 90,
      align: 'center',
      render: (v: number | undefined) => (
        <span
          style={{
            fontFamily: 'monospace',
            fontVariantNumeric: 'tabular-nums',
            color: getChangeColor(v),
          }}
        >
          {v === undefined || v === null ? '--' : `${v > 0 ? '+' : ''}${v.toFixed(2)}`}
        </span>
      ),
    },
    {
      title: '所属行业',
      dataIndex: 'industry',
      key: 'industry',
      width: 100,
      align: 'center',
      render: (v: string | undefined) => (v ? <Tag>{v}</Tag> : <span style={{ color: '#999' }}>--</span>),
    },
    {
      title: '自选日',
      dataIndex: 'add_time',
      key: 'add_time',
      width: 110,
      align: 'center',
      render: (v: string | undefined) => (
        <span style={{ color: '#64748d', fontSize: 12 }}>{formatDate(v)}</span>
      ),
    },
    {
      title: '自选价',
      dataIndex: 'add_price',
      key: 'add_price',
      width: 90,
      align: 'center',
      render: (v: number | undefined) => (
        <span style={{ fontFamily: 'monospace', fontVariantNumeric: 'tabular-nums', color: '#64748d' }}>
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
        if (record.price == null || record.add_price == null) return '--';
        const pct = ((record.price - record.add_price) / record.add_price) * 100;
        return (
          <span
            style={{
              fontFamily: 'monospace',
              fontVariantNumeric: 'tabular-nums',
              color: getChangeColor(pct),
              fontWeight: 500,
            }}
          >
            {pct > 0 ? '+' : ''}{pct.toFixed(2)}%
          </span>
        );
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 80,
      fixed: 'right',
      align: 'center',
      render: (_: unknown, record) => (
        <Popconfirm
          title={`确定将 ${record.name} 移出分组？`}
          onConfirm={() => handleRemoveStock(selectedGroupId!, record.code, record.name)}
        >
          <Button type="link" size="small" danger style={{ padding: 0 }}>
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
    await loadQuotes();
  }, [selectedGroupId, selectedStock, handleAddStock, loadQuotes]);

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------

  if (loading && groups.length === 0) {
    return <div style={{ textAlign: 'center', padding: 80 }}><Spin tip="加载自选股..." /></div>;
  }

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 64px)', background: '#f5f7fa' }}>
      {/* ---- Left: Group navigation ---- */}
      <div style={{
        width: 220, background: '#fff', borderRight: '1px solid #e5edf5',
        display: 'flex', flexDirection: 'column', flexShrink: 0,
      }}>
        <div style={{
          padding: '16px 12px', borderBottom: '1px solid #e5edf5',
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
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}>
                  {group.name}
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexShrink: 0 }}>
                <Tag style={{ margin: 0, fontSize: 11, lineHeight: '16px' }}>{group.stock_count}</Tag>
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

        {/* Add group button at bottom */}
        <div style={{
          padding: '12px 16px', borderTop: '1px solid #e5edf5',
        }}>
          <Button
            type="dashed" block icon={<PlusOutlined />}
            onClick={() => setCreateModalOpen(true)}
          >
            新增分组
          </Button>
        </div>
      </div>

      {/* ---- Right: Stock table ---- */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* Header */}
        <div style={{
          padding: '12px 20px', background: '#fff', borderBottom: '1px solid #e5edf5',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <h3 style={{ margin: 0, fontSize: 16, color: '#061b31' }}>
              {selectedGroup?.name ?? '自选股'}
            </h3>
            <span style={{ color: '#999', fontSize: 13 }}>
              共 {filteredStocks.length} 只股票
            </span>
          </div>

          <Input
            placeholder="搜索代码/名称"
            prefix={<SearchOutlined style={{ color: '#999' }} />}
            style={{ width: 220 }}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            allowClear
            size="small"
          />
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
                <Button type="primary" icon={<PlusOutlined />} onClick={() => setAddModalOpen(true)}>
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
                size="small"
                pagination={false}
                scroll={{ x: 900 }}
                tableLayout="fixed"
              />
              <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0',
              }}>
                <Button type="dashed" icon={<PlusOutlined />} size="small" onClick={() => setAddModalOpen(true)}>
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
