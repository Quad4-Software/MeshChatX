// SPDX-License-Identifier: 0BSD

import { render, cleanup, fireEvent, waitFor, screen } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import AuthPage from "../../meshchatx/src/frontend/features/auth/AuthPage.svelte";
import { validateAuthForm } from "../../meshchatx/src/frontend/features/auth/lib/authActions.ts";
import {
    API_AUTH_LOGIN,
    API_AUTH_SETUP,
    API_AUTH_STATUS,
    AUTH_MIN_PASSWORD_LENGTH,
} from "../../meshchatx/src/frontend/features/auth/lib/constants.ts";
import { registerFallbackMessages, registerTranslator } from "../../meshchatx/src/frontend/js/i18n.ts";

const authI18n = {
    auth: {
        setup_title: "Initial Setup",
        login_title: "Authentication Required",
        setup_subtitle: "Set an admin password to secure your MeshChatX instance",
        login_subtitle: "Please enter your password to continue",
        password_label: "Password",
        password_placeholder: "Enter password",
        password_min_length: "Password must be at least 8 characters long",
        confirm_password_label: "Confirm Password",
        confirm_password_placeholder: "Confirm password",
        processing: "Processing...",
        set_password: "Set Password",
        login: "Login",
        passwords_mismatch: "Passwords do not match",
        status_check_failed: "Failed to check authentication status",
        failed: "Authentication failed",
    },
};

describe("validateAuthForm", () => {
    it("allows any password in login mode", () => {
        expect(validateAuthForm(false, "short", "")).toEqual({ valid: true });
        expect(validateAuthForm(false, "", "")).toEqual({ valid: true });
    });

    it("rejects mismatched passwords in setup mode", () => {
        const result = validateAuthForm(true, "password123", "password456");
        expect(result).toEqual({ valid: false, errorKey: "auth.passwords_mismatch" });
    });

    it("rejects short passwords in setup mode", () => {
        const result = validateAuthForm(true, "short", "short");
        expect(result).toEqual({ valid: false, errorKey: "auth.password_min_length" });
    });

    it("accepts valid matching passwords of required length in setup mode", () => {
        const result = validateAuthForm(true, "validpassword", "validpassword");
        expect(result).toEqual({ valid: true });
    });
});

