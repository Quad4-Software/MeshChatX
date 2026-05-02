package com.meshchatx;

final class MeshchatDownloadUtils {

    private MeshchatDownloadUtils() {}

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
        base = base.replaceAll("[^A-Za-z0-9._ -]+", "_").trim();
        if (base.isEmpty()) {
            return "download.bin";
        }
        if (base.length() > 120) {
            base = base.substring(0, 120);
        }
        return base;
    }
}
