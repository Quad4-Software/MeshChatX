// SPDX-License-Identifier: 0BSD

import { describe, it, expect, beforeEach, vi } from "vitest";
import {
    trackMessageNotification,
    closeMessageNotificationsFor,
    closeAllMessageNotifications,
    resetMessageNotificationTrackerForTests,
} from "../../electron/messageNotifications.js";

describe("electron/messageNotifications", () => {
    beforeEach(() => {
        resetMessageNotificationTrackerForTests();
    });

    it("closes notifications for a destination hash", () => {
        const a = { close: vi.fn() };
        const b = { close: vi.fn() };
        trackMessageNotification("aaaa", a);
        trackMessageNotification("bbbb", b);
        expect(closeMessageNotificationsFor("aaaa")).toBe(1);
        expect(a.close).toHaveBeenCalledTimes(1);
        expect(b.close).not.toHaveBeenCalled();
        expect(closeMessageNotificationsFor("aaaa")).toBe(0);
    });

    it("closeAll closes every tracked notification", () => {
        const a = { close: vi.fn() };
        const b = { close: vi.fn() };
        trackMessageNotification("aaaa", a);
        trackMessageNotification("bbbb", b);
        expect(closeAllMessageNotifications()).toBe(2);
        expect(a.close).toHaveBeenCalled();
        expect(b.close).toHaveBeenCalled();
    });

    it("unknown hash is a no-op", () => {
        expect(closeMessageNotificationsFor("missing")).toBe(0);
        expect(closeMessageNotificationsFor("")).toBe(0);
    });
});
