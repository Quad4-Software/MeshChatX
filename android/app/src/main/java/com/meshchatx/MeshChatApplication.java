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
        // PyApplication sets up native library paths. Preload Codec2 after that
        // so System.loadLibrary and absolute System.load can resolve jniLibs.
        super.onCreate();
        appContext = getApplicationContext();
        preloadCodec2NativeLibrary();
        createNotificationChannels();
    }

    private void preloadCodec2NativeLibrary() {
        String nativeDir = null;
        try {
            nativeDir = getApplicationInfo().nativeLibraryDir;
            if (nativeDir != null && !nativeDir.isEmpty()) {
                android.system.Os.setenv("MESHCHAT_NATIVE_LIB_DIR", nativeDir, true);
            }
        } catch (Exception e) {
            android.util.Log.w(
                "MeshChatX",
                "Could not set MESHCHAT_NATIVE_LIB_DIR: " + e.getMessage()
            );
        }
        java.io.File absoluteLib = null;
        if (nativeDir != null && !nativeDir.isEmpty()) {
            absoluteLib = new java.io.File(nativeDir, "libcodec2.so");
            if (absoluteLib.isFile()) {
                try {
                    android.system.Os.setenv(
                        "MESHCHAT_LIBCODEC2_PATH",
                        absoluteLib.getAbsolutePath(),
                        true
                    );
                } catch (Exception e) {
                    android.util.Log.w(
                        "MeshChatX",
                        "Could not set MESHCHAT_LIBCODEC2_PATH: " + e.getMessage()
                    );
                }
            } else {
                absoluteLib = null;
            }
        }
        try {
            System.loadLibrary("codec2");
            android.util.Log.i("MeshChatX", "Loaded libcodec2 via System.loadLibrary");
        } catch (UnsatisfiedLinkError e) {
            android.util.Log.w(
                "MeshChatX",
                "System.loadLibrary(codec2) failed before Python start: " + e.getMessage()
            );
        }
        // Absolute System.load helps some linkers expose the SONAME for later
        // Python ctypes / extension dlopen even after loadLibrary succeeded.
        if (absoluteLib == null) {
            return;
        }
        try {
            System.load(absoluteLib.getAbsolutePath());
            android.util.Log.i(
                "MeshChatX",
                "Loaded libcodec2 via System.load(" + absoluteLib.getAbsolutePath() + ")"
            );
        } catch (UnsatisfiedLinkError e) {
            android.util.Log.w(
                "MeshChatX",
                "System.load(libcodec2.so) failed: " + e.getMessage()
            );
        }
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
