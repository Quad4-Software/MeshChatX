/**
 * Retry helpers when the backend reports temporary unavailability.
 */

/**
 * @param {unknown} error
 * @returns {boolean}
 */
export function isRetryableHttpError(error) {
    if (!error || typeof error !== "object") {
        return false;
    }
    const name = error.name;
    if (name === "AbortError" || name === "CanceledError") {
        return false;
    }
    const status = error.response?.status;
    if (status === 503) {
        return true;
    }
    // No HTTP response: transient backend restart / connection drop.
    if (!error.response && (name === "TypeError" || name === "HttpError" || name === "Error")) {
        const message = typeof error.message === "string" ? error.message.toLowerCase() : "";
        if (
            message.includes("failed to fetch") ||
            message.includes("networkerror") ||
            message.includes("network request failed") ||
            message.includes("load failed") ||
            message.includes("econnrefused") ||
            message.includes("socket hang up")
        ) {
            return true;
        }
    }
    return false;
}

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
export async function withRetryableHttp(requestFn, options: any = {}) {
    // Long enough to cover identity switch and modest DB migrate windows.
    // Pages that mount on early ui_ready should still gate on identity ready.
    const maxAttempts = options.maxAttempts ?? 12;
    const baseDelayMs = options.baseDelayMs ?? 400;
    const sleep =
        options.sleep ??
        ((ms) =>
            new Promise<any>((resolve) => {
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
            const canRetry =
                isRetryableHttpError(requestError) &&
                attempt < maxAttempts - 1 &&
                !options.signal?.aborted &&
                !options.isAborted?.();
            if (!canRetry) {
                throw requestError;
            }
            attempt += 1;
            await sleep(baseDelayMs * attempt);
        }
    }
    throw new Error("withRetryableHttp exhausted attempts without a result");
}
