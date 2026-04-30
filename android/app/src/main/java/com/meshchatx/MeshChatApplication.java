package com.meshchatx;

import android.app.Application;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.content.Context;
import android.media.AudioAttributes;
import android.media.RingtoneManager;
import android.net.Uri;
import android.os.Build;
import android.provider.Settings;

import com.chaquo.python.android.PyApplication;

public class MeshChatApplication extends PyApplication {
    public static final String CHANNEL_ID_MESSAGES = "meshchatx_messages";
    public static final String CHANNEL_ID_BACKGROUND = "meshchatx_background";
    public static final String CHANNEL_ID_CALLS = "meshchatx_calls";

    private static volatile Context appContext;

    public static Context getAppContext() {
        return appContext;
    }

    @Override
    public void onCreate() {
        super.onCreate();
        appContext = getApplicationContext();
        createNotificationChannels();
    }

    private void createNotificationChannels() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
            return;
        }
        NotificationManager nm = getSystemService(NotificationManager.class);
        if (nm == null) {
            return;
        }

        NotificationChannel background = new NotificationChannel(
            CHANNEL_ID_BACKGROUND,
            getString(R.string.notification_channel_background_name),
            NotificationManager.IMPORTANCE_LOW
        );
        background.setDescription(getString(R.string.notification_channel_background_desc));
        nm.createNotificationChannel(background);

        NotificationChannel messages = new NotificationChannel(
            CHANNEL_ID_MESSAGES,
            getString(R.string.notification_channel_messages_name),
            NotificationManager.IMPORTANCE_HIGH
        );
        messages.setDescription(getString(R.string.notification_channel_messages_desc));
        nm.createNotificationChannel(messages);

        Uri ringUri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_RINGTONE);
        if (ringUri == null) {
            ringUri = Settings.System.DEFAULT_RINGTONE_URI;
        }
        NotificationChannel calls = new NotificationChannel(
            CHANNEL_ID_CALLS,
            getString(R.string.notification_channel_calls_name),
            NotificationManager.IMPORTANCE_HIGH
        );
        calls.setDescription(getString(R.string.notification_channel_calls_desc));
        calls.setLockscreenVisibility(Notification.VISIBILITY_PUBLIC);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            calls.setBypassDnd(true);
        }
        if (ringUri != null) {
            calls.setSound(
                ringUri,
                new AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_NOTIFICATION_RINGTONE)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                    .build()
            );
        }
        long[] pattern = new long[] {0, 400, 200, 400, 200, 600};
        try {
            calls.setVibrationPattern(pattern);
        } catch (Exception ignored) {
        }
        nm.createNotificationChannel(calls);
    }
}
