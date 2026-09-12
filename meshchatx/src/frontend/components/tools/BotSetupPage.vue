<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas">
        <ToolsPageHeader
            icon="robot-plus"
            :title="$t('bots.setup_title')"
            :description="$t('bots.setup_description')"
            accent="blue"
            back-to="/bots"
            :back-label="$t('tools.bots.title')"
        />
        <div
            class="flex-1 overflow-y-auto w-full px-3 sm:px-4 md:px-5 lg:px-8 py-4 sm:py-6 pb-[max(1.5rem,env(safe-area-inset-bottom))]"
        >
            <div class="space-y-6 w-full max-w-3xl mx-auto">
                <div v-if="loading" class="text-sm text-sem-fg-muted">
                    {{ $t("bots.loading") }}
                </div>

                <template v-else>
                    <div class="rounded-lg border border-sem-border bg-sem-surface p-4 sm:p-5">
                        <h3 class="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-3">
                            {{ $t("bots.choose_template") }}
                        </h3>
                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            <button
                                v-for="template in templates"
                                :key="template.id"
                                type="button"
                                class="relative flex items-start gap-3 rounded-lg border-2 p-3 text-left transition-all hover:bg-sem-surface-muted"
                                :class="
                                    selectedTemplateId === template.id
                                        ? 'border-blue-500 bg-sem-surface-muted'
                                        : 'border-sem-border'
                                "
                                @click="selectTemplate(template)"
                            >
                                <LxmfUserIcon
                                    v-if="template.default_icon"
                                    :icon-name="template.default_icon"
                                    icon-class="size-9 shrink-0"
                                />
                                <div class="min-w-0">
                                    <div class="font-semibold text-sem-fg text-sm">
                                        {{ template.name }}
                                    </div>
                                    <div class="text-xs text-gray-600 dark:text-gray-400 mt-0.5">
                                        {{ template.description }}
                                    </div>
                                </div>
                                <MaterialDesignIcon
                                    v-if="selectedTemplateId === template.id"
                                    icon-name="check-circle"
                                    class="size-5 text-blue-500 absolute top-2 right-2"
                                />
                            </button>
                        </div>
                    </div>

                    <template v-if="selectedTemplate">
                        <div class="rounded-lg border border-sem-border bg-sem-surface p-4 sm:p-5">
                            <label class="glass-label">{{ $t("bots.bot_name") }}</label>
                            <input
                                v-model="name"
                                type="text"
                                :placeholder="selectedTemplate.name"
                                class="input-field"
                                maxlength="256"
                            />
                        </div>

                        <div
                            v-if="selectedTemplateId === 'custom'"
                            class="rounded-lg border border-sem-border bg-sem-surface p-4 sm:p-5"
                        >
                            <h3 class="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-3">
                                {{ $t("bots.custom_section") }}
                            </h3>
                            <BotCustomCommandsEditor v-model="customDraft" />
                        </div>

                        <div
                            v-if="selectedTemplateId === 'rrc'"
                            class="rounded-lg border border-sem-border bg-sem-surface p-4 sm:p-5"
                        >
                            <h3 class="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-3">
                                {{ $t("bots.rrc_section") }}
                            </h3>
                            <BotRrcFields v-model="rrcDraft" />
                        </div>

                        <div class="rounded-lg border border-sem-border bg-sem-surface p-4 sm:p-5">
                            <h3 class="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-3">
                                {{ $t("bots.appearance") }}
                            </h3>
                            <LxmfIconEditor v-model="iconDraft" />
                        </div>

                        <div class="rounded-lg border border-sem-border bg-sem-surface p-4 sm:p-5">
                            <h3 class="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-1">
                                {{ $t("bots.advanced_lxmf_settings") }}
                            </h3>
                            <p class="text-xs text-sem-fg-muted mb-3">
                                {{ $t("bots.advanced_lxmf_settings_hint") }}
                            </p>
                            <LxmfConfigFields v-model="lxmfDraft" />
                        </div>

                        <div class="flex justify-end gap-2 pb-4">
                            <button
                                type="button"
                                class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-sem-fg-muted hover:bg-gray-50 dark:hover:bg-zinc-700 transition-colors"
                                :disabled="isStarting"
                                @click="goBack"
                            >
                                {{ $t("common.cancel") }}
                            </button>
                            <button
                                type="button"
                                class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border transition-colors disabled:opacity-50 disabled:cursor-not-allowed bg-blue-600 text-white border-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:border-blue-500 dark:hover:bg-blue-600"
                                :disabled="isStarting || !canCreate"
                                @click="createBot"
                            >
                                <span
                                    v-if="isStarting"
                                    class="inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin"
                                ></span>
                                <MaterialDesignIcon v-else icon-name="robot-plus" class="size-4" />
                                {{ $t("bots.create_and_start") }}
                            </button>
                        </div>
                    </template>
                </template>
            </div>
        </div>
    </div>
