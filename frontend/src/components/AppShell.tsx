import React from 'react';
import { Layout, Menu } from 'antd';
import { Link, useLocation } from 'react-router-dom';
import {
  DashboardOutlined,
  MessageOutlined,
  LaptopOutlined,
  ExperimentOutlined,
  ScanOutlined,
  CompassOutlined,
  ToolOutlined,
  HistoryOutlined,
  SettingOutlined,
} from '@ant-design/icons';

const { Sider, Content, Footer } = Layout;

const menuItems = [
  { key: '/dashboard', icon: <DashboardOutlined />, label: 'Dashboard' },
  { key: '/messages', icon: <MessageOutlined />, label: 'Messages' },
  { key: '/lab', icon: <LaptopOutlined />, label: 'Lab' },
  { key: '/bench', icon: <ExperimentOutlined />, label: 'StegoBench' },
  { key: '/analysis', icon: <ScanOutlined />, label: 'Steganalysis' },
  { key: '/recommender', icon: <CompassOutlined />, label: 'Recommender' },
  { key: '/hash-tool', icon: <ToolOutlined />, label: 'Hash Tool' },
  { key: '/history', icon: <HistoryOutlined />, label: 'History' },
  { key: '/settings', icon: <SettingOutlined />, label: 'Settings' },
];

export const AppShell: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const location = useLocation();
  const selectedKey = menuItems.find(item => location.pathname.startsWith(item.key))?.key;
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider breakpoint="lg" collapsedWidth="0">
        <div style={{ height: 32, margin: 16, color: 'white', fontWeight: 'bold' }}>StegChat</div>
        <Menu theme="dark" mode="inline" selectedKeys={[selectedKey || '/dashboard']} items={menuItems.map(item => ({
          key: item.key,
          icon: item.icon,
          label: <Link to={item.key}>{item.label}</Link>,
        }))} />
      </Sider>
      <Layout>
        <Content style={{ margin: '24px 16px 0' }}>
          {children}
        </Content>
        <Footer style={{ textAlign: 'center' }}>Academic prototype</Footer>
      </Layout>
    </Layout>
  );
};
