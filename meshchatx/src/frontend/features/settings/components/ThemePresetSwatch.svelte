<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    interface Props {
        colors: {
            canvas?: string;
            surface?: string;
            accent?: string;
            border?: string;
        };
        size?: "sm" | "md" | "lg";
    }

    let { colors, size = "md" }: Props = $props();

    const sizeClass = $derived.by(() => {
        if (size === "sm") return "h-7 w-7";
        if (size === "lg") return "h-10 w-10";
        return "h-8 w-8";
    });
</script>

<div
    class="theme-preset-swatch inline-grid shrink-0 overflow-hidden rounded-md border border-sem-border shadow-xs {sizeClass}"
    aria-hidden="true"
>
    <span class="theme-preset-swatch__band" style:background-color={colors.canvas || "transparent"}></span>
    <span class="theme-preset-swatch__band" style:background-color={colors.surface || "transparent"}></span>
    <span class="theme-preset-swatch__band" style:background-color={colors.accent || "transparent"}></span>
    <span class="theme-preset-swatch__band" style:background-color={colors.border || "transparent"}></span>
</div>

<style>
    .theme-preset-swatch {
        grid-template-columns: repeat(4, minmax(0, 1fr));
    }

    .theme-preset-swatch__band {
        min-height: 100%;
    }
</style>
