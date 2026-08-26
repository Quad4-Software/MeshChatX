<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <Transition name="confirm-dialog">
        <div
            v-if="pendingConfirm"
            class="fixed inset-0 z-9999 flex items-center justify-center p-4"
            role="alertdialog"
            aria-modal="true"
            :aria-labelledby="titleId"
            :aria-describedby="messageId"
        >
            <div class="fixed inset-0 bg-black/50 backdrop-blur-xs shadow-2xl" @click="cancel"></div>

            <div
                ref="dialogPanel"
                class="relative w-full sm:w-auto sm:min-w-[400px] sm:max-w-md bg-sem-surface sm:rounded-3xl rounded-3xl shadow-2xl border border-sem-border overflow-hidden transform transition-all"
                tabindex="-1"
                @click.stop
                @keydown.esc.prevent="cancel"
            >
                <div class="p-8">
                    <div class="flex items-start mb-6">
                        <div
                            class="shrink-0 flex items-center justify-center w-12 h-12 rounded-2xl bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 mr-4"
                        >
                            <MaterialDesignIcon icon-name="alert-circle" class="w-6 h-6" />
                        </div>
                        <div class="flex-1 min-w-0">
                            <h3 :id="titleId" class="text-xl font-black text-sem-fg mb-2">
                                {{ pendingConfirm.title || $t("common.confirm_action") }}
                            </h3>
                            <p :id="messageId" class="text-sem-fg-muted whitespace-pre-wrap leading-relaxed">
                                {{ pendingConfirm.message }}
                            </p>
                        </div>
                    </div>

                    <div class="flex flex-col sm:flex-row gap-3 sm:justify-end mt-8">
                        <button
                            ref="cancelButton"
                            type="button"
                            data-confirm-cancel
                            class="px-6 py-3 text-sm font-bold text-sem-fg-muted bg-sem-surface-muted rounded-xl hover:bg-gray-200 hover:bg-sem-surface-muted transition-all active:scale-95"
                            @click="cancel"
                        >
                            {{ $t("common.cancel") }}
                        </button>
                        <button
                            ref="confirmButton"
                            type="button"
                            class="px-6 py-3 text-sm font-bold text-white bg-red-600 hover:bg-red-700 rounded-xl shadow-lg shadow-red-600/20 transition-all active:scale-95"
                            @click="confirm"
                        >
                            {{ $t("common.confirm") }}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </Transition>
</template>

<script>
import GlobalEmitter from "../js/GlobalEmitter";
import MaterialDesignIcon from "./MaterialDesignIcon.vue";

function isComposingKey(event) {
    return Boolean(event && (event.isComposing || event.keyCode === 229));
}

function isTextEntryTarget(target) {
    if (!target || typeof target !== "object") {
        return false;
    }
    const tag = String(target.tagName || "").toLowerCase();
    if (tag === "input" || tag === "textarea" || tag === "select") {
        return true;
    }
    return Boolean(target.isContentEditable);
}

