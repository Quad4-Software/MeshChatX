// SPDX-License-Identifier: 0BSD

import GlobalEmitter from "./GlobalEmitter.js";

class ToastUtils {
    static show(message: unknown, type = "info", duration = 5000, key: string | null = null): void {
        GlobalEmitter.emit("toast", { message, type, duration, key });
    }

    static success(message: unknown, duration = 5000, key: string | null = null): void {
        this.show(message, "success", duration, key);
    }

    static showSuccess(message: unknown, duration = 5000, key: string | null = null): void {
        this.show(message, "success", duration, key);
    }

    static error(message: unknown, duration = 5000, key: string | null = null): void {
        this.show(message, "error", duration, key);
    }

    static showError(message: unknown, duration = 5000, key: string | null = null): void {
        this.show(message, "error", duration, key);
    }

    static warning(message: unknown, duration = 5000, key: string | null = null): void {
        this.show(message, "warning", duration, key);
    }

    static info(message: unknown, duration = 5000, key: string | null = null): void {
        this.show(message, "info", duration, key);
    }

    static loading(message: unknown, duration = 0, key: string | null = null): void {
        this.show(message, "loading", duration, key);
    }

    static helptips({
        title,
        details,
        type = "warning",
        duration = 11000,
        key = null,
    }: {
        title: unknown;
        details?: unknown;
        type?: string;
        duration?: number;
        key?: string | null;
    }): void {
        GlobalEmitter.emit("toast", {
            message: title,
            details: Array.isArray(details) ? details : [],
            type,
            duration,
            key,
        });
    }

    static dismiss(key: string | null | undefined): void {
        if (key == null) {
            return;
        }
        GlobalEmitter.emit("toast-dismiss", { key });
    }
}

export default ToastUtils;
