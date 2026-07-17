import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import NotificationUtils from "../../meshchatx/src/frontend/js/NotificationUtils";

describe("NotificationUtils", () => {
    let originalNotification;
    let electronMock;
    let androidMock;

    beforeEach(() => {
        originalNotification = globalThis.Notification;
        NotificationUtils._webMessageNotifications.clear();
        electronMock = {
            showNotification: vi.fn(),
            closeMessageNotifications: vi.fn(),
        };
        androidMock = {
            getPlatform: vi.fn().mockReturnValue("android"),
            showNotification: vi.fn(),
            showIncomingCallNotification: vi.fn(),
            showMissedCallNotification: vi.fn(),
            cancelIncomingCallNotification: vi.fn(),
            cancelMessageNotifications: vi.fn(),
            cancelAllMessageNotifications: vi.fn(),
            setOpenConversationHashes: vi.fn(),
            setDoNotDisturbEnabled: vi.fn(),
        };
        globalThis.Notification = vi.fn(function (title, opts) {
            this.title = title;
            this.opts = opts;
            this.close = vi.fn();
            return this;
        });
        globalThis.Notification.requestPermission = vi.fn().mockResolvedValue("granted");
    });

    afterEach(() => {
        globalThis.Notification = originalNotification;
        delete globalThis.electron;
        delete globalThis.MeshChatXAndroid;
        vi.restoreAllMocks();
    });

    describe("Electron", () => {
        beforeEach(() => {
            globalThis.electron = electronMock;
        });

        it("showNewMessageNotification delegates to electron with destination hash", () => {
            NotificationUtils.showNewMessageNotification("Alice", "hello", false, "abcd");
            expect(electronMock.showNotification).toHaveBeenCalledWith("New Message", "Alice: hello", false, "abcd");
        });

        it("showNewMessageNotification passes silent flag to electron", () => {
            NotificationUtils.showNewMessageNotification("Alice", "hello", true, "abcd");
            expect(electronMock.showNotification).toHaveBeenCalledWith("New Message", "Alice: hello", true, "abcd");
        });

        it("clearMessageNotifications delegates to electron", () => {
            NotificationUtils.clearMessageNotifications("abcd");
            expect(electronMock.closeMessageNotifications).toHaveBeenCalledWith("abcd");
        });

        it("showIncomingCallNotification delegates to electron", () => {
            NotificationUtils.showIncomingCallNotification("Bob");
            expect(electronMock.showNotification).toHaveBeenCalledWith("Incoming Call", "Bob is calling you.");
        });

        it("showMissedCallNotification delegates to electron", () => {
            NotificationUtils.showMissedCallNotification("Charlie");
            expect(electronMock.showNotification).toHaveBeenCalledWith(
                "Missed Call",
                "You missed a call from Charlie."
            );
        });

        it("showNewVoicemailNotification delegates to electron", () => {
            NotificationUtils.showNewVoicemailNotification("Dave");
            expect(electronMock.showNotification).toHaveBeenCalledWith(
                "New Voicemail",
                "You have a new voicemail from Dave."
            );
        });
    });

    describe("Android", () => {
        beforeEach(() => {
            globalThis.MeshChatXAndroid = androidMock;
        });

        it("showNewMessageNotification does not post OS notifs (push bridge owns them)", () => {
            NotificationUtils.showNewMessageNotification("Alice", "hello", false, "abcd");
            expect(androidMock.showNotification).not.toHaveBeenCalled();
        });

        it("clearMessageNotifications cancels by destination hash", () => {
            NotificationUtils.clearMessageNotifications("abcd");
            expect(androidMock.cancelMessageNotifications).toHaveBeenCalledWith("abcd");
        });

        it("clearAllMessageNotifications cancels all", () => {
            NotificationUtils.clearAllMessageNotifications();
            expect(androidMock.cancelAllMessageNotifications).toHaveBeenCalled();
        });

        it("syncAndroidNotificationContext pushes open peers and DND", () => {
            NotificationUtils.syncAndroidNotificationContext(["AAAA", "bbbb"], true);
            expect(androidMock.setOpenConversationHashes).toHaveBeenCalledWith("aaaa,bbbb");
            expect(androidMock.setDoNotDisturbEnabled).toHaveBeenCalledWith(true);
        });

        it("showIncomingCallNotification delegates to Android bridge", () => {
            NotificationUtils.showIncomingCallNotification("Bob");
            expect(androidMock.showIncomingCallNotification).toHaveBeenCalledWith("Bob");
        });

        it("showMissedCallNotification delegates to Android bridge", () => {
            NotificationUtils.showMissedCallNotification("Charlie");
            expect(androidMock.showMissedCallNotification).toHaveBeenCalledWith(
                "Missed Call",
                "You missed a call from Charlie."
            );
        });

        it("cancelIncomingCallNotification delegates to Android bridge", () => {
            NotificationUtils.cancelIncomingCallNotification();
            expect(androidMock.cancelIncomingCallNotification).toHaveBeenCalled();
        });
    });

    describe("Browser fallback", () => {
        it("showNewMessageNotification uses per-peer tag", async () => {
            NotificationUtils.showNewMessageNotification("Alice", "hello", false, "abcd1234");
            await new Promise((r) => setTimeout(r, 10));
            expect(globalThis.Notification).toHaveBeenCalledWith(
                "New Message",
                expect.objectContaining({ body: "Alice: hello", tag: "lxmf-abcd1234" })
            );
        });

        it("clearMessageNotifications closes tracked web notifications", async () => {
            NotificationUtils.showNewMessageNotification("Alice", "hello", false, "peer1");
            await new Promise((r) => setTimeout(r, 10));
            const instance = globalThis.Notification.mock.results[0].value;
            NotificationUtils.clearMessageNotifications("peer1");
            expect(instance.close).toHaveBeenCalled();
        });

        it("clear unknown hash is a no-op", () => {
            expect(() => NotificationUtils.clearMessageNotifications("missing")).not.toThrow();
        });
    });

    describe("_isAndroid detection", () => {
        it("returns false when MeshChatXAndroid is missing", () => {
            expect(NotificationUtils._isAndroid()).toBe(false);
        });

        it("returns false when getPlatform returns non-android", () => {
            globalThis.MeshChatXAndroid = { getPlatform: () => "ios" };
            expect(NotificationUtils._isAndroid()).toBe(false);
        });

        it("returns true when getPlatform returns android", () => {
            globalThis.MeshChatXAndroid = androidMock;
            expect(NotificationUtils._isAndroid()).toBe(true);
        });
    });
});
