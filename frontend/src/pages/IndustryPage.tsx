import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout, Menu, Table, Card, Spin, Statistic, Alert } from 'antd';
import { useIndustryStore } from '../store/industryStore';

const { Sider, Content } = Layout;

const IndustryPage: React.FC = () => {
  const navigate = useNavigate();
  const {
    industries, selectedIndustry, selectedIndustryName, avgChangePct,
    comparisonData, total, loading, tableLoading, error, tableError,
    fetchIndustries, selectIndustry,
  } = useIndustryStore();

  useEffect(() => {
    fetchIndustries();
  }, []);

  const columns = [
    {
      title: '股票名称/代码',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: any) => (
        <a onClick={() => navigate(`/market/stock/${record.code}`)}>
          {name} <span style={{ color: '#999', fontSize: 12 }}>{record.code}</span>
        </a>
      ),
    },
    {
      title: '涨跌幅',
      dataIndex: 'change_pct',
      key: 'change_pct',
      sorter: (a: any, b: any) => (a.change_pct || 0) - (b.change_pct || 0),
      render: (v: number) => {
        if (v === null || v === undefined) return '--';
        const color = v >= 0 ? '#f5222d' : '#52c41a';
        return <span style={{ color }}>{v > 0 ? '+' : ''}{v.toFixed(2)}%</span>;
      },
    },
    { title: 'PE', dataIndex: 'pe_ttm', key: 'pe_ttm', sorter: true, render: (v: number) => v?.toFixed(2) ?? '--' },
    { title: 'PB', dataIndex: 'pb', key: 'pb', sorter: true, render: (v: number) => v?.toFixed(2) ?? '--' },
    {
      title: '营收(亿)',
      dataIndex: 'revenue',
      key: 'revenue',
      sorter: true,
      render: (v: number) => v !== null && v !== undefined ? (v / 100000000).toFixed(2) : '--',
    },
    {
      title: '净利润(亿)',
      dataIndex: 'net_profit',
      key: 'net_profit',
      sorter: true,
      render: (v: number) => v !== null && v !== undefined ? (v / 100000000).toFixed(2) : '--',
    },
    {
      title: '净利润增长率',
      dataIndex: 'profit_growth_pct',
      key: 'profit_growth_pct',
      sorter: true,
      render: (v: number) => {
        if (v === null || v === undefined) return '--';
        const color = v >= 0 ? '#f5222d' : '#52c41a';
        return <span style={{ color }}>{v > 0 ? '+' : ''}{v.toFixed(2)}%</span>;
      },
    },
  ];

  const menuItems = industries.map((ind) => ({
    key: ind.code,
    label: ind.name,
  }));

  return (
    <div style={{ padding: 16 }}>
      <h2 style={{ marginBottom: 16 }}>行业对比</h2>
      <Layout style={{ background: 'transparent' }}>
        <Sider width={200} style={{ background: '#fff', borderRadius: 8, marginRight: 16 }}>
          {error ? (
            <Alert
              type="error"
              message={error}
              showIcon
              style={{ margin: 12 }}
              action={<a onClick={() => fetchIndustries()}>重试</a>}
            />
          ) : (
            <Spin spinning={loading}>
              <Menu
                mode="inline"
                selectedKeys={selectedIndustry ? [selectedIndustry] : []}
                items={menuItems}
                onClick={({ key }) => {
                  const ind = industries.find((i) => i.code === key);
                  selectIndustry(key, ind?.name || '');
                }}
                style={{ border: 'none' }}
              />
            </Spin>
          )}
        </Sider>
        <Content>
          {selectedIndustry ? (
            <>
              {tableError && (
                <Alert
                  type="error"
                  message={tableError}
                  showIcon
                  closable
                  style={{ marginBottom: 12 }}
                  action={<a onClick={() => selectIndustry(selectedIndustry, selectedIndustryName)}>重试</a>}
                />
              )}
              <Card size="small" style={{ marginBottom: 12 }}>
                <Statistic
                  title={`${selectedIndustryName} · 行业均涨幅`}
                  value={avgChangePct}
                  precision={2}
                  suffix="%"
                  valueStyle={{ color: avgChangePct >= 0 ? '#f5222d' : '#52c41a', fontSize: 20 }}
                />
              </Card>
              <Card size="small">
                <Table
                  columns={columns}
                  dataSource={comparisonData}
                  rowKey="code"
                  loading={tableLoading}
                  pagination={{ pageSize: 20, total }}
                  size="small"
                />
              </Card>
            </>
          ) : (
            <Card style={{ textAlign: 'center', padding: 80, color: '#999' }}>
              请从左侧选择一个行业
            </Card>
          )}
        </Content>
      </Layout>
    </div>
  );
};

export default IndustryPage;
