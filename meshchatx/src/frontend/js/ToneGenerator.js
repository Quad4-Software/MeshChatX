export default class ToneGenerator {
    constructor() {
        this.audioCtx = null;
        this.oscillator = null;
        this.gainNode = null;
        this.timeoutId = null;
        this.currentTone = null; // 'ringback', 'busy', or null
        this.volume = 0.1; // Default volume (0.0 to 1.0 real gain)
    }

    setVolume(volumePercent) {
        // volumePercent is 0-100
        this.volume = (volumePercent / 100) * 0.2; // Cap at 0.2 real gain for safety
        if (this.gainNode && this.audioCtx) {
            this.gainNode.gain.setTargetAtTime(this.volume, this.audioCtx.currentTime, 0.1);
        }
    }

    _initAudioContext() {
        if (!this.audioCtx) {
            this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            
            // Create a high-quality output chain
            this.masterCompressor = this.audioCtx.createDynamicsCompressor();
            this.masterCompressor.threshold.setValueAtTime(-24, this.audioCtx.currentTime);
            this.masterCompressor.knee.setValueAtTime(30, this.audioCtx.currentTime);
            this.masterCompressor.ratio.setValueAtTime(12, this.audioCtx.currentTime);
            this.masterCompressor.attack.setValueAtTime(0.003, this.audioCtx.currentTime);
            this.masterCompressor.release.setValueAtTime(0.25, this.audioCtx.currentTime);

            this.masterFilter = this.audioCtx.createBiquadFilter();
            this.masterFilter.type = "lowpass";
            this.masterFilter.frequency.setValueAtTime(4000, this.audioCtx.currentTime);
            this.masterFilter.Q.setValueAtTime(0.7, this.audioCtx.currentTime);

            this.masterCompressor.connect(this.masterFilter);
            this.masterFilter.connect(this.audioCtx.destination);
        }
    }

    playRingback() {
        if (this.currentTone === "ringback") return;
        this._initAudioContext();
        this.stop();
        this.currentTone = "ringback";

        const play = () => {
            const osc1 = this.audioCtx.createOscillator();
            const osc2 = this.audioCtx.createOscillator();
            const sub = this.audioCtx.createOscillator();
            
            const panner1 = this.audioCtx.createStereoPanner();
            const panner2 = this.audioCtx.createStereoPanner();
            const gain = this.audioCtx.createGain();
            const subGain = this.audioCtx.createGain();

            // Main frequencies
            osc1.type = "sine";
            osc1.frequency.setValueAtTime(440, this.audioCtx.currentTime);
            
            osc2.type = "sine";
            osc2.frequency.setValueAtTime(480, this.audioCtx.currentTime);

            // Sub layer for depth and "feel"
            sub.type = "sine";
            sub.frequency.setValueAtTime(40, this.audioCtx.currentTime);
            subGain.gain.setValueAtTime(0.05, this.audioCtx.currentTime);

            // Stereo separation for quality headphones
            panner1.pan.setValueAtTime(-0.4, this.audioCtx.currentTime);
            panner2.pan.setValueAtTime(0.4, this.audioCtx.currentTime);

            osc1.connect(panner1);
            panner1.connect(gain);
            osc2.connect(panner2);
            panner2.connect(gain);
            
            sub.connect(subGain);
            subGain.connect(gain);

            gain.gain.setValueAtTime(0, this.audioCtx.currentTime);
            gain.gain.linearRampToValueAtTime(this.volume, this.audioCtx.currentTime + 0.1);

            gain.connect(this.masterCompressor);

            osc1.start();
            osc2.start();
            sub.start();

            this.oscillator = [osc1, osc2, sub];
            this.gainNode = gain;

            // Stop after 2 seconds with a smooth fade-out
            setTimeout(() => {
                if (Array.isArray(this.oscillator) && this.oscillator.includes(osc1)) {
                    gain.gain.exponentialRampToValueAtTime(0.001, this.audioCtx.currentTime + 0.5);
                    setTimeout(() => {
                        osc1.stop();
                        osc2.stop();
                        sub.stop();
                        osc1.disconnect();
                        osc2.disconnect();
                        sub.disconnect();
                        subGain.disconnect();
                        panner1.disconnect();
                        panner2.disconnect();
                        gain.disconnect();
                    }, 500);
                }
            }, 2000);

            // Repeat every 6 seconds
            this.timeoutId = setTimeout(play, 6000);
        };

        play();
    }

    playBusyTone() {
        if (this.currentTone === "busy") return;
        this._initAudioContext();
        this.stop();
        this.currentTone = "busy";

        const play = () => {
            const osc = this.audioCtx.createOscillator();
            const sub = this.audioCtx.createOscillator();
            const gain = this.audioCtx.createGain();
            const subGain = this.audioCtx.createGain();

            osc.type = "sine";
            osc.frequency.setValueAtTime(480, this.audioCtx.currentTime);

            sub.type = "sine";
            sub.frequency.setValueAtTime(40, this.audioCtx.currentTime);
            subGain.gain.setValueAtTime(0.05, this.audioCtx.currentTime);

            osc.connect(gain);
            sub.connect(subGain);
            subGain.connect(gain);

            gain.gain.setValueAtTime(0, this.audioCtx.currentTime);
            gain.gain.linearRampToValueAtTime(this.volume, this.audioCtx.currentTime + 0.05);

            gain.connect(this.masterCompressor);

            osc.start();
            sub.start();

            this.oscillator = [osc, sub];
            this.gainNode = gain;

            // Stop after 0.5 seconds with a short fade
            setTimeout(() => {
                if (Array.isArray(this.oscillator) && this.oscillator.includes(osc)) {
                    gain.gain.exponentialRampToValueAtTime(0.001, this.audioCtx.currentTime + 0.1);
                    setTimeout(() => {
                        osc.stop();
                        sub.stop();
                        osc.disconnect();
                        sub.disconnect();
                        subGain.disconnect();
                        gain.disconnect();
                    }, 100);
                }
            }, 500);

            // Repeat every 1 second
            this.timeoutId = setTimeout(play, 1000);
        };

        play();

        // Auto-stop busy tone after 4 seconds (4 cycles)
        setTimeout(() => this.stop(), 4000);
    }

    stop() {
        this.currentTone = null;
        if (this.timeoutId) {
            clearTimeout(this.timeoutId);
            this.timeoutId = null;
        }

        if (this.oscillator) {
            if (Array.isArray(this.oscillator)) {
                this.oscillator.forEach((osc) => {
                    try {
                        osc.stop();
                    } catch {
                        // Ignore errors if oscillator is already stopped or disconnected
                    }
                    try {
                        osc.disconnect();
                    } catch {
                        // Ignore errors if oscillator is already disconnected
                    }
                });
            } else {
                try {
                    this.oscillator.stop();
                } catch {
                    // Ignore errors if oscillator is already stopped or disconnected
                }
                try {
                    this.oscillator.disconnect();
                } catch {
                    // Ignore errors if oscillator is already disconnected
                }
            }
            this.oscillator = null;
        }

        if (this.gainNode) {
            try {
                this.gainNode.disconnect();
            } catch {
                // Ignore errors if gain node is already disconnected
            }
            this.gainNode = null;
        }
    }
}
