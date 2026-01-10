class NotificationUtils {
    static showIncomingCallNotification() {
        if (window.electron) {
            window.electron.showNotification("Incoming Call", "Someone is calling you.");
            return;
        }
        Notification.requestPermission().then((result) => {
            if (result === "granted") {
                new window.Notification("Incoming Call", {
                    body: "Someone is calling you.",
                    tag: "incoming_telephone_call", // only ever show one incoming call notification at a time
                });
            }
        });
    }

    static showMissedCallNotification(from) {
        if (window.electron) {
            window.electron.showNotification("Missed Call", `You missed a call from ${from}.`);
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
        Notification.requestPermission().then((result) => {
            if (result === "granted") {
                new window.Notification("New Message", {
                    body: from ? `${from}: ${content || "Sent a message."}` : "Someone sent you a message.",
                    tag: "new_message", // only ever show one new message notification at a time
                });
            }
        });
    }
}

export default NotificationUtils;
