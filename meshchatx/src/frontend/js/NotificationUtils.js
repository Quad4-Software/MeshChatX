class NotificationUtils {
    static showIncomingCallNotification() {
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
        Notification.requestPermission().then((result) => {
            if (result === "granted") {
                new window.Notification("New Voicemail", {
                    body: `You have a new voicemail from ${from}.`,
                    tag: "new_voicemail",
                });
            }
        });
    }

    static showNewMessageNotification() {
        Notification.requestPermission().then((result) => {
            if (result === "granted") {
                new window.Notification("New Message", {
                    body: "Someone sent you a message.",
                    tag: "new_message", // only ever show one new message notification at a time
                });
            }
        });
    }
}

export default NotificationUtils;
