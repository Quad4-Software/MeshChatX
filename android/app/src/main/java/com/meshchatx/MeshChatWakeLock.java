package com.meshchatx;

import android.content.Context;
import android.os.PowerManager;

import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Shared partial wake lock for long-running transfers. Reference counted by
 * caller tag so overlapping downloads keep the CPU awake until the last one
 * ends. A safety timeout bounds the hold if a caller never releases.
 */
final class MeshChatWakeLock {

    private static final long SAFETY_TIMEOUT_MS = 30L * 60L * 1000L;
    private static final Set<String> holders = ConcurrentHashMap.newKeySet();
    private static PowerManager.WakeLock wakeLock;

    private MeshChatWakeLock() {}

    static synchronized void acquire(Context context, String tag) {
        holders.add(tag);
        Context appContext = context.getApplicationContext();
        if (wakeLock == null) {
            PowerManager powerManager = (PowerManager) appContext.getSystemService(Context.POWER_SERVICE);
            if (powerManager == null) {
                return;
            }
            wakeLock = powerManager.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "meshchatx:downloads");
            wakeLock.setReferenceCounted(false);
        }
        if (!wakeLock.isHeld()) {
            wakeLock.acquire(SAFETY_TIMEOUT_MS);
        }
    }

    static synchronized void release(String tag) {
        holders.remove(tag);
        if (holders.isEmpty() && wakeLock != null && wakeLock.isHeld()) {
            wakeLock.release();
        }
    }
}
