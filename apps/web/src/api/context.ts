import { createContext, useContext } from 'react';
import type { RetailApi } from '../lib/api';

export const ApiContext = createContext<RetailApi | null>(null);

export function useApi(): RetailApi {
  const api = useContext(ApiContext);
  if (!api) {
    throw new Error('useApi must be used inside <ApiProvider>');
  }
  return api;
}
