/**
 * Yield to the browser event loop so input and paint can interleave with
 * long render work. Prefers scheduler.yield (prioritized continuation);
 * falls back to a zero-delay MessageChannel post (setTimeout has 4ms clamp
 * under nesting) and finally setTimeout where neither is available.
 */

const channel =
    typeof MessageChannel !== "undefined"
        ? (() => {
              const c = new MessageChannel();
              return c;
          })()
        : null;

export function yieldToMainThread(): Promise<void> {
    const sched = (globalThis as any).scheduler;
    if (sched && typeof sched.yield === "function") {
        return sched.yield();
    }
    if (channel) {
        return new Promise((resolve) => {
            channel.port1.onmessage = () => resolve();
            channel.port2.postMessage(0);
        });
    }
    return new Promise((resolve) => setTimeout(resolve, 0));
}
