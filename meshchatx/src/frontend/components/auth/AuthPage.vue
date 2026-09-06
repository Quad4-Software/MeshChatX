<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="h-dvh min-h-0 w-full flex flex-col bg-sem-canvas">
        <div class="flex-1 min-h-0 flex items-center justify-center">
            <div class="w-full max-w-md p-8">
                <div class="bg-sem-surface rounded-2xl shadow-lg border border-sem-border p-8">
                    <div class="text-center mb-8">
                        <div
                            class="w-16 h-16 mx-auto mb-4 rounded-2xl overflow-hidden bg-white/70 dark:bg-white/10 border border-sem-border shadow-inner flex items-center justify-center"
                        >
                            <img class="w-16 h-16 object-contain p-2" :src="logoUrl" alt="" />
                        </div>
                        <h1 class="text-2xl font-bold text-sem-fg mb-2">
                            {{ isSetup ? $t("auth.setup_title") : $t("auth.login_title") }}
                        </h1>
                        <p class="text-sm text-sem-fg-muted">
                            {{ isSetup ? $t("auth.setup_subtitle") : $t("auth.login_subtitle") }}
                        </p>
                        <p v-if="authPageHint" class="mt-3 text-xs text-sem-fg-muted whitespace-pre-line">
                            {{ authPageHint }}
                        </p>
                    </div>

                    <form class="space-y-6" @submit.prevent="handleSubmit">
                        <div>
                            <label for="password" class="block text-sm font-medium text-sem-fg-muted mb-2">
                                {{ $t("auth.password_label") }}
                            </label>
                            <input
                                id="password"
                                v-model="password"
                                type="password"
                                required
                                :minlength="isSetup ? 8 : 1"
                                class="w-full px-4 py-2 border border-gray-300 dark:border-zinc-700 rounded-lg bg-white dark:bg-zinc-800 text-sem-fg focus:outline-hidden focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                :placeholder="$t('auth.password_placeholder')"
                                autocomplete="current-password"
                            />
                            <p v-if="isSetup" class="mt-2 text-xs text-sem-fg-muted">
                                {{ $t("auth.password_min_length") }}
                            </p>
                        </div>

                        <div v-if="isSetup">
                            <label for="confirmPassword" class="block text-sm font-medium text-sem-fg-muted mb-2">
                                {{ $t("auth.confirm_password_label") }}
                            </label>
                            <input
                                id="confirmPassword"
                                v-model="confirmPassword"
                                type="password"
                                required
                                minlength="8"
                                class="w-full px-4 py-2 border border-gray-300 dark:border-zinc-700 rounded-lg bg-white dark:bg-zinc-800 text-sem-fg focus:outline-hidden focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                :placeholder="$t('auth.confirm_password_placeholder')"
                                autocomplete="new-password"
                            />
                        </div>

                        <div
                            v-if="error"
                            class="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg"
                        >
                            <p class="text-sm text-red-800 dark:text-red-200">{{ error }}</p>
                        </div>

                        <button
                            type="submit"
                            :disabled="isLoading || (isSetup && password !== confirmPassword)"
                            class="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors"
                        >
                            <span v-if="isLoading">{{ $t("auth.processing") }}</span>
                            <span v-else>{{ isSetup ? $t("auth.set_password") : $t("auth.login") }}</span>
                        </button>
                    </form>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import logoUrl from "../../assets/images/logo.png";

export default {
    name: "AuthPage",
    data() {
        return {
            logoUrl,
            password: "",
            confirmPassword: "",
            error: "",
            isLoading: false,
            isSetup: false,
            authPageHint: "",
        };
    },
    async mounted() {
        await this.checkAuthStatus();
    },
    methods: {
        async checkAuthStatus() {
            try {
                const response = await window.api.get("/api/v1/auth/status");
                const status = response.data;

                if (!status.auth_enabled) {
                    this.$router.push("/");
                    return;
                }

                if (status.authenticated) {
                    this.$router.push("/");
                    return;
                }

                this.isSetup = !status.password_set;
                const hint = status.auth_page_hint;
                this.authPageHint = typeof hint === "string" ? hint : "";
            } catch (e) {
                console.error("Failed to check auth status:", e);
                this.error = this.$t("auth.status_check_failed");
            }
        },
        async handleSubmit() {
            this.error = "";

            if (this.isSetup) {
                if (this.password !== this.confirmPassword) {
                    this.error = this.$t("auth.passwords_mismatch");
                    return;
                }

                if (this.password.length < 8) {
                    this.error = this.$t("auth.password_min_length");
                    return;
                }
            }

            this.isLoading = true;

            try {
                const endpoint = this.isSetup ? "/api/v1/auth/setup" : "/api/v1/auth/login";
                const body = { password: this.password };
                await window.api.post(endpoint, body);

                window.location.reload();
            } catch (e) {
                this.error = e.response?.data?.error || this.$t("auth.failed");
                this.password = "";
                this.confirmPassword = "";
            } finally {
                this.isLoading = false;
            }
        },
    },
};
</script>
