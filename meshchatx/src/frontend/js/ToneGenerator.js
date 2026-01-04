export default class ToneGenerator {
    constructor() {
        this.audioCtx = null;
        this.oscillator = null;
        this.gainNode = null;
        this.timeoutId = null;
    }

    _initAudioContext() {
        if (!this.audioCtx) {
            this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
    }

    playRingback() {
        this._initAudioContext();
        this.stop();

        const play = () => {
            const osc1 = this.audioCtx.createOscillator();
            const osc2 = this.audioCtx.createOscillator();
            const gain = this.audioCtx.createGain();

            osc1.frequency.value = 440;
            osc2.frequency.value = 480;
            gain.gain.value = 0.1;

            osc1.connect(gain);
            osc2.connect(gain);
            gain.connect(this.audioCtx.destination);

            osc1.start();
            osc2.start();

            this.oscillator = [osc1, osc2];
            this.gainNode = gain;

            // Stop after 2 seconds
            setTimeout(() => {
                if (this.oscillator === osc1 || (Array.isArray(this.oscillator) && this.oscillator.includes(osc1))) {
                    gain.gain.exponentialRampToValueAtTime(0.001, this.audioCtx.currentTime + 0.5);
                    setTimeout(() => {
                        osc1.stop();
                        osc2.stop();
                        osc1.disconnect();
                        osc2.disconnect();
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
        this._initAudioContext();
        this.stop();

        const play = () => {
            const osc = this.audioCtx.createOscillator();
            const gain = this.audioCtx.createGain();

            osc.frequency.value = 480;
            gain.gain.value = 0.1;

            osc.connect(gain);
            gain.connect(this.audioCtx.destination);

            osc.start();

            this.oscillator = osc;
            this.gainNode = gain;

            // Stop after 0.5 seconds
            setTimeout(() => {
                if (this.oscillator === osc) {
                    osc.stop();
                    osc.disconnect();
                    gain.disconnect();
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
        if (this.timeoutId) {
            clearTimeout(this.timeoutId);
            this.timeoutId = null;
        }

        if (this.oscillator) {
            if (Array.isArray(this.oscillator)) {
                this.oscillator.forEach(osc => {
                    try { osc.stop(); } catch (e) {}
                    try { osc.disconnect(); } catch (e) {}
                });
            } else {
                try { this.oscillator.stop(); } catch (e) {}
                try { this.oscillator.disconnect(); } catch (e) {}
            }
            this.oscillator = null;
        }

        if (this.gainNode) {
            try { this.gainNode.disconnect(); } catch (e) {}
            this.gainNode = null;
        }
    }
}

