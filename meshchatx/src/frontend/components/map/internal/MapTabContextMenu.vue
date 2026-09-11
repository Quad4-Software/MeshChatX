<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <Teleport to="body">
        <ContextMenuPanel
            v-click-outside="{
                handler: () => {
                    if (!justOpened) $emit('close');
                },
                capture: true,
            }"
            :show="show"
            :x="x"
            :y="y"
        >
            <ContextMenuItem @click="$emit('rename')">
                <MaterialDesignIcon icon-name="pencil-outline" class="size-5" />
                <span>{{ $t("common.rename") }}</span>
            </ContextMenuItem>
            <ContextMenuItem @click="$emit('new-tab')">
                <MaterialDesignIcon icon-name="plus" class="size-5" />
                <span>{{ $t("map.new_tab") }}</span>
            </ContextMenuItem>
            <ContextMenuDivider />
            <ContextMenuItem @click="$emit('close-tab')">
                <MaterialDesignIcon icon-name="close" class="size-5" />
                <span>{{ $t("common.close") }}</span>
            </ContextMenuItem>
            <ContextMenuItem :disabled="!canCloseRight" @click="$emit('close-right')">
                <MaterialDesignIcon icon-name="tab-remove" class="size-5" />
                <span>{{ $t("map.close_tabs_to_right") }}</span>
            </ContextMenuItem>
            <ContextMenuItem :disabled="!canCloseOthers" @click="$emit('close-others')">
                <MaterialDesignIcon icon-name="tab-minus" class="size-5" />
                <span>{{ $t("map.close_other_tabs") }}</span>
            </ContextMenuItem>
            <ContextMenuItem :disabled="!canCloseAll" @click="$emit('close-all')">
                <MaterialDesignIcon icon-name="close-box-multiple-outline" class="size-5" />
                <span>{{ $t("map.close_all_tabs") }}</span>
            </ContextMenuItem>
        </ContextMenuPanel>
    </Teleport>
</template>

<script>
import ContextMenuDivider from "../../contextmenu/ContextMenuDivider.vue";
import ContextMenuItem from "../../contextmenu/ContextMenuItem.vue";
import ContextMenuPanel from "../../contextmenu/ContextMenuPanel.vue";
import MaterialDesignIcon from "../../MaterialDesignIcon.vue";

export default {
    name: "MapTabContextMenu",
    components: {
        ContextMenuDivider,
        ContextMenuItem,
        ContextMenuPanel,
        MaterialDesignIcon,
    },
    props: {
        show: {
            type: Boolean,
            required: true,
        },
        x: {
            type: Number,
            required: true,
        },
        y: {
            type: Number,
            required: true,
        },
        justOpened: {
            type: Boolean,
            default: false,
        },
        canCloseRight: {
            type: Boolean,
            default: false,
        },
        canCloseOthers: {
            type: Boolean,
            default: false,
        },
        canCloseAll: {
            type: Boolean,
            default: false,
        },
    },
    emits: ["close", "rename", "new-tab", "close-tab", "close-right", "close-others", "close-all"],
};
</script>
