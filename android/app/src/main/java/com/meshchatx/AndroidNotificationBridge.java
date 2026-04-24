package com.meshchatx;

import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.os.Handler;
import android.os.Looper;
import android.text.TextUtils;

import androidx.annotation.Nullable;
import androidx.core.app.NotificationCompat;

public final class AndroidNotificationBridge {
    private static final int NOTIFY_BASE_ID = 0x4d434800;

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

        NotificationCompat.Builder b = new NotificationCompat.Builder(ctx, MeshChatApplication.CHANNEL_ID_MESSAGES)
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(new NotificationCompat.BigTextStyle().bigText(body))
            .setContentIntent(pi)
            .setAutoCancel(true)
            .setCategory(NotificationCompat.CATEGORY_MESSAGE)
            .setVisibility(NotificationCompat.VISIBILITY_PRIVATE);

        int id = NOTIFY_BASE_ID;
        if (dedupeHex != null && dedupeHex.length() >= 8) {
            try {
                id = NOTIFY_BASE_ID + (int) (Long.parseLong(dedupeHex.substring(0, Math.min(8, dedupeHex.length())), 16) & 0x7fff_ffff);
            } catch (NumberFormatException ignored) {
                id = NOTIFY_BASE_ID + (dedupeHex.hashCode() & 0x7fff_ffff);
            }
        }

        try {
            nm.notify(id, b.build());
        } catch (SecurityException ignored) {
        }
    }
}
