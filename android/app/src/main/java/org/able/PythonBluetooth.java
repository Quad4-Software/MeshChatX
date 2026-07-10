package org.able;

import android.bluetooth.BluetoothGattCharacteristic;
import android.bluetooth.BluetoothGattDescriptor;
import android.bluetooth.BluetoothGattService;
import android.bluetooth.le.ScanResult;

import java.util.List;

/**
 * Python callback surface for {@link BLE}. Implemented from Chaquopy via
 * {@code java.dynamic_proxy}.
 */
public interface PythonBluetooth {
    void on_error(String msg);

    void on_scan_started(boolean success);

    void on_scan_result(ScanResult result);

    void on_scan_completed();

    void on_services(int status, List<BluetoothGattService> services);

    void on_characteristic_changed(BluetoothGattCharacteristic characteristic);

    void on_characteristic_read(BluetoothGattCharacteristic characteristic, int status);

    void on_characteristic_write(BluetoothGattCharacteristic characteristic, int status);

    void on_descriptor_read(BluetoothGattDescriptor descriptor, int status);

    void on_descriptor_write(BluetoothGattDescriptor descriptor, int status);

    void on_connection_state_change(int status, int state);

    void on_bluetooth_adapter_state_change(int state);

    void on_rssi_updated(int rssi, int status);

    void on_mtu_changed(int mtu, int status);
}
