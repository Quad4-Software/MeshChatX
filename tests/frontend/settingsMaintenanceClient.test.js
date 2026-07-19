import { describe, it, expect, vi } from "vitest";
import {
    buildMessageAgeFilterParams,
    previewMessageAgePurge,
    purgeMessagesByAge,
    exportMessagesBundle,
    previewDuplicateMessages,
    clearDuplicateMessages,
} from "@/js/settings/settingsMaintenanceClient.js";

describe("settingsMaintenanceClient message age helpers", () => {
    it("buildMessageAgeFilterParams validates days and date modes", () => {
        expect(buildMessageAgeFilterParams({ mode: "days", days: 90 })).toEqual({
            older_than_days: 90,
        });
        expect(buildMessageAgeFilterParams({ mode: "days", days: 0 })).toBeNull();
        expect(buildMessageAgeFilterParams({ mode: "date", beforeDate: "2024-06-01" })).toEqual({
            before: "2024-06-01",
        });
        expect(buildMessageAgeFilterParams({ mode: "date", beforeDate: "nope" })).toBeNull();
    });

    it("previewMessageAgePurge and purgeMessagesByAge hit the right endpoints", async () => {
        const api = {
            get: vi.fn().mockResolvedValue({ data: { count: 3, cutoff: 10 } }),
            delete: vi.fn().mockResolvedValue({ data: { deleted: 3, cutoff: 10 } }),
        };
        await expect(previewMessageAgePurge(api, { older_than_days: 7 })).resolves.toEqual({
            count: 3,
            cutoff: 10,
        });
        expect(api.get).toHaveBeenCalledWith("/api/v1/maintenance/messages/purge-preview", {
            params: { older_than_days: 7 },
        });
        await expect(purgeMessagesByAge(api, { before: "2024-01-01" })).resolves.toEqual({
            deleted: 3,
            cutoff: 10,
        });
        expect(api.delete).toHaveBeenCalledWith("/api/v1/maintenance/messages", {
            params: { before: "2024-01-01" },
        });
    });

    it("previewDuplicateMessages and clearDuplicateMessages hit endpoints", async () => {
        const api = {
            get: vi.fn().mockResolvedValue({ data: { count: 7 } }),
            delete: vi.fn().mockResolvedValue({ data: { deleted: 7 } }),
        };
        await expect(previewDuplicateMessages(api)).resolves.toEqual({ count: 7 });
        expect(api.get).toHaveBeenCalledWith("/api/v1/maintenance/messages/duplicates");
        await expect(clearDuplicateMessages(api)).resolves.toEqual({ deleted: 7 });
        expect(api.delete).toHaveBeenCalledWith("/api/v1/maintenance/messages/duplicates");
    });

    it("exportMessagesBundle passes optional filter params", async () => {
        const api = {
            get: vi.fn().mockResolvedValue({ data: { messages: [] } }),
        };
        await exportMessagesBundle(api);
        expect(api.get).toHaveBeenCalledWith("/api/v1/maintenance/messages/export", undefined);
        await exportMessagesBundle(api, { older_than_days: 14 });
        expect(api.get).toHaveBeenCalledWith("/api/v1/maintenance/messages/export", {
            params: { older_than_days: 14 },
        });
    });
});
