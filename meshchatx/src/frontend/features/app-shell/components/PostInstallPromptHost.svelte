<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";
    import AppUpdatePrompt from "./AppUpdatePrompt.svelte";
    import { listPostInstallPromptsByPriority } from "../../../js/registries/postInstallPromptRegistry.js";
    import type { PostInstallPromptEntry } from "../../../js/registries/postInstallPromptRegistry.js";
    import { markPromptSeen, shouldShowPrompt } from "../../../js/postInstallPromptState.js";

    interface Props {
        open?: boolean;
        oncompleted?: (payload: unknown) => void;
        ondismissed?: () => void;
    }

    let { open = $bindable(false), oncompleted, ondismissed }: Props = $props();

    let busy = $state(false);
    let activeEntry = $state<PostInstallPromptEntry | null>(null);

    const resolvedTitle = $derived(activeEntry?.titleKey ? t(activeEntry.titleKey) : "");

    const resolvedDescription = $derived(activeEntry?.descriptionKey ? t(activeEntry.descriptionKey) : "");

    const resolvedPrimaryLabel = $derived(t(activeEntry?.primaryLabelKey || "common.continue"));

    const resolvedSecondaryLabel = $derived(activeEntry?.secondaryLabelKey ? t(activeEntry.secondaryLabelKey) : "");

    export async function showNext(): Promise<boolean> {
        if (open) {
            return true;
        }
        const pending = await findNextPending();
        if (!pending) {
            return false;
        }
        activeEntry = pending;
        open = true;
        return true;
    }

    export async function findNextPending(): Promise<PostInstallPromptEntry | null> {
        for (const entry of listPostInstallPromptsByPriority()) {
            if (!shouldShowPrompt(entry.id, entry.revision)) {
                continue;
            }
            if (typeof entry.shouldShow === "function") {
                try {
                    const ok = await entry.shouldShow();
                    if (!ok) {
                        continue;
                    }
                } catch (e) {
                    console.error(`post-install prompt ${entry.id} shouldShow failed`, e);
                    continue;
                }
            }
            return entry;
        }
        return null;
    }

    export function hide(): void {
        open = false;
        activeEntry = null;
        busy = false;
        ondismissed?.();
    }

    export function dismissActive(): void {
        const entry = activeEntry;
        if (entry) {
            markPromptSeen(entry.id, entry.revision);
        }
        hide();
        oncompleted?.({ id: entry?.id, revision: entry?.revision });
    }

    export async function onPrimary(): Promise<void> {
        if (busy || !activeEntry) {
            return;
        }
        busy = true;
        try {
            const entry = activeEntry;
            let keepOpen = false;
            if (typeof entry.onPrimary === "function") {
                const result = await entry.onPrimary({ entry });
                keepOpen = result === false;
            }
            if (keepOpen) {
                return;
            }
            if (entry.dismissOnPrimary !== false) {
                dismissActive();
            } else {
                hide();
                oncompleted?.({ id: entry.id, revision: entry.revision });
            }
        } catch (e) {
            console.error("post-install prompt primary action failed", e);
        } finally {
            busy = false;
        }
    }

    export async function onSecondary(): Promise<void> {
        if (busy || !activeEntry?.secondaryLabelKey) {
            return;
        }
        busy = true;
        try {
            const entry = activeEntry;
            let keepOpen = false;
            if (typeof entry.onSecondary === "function") {
                const result = await entry.onSecondary({ entry });
                keepOpen = result === false;
            }
            if (keepOpen) {
                return;
            }
            if (entry.dismissOnSecondary !== false) {
                dismissActive();
            } else {
                hide();
                oncompleted?.({ id: entry.id, revision: entry.revision });
            }
        } catch (e) {
            console.error("post-install prompt secondary action failed", e);
        } finally {
            busy = false;
        }
    }
</script>

<AppUpdatePrompt
    bind:open
    title={resolvedTitle}
    description={resolvedDescription}
    primaryLabel={resolvedPrimaryLabel}
    secondaryLabel={resolvedSecondaryLabel}
    {busy}
    onprimary={onPrimary}
    onsecondary={onSecondary}
/>
