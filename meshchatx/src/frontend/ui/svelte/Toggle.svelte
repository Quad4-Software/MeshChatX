<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { Switch } from "bits-ui";

    interface Props {
        id?: string | null;
        checked?: boolean;
        label?: string | null;
        disabled?: boolean;
        onchange?: (checked: boolean) => void;
    }

    let { id = null, checked = $bindable(false), label = null, disabled = false, onchange }: Props = $props();
</script>

<label
    for={id ?? undefined}
    class="relative inline-flex w-auto shrink-0 items-center gap-3 {disabled
        ? 'opacity-50 cursor-not-allowed'
        : 'cursor-pointer'}"
>
    <Switch.Root
        id={id ?? undefined}
        bind:checked
        {disabled}
        onCheckedChange={(next) => onchange?.(next)}
        class="relative h-6 w-11 shrink-0 rounded-full bg-gray-200 outline-hidden transition-colors focus-visible:ring-4 focus-visible:ring-blue-300 disabled:cursor-not-allowed dark:bg-zinc-700 dark:focus-visible:ring-blue-800 data-[state=checked]:bg-blue-600 dark:data-[state=checked]:bg-blue-600"
    >
        <Switch.Thumb
            class="pointer-events-none absolute top-[2px] left-[2px] block h-5 w-5 rounded-full border border-gray-300 bg-white transition-transform data-[state=checked]:translate-x-full data-[state=checked]:border-white dark:border-gray-600"
        />
    </Switch.Root>
    {#if label}
        <span class="min-w-0 text-sm font-medium leading-snug text-gray-900 dark:text-gray-300">
            {label}
        </span>
    {/if}
</label>
