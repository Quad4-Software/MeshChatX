<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount } from "svelte";
    import logoUrl from "../../assets/images/logo.png";
    import { t } from "../../js/i18n.js";
    import { API_AUTH_LOGIN, API_AUTH_SETUP, API_AUTH_STATUS, AUTH_MIN_PASSWORD_LENGTH } from "./lib/constants.js";
    import { validateAuthForm, type AuthStatusPayload } from "./lib/authActions.js";

    interface Props {
        router?: { push: (path: string) => void };
    }

    let { router = undefined }: Props = $props();

    let password = $state("");
    let confirmPassword = $state("");
    let error = $state("");
    let isLoading = $state(false);
    let isSetup = $state(false);
    let authPageHint = $state("");

    function navigateHome(): void {
        if (router?.push) {
            router.push("/");
        } else {
            window.location.hash = "#/";
        }
    }

    async function checkAuthStatus(): Promise<void> {
        try {
            const response = await window.api.get(API_AUTH_STATUS);
            const status = (response?.data || {}) as AuthStatusPayload;

            if (!status.auth_enabled) {
                navigateHome();
                return;
            }

            if (status.authenticated) {
                navigateHome();
                return;
            }

            isSetup = !status.password_set;
            const hint = status.auth_page_hint;
            authPageHint = typeof hint === "string" ? hint : "";
        } catch (e) {
            console.error("Failed to check auth status:", e);
            error = t("auth.status_check_failed");
        }
    }

    async function handleSubmit(event?: Event): Promise<void> {
        if (event) {
            event.preventDefault();
        }
        error = "";

        const validation = validateAuthForm(isSetup, password, confirmPassword);
        if (!validation.valid && validation.errorKey) {
            error = t(validation.errorKey);
            return;
        }

        isLoading = true;

        try {
            const endpoint = isSetup ? API_AUTH_SETUP : API_AUTH_LOGIN;
            const body = { password };
            await window.api.post(endpoint, body);

            window.location.reload();
        } catch (e: any) {
            error = e?.response?.data?.error || t("auth.failed");
            password = "";
            confirmPassword = "";
        } finally {
            isLoading = false;
        }
    }

    onMount(() => {
        void checkAuthStatus();
    });
</script>

<div class="h-dvh min-h-0 w-full flex flex-col bg-sem-canvas" data-testid="auth-page">
    <div class="flex-1 min-h-0 flex items-center justify-center">
        <div class="w-full max-w-md p-8">
            <div class="bg-sem-surface rounded-2xl shadow-lg border border-sem-border p-8">
                <div class="text-center mb-8">
                    <div
                        class="w-16 h-16 mx-auto mb-4 rounded-2xl overflow-hidden bg-white/70 dark:bg-white/10 border border-sem-border shadow-inner flex items-center justify-center"
                    >
                        <img class="w-16 h-16 object-contain p-2" src={logoUrl} alt="" />
                    </div>
                    <h1 class="text-2xl font-bold text-sem-fg mb-2">
                        {isSetup ? t("auth.setup_title") : t("auth.login_title")}
                    </h1>
                    <p class="text-sm text-sem-fg-muted">
                        {isSetup ? t("auth.setup_subtitle") : t("auth.login_subtitle")}
                    </p>
                    {#if authPageHint}
                        <p class="mt-3 text-xs text-sem-fg-muted whitespace-pre-line">
                            {authPageHint}
                        </p>
                    {/if}
                </div>

                <form class="space-y-6" onsubmit={handleSubmit}>
                    <div>
                        <label for="password" class="block text-sm font-medium text-sem-fg-muted mb-2">
                            {t("auth.password_label")}
                        </label>
                        <input
                            id="password"
                            bind:value={password}
                            type="password"
                            required
                            minlength={isSetup ? AUTH_MIN_PASSWORD_LENGTH : 1}
                            class="w-full px-4 py-2 border border-gray-300 dark:border-zinc-700 rounded-lg bg-white dark:bg-zinc-800 text-sem-fg focus:outline-hidden focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder={t("auth.password_placeholder")}
                            autocomplete="current-password"
                        />
                        {#if isSetup}
                            <p class="mt-2 text-xs text-sem-fg-muted">
                                {t("auth.password_min_length")}
                            </p>
                        {/if}
                    </div>

                    {#if isSetup}
                        <div>
                            <label for="confirmPassword" class="block text-sm font-medium text-sem-fg-muted mb-2">
                                {t("auth.confirm_password_label")}
                            </label>
                            <input
                                id="confirmPassword"
                                bind:value={confirmPassword}
                                type="password"
                                required
                                minlength={AUTH_MIN_PASSWORD_LENGTH}
                                class="w-full px-4 py-2 border border-gray-300 dark:border-zinc-700 rounded-lg bg-white dark:bg-zinc-800 text-sem-fg focus:outline-hidden focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                placeholder={t("auth.confirm_password_placeholder")}
                                autocomplete="new-password"
                            />
                        </div>
                    {/if}

                    {#if error}
                        <div
                            class="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg"
                        >
                            <p class="text-sm text-red-800 dark:text-red-200">{error}</p>
                        </div>
                    {/if}

                    <button
                        type="submit"
                        disabled={isLoading || (isSetup && password !== confirmPassword)}
                        class="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors"
                    >
                        {#if isLoading}
                            <span>{t("auth.processing")}</span>
                        {:else}
                            <span>{isSetup ? t("auth.set_password") : t("auth.login")}</span>
                        {/if}
                    </button>
                </form>
            </div>
        </div>
    </div>
</div>
