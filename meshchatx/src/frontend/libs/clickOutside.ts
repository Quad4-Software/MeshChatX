// SPDX-License-Identifier: 0BSD

/**
 * Click-outside helper (binding shapes from the old directive API).
 * Used by unit tests and any caller that wants processDirectiveArguments /
 * bind / unbind without a framework directive.
 *
 * Binding shapes:
 *   handler function
 *   { handler, middleware, events, isActive, detectIframe, capture }
 */

export const HANDLERS_PROPERTY = "__meshchatx_click_outside";

const HAS_WINDOW = typeof window !== "undefined";
const HAS_NAVIGATOR = typeof navigator !== "undefined";

const IS_TOUCH =
    HAS_WINDOW && ("ontouchstart" in window || (HAS_NAVIGATOR && Number(navigator.maxTouchPoints || 0) > 0));

export const DEFAULT_EVENTS: readonly string[] = IS_TOUCH ? ["touchstart"] : ["click"];

export type ClickOutsideHandler = (event: Event) => void;
export type ClickOutsideMiddleware = (event: Event) => unknown;

export interface ClickOutsideBindingObject {
    handler?: ClickOutsideHandler;
    middleware?: ClickOutsideMiddleware;
    events?: string[];
    isActive?: boolean;
    detectIframe?: boolean;
    capture?: boolean;
}

export type ClickOutsideBindingValue = ClickOutsideHandler | ClickOutsideBindingObject;

export interface ProcessedClickOutsideArgs {
    handler: ClickOutsideHandler;
    middleware: ClickOutsideMiddleware;
    events: readonly string[];
    isActive: boolean;
    detectIframe: boolean;
    capture: boolean;
}

export interface ClickOutsideListenerEntry {
    event: string;
    srcTarget: EventTarget;
    handler: EventListener;
    capture: boolean;
}

export type ClickOutsideHostElement = Element & {
    [HANDLERS_PROPERTY]?: ClickOutsideListenerEntry[];
};

export interface ClickOutsideDirectiveBinding {
    value: ClickOutsideBindingValue;
    oldValue?: ClickOutsideBindingValue;
}

export function processDirectiveArguments(bindingValue: unknown): ProcessedClickOutsideArgs {
    const isFunction = typeof bindingValue === "function";
    if (!isFunction && (bindingValue == null || typeof bindingValue !== "object")) {
        throw new Error("v-click-outside: Binding value must be a function or an object");
    }
    const value = (isFunction ? {} : bindingValue) as ClickOutsideBindingObject;
    const handler = isFunction ? (bindingValue as ClickOutsideHandler) : value.handler;
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
 */
export function bindingsEqual(a: unknown, b: unknown): boolean {
    if (a === b) {
        return true;
    }
    if (typeof a === "function" || typeof b === "function") {
        return a === b;
    }
    if (!a || !b || typeof a !== "object" || typeof b !== "object") {
        return false;
    }
    const left = a as ClickOutsideBindingObject;
    const right = b as ClickOutsideBindingObject;
    return (
        left.handler === right.handler &&
        left.middleware === right.middleware &&
        left.isActive === right.isActive &&
        left.detectIframe === right.detectIframe &&
        Boolean(left.capture) === Boolean(right.capture) &&
        JSON.stringify(left.events ?? null) === JSON.stringify(right.events ?? null)
    );
}

export function execHandler({
    event,
    handler,
    middleware,
}: {
    event: Event;
    handler: ClickOutsideHandler;
    middleware: ClickOutsideMiddleware;
}): void {
    if (middleware(event)) {
        handler(event);
    }
}

export function isClickOutsideElement({ el, event }: { el: Element; event: Event }): boolean {
    const path =
        typeof event.composedPath === "function"
            ? event.composedPath()
            : "path" in event && Array.isArray((event as Event & { path?: EventTarget[] }).path)
              ? (event as Event & { path: EventTarget[] }).path
              : null;
    if (path) {
        return path.indexOf(el) < 0;
    }
    const target = event.target;
    if (!(target instanceof Node)) {
        return true;
    }
    return !el.contains(target);
}

export function onFauxIframeClick({
    el,
    event,
    handler,
    middleware,
}: {
    el: Element;
    event: Event;
    handler: ClickOutsideHandler;
    middleware: ClickOutsideMiddleware;
}): void {
    setTimeout(() => {
        const { activeElement } = document;
        if (activeElement && activeElement.tagName === "IFRAME" && !el.contains(activeElement)) {
            execHandler({ event, handler, middleware });
        }
    }, 0);
}

export function onOutsideEvent({
    el,
    event,
    handler,
    middleware,
}: {
    el: Element;
    event: Event;
    handler: ClickOutsideHandler;
    middleware: ClickOutsideMiddleware;
}): void {
    if (!isClickOutsideElement({ el, event })) {
        return;
    }
    execHandler({ event, handler, middleware });
}

export function beforeMount(el: ClickOutsideHostElement, { value }: { value: unknown }): void {
    const { events, handler, middleware, isActive, detectIframe, capture } = processDirectiveArguments(value);
    if (!isActive) {
        return;
    }

    el[HANDLERS_PROPERTY] = events.map((eventName) => ({
        event: eventName,
        srcTarget: document.documentElement,
        handler: ((event: Event) => onOutsideEvent({ el, event, handler, middleware })) as EventListener,
        capture,
    }));

    if (detectIframe) {
        el[HANDLERS_PROPERTY].push({
            event: "blur",
            srcTarget: window,
            handler: ((event: Event) => onFauxIframeClick({ el, event, handler, middleware })) as EventListener,
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

export function unmounted(el: ClickOutsideHostElement): void {
    const handlers = el[HANDLERS_PROPERTY] || [];
    for (const entry of handlers) {
        entry.srcTarget.removeEventListener(entry.event, entry.handler, entry.capture);
    }
    delete el[HANDLERS_PROPERTY];
}

export function updated(el: ClickOutsideHostElement, { value, oldValue }: { value: unknown; oldValue: unknown }): void {
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

interface ClickOutsideAppLike {
    directive(name: string, directive: typeof clickOutsideDirective): void;
}

const plugin = {
    install(app: ClickOutsideAppLike) {
        app.directive("click-outside", clickOutsideDirective);
    },
    directive: clickOutsideDirective,
};

export default plugin;
