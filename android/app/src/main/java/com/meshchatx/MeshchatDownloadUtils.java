package com.meshchatx;

final class MeshchatDownloadUtils {

    private static final int DOWNLOAD_NOTIFICATION_ID_BASE = 0x60000;
    private static final java.util.concurrent.ConcurrentHashMap<String, Integer> downloadNotificationIds =
        new java.util.concurrent.ConcurrentHashMap<>();
    private static final java.util.concurrent.atomic.AtomicInteger nextDownloadNotificationId =
        new java.util.concurrent.atomic.AtomicInteger(DOWNLOAD_NOTIFICATION_ID_BASE);

    private MeshchatDownloadUtils() {}

    /**
     * Maps a string download id to a stable notification id so progress updates
     * replace each other and the finished state reuses the same slot.
     */
    static int notificationIdFor(String downloadId) {
        String key = downloadId != null ? downloadId : "download";
        return downloadNotificationIds.computeIfAbsent(key, k -> nextDownloadNotificationId.getAndIncrement());
    }

    /**
     * Produces a filename safe for writing into app storage / MediaStore.
     */
    static String sanitizeFileName(String name) {
        if (name == null || name.isEmpty()) {
            return "download.bin";
        }
        int slash = Math.max(name.lastIndexOf('/'), name.lastIndexOf('\\'));
        String base = slash >= 0 ? name.substring(slash + 1) : name;
        if (base.isEmpty()) {
            return "download.bin";
        }
        // Hyphen must be first or last in the class so it is literal, not a range (space..hyphen would include '*').
        base = base.replaceAll("[^A-Za-z0-9._ \\-]+", "_").trim();
        if (base.isEmpty()) {
            return "download.bin";
        }
        if (base.length() > 120) {
            base = base.substring(0, 120);
        }
        return base;
    }
}
