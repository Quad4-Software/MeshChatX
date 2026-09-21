package com.meshchatx;

import android.app.DownloadManager;
import android.app.Notification;
import android.app.PendingIntent;
import android.content.ContentResolver;
import android.content.Context;
import android.content.Intent;
import android.app.NotificationManager;
import android.net.Uri;

import androidx.core.app.NotificationCompat;
import androidx.core.app.NotificationManagerCompat;

/**
 * Download progress and completion notifications.
 * Callers pass a stable download id; progress updates reuse the same
 * notification slot and are replaced by the finished or failed state.
 * Safe to call from any thread and safe when notifications are denied.
 */
final class DownloadNotifications {

    private DownloadNotifications() {}

    static void showProgress(Context context, String downloadId, String fileName, int percent) {
        Context appContext = context.getApplicationContext();
        NotificationManager manager = (NotificationManager) appContext.getSystemService(Context.NOTIFICATION_SERVICE);
        if (manager == null) {
            return;
        }
        NotificationCompat.Builder builder =
            new NotificationCompat.Builder(appContext, MeshChatApplication.CHANNEL_ID_DOWNLOADS)
                .setSmallIcon(R.drawable.ic_stat_meshchatx)
                .setContentTitle(fileName)
                .setOngoing(true)
                .setOnlyAlertOnce(true)
                .setCategory(NotificationCompat.CATEGORY_PROGRESS);
        if (percent >= 0) {
            int clamped = Math.max(0, Math.min(100, percent));
            builder.setContentText(appContext.getString(R.string.download_notification_progress, clamped));
            builder.setProgress(100, clamped, false);
        } else {
            builder.setContentText(appContext.getString(R.string.download_notification_running));
            builder.setProgress(0, 0, true);
        }
        notifyIfPermitted(appContext, manager, MeshchatDownloadUtils.notificationIdFor(downloadId), builder.build());
    }

    static void showFinished(Context context, String downloadId, String fileName, Uri contentUri) {
        Context appContext = context.getApplicationContext();
        NotificationManager manager = (NotificationManager) appContext.getSystemService(Context.NOTIFICATION_SERVICE);
        if (manager == null) {
            return;
        }
        NotificationCompat.Builder builder =
            new NotificationCompat.Builder(appContext, MeshChatApplication.CHANNEL_ID_DOWNLOADS)
                .setSmallIcon(R.drawable.ic_stat_meshchatx)
                .setContentTitle(fileName)
                .setContentText(appContext.getString(R.string.download_notification_complete))
                .setOngoing(false)
                .setAutoCancel(true)
                .setOnlyAlertOnce(true)
                .setCategory(NotificationCompat.CATEGORY_STATUS);
        int notificationId = MeshchatDownloadUtils.notificationIdFor(downloadId);
        PendingIntent openIntent = buildOpenIntent(appContext, notificationId, contentUri, fileName);
        if (openIntent != null) {
            builder.setContentIntent(openIntent);
        }
        notifyIfPermitted(appContext, manager, notificationId, builder.build());
    }

    static void showFailed(Context context, String downloadId, String fileName) {
        Context appContext = context.getApplicationContext();
        NotificationManager manager = (NotificationManager) appContext.getSystemService(Context.NOTIFICATION_SERVICE);
        if (manager == null) {
            return;
        }
        Notification notification =
            new NotificationCompat.Builder(appContext, MeshChatApplication.CHANNEL_ID_DOWNLOADS)
                .setSmallIcon(R.drawable.ic_stat_meshchatx)
                .setContentTitle(fileName)
                .setContentText(appContext.getString(R.string.download_notification_failed))
                .setOngoing(false)
                .setAutoCancel(true)
                .setOnlyAlertOnce(true)
                .setCategory(NotificationCompat.CATEGORY_STATUS)
                .build();
        notifyIfPermitted(appContext, manager, MeshchatDownloadUtils.notificationIdFor(downloadId), notification);
    }

    static void cancel(Context context, String downloadId) {
        Context appContext = context.getApplicationContext();
        NotificationManager manager = (NotificationManager) appContext.getSystemService(Context.NOTIFICATION_SERVICE);
        if (manager != null) {
            manager.cancel(MeshchatDownloadUtils.notificationIdFor(downloadId));
        }
    }

    private static PendingIntent buildOpenIntent(Context context, int requestCode, Uri uri, String fileName) {
        Intent intent = null;
        if (uri != null && ContentResolver.SCHEME_CONTENT.equals(uri.getScheme())) {
            Intent view = new Intent(Intent.ACTION_VIEW);
            String mime = android.webkit.MimeTypeMap.getSingleton().getMimeTypeFromExtension(extensionOf(fileName));
            view.setDataAndType(uri, mime != null ? mime : "application/octet-stream");
            view.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            if (view.resolveActivity(context.getPackageManager()) != null) {
                intent = view;
            }
        }
        if (intent == null) {
            Intent downloads = new Intent(DownloadManager.ACTION_VIEW_DOWNLOADS);
            if (downloads.resolveActivity(context.getPackageManager()) != null) {
                intent = downloads;
            }
        }
        if (intent == null) {
            return null;
        }
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        return PendingIntent.getActivity(
            context,
            requestCode,
            intent,
            PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT
        );
    }

    private static String extensionOf(String fileName) {
        if (fileName == null) {
            return "";
        }
        int dot = fileName.lastIndexOf('.');
        return dot >= 0 && dot < fileName.length() - 1 ? fileName.substring(dot + 1) : "";
    }

    private static void notifyIfPermitted(
        Context appContext,
        NotificationManager manager,
        int notificationId,
        Notification notification
    ) {
        if (NotificationManagerCompat.from(appContext).areNotificationsEnabled()) {
            manager.notify(notificationId, notification);
        }
    }
}
