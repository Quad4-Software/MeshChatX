// SPDX-License-Identifier: 0BSD
package org.meshchatx.locallink;

import android.Manifest;
import android.annotation.TargetApi;
import android.content.Context;
import android.content.pm.PackageManager;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.NetworkRequest;
import android.net.wifi.SoftApConfiguration;
import android.net.wifi.WifiConfiguration;
import android.net.wifi.WifiManager;
import android.net.wifi.WifiNetworkSpecifier;
import android.net.wifi.aware.WifiAwareManager;
import android.net.wifi.p2p.WifiP2pConfig;
import android.net.wifi.p2p.WifiP2pGroup;
import android.net.wifi.p2p.WifiP2pManager;
import android.nfc.NfcAdapter;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;

import androidx.core.content.ContextCompat;

import org.json.JSONException;
import org.json.JSONObject;

import java.security.SecureRandom;

/**
 * Local link manager for MeshChatX nearby transports.
 *
 * Owns the LocalOnlyHotspot lifecycle, WifiNetworkSpecifier joins, and
 * capability probing (WiFi Aware, WiFi Direct, NFC, satellite). All radio
 * state stays in this class; Python drives it through Chaquopy and receives
 * async events through {@link PythonLocalLink}.
 */
public class LocalLink {

    private static final String TAG = "LocalLink-meshchatx";

    // Matches SoftApConfiguration.SECURITY_TYPE_WPA2_PSK (API 30+), kept as a
    // plain int so pre-30 devices never touch the missing class.
    private static final int SECURITY_TYPE_WPA2_PSK_FALLBACK = 3;

    // Matches PackageManager.FEATURE_TELEPHONY_SATELLITE (API 36+), kept as a
    // string so compileSdk 35 can still probe for the feature at runtime.
    private static final String FEATURE_TELEPHONY_SATELLITE =
        "android.hardware.telephony.satellite";

    private static volatile Context appContext;

    public static void setAppContext(Context context) {
        appContext = context != null ? context.getApplicationContext() : null;
    }

    public static Context getAppContext() {
        return appContext;
    }

    private final PythonLocalLink mPython;
    private final Context mContext;
    private final Handler mHandler;
    private final WifiManager mWifiManager;
    private final ConnectivityManager mConnectivityManager;

    private WifiManager.LocalOnlyHotspotReservation mHotspotReservation;
    private String mHotspotSsid;
    private String mHotspotPassphrase;
    private ConnectivityManager.NetworkCallback mJoinCallback;
    private Network mJoinNetwork;
    private WifiP2pManager mP2pManager;
    private WifiP2pManager.Channel mP2pChannel;
    private String mP2pSsid;
    private String mP2pPassphrase;
    private boolean mP2pGroupActive;
    private final SecureRandom mRandom = new SecureRandom();

    public LocalLink(PythonLocalLink python) {
        mPython = python;
        mContext = appContext;
        mHandler = new Handler(Looper.getMainLooper());
        mWifiManager = mContext != null
            ? (WifiManager) mContext.getApplicationContext().getSystemService(Context.WIFI_SERVICE)
            : null;
        mConnectivityManager = mContext != null
            ? (ConnectivityManager) mContext.getSystemService(Context.CONNECTIVITY_SERVICE)
            : null;
    }

    public boolean isReady() {
        return mContext != null;
    }

    public boolean hasNearbyWifiPermissions() {
        if (mContext == null) {
            return false;
        }
        if (Build.VERSION.SDK_INT >= 33) {
            return ContextCompat.checkSelfPermission(
                mContext, Manifest.permission.NEARBY_WIFI_DEVICES)
                == PackageManager.PERMISSION_GRANTED;
        }
        return ContextCompat.checkSelfPermission(
            mContext, Manifest.permission.ACCESS_FINE_LOCATION)
            == PackageManager.PERMISSION_GRANTED;
    }

