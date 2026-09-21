// SPDX-License-Identifier: 0BSD
package org.meshchatx.locallink;

/**
 * Python callback surface for {@link NfcShare}. Implemented from Chaquopy via
 * {@code java.dynamic_proxy}.
 */
public interface PythonNfc {
    /** A complete payload was read from a peer's emulated card. */
    void on_nfc_payload(String payload);

    /** Reader state changed: "read_active", "share_active", "off". */
    void on_nfc_state(String state);

    void on_nfc_error(String message);
}
