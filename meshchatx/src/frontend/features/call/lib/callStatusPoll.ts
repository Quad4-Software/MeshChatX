// SPDX-License-Identifier: 0BSD

import {
    CALL_ENDED_RESET_TIMEOUT_MS,
    ELAPSED_TIME_INTERVAL_MS,
    HISTORY_POLL_INTERVAL_MS,
    STATUS_POLL_INTERVAL_MS,
    STATUS_POLL_LIVE_TRANSPORT_INTERVAL_MS,
} from "./constants.js";

export interface CallStatusPollerOptions {
    onPollStatus: () => void | Promise<void>;
    onPollHistory?: () => void | Promise<void>;
    onElapsedTick?: () => void;
    isLiveTransportReady?: () => boolean;
}

/**
 * Coordinates periodic polling for telephone status and call history
 */
export class CallStatusPoller {
    private options: CallStatusPollerOptions;
    private statusIntervalId: ReturnType<typeof setInterval> | null = null;
    private historyIntervalId: ReturnType<typeof setInterval> | null = null;
    private elapsedIntervalId: ReturnType<typeof setInterval> | null = null;
    private endedTimeoutId: ReturnType<typeof setTimeout> | null = null;

    constructor(options: CallStatusPollerOptions) {
        this.options = options;
    }

    /**
     * Starts or restarts the status polling interval depending on live transport status
     */
    startStatusPoll(): void {
        this.stopStatusPoll();
        const liveReady = this.options.isLiveTransportReady ? this.options.isLiveTransportReady() : false;
        const intervalMs = liveReady ? STATUS_POLL_LIVE_TRANSPORT_INTERVAL_MS : STATUS_POLL_INTERVAL_MS;

        this.statusIntervalId = setInterval(() => {
            try {
                const res = this.options.onPollStatus();
                if (res && typeof (res as Promise<void>).catch === "function") {
                    (res as Promise<void>).catch(() => {
                        // ignore poll failure
                    });
                }
            } catch {
                // ignore poll failure
            }
        }, intervalMs);
    }

    /**
     * Stops status polling interval
     */
    stopStatusPoll(): void {
        if (this.statusIntervalId !== null) {
            clearInterval(this.statusIntervalId);
            this.statusIntervalId = null;
        }
    }

    /**
     * Starts background history polling interval
     */
    startHistoryPoll(): void {
        this.stopHistoryPoll();
        if (!this.options.onPollHistory) {
            return;
        }
        this.historyIntervalId = setInterval(() => {
            try {
                const res = this.options.onPollHistory?.();
                if (res && typeof (res as Promise<void>).catch === "function") {
                    (res as Promise<void>).catch(() => {
                        // ignore poll failure
                    });
                }
            } catch {
                // ignore poll failure
            }
        }, HISTORY_POLL_INTERVAL_MS);
    }

    /**
     * Stops background history polling interval
     */
    stopHistoryPoll(): void {
        if (this.historyIntervalId !== null) {
            clearInterval(this.historyIntervalId);
            this.historyIntervalId = null;
        }
    }

    /**
     * Starts the one second elapsed time ticker
     */
    startElapsedTicker(): void {
        this.stopElapsedTicker();
        if (!this.options.onElapsedTick) {
            return;
        }
        this.elapsedIntervalId = setInterval(() => {
            try {
                this.options.onElapsedTick?.();
            } catch {
                // ignore tick failure
            }
        }, ELAPSED_TIME_INTERVAL_MS);
    }

    /**
     * Stops the elapsed time ticker
     */
    stopElapsedTicker(): void {
        if (this.elapsedIntervalId !== null) {
            clearInterval(this.elapsedIntervalId);
            this.elapsedIntervalId = null;
        }
    }

    /**
     * Schedules a callback when call ends after reset timeout
     */
    scheduleEndedReset(callback: () => void, timeoutMs: number = CALL_ENDED_RESET_TIMEOUT_MS): void {
        this.clearEndedReset();
        this.endedTimeoutId = setTimeout(() => {
            this.endedTimeoutId = null;
            callback();
        }, timeoutMs);
    }

    /**
     * Clears pending ended call reset timer
     */
    clearEndedReset(): void {
        if (this.endedTimeoutId !== null) {
            clearTimeout(this.endedTimeoutId);
            this.endedTimeoutId = null;
        }
    }

    /**
     * Starts all poll intervals
     */
    startAll(): void {
        this.startStatusPoll();
        this.startHistoryPoll();
        this.startElapsedTicker();
    }

    /**
     * Stops all active intervals and timeouts
     */
    stopAll(): void {
        this.stopStatusPoll();
        this.stopHistoryPoll();
        this.stopElapsedTicker();
        this.clearEndedReset();
    }
}
