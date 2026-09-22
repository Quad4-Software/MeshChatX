// SPDX-License-Identifier: 0BSD

export { createEmitter, default as emitter } from "./emitter.js";
export type { Emitter, EmitterHandler, WildcardHandler, HandlerMap } from "./emitter.js";
export { randomUuidV4, uuidv4, isUuidV4, fillRandomBytes, resolveCrypto, UUID_V4_RE } from "./uuid.js";
export {
    formatDate,
    fromNow,
    relativeLabel,
    meshDate,
    toDate,
    isSupportedFormatPattern,
    FROM_NOW_GOLDEN,
    FROM_NOW_THRESHOLDS,
    SUPPORTED_FORMAT_TOKENS,
    MONTHS_SHORT,
} from "./datetime.js";
export type {
    FormatToken,
    FromNowFixedThreshold,
    FromNowUnitThreshold,
    FromNowThreshold,
    FromNowGoldenEntry,
    MeshDateHelper,
} from "./datetime.js";
export {
    default as clickOutside,
    clickOutsideDirective,
    processDirectiveArguments,
    bindingsEqual,
    isClickOutsideElement,
    execHandler,
    onOutsideEvent,
    onFauxIframeClick,
    beforeMount,
    updated,
    unmounted,
    HANDLERS_PROPERTY,
    DEFAULT_EVENTS,
} from "./clickOutside.js";
export type {
    ClickOutsideHandler,
    ClickOutsideMiddleware,
    ClickOutsideBindingObject,
    ClickOutsideBindingValue,
    ProcessedClickOutsideArgs,
    ClickOutsideListenerEntry,
    ClickOutsideHostElement,
    ClickOutsideDirectiveBinding,
} from "./clickOutside.js";
