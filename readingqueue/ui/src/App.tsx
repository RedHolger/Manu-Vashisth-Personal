import { useEffect, useState } from 'react';
import type { JSX } from 'react';
import { Navbar } from './components/Navbar';
import { QueueDashboard } from './components/QueueDashboard';
import { TransactionVisualizer } from './components/TransactionVisualizer';
import { SqlStudio } from './components/SqlStudio';
import { TestHub } from './components/TestHub';
import { TransferModal } from './components/TransferModal';
import { api, setUser, getUser, setDialect, getDialect } from './api';
import type { Item, Dialect } from './types';
import { AlertCircle, X } from 'lucide-react';
import './styles/theme.css';

export default function App(): JSX.Element {
  const [currentUser, setCurrentUserState] = useState<string>(getUser());
  const [currentDialect, setCurrentDialectState] = useState<Dialect>(getDialect());
  const [items, setItems] = useState<Item[]>([]);
  const [activeTab, setActiveTab] = useState<'queue' | 'transactions' | 'sql' | 'tests'>('queue');
  const [isLiveBackend, setIsLiveBackend] = useState<boolean>(false);
  const [securityMessage, setSecurityMessage] = useState<string | null>(null);
  const [transferringItem, setTransferringItem] = useState<Item | null>(null);

  const loadData = async (): Promise<void> => {
    try {
      const res = await api.list('', 1, 50);
      setItems(res.items);
      const isOnline = await api.checkHealth();
      setIsLiveBackend(isOnline);
    } catch (e: any) {
      console.warn('Load failed:', e);
    }
  };

  useEffect(() => {
    setUser(currentUser);
    loadData();
  }, [currentUser]);

  const handleSelectDialect = (d: Dialect) => {
    setCurrentDialectState(d);
    setDialect(d);
  };

  const handleSelectUser = (u: string) => {
    setCurrentUserState(u);
    setUser(u);
    setSecurityMessage(null);
  };

  const handleUpdateStatus = async (id: number, status: 'unread' | 'reading' | 'done') => {
    try {
      await api.setStatus(id, status);
      await loadData();
    } catch (err: any) {
      setSecurityMessage(err.message);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await api.remove(id);
      await loadData();
    } catch (err: any) {
      setSecurityMessage(err.message);
    }
  };

  const handleAddItem = async (title: string, url: string, tags: string[]) => {
    try {
      await api.add(title, url, tags);
      await loadData();
    } catch (err: any) {
      setSecurityMessage(err.message);
    }
  };

  const handleExecuteTransfer = async (id: number, targetUser: string, injectFault: boolean) => {
    try {
      const res = await api.transfer(id, targetUser, injectFault);
      if (res.rolledBack) {
        setSecurityMessage(
          `Notice: Rollback Hook Verified. Forced failure caused full rollback. Item remains owned by '${res.item?.owner}'.`
        );
      }
      await loadData();
    } catch (err: any) {
      setSecurityMessage(err.message);
    }
  };

  return (
    <div style={{ position: 'relative', minHeight: '100vh', overflowX: 'hidden' }}>
      <div className="top-glow" />

      <div className="app-container">
        <Navbar
          currentDialect={currentDialect}
          onSelectDialect={handleSelectDialect}
          currentUser={currentUser}
          onSelectUser={handleSelectUser}
          activeTab={activeTab}
          onSelectTab={setActiveTab}
          isLiveBackend={isLiveBackend}
          itemCount={items.length}
        />

        {/* Security / Error Toast Banner */}
        {securityMessage && (
          <div className="security-toast">
            <AlertCircle size={18} style={{ color: 'var(--accent-rose)', flexShrink: 0, marginTop: 2 }} />
            <div style={{ flex: 1 }}>{securityMessage}</div>
            <button
              onClick={() => setSecurityMessage(null)}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer',
              }}
            >
              <X size={16} />
            </button>
          </div>
        )}

        {/* Tab Views */}
        <main>
          {activeTab === 'queue' && (
            <QueueDashboard
              items={items}
              currentUser={currentUser}
              onUpdateStatus={handleUpdateStatus}
              onDelete={handleDelete}
              onStartTransfer={(item) => setTransferringItem(item)}
              onAddItem={handleAddItem}
              onSecurityAlert={(msg) => setSecurityMessage(msg)}
            />
          )}

          {activeTab === 'transactions' && (
            <TransactionVisualizer
              items={items}
              currentUser={currentUser}
              currentDialect={currentDialect}
              onRefresh={loadData}
            />
          )}

          {activeTab === 'sql' && <SqlStudio />}

          {activeTab === 'tests' && <TestHub />}
        </main>

        {/* Transfer Modal */}
        {transferringItem && (
          <TransferModal
            item={transferringItem}
            currentUser={currentUser}
            onClose={() => setTransferringItem(null)}
            onExecute={handleExecuteTransfer}
          />
        )}
      </div>
    </div>
  );
}
