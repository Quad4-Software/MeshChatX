// SPDX-License-Identifier: 0BSD

type ClosableNotification = { close: () => void };

class NotificationUtils {
    static _webMessageNotifications = new Map<string, ClosableNotification[]>();

    static _isAndroid(): boolean {
        return Boolean(
            typeof window !== "undefined" &&
            window.MeshChatXAndroid &&
            typeof window.MeshChatXAndroid.getPlatform === "function" &&
            window.MeshChatXAndroid.getPlatform() === "android"
        );
    }

    /** Android OS message notifs are owned by the Python push bridge. */
    static ownsOsMessageNotifications(): boolean {
        return !NotificationUtils._isAndroid();
    }

    static _normalizeHash(destinationHash: unknown): string {
        if (destinationHash == null) {
            return "";
        }
        return String(destinationHash).trim().toLowerCase();
    }

    static _messageTag(destinationHash: unknown): string {
        const h = NotificationUtils._normalizeHash(destinationHash);
        return h ? `lxmf-${h}` : "new_message";
    }

    static _trackWebNotification(destinationHash: string, notification: ClosableNotification): void {
        const key = NotificationUtils._normalizeHash(destinationHash) || "__untagged__";
        let list = NotificationUtils._webMessageNotifications.get(key);
        if (!list) {
            list = [];
            NotificationUtils._webMessageNotifications.set(key, list);
        }
        list.push(notification);
    }

    static showIncomingCallNotification(callerName?: unknown): void {
        if (window.electron) {
            window.electron.showNotification(
                "Incoming Call",
                callerName ? `${callerName} is calling you.` : "Someone is calling you."
            );
            return;
        }
        if (NotificationUtils._isAndroid()) {
            window.MeshChatXAndroid.showIncomingCallNotification(callerName || "Someone");
            return;
        }
        Notification.requestPermission().then((result) => {
            if (result === "granted") {
                new window.Notification("Incoming Call", {
                    body: callerName ? `${callerName} is calling you.` : "Someone is calling you.",
                    tag: "incoming_telephone_call",
                });
            }
        });
    }

    static showMissedCallNotification(from: unknown): void {
        if (window.electron) {
            window.electron.showNotification("Missed Call", `You missed a call from ${from}.`);
            return;
        }
        if (NotificationUtils._isAndroid()) {
            window.MeshChatXAndroid.showMissedCallNotification("Missed Call", `You missed a call from ${from}.`);
            return;
        }
        Notification.requestPermission().then((result) => {
            if (result === "granted") {
                new window.Notification("Missed Call", {
                    body: `You missed a call from ${from}.`,
                    tag: "missed_call",
                });
            }
        });
    }

    static showNewVoicemailNotification(from: unknown): void {
        if (window.electron) {
            window.electron.showNotification("New Voicemail", `You have a new voicemail from ${from}.`);
            return;
        }
        if (NotificationUtils._isAndroid()) {
            window.MeshChatXAndroid.showNotification("New Voicemail", `You have a new voicemail from ${from}.`);
            return;
        }
        Notification.requestPermission().then((result) => {
            if (result === "granted") {
                new window.Notification("New Voicemail", {
                    body: `You have a new voicemail from ${from}.`,
                    tag: "new_voicemail",
                });
            }
        });
    }

    static showNewMessageNotification(
        from: unknown,
        content: unknown,
        silent = false,
        destinationHash: string | null = null
    ): void {
        if (!NotificationUtils.ownsOsMessageNotifications()) {
            return;
        }
        const body = from ? `${from}: ${content || "Sent a message."}` : "Someone sent you a message.";
        const hash = NotificationUtils._normalizeHash(destinationHash);

        if (window.electron) {
            if (typeof window.electron.showNotification === "function") {
                window.electron.showNotification("New Message", body, silent, hash || null);
            }
            return;
        }

        Notification.requestPermission().then((result) => {
            if (result !== "granted") {
                return;
            }
            const notification = new window.Notification("New Message", {
                body,
                tag: NotificationUtils._messageTag(hash),
                silent: Boolean(silent),
            });
            NotificationUtils._trackWebNotification(hash, notification);
            notification.onclose = () => {
                const key = hash || "__untagged__";
                const list = NotificationUtils._webMessageNotifications.get(key);
                if (!list) {
                    return;
                }
                const idx = list.indexOf(notification);
                if (idx >= 0) {
                    list.splice(idx, 1);
                }
                if (list.length === 0) {
                    NotificationUtils._webMessageNotifications.delete(key);
                }
            };
        });
    }

    /** Clear OS message notifications for a peer, or all when hash is empty. */
    static clearMessageNotifications(destinationHash?: string | null): void {
        const hash = NotificationUtils._normalizeHash(destinationHash);

        if (window.electron && typeof window.electron.closeMessageNotifications === "function") {
            window.electron.closeMessageNotifications(hash || null);
        }

        if (NotificationUtils._isAndroid()) {
            if (hash && typeof window.MeshChatXAndroid.cancelMessageNotifications === "function") {
                window.MeshChatXAndroid.cancelMessageNotifications(hash);
            } else if (!hash && typeof window.MeshChatXAndroid.cancelAllMessageNotifications === "function") {
                window.MeshChatXAndroid.cancelAllMessageNotifications();
            }
        }

        if (hash) {
            const list = NotificationUtils._webMessageNotifications.get(hash) || [];
            for (const n of list.slice()) {
                try {
                    n.close();
                } catch {
                    // ignore
                }
            }
            NotificationUtils._webMessageNotifications.delete(hash);
            return;
        }

        for (const [, list] of NotificationUtils._webMessageNotifications) {
            for (const n of list.slice()) {
                try {
                    n.close();
                } catch {
                    // ignore
                }
            }
        }
        NotificationUtils._webMessageNotifications.clear();
    }

    static clearAllMessageNotifications(): void {
        NotificationUtils.clearMessageNotifications(null);
    }

    /** Sync open peers + DND into the Android Python push bridge via Java. */
    static syncAndroidNotificationContext(hashes: string[] | null | undefined, dndEnabled = false): void {
        if (!NotificationUtils._isAndroid()) {
            return;
        }
        try {
            if (typeof window.MeshChatXAndroid.setOpenConversationHashes === "function") {
                const joined = (hashes || [])
                    .map((h) => NotificationUtils._normalizeHash(h))
                    .filter(Boolean)
                    .join(",");
                window.MeshChatXAndroid.setOpenConversationHashes(joined);
            }
            if (typeof window.MeshChatXAndroid.setDoNotDisturbEnabled === "function") {
                window.MeshChatXAndroid.setDoNotDisturbEnabled(Boolean(dndEnabled));
            }
        } catch (e) {
            console.error("Failed to sync Android notification context", e);
        }
    }

    static cancelIncomingCallNotification(): void {
        if (NotificationUtils._isAndroid()) {
            window.MeshChatXAndroid.cancelIncomingCallNotification();
        }
    }
}

export default NotificationUtils;