    public String probeCapabilities() {
        JSONObject out = new JSONObject();
        try {
            PackageManager pm = mContext != null ? mContext.getPackageManager() : null;
            boolean awareFeature = pm != null
                && pm.hasSystemFeature(PackageManager.FEATURE_WIFI_AWARE);
            boolean awareAvailable = awareFeature && awareManagerAvailable();
            boolean nfc = false;
            if (pm != null && pm.hasSystemFeature(PackageManager.FEATURE_NFC)) {
                nfc = NfcAdapter.getDefaultAdapter(mContext) != null;
            }
            out.put("supported", mContext != null);
            out.put("sdk", Build.VERSION.SDK_INT);
            out.put("permission_nearby_wifi", hasNearbyWifiPermissions());
            out.put("hotspot", mWifiManager != null);
            out.put("wifi_join_specifier", Build.VERSION.SDK_INT >= 29);
            out.put("wifi_aware", awareFeature);
            out.put("wifi_aware_available", awareAvailable);
            out.put("wifi_direct",
                pm != null && pm.hasSystemFeature(PackageManager.FEATURE_WIFI_DIRECT));
            out.put("nfc", nfc);
            out.put("satellite", satelliteStateJson());
        } catch (JSONException e) {
            Log.w(TAG, "probeCapabilities failed", e);
        }
        return out.toString();
    }

    @TargetApi(26)
    private boolean awareManagerAvailable() {
        // FEATURE_WIFI_AWARE cannot exist below API 26 so callers never reach
        // this on older devices, but lint cannot see that chain.
        WifiAwareManager aware = mContext.getSystemService(WifiAwareManager.class);
        return aware != null && aware.isAvailable();
    }

    private JSONObject satelliteStateJson() {
        JSONObject out = new JSONObject();
        try {
            PackageManager pm = mContext != null ? mContext.getPackageManager() : null;
            boolean feature = pm != null
                && pm.hasSystemFeature(FEATURE_TELEPHONY_SATELLITE);
            out.put("feature", feature);
            out.put("enabled", JSONObject.NULL);
            // SatelliteManager is API 36+; reflect so older builds and older
            // compile targets never link against the class.
            if (feature && Build.VERSION.SDK_INT >= 33) {
                try {
                    Class<?> mgrClass =
                        Class.forName("android.telephony.satellite.SatelliteManager");
                    Object mgr = mContext.getSystemService(mgrClass);
                    if (mgr != null) {
                        Object enabled =
                            mgrClass.getMethod("isSatelliteEnabled").invoke(mgr);
                        out.put("enabled", enabled);
                    }
                } catch (ReflectiveOperationException | SecurityException e) {
                    // Class absent or permission missing: enabled stays null.
                }
            }
        } catch (JSONException e) {
            Log.w(TAG, "satelliteStateJson failed", e);
        }
        return out;
    }

    // ------------------------------------------------------------------
    // Local-only hotspot
    // ------------------------------------------------------------------

