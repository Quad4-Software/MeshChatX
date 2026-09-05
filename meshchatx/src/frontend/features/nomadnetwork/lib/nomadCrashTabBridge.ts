// SPDX-License-Identifier: 0BSD

import { NOMAD_CRASH_TAB_CHANNEL } from "../../../js/nomadCrashTabShell.js";
import {
    WATCHDOG_MS,
    PING_INTERVAL_MS,
    WATCHDOG_STALL_MS,
    RENDER_DEADLINE_MS,
    RENDER_DEADLINE_MIN_RESUME_MS,
} from "./constants.js";
import type { NomadNavigateEvent } from "./types.js";

export function toCloneableMessage(msg: Record<string, unknown>): Record<string, unknown> | null {
    if (typeof structuredClone === "function") {
        try {
            return structuredClone({ channel: NOMAD_CRASH_TAB_CHANNEL, ...msg });
        } catch {
            // fall through to JSON
        }
    }
    try {
        return JSON.parse(JSON.stringify({ channel: NOMAD_CRASH_TAB_CHANNEL, ...msg }));
    } catch {
        return null;
    }
}

export function postToFrame(frame: HTMLIFrameElement | null, msg: Record<string, unknown>): boolean {
    if (!frame || !frame.contentWindow) {
        return false;
    }
    const payload = toCloneableMessage(msg);
    if (!payload) {
        return false;
    }
    frame.contentWindow.postMessage(payload, "*");
    return true;
}

export function isDocumentHidden(): boolean {
    if (typeof document === "undefined") {
        return false;
    }
    return document.visibilityState === "hidden" || document.hidden === true;
}

export interface WatchdogCallbacks {
    onHung: () => void;
    onPing: (pingId: number) => void;
}

export class NomadCrashTabWatchdog {
    private pingTimer: ReturnType<typeof setInterval> | null = null;
    private watchdogTimer: ReturnType<typeof setInterval> | null = null;
    private lastPongAt = Date.now();
    private pendingPingId = 0;

    constructor(private callbacks: WatchdogCallbacks) {}

    public ping(active: boolean, frameReady: boolean, livenessPaused: boolean): void {
        if (!active || !frameReady || livenessPaused || isDocumentHidden()) {
            return;
        }
        this.pendingPingId += 1;
        this.callbacks.onPing(this.pendingPingId);
    }

    public recordPong(): void {
        this.lastPongAt = Date.now();
    }

    public getLastPongAt(): number {
        return this.lastPongAt;
    }

    public start(active: boolean, livenessPaused: boolean): void {
        this.stop();
        if (!active || livenessPaused || isDocumentHidden()) {
            return;
        }
        this.lastPongAt = Date.now();
        this.pingTimer = setInterval(() => {
            this.callbacks.onPing(++this.pendingPingId);
        }, PING_INTERVAL_MS);
        this.watchdogTimer = setInterval(() => {
            this.check(active, livenessPaused);
        }, 1000);
    }

    public check(active: boolean, livenessPaused: boolean): void {
        if (!active || livenessPaused || isDocumentHidden()) {
            return;
        }
        const silentMs = Date.now() - this.lastPongAt;
        if (silentMs <= WATCHDOG_MS) {
            return;
        }
        if (silentMs > WATCHDOG_STALL_MS) {
            this.lastPongAt = Date.now();
            this.callbacks.onPing(++this.pendingPingId);
            return;
        }
        this.callbacks.onHung();
    }

    public stop(): void {
        if (this.pingTimer != null) {
            clearInterval(this.pingTimer);
            this.pingTimer = null;
        }
        if (this.watchdogTimer != null) {
            clearInterval(this.watchdogTimer);
            this.watchdogTimer = null;
        }
    }
}

export class NomadRenderDeadline {
    private timer: ReturnType<typeof setTimeout> | null = null;
    private armedAt = 0;
    private remainingMs = 0;
    private isParked = false;

    constructor(private onTimeout: () => void) {}

