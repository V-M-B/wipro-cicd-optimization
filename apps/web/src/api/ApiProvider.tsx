import type { ReactNode } from 'react';
import type { RetailApi } from '../lib/api';
import { ApiContext } from './context';

export function ApiProvider({ api, children }: { api: RetailApi; children: ReactNode }) {
  return <ApiContext.Provider value={api}>{children}</ApiContext.Provider>;
}
