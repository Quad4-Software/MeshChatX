<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <Teleport to="body">
        <ContextMenuPanel
            v-click-outside="{
                handler: () => {
                    if (!justOpened) emit('close');
                },
                capture: true,
            }"
            :show="show"
            :x="x"
            :y="y"
        >
            <ContextMenuItem :disabled="!hasActivePage" @click="emit('view-source')">
                <MaterialDesignIcon icon-name="code-tags" class="size-5" />
                <span>{{ $t("app.toggle_source") }}</span>
            </ContextMenuItem>
            <ContextMenuItem :disabled="!hasActivePage" @click="emit('reload')">
                <MaterialDesignIcon icon-name="refresh" class="size-5" />
                <span>{{ $t("common.refresh") }}</span>
            </ContextMenuItem>
            <ContextMenuItem :disabled="!canFavourite" @click="emit('favorite')">
                <MaterialDesignIcon :icon-name="isFavourite ? 'star-off' : 'star'" class="size-5" />
                <span>{{ isFavourite ? $t("nomadnet.remove_favourite") : $t("nomadnet.add_favourite") }}</span>
            </ContextMenuItem>
            <ContextMenuItem :disabled="!canDownloadPage" @click="emit('download-page')">
                <MaterialDesignIcon icon-name="download" class="size-5" />
                <span>{{ $t("nomadnet.download_page") }}</span>
            </ContextMenuItem>
            <template v-if="showTabActions">
                <ContextMenuDivider />
                <ContextMenuSectionLabel>{{ $t("nomadnet.context_tabs") }}</ContextMenuSectionLabel>
                <ContextMenuItem @click="emit('new-private-tab')">
                    <MaterialDesignIcon icon-name="incognito" class="size-5 text-purple-400" />
                    <span>{{ $t("nomadnet.new_private_tab") }}</span>
                </ContextMenuItem>
                <ContextMenuItem :disabled="!canCloseTabsRight" @click="emit('close-tabs-right')">
                    <MaterialDesignIcon icon-name="tab-remove" class="size-5" />
                    <span>{{ $t("nomadnet.close_tabs_to_right") }}</span>
                </ContextMenuItem>
                <ContextMenuItem :disabled="!canCloseOtherTabs" @click="emit('close-other-tabs')">
                    <MaterialDesignIcon icon-name="tab-minus" class="size-5" />
                    <span>{{ $t("nomadnet.close_other_tabs") }}</span>
                </ContextMenuItem>
                <ContextMenuItem :disabled="!canCloseAllTabs" @click="emit('close-all-tabs')">
                    <MaterialDesignIcon icon-name="close-box-multiple-outline" class="size-5" />
                    <span>{{ $t("nomadnet.close_all_tabs") }}</span>
                </ContextMenuItem>
            </template>
        </ContextMenuPanel>
    </Teleport>
</template>

<script setup lang="ts">
import ContextMenuDivider from "../contextmenu/ContextMenuDivider.vue";
import ContextMenuItem from "../contextmenu/ContextMenuItem.vue";
import ContextMenuPanel from "../contextmenu/ContextMenuPanel.vue";
import ContextMenuSectionLabel from "../contextmenu/ContextMenuSectionLabel.vue";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";

withDefaults(
    defineProps<{
        show: boolean;
        x: number;
        y: number;
        justOpened?: boolean;
        hasActivePage?: boolean;
        canFavourite?: boolean;
        isFavourite?: boolean;
        canDownloadPage?: boolean;
        showTabActions?: boolean;
        canCloseTabsRight?: boolean;
        canCloseOtherTabs?: boolean;
        canCloseAllTabs?: boolean;
        contextTabIsPrivate?: boolean;
    }>(),
    {
        justOpened: false,
        hasActivePage: false,
        canFavourite: false,
        isFavourite: false,
        canDownloadPage: false,
        showTabActions: false,
        canCloseTabsRight: false,
        canCloseOtherTabs: false,
        canCloseAllTabs: false,
        contextTabIsPrivate: false,
    }
);

const emit = defineEmits<{
    close: [];
    "view-source": [];
    reload: [];
    favorite: [];
    "download-page": [];
    "new-private-tab": [];
    "close-tabs-right": [];
    "close-other-tabs": [];
    "close-all-tabs": [];
}>();
</script>
