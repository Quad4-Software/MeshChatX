import GlobalEmitter from "./GlobalEmitter";

function dialogMessage(message) {
    if (message == null) {
        return "";
    }
    return typeof message === "string" ? message : String(message);
}

function hostListenerCount(event) {
    if (typeof GlobalEmitter.listenerCount !== "function") {
        return null;
    }
    return GlobalEmitter.listenerCount(event);
}

class DialogUtils {
    static alert(message, type = "info") {
        if (window.electron) {
            window.electron.alert(message);
        }

        GlobalEmitter.emit("toast", { message, type });
    }

    static confirm(message, title) {
        return new Promise((resolve) => {
            if (hostListenerCount("confirm") === 0) {
                resolve(false);
                return;
            }
            const payload = { message: dialogMessage(message), resolve };
            if (typeof title === "string" && title.trim()) {
                payload.title = title.trim();
            }
            GlobalEmitter.emit("confirm", payload);
        });
    }

    static confirmCustom(message, title) {
        return DialogUtils.confirm(message, title);
    }

    static prompt(message, defaultValue = "", options = {}) {
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
