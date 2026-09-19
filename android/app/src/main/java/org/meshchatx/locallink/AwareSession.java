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
import android.net.wifi.aware.AttachCallback;
import android.net.wifi.aware.DiscoverySessionCallback;
import android.net.wifi.aware.PeerHandle;
import android.net.wifi.aware.PublishConfig;
import android.net.wifi.aware.PublishDiscoverySession;
import android.net.wifi.aware.SubscribeConfig;
import android.net.wifi.aware.SubscribeDiscoverySession;
import android.net.wifi.aware.WifiAwareManager;
import android.net.wifi.aware.WifiAwareNetworkInfo;
import android.net.wifi.aware.WifiAwareNetworkSpecifier;
import android.net.wifi.aware.WifiAwareSession;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;

import androidx.core.content.ContextCompat;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.Inet6Address;
import java.net.InetSocketAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.util.ArrayDeque;
import java.util.Deque;
import java.util.HashMap;
import java.util.Map;

/**
 * WiFi Aware (NAN) session manager for MeshChatX.
 *
 * Publisher role advertises the generic service name with a random per-session
 * passphrase in the service info and answers DPREQ bootstrap messages by
 * creating a responder data path and a bound TCP listener. Subscriber role
 * discovers publishers, sends DPREQ, creates the initiator data path and
 * connects a TCP socket to the peer's link-local IPv6. Every established
 * socket is pumped to Python as raw bytes; framing lives on the Python side.
 *
 * Roles are fixed by the spec: subscriber is the initiator, publisher is the
 * responder. No identity or mesh data appears in advertisements.
 */
@TargetApi(26)
public class AwareSession {

    private static final String TAG = "AwareSession-meshchatx";

    static final String SERVICE_NAME = "meshchatx-locallink-v1";
    static final int AWARE_TCP_PORT = 42434;
    static final int MAX_PEERS = 8;
    static final int MAX_PENDING_DPREQ = 3;
    static final long MIN_DPREQ_INTERVAL_MS = 2000;
    static final long DPREQ_WINDOW_MS = 60000;
    static final int MAX_DPREQ_PER_WINDOW = 6;

    private static final byte[] DPREQ = "DPREQ".getBytes(StandardCharsets.UTF_8);
    private static final String INFO_PREFIX = "MCX1:";
    private static final int READ_BUFFER = 64 * 1024;

    private final PythonAware mPython;
    private final Context mContext;
    private final Handler mHandler;
    private final SecureRandom mRandom = new SecureRandom();

    private WifiAwareSession mSession;
    private PublishDiscoverySession mPub;
    private SubscribeDiscoverySession mSub;
    private ServerSocket mServer;
    private Thread mAcceptThread;
    private String mRole = "off";
    private String mPassphrase;
    private int mNextPeerId = 1;
    private int mNextMsgId = 1;
    private boolean mStopped;

    private final Map<Integer, PeerHandle> mPeerHandles = new HashMap<>();
    private final Map<Integer, Socket> mSockets = new HashMap<>();
    private final Map<Integer, Object> mWriteLocks = new HashMap<>();
    private final Map<Integer, ConnectivityManager.NetworkCallback> mNetCbs =
        new HashMap<>();
    private final Map<Integer, String> mExpectedPeerIps = new HashMap<>();
    private final Deque<Long> mDpreqTimes = new ArrayDeque<>();

    public AwareSession(Context context, PythonAware python) {
        mPython = python;
        mContext = context != null ? context.getApplicationContext() : null;
        mHandler = new Handler(Looper.getMainLooper());
    }

