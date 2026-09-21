<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount } from "svelte";
    import GlobalEmitter from "../../js/GlobalEmitter.js";
    import { t } from "../../js/i18n.js";
    import MaterialDesignIcon from "./MaterialDesignIcon.svelte";
    import type { ToastAction } from "../../js/ToastUtils.js";

    const MAX_TOASTS = 8;

    interface ToastItem {
        id: number;
        key?: string | number | null;
        message: string;
        details: string[];
        type: "success" | "error" | "warning" | "loading" | "info";
        duration: number;
        timer: ReturnType<typeof setTimeout> | null;
        action?: ToastAction | null;
        _startX?: number;
        _swipeX?: number;
        _swiping?: boolean;
        swipeClass?: string;
    }

    interface ToastPayload {
        key?: string | number | null;
        message: unknown;
        details?: string[];
        type?: "success" | "error" | "warning" | "loading" | "info";
        duration?: number;
        action?: ToastAction | null;
    }

    let toasts = $state<ToastItem[]>([]);
    let counter = 0;
    const swipeThreshold = 100;

    function looksLikeI18nKey(message: string): boolean {
        if (typeof message !== "string") return false;
        const parts = message.split(".");
        if (parts.length < 2) return false;
        for (let i = 0; i < parts.length; i += 1) {
            const part = parts[i];
            if (!part) return false;
            if (i === 0) {
                const first = part.charCodeAt(0);
                const isLetter = (first >= 65 && first <= 90) || (first >= 97 && first <= 122);
                if (!isLetter) return false;
                for (let j = 1; j < part.length; j += 1) {
                    const code = part.charCodeAt(j);
                    const ok =
                        (code >= 48 && code <= 57) ||
                        (code >= 65 && code <= 90) ||
                        (code >= 97 && code <= 122) ||
                        code === 95;
                    if (!ok) return false;
                }
            } else {
                for (let j = 0; j < part.length; j += 1) {
                    const code = part.charCodeAt(j);
                    const ok =
                        (code >= 48 && code <= 57) ||
                        (code >= 65 && code <= 90) ||
                        (code >= 97 && code <= 122) ||
                        code === 95;
                    if (!ok) return false;
                }
            }
        }
        return true;
    }

    function toastMessage(message: unknown): string {
        if (message == null || message === "") return "";
        const text = typeof message === "string" ? message : String(message);
        // Callers often pass already-translated text. Only look up dotted i18n keys.
        if (!looksLikeI18nKey(text)) {
            return text;
        }
        try {
            return t(text);
        } catch {
            return text;
        }
    }

    function remove(id: number): void {
        const index = toasts.findIndex((entry) => entry.id === id);
        if (index !== -1) {
            const toast = toasts[index];
            if (toast.timer) {
                clearTimeout(toast.timer);
            }
            toasts.splice(index, 1);
            if (toast.key != null) {
                GlobalEmitter.emit("toast-dismissed", { key: toast.key });
            }
        }
    }

    function isMobileViewport(): boolean {
        try {
            return window.matchMedia("(max-width: 639px)").matches;
        } catch {
            return false;
        }
    }

    function runAction(toast: ToastItem): void {
        const handler = toast?.action?.handler;
        remove(toast.id);
        if (typeof handler === "function") {
            try {
                handler();
            } catch (e) {
                console.error("toast action failed", e);
            }
        }
    }

    function add(payload: ToastPayload): void {
        // Generate a stable key for unkeyed toasts so identical messages do not
        // stack into a tower when a retry loop, poll, or watchdog fires repeatedly.
        let toastKey = payload.key;
        if (toastKey == null) {
            toastKey = `__unkeyed:${String(payload.type || "info")}:${String(payload.message || "")}`;
        }

        const existingIndex = toasts.findIndex((entry) => entry.key === toastKey);
        if (existingIndex !== -1) {
            const existing = toasts[existingIndex];
            if (existing.timer) {
                clearTimeout(existing.timer);
            }
            existing.message = payload.message == null ? "" : String(payload.message);
            existing.type = payload.type || "info";
            existing.duration = payload.duration !== undefined ? payload.duration : 5000;
            existing.details = Array.isArray(payload.details) ? payload.details : [];
            existing.action = payload.action || null;

            if (existing.duration > 0) {
                existing.timer = setTimeout(() => {
                    remove(existing.id);
                }, existing.duration);
            } else {
                existing.timer = null;
            }
            return;
        }

        const id = counter++;
        const duration = payload.duration !== undefined ? payload.duration : 5000;
        const newToast: ToastItem = {
            id,
            key: toastKey,
            message: payload.message == null ? "" : String(payload.message),
            details: Array.isArray(payload.details) ? payload.details : [],
            type: payload.type || "info",
            duration,
            timer: null,
            action: payload.action || null,
            _startX: 0,
            _swipeX: 0,
            _swiping: false,
            swipeClass: "",
        };

        if (duration > 0) {
            newToast.timer = setTimeout(() => {
                remove(id);
            }, duration);
        }

        // Mobile shows a single toast at a time. Evict older entries so the
        // newest message replaces the current one instead of stacking.
        if (isMobileViewport()) {
            for (const existing of [...toasts]) {
                remove(existing.id);
            }
        }

        toasts.push(newToast);
        // Backstop cap: unkeyed zero-duration toasts otherwise persist
        // forever when a dismiss call is skipped on an error path.
        while (toasts.length > MAX_TOASTS) {
            const evicted = toasts.shift();
            if (evicted?.timer) {
                clearTimeout(evicted.timer);
            }
        }
    }

    function toastClass(type: string): string {
        switch (type) {
            case "success":
                return "bg-white/90 dark:bg-zinc-900/90 border-green-500/30";
            case "error":
                return "bg-white/90 dark:bg-zinc-900/90 border-red-500/30";
            case "warning":
                return "bg-white/90 dark:bg-zinc-900/90 border-amber-500/30";
            default:
                return "bg-white/90 dark:bg-zinc-900/90 border-blue-500/30";
        }
    }

    function toastSwipeStyle(toast: ToastItem): string {
        const x = toast._swipeX || 0;
        if (x === 0) return "";
        const opacity = Math.max(0, 1 - Math.min(Math.abs(x) / swipeThreshold, 0.6));
        const transition = toast._swiping ? "none" : "transform 0.3s ease";
        return `transform: translateX(${x}px); transition: ${transition}; opacity: ${opacity};`;
    }

    function onTouchStart(event: TouchEvent, toast: ToastItem): void {
        if (event.touches.length !== 1) return;
        toast._startX = event.touches[0].clientX;
        toast._swipeX = 0;
        toast._swiping = true;
        toast.swipeClass = "";
    }

    function onTouchMove(event: TouchEvent, toast: ToastItem): void {
        if (!toast._swiping || event.touches.length !== 1 || toast._startX === undefined) return;
        toast._swipeX = event.touches[0].clientX - toast._startX;
    }

    function onTouchEnd(toast: ToastItem): void {
        if (!toast._swiping) return;
        toast._swiping = false;
        if (Math.abs(toast._swipeX || 0) >= swipeThreshold) {
            toast.swipeClass = (toast._swipeX || 0) > 0 ? "toast-swipe-out-right" : "toast-swipe-out-left";
            setTimeout(() => {
                remove(toast.id);
            }, 250);
        } else {
            toast._swipeX = 0;
        }
    }

    onMount(() => {
        const toastHandler = (payload: unknown) => {
            if (payload && typeof payload === "object") {
                add(payload as ToastPayload);
            }
        };
        const dismissHandler = (payload: unknown) => {
            const typed = payload as { key?: string | number | null } | undefined;
            if (typed && typed.key != null) {
                const index = toasts.findIndex((entry) => entry.key === typed.key);
                if (index !== -1) {
                    remove(toasts[index].id);
                }
            }
        };

        GlobalEmitter.on("toast", toastHandler);
        GlobalEmitter.on("toast-dismiss", dismissHandler);

        return () => {
            GlobalEmitter.off("toast", toastHandler);
            GlobalEmitter.off("toast-dismiss", dismissHandler);
            for (const toast of toasts) {
                if (toast.timer) {
                    clearTimeout(toast.timer);
                }
            }
        };
    });