</template>

<script>
import ToastUtils from "../../js/ToastUtils";
import { apiPath } from "../../js/constants.js";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import LxmfUserIcon from "../LxmfUserIcon.vue";
import LxmfIconEditor, { defaultBotIconDraft } from "../LxmfIconEditor.vue";
import ToolsPageHeader from "./ToolsPageHeader.vue";
import LxmfConfigFields from "./internal/BotLxmfConfigFields.vue";
import BotCustomCommandsEditor, {
    buildCustomPayload,
    defaultCustomDraft,
} from "./internal/BotCustomCommandsEditor.vue";
import BotRrcFields, { buildRrcPayload, defaultRrcDraft } from "./internal/BotRrcFields.vue";
import { buildLxmfConfigPatch, defaultLxmfConfigDraft } from "./internal/botLxmfConfigForm.js";

export default {
    name: "BotSetupPage",
    components: {
        MaterialDesignIcon,
        LxmfUserIcon,
        LxmfIconEditor,
        ToolsPageHeader,
        LxmfConfigFields,
        BotCustomCommandsEditor,
        BotRrcFields,
    },
    data() {
        return {
            templates: [],
            loading: true,
            selectedTemplateId: null,
            name: "",
            lxmfDraft: defaultLxmfConfigDraft(),
            iconDraft: null,
            customDraft: defaultCustomDraft(),
            rrcDraft: defaultRrcDraft(),
            isStarting: false,
        };
    },
    computed: {
        selectedTemplate() {
            return this.templates.find((t) => t.id === this.selectedTemplateId) || null;
        },
        canCreate() {
            if (!this.selectedTemplateId) {
                return false;
            }
            if (this.selectedTemplateId === "rrc") {
                return /^[0-9a-f]{32}$/.test((this.rrcDraft.hub || "").trim().toLowerCase());
            }
            if (this.selectedTemplateId === "custom") {
                return buildCustomPayload(this.customDraft).commands.length > 0;
            }
            return true;
        },
    },
    mounted() {
        this.loadTemplates();
    },
    methods: {
        async loadTemplates() {
            try {
                const response = await window.api.get(apiPath("/bots/status"));
                this.templates = response.data.templates || [];
                const wanted = this.$route.query.template;
                const found = this.templates.find((t) => t.id === wanted);
                this.selectTemplate(found || this.templates[0] || null);
            } catch (e) {
                console.error("[BotSetupPage] status failed", e?.response?.data || e?.message || e);
                ToastUtils.error(this.$t("bots.failed_to_load"));
            } finally {
                this.loading = false;
            }
        },
        selectTemplate(template) {
            if (!template) {
                this.selectedTemplateId = null;
                return;
            }
            this.selectedTemplateId = template.id;
            if (!this.name || this.isTemplateDefaultName(this.name)) {
                this.name = template.name;
            }
            if (!this.iconDraft) {
                this.iconDraft = template.default_icon ? defaultBotIconDraft(template.default_icon) : null;
            }
        },
        isTemplateDefaultName(name) {
            return this.templates.some((t) => t.name === name);
        },
        async createBot() {
            if (this.isStarting || !this.selectedTemplate) {
                return;
            }
            const templateId = this.selectedTemplate.id;
            if (templateId === "rrc" && !this.canCreate) {
                ToastUtils.error(this.$t("bots.rrc_hub_required"));
                return;
            }
            if (templateId === "custom" && !this.canCreate) {
                ToastUtils.error(this.$t("bots.custom_requires_command"));
                return;
            }
            this.isStarting = true;
            try {
                const payload = {
                    template_id: templateId,
                    name: this.name,
                };
                const lxmfPatch = buildLxmfConfigPatch(this.lxmfDraft);
                if (Object.keys(lxmfPatch).length > 0) {
                    payload.lxmf_config = lxmfPatch;
                }
                if (this.iconDraft && this.iconDraft.icon_name) {
                    payload.icon = this.iconDraft;
                }
                if (templateId === "custom") {
                    payload.custom = buildCustomPayload(this.customDraft);
                }
                if (templateId === "rrc") {
                    payload.rrc = buildRrcPayload(this.rrcDraft);
                }
                await window.api.post(apiPath("/bots/start"), payload);
                ToastUtils.success(this.$t("bots.bot_started"));
                this.$router.push("/bots");
            } catch (e) {
                console.error(e);
                ToastUtils.error(e.response?.data?.message || this.$t("bots.failed_to_start"));
            } finally {
                this.isStarting = false;
            }
        },
        goBack() {
            this.$router.push("/bots");
        },
    },
};
</script>

<style scoped>
@reference "../../style.css";
.glass-label {
    @apply block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1;
}
</style>
