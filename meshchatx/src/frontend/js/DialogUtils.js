import GlobalEmitter from "./GlobalEmitter";

class DialogUtils {
    static alert(message, type = "info") {
        if (window.electron) {
            window.electron.alert(message);
        }

        GlobalEmitter.emit("toast", { message, type });
    }

    static confirm(message, title) {
        return new Promise((resolve) => {
            const payload = { message, resolve };
            if (typeof title === "string" && title.trim()) {
                payload.title = title.trim();
            }
            GlobalEmitter.emit("confirm", payload);
        });
    }

    static confirmCustom(message, title) {
        return DialogUtils.confirm(message, title);
    }

    static async prompt(message, defaultValue = "", options = {}) {
        const inputType =
            options && typeof options === "object" && options.inputType ? String(options.inputType) : "text";
        if (window.electron && typeof window.electron.prompt === "function" && inputType === "text") {
            try {
                return await window.electron.prompt(message, defaultValue);
            } catch {
                // Fall through to in-app dialog when IPC prompt fails.
            }
        }
        return new Promise((resolve) => {
            GlobalEmitter.emit("prompt", {
                message,
                defaultValue: defaultValue == null ? "" : String(defaultValue),
                inputType,
                resolve,
            });
        });
    }
}

export default DialogUtils;
