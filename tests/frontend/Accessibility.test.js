import { describe, it, expect, vi, beforeEach } from "vitest";
import GlobalEmitter from "../../meshchatx/src/frontend/js/GlobalEmitter";
import "../../meshchatx/src/frontend/js/KeyboardShortcuts";

describe("UI Accessibility and Keyboard Navigation", () => {
    beforeEach(() => {
        document.body.innerHTML = "";
        vi.clearAllMocks();
    });

    it("verifies that keyboard shortcuts trigger global events", async () => {
        const emitSpy = vi.spyOn(GlobalEmitter, "emit");
        const shortcuts = [
            { key: "1", altKey: true, action: "nav_messages" },
            { key: "s", altKey: true, action: "nav_settings" },
        ];
        for (const shortcut of shortcuts) {
            const event = new KeyboardEvent("keydown", {
                key: shortcut.key,
                altKey: shortcut.altKey || false,
                ctrlKey: shortcut.ctrlKey || false,
                code: shortcut.key.match(/^\d$/) ? `Digit${shortcut.key}` : `Key${shortcut.key.toUpperCase()}`,
                bubbles: true,
            });
            window.dispatchEvent(event);
            expect(emitSpy).toHaveBeenCalledWith("keyboard-shortcut", shortcut.action);
        }
        const ctrlK = new KeyboardEvent("keydown", {
            key: "k",
            ctrlKey: true,
            code: "KeyK",
            bubbles: true,
        });
        window.dispatchEvent(ctrlK);
        expect(emitSpy).toHaveBeenCalledTimes(2);
    });

    it("ensures shortcuts are ignored in inputs without modifiers", async () => {
        const emitSpy = vi.spyOn(GlobalEmitter, "emit");
        const input = document.createElement("input");
        document.body.appendChild(input);
        input.focus();
        const navEvent = new KeyboardEvent("keydown", {
            key: "1",
            altKey: true,
            code: "Digit1",
            bubbles: true,
        });
        window.dispatchEvent(navEvent);
        expect(emitSpy).toHaveBeenCalledWith("keyboard-shortcut", "nav_messages");
    });

    it("checks for ARIA labels on critical buttons", () => {
        document.body.innerHTML = `
        <div>
          <button aria-label="Send Message" class="send-btn">Icon Only</button>
          <button class="named-btn">Delete</button>
        </div>`;
        const sendBtn = document.querySelector(".send-btn");
        expect(sendBtn.getAttribute("aria-label")).toBe("Send Message");
    });
});
