class NotificationUtils {
    static _isAndroid() {
        return Boolean(
            typeof window !== "undefined" &&
            window.MeshChatXAndroid &&
            typeof window.MeshChatXAndroid.getPlatform === "function" &&
            window.MeshChatXAndroid.getPlatform() === "android"
        );
    }

    static showIncomingCallNotification(callerName) {
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

    static showMissedCallNotification(from) {
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

    static showNewVoicemailNotification(from) {
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

    static showNewMessageNotification(from, content) {
        if (window.electron) {
            window.electron.showNotification(
                "New Message",
                from ? `${from}: ${content || "Sent a message."}` : "Someone sent you a message."
            );
            return;
        }
        if (NotificationUtils._isAndroid()) {
            window.MeshChatXAndroid.showNotification(
                "New Message",
                from ? `${from}: ${content || "Sent a message."}` : "Someone sent you a message."
            );
            return;
        }
        Notification.requestPermission().then((result) => {
            if (result === "granted") {
                new window.Notification("New Message", {
                    body: from ? `${from}: ${content || "Sent a message."}` : "Someone sent you a message.",
                    tag: "new_message",
                });
            }
        });
    }

    static cancelIncomingCallNotification() {
        if (NotificationUtils._isAndroid()) {
            window.MeshChatXAndroid.cancelIncomingCallNotification();
        }
    }
}

export default NotificationUtils;
