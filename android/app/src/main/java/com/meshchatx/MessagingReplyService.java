// SPDX-License-Identifier: 0BSD
package com.meshchatx;

import android.app.IntentService;
import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.text.TextUtils;

import androidx.annotation.Nullable;
import androidx.core.app.RemoteInput;

/**
 * Handles Android Auto (and notification) reply / mark-as-read actions.
 *
 * <p>Started only via PendingIntents owned by this app. Exported is false in the
 * manifest so other packages cannot forge these intents.
 */
public final class MessagingReplyService extends IntentService {
    public static final String ACTION_REPLY = "com.meshchatx.action.MESSAGE_REPLY";
    public static final String ACTION_MARK_AS_READ = "com.meshchatx.action.MESSAGE_MARK_AS_READ";

    public static final String EXTRA_DESTINATION_HASH = "destination_hash";
    public static final String REMOTE_INPUT_RESULT_KEY = "meshchatx_reply_input";

    public MessagingReplyService() {
        super("MessagingReplyService");
    }

    public static Intent replyIntent(Context ctx, String destinationHash) {
        Intent intent = new Intent(ctx, MessagingReplyService.class);
        intent.setAction(ACTION_REPLY);
        intent.putExtra(EXTRA_DESTINATION_HASH, destinationHash);
        return intent;
    }

    public static Intent markAsReadIntent(Context ctx, String destinationHash) {
        Intent intent = new Intent(ctx, MessagingReplyService.class);
        intent.setAction(ACTION_MARK_AS_READ);
        intent.putExtra(EXTRA_DESTINATION_HASH, destinationHash);
        return intent;
    }

    @Override
    protected void onHandleIntent(@Nullable Intent intent) {
        if (intent == null) {
            return;
        }
        String action = intent.getAction();
        String destinationHash = intent.getStringExtra(EXTRA_DESTINATION_HASH);
        if (TextUtils.isEmpty(destinationHash)) {
            return;
        }
        if (ACTION_MARK_AS_READ.equals(action)) {
            LocalApiClient.markConversationRead(this, destinationHash);
            AndroidNotificationBridge.cancelMessageNotifications(destinationHash);
            AndroidNotificationBridge.clearConversationMessageCache(destinationHash);
            return;
        }
        if (ACTION_REPLY.equals(action)) {
            CharSequence reply = extractReplyText(intent);
            if (reply == null || TextUtils.isEmpty(reply.toString().trim())) {
                return;
            }
            String text = reply.toString().trim();
            boolean sent = LocalApiClient.sendLxmfText(this, destinationHash, text);
            if (sent) {
                LocalApiClient.markConversationRead(this, destinationHash);
                AndroidNotificationBridge.cancelMessageNotifications(destinationHash);
                AndroidNotificationBridge.clearConversationMessageCache(destinationHash);
            }
        }
    }

    @Nullable
    static CharSequence extractReplyText(Intent intent) {
        Bundle results = RemoteInput.getResultsFromIntent(intent);
        if (results == null) {
            return null;
        }
        return results.getCharSequence(REMOTE_INPUT_RESULT_KEY);
    }
}
