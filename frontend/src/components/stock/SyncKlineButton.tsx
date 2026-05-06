import React, { useState } from 'react';
import { Button, message, Tooltip } from 'antd';
import { SyncOutlined } from '@ant-design/icons';

interface SyncKlineButtonProps {
  code: string;
  period: 'daily' | 'weekly' | 'monthly';
  onSuccess?: () => void;
}

const SyncKlineButton: React.FC<SyncKlineButtonProps> = ({ code, period, onSuccess }) => {
  const [syncing, setSyncing] = useState(false);

  const getDateRange = (p: string): { startDate: string; endDate: string } => {
    const now = new Date();
    const endDate = now.toISOString().split('T')[0];
    let startDate: string;

    if (p === 'weekly') {
      // 近3年
      const d = new Date(now);
      d.setFullYear(d.getFullYear() - 3);
      startDate = d.toISOString().split('T')[0];
    } else if (p === 'monthly') {
      // 近5年
      const d = new Date(now);
      d.setFullYear(d.getFullYear() - 5);
      startDate = d.toISOString().split('T')[0];
    } else {
      // 日K: 近1年
      const d = new Date(now);
      d.setFullYear(d.getFullYear() - 1);
      startDate = d.toISOString().split('T')[0];
    }

    return { startDate, endDate };
  };

  const handleSync = async () => {
    if (syncing) return;
    setSyncing(true);

    try {
      const { startDate, endDate } = getDateRange(period);
      const params = new URLSearchParams({
        source_type: 'akshare',
        data_type: 'daily_quote',
        symbol: code,
        start_date: startDate,
        end_date: endDate,
        period: period,
      });

      const url = `/api/v1/sync/execute?${params.toString()}`;

      // 使用 EventSource 解析 SSE
      await new Promise<void>((resolve, reject) => {
        const evtSource = new EventSource(url);

        evtSource.addEventListener('sync_completed', () => {
          evtSource.close();
          resolve();
        });

        evtSource.addEventListener('sync_failed', (e) => {
          evtSource.close();
          reject(new Error(e.data || '同步失败'));
        });

        evtSource.addEventListener('sync_error', (e) => {
          evtSource.close();
          reject(new Error(e.data || '同步错误'));
        });

        evtSource.onerror = () => {
          evtSource.close();
          reject(new Error('同步连接中断'));
        };

        // 超时保护: 60秒
        setTimeout(() => {
          evtSource.close();
          reject(new Error('同步超时'));
        }, 60000);
      });

      message.success('K线数据同步成功');
      onSuccess?.();
    } catch (err: any) {
      // 解析SSE data中的错误信息
      let errMsg = '同步失败';
      try {
        const parsed = JSON.parse(err.message);
        errMsg = parsed.message || errMsg;
      } catch {
        errMsg = err.message || errMsg;
      }
      message.error(errMsg);
    } finally {
      setSyncing(false);
    }
  };

  const periodLabel = period === 'daily' ? '日K' : period === 'weekly' ? '周K' : '月K';

  return (
    <Tooltip title={`同步${periodLabel}数据`}>
      <Button
        type="text"
        size="small"
        icon={<SyncOutlined spin={syncing} />}
        onClick={handleSync}
        loading={syncing}
      >
        同步
      </Button>
    </Tooltip>
  );
};

export default SyncKlineButton;
