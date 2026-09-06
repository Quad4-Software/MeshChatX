import { cleanup, render } from "@testing-library/svelte";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import AndroidStorageChoicePrompt from "../../meshchatx/src/frontend/features/app-shell/components/AndroidStorageChoicePrompt.svelte";

const scheduleCopyToExternalAndRestart = vi.fn(() => true);
const getStatus = vi.fn(() => ({
    needs_upgrade_prompt: true,
    active_path: "/data/user/0/com.meshchatx/files/meshchatx",
}));

vi.mock("../../meshchatx/src/frontend/js/AndroidStorageBridge.js", () => ({
    default: class MockAndroidStorageBridge {
        isAndroidHost() {
            return true;
        }
        getStatus() {
            return getStatus();
        }
        scheduleCopyToExternalAndRestart() {
            return scheduleCopyToExternalAndRestart();
        }
        keepInternalAndDismiss() {
            return true;
        }
        restartApp() {
            return true;
        }
    },
}));

describe("AndroidStorageChoicePrompt", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    afterEach(() => cleanup());

    it("showUpgrade opens dialog when status requires prompt", async () => {
        const { component } = render(AndroidStorageChoicePrompt, { variant: "upgrade", open: false });
        expect(component.showUpgrade()).toBe(true);
        await Promise.resolve();
        expect(getStatus).toHaveBeenCalled();
    });
});
