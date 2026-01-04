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

        // Update active keys from modifiers to ensure they are in sync
        if (e.ctrlKey) this.activeKeys.add("control");
        else if (!this.isRecording) this.activeKeys.delete("control");

        if (e.altKey) this.activeKeys.add("alt");
        else if (!this.isRecording) this.activeKeys.delete("alt");

        if (e.shiftKey) this.activeKeys.add("shift");
        else if (!this.isRecording) this.activeKeys.delete("shift");

        if (e.metaKey) this.activeKeys.add("meta");
        else if (!this.isRecording) this.activeKeys.delete("meta");

        if (!["control", "alt", "shift", "meta"].includes(key)) {
            this.activeKeys.add(key);
        }

        if (this.isRecording) {
            e.preventDefault();
            if (this.onRecordCallback) {
                this.onRecordCallback(Array.from(this.activeKeys));
            }
            return;
        }

        // Check for matches
        for (const shortcut of this.shortcuts) {
            if (this.matches(shortcut.keys, e)) {
                // Don't trigger if user is typing in an input, unless it's a global shortcut
                const isInput = ["INPUT", "TEXTAREA"].includes(document.activeElement.tagName);
                const hasModifier = shortcut.keys.some((k) => ["control", "alt", "meta"].includes(k));

                if (isInput && !hasModifier) {
                    continue;
                }

                e.preventDefault();
                e.stopPropagation();
                this.executeAction(shortcut.action);
                break;
            }
        }
    }

    handleKeyUp(e) {
        const key = e.key.toLowerCase();
        this.activeKeys.delete(key);

        // Sync modifiers on keyup
        if (!e.ctrlKey) this.activeKeys.delete("control");
        if (!e.altKey) this.activeKeys.delete("alt");
        if (!e.shiftKey) this.activeKeys.delete("shift");
        if (!e.metaKey) this.activeKeys.delete("meta");
    }

    matches(shortcutKeys, e) {
        if (!shortcutKeys || shortcutKeys.length === 0) return false;

        // Check modifiers using event properties (most reliable in browsers)
        const hasControl = shortcutKeys.includes("control");
        const hasAlt = shortcutKeys.includes("alt");
        const hasShift = shortcutKeys.includes("shift");

        // Allow Cmd (Meta) to act as Control on Mac for improved compatibility
        const ctrlMatch = hasControl ? e.ctrlKey || e.metaKey : !e.ctrlKey && !e.metaKey;
        const altMatch = hasAlt ? e.altKey : !e.altKey;
        const shiftMatch = hasShift ? e.shiftKey : !e.shiftKey;

        if (!ctrlMatch || !altMatch || !shiftMatch) return false;

        // Find the non-modifier key in the shortcut
        const mainKey = shortcutKeys.find((k) => !["control", "alt", "shift", "meta"].includes(k));
        if (!mainKey) return true; // Modifier-only shortcut (rare but possible)

        const pressedKey = e.key.toLowerCase();
        if (pressedKey === mainKey.toLowerCase()) return true;

        // Layout independence: check e.code as well (handles Alt+key layout changes)
        if (e.code === `Digit${mainKey}`) return true;
        if (e.code === `Key${mainKey.toUpperCase()}`) return true;

        return false;
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
