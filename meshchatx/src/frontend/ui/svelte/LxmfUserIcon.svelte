<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<script>
    import MaterialDesignIcon from "./MaterialDesignIcon.svelte";

    /**
     * @type {{
     *   customImage?: string,
     *   iconName?: string,
     *   iconForegroundColour?: string,
     *   iconBackgroundColour?: string,
     *   iconClass?: string,
     * }}
     */
    let {
        customImage = "",
        iconName = "",
        iconForegroundColour = "",
        iconBackgroundColour = "",
        iconClass = "",
    } = $props();

    const resolvedShellClass = $derived(
        (() => {
            const extra = (iconClass || "").trim();
            if (
                /\bsize-[\w.]+\b/.test(extra) ||
                /\bw-[\w.]+\b/.test(extra) ||
                /\bh-[\w.]+\b/.test(extra) ||
                /\bmin-w-/.test(extra) ||
                /\bmin-h-/.test(extra)
            ) {
                return extra;
            }
            return ["size-6", extra].filter(Boolean).join(" ").trim();
        })()
    );

    const finalForegroundColor = $derived(
        iconForegroundColour && iconForegroundColour !== "" ? iconForegroundColour : "#6b7280"
    );
    const finalBackgroundColor = $derived(
        iconBackgroundColour && iconBackgroundColour !== "" ? iconBackgroundColour : "#e5e7eb"
    );
    const fallbackBackgroundColor = $derived(
        iconBackgroundColour && iconBackgroundColour !== "" ? iconBackgroundColour : ""
    );
</script>

{#if customImage}
    <div class="rounded-full overflow-hidden shrink-0 flex items-center justify-center {resolvedShellClass}">
        <img src={customImage} alt="" class="w-full h-full object-cover" />
    </div>
{:else if iconName}
    <div
        class="p-[10%] rounded-full shrink-0 flex items-center justify-center {resolvedShellClass}"
        style="background-color: {finalBackgroundColor}; color: {finalForegroundColor}"
    >
        <MaterialDesignIcon {iconName} class="size-full" />
    </div>
{:else}
    <div
        class="bg-sem-surface-muted text-sem-fg-muted p-[10%] rounded-full shrink-0 flex items-center justify-center border border-sem-border {resolvedShellClass}"
        style={fallbackBackgroundColor ? `background-color: ${fallbackBackgroundColor}` : undefined}
    >
        <MaterialDesignIcon iconName="account" class="w-full h-full" />
    </div>
{/if}
