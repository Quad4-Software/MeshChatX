package com.meshchatx;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;

/**
 * Non-exported trampoline for incoming-call notification actions.
 *
 * <p>PendingIntents for answer/decline must not target the exported {@link MainActivity}.
 * Same-profile apps can forge intents to exported activities. This component stays
 * package-private so only our notification PendingIntents can start it.
 */
public final class CallNotificationTrampolineActivity extends Activity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        Intent inbound = getIntent();
        String action = inbound != null ? inbound.getAction() : null;
        String trusted = AndroidNotificationBridge.mapCallNotificationAction(action);
        if (trusted != null) {
            AndroidNotificationBridge.offerTrustedCallAction(trusted);
        }

        Intent main = new Intent(this, MainActivity.class);
        main.addFlags(
            Intent.FLAG_ACTIVITY_NEW_TASK
                | Intent.FLAG_ACTIVITY_CLEAR_TOP
                | Intent.FLAG_ACTIVITY_SINGLE_TOP
        );
        try {
            startActivity(main);
        } catch (Exception ignored) {
        }
        finish();
    }
}
