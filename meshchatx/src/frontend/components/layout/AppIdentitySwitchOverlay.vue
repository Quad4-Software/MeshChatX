<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <transition name="fade-blur">
        <div
            v-if="show"
            class="fixed inset-0 z-200 flex items-center justify-center bg-slate-900/45 dark:bg-black/55 backdrop-blur-xs px-4"
            role="status"
            aria-live="polite"
        >
            <div
                class="w-full max-w-sm overflow-hidden rounded-2xl border border-gray-200/90 bg-white/95 shadow-xl dark:border-zinc-700/90 dark:bg-zinc-900/95"
            >
                <div class="px-6 pt-7 pb-1 text-center">
                    <div
                        class="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-50 ring-1 ring-gray-200/80 dark:bg-zinc-950 dark:ring-zinc-700"
                    >
                        <img :src="logoUrl" alt="" class="h-9 w-9 object-contain p-1" />
                    </div>
                    <p class="text-xs font-medium text-gray-500 dark:text-zinc-500">
                        {{ $t("app.loading_overlay_kicker") }}
                    </p>
                    <h2 class="mt-1.5 text-lg font-semibold tracking-tight text-gray-900 dark:text-white">
                        {{ $t("app.loading_overlay_title") }}
                    </h2>
                    <p class="mt-3 text-sm leading-relaxed text-gray-600 dark:text-zinc-400">
                        {{ $t("app.loading_overlay_subtitle") }}
                    </p>
                </div>
                <div class="px-6 pb-7 pt-2">
                    <div class="h-1 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-zinc-800">
                        <div
                            class="identity-switch-indeterminate h-full w-1/3 rounded-full bg-blue-600 dark:bg-blue-500"
                        />
                    </div>
                </div>
            </div>
        </div>
    </transition>
</template>

<script>
export default {
    name: "AppIdentitySwitchOverlay",
    props: {
        show: {
            type: Boolean,
            default: false,
        },
        logoUrl: {
            type: String,
            required: true,
        },
    },
};
</script>

<style>
@keyframes identity-switch-indeterminate {
    0% {
        transform: translateX(-100%);
    }
    100% {
        transform: translateX(350%);
    }
}

.identity-switch-indeterminate {
    animation: identity-switch-indeterminate 1.4s ease-in-out infinite;
}

.fade-blur-enter-active,
.fade-blur-leave-active {
    transition: all 0.5s ease;
}

.fade-blur-enter-from,
.fade-blur-leave-to {
    opacity: 0;
    backdrop-filter: blur(0);
}
</style>
