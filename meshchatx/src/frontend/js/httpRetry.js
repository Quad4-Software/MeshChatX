/**
 * Retry GET-style helpers when the backend reports temporary unavailability.
 */

/**
 * @param {() => Promise<any>} requestFn
 * @param {{
 *   maxAttempts?: number,
 *   baseDelayMs?: number,
 *   signal?: AbortSignal | null,
 *   isAborted?: () => boolean,
 *   sleep?: (ms: number) => Promise<void>,
 * }} [options]
 * @returns {Promise<any>}
 */
export async function withRetryableHttp(requestFn, options = {}) {
    const maxAttempts = options.maxAttempts ?? 4;
    const baseDelayMs = options.baseDelayMs ?? 250;
    const sleep =
        options.sleep ??
        ((ms) =>
            new Promise((resolve) => {
                setTimeout(resolve, ms);
            }));

    let attempt = 0;
    while (attempt < maxAttempts) {
        if (options.signal?.aborted || options.isAborted?.()) {
            throw Object.assign(new Error("Aborted"), { name: "AbortError" });
        }
        try {
            return await requestFn();
        } catch (requestError) {
            const status = requestError?.response?.status;
            const canRetry =
                status === 503 && attempt < maxAttempts - 1 && !options.signal?.aborted && !options.isAborted?.();
            if (!canRetry) {
                throw requestError;
            }
            attempt += 1;
            await sleep(baseDelayMs * attempt);
        }
    }
    throw new Error("withRetryableHttp exhausted attempts without a result");
}