export default {
    name: "ConfirmDialog",
    components: {
        MaterialDesignIcon,
    },
    data() {
        return {
            pendingConfirm: null,
            resolvePromise: null,
            enterIsDown: false,
            keyboardArmed: false,
            titleId: "confirm-dialog-title",
            messageId: "confirm-dialog-message",
        };
    },
    mounted() {
        GlobalEmitter.on("confirm", this.show);
        GlobalEmitter.on("prompt", this.dismissForOtherDialog);
        window.addEventListener("keydown", this.onWindowKeydown, true);
        window.addEventListener("keyup", this.onWindowKeyup, true);
    },
    beforeUnmount() {
        this.cancel();
        GlobalEmitter.off("confirm", this.show);
        GlobalEmitter.off("prompt", this.dismissForOtherDialog);
        window.removeEventListener("keydown", this.onWindowKeydown, true);
        window.removeEventListener("keyup", this.onWindowKeyup, true);
    },
    methods: {
        show({ message, title, resolve } = {}) {
            if (typeof this.resolvePromise === "function") {
                this.resolvePromise(false);
            }
            this.pendingConfirm = {
                message: message == null ? "" : String(message),
                title: typeof title === "string" && title.trim() ? title.trim() : "",
            };
            this.resolvePromise = typeof resolve === "function" ? resolve : null;
            this.keyboardArmed = !this.enterIsDown;
            this.$nextTick(() => {
                if (this.keyboardArmed) {
                    this.focusDefaultButton();
                    return;
                }
                const panel = this.$refs.dialogPanel;
                if (panel && typeof panel.focus === "function") {
                    panel.focus();
                }
            });
        },
        dismissForOtherDialog() {
            this.cancel();
        },
        isCancelTarget(target) {
            if (!target || typeof target !== "object") {
                return false;
            }
            const cancelButton = this.$refs.cancelButton;
            if (cancelButton && target === cancelButton) {
                return true;
            }
            if (
                cancelButton &&
                typeof target.nodeType === "number" &&
                typeof cancelButton.contains === "function" &&
                cancelButton.contains(target)
            ) {
                return true;
            }
            return typeof target.closest === "function" && Boolean(target.closest("[data-confirm-cancel]"));
        },
        focusDefaultButton() {
            const button = this.$refs.confirmButton;
            if (button && typeof button.focus === "function") {
                button.focus();
            }
        },
        trapFocus(event) {
            const panel = this.$refs.dialogPanel;
            if (!panel) {
                return;
            }
            const nodes = panel.querySelectorAll("button");
            const list = Array.from(nodes).filter((el) => !el.disabled);
            if (list.length === 0) {
                event.preventDefault();
                event.stopPropagation();
                return;
            }
            const first = list[0];
            const last = list[list.length - 1];
            const active = document.activeElement;
            if (event.shiftKey && (active === first || !panel.contains(active))) {
                event.preventDefault();
                event.stopPropagation();
                last.focus();
                return;
            }
            if (!event.shiftKey && (active === last || !panel.contains(active))) {
                event.preventDefault();
                event.stopPropagation();
                first.focus();
            }
        },
        onWindowKeydown(event) {
            if (event.key === "Enter") {
                this.enterIsDown = true;
            }
            if (!this.pendingConfirm) {
                return;
            }
            if (event.key === "Escape") {
                event.preventDefault();
                event.stopPropagation();
                this.cancel();
                return;
            }
            if (event.key === "Tab") {
                this.trapFocus(event);
                return;
            }
            if (event.key !== "Enter") {
                return;
            }
            if (!this.keyboardArmed || event.repeat || isComposingKey(event)) {
                event.preventDefault();
                event.stopPropagation();
                return;
            }
            if (this.isCancelTarget(event.target) || isTextEntryTarget(event.target)) {
                return;
            }
            event.preventDefault();
            event.stopPropagation();
            this.confirm();
        },
        onWindowKeyup(event) {
            if (event.key !== "Enter") {
                return;
            }
            this.enterIsDown = false;
            if (this.pendingConfirm && !this.keyboardArmed) {
                this.keyboardArmed = true;
                this.focusDefaultButton();
            }
        },
        confirm() {
            if (this.resolvePromise) {
                this.resolvePromise(true);
                this.resolvePromise = null;
            }
            this.pendingConfirm = null;
            this.keyboardArmed = false;
        },
        cancel() {
            if (this.resolvePromise) {
                this.resolvePromise(false);
                this.resolvePromise = null;
            }
            this.pendingConfirm = null;
            this.keyboardArmed = false;
        },
    },
};
</script>

<style scoped>
.confirm-dialog-enter-active,
.confirm-dialog-leave-active {
    transition: all 0.2s ease;
}

.confirm-dialog-enter-from,
.confirm-dialog-leave-to {
    opacity: 0;
}

.confirm-dialog-enter-from .relative,
.confirm-dialog-leave-to .relative {
    transform: scale(0.95);
    opacity: 0;
}
</style>
