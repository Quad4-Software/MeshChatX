<!-- SPDX-License-Identifier: 0BSD -->

<script>
    import { getMdiIconPath } from "../../js/mdiIconNames.js";

    /**
     * @type {{
     *   customImage?: string,
     *   iconName?: string,
     *   iconForegroundColour?: string,
     *   iconBackgroundColour?: string,
     *   iconClass?: string,
     *   iconStyle?: Record<string, string | number> | string,
     * }}
     */
    let {
        customImage = "",
        iconName = "",
        iconForegroundColour = "",
        iconBackgroundColour = "",
        iconClass = "",
        iconStyle = undefined,
    } = $props();

    const resolvedIconName = $derived(iconName && String(iconName).trim() ? String(iconName).trim() : "account");
    const hasCustomIcon = $derived(Boolean(iconName && String(iconName).trim()));
    const iconPath = $derived(getMdiIconPath(resolvedIconName));

    const shellPx = $derived.by(() => {
        if (iconStyle && typeof iconStyle === "object") {
            const raw = iconStyle.width ?? iconStyle.height;
            if (raw != null && raw !== "") {
                const n = parseFloat(String(raw));
                if (Number.isFinite(n) && n > 0) return n;
            }
        }
        const extra = (iconClass || "").trim();
        const sizeMatch = extra.match(/\bsize-(\d+\.\d+)\b/) || extra.match(/\bsize-(\d+)\b/);
        if (sizeMatch) return Number(sizeMatch[1]) * 4;
        const wMatch = extra.match(/\bw-(\d+\.\d+)\b/) || extra.match(/\bw-(\d+)\b/);
        if (wMatch) return Number(wMatch[1]) * 4;
        return 24;
    });

    const glyphPx = $derived(Math.max(10, Math.round(shellPx * 0.72)));

    const finalForegroundColor = $derived(
        hasCustomIcon && iconForegroundColour && iconForegroundColour !== "" ? iconForegroundColour : "#6b7280"
    );
    const finalBackgroundColor = $derived(
        hasCustomIcon && iconBackgroundColour && iconBackgroundColour !== ""
            ? iconBackgroundColour
            : hasCustomIcon
              ? "#e5e7eb"
              : ""
    );

    const shellStyle = $derived(
        (() => {
            /** @type {string[]} */
            const parts = [`width: ${shellPx}px`, `height: ${shellPx}px`];
            if (finalBackgroundColor) {
                parts.push(`background-color: ${finalBackgroundColor}`);
            }
            if (iconStyle && typeof iconStyle === "object") {
                for (const [key, value] of Object.entries(iconStyle)) {
                    if (value == null || value === "") continue;
                    if (key === "width" || key === "height") continue;
                    const cssKey = key.replace(/[A-Z]/g, (m) => `-${m.toLowerCase()}`);
                    parts.push(`${cssKey}: ${value}`);
                }
            } else if (typeof iconStyle === "string" && iconStyle.trim()) {
                parts.push(iconStyle.trim());
            }
            return parts.join("; ");
        })()
    );

    const shellClass = $derived(
        [
            "rounded-full shrink-0 flex items-center justify-center overflow-hidden",
            hasCustomIcon ? "" : "bg-sem-surface-muted text-sem-fg-muted border border-sem-border",
            (iconClass || "").replace(/\b(size|w|h)-[\w.]+/g, "").trim(),
        ]
            .filter(Boolean)
            .join(" ")
    );
</script>

{#if customImage}
    <div class={shellClass} style={shellStyle}>
        <img src={customImage} alt="" class="w-full h-full object-cover" />
    </div>
{:else}
    <div class={shellClass} style={shellStyle}>
        <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            role="img"
            aria-label={resolvedIconName}
            width={glyphPx}
            height={glyphPx}
            fill={finalForegroundColor}
            class="block shrink-0"
        >
            <path d={iconPath} fill={finalForegroundColor} />
        </svg>
    </div>
{/if}
