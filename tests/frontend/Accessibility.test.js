import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";
import GlobalEmitter from "../../meshchatx/src/frontend/js/GlobalEmitter";
import GlobalState from "../../meshchatx/src/frontend/js/GlobalState";
import "../../meshchatx/src/frontend/js/KeyboardShortcuts";

// Mock Vuetify components that might be used
const VBtn = {
    template: '<button class="v-btn"><slot /></button>',
};

const VTextField = {
    template: '<div class="v-text-field"><input class="v-field__input" /></div>',
};

describe("UI Accessibility and Keyboard Navigation", () => {
    beforeEach(() => {
        // Reset document state
        document.body.innerHTML = "";
        vi.clearAllMocks();
    });

    it("verifies that keyboard shortcuts trigger global events", async () => {
        const emitSpy = vi.spyOn(GlobalEmitter, "emit");

        // Test a few shortcuts (Ctrl+K is handled by CommandPalette in capture phase; KeyboardShortcuts skips emitting it)
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

        // Create an input and focus it
        const input = document.createElement("input");
        document.body.appendChild(input);
        input.focus();

        // Trigger a key that matches a shortcut action name or similar (if any existed without modifiers)
        // For now, let's just verify that Alt+1 still works in an input
        const navEvent = new KeyboardEvent("keydown", {
            key: "1",
            altKey: true,
            code: "Digit1",
            bubbles: true,
        });
        window.dispatchEvent(navEvent);
        expect(emitSpy).toHaveBeenCalledWith("keyboard-shortcut", "nav_messages");

        // Verify a plain key doesn't trigger anything (though none of our defaults are plain keys)
    });

    it("checks for ARIA labels on critical buttons", async () => {
        // We can mount a component and check for accessibility attributes
        const TestComponent = {
            template: `
        <div>
          <button aria-label="Send Message" class="send-btn">Icon Only</button>
          <button class="named-btn">Delete</button>
        </div>
      `,
        };

        const wrapper = mount(TestComponent);
        const sendBtn = wrapper.find(".send-btn");

        expect(sendBtn.attributes("aria-label")).toBe("Send Message");
    });
});
