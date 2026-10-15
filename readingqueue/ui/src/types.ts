export interface Item {
  id: number;
  owner: string;
  title: string;
  url: string;
  status: 'unread' | 'reading' | 'done';
  createdAt?: string;
  tags?: string[];
}

export type Dialect = 'postgres' | 'sqlserver';

export interface TransactionStep {
  id: string;
  step: number;
  description: string;
  sql: string;
  dialect: Dialect;
  status: 'pending' | 'success' | 'failed' | 'rolled_back';
  durationMs: number;
  detail?: string;
}

export interface TransactionResult {
  success: boolean;
  item: Item | null;
  steps: TransactionStep[];
  rolledBack: boolean;
  error?: string;
}

export interface VerificationTest {
  id: string;
  suite: 'DbTest' | 'ApiTest';
  name: string;
  description: string;
  status: 'pass' | 'fail' | 'unrun';
  durationMs: number;
  assertion: string;
}
