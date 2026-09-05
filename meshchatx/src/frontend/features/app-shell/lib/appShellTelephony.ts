// SPDX-License-Identifier: 0BSD

/**
 * Ringtone playback and telephone status polling for the shell call chrome.
 */

import GlobalState from "../../../js/GlobalState.js";
import GlobalEmitter from "../../../js/GlobalEmitter.js";
import NotificationSoundUtils from "../../../js/NotificationSoundUtils.js";
import ElectronUtils from "../../../js/ElectronUtils.js";
import { apiClient, electronBridge } from "./appShellShared.js";
import type { AppShellState } from "./appShellState.svelte.js";

// Telephony chrome
// ------------------------------------------------------------------
export function onRingtoneUnlockGesture(state: AppShellState): void {
    NotificationSoundUtils.unlockAutoplay();
    if (!state.ringtoneAutoplayBlocked) {
        return;
    }
    state.ringtoneAutoplayBlocked = false;
    if (state.activeCall?.status === 4 && state.activeCall?.is_incoming) {
        playRingtone(state);
    }
}

export async function updateRingtonePlayer(state: AppShellState): Promise<void> {
    if (state.ringtonePlayer) {
        state.ringtonePlayer.pause();
        state.ringtonePlayer = null;
    }
    if (state.config?.custom_ringtone_enabled) {
        try {
            const response = await apiClient().get("/api/v1/telephone/ringtones/status");
            const status = response.data;
            if (status.has_custom_ringtone && status.id) {
                state.ringtonePlayer = new Audio(`/api/v1/telephone/ringtones/${status.id}/audio`);
                state.ringtonePlayer.loop = true;
                if (status.volume !== undefined) {
                    state.ringtonePlayer.volume = status.volume;
                }
            }
        } catch (e) {
            console.error("Failed to update ringtone player:", e);
        }
    }
}

export function playRingtone(state: AppShellState): void {
    if (!state.ringtonePlayer || state.ringtoneAutoplayBlocked) {
        return;
    }
    if (state.ringtonePlayer.paused) {
        state.ringtonePlayer.play().catch((e: { name?: string }) => {
            if (e?.name === "NotAllowedError") {
                // Browser autoplay policy blocked playback until user gesture.
                state.ringtoneAutoplayBlocked = true;
                return;
            }
            console.warn("Failed to play custom ringtone:", e);
        });
    }
}

export function stopRingtone(state: AppShellState): void {
    if (state.ringtonePlayer) {
        try {
            state.ringtonePlayer.pause();
            state.ringtonePlayer.currentTime = 0;
        } catch {
            // ignore errors during pause
        }
    }
}

