/**
 * Exponential backoff retry logic for the AumOS TypeScript SDK.
 *
 * Uses the "full jitter" strategy: delay = random(0, min(cap, base * 2^attempt)).
 * Respects Retry-After headers on 429 responses.
 *
 * @example
 * const result = await withRetry(() => fetch(url))
 */

export interface RetryConfig {
  /** Maximum number of retry attempts after the initial attempt. Default: 3 */
  maxRetries: number;
  /** Base delay in milliseconds for the first retry. Default: 500 */
  baseDelayMs: number;
  /** Maximum delay cap in milliseconds. Default: 60_000 */
  maxDelayMs: number;
}

export const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxRetries: 3,
  baseDelayMs: 500,
  maxDelayMs: 60_000,
};

const RETRYABLE_STATUS_CODES = new Set([429, 500, 502, 503, 504]);

interface RetryableError extends Error {
  status?: number;
  headers?: Headers | Record<string, string>;
}

function isRetryableError(err: unknown): boolean {
  if (!(err instanceof Error)) return false;
  const retryable = err as RetryableError;
  if (retryable.status !== undefined) {
    return RETRYABLE_STATUS_CODES.has(retryable.status);
  }
  // Network-level errors (no status code) are always retryable
  return (
    err.message.includes("ECONNREFUSED") ||
    err.message.includes("ETIMEDOUT") ||
    err.message.includes("fetch failed")
  );
}

function getRetryAfterMs(err: unknown): number | null {
  if (!(err instanceof Error)) return null;
  const retryable = err as RetryableError;
  if (retryable.status !== 429) return null;

  const headers = retryable.headers;
  if (!headers) return null;

  const retryAfter =
    typeof headers === "object" && "get" in headers
      ? (headers as Headers).get("retry-after")
      : (headers as Record<string, string>)["retry-after"];

  if (retryAfter === null || retryAfter === undefined) return null;
  const parsed = parseFloat(retryAfter);
  return isNaN(parsed) ? null : parsed * 1000;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Execute an async function with automatic exponential backoff retry.
 *
 * @param fn - Async function to execute and retry on transient failure.
 * @param config - Retry configuration (uses DEFAULT_RETRY_CONFIG if omitted).
 * @returns The resolved value of fn on success.
 * @throws The last error after all retry attempts are exhausted.
 */
export async function withRetry<T>(
  fn: () => Promise<T>,
  config: RetryConfig = DEFAULT_RETRY_CONFIG,
): Promise<T> {
  let lastError: unknown;

  for (let attempt = 0; attempt <= config.maxRetries; attempt++) {
    try {
      return await fn();
    } catch (err) {
      lastError = err;

      if (!isRetryableError(err)) {
        throw err;
      }

      if (attempt === config.maxRetries) {
        break;
      }

      const retryAfterMs = getRetryAfterMs(err);
      let delayMs: number;

      if (retryAfterMs !== null) {
        delayMs = Math.min(retryAfterMs, config.maxDelayMs);
      } else {
        const cap = Math.min(config.maxDelayMs, config.baseDelayMs * 2 ** attempt);
        delayMs = Math.random() * cap;
      }

      await sleep(delayMs);
    }
  }

  throw new Error(
    `AumOS request failed after ${config.maxRetries} retries: ${String(lastError)}`,
    { cause: lastError },
  );
}
