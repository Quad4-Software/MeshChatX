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
        window.addEventListener("mousedown", () => this.activeKeys.clear()); // Clear on mouse click to prevent stuck modifiers
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
        // Always update modifier states regardless of other conditions
        this.updateModifiers(e);

        const key = e.key.toLowerCase();
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
                if (shortcut.action === "command_palette") {
                    continue;
                }
                // Check if we should ignore because we're in an input
                const isInput =
                    ["INPUT", "TEXTAREA"].includes(document.activeElement.tagName) ||
                    document.activeElement.isContentEditable ||
                    document.activeElement.closest(".v-input"); // Better Vuetify detection

                const hasModifier = shortcut.keys.some((k) => ["control", "alt", "meta"].includes(k));

                // If it's an input, only allow shortcuts with modifiers (like Alt+1, Ctrl+K)
                // but ignore simple keys if they're not explicitly allowed in inputs
                if (isInput && !hasModifier) {
                    continue;
                }

                // Specifically allow navigation shortcuts (Alt+number) even in inputs
                // as they don't usually conflict with typing (unless using special chars)

                e.preventDefault();
                e.stopPropagation();
                this.executeAction(shortcut.action);
                break;
            }
        }
    }

    updateModifiers(e) {
        if (e.ctrlKey) this.activeKeys.add("control");
        else if (!this.isRecording) this.activeKeys.delete("control");

        if (e.altKey) this.activeKeys.add("alt");
        else if (!this.isRecording) this.activeKeys.delete("alt");

        if (e.shiftKey) this.activeKeys.add("shift");
        else if (!this.isRecording) this.activeKeys.delete("shift");

        if (e.metaKey) this.activeKeys.add("meta");
        else if (!this.isRecording) this.activeKeys.delete("meta");
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
        const hasMeta = shortcutKeys.includes("meta");

        // Browsers handle Alt and Control differently on different OSs.
        // We use a normalized approach here.
        const isControlPressed = e.ctrlKey;
        const isAltPressed = e.altKey;
        const isShiftPressed = e.shiftKey;
        const isMetaPressed = e.metaKey;

        const isMac = navigator.platform.toUpperCase().indexOf("MAC") >= 0;
        const ctrlMatch = hasControl
            ? isControlPressed || (isMac && isMetaPressed)
            : !isControlPressed && !(isMac && isMetaPressed);
        if (!ctrlMatch) return false;

        if (isAltPressed !== hasAlt) return false;
        if (isShiftPressed !== hasShift) return false;
        if (!isMac && isMetaPressed !== hasMeta) return false;

        // Find the non-modifier key in the shortcut
        const mainKey = shortcutKeys.find((k) => !["control", "alt", "shift", "meta"].includes(k));
        if (!mainKey) return true; // Modifier-only shortcut (rare but possible)

        const pressedKey = e.key.toLowerCase();

        // Direct key match
        if (pressedKey === mainKey.toLowerCase()) return true;

        // Layout independence: check e.code as well (handles Alt+key layout changes)
        // e.g. Alt+1 might be captured as Digit1 regardless of layout
        const codeMatch =
            e.code === `Digit${mainKey}` ||
            e.code === `Key${mainKey.toUpperCase()}` ||
            e.code === mainKey.toUpperCase(); // For keys like 'Enter', 'Escape'

        if (codeMatch) return true;

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
