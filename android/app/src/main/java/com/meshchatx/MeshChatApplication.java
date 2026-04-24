package com.meshchatx;

import android.app.Application;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.content.Context;
import android.os.Build;

import com.chaquo.python.android.PyApplication;

public class MeshChatApplication extends PyApplication {
    public static final String CHANNEL_ID_MESSAGES = "meshchatx_messages";
    public static final String CHANNEL_ID_BACKGROUND = "meshchatx_background";

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
            NotificationManager.IMPORTANCE_DEFAULT
        );
        messages.setDescription(getString(R.string.notification_channel_messages_desc));
        nm.createNotificationChannel(messages);
    }
}
