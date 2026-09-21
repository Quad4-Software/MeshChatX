// SPDX-License-Identifier: 0BSD
package org.meshchatx.locallink;

import android.nfc.cardemulation.HostApduService;
import android.os.Bundle;
import android.util.Log;

import java.io.ByteArrayOutputStream;

/**
 * Host card emulation for MeshChatX NFC bootstrap sharing.
 *
 * Emulates a proprietary-AID card while the app sets a share payload. The
 * reader selects the AID, receives a length-prefixed header plus the first
 * data chunk, then pulls remaining chunks with GET NEXT. Payloads are small
 * bootstrap URIs (WiFi join credentials or contact URIs), never keys.
 */
public class NfcShareService extends HostApduService {

    private static final String TAG = "NfcShare-meshchatx";

    // AID F04D43585331: proprietary range prefix F0 then ASCII "MCXS1".
    private static final byte[] SELECT_AID = {
        0x00, (byte) 0xA4, 0x04, 0x00, 0x06,
        (byte) 0xF0, 0x4D, 0x43, 0x58, 0x53, 0x31,
    };
    private static final byte INS_GET_NEXT = 0x02;
    private static final byte[] SW_OK = {(byte) 0x90, 0x00};
    private static final byte[] SW_NOT_FOUND = {0x6A, (byte) 0x82};

    private static final int HEADER_LEN = 6; // "MCX1" + u16 total payload len
    private static final int MAX_PAYLOAD = 2048;
    private static final int MAX_RESPONSE_DATA = 245;

    private static volatile byte[] sPayload;

    public static void setPayload(byte[] payload) {
        if (payload != null && payload.length > MAX_PAYLOAD) {
            payload = null;
        }
        sPayload = payload;
    }

    public static void clearPayload() {
        sPayload = null;
    }

    private byte[] mPending;
    private int mOffset;

    @Override
    public byte[] processCommandApdu(byte[] apdu, Bundle extras) {
        if (apdu == null || apdu.length < 4) {
            return SW_NOT_FOUND;
        }
        if (isSelectAid(apdu)) {
            byte[] payload = sPayload;
            if (payload == null || payload.length == 0) {
                mPending = null;
                return SW_NOT_FOUND;
            }
            mPending = payload;
            mOffset = 0;
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            out.write('M');
            out.write('C');
            out.write('X');
            out.write('1');
            out.write((payload.length >> 8) & 0xFF);
            out.write(payload.length & 0xFF);
            int take = Math.min(payload.length, MAX_RESPONSE_DATA - HEADER_LEN);
            out.write(payload, 0, take);
            mOffset = take;
            return appendSw(out.toByteArray(), SW_OK);
        }
        if (apdu[1] == INS_GET_NEXT && mPending != null) {
            int remaining = mPending.length - mOffset;
            if (remaining <= 0) {
                mPending = null;
                return SW_OK;
            }
            int take = Math.min(remaining, MAX_RESPONSE_DATA);
            byte[] chunk = new byte[take];
            System.arraycopy(mPending, mOffset, chunk, 0, take);
            mOffset += take;
            return appendSw(chunk, SW_OK);
        }
        return SW_NOT_FOUND;
    }

    @Override
    public void onDeactivated(int reason) {
        mPending = null;
        mOffset = 0;
    }

    private static boolean isSelectAid(byte[] apdu) {
        if (apdu.length < SELECT_AID.length) {
            return false;
        }
        for (int i = 0; i < SELECT_AID.length; i++) {
            if (apdu[i] != SELECT_AID[i]) {
                return false;
            }
        }
        return true;
    }

    private static byte[] appendSw(byte[] data, byte[] sw) {
        byte[] out = new byte[data.length + sw.length];
        System.arraycopy(data, 0, out, 0, data.length);
        System.arraycopy(sw, 0, out, data.length, sw.length);
        return out;
    }
}
