import { describe, it, expect, vi, beforeEach } from "vitest";
import GlobalEmitter from "../../meshchatx/src/frontend/js/GlobalEmitter";

const wsSend = vi.fn();

vi.mock("../../meshchatx/src/frontend/js/WebSocketConnection", () => ({
    default: {
        send: (...args) => wsSend(...args),
        on: vi.fn(),
        off: vi.fn(),
        emit: vi.fn(),
    },
}));

import KeyboardShortcuts from "../../meshchatx/src/frontend/js/KeyboardShortcuts";

function dispatchKeyDown(init) {
    const ev = new KeyboardEvent("keydown", {
        key: init.key,
        code: init.code,
        ctrlKey: !!init.ctrlKey,
        altKey: !!init.altKey,
        shiftKey: !!init.shiftKey,
        metaKey: !!init.metaKey,
        bubbles: true,
        cancelable: true,
    });
    window.dispatchEvent(ev);
    return ev;
}

describe("KeyboardShortcuts", () => {
    let emitSpy;

    beforeEach(() => {
        vi.clearAllMocks();
        emitSpy = vi.spyOn(GlobalEmitter, "emit");
        document.body.innerHTML = "";
        if (document.activeElement && document.activeElement !== document.body) {
            document.activeElement.blur();
        }
    });

    afterEach(() => {
        KeyboardShortcuts.setShortcuts(KeyboardShortcuts.getDefaultShortcuts());
    });

    it("emits nav_messages for Alt+1", () => {
        dispatchKeyDown({ key: "1", altKey: true, code: "Digit1" });
        expect(emitSpy).toHaveBeenCalledWith("keyboard-shortcut", "nav_messages");
    });

    it("emits nav_nomad for Alt+2", () => {
        dispatchKeyDown({ key: "2", altKey: true, code: "Digit2" });
        expect(emitSpy).toHaveBeenCalledWith("keyboard-shortcut", "nav_nomad");
    });

    it("emits nav_map for Alt+3", () => {
        dispatchKeyDown({ key: "3", altKey: true, code: "Digit3" });
        expect(emitSpy).toHaveBeenCalledWith("keyboard-shortcut", "nav_map");
    });

    it("emits nav_archives for Alt+4", () => {
        dispatchKeyDown({ key: "4", altKey: true, code: "Digit4" });
        expect(emitSpy).toHaveBeenCalledWith("keyboard-shortcut", "nav_archives");
    });

    it("emits nav_calls for Alt+5", () => {
        dispatchKeyDown({ key: "5", altKey: true, code: "Digit5" });
        expect(emitSpy).toHaveBeenCalledWith("keyboard-shortcut", "nav_calls");
    });

    it("emits nav_paper for Alt+P", () => {
        dispatchKeyDown({ key: "p", altKey: true, code: "KeyP" });
        expect(emitSpy).toHaveBeenCalledWith("keyboard-shortcut", "nav_paper");
    });

    it("emits nav_settings for Alt+S", () => {
        dispatchKeyDown({ key: "s", altKey: true, code: "KeyS" });
        expect(emitSpy).toHaveBeenCalledWith("keyboard-shortcut", "nav_settings");
    });

    it("emits compose_message for Alt+N", () => {
        dispatchKeyDown({ key: "n", altKey: true, code: "KeyN" });
        expect(emitSpy).toHaveBeenCalledWith("keyboard-shortcut", "compose_message");
    });

    it("emits sync_messages for Alt+R", () => {
        dispatchKeyDown({ key: "r", altKey: true, code: "KeyR" });
        expect(emitSpy).toHaveBeenCalledWith("keyboard-shortcut", "sync_messages");
    });

    it("emits toggle_sidebar for Ctrl+B", () => {
        dispatchKeyDown({ key: "b", ctrlKey: true, code: "KeyB" });
        expect(emitSpy).toHaveBeenCalledWith("keyboard-shortcut", "toggle_sidebar");
    });

    it("does not emit command_palette from KeyboardShortcuts (handled by CommandPalette)", () => {
        dispatchKeyDown({ key: "k", ctrlKey: true, code: "KeyK" });
        expect(emitSpy).not.toHaveBeenCalledWith("keyboard-shortcut", "command_palette");
    });

    it("allows Alt+digit navigation while focus is in an input (modifier shortcuts)", () => {
        const input = document.createElement("input");
        document.body.appendChild(input);
        input.focus();

        dispatchKeyDown({ key: "2", altKey: true, code: "Digit2" });
        expect(emitSpy).toHaveBeenCalledWith("keyboard-shortcut", "nav_nomad");
    });

    it("setShortcuts replaces shortcuts and still emits for updated actions", () => {
        KeyboardShortcuts.setShortcuts([
            { action: "nav_messages", keys: ["alt", "9"] },
            ...KeyboardShortcuts.getDefaultShortcuts().filter((s) => s.action !== "nav_messages"),
        ]);
        dispatchKeyDown({ key: "9", altKey: true, code: "Digit9" });
        expect(emitSpy).toHaveBeenCalledWith("keyboard-shortcut", "nav_messages");
        KeyboardShortcuts.setShortcuts(KeyboardShortcuts.getDefaultShortcuts());
    });

    it("saveShortcut sends keyboard_shortcuts.set over WebSocket", async () => {
        await KeyboardShortcuts.saveShortcut("nav_messages", ["alt", "q"]);
        expect(wsSend).toHaveBeenCalledWith(
            JSON.stringify({
                type: "keyboard_shortcuts.set",
                action: "nav_messages",
                keys: ["alt", "q"],
            })
        );
    });

    it("deleteShortcut sends keyboard_shortcuts.delete over WebSocket", async () => {
        await KeyboardShortcuts.deleteShortcut("nav_map");
        expect(wsSend).toHaveBeenCalledWith(
            JSON.stringify({
                type: "keyboard_shortcuts.delete",
                action: "nav_map",
            })
        );
    });
});
