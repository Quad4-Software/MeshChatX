import { readFileSync } from "fs";
import { join } from "path";
import { describe, it, expect } from "vitest";

const src = readFileSync(
    join(
        process.cwd(),
        "meshchatx/src/frontend/features/call/components/CallVoicemailSettings.svelte",
    ),
    "utf8"
);

describe("CallVoicemailSettings eSpeak fallback", () => {
    it("shows a warning banner when eSpeak is missing", () => {
        expect(src).toContain("{#if !props.voicemailStatus?.has_espeak}");
        expect(src).toContain("You can still record a greeting or");
    });

    it("keeps the voicemail enable toggle usable without eSpeak", () => {
        // The enable toggle must not be disabled by has_espeak.
        const toggleBlock = src.match(
            /call\.enable_voicemail[\s\S]*?<button[\s\S]*?onclick=\{handleToggleVoicemailEnabled\}/
        );
        expect(toggleBlock).toBeTruthy();
        expect(toggleBlock[0]).not.toContain("has_espeak");
        expect(toggleBlock[0]).not.toContain("disabled=");
    });

    it("disables only the TTS generation path without eSpeak", () => {
        // Save & Generate is gated on eSpeak.
        const genButton = src.match(/<button[\s\S]*?onsaveandgenerate[\s\S]*?<\/button>/);
        expect(genButton).toBeTruthy();
        expect(genButton[0]).toContain("!props.voicemailStatus?.has_espeak");

        // TTS settings grid is visually disabled.
        expect(src).toContain("class:opacity-50={!props.voicemailStatus?.has_espeak}");
        expect(src).toContain("class:pointer-events-none={!props.voicemailStatus?.has_espeak}");
    });

    it("keeps audio upload and recording enabled without eSpeak", () => {
        const uploadButton = src.match(
            /<button[^>]*onclick=\{\(\) => greetingUploadInput\?\.click\(\)\}[^>]*>/
        );
        expect(uploadButton).toBeTruthy();
        expect(uploadButton[0]).not.toContain("has_espeak");
    });
});