    public synchronized void startHotspot() {
        if (mContext == null || mWifiManager == null) {
            throw new IllegalStateException("wifi manager unavailable");
        }
        if (!hasNearbyWifiPermissions()) {
            throw new SecurityException("nearby wifi permission not granted");
        }
        if (mHotspotReservation != null) {
            // Already running: report current credentials again.
            if (mPython != null && mHotspotSsid != null) {
                mPython.on_hotspot_started(mHotspotSsid, mHotspotPassphrase,
                    SECURITY_TYPE_WPA2_PSK_FALLBACK);
            }
            return;
        }
        try {
            mWifiManager.startLocalOnlyHotspot(
                new WifiManager.LocalOnlyHotspotCallback() {
                    @Override
                    public void onStarted(WifiManager.LocalOnlyHotspotReservation reservation) {
                        synchronized (LocalLink.this) {
                            mHotspotReservation = reservation;
                            String ssid = null;
                            String pass = null;
                            int security = SoftApConfiguration.SECURITY_TYPE_WPA2_PSK;
                            if (Build.VERSION.SDK_INT >= 30) {
                                SoftApConfiguration config = reservation.getSoftApConfiguration();
                                if (config != null) {
                                    ssid = config.getSsid();
                                    pass = config.getPassphrase();
                                    security = config.getSecurityType();
                                }
                            } else {
                                WifiConfiguration config = reservation.getWifiConfiguration();
                                if (config != null) {
                                    ssid = config.SSID;
                                    if (ssid != null && ssid.startsWith("\"")
                                        && ssid.endsWith("\"")) {
                                        ssid = ssid.substring(1, ssid.length() - 1);
                                    }
                                    pass = config.preSharedKey;
                                    if (pass != null && pass.startsWith("\"")
                                        && pass.endsWith("\"")) {
                                        pass = pass.substring(1, pass.length() - 1);
                                    }
                                }
                            }
                            mHotspotSsid = ssid;
                            mHotspotPassphrase = pass;
                            if (mPython != null) {
                                mPython.on_hotspot_started(ssid, pass, security);
                            }
                        }
                    }

                    @Override
                    public void onStopped() {
                        synchronized (LocalLink.this) {
                            mHotspotReservation = null;
                            mHotspotSsid = null;
                            mHotspotPassphrase = null;
                        }
                        if (mPython != null) {
                            mPython.on_hotspot_stopped();
                        }
                    }

                    @Override
                    public void onFailed(int reason) {
                        synchronized (LocalLink.this) {
                            mHotspotReservation = null;
                        }
                        if (mPython != null) {
                            mPython.on_hotspot_failed(reason);
                        }
                    }
                },
                mHandler
            );
        } catch (SecurityException e) {
            notifyError("hotspot", "permission denied: " + e.getMessage());
            throw e;
        } catch (Exception e) {
            notifyError("hotspot", String.valueOf(e.getMessage()));
            throw new IllegalStateException("hotspot start failed: " + e.getMessage(), e);
        }
    }

    public synchronized void stopHotspot() {
        if (mHotspotReservation != null) {
            try {
                mHotspotReservation.close();
            } catch (Exception e) {
                Log.w(TAG, "hotspot close failed", e);
            }
            mHotspotReservation = null;
            mHotspotSsid = null;
            mHotspotPassphrase = null;
        }
    }

    public synchronized boolean isHotspotActive() {
        return mHotspotReservation != null;
    }

    public synchronized String hotspotInfo() {
        JSONObject out = new JSONObject();
        try {
            out.put("active", mHotspotReservation != null);
            if (mHotspotReservation != null) {
                out.put("ssid", mHotspotSsid != null ? mHotspotSsid : JSONObject.NULL);
            }
        } catch (JSONException ignored) {
        }
        return out.toString();
    }

    // ------------------------------------------------------------------
    // Join a peer-hosted WiFi network (WifiNetworkSpecifier)
    // ------------------------------------------------------------------

