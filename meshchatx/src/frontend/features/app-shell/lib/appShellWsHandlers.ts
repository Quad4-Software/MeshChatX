// SPDX-License-Identifier: 0BSD

/**
 * Shell-level WebSocket handlers, ported from App.vue getShellWsHandlers.
 * Kept out of the component so the map stays readable and testable.
 */

import GlobalState, { mergeGlobalConfig } from "../../../js/GlobalState.js";
import LiveTransport from "../../../js/liveTransport.js";
import ToastUtils from "../../../js/ToastUtils.js";
import NotificationUtils from "../../../js/NotificationUtils.js";
import NotificationSoundUtils from "../../../js/NotificationSoundUtils.js";
import KeyboardShortcuts from "../../../js/KeyboardShortcuts.js";
import ElectronUtils from "../../../js/ElectronUtils.js";
import { t } from "../../../js/i18n.js";
import {
    deliverySourceHash,
    isUserFacingLxmfDeliveryMessage,
    shouldPlayMessageSound,
    shouldShowOsMessageNotification,
} from "../../../js/notificationPolicy.js";
import { listOpenDestinationHashes } from "../../../js/activeConversationStore.js";
import { showDatabaseHealthIssuesToastIfNeeded } from "../../../js/databaseHealthWarning.js";
import { handleHealthWarningPayload } from "../../../js/healthMemoryWarning.js";
import { handleLxmIngestUriResult } from "../../../js/ingestUriResultNavigation.js";
import { navigate, router } from "../../../shell/hashRouter.js";
import type { AppShellState } from "./appShellState.svelte.js";
import { handleActiveSessionsUpdated } from "./appShellNav.js";
import { applyAnnouncedEvent, resolvePendingConfigSet, setConfig } from "./appShellConfig.js";
import { applyIdentitySwitched } from "./appShellIdentity.js";
import { playRingtone, stopRingtone, updateTelephoneStatus } from "./appShellTelephony.js";

type WsHandler = (payload: any) => void | Promise<void>;

/**
 * Build the WS type to handler map for a shell instance.
 */
