// SPDX-License-Identifier: 0BSD

import { createEmitter } from "../libs/emitter.js";

class GlobalEmitter {
    declare emitter: ReturnType<typeof createEmitter>;
    constructor() {
        this.emitter = createEmitter();
    }

    // add event listener
    on(event: string, handler: (...args: any[]) => void) {
        this.emitter.on(event, handler);
    }

    // remove event listener
    off(event: string, handler: (...args: any[]) => void) {
        this.emitter.off(event, handler);
    }

    // emit event
    emit(type: string, event?: unknown) {
        this.emitter.emit(type, event);
    }

    listenerCount(event: string) {
        const list = this.emitter?.all?.get(event);
        return Array.isArray(list) ? list.length : 0;
    }
}

export default new GlobalEmitter();