describe("AuthPage.svelte", () => {
    let axiosMock;
    let routerMock;

    beforeEach(() => {
        registerTranslator(null);
        registerFallbackMessages(authI18n);

        axiosMock = {
            get: vi.fn().mockImplementation((url) => {
                if (url === API_AUTH_STATUS) {
                    return Promise.resolve({
                        data: {
                            auth_enabled: true,
                            authenticated: false,
                            password_set: true,
                        },
                    });
                }
                return Promise.resolve({ data: {} });
            }),
            post: vi.fn().mockResolvedValue({ data: { success: true } }),
        };
        window.api = axiosMock;

        routerMock = {
            push: vi.fn(),
        };

        Object.defineProperty(window, "location", {
            value: {
                reload: vi.fn(),
                hash: "",
            },
            writable: true,
        });
    });

    afterEach(() => {
        cleanup();
        delete window.api;
        vi.clearAllMocks();
    });

    it("renders login form when password is set", async () => {
        axiosMock.get.mockResolvedValueOnce({
            data: {
                auth_enabled: true,
                authenticated: false,
                password_set: true,
            },
        });

        render(AuthPage, { props: { router: routerMock } });

        expect(await screen.findByText("Authentication Required")).toBeTruthy();
        expect(screen.getByText("Please enter your password to continue")).toBeTruthy();
        expect(screen.getByRole("button", { name: "Login" })).toBeTruthy();
        expect(screen.getByLabelText("Password")).toBeTruthy();
        expect(screen.queryByLabelText("Confirm Password")).toBeNull();
    });

    it("renders setup form when password is not set", async () => {
        axiosMock.get.mockResolvedValueOnce({
            data: {
                auth_enabled: true,
                authenticated: false,
                password_set: false,
            },
        });

        render(AuthPage, { props: { router: routerMock } });

        expect(await screen.findByText("Initial Setup")).toBeTruthy();
        expect(screen.getByText("Set an admin password to secure your MeshChatX instance")).toBeTruthy();
        expect(screen.getByText("Password must be at least 8 characters long")).toBeTruthy();
        expect(screen.getByLabelText("Password")).toBeTruthy();
        expect(screen.getByLabelText("Confirm Password")).toBeTruthy();
        expect(screen.getByRole("button", { name: "Set Password" })).toBeTruthy();
    });

    it("displays auth page hint when provided in status", async () => {
        axiosMock.get.mockResolvedValueOnce({
            data: {
                auth_enabled: true,
                authenticated: false,
                password_set: true,
                auth_page_hint: "Default password is admin",
            },
        });

        render(AuthPage, { props: { router: routerMock } });

        expect(await screen.findByText("Default password is admin")).toBeTruthy();
    });

    it("redirects to hash root when auth is disabled and router is omitted", async () => {
        axiosMock.get.mockResolvedValueOnce({
            data: {
                auth_enabled: false,
                authenticated: false,
                password_set: false,
            },
        });

        render(AuthPage);

        await waitFor(() => {
            expect(window.location.hash).toBe("#/");
        });
    });

    it("redirects via router push when auth is disabled and router prop is provided", async () => {
        axiosMock.get.mockResolvedValueOnce({
            data: {
                auth_enabled: false,
                authenticated: false,
                password_set: false,
            },
        });

        render(AuthPage, { props: { router: routerMock } });

        await waitFor(() => {
            expect(routerMock.push).toHaveBeenCalledWith("/");
        });
    });

    it("redirects to hash root when already authenticated and router is omitted", async () => {
        axiosMock.get.mockResolvedValueOnce({
            data: {
                auth_enabled: true,
                authenticated: true,
                password_set: true,
            },
        });

        render(AuthPage);

        await waitFor(() => {
            expect(window.location.hash).toBe("#/");
        });
    });

    it("redirects via router push when already authenticated and router prop is provided", async () => {
        axiosMock.get.mockResolvedValueOnce({
            data: {
                auth_enabled: true,
                authenticated: true,
                password_set: true,
            },
        });

        render(AuthPage, { props: { router: routerMock } });

        await waitFor(() => {
            expect(routerMock.push).toHaveBeenCalledWith("/");
        });
    });

    it("validates password length in setup mode", async () => {
        axiosMock.get.mockResolvedValueOnce({
            data: {
                auth_enabled: true,
                authenticated: false,
                password_set: false,
            },
        });

        render(AuthPage, { props: { router: routerMock } });
        await screen.findByText("Initial Setup");

        const passwordInput = screen.getByLabelText("Password");
        const confirmPasswordInput = screen.getByLabelText("Confirm Password");

        await fireEvent.input(passwordInput, { target: { value: "short" } });
        await fireEvent.input(confirmPasswordInput, { target: { value: "short" } });

        const form = passwordInput.closest("form");
        await fireEvent.submit(form);

        await waitFor(() => {
            const matches = screen.getAllByText("Password must be at least 8 characters long");
            expect(matches.length).toBe(2);
        });
        expect(axiosMock.post).not.toHaveBeenCalled();
    });

    it("validates password match in setup mode and keeps button disabled", async () => {
        axiosMock.get.mockResolvedValueOnce({
            data: {
                auth_enabled: true,
                authenticated: false,
                password_set: false,
            },
        });

        render(AuthPage, { props: { router: routerMock } });
        await screen.findByText("Initial Setup");

        const passwordInput = screen.getByLabelText("Password");
        const confirmPasswordInput = screen.getByLabelText("Confirm Password");

        await fireEvent.input(passwordInput, { target: { value: "password123" } });
        await fireEvent.input(confirmPasswordInput, { target: { value: "password456" } });

        const submitButton = screen.getByRole("button", { name: "Set Password" });
        expect(submitButton.disabled).toBe(true);

        const form = passwordInput.closest("form");
        await fireEvent.submit(form);

        expect(await screen.findByText("Passwords do not match")).toBeTruthy();
        expect(axiosMock.post).not.toHaveBeenCalled();
    });

    it("submits setup form with valid password and reloads", async () => {
        axiosMock.get.mockResolvedValueOnce({
            data: {
                auth_enabled: true,
                authenticated: false,
                password_set: false,
            },
        });

        render(AuthPage, { props: { router: routerMock } });
        await screen.findByText("Initial Setup");

        const passwordInput = screen.getByLabelText("Password");
        const confirmPasswordInput = screen.getByLabelText("Confirm Password");

        await fireEvent.input(passwordInput, { target: { value: "password123" } });
        await fireEvent.input(confirmPasswordInput, { target: { value: "password123" } });

        const submitButton = screen.getByRole("button", { name: "Set Password" });
        expect(submitButton.disabled).toBe(false);

        await fireEvent.click(submitButton);

        await waitFor(() => {
            expect(axiosMock.post).toHaveBeenCalledWith(API_AUTH_SETUP, {
                password: "password123",
            });
        });
        expect(window.location.reload).toHaveBeenCalled();
    });

    it("submits login form with password and reloads", async () => {
        axiosMock.get.mockResolvedValueOnce({
            data: {
                auth_enabled: true,
                authenticated: false,
                password_set: true,
            },
        });

        render(AuthPage, { props: { router: routerMock } });
        await screen.findByText("Authentication Required");

        const passwordInput = screen.getByLabelText("Password");
        await fireEvent.input(passwordInput, { target: { value: "password123" } });

        const submitButton = screen.getByRole("button", { name: "Login" });
        await fireEvent.click(submitButton);

        await waitFor(() => {
            expect(axiosMock.post).toHaveBeenCalledWith(API_AUTH_LOGIN, {
                password: "password123",
            });
        });
        expect(window.location.reload).toHaveBeenCalled();
    });

    it("displays error message on login failure and clears inputs", async () => {
        axiosMock.get.mockResolvedValueOnce({
            data: {
                auth_enabled: true,
                authenticated: false,
                password_set: true,
            },
        });
        axiosMock.post.mockRejectedValueOnce({
            response: {
                data: {
                    error: "Invalid password",
                },
            },
        });

        render(AuthPage, { props: { router: routerMock } });
        await screen.findByText("Authentication Required");

        const passwordInput = screen.getByLabelText("Password");
        await fireEvent.input(passwordInput, { target: { value: "wrongpassword" } });

        const submitButton = screen.getByRole("button", { name: "Login" });
        await fireEvent.click(submitButton);

        expect(await screen.findByText("Invalid password")).toBeTruthy();
        expect(passwordInput.value).toBe("");
    });

    it("displays fallback error message on login failure without response error text", async () => {
        axiosMock.get.mockResolvedValueOnce({
            data: {
                auth_enabled: true,
                authenticated: false,
                password_set: true,
            },
        });
        axiosMock.post.mockRejectedValueOnce(new Error("Network failed"));

        render(AuthPage, { props: { router: routerMock } });
        await screen.findByText("Authentication Required");

        const passwordInput = screen.getByLabelText("Password");
        await fireEvent.input(passwordInput, { target: { value: "wrongpassword" } });

        const submitButton = screen.getByRole("button", { name: "Login" });
        await fireEvent.click(submitButton);

        expect(await screen.findByText("Authentication failed")).toBeTruthy();
    });

    it("displays error message on setup failure and clears inputs", async () => {
        axiosMock.get.mockResolvedValueOnce({
            data: {
                auth_enabled: true,
                authenticated: false,
                password_set: false,
            },
        });
        axiosMock.post.mockRejectedValueOnce({
            response: {
                data: {
                    error: "Setup failed",
                },
            },
        });

        render(AuthPage, { props: { router: routerMock } });
        await screen.findByText("Initial Setup");

        const passwordInput = screen.getByLabelText("Password");
        const confirmPasswordInput = screen.getByLabelText("Confirm Password");

        await fireEvent.input(passwordInput, { target: { value: "password123" } });
        await fireEvent.input(confirmPasswordInput, { target: { value: "password123" } });

        const submitButton = screen.getByRole("button", { name: "Set Password" });
        await fireEvent.click(submitButton);

        expect(await screen.findByText("Setup failed")).toBeTruthy();
        expect(passwordInput.value).toBe("");
        expect(confirmPasswordInput.value).toBe("");
    });

    it("handles status check network failure gracefully", async () => {
        axiosMock.get.mockRejectedValueOnce(new Error("Status check network error"));

        render(AuthPage, { props: { router: routerMock } });

        expect(await screen.findByText("Failed to check authentication status")).toBeTruthy();
    });
});
