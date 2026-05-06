import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Collapse, Button, Modal, Input, Popconfirm, Empty, Spin, Tag, Alert } from 'antd';
import { PlusOutlined, DeleteOutlined, EditOutlined } from '@ant-design/icons';
import { useWatchlistStore } from '../store/watchlistStore';

const WatchlistPage: React.FC = () => {
  const navigate = useNavigate();
  const { groups, loading, error, fetchGroups, createGroup, renameGroup, deleteGroup, removeStock } = useWatchlistStore();
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [newGroupName, setNewGroupName] = useState('');
  const [renameModalOpen, setRenameModalOpen] = useState<{ id: number; name: string } | null>(null);

  useEffect(() => {
    fetchGroups();
  }, []);

  const handleCreate = async () => {
    if (!newGroupName.trim()) return;
    await createGroup(newGroupName.trim());
    setNewGroupName('');
    setCreateModalOpen(false);
  };

  const handleRename = async () => {
    if (!renameModalOpen || !renameModalOpen.name.trim()) return;
    await renameGroup(renameModalOpen.id, renameModalOpen.name.trim());
    setRenameModalOpen(null);
  };

  const handleChangePct = (v: number | undefined) => {
    if (v === undefined || v === null) return <span style={{ color: '#999' }}>--</span>;
    const color = v >= 0 ? '#f5222d' : '#52c41a';
    return <span style={{ color }}>{v > 0 ? '+' : ''}{v.toFixed(2)}%</span>;
  };

  if (loading && groups.length === 0) {
    return <div style={{ textAlign: 'center', padding: 80 }}><Spin tip="加载自选股..." /></div>;
  }

  const collapseItems = groups.map((group) => ({
    key: group.id.toString(),
    label: (
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span>{group.name}</span>
        <Tag>{group.stock_count}只</Tag>
        {!group.is_default && (
          <span>
            <EditOutlined
              style={{ color: '#533afd', cursor: 'pointer' }}
              onClick={(e) => { e.stopPropagation(); setRenameModalOpen({ id: group.id, name: group.name }); }}
            />
            <Popconfirm
              title={`确定删除分组"${group.name}"？组内股票将移入"观察股"`}
              onConfirm={() => deleteGroup(group.id)}
            >
              <DeleteOutlined style={{ color: '#ff4d4f', cursor: 'pointer', marginLeft: 8 }} onClick={(e) => e.stopPropagation()} />
            </Popconfirm>
          </span>
        )}
      </div>
    ),
    children: group.stocks && group.stocks.length > 0 ? (
      <div>
        {group.stocks.map((stock) => (
          <div
            key={stock.code}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '6px 8px', borderBottom: '1px solid #f0f0f0', cursor: 'pointer',
            }}
            onClick={() => navigate(`/market/stock/${stock.code}`)}
          >
            <div>
              <strong>{stock.name}</strong>
              <span style={{ color: '#999', marginLeft: 8, fontSize: 12 }}>{stock.code}</span>
              {stock.industry && <Tag style={{ marginLeft: 8 }}>{stock.industry}</Tag>}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span>{stock.price?.toFixed(2) ?? '--'}</span>
              {handleChangePct(stock.change_pct)}
              <Button
                type="text"
                size="small"
                danger
                onClick={(e) => { e.stopPropagation(); removeStock(group.id, stock.code); }}
              >
                移除
              </Button>
            </div>
          </div>
        ))}
      </div>
    ) : (
      <Empty description="暂无股票" image={Empty.PRESENTED_IMAGE_SIMPLE} />
    ),
  }));

  return (
    <div style={{ padding: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>自选股管理</h2>
        <Button icon={<PlusOutlined />} type="primary" onClick={() => setCreateModalOpen(true)}>
          新增分组
        </Button>
      </div>

      {error && (
        <Alert
          type="error"
          message={error}
          showIcon
          closable
          style={{ marginBottom: 16 }}
          action={<a onClick={() => fetchGroups()}>重试</a>}
        />
      )}

      {groups.length === 0 ? (
        <Empty description="暂无自选股分组" />
      ) : (
        <Collapse items={collapseItems} defaultActiveKey={groups.map((g) => g.id.toString())} />
      )}

      <Modal
        title="新增分组"
        open={createModalOpen}
        onOk={handleCreate}
        onCancel={() => setCreateModalOpen(false)}
      >
        <Input
          placeholder="分组名称（最多10个字）"
          maxLength={10}
          value={newGroupName}
          onChange={(e) => setNewGroupName(e.target.value)}
        />
      </Modal>

      <Modal
        title="重命名分组"
        open={!!renameModalOpen}
        onOk={handleRename}
        onCancel={() => setRenameModalOpen(null)}
      >
        <Input
          maxLength={10}
          value={renameModalOpen?.name || ''}
          onChange={(e) => setRenameModalOpen(renameModalOpen ? { ...renameModalOpen, name: e.target.value } : null)}
        />
      </Modal>
    </div>
  );
};

export default WatchlistPage;
