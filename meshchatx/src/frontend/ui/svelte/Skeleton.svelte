<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    type SkeletonVariant = "line" | "row" | "avatar" | "card";

    interface Props {
        variant?: SkeletonVariant;
        class?: string;
    }

    const VARIANT_CLASSES: Record<SkeletonVariant, string> = {
        line: "h-3 w-full rounded-md",
        row: "h-10 w-full rounded-xl",
        avatar: "size-10 rounded-full shrink-0",
        card: "h-24 w-full rounded-2xl",
    };

    let { variant = "line", class: className = "" }: Props = $props();

    const rootClasses = $derived(
        [
            "bg-sem-surface-muted animate-pulse motion-reduce:animate-none",
            VARIANT_CLASSES[variant] || VARIANT_CLASSES.line,
            className,
        ]
            .filter(Boolean)
            .join(" ")
    );
</script>

<div class={rootClasses} aria-hidden="true" role="presentation"></div>
