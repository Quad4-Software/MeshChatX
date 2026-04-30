package com.meshchatx;

import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.text.TextUtils;

import androidx.annotation.Nullable;
import androidx.core.app.NotificationCompat;
import androidx.core.app.Person;

public final class AndroidNotificationBridge {
    private static final int NOTIFY_BASE_ID = 0x4d434800;
    public static final int INCOMING_CALL_NOTIFICATION_ID = 0x4d434900;

    public static final String ACTION_CALL_ANSWER = "com.meshchatx.action.CALL_ANSWER";
    public static final String ACTION_CALL_DECLINE = "com.meshchatx.action.CALL_DECLINE";
    public static final String ACTION_CALL_OPEN = "com.meshchatx.action.CALL_OPEN";

    private static final int REQ_CALL_OPEN = 0x4c31;
    private static final int REQ_CALL_FULL = 0x4c32;
    private static final int REQ_CALL_ANSWER = 0x4c33;
    private static final int REQ_CALL_DECLINE = 0x4c34;

    private AndroidNotificationBridge() {
    }

    public static void showInboundMessage(String title, String body, @Nullable String dedupeHex) {
        Context ctx = MeshChatApplication.getAppContext();
        if (ctx == null) {
            return;
        }
        String safeTitle = TextUtils.isEmpty(title) ? ctx.getString(R.string.app_name) : title;
        String safeBody = TextUtils.isEmpty(body) ? ctx.getString(R.string.notification_new_message_fallback) : body;

        new Handler(Looper.getMainLooper()).post(() -> postInboundMessage(ctx, safeTitle, safeBody, dedupeHex));
    }

    public static void showIncomingCall(String callerName, @Nullable String dedupeHex) {
        Context ctx = MeshChatApplication.getAppContext();
        if (ctx == null) {
            return;
        }
        String name = (callerName == null) ? "Mesh" : callerName.trim();
        if (name.isEmpty()) {
            name = "Mesh";
        }
        final String displayName = name;
        new Handler(Looper.getMainLooper()).post(() -> postIncomingCall(ctx, displayName, dedupeHex));
    }

    public static void showMissedCall(String title, String body, @Nullable String dedupeHex) {
        Context ctx = MeshChatApplication.getAppContext();
        if (ctx == null) {
            return;
        }
        String safeTitle = TextUtils.isEmpty(title) ? ctx.getString(R.string.notification_missed_call_label) : title;
        String safeBody = TextUtils.isEmpty(body) ? ctx.getString(R.string.app_name) : body;
        new Handler(Looper.getMainLooper()).post(() -> postMissedCall(ctx, safeTitle, safeBody, dedupeHex));
    }

    public static void cancelIncomingCallNotification() {
        Context ctx = MeshChatApplication.getAppContext();
        if (ctx == null) {
            return;
        }
        new Handler(Looper.getMainLooper()).post(
            () -> {
                NotificationManager nm = ctx.getSystemService(NotificationManager.class);
                if (nm == null) {
                    return;
                }
                try {
                    nm.cancel(INCOMING_CALL_NOTIFICATION_ID);
                } catch (Exception ignored) {
                }
            }
        );
    }

    private static Intent callIntent(Context ctx, String action) {
        Intent i = new Intent(ctx, MainActivity.class);
        i.setAction(action);
        i.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        return i;
    }

    private static void postIncomingCall(Context ctx, String callerName, @Nullable String dedupeHex) {
        NotificationManager nm = ctx.getSystemService(NotificationManager.class);
        if (nm == null) {
            return;
        }

        PendingIntent open = PendingIntent.getActivity(
            ctx,
            REQ_CALL_OPEN,
            callIntent(ctx, ACTION_CALL_OPEN),
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );
        PendingIntent full = PendingIntent.getActivity(
            ctx,
            REQ_CALL_FULL,
            callIntent(ctx, ACTION_CALL_OPEN),
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );
        PendingIntent answer = PendingIntent.getActivity(
            ctx,
            REQ_CALL_ANSWER,
            callIntent(ctx, ACTION_CALL_ANSWER),
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );
        PendingIntent decline = PendingIntent.getActivity(
            ctx,
            REQ_CALL_DECLINE,
            callIntent(ctx, ACTION_CALL_DECLINE),
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );

        Person person = new Person.Builder().setName(callerName).setImportant(true).build();
        String incomingLabel = ctx.getString(R.string.notification_incoming_call_label, callerName);

        NotificationCompat.Builder b = new NotificationCompat.Builder(ctx, MeshChatApplication.CHANNEL_ID_CALLS)
            .setSmallIcon(R.drawable.ic_stat_meshchatx)
            .setOngoing(true)
            .setAutoCancel(false)
            .setContentIntent(open)
            .setCategory(NotificationCompat.CATEGORY_CALL)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .setContentTitle(callerName)
            .setContentText(ctx.getString(R.string.notification_incoming_call_tap));

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            b.setStyle(
                NotificationCompat.CallStyle.forIncomingCall(
                    person,
                    decline,
                    answer
                )
            );
        } else {
            b.setStyle(new NotificationCompat.BigTextStyle().bigText(incomingLabel));
            b.setContentText(ctx.getString(R.string.notification_incoming_call_tap));
            b.addAction(0, ctx.getString(R.string.notification_call_decline), decline);
            b.addAction(0, ctx.getString(R.string.notification_call_answer), answer);
        }
        b.setOnlyAlertOnce(false);
        b.setTimeoutAfter(120_000L);

