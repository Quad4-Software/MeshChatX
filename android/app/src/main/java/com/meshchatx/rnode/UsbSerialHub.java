package com.meshchatx.rnode;

import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.hardware.usb.UsbDevice;
import android.hardware.usb.UsbDeviceConnection;
import android.hardware.usb.UsbManager;
import android.os.Build;
import android.util.Log;

import androidx.annotation.Nullable;
import androidx.core.content.ContextCompat;

import com.hoho.android.usbserial.driver.UsbSerialDriver;
import com.hoho.android.usbserial.driver.UsbSerialPort;
import com.hoho.android.usbserial.driver.UsbSerialProber;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

/**
 * Native USB serial hub for the RNode flasher Activity (no WebView).
 */
public final class UsbSerialHub {
    private static final String TAG = "UsbSerialHub";
    public static final String ACTION_USB_PERMISSION = "com.meshchatx.USB_PERMISSION";

    public interface Listener {
        void onUsbPermissionResult(String deviceId, boolean granted);

        void onPortsChanged();
    }

    public static final class PortInfo {
        public final String deviceId;
        public final String deviceName;
        public final int vendorId;
        public final int productId;
        public final boolean hasPermission;
        public final String driverName;

        PortInfo(
            String deviceId,
            String deviceName,
            int vendorId,
            int productId,
            boolean hasPermission,
            String driverName
        ) {
            this.deviceId = deviceId;
            this.deviceName = deviceName;
            this.vendorId = vendorId;
            this.productId = productId;
            this.hasPermission = hasPermission;
            this.driverName = driverName;
        }

        @Override
        public String toString() {
            return deviceName
                + " (0x"
                + Integer.toHexString(vendorId)
                + ":0x"
                + Integer.toHexString(productId)
                + ")";
        }
    }

    private final Context appContext;
    private final List<Listener> listeners = new CopyOnWriteArrayList<>();
    @Nullable
    private BroadcastReceiver permissionReceiver;
    private boolean receiverRegistered = false;

    @Nullable
    private UsbSerialPort openPort;
    @Nullable
    private UsbDeviceConnection openConnection;
    @Nullable
    private String openDeviceId;

    public UsbSerialHub(Context context) {
        this.appContext = context.getApplicationContext();
    }

    public void addListener(Listener listener) {
        if (listener != null) {
            listeners.add(listener);
        }
    }

    public void removeListener(Listener listener) {
        listeners.remove(listener);
    }

    public void start() {
        ensurePermissionReceiver();
    }

    public void stop() {
        close();
        if (receiverRegistered && permissionReceiver != null) {
            try {
                appContext.unregisterReceiver(permissionReceiver);
            } catch (Exception ignored) {
            }
            receiverRegistered = false;
        }
        listeners.clear();
    }

    public List<PortInfo> listPorts() {
        List<PortInfo> out = new ArrayList<>();
        UsbManager manager = usbManager();
        if (manager == null) {
            return out;
        }
        List<UsbSerialDriver> drivers =
            UsbSerialProber.getDefaultProber().findAllDrivers(manager);
        for (UsbSerialDriver driver : drivers) {
            UsbDevice device = driver.getDevice();
            if (device == null) {
                continue;
            }
            out.add(
                new PortInfo(
                    deviceIdFor(device),
                    device.getDeviceName(),
                    device.getVendorId(),
                    device.getProductId(),
                    manager.hasPermission(device),
                    driver.getClass().getSimpleName()
                )
            );
        }
        return out;
    }

