// SPDX-License-Identifier: 0BSD
package org.meshchatx.locallink;

/**
 * Python callback surface for {@link AwareSession}. Implemented from Chaquopy
 * via {@code java.dynamic_proxy}.
 */
public interface PythonAware {
    /**
     * Lifecycle event: "attached", "publish_started", "subscribe_started",
     * "session_lost", "stopped".
     */
    void on_aware_event(String what);

    /** A peer was discovered (subscriber side) or requested a path (publisher). */
    void on_aware_peer(int peerId);

    /** A data path socket is ready for framing; peerId identifies the peer. */
    void on_aware_link_up(int peerId);

    /** Raw bytes received on a peer socket. */
    void on_aware_data(int peerId, byte[] data);

    /** A peer socket closed or the data path was lost. */
    void on_aware_link_down(int peerId);

    void on_aware_error(String where, String message);
}
