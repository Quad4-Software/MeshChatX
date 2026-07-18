package com.meshchatx;

import org.junit.After;
import org.junit.Assert;
import org.junit.Test;

/**
 * Trusted call-notification actions must not be forgeable via exported MainActivity.
 */
public class CallNotificationTrustedActionTest {

    @After
    public void tearDown() {
        AndroidNotificationBridge.clearTrustedCallActionForTests();
    }

    @Test
    public void mapCallNotificationActionRecognizesAnswerDeclineOpen() {
        Assert.assertEquals(
            AndroidNotificationBridge.TRUSTED_CALL_ACTION_ANSWER,
            AndroidNotificationBridge.mapCallNotificationAction(
                AndroidNotificationBridge.ACTION_CALL_ANSWER
            )
        );
        Assert.assertEquals(
            AndroidNotificationBridge.TRUSTED_CALL_ACTION_DECLINE,
            AndroidNotificationBridge.mapCallNotificationAction(
                AndroidNotificationBridge.ACTION_CALL_DECLINE
            )
        );
        Assert.assertEquals(
            AndroidNotificationBridge.TRUSTED_CALL_ACTION_OPEN,
            AndroidNotificationBridge.mapCallNotificationAction(
                AndroidNotificationBridge.ACTION_CALL_OPEN
            )
        );
        Assert.assertNull(AndroidNotificationBridge.mapCallNotificationAction(null));
        Assert.assertNull(AndroidNotificationBridge.mapCallNotificationAction("android.intent.action.VIEW"));
        Assert.assertNull(
            AndroidNotificationBridge.mapCallNotificationAction("com.meshchatx.action.CALL_ATTACK")
        );
    }

    @Test
    public void offerAndTakeTrustedCallActionIsOneShot() {
        AndroidNotificationBridge.offerTrustedCallAction(
            AndroidNotificationBridge.TRUSTED_CALL_ACTION_ANSWER
        );
        Assert.assertEquals(
            AndroidNotificationBridge.TRUSTED_CALL_ACTION_ANSWER,
            AndroidNotificationBridge.takeTrustedCallAction()
        );
        Assert.assertNull(AndroidNotificationBridge.takeTrustedCallAction());
    }

    @Test
    public void offerTrustedCallActionRejectsUnknownTokens() {
        AndroidNotificationBridge.offerTrustedCallAction("initiate");
        AndroidNotificationBridge.offerTrustedCallAction("");
        AndroidNotificationBridge.offerTrustedCallAction(null);
        Assert.assertNull(AndroidNotificationBridge.takeTrustedCallAction());
    }

    @Test
    public void latestTrustedCallActionWins() {
        AndroidNotificationBridge.offerTrustedCallAction(
            AndroidNotificationBridge.TRUSTED_CALL_ACTION_ANSWER
        );
        AndroidNotificationBridge.offerTrustedCallAction(
            AndroidNotificationBridge.TRUSTED_CALL_ACTION_DECLINE
        );
        Assert.assertEquals(
            AndroidNotificationBridge.TRUSTED_CALL_ACTION_DECLINE,
            AndroidNotificationBridge.takeTrustedCallAction()
        );
    }
}
