import React, { useState } from 'react';
import { Button, Modal, List, Tag, message } from 'antd';
import { StarOutlined } from '@ant-design/icons';
import { useWatchlistStore } from '../../store/watchlistStore';

interface AddToWatchlistButtonProps {
  stockCode: string;
  stockName: string;
}

const AddToWatchlistButton: React.FC<AddToWatchlistButtonProps> = ({ stockCode, stockName }) => {
  const [open, setOpen] = useState(false);
  const { groups, fetchGroups, addStock } = useWatchlistStore();
  const [loading, setLoading] = useState(false);

  const handleOpen = async () => {
    await fetchGroups();
    setOpen(true);
  };

  const handleAdd = async (groupId: number) => {
    setLoading(true);
    try {
      await addStock(groupId, stockCode, stockName);
      message.success('已添加到自选股');
      setOpen(false);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '添加失败');
    } finally {
      setLoading(false);
    }
  };

  // 判断该股票是否已在某个分组中
  const getExistingGroupIds = (): Set<number> => {
    const ids = new Set<number>();
    groups.forEach((g) => {
      g.stocks?.forEach((s) => {
        if (s.code === stockCode) ids.add(g.id);
      });
    });
    return ids;
  };

  const existingGroupIds = getExistingGroupIds();

  return (
    <>
      <Button icon={<StarOutlined />} size="small" type="text" onClick={handleOpen}
        style={{ fontSize: 12, color: '#94a3b8', padding: '0 4px', height: 20 }}
      >
        加入自选
      </Button>
      <Modal
        title="选择分组"
        open={open}
        onCancel={() => setOpen(false)}
        footer={null}
        width={320}
      >
        <List
          loading={loading}
          dataSource={groups}
          renderItem={(group) => {
            const exists = existingGroupIds.has(group.id);
            return (
              <List.Item
                style={{
                  cursor: exists ? 'default' : 'pointer',
                  padding: '8px 12px',
                  opacity: exists ? 0.5 : 1,
                }}
                onClick={() => !exists && handleAdd(group.id)}
              >
                <span>{group.name}</span>
                {exists && <Tag color="default">已添加</Tag>}
                <span style={{ color: '#999', fontSize: 12 }}>
                  ({group.stock_count}只)
                </span>
              </List.Item>
            );
          }}
        />
      </Modal>
    </>
  );
};

export default AddToWatchlistButton;
