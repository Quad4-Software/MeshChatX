import GlobalEmitter from "./GlobalEmitter";

class ToastUtils {
    static show(message, type = "info", duration = 5000, key = null) {
        GlobalEmitter.emit("toast", { message, type, duration, key });
    }

    static success(message, duration = 5000, key = null) {
        this.show(message, "success", duration, key);
    }

    static error(message, duration = 5000, key = null) {
        this.show(message, "error", duration, key);
    }

    static warning(message, duration = 5000, key = null) {
        this.show(message, "warning", duration, key);
    }

    static info(message, duration = 5000, key = null) {
        this.show(message, "info", duration, key);
    }

    static loading(message, duration = 0, key = null) {
        this.show(message, "loading", duration, key);
    }
}

export default ToastUtils;
