<template>
    <div class="h-screen w-full flex items-center justify-center bg-slate-50 dark:bg-zinc-950">
        <div class="w-full max-w-md p-8">
            <div
                class="bg-white dark:bg-zinc-900 rounded-2xl shadow-lg border border-gray-200 dark:border-zinc-800 p-8"
            >
                <div class="text-center mb-8">
                    <div
                        class="w-16 h-16 mx-auto mb-4 rounded-2xl overflow-hidden bg-white/70 dark:bg-white/10 border border-gray-200 dark:border-zinc-700 shadow-inner flex items-center justify-center"
                    >
                        <img class="w-16 h-16 object-contain p-2" :src="logoUrl" />
                    </div>
                    <h1 class="text-2xl font-bold text-gray-900 dark:text-zinc-100 mb-2">
                        {{ isSetup ? "Initial Setup" : "Authentication Required" }}
                    </h1>
                    <p class="text-sm text-gray-600 dark:text-zinc-400">
                        {{
                            isSetup
                                ? "Set an admin password to secure your MeshChatX instance"
                                : "Please enter your password to continue"
                        }}
                    </p>
                </div>

                <form class="space-y-6" @submit.prevent="handleSubmit">
                    <div>
                        <label for="password" class="block text-sm font-medium text-gray-700 dark:text-zinc-300 mb-2">
                            Password
                        </label>
                        <input
                            id="password"
                            v-model="password"
                            type="password"
                            required
                            minlength="8"
                            class="w-full px-4 py-2 border border-gray-300 dark:border-zinc-700 rounded-lg bg-white dark:bg-zinc-800 text-gray-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="Enter password"
                            autocomplete="current-password"
                        />
                        <p v-if="isSetup" class="mt-2 text-xs text-gray-500 dark:text-zinc-500">
                            Password must be at least 8 characters long
                        </p>
                    </div>

                    <div v-if="isSetup">
                        <label
                            for="confirmPassword"
                            class="block text-sm font-medium text-gray-700 dark:text-zinc-300 mb-2"
                        >
                            Confirm Password
                        </label>
                        <input
                            id="confirmPassword"
                            v-model="confirmPassword"
                            type="password"
                            required
                            minlength="8"
                            class="w-full px-4 py-2 border border-gray-300 dark:border-zinc-700 rounded-lg bg-white dark:bg-zinc-800 text-gray-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="Confirm password"
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
                        <span v-if="isLoading">Processing...</span>
                        <span v-else>{{ isSetup ? "Set Password" : "Login" }}</span>
                    </button>
                </form>
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
        };
    },
    async mounted() {
        await this.checkAuthStatus();
    },
    methods: {
        async checkAuthStatus() {
            try {
                const response = await window.axios.get("/api/v1/auth/status");
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
            } catch (e) {
                console.error("Failed to check auth status:", e);
                this.error = "Failed to check authentication status";
            }
        },
        async handleSubmit() {
            this.error = "";

            if (this.isSetup) {
                if (this.password !== this.confirmPassword) {
                    this.error = "Passwords do not match";
                    return;
                }

                if (this.password.length < 8) {
                    this.error = "Password must be at least 8 characters long";
                    return;
                }
            }

            this.isLoading = true;

            try {
                const endpoint = this.isSetup ? "/api/v1/auth/setup" : "/api/v1/auth/login";
                await window.axios.post(endpoint, {
                    password: this.password,
                });

                window.location.reload();
            } catch (e) {
                this.error = e.response?.data?.error || "Authentication failed";
                this.password = "";
                this.confirmPassword = "";
            } finally {
                this.isLoading = false;
            }
        },
    },
};
</script>