</script>

<div
    class="fixed max-sm:bottom-[calc(4.5rem+max(1.25rem,env(safe-area-inset-bottom,0px)))] bottom-4 left-1/2 -translate-x-1/2 sm:left-auto sm:right-4 sm:translate-x-0 z-100 flex flex-col gap-2 pointer-events-none w-[calc(100%-2rem)] max-w-sm sm:w-auto sm:max-w-md"
>
    {#each toasts as toast (toast.id)}
        <div
            class="pointer-events-auto flex items-center p-4 w-full sm:min-w-[300px] sm:max-w-md rounded-xl shadow-lg border backdrop-blur-md transition-all duration-300 select-text touch-pan-y {toastClass(
                toast.type
            )} {toast.swipeClass || ''}"
            style={toastSwipeStyle(toast)}
            ontouchstart={(e) => onTouchStart(e, toast)}
            ontouchmove={(e) => onTouchMove(e, toast)}
            ontouchend={() => onTouchEnd(toast)}
            ontouchcancel={() => onTouchEnd(toast)}
            role="status"
        >
            <div class="mr-3 shrink-0">
                {#if toast.type === "success"}
                    <MaterialDesignIcon iconName="check-circle" class="h-6 w-6 text-green-500" />
                {:else if toast.type === "error"}
                    <MaterialDesignIcon iconName="alert-circle" class="h-6 w-6 text-red-500" />
                {:else if toast.type === "warning"}
                    <MaterialDesignIcon iconName="alert" class="h-6 w-6 text-amber-500" />
                {:else if toast.type === "loading"}
                    <MaterialDesignIcon iconName="loading" class="h-6 w-6 text-blue-500 animate-spin" />
                {:else}
                    <MaterialDesignIcon iconName="information" class="h-6 w-6 text-blue-500" />
                {/if}
            </div>

            <div class="flex-1 mr-2 text-sm font-medium text-sem-fg min-w-0">
                <div>{toastMessage(toast.message)}</div>
                {#if toast.details && toast.details.length > 0}
                    <ul class="mt-2 list-disc list-inside space-y-1 text-xs font-normal text-sem-fg-muted">
                        {#each toast.details as line, idx (idx)}
                            <li>{line}</li>
                        {/each}
                    </ul>
                {/if}
                {#if toast.action && toast.action.label}
                    <button
                        type="button"
                        class="mt-2 inline-flex min-h-[36px] items-center rounded-lg border border-sem-border px-3 text-xs font-bold text-sem-accent transition-colors hover:bg-sem-surface-raised"
                        onclick={() => runAction(toast)}
                    >
                        {toastMessage(toast.action.label)}
                    </button>
                {/if}
            </div>

            <button
                type="button"
                class="ml-auto inline-flex min-h-[44px] min-w-[44px] items-center justify-center -my-2 -mr-2 text-sem-fg-muted hover:text-sem-fg"
                aria-label={t("common.close")}
                onclick={() => remove(toast.id)}
            >
                <MaterialDesignIcon iconName="close" class="h-4 w-4" />
            </button>
        </div>
    {/each}
</div>

<style>
    .toast-swipe-out-left {
        transform: translateX(-120%) !important;
        opacity: 0 !important;
        transition:
            transform 0.25s ease,
            opacity 0.25s ease !important;
    }
    .toast-swipe-out-right {
        transform: translateX(120%) !important;
        opacity: 0 !important;
        transition:
            transform 0.25s ease,
            opacity 0.25s ease !important;
    }
</style>
