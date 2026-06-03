package com.meshchatx;

import android.content.Context;
import android.content.SharedPreferences;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.channels.FileChannel;
import org.json.JSONObject;

/**
 * Resolves MeshChatX data roots on Android (app-internal vs app-specific external storage)
 * and runs one-shot copy migrations before the embedded Python server starts.
 */
public final class AndroidStorageManager {
    public static final String PREFS_NAME = "meshchatx";
    public static final String PREF_STORAGE_MODE = "android_storage_mode";
    public static final String PREF_SETUP_COMPLETED = "android_storage_setup_completed";
    public static final String PREF_PENDING_COPY_EXTERNAL = "android_storage_pending_copy_external";
    public static final String PREF_UPGRADE_PROMPT_VERSION = "android_storage_upgrade_prompt_version";

    public static final String MODE_INTERNAL = "internal";
    public static final String MODE_EXTERNAL = "external";
    public static final String MESHCHAT_DIR = "meshchatx";

    private AndroidStorageManager() {}

    public static SharedPreferences prefs(Context context) {
        return context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
    }

    public static File internalBaseDir(Context context) {
        return context.getFilesDir();
    }

    public static File externalBaseDir(Context context) {
        File external = context.getExternalFilesDir(null);
        return external != null ? external : context.getFilesDir();
    }

    public static File baseDirForMode(Context context, String mode) {
        if (MODE_EXTERNAL.equals(mode)) {
            return externalBaseDir(context);
        }
        return internalBaseDir(context);
    }

    public static File meshchatRoot(Context context, String mode) {
        return new File(baseDirForMode(context, mode), MESHCHAT_DIR);
    }

    public static String getConfiguredMode(Context context) {
        return prefs(context).getString(PREF_STORAGE_MODE, null);
    }

    public static void setConfiguredMode(Context context, String mode) {
        if (!MODE_INTERNAL.equals(mode) && !MODE_EXTERNAL.equals(mode)) {
            throw new IllegalArgumentException("Invalid storage mode: " + mode);
        }
        prefs(context).edit().putString(PREF_STORAGE_MODE, mode).apply();
    }

    public static void markSetupCompleted(Context context) {
        prefs(context).edit().putBoolean(PREF_SETUP_COMPLETED, true).apply();
    }

    public static boolean isSetupCompleted(Context context) {
        return prefs(context).getBoolean(PREF_SETUP_COMPLETED, false);
    }

    public static void scheduleCopyToExternal(Context context) {
        prefs(context)
            .edit()
            .putBoolean(PREF_PENDING_COPY_EXTERNAL, true)
            .apply();
    }

    public static boolean isPendingCopyToExternal(Context context) {
        return prefs(context).getBoolean(PREF_PENDING_COPY_EXTERNAL, false);
    }

    public static void clearPendingCopyToExternal(Context context) {
        prefs(context).edit().remove(PREF_PENDING_COPY_EXTERNAL).apply();
    }

    public static void markUpgradePromptSeen(Context context, int versionCode) {
        prefs(context).edit().putInt(PREF_UPGRADE_PROMPT_VERSION, versionCode).apply();
    }

    public static int getUpgradePromptSeenVersion(Context context) {
        return prefs(context).getInt(PREF_UPGRADE_PROMPT_VERSION, 0);
    }

    public static boolean hasMeshchatData(File root) {
        if (root == null || !root.isDirectory()) {
            return false;
        }
        File storage = new File(root, "storage");
        if (directoryHasEntries(storage)) {
            return true;
        }
        File reticulum = new File(root, "reticulum");
        if (directoryHasEntries(reticulum)) {
            return true;
        }
        return false;
    }

    private static boolean directoryHasEntries(File dir) {
        if (!dir.isDirectory()) {
            return false;
        }
        String[] names = dir.list();
        return names != null && names.length > 0;
    }

    public static boolean hasInternalMeshchatData(Context context) {
        return hasMeshchatData(meshchatRoot(context, MODE_INTERNAL));
    }

    public static boolean hasExternalMeshchatData(Context context) {
        return hasMeshchatData(meshchatRoot(context, MODE_EXTERNAL));
    }

    /**
     * Active mode used to start the embedded server on this process launch.
     */
    public static String resolveActiveMode(Context context) {
        String configured = getConfiguredMode(context);
        if (configured != null) {
            return configured;
        }
        if (hasInternalMeshchatData(context)) {
            return MODE_INTERNAL;
        }
        return MODE_EXTERNAL;
    }

