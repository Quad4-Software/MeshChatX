// SPDX-License-Identifier: 0BSD
package org.meshchatx.locallink;

import android.app.Activity;
import android.nfc.NfcAdapter;
import android.nfc.Tag;
import android.nfc.tech.IsoDep;
import android.util.Log;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;

/**
 * NFC share manager for MeshChatX bootstrap payloads.
 *
 * Share side sets the payload that {@link NfcShareService} emits while a
 * reader selects our AID. Read side uses NFC reader mode while the Nearby
 * page is open and delivers the decoded payload text to Python.
 */
public class NfcShare {

    private static final String TAG = "NfcShare-meshchatx";

    private static final byte[] SELECT_AID = {
        0x00, (byte) 0xA4, 0x04, 0x00, 0x06,
        (byte) 0xF0, 0x4D, 0x43, 0x58, 0x53, 0x31,
    };
    private static final byte[] GET_NEXT = {0x00, 0x02, 0x00, 0x00, 0x00};
    private static final int MAX_PAYLOAD = 2048;

    private final Activity mActivity;
    private final PythonNfc mPython;
    private boolean mReading;

    public NfcShare(Activity activity, PythonNfc python) {
        mActivity = activity;
        mPython = python;
    }

    private NfcAdapter adapter() {
        return mActivity != null ? NfcAdapter.getDefaultAdapter(mActivity) : null;
    }

    // ------------------------------------------------------------------
    // Share side: payload served by NfcShareService to a tapping reader
    // ------------------------------------------------------------------

    public synchronized void setSharePayload(String payload) {
        if (payload == null || payload.isEmpty()
            || payload.getBytes(StandardCharsets.UTF_8).length > MAX_PAYLOAD) {
            NfcShareService.clearPayload();
            return;
        }
        NfcShareService.setPayload(payload.getBytes(StandardCharsets.UTF_8));
        if (mPython != null) {
            mPython.on_nfc_state("share_active");
        }
    }

    public synchronized void clearSharePayload() {
        NfcShareService.clearPayload();
        if (mPython != null) {
            mPython.on_nfc_state("off");
        }
    }

    // ------------------------------------------------------------------
    // Read side: reader mode while the Nearby page is open
    // ------------------------------------------------------------------

    public synchronized void startReader() {
        NfcAdapter adapter = adapter();
        if (adapter == null) {
            throw new IllegalStateException("nfc unavailable");
        }
        try {
            adapter.enableReaderMode(
                mActivity,
                new NfcAdapter.ReaderCallback() {
                    @Override
                    public void onTagDiscovered(Tag tag) {
                        handleTag(tag);
                    }
                },
                NfcAdapter.FLAG_READER_NFC_A
                    | NfcAdapter.FLAG_READER_NFC_B
                    | NfcAdapter.FLAG_READER_SKIP_NDEF_CHECK,
                null
            );
            mReading = true;
            if (mPython != null) {
                mPython.on_nfc_state("read_active");
            }
        } catch (Exception e) {
            throw new IllegalStateException("reader mode failed: " + e.getMessage(), e);
        }
    }

    public synchronized void stopReader() {
        NfcAdapter adapter = adapter();
        if (adapter != null && mReading) {
            try {
                adapter.disableReaderMode(mActivity);
            } catch (Exception e) {
                Log.w(TAG, "disableReaderMode failed", e);
            }
        }
        mReading = false;
        if (mPython != null) {
            mPython.on_nfc_state("off");
        }
    }

    private void handleTag(final Tag tag) {
        new Thread(
            () -> {
                IsoDep iso = IsoDep.get(tag);
                if (iso == null) {
                    return;
                }
                try {
                    iso.connect();
                    iso.setTimeout(3000);
                    byte[] response = iso.transceive(SELECT_AID);
                    String payload = readPayload(iso, response);
                    if (payload != null && mPython != null) {
                        mPython.on_nfc_payload(payload);
                    }
                } catch (IOException e) {
                    if (mPython != null) {
                        mPython.on_nfc_error("nfc read failed");
                    }
                } finally {
                    try {
                        iso.close();
                    } catch (IOException ignored) {
                    }
                }
            },
            "nfc-read"
        ).start();
    }

    private static String readPayload(IsoDep iso, byte[] selectResponse) throws IOException {
        if (selectResponse == null || selectResponse.length < 8) {
            return null;
        }
        int len = selectResponse.length;
        if (selectResponse[len - 2] != (byte) 0x90 || selectResponse[len - 1] != 0x00) {
            return null;
        }
        ByteArrayOutputStream body = new ByteArrayOutputStream();
        body.write(selectResponse, 0, len - 2);
        byte[] header = body.toByteArray();
        if (header.length < 6
            || header[0] != 'M' || header[1] != 'C' || header[2] != 'X' || header[3] != '1') {
            return null;
        }
        int total = ((header[4] & 0xFF) << 8) | (header[5] & 0xFF);
        if (total <= 0 || total > MAX_PAYLOAD) {
            return null;
        }
        ByteArrayOutputStream payload = new ByteArrayOutputStream();
        payload.write(header, 6, header.length - 6);
        while (payload.size() < total) {
            byte[] chunk = iso.transceive(GET_NEXT);
            if (chunk == null || chunk.length < 2
                || chunk[chunk.length - 2] != (byte) 0x90
                || chunk[chunk.length - 1] != 0x00) {
                return null;
            }
            if (chunk.length == 2) {
                break;
            }
            payload.write(chunk, 0, chunk.length - 2);
        }
        if (payload.size() != total) {
            return null;
        }
        return new String(payload.toByteArray(), StandardCharsets.UTF_8);
    }
}
