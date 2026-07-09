const fs = require("fs");
const path = require("node:path");

const CLOSE_BEHAVIORS = new Set(["ask", "quit", "background"]);

function defaultCloseSettings() {
    return {
        closeBehavior: "ask",
        trayEnabled: true,
    };
}

function closeSettingsPath(storageDir) {
    return path.join(storageDir, "desktop-close-settings.json");
}

function normalizeCloseSettings(raw) {
    const defaults = defaultCloseSettings();
    if (!raw || typeof raw !== "object") {
        return defaults;
    }
    const closeBehavior = CLOSE_BEHAVIORS.has(raw.closeBehavior) ? raw.closeBehavior : defaults.closeBehavior;
    const trayEnabled = typeof raw.trayEnabled === "boolean" ? raw.trayEnabled : defaults.trayEnabled;
    return { closeBehavior, trayEnabled };
}

function loadCloseSettings(storageDir) {
    try {
        const filePath = closeSettingsPath(storageDir);
        if (!fs.existsSync(filePath)) {
            return defaultCloseSettings();
        }
        const parsed = JSON.parse(fs.readFileSync(filePath, "utf8"));
        return normalizeCloseSettings(parsed);
    } catch {
        return defaultCloseSettings();
    }
}

function saveCloseSettings(storageDir, partial) {
    const current = loadCloseSettings(storageDir);
    const next = normalizeCloseSettings({
        ...current,
        ...(partial && typeof partial === "object" ? partial : {}),
    });
    try {
        fs.mkdirSync(storageDir, { recursive: true });
        fs.writeFileSync(closeSettingsPath(storageDir), JSON.stringify(next, null, 2), "utf8");
    } catch {
        // ignore persistence failures; in-memory choice still applies for this session
    }
    return next;
}

/**
 * Resolve what to do on window close.
 * @returns {"ask"|"quit"|"background"|"minimize"}
 */
function resolveCloseAction(settings) {
    const normalized = normalizeCloseSettings(settings);
    if (normalized.closeBehavior === "ask") {
        return "ask";
    }
    if (normalized.closeBehavior === "quit") {
        return "quit";
    }
    if (!normalized.trayEnabled) {
        return "minimize";
    }
    return "background";
}

/**
 * Map a chosen close action + remember checkbox into persisted settings.
 * Non-quit choices are stored as "background" and resolved to minimize when tray is off.
 * @param {"quit"|"background"|"minimize"} action
 * @param {boolean} remember
 * @returns {{ closeBehavior: "quit"|"background" }|null}
 */
function rememberedCloseSettings(action, remember) {
    if (!remember) {
        return null;
    }
    if (action === "quit") {
        return { closeBehavior: "quit" };
    }
    if (action === "background" || action === "minimize") {
        return { closeBehavior: "background" };
    }
    return null;
}

/**
 * Simple re-entrancy guard for async close handling.
 */
function createCloseRequestGuard() {
    let inFlight = false;
    return {
        tryEnter() {
            if (inFlight) {
                return false;
            }
            inFlight = true;
            return true;
        },
        leave() {
            inFlight = false;
        },
    };
}

module.exports = {
    CLOSE_BEHAVIORS,
    defaultCloseSettings,
    loadCloseSettings,
    saveCloseSettings,
    resolveCloseAction,
    normalizeCloseSettings,
    rememberedCloseSettings,
    createCloseRequestGuard,
};
