export default class LinkUtils {
    /**
     * Detects and wraps NomadNet links in HTML.
     * Supports nomadnet://<hash>:/path and <hash>:/path
     */
    static renderNomadNetLinks(text) {
        if (!text) return "";

        // Hash is 32 hex chars. Path is optional.
        const hashPattern = "[a-fA-F0-9]{32}";
        const nomadnetRegex = new RegExp(`(?:nomadnet://)?(${hashPattern})(?::(/[\\w\\d./?%&=-]*))?`, "g");

        return text.replace(nomadnetRegex, (match, hash, path) => {
            const fullPath = path || "/page/index.mu";
            const url = `${hash}:${fullPath}`;
            return `<a href="#" class="nomadnet-link text-blue-600 dark:text-blue-400 hover:underline font-mono" data-nomadnet-url="${url}">${match}</a>`;
        });
    }

    /**
     * Basic URL detection for standard http/https links.
     */
    static renderStandardLinks(text) {
        if (!text) return "";

        // Simple regex for URLs
        const urlRegex = /(https?:\/\/[^\s<]+)/g;
        return text.replace(urlRegex, (url) => {
            return `<a href="${url}" target="_blank" rel="noopener noreferrer" class="text-blue-600 dark:text-blue-400 hover:underline">${url}</a>`;
        });
    }

    /**
     * Applies all link rendering.
     */
    static renderAllLinks(text) {
        text = this.renderStandardLinks(text);
        text = this.renderNomadNetLinks(text);
        return text;
    }
}