    private boolean hasPermissions() {
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

    private WifiAwareManager awareManager() {
        if (mContext == null || Build.VERSION.SDK_INT < 26) {
            return null;
        }
        WifiAwareManager mgr = mContext.getSystemService(WifiAwareManager.class);
        return (mgr != null && mgr.isAvailable()) ? mgr : null;
    }

    private String randomHex(int bytes) {
        byte[] buf = new byte[bytes];
        mRandom.nextBytes(buf);
        StringBuilder out = new StringBuilder(bytes * 2);
        for (byte b : buf) {
            out.append(String.format("%02x", b));
        }
        return out.toString();
    }

    // ------------------------------------------------------------------
    // Attach and discovery
    // ------------------------------------------------------------------

    public synchronized void startPublish() {
        startAttach("publish");
    }

    public synchronized void startSubscribe() {
        startAttach("subscribe");
    }

    private void startAttach(final String role) {
        if (mContext == null) {
            throw new IllegalStateException("context unavailable");
        }
        if (Build.VERSION.SDK_INT < 26) {
            throw new IllegalStateException("wifi aware requires Android 8+");
        }
        if (!hasPermissions()) {
            throw new SecurityException("nearby wifi permission not granted");
        }
        WifiAwareManager mgr = awareManager();
        if (mgr == null) {
            throw new IllegalStateException("wifi aware is not available");
        }
        stopLocked();
        mStopped = false;
        mRole = role;
        if ("publish".equals(role)) {
            mPassphrase = randomHex(16);
        }
        try {
            mgr.attach(
                new AttachCallback() {
                    @Override
                    public void onAttached(WifiAwareSession session) {
                        synchronized (AwareSession.this) {
                            mSession = session;
                        }
                        notifyEvent("attached");
                        if ("publish".equals(role)) {
                            beginPublish(session);
                        } else {
                            beginSubscribe(session);
                        }
                    }

                    @Override
                    public void onAttachFailed() {
                        notifyError("aware", "attach failed");
                    }

                    @Override
                    public void onAwareSessionTerminated() {
                        notifyEvent("session_lost");
                    }
                },
                mHandler
            );
        } catch (SecurityException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalStateException("aware attach failed: " + e.getMessage(), e);
        }
    }

    private void beginPublish(WifiAwareSession session) {
        try {
            PublishConfig config =
                new PublishConfig.Builder()
                    .setServiceName(SERVICE_NAME)
                    .setPublishType(PublishConfig.PUBLISH_TYPE_UNSOLICITED)
                    .setServiceSpecificInfo(
                        (INFO_PREFIX + mPassphrase).getBytes(StandardCharsets.UTF_8))
                    .build();
            session.publish(
                config,
                new DiscoverySessionCallback() {
                    @Override
                    public void onPublishStarted(PublishDiscoverySession session) {
                        synchronized (AwareSession.this) {
                            mPub = session;
                        }
                        notifyEvent("publish_started");
                    }

                    @Override
                    public void onMessageReceived(PeerHandle peerHandle, byte[] message) {
                        if (message == null || !isDpreq(message)) {
                            return;
                        }
                        onDpreq(peerHandle);
                    }

                    @Override
                    public void onSessionTerminated() {
                        notifyEvent("session_lost");
                    }
                },
                mHandler
            );
        } catch (SecurityException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalStateException("aware publish failed: " + e.getMessage(), e);
        }
    }

    private void beginSubscribe(WifiAwareSession session) {
        try {
            SubscribeConfig config =
                new SubscribeConfig.Builder()
                    .setServiceName(SERVICE_NAME)
                    .setSubscribeType(SubscribeConfig.SUBSCRIBE_TYPE_PASSIVE)
                    .build();
            session.subscribe(
                config,
                new DiscoverySessionCallback() {
                    @Override
                    public void onSubscribeStarted(SubscribeDiscoverySession session) {
                        synchronized (AwareSession.this) {
                            mSub = session;
                        }
                        notifyEvent("subscribe_started");
                    }

                    @Override
                    public void onServiceDiscovered(
                        PeerHandle peerHandle,
                        byte[] serviceSpecificInfo,
                        java.util.List<byte[]> matchFilter
                    ) {
                        onPeerDiscovered(peerHandle, serviceSpecificInfo);
                    }

                    @Override
                    public void onSessionTerminated() {
                        notifyEvent("session_lost");
                    }
                },
                mHandler
            );
        } catch (SecurityException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalStateException("aware subscribe failed: " + e.getMessage(), e);
        }
    }

    private static boolean isDpreq(byte[] message) {
        if (message.length != DPREQ.length) {
            return false;
        }
        for (int i = 0; i < DPREQ.length; i++) {
            if (message[i] != DPREQ[i]) {
                return false;
            }
        }
        return true;
    }

    // ------------------------------------------------------------------
    // Data path setup
    // ------------------------------------------------------------------

    private void onDpreq(PeerHandle peerHandle) {
        synchronized (this) {
            if (mPub == null || mSockets.size() >= MAX_PEERS) {
                return;
            }
            long now = System.currentTimeMillis();
            while (!mDpreqTimes.isEmpty()
                && now - mDpreqTimes.peekFirst() > DPREQ_WINDOW_MS) {
                mDpreqTimes.pollFirst();
            }
            if (mDpreqTimes.size() >= MAX_DPREQ_PER_WINDOW) {
                return;
            }
            if (!mDpreqTimes.isEmpty()
                && now - mDpreqTimes.peekLast() < MIN_DPREQ_INTERVAL_MS) {
                return;
            }
            mDpreqTimes.addLast(now);
            int peerId = peerIdFor(peerHandle);
            requestDataPath(mPub, peerHandle, mPassphrase,
                WifiAwareManager.WIFI_AWARE_DATA_PATH_ROLE_RESPONDER, peerId);
        }
        notifyPeer(peerIdFor(peerHandle));
    }

    private void onPeerDiscovered(PeerHandle peerHandle, byte[] serviceSpecificInfo) {
        String passphrase = parsePassphrase(serviceSpecificInfo);
        if (passphrase == null) {
            return;
        }
        synchronized (this) {
            if (mSub == null || mSockets.size() >= MAX_PEERS) {
                return;
            }
            if (peerIdFor(peerHandle) != 0 && mSockets.containsKey(peerIdFor(peerHandle))) {
                return;
            }
            int peerId = peerIdFor(peerHandle);
            try {
                mSub.sendMessage(peerHandle, mNextMsgId++, DPREQ);
            } catch (Exception e) {
                notifyError("aware", "sendMessage failed: " + e.getMessage());
            }
            requestDataPath(mSub, peerHandle, passphrase,
                WifiAwareManager.WIFI_AWARE_DATA_PATH_ROLE_INITIATOR, peerId);
        }
    }

    private static String parsePassphrase(byte[] info) {
        if (info == null || info.length <= INFO_PREFIX.length() || info.length > 64) {
            return null;
        }
        String text = new String(info, StandardCharsets.UTF_8);
        if (!text.startsWith(INFO_PREFIX)) {
            return null;
        }
        String hex = text.substring(INFO_PREFIX.length());
        if (hex.length() < 8 || hex.length() > 48) {
            return null;
        }
        return hex;
    }

    private int peerIdFor(PeerHandle handle) {
        for (Map.Entry<Integer, PeerHandle> entry : mPeerHandles.entrySet()) {
            if (entry.getValue() != null && entry.getValue().equals(handle)) {
                return entry.getKey();
            }
        }
        int id = mNextPeerId++;
        mPeerHandles.put(id, handle);
        return id;
    }

    private void requestDataPath(
        android.net.wifi.aware.DiscoverySession session,
        PeerHandle peerHandle,
        String passphrase,
        int role,
        int peerId
    ) {
        if (Build.VERSION.SDK_INT < 33) {
            notifyError("aware", "data path TCP requires Android 13+");
            return;
        }
        ConnectivityManager cm =
            (ConnectivityManager) mContext.getSystemService(Context.CONNECTIVITY_SERVICE);
        if (cm == null) {
            notifyError("aware", "connectivity manager unavailable");
            return;
        }
        // The specifier role is fixed by session type: publish creates a
        // responder specifier, subscribe creates an initiator specifier.
        WifiAwareNetworkSpecifier specifier =
            (WifiAwareNetworkSpecifier)
                session.createNetworkSpecifierPassphrase(peerHandle, passphrase);
        NetworkRequest request =
            new NetworkRequest.Builder()
                .addTransportType(NetworkCapabilities.TRANSPORT_WIFI_AWARE)
                .setNetworkSpecifier(specifier)
                .build();
        ConnectivityManager.NetworkCallback cb =
            new ConnectivityManager.NetworkCallback() {
                @Override
                public void onAvailable(Network network) {
                    onDataPathReady(network, role, peerId);
                }

                @Override
                public void onLost(Network network) {
                    peerDown(peerId);
                }
            };
        synchronized (this) {
            ConnectivityManager.NetworkCallback old = mNetCbs.put(peerId, cb);
            if (old != null) {
                try {
                    cm.unregisterNetworkCallback(old);
                } catch (Exception ignored) {
                }
            }
        }
        try {
            cm.requestNetwork(request, cb);
        } catch (SecurityException e) {
            synchronized (this) {
                mNetCbs.remove(peerId);
            }
            notifyError("aware", "datapath permission denied: " + e.getMessage());
        }
    }

    @TargetApi(29)
    private void onDataPathReady(Network network, int role, int peerId) {
        ConnectivityManager cm =
            (ConnectivityManager) mContext.getSystemService(Context.CONNECTIVITY_SERVICE);
        if (cm == null) {
            return;
        }
        NetworkCapabilities caps = cm.getNetworkCapabilities(network);
        WifiAwareNetworkInfo info =
            caps != null && caps.getTransportInfo() instanceof WifiAwareNetworkInfo
                ? (WifiAwareNetworkInfo) caps.getTransportInfo()
                : null;
        Inet6Address peerIp = info != null ? info.getPeerIpv6Addr() : null;
        if (role == WifiAwareManager.WIFI_AWARE_DATA_PATH_ROLE_RESPONDER) {
            synchronized (this) {
                if (peerIp != null) {
                    mExpectedPeerIps.put(peerId, peerIp.getHostAddress());
                }
            }
            openServerSocket(network);
        } else {
            connectToPeer(network, peerIp, peerId);
        }
    }

    private void openServerSocket(final Network network) {
        ConnectivityManager cm =
            (ConnectivityManager) mContext.getSystemService(Context.CONNECTIVITY_SERVICE);
        java.net.InetAddress bindAddr = null;
        if (cm != null) {
            android.net.LinkProperties lp = cm.getLinkProperties(network);
            if (lp != null) {
                for (android.net.LinkAddress la : lp.getLinkAddresses()) {
                    java.net.InetAddress addr = la.getAddress();
                    if (addr != null && addr.isLinkLocalAddress()) {
                        bindAddr = addr;
                        break;
                    }
                }
            }
        }
        synchronized (this) {
            if (mServer != null) {
                return;
            }
            if (bindAddr == null) {
                // Fail closed: a wildcard listener would also accept
                // connections from regular LAN interfaces, letting any
                // link-local host feed frames into RNS.
                notifyError("aware", "no link-local address on aware network");
                return;
            }
            try {
                mServer = new ServerSocket(AWARE_TCP_PORT, 50, bindAddr);
            } catch (Exception e) {
                notifyError("aware", "server socket failed: " + e.getMessage());
                return;
            }
            mAcceptThread = new Thread(this::acceptLoop, "aware-accept");
            mAcceptThread.setDaemon(true);
            mAcceptThread.start();
        }
    }

    private void acceptLoop() {
        while (true) {
            ServerSocket server;
            synchronized (this) {
                server = mServer;
            }
            if (server == null) {
                return;
            }
            try {
                Socket accepted = server.accept();
                int peerId;
                synchronized (this) {
                    if (mSockets.size() >= MAX_PEERS || !peerAddressAllowed(accepted)) {
                        try {
                            accepted.close();
                        } catch (IOException ignored) {
                        }
                        continue;
                    }
                    peerId = matchExpectedPeer(accepted);
                    registerSocket(peerId, accepted);
                }
                notifyLinkUp(peerId);
            } catch (IOException e) {
                synchronized (this) {
                    if (mServer == null) {
                        return;
                    }
                }
            }
        }
    }

    private boolean peerAddressAllowed(Socket accepted) {
        java.net.InetAddress remote = accepted.getInetAddress();
        if (remote == null || !remote.isLinkLocalAddress()) {
            return false;
        }
        if (mExpectedPeerIps.isEmpty()) {
            return true;
        }
        return mExpectedPeerIps.containsValue(remote.getHostAddress());
    }

    private int matchExpectedPeer(Socket accepted) {
        String remote =
            accepted.getInetAddress() != null
                ? accepted.getInetAddress().getHostAddress()
                : null;
        if (remote != null) {
            for (Map.Entry<Integer, String> entry : mExpectedPeerIps.entrySet()) {
                if (remote.equals(entry.getValue())) {
                    return entry.getKey();
                }
            }
        }
        int id = mNextPeerId++;
        mPeerHandles.put(id, null);
        return id;
    }

    private void connectToPeer(Network network, Inet6Address peerIp, int peerId) {
        if (peerIp == null) {
            notifyError("aware", "peer address unavailable");
            return;
        }
        new Thread(
            () -> {
                try {
                    Socket socket = network.getSocketFactory().createSocket();
                    socket.connect(new InetSocketAddress(peerIp, AWARE_TCP_PORT), 5000);
                    synchronized (AwareSession.this) {
                        registerSocket(peerId, socket);
                    }
                    notifyLinkUp(peerId);
                } catch (Exception e) {
                    notifyError("aware", "connect failed: " + e.getMessage());
                }
            },
            "aware-connect"
        ).start();
    }

    // ------------------------------------------------------------------
    // Socket pump
    // ------------------------------------------------------------------

    private void registerSocket(int peerId, Socket socket) {
        if (mStopped) {
            // The session was torn down while connect/accept was in flight.
            try {
                socket.close();
            } catch (IOException ignored) {
            }
            return;
        }
        mSockets.put(peerId, socket);
        mWriteLocks.put(peerId, new Object());
        Thread reader =
            new Thread(() -> readLoop(peerId, socket), "aware-read-" + peerId);
        reader.setDaemon(true);
        reader.start();
    }

    private void readLoop(int peerId, Socket socket) {
        byte[] buffer = new byte[READ_BUFFER];
        try {
            InputStream in = socket.getInputStream();
            while (true) {
                int n = in.read(buffer);
                if (n < 0) {
                    break;
                }
                if (n > 0 && mPython != null) {
                    byte[] copy = new byte[n];
                    System.arraycopy(buffer, 0, copy, 0, n);
                    mPython.on_aware_data(peerId, copy);
                }
            }
        } catch (IOException ignored) {
        }
        peerDown(peerId);
    }

    public boolean sendToPeer(int peerId, byte[] data) {
        Socket socket;
        Object lock;
        synchronized (this) {
            socket = mSockets.get(peerId);
            lock = mWriteLocks.get(peerId);
        }
        if (socket == null || lock == null) {
            return false;
        }
        synchronized (lock) {
            try {
                OutputStream out = socket.getOutputStream();
                out.write(data);
                out.flush();
                return true;
            } catch (IOException e) {
                peerDown(peerId);
                return false;
            }
        }
    }

    public synchronized void closePeer(int peerId) {
        peerDown(peerId);
    }

    private void peerDown(int peerId) {
        Socket socket;
        ConnectivityManager.NetworkCallback cb;
        boolean known;
        synchronized (this) {
            socket = mSockets.remove(peerId);
            mWriteLocks.remove(peerId);
            mExpectedPeerIps.remove(peerId);
            known = mPeerHandles.remove(peerId) != null;
            cb = mNetCbs.remove(peerId);
        }
        if (cb != null && mContext != null) {
            ConnectivityManager cm =
                (ConnectivityManager)
                    mContext.getSystemService(Context.CONNECTIVITY_SERVICE);
            if (cm != null) {
                try {
                    cm.unregisterNetworkCallback(cb);
                } catch (Exception ignored) {
                }
            }
        }
        if (socket != null) {
            try {
                socket.close();
            } catch (IOException ignored) {
            }
        }
        if ((socket != null || known) && mPython != null) {
            mPython.on_aware_link_down(peerId);
        }
    }

    // ------------------------------------------------------------------
    // Lifecycle
    // ------------------------------------------------------------------

    public synchronized void stop() {
        stopLocked();
        notifyEvent("stopped");
    }

    private void stopLocked() {
        mStopped = true;
        mRole = "off";
        for (Map.Entry<Integer, Socket> entry : mSockets.entrySet()) {
            try {
                entry.getValue().close();
            } catch (IOException ignored) {
            }
        }
        mSockets.clear();
        mWriteLocks.clear();
        mPeerHandles.clear();
        mExpectedPeerIps.clear();
        mDpreqTimes.clear();
        if (!mNetCbs.isEmpty() && mContext != null) {
            ConnectivityManager cm =
                (ConnectivityManager) mContext.getSystemService(Context.CONNECTIVITY_SERVICE);
            if (cm != null) {
                for (ConnectivityManager.NetworkCallback cb : mNetCbs.values()) {
                    try {
                        cm.unregisterNetworkCallback(cb);
                    } catch (Exception ignored) {
                    }
                }
            }
        }
        mNetCbs.clear();
        if (mServer != null) {
            try {
                mServer.close();
            } catch (IOException ignored) {
            }
            mServer = null;
        }
        if (mPub != null) {
            try {
                mPub.close();
            } catch (Exception ignored) {
            }
            mPub = null;
        }
        if (mSub != null) {
            try {
                mSub.close();
            } catch (Exception ignored) {
            }
            mSub = null;
        }
        if (mSession != null) {
            try {
                mSession.close();
            } catch (Exception ignored) {
            }
            mSession = null;
        }
    }

    public synchronized String statusJson() {
        JSONObject out = new JSONObject();
        try {
            out.put("role", mRole);
            out.put("session", mSession != null);
            out.put("peers", mPeerHandles.size());
            out.put("links", mSockets.size());
        } catch (JSONException ignored) {
        }
        return out.toString();
    }

    private void notifyEvent(String what) {
        if (mPython != null) {
            mPython.on_aware_event(what);
        }
    }

    private void notifyPeer(int peerId) {
        if (mPython != null) {
            mPython.on_aware_peer(peerId);
        }
    }

    private void notifyLinkUp(int peerId) {
        if (mPython != null) {
            mPython.on_aware_link_up(peerId);
        }
    }

    private void notifyError(String where, String message) {
        if (mPython != null) {
            mPython.on_aware_error(where, message);
        } else {
            Log.w(TAG, where + ": " + message);
        }
    }
}
