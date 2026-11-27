<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <article
        v-if="archive"
        ref="rootEl"
        class="group flex cursor-pointer flex-col overflow-hidden rounded-2xl border border-sem-border/70 bg-sem-surface/40 shadow-sm transition-colors hover:border-sem-accent/40 hover:bg-sem-surface/70"
        :class="{
            'ring-2 ring-sem-accent/40 border-sem-accent/40': active,
        }"
        @click="emit('open', archive)"
    >
        <div class="flex items-start justify-between gap-2 border-b border-sem-border/50 px-3 py-2.5">
            <div class="min-w-0">
                <h2 class="truncate text-sm font-semibold group-hover:text-sem-accent">
                    {{ archive.node_name }}
                </h2>
                <p class="mt-0.5 truncate font-mono text-[11px] text-sem-fg-muted">
                    {{ archive.page_path || "/" }}
                </p>
            </div>
            <div class="shrink-0 text-right text-[10px] text-sem-fg-muted">
                <div>{{ formatDate(archive.created_at) }}</div>
                <div class="mt-0.5 font-mono opacity-70">
                    {{ (archive.hash || "").substring(0, 8) }}
                </div>
            </div>
        </div>

        <div class="archive-card-preview min-h-[5.5rem] flex-1 overflow-hidden px-3 py-2">
            <!-- eslint-disable vue/no-v-html -- sanitized via renderPreviewHtml -->
            <div
                v-if="previewRendered"
                class="pointer-events-none max-h-36 overflow-hidden text-xs leading-relaxed text-sem-fg-muted"
                :class="previewClasses"
                v-html="previewHtml"
            ></div>
            <!-- eslint-enable vue/no-v-html -->
            <div v-else class="space-y-2 py-1" aria-hidden="true">
                <Skeleton variant="line" root-class="w-11/12" />
                <Skeleton variant="line" root-class="w-full" />
                <Skeleton variant="line" root-class="w-3/4" />
            </div>
        </div>

        <div class="flex items-center justify-between gap-2 border-t border-sem-border/50 px-3 py-2">
            <span class="rounded bg-sem-surface-muted px-1.5 py-0.5 font-mono text-[10px] text-sem-fg-muted">
                {{ shortHash(archive.destination_hash) }}
            </span>
            <span class="flex items-center gap-2.5">
                <button
                    type="button"
                    class="text-[10px] font-medium text-sem-fg-muted transition-colors hover:text-sem-accent disabled:opacity-60"
                    :disabled="exporting"
                    :title="$t('archives.export_mu')"
                    @click.stop="emit('export', archive)"
                >
                    {{ exporting ? $t("archives.exporting") : $t("archives.export") }}
                </button>
                <span
                    class="text-[10px] font-medium text-sem-accent opacity-0 transition-opacity group-hover:opacity-100"
                >
                    {{ $t("archives.view") }}
                </span>
            </span>
        </div>
    </article>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import Skeleton from "../Skeleton.vue";
import Utils from "../../js/Utils";
import { attachInView } from "../../js/inViewObserver.js";

const props = withDefaults(
    defineProps<{
        archive: Record<string, any>;
        active?: boolean;
        exporting?: boolean;
        renderPreview: (...args: any[]) => any;
        previewClasses?: any[] | string;
        previewEpoch?: number;
    }>(),
    {
        active: false,
        exporting: false,
        previewClasses: () => [],
        previewEpoch: 0,
    }
);

const emit = defineEmits<{
    open: [archive: any];
    export: [archive: any];
}>();

const inView = ref(false);
const previewHtml = ref("");
const previewRendered = ref(false);
const rootEl = ref<HTMLElement | null>(null);

let detachInView: (() => void) | null = null;

watch(
    () => props.previewEpoch,
    () => {
        if (inView.value) {
            renderPreviewNow();
        }
    }
);

watch(
    () => props.archive?.hash,
    () => {
        if (inView.value) {
            renderPreviewNow();
        }
    }
);

onMounted(() => {
    const el = rootEl.value;
    if (!props.archive || !(el instanceof Element)) {
        return;
    }
    detachInView = attachInView(
        el,
        (entry: IntersectionObserverEntry) => {
            if (!entry.isIntersecting) {
                return;
            }
            inView.value = true;
            renderPreviewNow();
            detachInView?.();
            detachInView = null;
        },
        { rootMargin: "300px 0px" }
    );
});

onBeforeUnmount(() => {
    detachInView?.();
    detachInView = null;
});

function renderPreviewNow() {
    previewHtml.value = props.renderPreview(props.archive) || "";
    previewRendered.value = true;
}

function shortHash(hash: string) {
    return (hash || "").substring(0, 12);
}

function formatDate(dateStr: string) {
    return Utils.formatTimeAgo(dateStr);
}
</script>