    public synchronized void joinWifiNetwork(String ssid, String passphrase) {
        if (mContext == null || mConnectivityManager == null) {
            throw new IllegalStateException("connectivity manager unavailable");
        }
        if (Build.VERSION.SDK_INT < 29) {
            throw new IllegalStateException("wifi specifier requires Android 10+");
        }
        if (!hasNearbyWifiPermissions()) {
            throw new SecurityException("nearby wifi permission not granted");
        }
        cancelJoinLocked();
        try {
            WifiNetworkSpecifier.Builder builder = new WifiNetworkSpecifier.Builder()
                .setSsid(ssid);
            if (passphrase != null && !passphrase.isEmpty()) {
                builder.setWpa2Passphrase(passphrase);
            }
            NetworkRequest request = new NetworkRequest.Builder()
                .addTransportType(NetworkCapabilities.TRANSPORT_WIFI)
                .removeCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
                .setNetworkSpecifier(builder.build())
                .build();
            mJoinCallback = new ConnectivityManager.NetworkCallback() {
                @Override
                public void onAvailable(Network network) {
                    synchronized (LocalLink.this) {
                        mJoinNetwork = network;
                        try {
                            mConnectivityManager.bindProcessToNetwork(network);
                        } catch (Exception e) {
                            Log.w(TAG, "bindProcessToNetwork failed", e);
                        }
                    }
                    if (mPython != null) {
                        mPython.on_join_status("available");
                    }
                }

                @Override
                public void onUnavailable() {
                    synchronized (LocalLink.this) {
                        // The request is dead; do not keep reporting it as
                        // pending in joinStatus or hold the callback.
                        if (mJoinCallback == this) {
                            mJoinCallback = null;
                        }
                    }
                    if (mPython != null) {
                        mPython.on_join_status("unavailable");
                    }
                }

                @Override
                public void onLost(Network network) {
                    synchronized (LocalLink.this) {
                        if (network != null && network.equals(mJoinNetwork)) {
                            mJoinNetwork = null;
                            try {
                                mConnectivityManager.bindProcessToNetwork(null);
                            } catch (Exception e) {
                                Log.w(TAG, "unbind failed", e);
                            }
                        }
                    }
                    if (mPython != null) {
                        mPython.on_join_status("lost");
                    }
                }
            };
            mConnectivityManager.requestNetwork(request, mJoinCallback);
            if (mPython != null) {
                mPython.on_join_status("requested");
            }
        } catch (SecurityException e) {
            notifyError("join", "permission denied: " + e.getMessage());
            throw e;
        } catch (Exception e) {
            notifyError("join", String.valueOf(e.getMessage()));
            throw new IllegalStateException("wifi join failed: " + e.getMessage(), e);
        }
    }

    public synchronized void cancelJoin() {
        cancelJoinLocked();
        if (mPython != null) {
            mPython.on_join_status("cancelled");
        }
    }

    private void cancelJoinLocked() {
        if (mJoinCallback != null) {
            try {
                mConnectivityManager.unregisterNetworkCallback(mJoinCallback);
            } catch (Exception e) {
                Log.w(TAG, "unregister join callback failed", e);
            }
            mJoinCallback = null;
        }
        if (mJoinNetwork != null) {
            mJoinNetwork = null;
            try {
                mConnectivityManager.bindProcessToNetwork(null);
            } catch (Exception e) {
                Log.w(TAG, "unbind failed", e);
            }
        }
    }

    public synchronized String joinStatus() {
        JSONObject out = new JSONObject();
        try {
            out.put("requested", mJoinCallback != null);
            out.put("connected", mJoinNetwork != null);
        } catch (JSONException ignored) {
        }
        return out.toString();
    }

    // ------------------------------------------------------------------
    // WiFi Direct named group (createGroup with deterministic credentials)
    // ------------------------------------------------------------------

    private String randomToken(int chars) {
        // Unambiguous alphabet so the credentials survive QR display.
        final String alphabet = "abcdefghjkmnpqrstuvwxyz23456789";
        StringBuilder out = new StringBuilder(chars);
        for (int i = 0; i < chars; i++) {
            out.append(alphabet.charAt(mRandom.nextInt(alphabet.length())));
        }
        return out.toString();
    }