    public static File resolveActiveBaseDir(Context context) {
        return baseDirForMode(context, resolveActiveMode(context));
    }

    /**
     * Copy internal meshchatx tree to external when requested, then pin mode to external.
     */
    public static void runPendingMigration(Context context) throws IOException {
        if (!isPendingCopyToExternal(context)) {
            return;
        }
        File src = meshchatRoot(context, MODE_INTERNAL);
        File dst = meshchatRoot(context, MODE_EXTERNAL);
        if (hasMeshchatData(src)) {
            copyDirectory(src, dst);
        }
        setConfiguredMode(context, MODE_EXTERNAL);
        markSetupCompleted(context);
        clearPendingCopyToExternal(context);
        int versionCode = readAppVersionCode(context);
        if (versionCode > 0) {
            markUpgradePromptSeen(context, versionCode);
        }
    }

    private static int readAppVersionCode(Context context) {
        try {
            return context.getPackageManager().getPackageInfo(context.getPackageName(), 0).versionCode;
        } catch (Exception e) {
            return 0;
        }
    }

    public static boolean externalStorageAvailable(Context context) {
        File external = context.getExternalFilesDir(null);
        return external != null;
    }

    public static boolean needsSetupChoice(Context context) {
        if (getConfiguredMode(context) != null) {
            return false;
        }
        return !isSetupCompleted(context) && !hasInternalMeshchatData(context);
    }

    public static boolean needsUpgradePrompt(Context context, int appVersionCode) {
        if (getConfiguredMode(context) != null) {
            return false;
        }
        if (!hasInternalMeshchatData(context)) {
            return false;
        }
        if (isPendingCopyToExternal(context)) {
            return false;
        }
        return getUpgradePromptSeenVersion(context) < appVersionCode;
    }

    public static void keepInternalAndDismissUpgrade(Context context, int appVersionCode) {
        setConfiguredMode(context, MODE_INTERNAL);
        markSetupCompleted(context);
        markUpgradePromptSeen(context, appVersionCode);
    }

    public static String statusJson(Context context, int appVersionCode) throws Exception {
        String configured = getConfiguredMode(context);
        String active = resolveActiveMode(context);
        JSONObject json = new JSONObject();
        json.put("platform", "android");
        json.put("configured_mode", configured == null ? JSONObject.NULL : configured);
        json.put("active_mode", active);
        json.put("internal_path", meshchatRoot(context, MODE_INTERNAL).getAbsolutePath());
        json.put("external_path", meshchatRoot(context, MODE_EXTERNAL).getAbsolutePath());
        json.put("active_path", meshchatRoot(context, active).getAbsolutePath());
        json.put("has_internal_data", hasInternalMeshchatData(context));
        json.put("has_external_data", hasExternalMeshchatData(context));
        json.put("needs_setup_choice", needsSetupChoice(context));
        json.put("needs_upgrade_prompt", needsUpgradePrompt(context, appVersionCode));
        json.put("pending_copy", isPendingCopyToExternal(context));
        json.put("external_available", externalStorageAvailable(context));
        json.put("setup_completed", isSetupCompleted(context));
        return json.toString();
    }

    public static void copyDirectory(File source, File target) throws IOException {
        if (!source.exists()) {
            return;
        }
        if (source.isFile()) {
            copyFile(source, target);
            return;
        }
        if (!source.isDirectory()) {
            return;
        }
        if (!target.exists() && !target.mkdirs()) {
            throw new IOException("mkdirs failed: " + target.getAbsolutePath());
        }
        File[] children = source.listFiles();
        if (children == null) {
            return;
        }
        for (File child : children) {
            copyDirectory(child, new File(target, child.getName()));
        }
    }

    public static void copyFile(File source, File target) throws IOException {
        File parent = target.getParentFile();
        if (parent != null && !parent.exists() && !parent.mkdirs()) {
            throw new IOException("mkdirs failed: " + parent.getAbsolutePath());
        }
        try (FileInputStream in = new FileInputStream(source);
            FileOutputStream out = new FileOutputStream(target, false);
            FileChannel inChannel = in.getChannel();
            FileChannel outChannel = out.getChannel()) {
            long size = inChannel.size();
            long transferred = 0L;
            while (transferred < size) {
                transferred += inChannel.transferTo(transferred, size - transferred, outChannel);
            }
            outChannel.force(true);
        }
    }
}