export function createShellWsHandlers(state: AppShellState): Record<string, WsHandler> {
    return {
        error: (json) => {
            const code = json?.code;
            if (code === "auth_required") {
                GlobalState.authenticated = false;
                if (state.routeName !== "auth") {
                    void navigate("/auth");
                }
                ToastUtils.error(t("app.live_auth_required"));
                return;
            }
            if (code === "rate_limited") {
                ToastUtils.warning(json?.message || t("app.live_rate_limited"));
                return;
            }
            if (code === "config_set_failed") {
                ToastUtils.error(t("common.save_failed"));
                return;
            }
            if (json?.message) {
                ToastUtils.warning(String(json.message));
            }
        },
        "config.set": (json) => {
            if (json?.status === "success" && json?.request_id) {
                resolvePendingConfigSet(state, json.request_id);
            }
        },
        config: (json) => {
            const next = json?.config;
            if (next && typeof next === "object") {
                mergeGlobalConfig(next);
                setConfig(state, next);
                LiveTransport.configure({ mode: next.live_transport_mode || "auto" });
            }
        },
        "app.sessions.updated": (json) => {
            handleActiveSessionsUpdated(state, json);
        },
        keyboard_shortcuts: (json) => {
            KeyboardShortcuts.setShortcuts(json.shortcuts);
        },
        announced: (json) => {
            applyAnnouncedEvent(state, json);
        },
        telephone_ringing: (json) => {
            if (state.config?.do_not_disturb_enabled) {
                return;
            }
            if (
                (state.config?.telephone_allow_calls_from_contacts_only || state.config?.block_all_from_strangers) &&
                !json.is_contact
            ) {
                return;
            }
            if (state.initiationStatus) {
                return;
            }
            NotificationUtils.showIncomingCallNotification(json.remote_identity_name || json.remote_identity_hash);
            void updateTelephoneStatus(state);
            playRingtone(state);
        },
        telephone_missed_call: (json) => {
            NotificationUtils.showMissedCallNotification(json.remote_identity_name || json.remote_identity_hash);
            void updateTelephoneStatus(state);
        },
        telephone_initiation_status: (json) => {
            state.initiationStatus = json.status;
            state.initiationTargetHash = json.target_hash;
            state.initiationTargetName = json.target_name;

            if (state.initiationStatus === "Ringing...") {
                if (state.config?.telephone_tone_generator_enabled) {
                    state.toneGenerator.setVolume(state.config.telephone_tone_generator_volume);
                    state.toneGenerator.playRingback();
                }
            } else if (state.initiationStatus === null) {
                state.toneGenerator.stop();
            }
        },
        new_voicemail: (json) => {
            NotificationUtils.showNewVoicemailNotification(json.remote_identity_name || json.remote_identity_hash);
            void updateTelephoneStatus(state);
        },
        telephone_call_established: () => {
            stopRingtone(state);
            state.ringtonePlayer = null;
            state.toneGenerator.stop();
            NotificationUtils.cancelIncomingCallNotification();
            void updateTelephoneStatus(state);
            // Ensure CallPage is mounted so Android native audio / web audio can
            // attach after answering from the overlay or a notification.
            if (state.routeName !== "call" || state.route?.query?.tab !== "phone") {
                void navigate({ name: "call", query: { tab: "phone" } });
            }
        },
        telephone_call_ended: async () => {
            stopRingtone(state);
            NotificationUtils.cancelIncomingCallNotification();
            state.ringtonePlayer = null;
            if (state.config?.telephone_tone_generator_enabled) {
                state.toneGenerator.setVolume(state.config.telephone_tone_generator_volume);
                state.toneGenerator.playBusyTone();
            }
            await updateTelephoneStatus(state, { forceHistoryRefresh: true });
        },
        blocked_destinations: (json) => {
            GlobalState.blockedDestinations = json.blocked_destinations || [];
        },
        "rrc.message": (json) => {
            if (json.mention || json.message?.mention) {
                state.updateRelayChatUnreadCount();
            }
        },
        "rrc.change": () => {
            state.updateRelayChatUnreadCount();
        },
        "lxmf.delivery": async (json) => {
            if (json.sieve_suppress_notifications) {
                return;
            }
            const lxmfMessage = json.lxmf_message;
            const isIncoming = lxmfMessage?.is_incoming === true;
            const userFacing = isUserFacingLxmfDeliveryMessage(lxmfMessage);
            const sourceHash = deliverySourceHash(json);
            const openHashes = listOpenDestinationHashes();
            const sourceOpen = openHashes.includes(String(sourceHash || "").toLowerCase());
            // Minimized Electron windows often keep hasFocus true while
            // visibilityState is hidden. Require both for "in foreground".
            const hasFocus =
                typeof document !== "undefined"
                    ? document.visibilityState !== "hidden" && document.hasFocus()
                    : true;
            const policyBase = {
                isIncoming,
                sieveSuppress: Boolean(json.sieve_suppress_notifications),
                dnd: Boolean(state.config?.do_not_disturb_enabled),
                hasFocus,
                openDestinationHashes: openHashes,
                sourceHash,
                userFacing,
            };

            // DND suppresses OS notifications and sound only. The unread badge must
            // still refresh so the Messages nav does not freeze while DND is on.
            if (isIncoming && userFacing && !sourceOpen) {
                state.updateUnreadConversationsCount();
            }

            let playedNotificationSound = false;
            if (shouldPlayMessageSound(policyBase)) {
                playedNotificationSound = await NotificationSoundUtils.play(state.config);
            }
            if (shouldShowOsMessageNotification(policyBase)) {
                NotificationUtils.showNewMessageNotification(
                    json.remote_identity_name,
                    lxmfMessage?.content || lxmfMessage?.title || "",
                    playedNotificationSound,
                    sourceHash
                );
            }
        },
        "lxm.ingest_uri.result": async (json) => {
            const handled = await handleLxmIngestUriResult(json, {
                router,
                toast: ToastUtils,
            });
            if (handled) {
                return;
            }
            if (json.status === "success") {
                ToastUtils.success(json.message);
            } else if (json.status === "error") {
                ToastUtils.error(json.message);
            } else if (json.status === "warning") {
                ToastUtils.warning(json.message);
            } else {
                ToastUtils.info(json.message);
            }
        },
        database_health_warning: (json) => {
            showDatabaseHealthIssuesToastIfNeeded(json.issues, ToastUtils);
        },
        health_warning: (json) => {
            handleHealthWarningPayload(json, ToastUtils);
        },
        identity_switched: async (json) => {
            await applyIdentitySwitched(state, json);
        },
        "rncp.receive.completed": (json) => {
            if (state.routeName !== "rncp") {
                const detail =
                    json.status === "completed" && json.saved_path ? json.saved_path : json.error || json.status || "";
                if (json.status === "completed") {
                    ToastUtils.success(`${t("rncp.received_file")}${detail ? ": " + detail : ""}`);
                    if (ElectronUtils.isElectron()) {
                        ElectronUtils.showNotification(t("rncp.received_file"), detail || "");
                    }
                } else {
                    ToastUtils.error(`${t("rncp.receive_failed")}${detail ? ": " + detail : ""}`);
                }
            }
        },
    };
}
