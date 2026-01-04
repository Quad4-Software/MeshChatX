<template>
    <div class="flex flex-col h-full w-full bg-white dark:bg-zinc-950 overflow-hidden">
        <!-- header -->
        <div
            class="flex items-center px-4 py-2 border-b border-gray-200 dark:border-zinc-800 bg-white/60 dark:bg-zinc-900/50 backdrop-blur-lg z-10 relative"
        >
            <div class="flex items-center space-x-2">
                <v-icon icon="mdi-chip" color="purple" size="24"></v-icon>
                <h1 class="text-xl font-black text-gray-900 dark:text-white">{{ $t("tools.rnode_flasher.title") }}</h1>
            </div>

            <div class="ml-auto flex items-center space-x-2">
                <a
                    href="/rnode-flasher/index.html"
                    target="_blank"
                    class="p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-zinc-800 rounded-lg transition-colors flex items-center gap-2 text-sm font-medium"
                    title="Open in new tab"
                >
                    <MaterialDesignIcon icon-name="open-in-new" class="size-5" />
                    <span class="hidden sm:inline">Open in new tab</span>
                </a>
                <button
                    class="p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-zinc-800 rounded-lg transition-colors"
                    @click="$router.push({ name: 'tools' })"
                >
                    <MaterialDesignIcon icon-name="close" class="size-5" />
                </button>
            </div>
        </div>

        <!-- content -->
        <div class="flex-1 min-h-0 relative">
            <iframe src="/rnode-flasher/index.html" class="w-full h-full border-0" allow="serial"></iframe>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";

export default {
    name: "RNodeFlasherPage",
    components: {
        MaterialDesignIcon,
    },
};
</script>
