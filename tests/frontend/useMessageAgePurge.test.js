// SPDX-License-Identifier: 0BSD

import { beforeEach, describe, expect, it, vi } from "vitest";
import { useMessageAgePurge } from "../../meshchatx/src/frontend/js/settings/useMessageAgePurge.js";
import DialogUtils from "../../meshchatx/src/frontend/js/DialogUtils.js";

describe("useMessageAgePurge", () => {
    beforeEach(() => {
        vi.restoreAllMocks();
        window.api = {
            get: vi.fn(async () => ({ data: { count: 3 } })),
            delete: vi.fn(async () => ({ data: { deleted: 2 } })),
            post: vi.fn(async () => ({ data: { format: "meshchatx/messages/v2", messages: [] } })),
        };
    });

    it("builds filter params from days mode", () => {
        const purge = useMessageAgePurge();
        purge.messageAgePurgeDays.value = 30;
        expect(purge.messageAgeFilterParams()).toEqual({ older_than_days: 30 });
    });

    it("builds filter params from date mode", () => {
        const purge = useMessageAgePurge();
        purge.messageAgePurgeMode.value = "date";
        purge.messageAgePurgeBeforeDate.value = "2024-01-15";
        expect(purge.messageAgeFilterParams()).toEqual({ before: "2024-01-15" });
    });

    it("preview stores the count and toggles loading", async () => {
        const purge = useMessageAgePurge();
        const pending = purge.refreshMessageAgePurgePreview();
        expect(purge.messageAgePurgePreviewLoading.value).toBe(true);
        await pending;
        expect(purge.messageAgePurgePreviewLoading.value).toBe(false);
        expect(purge.messageAgePurgePreviewCount.value).toBe(3);
    });

    it("preview failure resets count to null", async () => {
        window.api.get = vi.fn(async () => Promise.reject(new Error("down")));
        const purge = useMessageAgePurge();
        await purge.refreshMessageAgePurgePreview();
        expect(purge.messageAgePurgePreviewCount.value).toBeNull();
    });

    it("purge asks for confirmation and resets preview count", async () => {
        vi.spyOn(DialogUtils, "confirm").mockResolvedValue(true);
        const purge = useMessageAgePurge();
        purge.messageAgePurgePreviewCount.value = 7;
        await purge.purgeOldMessages();
        expect(DialogUtils.confirm).toHaveBeenCalled();
        expect(window.api.delete).toHaveBeenCalled();
        expect(purge.messageAgePurgePreviewCount.value).toBe(0);
        expect(purge.messageAgePurgeBusy.value).toBe(false);
    });

    it("purge without confirmation does nothing", async () => {
        vi.spyOn(DialogUtils, "confirm").mockResolvedValue(false);
        const purge = useMessageAgePurge();
        await purge.purgeOldMessages();
        expect(window.api.delete).not.toHaveBeenCalled();
    });
});
