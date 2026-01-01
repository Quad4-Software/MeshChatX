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
            // running inside normal browser, use browser alert
            return window.confirm(message);
        }
    }

    static async prompt(message) {
        if (window.electron) {
            // running inside electron, use ipc prompt
            return await window.electron.prompt(message);
        } else {
            // running inside normal browser, use browser prompt
            return window.prompt(message);
        }
    }
}

export default DialogUtils;