export async function updateTelephoneStatus(
    state: AppShellState,
    options: { forceHistoryRefresh?: boolean } = {}
): Promise<void> {
    try {
        const response = await apiClient().get("/api/v1/telephone/status");
        const oldCall = state.activeCall;
        const newCall = response.data.active_call;

        state.activeCall = newCall;
        if (state.activeCall) {
            state.toneGenerator.stop();
        }
        state.voicemailStatus = response.data.voicemail;
        state.initiationStatus = response.data.initiation_status;
        state.initiationTargetHash = response.data.initiation_target_hash;
        state.initiationTargetName = response.data.initiation_target_name;
        GlobalState.missedCallsCount = response.data?.missed_calls_unread_count ?? 0;

        const justEnded = oldCall != null && state.activeCall == null;
        const forceHistory = options.forceHistoryRefresh === true;
        if (justEnded || forceHistory) {
            if (justEnded) {
                state.lastCall = oldCall;
                if (state.config?.telephone_tone_generator_enabled) {
                    state.toneGenerator.setVolume(state.config.telephone_tone_generator_volume);
                    state.toneGenerator.playBusyTone();
                }
            }

            GlobalEmitter.emit("telephone-history-updated");

            if (justEnded && !state.wasDeclined) {
                state.isCallEnded = true;
            }

            if (justEnded) {
                if (state.endedTimeout) {
                    clearTimeout(state.endedTimeout);
                }
                state.endedTimeout = setTimeout(() => {
                    state.isCallEnded = false;
                    state.wasDeclined = false;
                    state.lastCall = null;
                }, 5000);
            }
        }

        if (state.initiationStatus === "Ringing...") {
            if (state.config?.telephone_tone_generator_enabled) {
                state.toneGenerator.setVolume(state.config.telephone_tone_generator_volume);
                state.toneGenerator.playRingback();
            }
        } else if (!state.initiationStatus && !state.activeCall && !state.isCallEnded) {
            // Only stop if we are not ringing, in a call, or just finished a call
            state.toneGenerator.stop();
        }

        if (ElectronUtils.isElectron()) {
            const electron = electronBridge();
            if (state.activeCall) {
                electron?.setPowerSaveBlocker(true);
            } else if (!state.initiationStatus) {
                electron?.setPowerSaveBlocker(false);
            }
        }

        const meta = (state.route?.meta || {}) as { isPopout?: boolean };
        if (
            (state.activeCall || state.initiationStatus) &&
            state.config?.desktop_open_calls_in_separate_window &&
            ElectronUtils.isElectron()
        ) {
            if (!state.isCallWindowOpen && !meta.isPopout) {
                state.isCallWindowOpen = true;
                window.open("/call.html", "MeshChatXCallWindow", "width=600,height=800");
            }
        } else {
            state.isCallWindowOpen = false;
        }

        if (state.activeCall?.status === 4 && state.activeCall?.is_incoming) {
            if (!state.ringtonePlayer && state.config?.custom_ringtone_enabled && !state.isFetchingRingtone) {
                state.isFetchingRingtone = true;
                try {
                    const callerHash = state.activeCall.remote_identity_hash;
                    const ringResponse = await apiClient().get(
                        `/api/v1/telephone/ringtones/status?caller_hash=${callerHash}`
                    );
                    const status = ringResponse.data;
                    if (status.has_custom_ringtone && status.id) {
                        // Double check the call did not end during the await.
                        if (state.activeCall?.status === 4) {
                            stopRingtone(state);
                            state.ringtonePlayer = new Audio(`/api/v1/telephone/ringtones/${status.id}/audio`);
                            state.ringtonePlayer.loop = true;
                            if (status.volume !== undefined) {
                                state.ringtonePlayer.volume = status.volume;
                            }
                            playRingtone(state);
                        }
                    }
                } finally {
                    state.isFetchingRingtone = false;
                }
            } else if (state.ringtonePlayer && state.activeCall?.status === 4) {
                playRingtone(state);
            }
        } else if (state.ringtonePlayer) {
            stopRingtone(state);
            state.ringtonePlayer = null;
        }

        if (newCall && oldCall) {
            newCall.is_mic_muted = oldCall.is_mic_muted;
            newCall.is_speaker_muted = oldCall.is_speaker_muted;
        }

        if (justEnded) {
            // handled above
        } else if (state.activeCall != null) {
            state.isCallEnded = false;
            state.wasDeclined = false;
            state.lastCall = null;
            if (state.endedTimeout) {
                clearTimeout(state.endedTimeout);
            }
        } else if (!state.endedTimeout) {
            state.isCallEnded = false;
            state.wasDeclined = false;
            state.lastCall = null;
        }
    } catch {
        // do nothing on error
    }
}

export function onOverlayHangup(state: AppShellState): void {
    if (state.activeCall && state.activeCall.is_incoming && state.activeCall.status === 4) {
        state.wasDeclined = true;
    }
}

export function onToggleMic(state: AppShellState, isMuted: boolean): void {
    if (state.activeCall) {
        state.activeCall.is_mic_muted = isMuted;
    }
}

export function onToggleSpeaker(state: AppShellState, isMuted: boolean): void {
    if (state.activeCall) {
        state.activeCall.is_speaker_muted = isMuted;
    }
}
