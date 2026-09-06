/**
 * Retry helpers when the backend reports temporary unavailability.
 */

export type RetryableHttpError = {
    name?: string;
    message?: string;
    response?: { status?: number };
};

export type WithRetryableHttpOptions = {
    maxAttempts?: number;
    baseDelayMs?: number;
    signal?: AbortSignal | null;
    isAborted?: () => boolean;
    sleep?: (ms: number) => Promise<void>;
};

export function isRetryableHttpError(error: unknown): boolean {
    if (!error || typeof error !== "object") {
        return false;
    }
    const err = error as RetryableHttpError;
    const name = err.name;
    if (name === "AbortError" || name === "CanceledError") {
        return false;
    }
    const status = err.response?.status;
    if (status === 503) {
        return true;
    }
    // No HTTP response: transient backend restart / connection drop.
    if (!err.response && (name === "TypeError" || name === "HttpError" || name === "Error")) {
        const message = typeof err.message === "string" ? err.message.toLowerCase() : "";
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

export async function withRetryableHttp<T>(
    requestFn: () => Promise<T>,
    options: WithRetryableHttpOptions = {}
): Promise<T> {
    // Long enough to cover identity switch and modest DB migrate windows.
    // Pages that mount on early ui_ready should still gate on identity ready.
    const maxAttempts = options.maxAttempts ?? 12;
    const baseDelayMs = options.baseDelayMs ?? 400;
    const sleep =
        options.sleep ??
        ((ms: number) =>
            new Promise<void>((resolve) => {
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
