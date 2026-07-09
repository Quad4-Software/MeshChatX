package com.meshchatx;

import android.content.Context;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.os.Build;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;

/**
 * Formats Android startup / backend failure messages with app and device diagnostics
 * so crash reports from older builds are easier to triage.
 */
public final class StartupErrorReport {

    private StartupErrorReport() {}

    public static final class Diagnostics {
        public final String appVersionName;
        public final String appVersionCode;
        public final String androidRelease;
        public final int sdkInt;
        public final String manufacturer;
        public final String model;
        public final String device;

        public Diagnostics(
            @Nullable String appVersionName,
            @Nullable String appVersionCode,
            @Nullable String androidRelease,
            int sdkInt,
            @Nullable String manufacturer,
            @Nullable String model,
            @Nullable String device
        ) {
            this.appVersionName = appVersionName;
            this.appVersionCode = appVersionCode;
            this.androidRelease = androidRelease;
            this.sdkInt = sdkInt;
            this.manufacturer = manufacturer;
            this.model = model;
            this.device = device;
        }
    }

    @NonNull
    public static Diagnostics collect(@NonNull Context context) {
        String versionName = "unknown";
        String versionCode = "unknown";
        try {
            PackageInfo pi = context
                .getPackageManager()
                .getPackageInfo(context.getPackageName(), 0);
            if (pi.versionName != null && !pi.versionName.isEmpty()) {
                versionName = pi.versionName;
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                versionCode = Long.toString(pi.getLongVersionCode());
            } else {
                versionCode = Integer.toString(pi.versionCode);
            }
        } catch (PackageManager.NameNotFoundException ignored) {
        }
        return new Diagnostics(
            versionName,
            versionCode,
            Build.VERSION.RELEASE,
            Build.VERSION.SDK_INT,
            Build.MANUFACTURER,
            Build.MODEL,
            Build.DEVICE
        );
    }

    @NonNull
    public static String format(
        @NonNull String title,
        @Nullable String detail,
        @NonNull Diagnostics diagnostics
    ) {
        StringBuilder sb = new StringBuilder();
        sb.append(title == null ? "MeshChatX error" : title.trim());
        sb.append('\n');
        sb.append(formatDiagnosticsBlock(diagnostics));
        if (detail != null) {
            String trimmed = detail.trim();
            if (!trimmed.isEmpty()) {
                sb.append("\n\n");
                sb.append(trimmed);
            }
        }
        return sb.toString();
    }

    @NonNull
    public static String formatDiagnosticsBlock(@NonNull Diagnostics diagnostics) {
        StringBuilder sb = new StringBuilder();
        sb.append("App: ");
        sb.append(safe(diagnostics.appVersionName, "unknown"));
        String code = safe(diagnostics.appVersionCode, "");
        if (!code.isEmpty() && !"unknown".equals(code)) {
            sb.append(" (").append(code).append(')');
        }
        sb.append('\n');
        sb.append("Android: ");
        sb.append(safe(diagnostics.androidRelease, "unknown"));
        if (diagnostics.sdkInt > 0) {
            sb.append(" (API ").append(diagnostics.sdkInt).append(')');
        }
        sb.append('\n');
        sb.append("Device: ");
        String manufacturer = safe(diagnostics.manufacturer, "");
        String model = safe(diagnostics.model, "");
        if (!manufacturer.isEmpty() && !model.isEmpty()) {
            sb.append(manufacturer).append(' ').append(model);
        } else if (!model.isEmpty()) {
            sb.append(model);
        } else if (!manufacturer.isEmpty()) {
            sb.append(manufacturer);
        } else {
            sb.append("unknown");
        }
        String device = safe(diagnostics.device, "");
        if (!device.isEmpty() && !device.equalsIgnoreCase(model)) {
            sb.append(" [").append(device).append(']');
        }
        return sb.toString();
    }

    @NonNull
    private static String safe(@Nullable String value, @NonNull String fallback) {
        if (value == null) {
            return fallback;
        }
        String trimmed = value.trim();
        return trimmed.isEmpty() ? fallback : trimmed;
    }
}
