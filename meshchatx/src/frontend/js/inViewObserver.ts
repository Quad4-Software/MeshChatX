export function isAnimatedRasterType(imageType: unknown): boolean {
    const s = String(imageType || "").toLowerCase();
    return s === "gif" || s === "webp";
}

export type InViewCallback = (
    entry: IntersectionObserverEntry | { isIntersecting: true; target: Element } | any
) => void;

/** Attach an IntersectionObserver and return a disconnect function. */
export function attachInView(
    el: Element | null | undefined,
    callback: InViewCallback,
    options: IntersectionObserverInit = {}
): () => void {
    if (!el) {
        return () => {};
    }
    if (typeof IntersectionObserver === "undefined") {
        callback({ isIntersecting: true, target: el });
        return () => {};
    }
    const io = new IntersectionObserver(
        (entries) => {
            const e = entries[0];
            if (e) {
                callback(e);
            }
        },
        {
            threshold: options.threshold ?? 0.06,
            rootMargin: options.rootMargin ?? "120px 0px",
            ...options,
        }
    );
    io.observe(el);
    return () => {
        io.disconnect();
    };
}