    public boolean requestPermission(String deviceId) {
        UsbManager manager = usbManager();
        if (manager == null) {
            return false;
        }
        ensurePermissionReceiver();
        UsbSerialDriver driver = findDriver(manager, deviceId);
        if (driver == null) {
            return false;
        }
        UsbDevice device = driver.getDevice();
        if (manager.hasPermission(device)) {
            return false;
        }
        Intent intent = new Intent(ACTION_USB_PERMISSION);
        intent.setPackage(appContext.getPackageName());
        int flags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            flags |= PendingIntent.FLAG_IMMUTABLE;
        }
        PendingIntent pi =
            PendingIntent.getBroadcast(appContext, device.getDeviceId(), intent, flags);
        manager.requestPermission(device, pi);
        return true;
    }

    public boolean requestPermissionsForAll() {
        boolean any = false;
        for (PortInfo port : listPorts()) {
            if (!port.hasPermission) {
                any |= requestPermission(port.deviceId);
            }
        }
        return any;
    }

    public synchronized boolean open(String deviceId, int baudRate) throws IOException {
        close();
        UsbManager manager = usbManager();
        if (manager == null) {
            throw new IOException("USB service unavailable");
        }
        UsbSerialDriver driver = findDriver(manager, deviceId);
        if (driver == null) {
            throw new IOException("No serial driver for " + deviceId);
        }
        UsbDevice device = driver.getDevice();
        if (!manager.hasPermission(device)) {
            requestPermission(deviceId);
            throw new IOException("USB permission required");
        }
        UsbDeviceConnection connection = manager.openDevice(device);
        if (connection == null) {
            throw new IOException("openDevice failed");
        }
        List<UsbSerialPort> ports = driver.getPorts();
        if (ports == null || ports.isEmpty()) {
            connection.close();
            throw new IOException("No serial ports on device");
        }
        UsbSerialPort port = ports.get(0);
        port.open(connection);
        int baud = baudRate > 0 ? baudRate : 115200;
        port.setParameters(baud, 8, UsbSerialPort.STOPBITS_1, UsbSerialPort.PARITY_NONE);
        port.setDTR(false);
        port.setRTS(false);
        openPort = port;
        openConnection = connection;
        openDeviceId = deviceId;
        return true;
    }

    public synchronized void close() {
        if (openPort != null) {
            try {
                openPort.close();
            } catch (Exception ignored) {
            }
            openPort = null;
        }
        if (openConnection != null) {
            try {
                openConnection.close();
            } catch (Exception ignored) {
            }
            openConnection = null;
        }
        openDeviceId = null;
    }

    public synchronized boolean isOpen() {
        return openPort != null;
    }

    @Nullable
    public synchronized String getOpenDeviceId() {
        return openDeviceId;
    }

    public synchronized void setBaudRate(int baudRate) throws IOException {
        requireOpen();
        openPort.setParameters(baudRate, 8, UsbSerialPort.STOPBITS_1, UsbSerialPort.PARITY_NONE);
    }

    public synchronized void setDtrRts(boolean dtr, boolean rts) throws IOException {
        requireOpen();
        openPort.setDTR(dtr);
        openPort.setRTS(rts);
    }

    public synchronized void write(byte[] data) throws IOException {
        requireOpen();
        openPort.write(data, 2000);
    }

    public synchronized int read(byte[] buffer, int timeoutMs) throws IOException {
        requireOpen();
        return openPort.read(buffer, timeoutMs);
    }

    private void requireOpen() throws IOException {
        if (openPort == null) {
            throw new IOException("Serial port not open");
        }
    }

    private void ensurePermissionReceiver() {
        if (receiverRegistered) {
            return;
        }
        permissionReceiver =
            new BroadcastReceiver() {
                @Override
                public void onReceive(Context context, Intent intent) {
                    if (intent == null || !ACTION_USB_PERMISSION.equals(intent.getAction())) {
                        return;
                    }
                    UsbDevice device = intent.getParcelableExtra(UsbManager.EXTRA_DEVICE);
                    boolean granted =
                        intent.getBooleanExtra(UsbManager.EXTRA_PERMISSION_GRANTED, false);
                    String deviceId = device != null ? deviceIdFor(device) : "";
                    for (Listener listener : listeners) {
                        listener.onUsbPermissionResult(deviceId, granted);
                        listener.onPortsChanged();
                    }
                }
            };
        IntentFilter filter = new IntentFilter(ACTION_USB_PERMISSION);
        try {
            // App-private USB permission result. Not exported to other apps.
            ContextCompat.registerReceiver(
                appContext,
                permissionReceiver,
                filter,
                ContextCompat.RECEIVER_NOT_EXPORTED
            );
            receiverRegistered = true;
        } catch (Exception e) {
            Log.w(TAG, "registerReceiver failed: " + e.getMessage());
        }
    }

    @Nullable
    private UsbSerialDriver findDriver(UsbManager manager, String deviceId) {
        List<UsbSerialDriver> drivers =
            UsbSerialProber.getDefaultProber().findAllDrivers(manager);
        for (UsbSerialDriver driver : drivers) {
            UsbDevice device = driver.getDevice();
            if (device != null && deviceIdFor(device).equals(deviceId)) {
                return driver;
            }
        }
        return null;
    }

    private static String deviceIdFor(UsbDevice device) {
        return String.valueOf(device.getDeviceId());
    }

    @Nullable
    private UsbManager usbManager() {
        return (UsbManager) appContext.getSystemService(Context.USB_SERVICE);
    }
}
