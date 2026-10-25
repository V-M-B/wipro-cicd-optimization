import { useCallback, useEffect, useState } from 'react';

export type AsyncState<T> =
  | { status: 'loading'; data: undefined; error: undefined }
  | { status: 'success'; data: T; error: undefined }
  | { status: 'error'; data: undefined; error: unknown };

export interface AsyncResult<T> {
  state: AsyncState<T>;
  reload: () => void;
  /** Replace the loaded data locally (e.g. after a successful mutation). */
  setData: (data: T) => void;
}

/**
 * Run `load` on mount and whenever it changes identity (callers memoise it with useCallback).
 * Results of superseded runs are ignored and their AbortSignal is aborted.
 */
export function useAsync<T>(load: (signal: AbortSignal) => Promise<T>): AsyncResult<T> {
  const [state, setState] = useState<AsyncState<T>>({ status: 'loading', data: undefined, error: undefined });
  const [token, setToken] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setState({ status: 'loading', data: undefined, error: undefined });
    load(controller.signal).then(
      (data) => {
        if (active) setState({ status: 'success', data, error: undefined });
      },
      (error: unknown) => {
        if (active) setState({ status: 'error', data: undefined, error });
      },
    );
    return () => {
      active = false;
      controller.abort();
    };
  }, [load, token]);

  const reload = useCallback(() => setToken((t) => t + 1), []);
  const setData = useCallback((data: T) => setState({ status: 'success', data, error: undefined }), []);
  return { state, reload, setData };
}
