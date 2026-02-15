export default class LinkUtils {
    /**
     * Detects and wraps Reticulum (NomadNet and LXMF) links in HTML.
     * Supports nomadnet://<hash>, nomadnet@<hash>, lxmf://<hash>, lxmf@<hash> and bare <hash>
     */
    static renderReticulumLinks(text) {
        if (!text) return "";

        // Hash is 32 hex chars. Path is optional (NomadNet only).
        const hashPattern = "[a-fA-F0-9]{32}";
        // Optional prefix (nomadnet://, nomadnet@, lxmf://, lxmf@), then hash, optional path.
        const reticulumRegex = new RegExp(
            `(nomadnet://|nomadnet@|lxmf://|lxmf@)?(${hashPattern})(?::(/[\\w\\d./?%&=-]*))?`,
            "g"
        );

        return text.replace(reticulumRegex, (match, prefix, hash, path) => {
            // Determine if it should be treated as a NomadNet link:
            // - Has nomadnet prefix
            // - OR has a path component (e.g. hash:/page)
            const isNomadNet =
                (prefix && (prefix.startsWith("nomadnet://") || prefix.startsWith("nomadnet@"))) || !!path;

            if (isNomadNet) {
                const fullPath = path || "/page/index.mu";
                const url = `${hash}:${fullPath}`;
                return `<a href="#" class="nomadnet-link text-blue-600 dark:text-blue-400 hover:underline font-mono" data-nomadnet-url="${url}">${match}</a>`;
            } else {
                // Treat as LXMF link
                return `<a href="#" class="lxmf-link text-blue-600 dark:text-blue-400 hover:underline font-mono" data-lxmf-address="${hash}">${match}</a>`;
            }
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
        text = this.renderReticulumLinks(text);
        return text;
    }
}
