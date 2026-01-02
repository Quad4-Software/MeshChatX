import GlobalEmitter from "./GlobalEmitter";
import WebSocketConnection from "./WebSocketConnection";

class KeyboardShortcuts {
    constructor() {
        this.shortcuts = this.getDefaultShortcuts();
        this.activeKeys = new Set();
        this.isRecording = false;
        this.onRecordCallback = null;

        window.addEventListener("keydown", (e) => this.handleKeyDown(e));
        window.addEventListener("keyup", (e) => this.handleKeyUp(e));
        window.addEventListener("blur", () => this.activeKeys.clear());
    }

    getDefaultShortcuts() {
        return [
            { action: "nav_messages", keys: ["alt", "1"], description: "Go to Messages" },
            { action: "nav_nomad", keys: ["alt", "2"], description: "Go to Nomad Network" },
            { action: "nav_map", keys: ["alt", "3"], description: "Go to Map" },
            { action: "nav_paper", keys: ["alt", "p"], description: "Go to Paper Message Generator" },
            { action: "nav_archives", keys: ["alt", "4"], description: "Go to Archives" },
            { action: "nav_calls", keys: ["alt", "5"], description: "Go to Calls" },
            { action: "nav_settings", keys: ["alt", "s"], description: "Go to Settings" },
            { action: "compose_message", keys: ["alt", "n"], description: "Compose New Message" },
            { action: "sync_messages", keys: ["alt", "r"], description: "Sync Messages" },
            { action: "command_palette", keys: ["control", "k"], description: "Open Command Palette" },
            { action: "toggle_sidebar", keys: ["control", "b"], description: "Toggle Sidebar" },
        ];
    }

    handleKeyDown(e) {
        const key = e.key.toLowerCase();
        this.activeKeys.add(key);

        if (this.isRecording) {
            e.preventDefault();
            if (this.onRecordCallback) {
                const keys = Array.from(this.activeKeys);
                this.onRecordCallback(keys);
            }
            return;
        }

        // Check for matches
        for (const shortcut of this.shortcuts) {
            if (this.matches(shortcut.keys)) {
                // Don't trigger if user is typing in an input, unless it's a global shortcut
                if (
                    ["INPUT", "TEXTAREA"].includes(document.activeElement.tagName) &&
                    !shortcut.keys.includes("control") &&
                    !shortcut.keys.includes("alt") &&
                    !shortcut.keys.includes("meta")
                ) {
                    continue;
                }

                e.preventDefault();
                this.executeAction(shortcut.action);
                break;
            }
        }
    }

    handleKeyUp(e) {
        const key = e.key.toLowerCase();
        this.activeKeys.delete(key);
    }

    matches(shortcutKeys) {
        if (shortcutKeys.length === 0) return false;

        // Map common keys
        const mappedActiveKeys = Array.from(this.activeKeys).map((k) => {
            if (k === "control") return "control";
            if (k === "alt") return "alt";
            if (k === "shift") return "shift";
            if (k === "meta") return "meta";
            return k;
        });

        if (shortcutKeys.length !== mappedActiveKeys.length) return false;

        return shortcutKeys.every((k) => mappedActiveKeys.includes(k));
    }

    executeAction(action) {
        GlobalEmitter.emit("keyboard-shortcut", action);
    }

    setShortcuts(shortcuts) {
        // Merge with defaults to ensure all actions have a description
        const defaults = this.getDefaultShortcuts();
        this.shortcuts = shortcuts.map((s) => {
            const def = defaults.find((d) => d.action === s.action);
            return {
                ...s,
                description: def ? def.description : s.action,
            };
        });
    }

    startRecording(callback) {
        this.isRecording = true;
        this.onRecordCallback = callback;
        this.activeKeys.clear();
    }

    stopRecording() {
        this.isRecording = false;
        this.onRecordCallback = null;
        this.activeKeys.clear();
    }

    async saveShortcut(action, keys) {
        WebSocketConnection.send(
            JSON.stringify({
                type: "keyboard_shortcuts.set",
                action: action,
                keys: keys,
            })
        );
    }

    async deleteShortcut(action) {
        WebSocketConnection.send(
            JSON.stringify({
                type: "keyboard_shortcuts.delete",
                action: action,
            })
        );
    }
}

export default new KeyboardShortcuts();
