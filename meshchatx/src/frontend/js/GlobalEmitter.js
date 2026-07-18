// SPDX-License-Identifier: 0BSD

import { createEmitter } from "../libs/emitter.js";

class GlobalEmitter {
    constructor() {
        this.emitter = createEmitter();
    }

    // add event listener
    on(event, handler) {
        this.emitter.on(event, handler);
    }

    // remove event listener
    off(event, handler) {
        this.emitter.off(event, handler);
    }

    // emit event
    emit(type, event) {
        this.emitter.emit(type, event);
    }
}

export default new GlobalEmitter();