        try {
            b.setFullScreenIntent(full, true);
        } catch (Exception ignored) {
        }

        try {
            nm.notify(INCOMING_CALL_NOTIFICATION_ID, b.build());
        } catch (SecurityException ignored) {
        } catch (Exception ignored) {
        }
    }

    private static int missedCallNotificationId(@Nullable String dedupeHex) {
        if (dedupeHex != null && dedupeHex.length() >= 8) {
            try {
                return NOTIFY_BASE_ID + 0x1000 + (int) (
                    Long.parseLong(
                        dedupeHex.substring(0, Math.min(8, dedupeHex.length())), 16) & 0x7fff_ffff);
            } catch (NumberFormatException ignored) {
                return NOTIFY_BASE_ID + 0x1000 + (dedupeHex.hashCode() & 0x7fff_ffff);
            }
        }
        return NOTIFY_BASE_ID + 0x3fff;
    }

    private static void postMissedCall(
        Context ctx,
        String title,
        String body,
        @Nullable String dedupeHex
    ) {
        NotificationManager nm = ctx.getSystemService(NotificationManager.class);
        if (nm == null) {
            return;
        }

        Intent open = new Intent(ctx, MainActivity.class);
        open.setAction(ACTION_CALL_OPEN);
        open.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        PendingIntent pi = PendingIntent.getActivity(
            ctx,
            REQ_CALL_OPEN,
            open,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );

        int id = missedCallNotificationId(dedupeHex);
        NotificationCompat.Builder b = new NotificationCompat.Builder(ctx, MeshChatApplication.CHANNEL_ID_CALLS)
            .setSmallIcon(R.drawable.ic_stat_meshchatx)
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(new NotificationCompat.BigTextStyle().bigText(body))
            .setContentIntent(pi)
            .setAutoCancel(true)
            .setCategory(NotificationCompat.CATEGORY_MISSED_CALL)
            .setVisibility(NotificationCompat.VISIBILITY_PRIVATE);
        b.setDefaults(NotificationCompat.DEFAULT_ALL);

        try {
            nm.notify(id, b.build());
        } catch (SecurityException ignored) {
        }
    }

    private static void postInboundMessage(Context ctx, String title, String body, @Nullable String dedupeHex) {
        NotificationManager nm = ctx.getSystemService(NotificationManager.class);
        if (nm == null) {
            return;
        }

        Intent open = new Intent(ctx, MainActivity.class);
        open.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        PendingIntent pi = PendingIntent.getActivity(
            ctx,
            0,
            open,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );

        int id = NOTIFY_BASE_ID;
        if (dedupeHex != null && dedupeHex.length() >= 8) {
            try {
                id = NOTIFY_BASE_ID
                    + (int) (Long.parseLong(
                        dedupeHex.substring(0, Math.min(8, dedupeHex.length())), 16) & 0x7fff_ffff);
            } catch (NumberFormatException ignored) {
                id = NOTIFY_BASE_ID + (dedupeHex.hashCode() & 0x7fff_ffff);
            }
        }

        try {
            nm.cancel(id);
        } catch (Exception ignored) {
        }

        NotificationCompat.Builder b = new NotificationCompat.Builder(ctx, MeshChatApplication.CHANNEL_ID_MESSAGES)
            .setSmallIcon(R.drawable.ic_stat_meshchatx)
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(new NotificationCompat.BigTextStyle().bigText(body))
            .setContentIntent(pi)
            .setAutoCancel(true)
            .setCategory(NotificationCompat.CATEGORY_MESSAGE)
            .setVisibility(NotificationCompat.VISIBILITY_PRIVATE)
            .setDefaults(NotificationCompat.DEFAULT_ALL)
            .setOnlyAlertOnce(false);

        try {
            nm.notify(id, b.build());
        } catch (SecurityException ignored) {
        }
    }
}
