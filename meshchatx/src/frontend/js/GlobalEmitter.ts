// SPDX-License-Identifier: 0BSD

import { createEmitter } from "../libs/emitter";

class GlobalEmitter {
    private emitter = createEmitter();

    on(event: string, handler: (data: unknown) => void): void {
        this.emitter.on(event, handler);
    }

    off(event: string, handler: (data: unknown) => void): void {
        this.emitter.off(event, handler);
    }

    emit(type: string, event?: unknown): void {
        this.emitter.emit(type, event);
    }

    listenerCount(event: string): number {
        const list = this.emitter?.all?.get(event);
        return Array.isArray(list) ? list.length : 0;
    }
}

export default new GlobalEmitter();
