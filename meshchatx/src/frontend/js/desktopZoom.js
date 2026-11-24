import { NOMAD_CRASH_TAB_CHANNEL } from "./nomadCrashTabShell.js";

export const DESKTOP_ZOOM_MESSAGE_TYPE = "desktop-zoom";
export const DESKTOP_ZOOM_ACTIONS = ["in", "out", "reset"];

export function desktopZoomKeyAction(event) {
    if (!event || event.defaultPrevented || !(event.ctrlKey || event.metaKey) || event.altKey) {
        return null;
    }
    const key = String(event.key || "");
    if (key === "=" || key === "+") {
        return "in";
    }
    if (key === "-") {
        return "out";
    }
    if (key === "0") {
        return "reset";
    }
    return null;
}

export function desktopZoomWheelAction(event) {
    if (!event || event.defaultPrevented || !(event.ctrlKey || event.metaKey)) {
        return null;
    }
    if (event.deltaY < 0) {
        return "in";
    }
    if (event.deltaY > 0) {
        return "out";
    }
    return null;
}

export function desktopZoomBridge(win) {
    const desktop = win && win.desktop;
    return desktop && typeof desktop.zoom === "function" ? desktop : null;
}

export function isDesktopZoomAvailable(win) {
    const target = win || (typeof window !== "undefined" ? window : null);
    return desktopZoomBridge(target) != null;
}

export function getDesktopZoom(win) {
    const target = win || (typeof window !== "undefined" ? window : null);
    const desktop = target && target.desktop;
    if (!desktop || typeof desktop.getZoom !== "function") {
        return Promise.resolve(null);
    }
    return Promise.resolve(desktop.getZoom())
        .then((level) => (typeof level === "number" && isFinite(level) ? level : null))
        .catch(() => null);
}

export function requestDesktopZoom(win, action) {
    const bridge = desktopZoomBridge(win);
    if (!bridge || DESKTOP_ZOOM_ACTIONS.indexOf(action) < 0) {
        return Promise.resolve(null);
    }
    return Promise.resolve(bridge.zoom(action))
        .then((res) => {
            const level = res && typeof res.zoom === "number" ? res.zoom : null;
            return level;
        })
        .catch(() => null);
}

export function installDesktopZoom(win) {
    const target = win || (typeof window !== "undefined" ? window : null);
    const bridge = desktopZoomBridge(target);
    if (!bridge || !target || target.__desktopZoomInstalled) {
        return null;
    }
    target.__desktopZoomInstalled = true;

    const send = (action) => {
        try {
            Promise.resolve(bridge.zoom(action)).catch(() => {});
        } catch {
            return;
        }
    };
    const onKeyDown = (event) => {
        const action = desktopZoomKeyAction(event);
        if (action) {
            event.preventDefault();
            send(action);
        }
    };
    const onWheel = (event) => {
        const action = desktopZoomWheelAction(event);
        if (action) {
            event.preventDefault();
            send(action);
        }
    };
    const onMessage = (event) => {
        const data = event && event.data;
        if (!data || data.channel !== NOMAD_CRASH_TAB_CHANNEL || data.type !== DESKTOP_ZOOM_MESSAGE_TYPE) {
            return;
        }
        if (event.origin !== "null") {
            return;
        }
        if (DESKTOP_ZOOM_ACTIONS.indexOf(data.action) < 0) {
            return;
        }
        send(data.action);
    };
    target.addEventListener("keydown", onKeyDown);
    target.addEventListener("wheel", onWheel, { passive: false });
    target.addEventListener("message", onMessage);
    return function uninstallDesktopZoom() {
        target.removeEventListener("keydown", onKeyDown);
        target.removeEventListener("wheel", onWheel);
        target.removeEventListener("message", onMessage);
        target.__desktopZoomInstalled = false;
    };
}