    public synchronized void p2pGroupCreate() {
        if (mContext == null) {
            throw new IllegalStateException("context unavailable");
        }
        if (Build.VERSION.SDK_INT < 29) {
            throw new IllegalStateException("wifi direct groups require Android 10+");
        }
        if (!hasNearbyWifiPermissions()) {
            throw new SecurityException("nearby wifi permission not granted");
        }
        if (mP2pGroupActive) {
            if (mPython != null && mP2pSsid != null) {
                mPython.on_p2p_group_started(mP2pSsid, mP2pPassphrase);
            }
            return;
        }
        if (mP2pManager == null) {
            mP2pManager =
                (WifiP2pManager) mContext.getSystemService(Context.WIFI_P2P_SERVICE);
        }
        if (mP2pManager == null) {
            throw new IllegalStateException("wifi p2p manager unavailable");
        }
        if (mP2pChannel == null) {
            mP2pChannel = mP2pManager.initialize(mContext, Looper.getMainLooper(), null);
        }
        final String ssid = "DIRECT-mc-" + randomToken(4);
        final String passphrase = randomToken(16);
        WifiP2pConfig config =
            new WifiP2pConfig.Builder()
                .setNetworkName(ssid)
                .setPassphrase(passphrase)
                .setGroupOperatingBand(WifiP2pConfig.GROUP_OWNER_BAND_2GHZ)
                .build();
        try {
            mP2pManager.createGroup(
                mP2pChannel,
                config,
                new WifiP2pManager.ActionListener() {
                    @Override
                    public void onSuccess() {
                        synchronized (LocalLink.this) {
                            mP2pGroupActive = true;
                            mP2pSsid = ssid;
                            mP2pPassphrase = passphrase;
                        }
                        reportP2pGroupInfo();
                    }

                    @Override
                    public void onFailure(int reason) {
                        if (mPython != null) {
                            mPython.on_p2p_group_failed("createGroup failed: " + reason);
                        }
                    }
                });
        } catch (SecurityException e) {
            notifyError("p2p", "permission denied: " + e.getMessage());
            throw e;
        } catch (Exception e) {
            notifyError("p2p", String.valueOf(e.getMessage()));
            throw new IllegalStateException("p2p group failed: " + e.getMessage(), e);
        }
    }

    private void reportP2pGroupInfo() {
        WifiP2pManager mgr = mP2pManager;
        WifiP2pManager.Channel channel = mP2pChannel;
        if (mgr == null || channel == null) {
            return;
        }
        try {
            mgr.requestGroupInfo(
                channel,
                new WifiP2pManager.GroupInfoListener() {
                    @Override
                    public void onGroupInfoAvailable(WifiP2pGroup group) {
                        synchronized (LocalLink.this) {
                            if (group != null) {
                                if (group.getNetworkName() != null) {
                                    mP2pSsid = group.getNetworkName();
                                }
                                if (group.getPassphrase() != null
                                    && !group.getPassphrase().isEmpty()) {
                                    mP2pPassphrase = group.getPassphrase();
                                }
                            }
                        }
                        if (mPython != null) {
                            mPython.on_p2p_group_started(mP2pSsid, mP2pPassphrase);
                        }
                    }
                });
        } catch (SecurityException e) {
            // Group exists but info query is denied; report what we configured.
            if (mPython != null) {
                mPython.on_p2p_group_started(mP2pSsid, mP2pPassphrase);
            }
        }
    }

    public synchronized void p2pGroupRemove() {
        WifiP2pManager mgr = mP2pManager;
        WifiP2pManager.Channel channel = mP2pChannel;
        mP2pGroupActive = false;
        mP2pSsid = null;
        mP2pPassphrase = null;
        if (mgr == null || channel == null) {
            return;
        }
        try {
            mgr.removeGroup(
                channel,
                new WifiP2pManager.ActionListener() {
                    @Override
                    public void onSuccess() {
                        if (mPython != null) {
                            mPython.on_p2p_group_stopped();
                        }
                    }

                    @Override
                    public void onFailure(int reason) {
                        if (mPython != null) {
                            mPython.on_p2p_group_stopped();
                        }
                    }
                });
        } catch (Exception e) {
            notifyError("p2p", String.valueOf(e.getMessage()));
        }
    }

    public synchronized boolean isP2pGroupActive() {
        return mP2pGroupActive;
    }

    private void notifyError(String where, String message) {
        if (mPython != null) {
            mPython.on_error(where, message);
        } else {
            Log.w(TAG, where + ": " + message);
        }
    }
}
