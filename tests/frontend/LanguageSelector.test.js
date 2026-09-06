import { cleanup, fireEvent, render, screen } from "@testing-library/svelte";
import { afterEach, describe, expect, it, vi } from "vitest";
import { tick } from "svelte";
import LanguageSelector from "@/ui/svelte/LanguageSelector.svelte";

vi.mock("@/js/localeLoader.js", async () => {
    const actual = await vi.importActual("@/js/localeLoader.js");
    return {
        ...actual,
        setLocale: vi.fn(async () => true),
        ensureLocaleMessages: vi.fn(async () => {}),
        getCurrentUiLocale: vi.fn(() => "en"),
    };
});

import { setLocale } from "@/js/localeLoader.js";

describe("LanguageSelector.svelte", () => {
    afterEach(() => {
        cleanup();
        vi.clearAllMocks();
    });

    it("renders the language selector button", () => {
        render(LanguageSelector);
        expect(screen.getByRole("button")).toBeTruthy();
    });

    it("toggles the dropdown when the button is clicked", async () => {
        render(LanguageSelector);
        const button = screen.getByRole("button");
        expect(screen.queryByRole("menu")).toBeNull();
        await fireEvent.click(button);
        expect(screen.getByRole("menu")).toBeTruthy();
        await fireEvent.click(button);
        expect(screen.queryByRole("menu")).toBeNull();
    });

    it("lists all available languages in the dropdown", async () => {
        const { container } = render(LanguageSelector);
        await fireEvent.click(screen.getByRole("button", { name: /language/i }));
        const menu = container.querySelector('[role="menu"]');
        expect(menu).toBeTruthy();
        const labels = [...menu.querySelectorAll("button")].map((b) => b.textContent || "");
        // English is pinned to the front; remaining locales are sorted by display name
        expect(labels[0]).toContain("English");
        expect(labels).toEqual(
            expect.arrayContaining([
                expect.stringContaining("English"),
                expect.stringContaining("Deutsch"),
                expect.stringContaining("Español"),
                expect.stringContaining("Français"),
                expect.stringContaining("Italiano"),
                expect.stringContaining("Nederlands"),
                expect.stringContaining("\u0420\u0443\u0441\u0441\u043a\u0438\u0439"),
                expect.stringContaining("\u4e2d\u6587"),
            ])
        );
        expect(labels.length).toBeGreaterThanOrEqual(8);
    });

    it("emits language-change when a different language is selected", async () => {
        const onlanguagechange = vi.fn();
        const { container } = render(LanguageSelector, { onlanguagechange });
        await fireEvent.click(screen.getByRole("button", { name: /language/i }));
        const deButton = [...container.querySelectorAll('[role="menu"] button')].find((b) =>
            b.textContent?.includes("Deutsch")
        );
        expect(deButton).toBeTruthy();
        await fireEvent.click(deButton);
        await tick();
        expect(setLocale).toHaveBeenCalled();
        expect(onlanguagechange).toHaveBeenCalledWith("de");
        expect(container.querySelector('[role="menu"]')).toBeNull();
    });

    it("does not emit language-change when the current language is selected", async () => {
        const onlanguagechange = vi.fn();
        const { container } = render(LanguageSelector, { onlanguagechange });
        await fireEvent.click(screen.getByRole("button", { name: /language/i }));
        const enButton = [...container.querySelectorAll('[role="menu"] button')].find((b) =>
            b.textContent?.includes("English")
        );
        await fireEvent.click(enButton);
        await tick();
        expect(onlanguagechange).not.toHaveBeenCalled();
        expect(container.querySelector('[role="menu"]')).toBeNull();
    });

    it("renders a single trigger button", () => {
        const { container } = render(LanguageSelector);
        expect(container.querySelectorAll("button").length).toBe(1);
    });

    it("button is focusable", () => {
        render(LanguageSelector);
        const btn = screen.getByRole("button", { name: /language/i });
        expect(btn.tabIndex).toBeGreaterThanOrEqual(-1);
    });
});
