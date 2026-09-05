// SPDX-License-Identifier: 0BSD

import GlobalEmitter from "./GlobalEmitter.js";

function dialogMessage(message: unknown): string {
    if (message == null) {
        return "";
    }
    return typeof message === "string" ? message : String(message);
}

function hostListenerCount(event: string): number | null {
    const emitter = GlobalEmitter as { listenerCount?: (e: string) => number };
    if (typeof emitter.listenerCount !== "function") {
        return null;
    }
    return emitter.listenerCount(event);
}

class DialogUtils {
    static alert(message: unknown, type = "info"): void {
        if (window.electron?.alert) {
            window.electron.alert(message);
        }
        GlobalEmitter.emit("toast", { message, type });
    }

    static confirm(message: unknown, title?: string): Promise<boolean> {
        return new Promise((resolve) => {
            if (hostListenerCount("confirm") === 0) {
                resolve(false);
                return;
            }
            const payload: { message: string; resolve: (v: boolean) => void; title?: string } = {
                message: dialogMessage(message),
                resolve,
            };
            if (typeof title === "string" && title.trim()) {
                payload.title = title.trim();
            }
            GlobalEmitter.emit("confirm", payload);
        });
    }

    static confirmCustom(message: unknown, title?: string): Promise<boolean> {
        return DialogUtils.confirm(message, title);
    }

    static prompt(
        message: unknown,
        defaultValue: unknown = "",
        options: { inputType?: string } | null = {}
    ): Promise<string | null> {
        const inputType =
            options && typeof options === "object" && options.inputType ? String(options.inputType) : "text";
        return new Promise((resolve) => {
            if (hostListenerCount("prompt") === 0) {
                resolve(null);
                return;
            }
            GlobalEmitter.emit("prompt", {
                message: dialogMessage(message),
                defaultValue: defaultValue == null ? "" : String(defaultValue),
                inputType,
                resolve,
            });
        });
    }
}

export default DialogUtils;
