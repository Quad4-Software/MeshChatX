/**
 * A simple class for recording microphone input and returning the audio.
 */
class MicrophoneRecorder {
    constructor() {
        this.audioChunks = [];
        this.microphoneMediaStream = null;
        this.mediaRecorder = null;
    }

    cleanupMediaStream() {
        if (!this.microphoneMediaStream) {
            return;
        }
        this.microphoneMediaStream.getTracks().forEach((track) => {
            try {
                track.stop();
            } catch {
                // ignore track stop failures
            }
        });
        this.microphoneMediaStream = null;
    }

    async start() {
        try {
            this.audioChunks = [];
            if (!navigator?.mediaDevices || typeof navigator.mediaDevices.getUserMedia !== "function") {
                return false;
            }
            if (typeof MediaRecorder !== "function") {
                return false;
            }

            // request access to the microphone
            this.microphoneMediaStream = await navigator.mediaDevices.getUserMedia({
                audio: true,
            });

            // create media recorder
            this.mediaRecorder = new MediaRecorder(this.microphoneMediaStream);

            // handle received audio from media recorder
            this.mediaRecorder.ondataavailable = (event) => {
                if (event?.data) {
                    this.audioChunks.push(event.data);
                }
            };

            // start recording
            this.mediaRecorder.start();

            // successfully started recording
            return true;
        } catch {
            this.cleanupMediaStream();
            this.mediaRecorder = null;
            return false;
        }
    }

    async stop() {
        return new Promise((resolve, reject) => {
            if (!this.mediaRecorder) {
                reject(new Error("Cannot stop recording before start()"));
                return;
            }

            const recorder = this.mediaRecorder;

            // handle media recording stopped
            recorder.onstop = () => {
                const blob = new Blob(this.audioChunks, {
                    type: recorder.mimeType || "audio/webm;codecs=opus",
                });
                this.mediaRecorder = null;
                this.cleanupMediaStream();
                resolve(blob);
            };
            recorder.onerror = (event) => {
                this.mediaRecorder = null;
                this.cleanupMediaStream();
                reject(event?.error || new Error("MediaRecorder error while stopping"));
            };

            try {
                // stop recording
                recorder.stop();
            } catch (e) {
                this.mediaRecorder = null;
                this.cleanupMediaStream();
                reject(e);
            }
        });
    }
}

export default MicrophoneRecorder;
