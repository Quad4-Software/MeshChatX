import GlobalEmitter from "./GlobalEmitter";

class ToastUtils {
    static show(message, type = "info", duration = 5000) {
        GlobalEmitter.emit("toast", { message, type, duration });
    }

    static success(message, duration = 5000) {
        this.show(message, "success", duration);
    }

    static error(message, duration = 5000) {
        this.show(message, "error", duration);
    }

    static warning(message, duration = 5000) {
        this.show(message, "warning", duration);
    }

    static info(message, duration = 5000) {
        this.show(message, "info", duration);
    }
}

export default ToastUtils;
