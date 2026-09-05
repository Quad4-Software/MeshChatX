// SPDX-License-Identifier: 0BSD
package com.meshchatx;

import org.junit.After;
import org.junit.Assert;
import org.junit.Test;

/**
 * Android Auto messaging: destination hash validation and PendingIntent request codes.
 */
public class AndroidAutoMessagingTest {

    @After
    public void tearDown() {
        AndroidNotificationBridge.clearAllConversationMessageCacheForTests();
    }

    @Test
    public void normalizeDestinationHashAcceptsHex() {
        Assert.assertEquals(
            "abcdef0123456789abcdef0123456789",
            LocalApiClient.normalizeDestinationHash("ABCDEF0123456789abcdef0123456789")
        );
        Assert.assertEquals("abcd1234", LocalApiClient.normalizeDestinationHash("  abcd1234  "));
    }

    @Test
    public void normalizeDestinationHashRejectsGarbage() {
        Assert.assertNull(LocalApiClient.normalizeDestinationHash(null));
        Assert.assertNull(LocalApiClient.normalizeDestinationHash(""));
        Assert.assertNull(LocalApiClient.normalizeDestinationHash("short"));
        Assert.assertNull(LocalApiClient.normalizeDestinationHash("zzzzzzzz"));
        Assert.assertNull(LocalApiClient.normalizeDestinationHash("abcd-1234"));
        StringBuilder tooLong = new StringBuilder();
        for (int i = 0; i < 65; i++) {
            tooLong.append('a');
        }
        Assert.assertNull(LocalApiClient.normalizeDestinationHash(tooLong.toString()));
    }

    @Test
    public void replyAndMarkRequestCodesAreStablePerConversation() {
        String hash = "abcdef0123456789abcdef0123456789";
        Assert.assertEquals(
            AndroidNotificationBridge.replyRequestCode(hash),
            AndroidNotificationBridge.replyRequestCode(hash)
        );
        Assert.assertEquals(
            AndroidNotificationBridge.markAsReadRequestCode(hash),
            AndroidNotificationBridge.markAsReadRequestCode(hash)
        );
        Assert.assertNotEquals(
            AndroidNotificationBridge.replyRequestCode(hash),
            AndroidNotificationBridge.markAsReadRequestCode(hash)
        );
        Assert.assertNotEquals(
            AndroidNotificationBridge.replyRequestCode(hash),
            AndroidNotificationBridge.replyRequestCode("fedcba9876543210fedcba9876543210")
        );
    }

    @Test
    public void messagingReplyServiceActionConstants() {
        Assert.assertEquals(
            "com.meshchatx.action.MESSAGE_REPLY",
            MessagingReplyService.ACTION_REPLY
        );
        Assert.assertEquals(
            "com.meshchatx.action.MESSAGE_MARK_AS_READ",
            MessagingReplyService.ACTION_MARK_AS_READ
        );
        Assert.assertEquals("destination_hash", MessagingReplyService.EXTRA_DESTINATION_HASH);
        Assert.assertEquals("meshchatx_reply_input", MessagingReplyService.REMOTE_INPUT_RESULT_KEY);
    }
}
