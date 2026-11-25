import { describe, expect, it, vi } from 'vitest';
import { formatLatency, formatNumber, formatRelativeTime, parseNdjson } from '../lib/utils';

function response(text: string): Response {
  return { text: async () => text } as Response;
}

describe('dashboard formatting', () => {
  it('distinguishes missing and zero values', () => {
    expect(formatNumber(null)).toBe('—');
    expect(formatNumber(0)).toBe('0');
    expect(formatLatency(0)).toBe('0ms');
    expect(formatLatency(null)).toBe('—');
  });

  it('formats compact large counts', () => {
    expect(formatNumber(1200)).toBe('1.2K');
    expect(formatNumber(1500000)).toBe('1.5M');
  });

  it('formats elapsed time with a fixed clock', () => {
    const spy = vi.spyOn(Date, 'now').mockReturnValue(Date.parse('2026-01-01T12:00:00Z'));
    try {
      expect(formatRelativeTime('2026-01-01T11:58:00Z')).toBe('2m ago');
    } finally {
      spy.mockRestore();
    }
  });
});

describe('query result NDJSON', () => {
  it('preserves rows and skips blank lines', async () => {
    expect(await parseNdjson(response('{"id":1}\n\n{"id":2}\n'))).toEqual([{ id: 1 }, { id: 2 }]);
  });

  it('rejects backend error frames instead of treating them as rows', async () => {
    await expect(parseNdjson(response('{"id":1}\n{"error":"query failed"}\n'))).rejects.toThrow('query failed');
  });

  it('rejects malformed JSON', async () => {
    await expect(parseNdjson(response('not-json\n'))).rejects.toThrow();
  });
});
