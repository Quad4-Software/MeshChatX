// SPDX-License-Identifier: 0BSD

/**
 * Vue 3 click-outside directive and plugin.
 * Compatible with the previous click-outside-vue3 binding shapes:
 *   v-click-outside="handler"
 *   v-click-outside="{ handler, middleware, events, isActive, detectIframe, capture }"
 */

const HANDLERS_PROPERTY = "__meshchatx_click_outside";

const HAS_WINDOW = typeof window !== "undefined";
const HAS_NAVIGATOR = typeof navigator !== "undefined";

const IS_TOUCH =
    HAS_WINDOW && ("ontouchstart" in window || (HAS_NAVIGATOR && Number(navigator.maxTouchPoints || 0) > 0));

const DEFAULT_EVENTS = IS_TOUCH ? ["touchstart"] : ["click"];

/**
 * @param {unknown} bindingValue
 */
export function processDirectiveArguments(bindingValue) {
    const isFunction = typeof bindingValue === "function";
    if (!isFunction && (bindingValue == null || typeof bindingValue !== "object")) {
        throw new Error("v-click-outside: Binding value must be a function or an object");
    }
    const value = /** @type {Record<string, unknown>} */ (isFunction ? {} : bindingValue);
    const handler = isFunction ? bindingValue : value.handler;
    if (typeof handler !== "function") {
        throw new Error("v-click-outside: handler must be a function");
    }
    return {
        handler,
        middleware: typeof value.middleware === "function" ? value.middleware : (item) => item,
        events: Array.isArray(value.events) && value.events.length > 0 ? value.events : DEFAULT_EVENTS,
        isActive: value.isActive !== false,
        detectIframe: value.detectIframe !== false,
        capture: Boolean(value.capture),
    };
}

/**
 * Compare bindings without JSON.stringify so function identity is preserved.
 *
 * @param {unknown} a
 * @param {unknown} b
 * @returns {boolean}
 */
export function bindingsEqual(a, b) {
    if (a === b) {
        return true;
    }
    if (typeof a === "function" || typeof b === "function") {
        return a === b;
    }
    if (!a || !b || typeof a !== "object" || typeof b !== "object") {
        return false;
    }
    const left = /** @type {Record<string, unknown>} */ (a);
    const right = /** @type {Record<string, unknown>} */ (b);
    return (
        left.handler === right.handler &&
        left.middleware === right.middleware &&
        left.isActive === right.isActive &&
        left.detectIframe === right.detectIframe &&
        Boolean(left.capture) === Boolean(right.capture) &&
        JSON.stringify(left.events ?? null) === JSON.stringify(right.events ?? null)
    );
}

/**
 * @param {{ event: Event, handler: Function, middleware: Function }} args
 */
export function execHandler({ event, handler, middleware }) {
    if (middleware(event)) {
        handler(event);
    }
}

/**
 * @param {{ el: Element, event: Event }} args
 * @returns {boolean}
 */
export function isClickOutsideElement({ el, event }) {
    const path =
        typeof event.composedPath === "function" ? event.composedPath() : Array.isArray(event.path) ? event.path : null;
    if (path) {
        return path.indexOf(el) < 0;
    }
    const target = event.target;
    if (!(target instanceof Node)) {
        return true;
    }
    return !el.contains(target);
}

/**
 * @param {{ el: Element, event: Event, handler: Function, middleware: Function }} args
 */
export function onFauxIframeClick({ el, event, handler, middleware }) {
    setTimeout(() => {
        const { activeElement } = document;
        if (activeElement && activeElement.tagName === "IFRAME" && !el.contains(activeElement)) {
            execHandler({ event, handler, middleware });
        }
    }, 0);
}

/**
 * @param {{ el: Element, event: Event, handler: Function, middleware: Function }} args
 */
export function onOutsideEvent({ el, event, handler, middleware }) {
    if (!isClickOutsideElement({ el, event })) {
        return;
    }
    execHandler({ event, handler, middleware });
}

/**
 * @param {Element} el
 * @param {{ value: unknown }} binding
 */
export function beforeMount(el, { value }) {
    const { events, handler, middleware, isActive, detectIframe, capture } = processDirectiveArguments(value);
    if (!isActive) {
        return;
    }

    el[HANDLERS_PROPERTY] = events.map((eventName) => ({
        event: eventName,
        srcTarget: document.documentElement,
        handler: (event) => onOutsideEvent({ el, event, handler, middleware }),
        capture,
    }));

    if (detectIframe) {
        el[HANDLERS_PROPERTY].push({
            event: "blur",
            srcTarget: window,
            handler: (event) => onFauxIframeClick({ el, event, handler, middleware }),
            capture,
        });
    }

    for (const entry of el[HANDLERS_PROPERTY]) {
        setTimeout(() => {
            if (!el[HANDLERS_PROPERTY]) {
                return;
            }
            entry.srcTarget.addEventListener(entry.event, entry.handler, entry.capture);
        }, 0);
    }
}

/**
 * @param {Element} el
 */
export function unmounted(el) {
    const handlers = el[HANDLERS_PROPERTY] || [];
    for (const entry of handlers) {
        entry.srcTarget.removeEventListener(entry.event, entry.handler, entry.capture);
    }
    delete el[HANDLERS_PROPERTY];
}

/**
 * @param {Element} el
 * @param {{ value: unknown, oldValue: unknown }} binding
 */
export function updated(el, { value, oldValue }) {
    if (bindingsEqual(value, oldValue)) {
        return;
    }
    unmounted(el);
    beforeMount(el, { value });
}

export const clickOutsideDirective = HAS_WINDOW
    ? {
          beforeMount,
          updated,
          unmounted,
      }
    : {};

const plugin = {
    install(app) {
        app.directive("click-outside", clickOutsideDirective);
    },
    directive: clickOutsideDirective,
};

export { HANDLERS_PROPERTY, DEFAULT_EVENTS };
export default plugin;
