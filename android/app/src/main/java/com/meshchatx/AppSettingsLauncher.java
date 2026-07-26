package com.meshchatx;

import android.content.ActivityNotFoundException;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.provider.Settings;
import android.util.Log;
import android.widget.Toast;

/**
 * Open app / Bluetooth settings with GrapheneOS-friendly fallbacks.
 *
 * ACTION_APPLICATION_DETAILS_SETTINGS alone can fail on hardened builds. Try
 * several intents before surfacing an error to the user.
 */
public final class AppSettingsLauncher {
    private static final String TAG = "AppSettingsLauncher";

    private AppSettingsLauncher() {
    }

    public static boolean openAppDetails(Context context) {
        if (context == null) {
            return false;
        }
        String packageName = context.getPackageName();
        Intent[] candidates =
            new Intent[] {
                detailsIntent(packageName),
                detailsIntentWithSettingsPackage(packageName),
                new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
                    .setData(Uri.parse("package:" + packageName)),
                new Intent(Settings.ACTION_MANAGE_APPLICATIONS_SETTINGS),
                new Intent(Settings.ACTION_SETTINGS),
            };
        return startFirstAvailable(context, candidates, "Could not open app settings");
    }

    public static boolean openBluetoothSettings(Context context) {
        if (context == null) {
            return false;
        }
        String packageName = context.getPackageName();
        Intent[] candidates =
            new Intent[] {
                new Intent(Settings.ACTION_BLUETOOTH_SETTINGS),
                detailsIntent(packageName),
                detailsIntentWithSettingsPackage(packageName),
                new Intent(Settings.ACTION_MANAGE_APPLICATIONS_SETTINGS),
                new Intent(Settings.ACTION_SETTINGS),
            };
        return startFirstAvailable(
            context,
            candidates,
            "Could not open Bluetooth or app settings"
        );
    }

    private static Intent detailsIntent(String packageName) {
        Intent intent = new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS);
        intent.setData(Uri.fromParts("package", packageName, null));
        return intent;
    }

    private static Intent detailsIntentWithSettingsPackage(String packageName) {
        Intent intent = detailsIntent(packageName);
        intent.setPackage("com.android.settings");
        return intent;
    }

    private static boolean startFirstAvailable(
        Context context,
        Intent[] candidates,
        String failureMessage
    ) {
        Exception last = null;
        for (Intent base : candidates) {
            if (base == null) {
                continue;
            }
            try {
                Intent intent = new Intent(base);
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                context.startActivity(intent);
                return true;
            } catch (ActivityNotFoundException | SecurityException e) {
                last = e;
                Log.w(TAG, "Settings intent failed: " + base.getAction() + " " + e.getMessage());
            } catch (Exception e) {
                last = e;
                Log.w(TAG, "Settings intent failed: " + base.getAction() + " " + e.getMessage());
            }
        }
        String detail = last != null && last.getMessage() != null ? last.getMessage() : "";
        Toast.makeText(
                context,
                detail.isEmpty() ? failureMessage : failureMessage + ": " + detail,
                Toast.LENGTH_LONG)
            .show();
        return false;
    }
}