    public clear(): void {
        if (this.timer != null) {
            clearTimeout(this.timer);
            this.timer = null;
        }
        this.isParked = false;
        this.remainingMs = 0;
        this.armedAt = 0;
    }

    public park(status: string): void {
        if (this.timer != null) {
            clearTimeout(this.timer);
            this.timer = null;
            const elapsed = Date.now() - (this.armedAt || Date.now());
            const left = (this.remainingMs || RENDER_DEADLINE_MS) - elapsed;
            this.remainingMs = Math.max(RENDER_DEADLINE_MIN_RESUME_MS, left);
            this.isParked = true;
            return;
        }
        if (status === "rendering" || status === "loading") {
            this.isParked = true;
            if (!this.remainingMs) {
                this.remainingMs = RENDER_DEADLINE_MS;
            }
        }
    }

    public arm(
        livenessPaused: boolean,
        currentEpoch: number,
        getEpoch: () => number,
        getStatus: () => string,
        timeoutMs?: number
    ): void {
        this.clear();
        const wait = timeoutMs == null ? RENDER_DEADLINE_MS : timeoutMs;
        this.remainingMs = wait;
        if (livenessPaused || isDocumentHidden()) {
            this.isParked = true;
            return;
        }
        this.armedAt = Date.now();
        this.timer = setTimeout(() => {
            this.timer = null;
            if (getEpoch() !== currentEpoch) {
                return;
            }
            const st = getStatus();
            if (st !== "rendering" && st !== "loading") {
                return;
            }
            if (livenessPaused || isDocumentHidden()) {
                this.isParked = true;
                if (!this.remainingMs) {
                    this.remainingMs = RENDER_DEADLINE_MS;
                }
                return;
            }
            this.onTimeout();
        }, wait);
    }

    public unpark(
        livenessPaused: boolean,
        currentEpoch: number,
        getEpoch: () => number,
        getStatus: () => string
    ): void {
        if (!this.isParked) {
            return;
        }
        this.isParked = false;
        const st = getStatus();
        if (st !== "rendering" && st !== "loading") {
            this.remainingMs = 0;
            return;
        }
        this.arm(livenessPaused, currentEpoch, getEpoch, getStatus, this.remainingMs || RENDER_DEADLINE_MS);
    }
}

export interface CrashTabMessageCallbacks {
    onReady: () => void;
    onPong: () => void;
    onRenderStarted: () => void;
    onRenderDone: (partials: unknown[]) => void;
    onRenderError: () => void;
    onShellBackground: (bg: string | null) => void;
    onAborted: () => void;
    onNavigate: (event: NomadNavigateEvent) => void;
}

export function handleCrashTabMessage(
    event: MessageEvent,
    frame: HTMLIFrameElement | null,
    callbacks: CrashTabMessageCallbacks
): void {
    if (
        frame &&
        frame.contentWindow &&
        event.source &&
        event.source !== frame.contentWindow &&
        event.source !== window
    ) {
        return;
    }
    const data = event.data;
    if (!data || data.channel !== NOMAD_CRASH_TAB_CHANNEL) {
        return;
    }
    switch (data.type) {
        case "ready":
            callbacks.onReady();
            break;
        case "pong":
            callbacks.onPong();
            break;
        case "render-started":
            callbacks.onRenderStarted();
            break;
        case "render-done":
            callbacks.onRenderDone(Array.isArray(data.partials) ? data.partials : []);
            break;
        case "render-error":
            callbacks.onRenderError();
            break;
        case "shell-background":
            callbacks.onShellBackground(data.background || null);
            break;
        case "aborted":
            callbacks.onAborted();
            break;
        case "navigate":
            callbacks.onNavigate({
                kind: data.kind,
                url: data.url,
                fields: data.fields,
                fieldSpec: data.fieldSpec,
                button: data.button,
                ctrlKey: data.ctrlKey,
                metaKey: data.metaKey,
            });
            break;
    }
}
