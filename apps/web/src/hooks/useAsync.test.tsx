import { act, renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { useAsync } from './useAsync';

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

describe('useAsync', () => {
  it('starts loading and resolves to success', async () => {
    const load = vi.fn(async () => 42);
    const { result } = renderHook(() => useAsync(load));
    expect(result.current.state.status).toBe('loading');
    await waitFor(() => expect(result.current.state).toEqual({ status: 'success', data: 42, error: undefined }));
  });

  it('captures rejections as errors', async () => {
    const failure = new Error('nope');
    const load = async () => Promise.reject(failure);
    const { result } = renderHook(() => useAsync(load));
    await waitFor(() => expect(result.current.state.status).toBe('error'));
    expect(result.current.state.error).toBe(failure);
  });

  it('reload runs the loader again', async () => {
    const load = vi.fn(async () => 'x');
    const { result } = renderHook(() => useAsync(load));
    await waitFor(() => expect(result.current.state.status).toBe('success'));
    act(() => result.current.reload());
    await waitFor(() => expect(load).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(result.current.state.status).toBe('success'));
  });

  it('setData replaces the loaded value', async () => {
    const load = async () => 1;
    const { result } = renderHook(() => useAsync(load));
    await waitFor(() => expect(result.current.state.status).toBe('success'));
    act(() => result.current.setData(2));
    expect(result.current.state.data).toBe(2);
  });

  it('ignores results from a superseded loader and aborts it', async () => {
    const first = deferred<string>();
    const second = deferred<string>();
    const signals: AbortSignal[] = [];
    const loaders = [first, second].map((d) => (signal: AbortSignal) => {
      signals.push(signal);
      return d.promise;
    });
    const { result, rerender } = renderHook(({ load }) => useAsync(load), { initialProps: { load: loaders[0]! } });
    rerender({ load: loaders[1]! });
    expect(signals[0]?.aborted).toBe(true);
    await act(async () => {
      second.resolve('second');
      first.resolve('first');
    });
    expect(result.current.state.data).toBe('second');
  });

  it('aborts the in-flight request on unmount', () => {
    let captured: AbortSignal | undefined;
    const load = (signal: AbortSignal) => {
      captured = signal;
      return new Promise<never>(() => undefined);
    };
    const { unmount } = renderHook(() => useAsync(load));
    unmount();
    expect(captured?.aborted).toBe(true);
  });
});
