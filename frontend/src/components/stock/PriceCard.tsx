import React from 'react';
import { Card, Row, Col, Statistic, Skeleton } from 'antd';

interface PriceCardProps {
  name: string;
  code: string;
  price: number | null;
  changeAmount: number | null;
  changePct: number | null;
  volume: number | null;
  amount: number | null;
}

const PriceCard: React.FC<PriceCardProps> = ({
  name, code, price, changeAmount, changePct, volume, amount,
}) => {
  const isLoading = price === null || price === undefined;

  if (isLoading) {
    return (
      <Card size="small" style={{ marginBottom: 12 }}>
        <Row gutter={16} align="middle">
          <Col>
            <Skeleton.Input active size="small" style={{ width: 120 }} />
            <Skeleton.Input active size="small" style={{ width: 80, marginTop: 4 }} />
          </Col>
          <Col>
            <Skeleton.Input active size="default" style={{ width: 100 }} />
          </Col>
          <Col>
            <Skeleton.Input active size="small" style={{ width: 80 }} />
            <Skeleton.Input active size="small" style={{ width: 80, marginTop: 4 }} />
          </Col>
          <Col flex="auto" />
          <Col>
            <Skeleton.Input active size="small" style={{ width: 80 }} />
          </Col>
          <Col>
            <Skeleton.Input active size="small" style={{ width: 80 }} />
          </Col>
        </Row>
      </Card>
    );
  }

  const isUp = (changePct ?? 0) > 0;
  const isDown = (changePct ?? 0) < 0;
  const color = isUp ? '#f5222d' : isDown ? '#52c41a' : '#666';

  return (
    <Card size="small" style={{ marginBottom: 12 }}>
      <Row gutter={16} align="middle">
        <Col>
          <div style={{ fontSize: 18, fontWeight: 600 }}>{name}</div>
          <div style={{ fontSize: 12, color: '#999' }}>{code}</div>
        </Col>
        <Col>
          <span style={{ fontSize: 28, fontWeight: 700, color }}>
            {price?.toFixed(2) ?? '--'}
          </span>
        </Col>
        <Col>
          <div style={{ color, fontSize: 14 }}>
            {changeAmount !== null ? `${changeAmount > 0 ? '+' : ''}${changeAmount.toFixed(2)}` : '--'}
          </div>
          <div style={{ color, fontSize: 14 }}>
            {changePct !== null ? `${changePct > 0 ? '+' : ''}${changePct.toFixed(2)}%` : '--'}
          </div>
        </Col>
        <Col flex="auto" />
        <Col>
          <Statistic title="成交量" value={formatVol(volume)} valueStyle={{ fontSize: 13 }} />
        </Col>
        <Col>
          <Statistic title="成交额" value={formatAmt(amount)} valueStyle={{ fontSize: 13 }} />
        </Col>
      </Row>
    </Card>
  );
};

function formatVol(v: number | null | undefined): string {
  if (!v) return '--';
  if (v >= 10000) return (v / 10000).toFixed(0) + '万';
  return v.toFixed(0);
}

function formatAmt(v: number | null | undefined): string {
  if (!v) return '--';
  if (v >= 100000000) return (v / 100000000).toFixed(2) + '亿';
  if (v >= 10000) return (v / 10000).toFixed(2) + '万';
  return v.toFixed(2);
}

export default PriceCard;
