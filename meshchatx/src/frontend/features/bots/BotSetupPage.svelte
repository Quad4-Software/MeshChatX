<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount } from "svelte";
    import ToastUtils from "../../js/ToastUtils.js";
    import { t } from "../../js/i18n.js";
    import MaterialDesignIcon from "../../ui/svelte/MaterialDesignIcon.svelte";
    import LxmfUserIcon from "../../ui/svelte/LxmfUserIcon.svelte";
    import LxmfIconEditor, { defaultBotIconDraft, type LxmfIconDraft } from "../../ui/svelte/LxmfIconEditor.svelte";
    import ToolsPageHeader from "../../ui/svelte/ToolsPageHeader.svelte";
    import LxmfConfigFields from "./components/BotLxmfConfigFields.svelte";
    import BotCustomCommandsEditor from "./components/BotCustomCommandsEditor.svelte";
    import BotRrcFields from "./components/BotRrcFields.svelte";
    import { fetchBotsStatus, startBot } from "./lib/botsApi.js";
    import { buildLxmfConfigPatch, defaultLxmfConfigDraft } from "./lib/botLxmfConfigForm.js";
    import { buildCustomPayload, defaultCustomDraft, buildRrcPayload, defaultRrcDraft } from "./lib/botDrafts.js";
    import type { BotTemplate, LxmfConfigDraft } from "./lib/types.js";

    interface Props {
        routeQuery?: Record<string, string>;
    }

    let { routeQuery = {} }: Props = $props();

    let templates = $state<BotTemplate[]>([]);
    let loading = $state(true);
    let selectedTemplateId = $state<string | null>(null);
    let name = $state("");
    let lxmfDraft = $state<LxmfConfigDraft>(defaultLxmfConfigDraft());
    let iconDraft = $state<LxmfIconDraft | null>(null);
    let customDraft = $state(defaultCustomDraft());
    let rrcDraft = $state(defaultRrcDraft());
    let isStarting = $state(false);

    const selectedTemplate = $derived(templates.find((tpl) => tpl.id === selectedTemplateId) || null);

    const canCreate = $derived.by(() => {
        if (!selectedTemplateId) {
            return false;
        }
        if (selectedTemplateId === "rrc") {
            return /^[0-9a-f]{32}$/.test((rrcDraft.hub || "").trim().toLowerCase());
        }
        if (selectedTemplateId === "custom") {
            return buildCustomPayload(customDraft).commands.length > 0;
        }
        return true;
    });

    function isTemplateDefaultName(value: string): boolean {
        return templates.some((tpl) => tpl.name === value);
    }

    function selectTemplate(template: BotTemplate | null): void {
        if (!template) {
            selectedTemplateId = null;
            return;
        }
        selectedTemplateId = template.id;
        if (!name || isTemplateDefaultName(name)) {
            name = template.name;
        }
        if (!iconDraft) {
            iconDraft = template.default_icon ? defaultBotIconDraft(template.default_icon) : null;
        }
    }

    async function loadTemplates(): Promise<void> {
        try {
            const data = await fetchBotsStatus();
            templates = data.templates;
            const wanted = routeQuery?.template;
            const found = templates.find((tpl) => tpl.id === wanted);
            selectTemplate(found || templates[0] || null);
        } catch (e: unknown) {
            console.error("[BotSetupPage] status failed", (e as { message?: string })?.message || e);
            ToastUtils.error(t("bots.failed_to_load"));
        } finally {
            loading = false;
        }
    }

    async function createBot(): Promise<void> {
        if (isStarting || !selectedTemplate) {
            return;
        }
        const templateId = selectedTemplate.id;
        if (templateId === "rrc" && !canCreate) {
            ToastUtils.error(t("bots.rrc_hub_required"));
            return;
        }
        if (templateId === "custom" && !canCreate) {
            ToastUtils.error(t("bots.custom_requires_command"));
            return;
        }
        isStarting = true;
        try {
            const payload: Parameters<typeof startBot>[0] = {
                template_id: templateId,
                name,
            };
            const lxmfPatch = buildLxmfConfigPatch(lxmfDraft);
            if (Object.keys(lxmfPatch).length > 0) {
                payload.lxmf_config = lxmfPatch;
            }
            if (iconDraft && iconDraft.icon_name) {
                payload.icon = iconDraft;
            }
            if (templateId === "custom") {
                payload.custom = buildCustomPayload(customDraft);
            }
            if (templateId === "rrc") {
                payload.rrc = buildRrcPayload(rrcDraft);
            }
            await startBot(payload);
            ToastUtils.success(t("bots.bot_started"));
            goBack();
        } catch (e: unknown) {
            console.error(e);
            ToastUtils.error(
                (e as { response?: { data?: { message?: string } } })?.response?.data?.message ||
                    t("bots.failed_to_start")
            );
        } finally {
            isStarting = false;
        }
    }

    function goBack(): void {
        window.location.hash = "#/bots";
    }

    onMount(() => {
        void loadTemplates();
    });
