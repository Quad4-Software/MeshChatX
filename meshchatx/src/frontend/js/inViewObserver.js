export function isAnimatedRasterType(imageType) {
    const s = String(imageType || "").toLowerCase();
    return s === "gif" || s === "webp";
}

/**
 * @param {Element} el
 * @param {(entry: IntersectionObserverEntry) => void} callback
 * @param {IntersectionObserverInit} [options]
 * @returns {() => void} disconnect
 */
export function attachInView(el, callback, options = {}) {
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
