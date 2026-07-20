import GlobalEmitter from "./GlobalEmitter";

class DialogUtils {
    static alert(message, type = "info") {
        if (window.electron) {
            // running inside electron, use ipc alert
            window.electron.alert(message);
        }

        // always show toast as well (or instead of browser alert)
        GlobalEmitter.emit("toast", { message, type });
    }

    static confirm(message) {
        if (window.electron) {
            // running inside electron, use ipc confirm
            return window.electron.confirm(message);
        } else {
            // running inside normal browser, use custom confirm dialog
            return new Promise((resolve) => {
                GlobalEmitter.emit("confirm", { message, resolve });
            });
        }
    }

    // Always use the in-app confirm dialog, even inside electron, for
    // callers that want a themed dialog instead of the native OS prompt.
    static confirmCustom(message) {
        return new Promise((resolve) => {
            GlobalEmitter.emit("confirm", { message, resolve });
        });
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