</script>

<div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas">
    <ToolsPageHeader
        icon="robot"
        title={t("bots.setup_title")}
        description={t("bots.setup_description")}
        accent="blue"
        backTo="/bots"
        backLabel={t("tools.bots.title")}
    />
    <div
        class="flex-1 overflow-y-auto w-full px-3 sm:px-4 md:px-5 lg:px-8 py-4 sm:py-6 pb-[max(1.5rem,env(safe-area-inset-bottom))]"
    >
        <div class="space-y-6 w-full max-w-3xl mx-auto">
            {#if loading}
                <div class="text-sm text-sem-fg-muted">
                    {t("bots.loading")}
                </div>
            {:else}
                <div class="rounded-lg border border-sem-border bg-sem-surface p-4 sm:p-5">
                    <h3 class="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-3">
                        {t("bots.choose_template")}
                    </h3>
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        {#each templates as template (template.id)}
                            <button
                                type="button"
                                class="relative flex items-start gap-3 rounded-lg border-2 p-3 text-left transition-all hover:bg-sem-surface-muted {selectedTemplateId ===
                                template.id
                                    ? 'border-blue-500 bg-sem-surface-muted'
                                    : 'border-sem-border'}"
                                onclick={() => selectTemplate(template)}
                            >
                                {#if template.default_icon}
                                    <LxmfUserIcon iconName={template.default_icon} iconClass="size-9 shrink-0" />
                                {/if}
                                <div class="min-w-0">
                                    <div class="font-semibold text-sem-fg text-sm">
                                        {template.name}
                                    </div>
                                    <div class="text-xs text-gray-600 dark:text-gray-400 mt-0.5">
                                        {template.description}
                                    </div>
                                </div>
                                {#if selectedTemplateId === template.id}
                                    <MaterialDesignIcon
                                        iconName="check-circle"
                                        class="size-5 text-blue-500 absolute top-2 right-2"
                                    />
                                {/if}
                            </button>
                        {/each}
                    </div>
                </div>

                {#if selectedTemplate}
                    <div class="rounded-lg border border-sem-border bg-sem-surface p-4 sm:p-5">
                        <label class="glass-label" for="bot-setup-name">{t("bots.bot_name")}</label>
                        <input
                            id="bot-setup-name"
                            bind:value={name}
                            type="text"
                            placeholder={selectedTemplate.name}
                            class="input-field"
                            maxlength="256"
                        />
                    </div>

                    {#if selectedTemplateId === "custom"}
                        <div class="rounded-lg border border-sem-border bg-sem-surface p-4 sm:p-5">
                            <h3 class="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-3">
                                {t("bots.custom_section")}
                            </h3>
                            <BotCustomCommandsEditor bind:draft={customDraft} />
                        </div>
                    {/if}

                    {#if selectedTemplateId === "rrc"}
                        <div class="rounded-lg border border-sem-border bg-sem-surface p-4 sm:p-5">
                            <h3 class="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-3">
                                {t("bots.rrc_section")}
                            </h3>
                            <BotRrcFields bind:draft={rrcDraft} />
                        </div>
                    {/if}

                    <div class="rounded-lg border border-sem-border bg-sem-surface p-4 sm:p-5">
                        <h3 class="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-3">
                            {t("bots.appearance")}
                        </h3>
                        <LxmfIconEditor bind:value={iconDraft} />
                    </div>

                    <div class="rounded-lg border border-sem-border bg-sem-surface p-4 sm:p-5">
                        <h3 class="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-1">
                            {t("bots.advanced_lxmf_settings")}
                        </h3>
                        <p class="text-xs text-sem-fg-muted mb-3">
                            {t("bots.advanced_lxmf_settings_hint")}
                        </p>
                        <LxmfConfigFields bind:draft={lxmfDraft} />
                    </div>

                    <div class="flex justify-end gap-2 pb-4">
                        <button
                            type="button"
                            class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-sem-fg-muted hover:bg-gray-50 dark:hover:bg-zinc-700 transition-colors"
                            disabled={isStarting}
                            onclick={goBack}
                        >
                            {t("common.cancel")}
                        </button>
                        <button
                            type="button"
                            class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border transition-colors disabled:opacity-50 disabled:cursor-not-allowed bg-blue-600 text-white border-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:border-blue-500 dark:hover:bg-blue-600"
                            disabled={isStarting || !canCreate}
                            onclick={createBot}
                        >
                            {#if isStarting}
                                <span
                                    class="inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin"
                                ></span>
                            {:else}
                                <MaterialDesignIcon iconName="robot" class="size-4" />
                            {/if}
                            {t("bots.create_and_start")}
                        </button>
                    </div>
                {/if}
            {/if}
        </div>
    </div>
</div>
