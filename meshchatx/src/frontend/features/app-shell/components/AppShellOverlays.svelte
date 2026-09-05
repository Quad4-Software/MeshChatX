<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    /**
     * Every shell-level overlay that sits above the page: the call overlay,
     * the global toast and dialog singletons, the one-shot modals, the LXMF
     * identity QR, and the identity switch curtain. Modal instances are
     * published back to the shell state so it can open them on demand.
     */
    import { t } from "../../../js/i18n.js";
    import logoUrl from "../../../assets/images/logo.png";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import Toast from "../../../ui/svelte/Toast.svelte";
    import ConfirmDialog from "../../../ui/svelte/ConfirmDialog.svelte";
    import PromptDialog from "../../../ui/svelte/PromptDialog.svelte";
    import { navigate, router } from "../../../shell/hashRouter.js";
    import CallOverlay from "../../call/components/CallOverlay.svelte";
    import TutorialModalHost from "../../tutorial/components/TutorialModalHost.svelte";
    import AppIdentitySwitchOverlay from "./AppIdentitySwitchOverlay.svelte";
    import CommandPalette from "./CommandPalette.svelte";
    import IntegrityWarningModal from "./IntegrityWarningModal.svelte";
    import ChangelogModal from "./ChangelogModal.svelte";
    import ChannelPromptModal from "./ChannelPromptModal.svelte";
    import AndroidStorageChoicePrompt from "./AndroidStorageChoicePrompt.svelte";
    import PostInstallPromptHost from "./PostInstallPromptHost.svelte";
    import type { AppShellState } from "../lib/appShellState.svelte.js";
    import { copyIdentityUri, getMyIdentityUri } from "../lib/appShellIdentity.js";
    import { onOverlayHangup, onToggleMic, onToggleSpeaker } from "../lib/appShellTelephony.js";

    interface Props {
        shell: AppShellState;
    }

    let { shell }: Props = $props();

    const tr = $derived.by(() => {
        void shell.localeVersion;
        return (key: string, values?: Record<string, unknown>) => t(key, values);
    });

    let changelogModal: ReturnType<typeof ChangelogModal> | undefined = $state();
    let channelPromptModal: ReturnType<typeof ChannelPromptModal> | undefined = $state();
    let androidStoragePrompt: ReturnType<typeof AndroidStorageChoicePrompt> | undefined = $state();
    let postInstallHost: ReturnType<typeof PostInstallPromptHost> | undefined = $state();
    let commandPalette: ReturnType<typeof CommandPalette> | undefined = $state();
    let tutorialHost: ReturnType<typeof TutorialModalHost> | undefined = $state();

    $effect(() => {
        shell.hosts = {
            changelog: changelogModal ?? null,
            tutorial: tutorialHost ?? null,
            channelPrompt: channelPromptModal ?? null,
            androidStorage: androidStoragePrompt ?? null,
            postInstall: postInstallHost ?? null,
            commandPalette: commandPalette ?? null,
        };
    });

    function onCommandPaletteNavigate(route: unknown): void {
        void navigate(route as never);
    }
</script>

{#if shell.shouldShowCallOverlay}
    <CallOverlay
        activeCall={shell.activeCall || shell.lastCall}
        isEnded={shell.isCallEnded}
        wasDeclined={shell.wasDeclined}
        voicemailStatus={shell.voicemailStatus}
        initiationStatus={shell.initiationStatus}
        initiationTargetHash={shell.initiationTargetHash}
        initiationTargetName={shell.initiationTargetName}
        {router}
        route={shell.route}
        onhangup={() => onOverlayHangup(shell)}
        ontogglemic={(muted) => onToggleMic(shell, muted)}
        ontogglespeaker={(muted) => onToggleSpeaker(shell, muted)}
    />
{/if}

<Toast />
<ConfirmDialog />
<PromptDialog />
<CommandPalette bind:this={commandPalette} onnavigate={onCommandPaletteNavigate} />
<IntegrityWarningModal />
<ChangelogModal bind:this={changelogModal} appVersion={shell.appInfo?.version ?? ""} />
<ChannelPromptModal bind:this={channelPromptModal} />
<TutorialModalHost bind:this={tutorialHost} />
<AndroidStorageChoicePrompt bind:this={androidStoragePrompt} variant="upgrade" />
<PostInstallPromptHost bind:this={postInstallHost} />

{#if shell.showLxmfQr}
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
        class="fixed inset-0 z-190 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs"
        onclick={(event) => {
            if (event.target === event.currentTarget) {
                shell.showLxmfQr = false;
            }
        }}
    >
        <div class="w-full max-w-sm bg-sem-surface rounded-2xl shadow-2xl overflow-hidden">
            <div class="px-4 py-3 border-b border-sem-border flex items-center justify-between">
                <h3 class="text-sm font-semibold text-sem-fg">Identity QR (LXMA)</h3>
                <button
                    type="button"
                    class="text-sem-fg-muted hover:text-sem-fg transition-colors"
                    onclick={() => (shell.showLxmfQr = false)}
                >
                    <MaterialDesignIcon iconName="close" class="size-5" />
                </button>
            </div>
            <div class="p-4 space-y-3">
                <div class="flex justify-center">
                    {#if shell.lxmfQrDataUrl}
                        <img
                            src={shell.lxmfQrDataUrl}
                            alt="LXMF QR"
                            class="w-48 h-48 bg-white rounded-xl border border-sem-border"
                        />
                    {/if}
                </div>
                {#if shell.config?.lxmf_address_hash}
                    <div class="text-xs font-mono text-sem-fg-secondary text-center wrap-break-word">
                        {getMyIdentityUri(shell)}
                    </div>
                {/if}
                <div class="flex justify-center">
                    <button
                        type="button"
                        class="px-3 py-1.5 text-xs font-semibold text-sem-accent hover:underline"
                        onclick={() => void copyIdentityUri(shell)}
                    >
                        {tr("common.copy")}
                    </button>
                </div>
            </div>
        </div>
    </div>
{/if}

<AppIdentitySwitchOverlay show={shell.isSwitchingIdentity} {logoUrl} />
