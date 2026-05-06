import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import NotificationUtils from "../../meshchatx/src/frontend/js/NotificationUtils";

describe("NotificationUtils", () => {
    let originalNotification;
    let electronMock;
    let androidMock;

    beforeEach(() => {
        originalNotification = globalThis.Notification;
        electronMock = { showNotification: vi.fn() };
        androidMock = {
            getPlatform: vi.fn().mockReturnValue("android"),
            showNotification: vi.fn(),
            showIncomingCallNotification: vi.fn(),
            showMissedCallNotification: vi.fn(),
            cancelIncomingCallNotification: vi.fn(),
        };
        globalThis.Notification = vi.fn(function (title, opts) {
            return { title, opts };
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

        it("showNewMessageNotification delegates to electron", () => {
            NotificationUtils.showNewMessageNotification("Alice", "hello");
            expect(electronMock.showNotification).toHaveBeenCalledWith("New Message", "Alice: hello");
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

        it("showNewMessageNotification delegates to Android bridge", () => {
            NotificationUtils.showNewMessageNotification("Alice", "hello");
            expect(androidMock.showNotification).toHaveBeenCalledWith("New Message", "Alice: hello");
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

        it("showNewVoicemailNotification delegates to Android bridge", () => {
            NotificationUtils.showNewVoicemailNotification("Dave");
            expect(androidMock.showNotification).toHaveBeenCalledWith(
                "New Voicemail",
                "You have a new voicemail from Dave."
            );
        });

        it("cancelIncomingCallNotification delegates to Android bridge", () => {
            NotificationUtils.cancelIncomingCallNotification();
            expect(androidMock.cancelIncomingCallNotification).toHaveBeenCalled();
        });
    });

    describe("Browser fallback", () => {
        it("showNewMessageNotification uses browser Notification API", async () => {
            NotificationUtils.showNewMessageNotification("Alice", "hello");
            await new Promise((r) => setTimeout(r, 10));
            expect(globalThis.Notification).toHaveBeenCalledWith(
                "New Message",
                expect.objectContaining({ body: "Alice: hello" })
            );
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
