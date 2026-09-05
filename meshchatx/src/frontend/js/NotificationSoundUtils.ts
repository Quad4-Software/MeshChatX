export interface NotificationSoundStatus {
    enabled?: boolean;
    has_sound?: boolean;
    id?: number | string | null;
    filename?: string | null;
    volume?: number;
}

class NotificationSoundUtils {
    static _player = null;
    static autoplayBlocked = false;

    static isSupported() {
        return typeof window !== "undefined" && typeof Audio !== "undefined";
    }

    static shouldPlay(config) {
        return Boolean(config?.notification_sound_enabled);
    }

    static _normalizeVolume(volume) {
        if (typeof volume !== "number" || Number.isNaN(volume)) {
            return 1;
        }
        return Math.min(1, Math.max(0, volume));
    }

    static stop() {
        if (!NotificationSoundUtils._player) {
            return;
        }
        try {
            NotificationSoundUtils._player.pause();
            NotificationSoundUtils._player.currentTime = 0;
        } catch {
            // ignore pause errors
        }
        NotificationSoundUtils._player = null;
    }

    static unlockAutoplay() {
        if (!NotificationSoundUtils.autoplayBlocked) {
            return;
        }
        NotificationSoundUtils.autoplayBlocked = false;
    }

    static async _fetchStatus(): Promise<NotificationSoundStatus | null> {
        if (typeof window === "undefined" || !window.api) {
            return null;
        }
        const response = await window.api.get("/api/v1/notification-sounds/status");
        return (response?.data as NotificationSoundStatus | undefined) ?? null;
    }

    static async play(config) {
        if (!NotificationSoundUtils.isSupported()) {
            return false;
        }
        if (!NotificationSoundUtils.shouldPlay(config)) {
            return false;
        }
        if (NotificationSoundUtils.autoplayBlocked) {
            return false;
        }

        try {
            const status = await NotificationSoundUtils._fetchStatus();
            if (!status?.enabled || !status?.has_sound || !status?.id) {
                return false;
            }

            NotificationSoundUtils.stop();

            const player = new Audio(`/api/v1/notification-sounds/${status.id}/audio`);
            player.loop = false;
            player.volume = NotificationSoundUtils._normalizeVolume(
                status.volume ?? config.notification_sound_volume / 100.0
            );

            player.onended = () => {
                if (NotificationSoundUtils._player === player) {
                    NotificationSoundUtils._player = null;
                }
            };

            NotificationSoundUtils._player = player;
            await player.play();
            return true;
        } catch (error) {
            if (error?.name === "NotAllowedError") {
                NotificationSoundUtils.autoplayBlocked = true;
                return false;
            }
            console.warn("Failed to play notification sound:", error);
            return false;
        }
    }

    static async preview(soundId, volumePercent = 100) {
        if (!NotificationSoundUtils.isSupported() || !soundId) {
            return false;
        }

        NotificationSoundUtils.stop();

        try {
            const player = new Audio(`/api/v1/notification-sounds/${soundId}/audio`);
            player.loop = false;
            player.volume = NotificationSoundUtils._normalizeVolume(volumePercent / 100.0);
            player.onended = () => {
                if (NotificationSoundUtils._player === player) {
                    NotificationSoundUtils._player = null;
                }
            };
            NotificationSoundUtils._player = player;
            await player.play();
            NotificationSoundUtils.unlockAutoplay();
            return true;
        } catch (error) {
            if (error?.name === "NotAllowedError") {
                NotificationSoundUtils.autoplayBlocked = true;
                return false;
            }
            console.warn("Failed to preview notification sound:", error);
            return false;
        }
    }
}

export default NotificationSoundUtils;
