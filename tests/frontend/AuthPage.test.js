import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import AuthPage from "../../meshchatx/src/frontend/components/auth/AuthPage.vue";

describe("AuthPage.vue", () => {
    let axiosMock;
    let routerMock;

    beforeEach(() => {
        axiosMock = {
            get: vi.fn().mockResolvedValue({
                data: {
                    auth_enabled: true,
                    authenticated: false,
                    password_set: true,
                },
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
            },
            writable: true,
        });
    });

    afterEach(() => {
        delete window.api;
        vi.clearAllMocks();
    });

    const mountAuthPage = () => {
        return mount(AuthPage, {
            global: {
                mocks: {
                    $router: routerMock,
                },
            },
        });
    };

    it("renders login form when password is set", async () => {
        axiosMock.get.mockResolvedValueOnce({
            data: {
                auth_enabled: true,
                authenticated: false,
                password_set: true,
            },
        });

        const wrapper = mountAuthPage();
        await wrapper.vm.$nextTick();
        await wrapper.vm.checkAuthStatus();
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).toContain("Authentication Required");
        expect(wrapper.text()).toContain("Login");
        expect(wrapper.find('input[type="password"]').exists()).toBe(true);
    });

    it("renders setup form when password is not set", async () => {
        axiosMock.get.mockResolvedValueOnce({
            data: {
                auth_enabled: true,
                authenticated: false,
                password_set: false,
            },
        });

        const wrapper = mountAuthPage();
        await wrapper.vm.$nextTick();
        await new Promise((resolve) => setTimeout(resolve, 100));

        expect(wrapper.vm.isSetup).toBe(true);
        expect(wrapper.text()).toContain("Initial Setup");
        expect(wrapper.text()).toContain("Set Password");
        expect(wrapper.findAll('input[type="password"]').length).toBe(2);
    });

    it("redirects to home when auth is disabled", async () => {
        axiosMock.get.mockResolvedValueOnce({
            data: {
                auth_enabled: false,
                authenticated: false,
                password_set: false,
            },
        });

        const wrapper = mountAuthPage();
        await wrapper.vm.$nextTick();
        await wrapper.vm.checkAuthStatus();
        await wrapper.vm.$nextTick();

        expect(routerMock.push).toHaveBeenCalledWith("/");
    });

    it("redirects to home when already authenticated", async () => {
        axiosMock.get.mockResolvedValueOnce({
            data: {
                auth_enabled: true,
                authenticated: true,
                password_set: true,
            },
        });

        const wrapper = mountAuthPage();
        await wrapper.vm.$nextTick();
        await wrapper.vm.checkAuthStatus();
        await wrapper.vm.$nextTick();

        expect(routerMock.push).toHaveBeenCalledWith("/");
    });

    it("validates password length in setup mode", async () => {
        axiosMock.get.mockResolvedValueOnce({
            data: {
                auth_enabled: true,
                authenticated: false,
                password_set: false,
            },
        });

        const wrapper = mountAuthPage();
        await wrapper.vm.$nextTick();
        await new Promise((resolve) => setTimeout(resolve, 100));

        wrapper.vm.password = "short";
        wrapper.vm.confirmPassword = "short";
        await wrapper.vm.$nextTick();
        await wrapper.vm.handleSubmit();
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.error).toContain("at least 8 characters");
        expect(axiosMock.post).not.toHaveBeenCalled();
    });

    it("validates password match in setup mode", async () => {
        axiosMock.get.mockResolvedValueOnce({
            data: {
                auth_enabled: true,
                authenticated: false,
                password_set: false,
            },
        });

        const wrapper = mountAuthPage();
        await wrapper.vm.$nextTick();
        await new Promise((resolve) => setTimeout(resolve, 100));

        wrapper.vm.password = "password123";
        wrapper.vm.confirmPassword = "password456";
        await wrapper.vm.$nextTick();
        await wrapper.vm.handleSubmit();
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.error).toContain("do not match");
        expect(axiosMock.post).not.toHaveBeenCalled();
    });

    it("submits setup form with valid password", async () => {
        axiosMock.get.mockResolvedValueOnce({
            data: {
                auth_enabled: true,
                authenticated: false,
                password_set: false,
            },
        });

        const wrapper = mountAuthPage();
        await wrapper.vm.$nextTick();
        await new Promise((resolve) => setTimeout(resolve, 100));

        wrapper.vm.password = "password123";
        wrapper.vm.confirmPassword = "password123";
        await wrapper.vm.$nextTick();
        await wrapper.vm.handleSubmit();
        await wrapper.vm.$nextTick();
        await new Promise((resolve) => setTimeout(resolve, 100));

        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/auth/setup", {
            password: "password123",
        });
    });

    it("submits login form with password", async () => {
        axiosMock.get.mockResolvedValueOnce({
            data: {
                auth_enabled: true,
                authenticated: false,
                password_set: true,
            },
        });

        const wrapper = mountAuthPage();
        await wrapper.vm.$nextTick();
        await wrapper.vm.checkAuthStatus();
        await wrapper.vm.$nextTick();

        wrapper.vm.password = "password123";
        await wrapper.vm.handleSubmit();
        await wrapper.vm.$nextTick();

        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/auth/login", {
            password: "password123",
        });
    });

    it("reloads page after successful login", async () => {
        axiosMock.get.mockResolvedValueOnce({
            data: {
                auth_enabled: true,
                authenticated: false,
                password_set: true,
            },
        });

        const wrapper = mountAuthPage();
        await wrapper.vm.$nextTick();
        await wrapper.vm.checkAuthStatus();
        await wrapper.vm.$nextTick();

        wrapper.vm.password = "password123";
        await wrapper.vm.handleSubmit();
        await wrapper.vm.$nextTick();

        expect(window.location.reload).toHaveBeenCalled();
    });

    it("displays error message on login failure", async () => {
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

        const wrapper = mountAuthPage();
        await wrapper.vm.$nextTick();
        await wrapper.vm.checkAuthStatus();
        await wrapper.vm.$nextTick();

        wrapper.vm.password = "wrongpassword";
        await wrapper.vm.handleSubmit();
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.error).toBe("Invalid password");
        expect(wrapper.vm.isLoading).toBe(false);
    });

    it("displays error message on setup failure", async () => {
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

        const wrapper = mountAuthPage();
        await wrapper.vm.$nextTick();
        await wrapper.vm.checkAuthStatus();
        await wrapper.vm.$nextTick();

        wrapper.vm.password = "password123";
        wrapper.vm.confirmPassword = "password123";
        await wrapper.vm.handleSubmit();
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.error).toBe("Setup failed");
        expect(wrapper.vm.isLoading).toBe(false);
    });

    it("disables submit button when loading", async () => {
        axiosMock.get.mockResolvedValueOnce({
            data: {
                auth_enabled: true,
                authenticated: false,
                password_set: true,
            },
        });

        const wrapper = mountAuthPage();
        await wrapper.vm.$nextTick();
        await wrapper.vm.checkAuthStatus();
        await wrapper.vm.$nextTick();

        wrapper.vm.isLoading = true;
        await wrapper.vm.$nextTick();

        const submitButton = wrapper.find('button[type="submit"]');
        expect(submitButton.attributes("disabled")).toBeDefined();
    });

    it("disables submit button when passwords do not match in setup mode", async () => {
        axiosMock.get.mockResolvedValueOnce({
            data: {
                auth_enabled: true,
                authenticated: false,
                password_set: false,
            },
        });

        const wrapper = mountAuthPage();
        await wrapper.vm.$nextTick();
        await new Promise((resolve) => setTimeout(resolve, 100));

        wrapper.vm.password = "password123";
        wrapper.vm.confirmPassword = "password456";
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();

        const submitButton = wrapper.find('button[type="submit"]');
        const disabledAttr = submitButton.attributes("disabled");
        const disabledProp = submitButton.element.disabled;
        expect(disabledAttr !== undefined || disabledProp === true).toBe(true);
    });

    it("handles network errors gracefully", async () => {
        axiosMock.get.mockRejectedValueOnce(new Error("Network error"));

        const wrapper = mountAuthPage();
        await wrapper.vm.$nextTick();
        await wrapper.vm.checkAuthStatus();
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.error).toContain("Failed to check");
    });
});
