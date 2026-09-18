// SPDX-License-Identifier: 0BSD
package org.meshchatx.locallink;

/**
 * Python callback surface for {@link LocalLink}. Implemented from Chaquopy via
 * {@code java.dynamic_proxy}.
 */
public interface PythonLocalLink {
    void on_hotspot_started(String ssid, String passphrase, int securityType);

    void on_hotspot_failed(int errorCode);

    void on_hotspot_stopped();

    void on_p2p_group_started(String ssid, String passphrase);

    void on_p2p_group_failed(String reason);

    void on_p2p_group_stopped();

    void on_join_status(String status);

    void on_error(String where, String message);
}
