/**
 * Micron Parser JavaScript implementation
 *
 * micron-parser.js is based on MicronParser.py from NomadNet:
 * https://raw.githubusercontent.com/markqvist/NomadNet/refs/heads/master/nomadnet/ui/textui/MicronParser.py
 *
 * Documentation for the Micron markdown format can be found here:
 * https://raw.githubusercontent.com/markqvist/NomadNet/refs/heads/master/nomadnet/ui/textui/Guide.py
 */
 
class MicronParser {

    constructor(darkTheme = true, enableForceMonospace = true) {
        this.darkTheme = darkTheme;
        this.enableForceMonospace = enableForceMonospace;
        this.DEFAULT_FG_DARK = "ddd";
        this.DEFAULT_FG_LIGHT = "222";
        this.DEFAULT_BG = "default";

        if (this.enableForceMonospace) {
            this.injectMonospaceStyles();
        }

        try {
            if (typeof DOMPurify === 'undefined') {
                console.warn('DOMPurify is not installed. Include it above micron-parser.js or run npm install dompurify');
            }
        } catch (error) {
            console.warn('DOMPurify is not installed. Include it above micron-parser.js or run npm install dompurify');
        }

        this.STYLES_DARK = {
            "plain": {fg: this.DEFAULT_FG_DARK, bg: this.DEFAULT_BG, bold: false, underline: false, italic: false},
            "heading1": {fg: "222", bg: "bbb", bold: false, underline: false, italic: false},
            "heading2": {fg: "111", bg: "999", bold: false, underline: false, italic: false},
            "heading3": {fg: "000", bg: "777", bold: false, underline: false, italic: false}
        };

        this.STYLES_LIGHT = {
            "plain": {fg: this.DEFAULT_FG_LIGHT, bg: this.DEFAULT_BG, bold: false, underline: false, italic: false},
            "heading1": {fg: "000", bg: "777", bold: false, underline: false, italic: false},
            "heading2": {fg: "111", bg: "aaa", bold: false, underline: false, italic: false},
            "heading3": {fg: "222", bg: "ccc", bold: false, underline: false, italic: false}
        };

        this.SELECTED_STYLES = this.darkTheme ? this.STYLES_DARK : this.STYLES_LIGHT;

    }

    injectMonospaceStyles() {
        if (document.getElementById('micron-monospace-styles')) {
            return;
        }

        const styleEl = document.createElement('style');
        styleEl.id = 'micron-monospace-styles';

        styleEl.textContent = `
            .Mu-nl {
                cursor: pointer;
            }
            .Mu-mnt {
                display: inline-block;
                width: 0.6em;
                text-align: center;
                white-space: pre;
                text-decoration: inherit;
            }
            .Mu-mws {
                text-decoration: inherit;
                display: inline-block;
            }
        `;
        document.head.appendChild(styleEl);
    }

    static formatNomadnetworkUrl(url) {
        return `nomadnetwork://${url}`;
    }


    parseHeaderTags(markup) {
        let pageFg = null;
        let pageBg = null;

        const lines = markup.split("\n");

        for (let line of lines) {
            const trimmedLine = line.trim();

            if (trimmedLine.length === 0) {
                continue;
            }

            if (!trimmedLine.startsWith("#!")) {
                break;
            }

            if (trimmedLine.startsWith("#!fg=")) {
                let color = trimmedLine.substring(5).trim();
                if (color.length === 3 || color.length === 6) {
                    pageFg = color;
                }
            }

            if (trimmedLine.startsWith("#!bg=")) {
                let color = trimmedLine.substring(5).trim();
                if (color.length === 3 || color.length === 6) {
                    pageBg = color;
                }
            }
        }

        return { fg: pageFg, bg: pageBg };
    }

    convertMicronToHtml(markup) {
        let html = "";

        // parse header tags for page-level color defaults
        const headerColors = this.parseHeaderTags(markup);

        const plainStyle = this.SELECTED_STYLES?.plain || {fg: this.DEFAULT_FG_DARK, bg: this.DEFAULT_BG};
        const defaultFg = headerColors.fg || plainStyle.fg;
        const defaultBg = headerColors.bg || this.DEFAULT_BG;

        let state = {
            literal: false,
            depth: 0,
            fg_color: defaultFg,
            bg_color: defaultBg,
            formatting: {
                bold: false,
                underline: false,
                italic: false,
                strikethrough: false
            },
            default_align: "left",
            align: "left",
            default_fg: defaultFg,
            default_bg: defaultBg,
            radio_groups: {}
        };

        const lines = markup.split("\n");

        for (let line of lines) {
            const lineOutput = this.parseLine(line, state);
            if (lineOutput && lineOutput.length > 0) {
                for (let el of lineOutput) {
                    html += el.outerHTML;
                }
            } else if (lineOutput && lineOutput.length === 0) {
                // skip
            } else {
                html += "<br>";
            }
        }


       try {
        return DOMPurify.sanitize(html, { USE_PROFILES: { html: true } });
       } catch (error) {
            console.warn('DOMPurify is not installed. Include it above micron-parser.js or run npm install dompurify ', error);
            return `<p style="color: red;"> ⚠ DOMPurify is not installed. Include it above micron-parser.js or run npm install dompurify </p>`;
       }
    }

    convertMicronToFragment(markup) {
        // Create a fragment to hold all the Micron output
        const fragment = document.createDocumentFragment();

        const headerColors = this.parseHeaderTags(markup);

        const plainStyle = this.SELECTED_STYLES?.plain || {fg: this.DEFAULT_FG_DARK, bg: this.DEFAULT_BG};
        const defaultFg = headerColors.fg || plainStyle.fg;
        const defaultBg = headerColors.bg || this.DEFAULT_BG;

        let state = {
            literal: false,
            depth: 0,
            fg_color: defaultFg,
            bg_color: defaultBg,
            formatting: {
                bold: false,
                underline: false,
                italic: false,
                strikethrough: false
            },
            default_align: "left",
            align: "left",
            default_fg: defaultFg,
            default_bg: defaultBg,
            radio_groups: {}
        };

        const lines = markup.split("\n");

        for (let line of lines) {
            line = DOMPurify.sanitize(line, { USE_PROFILES: { html: true } });
            const lineOutput = this.parseLine(line, state);
            if (lineOutput && lineOutput.length > 0) {
                for (let el of lineOutput) {

                    fragment.appendChild(el);
                }
            } else if (lineOutput && lineOutput.length === 0) {
                // skip
            } else {
                fragment.appendChild(document.createElement("br"));
            }
        }

        return fragment;
    }

    parseLine(line, state) {
        if (line.length > 0) {
            // Check literals toggle
            if (line === "`=") {
                state.literal = !state.literal;
                return null;
            }


            if (!state.literal) {
                // Comments, and header tags s
                if (line[0] === "#") {
                    return [];
                }

                // Reset section depth
                if (line[0] === "<") {
                    state.depth = 0;
                    return this.parseLine(line.slice(1), state);
                }

                // Section headings
                if (line[0] === ">") {
                    let i = 0;
                    while (i < line.length && line[i] === ">") {
                        i++;
                    }
                    state.depth = i;
                    let headingLine = line.slice(i);

                    if (headingLine.length > 0) {
                        // apply heading style if it exists
                        let style = null;
                        let wanted_style = "heading" + i;
                        const defaultPlain = {fg: this.darkTheme ? this.DEFAULT_FG_DARK : this.DEFAULT_FG_LIGHT, bg: this.DEFAULT_BG, bold: false, underline: false, italic: false};
                        if (this.SELECTED_STYLES?.[wanted_style]) {
                            style = this.SELECTED_STYLES[wanted_style];
                        } else {
                            style = this.SELECTED_STYLES?.plain || defaultPlain;
                        }

                        const latched_style = this.stateToStyle(state);
                        this.styleToState(style, state);

                        let outputParts = this.makeOutput(state, headingLine);
                        this.styleToState(latched_style, state);

                        // make outputParts full container width
                        if (outputParts && outputParts.length > 0) {
                            const outerDiv = document.createElement("div");
                            outerDiv.style.display = "inline-block";
                            outerDiv.style.width = "100%";
                            this.applyStyleToElement(outerDiv, style);

                            const innerDiv = document.createElement("div");
                            this.applySectionIndent(innerDiv, state);

                            this.appendOutput(innerDiv, outputParts, state);
                            outerDiv.appendChild(innerDiv);

                            const br = document.createElement("br");
                            return [outerDiv, br]
                        }
                        // wrap in a heading container
                        if (outputParts && outputParts.length > 0) {
                            const div = document.createElement("div");
                            this.applyAlignment(div, state);
                            this.applySectionIndent(div, state);
                            // merge text nodes
                            this.appendOutput(div, outputParts, state);
                            return [div];
                        } else {
                            return null;
                        }
                    } else {
                        return null;
                    }
                }

                // horizontal dividers
                if (line[0] === "-") {
                    // if the line is  just "-", do a normal <hr>
                    if (line.length === 1) {
                        const hr = document.createElement("hr");
                        hr.style.all = "revert";
                        hr.style.borderColor = this.colorToCss(state.fg_color);
                        hr.style.margin = "0.5em 0.5em 0.5em 0.5em";
                        hr.style.boxShadow = "0 0 0 0.5em " + this.colorToCss(state.bg_color);
                        this.applySectionIndent(hr, state);
                        return [hr];
                    } else {
                        // if second char given
                        const dividerChar = line[1];  // use the following character for creating the divider
                        const repeated = dividerChar.repeat(250);

                        const div = document.createElement("div");
                        div.style.whiteSpace = "pre";   // needs to not wrap and ignore container formatting
                        div.textContent = repeated;
                        div.style.width = "100%";
                        div.style.whiteSpace = "nowrap";
                        div.style.overflow = "hidden";
                        div.style.color = this.colorToCss(state.fg_color);
                        div.style.backgroundColor = this.colorToCss(state.bg_color);
                        this.applySectionIndent(div, state);

                        return [div];
                    }
                }

            }

            let outputParts = this.makeOutput(state, line);
            // outputParts can contain text (tuple) and special objects (fields/checkbox)
            if (outputParts) {

                // create parent div container to apply proper section indent
                let container = document.createElement("div");
                this.applyAlignment(container, state);
                this.applySectionIndent(container, state);

                this.appendOutput(container, outputParts, state);

                // if theres a background color, wrap with outer div
                if (state.bg_color !== this.DEFAULT_BG) {
                    const outerDiv = document.createElement("div");
                    outerDiv.style.backgroundColor = this.colorToCss(state.bg_color);
                    outerDiv.style.width = "100%";
                    outerDiv.style.display = "block";
                    outerDiv.appendChild(container);
                    return [outerDiv];
                }
                return [container];
            } else {
                // empty line but maintain background color if set
                const br = document.createElement("br");
                if (state.bg_color !== this.DEFAULT_BG) {
                    const outerDiv = document.createElement("div");
                    outerDiv.style.backgroundColor = this.colorToCss(state.bg_color);
                    outerDiv.style.width = "100%";
                    outerDiv.style.height = "1.2em";
                    outerDiv.style.display = "block";

                    const innerDiv = document.createElement("div");
                    this.applySectionIndent(innerDiv, state);
                    innerDiv.appendChild(br);
                    outerDiv.appendChild(innerDiv);

                    return [outerDiv];
                }
                return [br];
            }
        } else {
            // Empty line handling for just newline background color
            const br = document.createElement("br");
            if (state.bg_color !== this.DEFAULT_BG) {
                const outerDiv = document.createElement("div");
                outerDiv.style.backgroundColor = this.colorToCss(state.bg_color);
                outerDiv.style.width = "100%";
                outerDiv.style.height = "1.2em";
                outerDiv.style.display = "block";

                const innerDiv = document.createElement("div");
                this.applySectionIndent(innerDiv, state);
                innerDiv.appendChild(br);
                outerDiv.appendChild(innerDiv);

                return [outerDiv];
            }
            return [br];
        }
    }

    applyAlignment(el, state) {
        // use CSS text-align for alignment
        el.style.textAlign = state.align || "left";
    }

    applySectionIndent(el, state) {
        // indent by state.depth
        let indent = (state.depth - 1) * 2;
        if (indent > 0 ) {
            // Indent according to forceMonospace() character width
            el.style.marginLeft = (indent * 0.6) + "em";
        }
    }

    // convert current state to a style object
    stateToStyle(state) {
        return {
            fg: state.fg_color,
            bg: state.bg_color,
            bold: state.formatting.bold,
            underline: state.formatting.underline,
            italic: state.formatting.italic
        };
    }

    styleToState(style, state) {
        if (style.fg !== undefined && style.fg !== null) state.fg_color = style.fg;
        if (style.bg !== undefined && style.bg !== null) state.bg_color = style.bg;
        if (style.bold !== undefined && style.bold !== null) state.formatting.bold = style.bold;
        if (style.underline !== undefined && style.underline !== null) state.formatting.underline = style.underline;
        if (style.italic !== undefined && style.italic !== null) state.formatting.italic = style.italic;
    }

    appendOutput(container, parts, state) {

        let currentSpan = null;
        let currentStyle = null;

         const flushSpan = () => {
            if (currentSpan) {
                if (currentStyle && currentStyle.bg !== this.DEFAULT_BG) {
                    currentSpan.style.display = "inline-block";
                }
                container.appendChild(currentSpan);
                currentSpan = null;
                currentStyle = null;
            }
        };

        for (let p of parts) {
            if (typeof p === 'string') {
                let span = document.createElement("span");
                span.innerHTML = p;
                container.appendChild(span);
            } else if (Array.isArray(p) && p.length === 2) {
                // tuple: [styleSpec, text]
                let [styleSpec, text] = p;
                // if different style, flush currentSpan
                if (!this.stylesEqual(styleSpec, currentStyle)) {
                    flushSpan();
                    currentSpan = document.createElement("span");
                    this.applyStyleToElement(currentSpan, styleSpec);
                    currentStyle = styleSpec;
                }
                currentSpan.innerHTML += text;
            } else if (p && typeof p === 'object') {
                // field, checkbox, radio, link
                flushSpan();
                if (p.type === "field") {
                    let input = document.createElement("input");
                    input.type = p.masked ? "password" : "text";
                    input.name = p.name;
                    input.setAttribute('value', p.data);
                    if (p.width) {
                        input.size = p.width;
                    }
                    this.applyStyleToElement(input, this.styleFromState(p.style));
                    container.appendChild(input);
                } else if (p.type === "checkbox") {
                    let label = document.createElement("label");
                    let cb = document.createElement("input");
                    cb.type = "checkbox";
                    cb.name = p.name;
                    cb.value = p.value;
                    if (p.prechecked) cb.setAttribute('checked', true);
                    label.appendChild(cb);
                    label.appendChild(document.createTextNode(" " + p.label));
                    this.applyStyleToElement(label, this.styleFromState(p.style));
                    container.appendChild(label);
                } else if (p.type === "radio") {
                    let label = document.createElement("label");
                    let rb = document.createElement("input");
                    rb.type = "radio";
                    rb.name = p.name;
                    rb.value = p.value;
                    if (p.prechecked) rb.setAttribute('checked', true);
                    label.appendChild(rb);
                    label.appendChild(document.createTextNode(" " + p.label));
                    this.applyStyleToElement(label, this.styleFromState(p.style));
                    container.appendChild(label);
                } else if (p.type === "link") {

                    let directURL = p.url.replace('nomadnetwork://', '').replace('lxmf://', '');
                    // use p.url as is for the href
                    const formattedUrl = p.url;

                    let a = document.createElement("a");
                    a.href = formattedUrl;
                    a.title = formattedUrl;

                    let fieldsToSubmit = [];
                    let requestVars = {};
                    let foundAll = false;

                    if (p.fields && p.fields.length > 0) {
                        for (const f of p.fields) {
                            if (f === '*') {
                                // submit all fields
                                foundAll = true;
                            } else if (f.includes('=')) {
                                // this is a request variable (key=value)
                                const [k, v] = f.split('=');
                                requestVars[k] = v;
                            } else {
                                // this is a field name to submit
                                fieldsToSubmit.push(f);
                            }
                        }

                        let fieldStr = '';
                        if (foundAll) {
                            // if '*' was found, submit all fields
                            fieldStr = '*';
                        } else {
                            fieldStr = fieldsToSubmit.join('|');
                        }

                        // append request variables directly to the directURL as query parameters
                        const varEntries = Object.entries(requestVars);
                        if (varEntries.length > 0) {
                            const queryString = varEntries.map(([k, v]) => `${k}=${v}`).join('|');

                            directURL += directURL.includes('`') ? `|${queryString}` : `\`${queryString}`;
                        }

                        a.setAttribute("data-destination", `${directURL}`);
                        a.setAttribute("data-fields", `${fieldStr}`);
                    } else {
                        // no fields or request variables, just handle the direct URL
                        a.setAttribute("data-destination", `${directURL}`);
                    }
                    a.classList.add('Mu-nl');
                    a.setAttribute('data-action', "openNode");
                    a.innerHTML = p.label;
                    this.applyStyleToElement(a, this.styleFromState(p.style));
                    container.appendChild(a);
                }

            }
        }

        flushSpan();
    }

    stylesEqual(s1, s2) {
        if (!s1 && !s2) return true;
        if (!s1 || !s2) return false;
        return (s1.fg === s2.fg && s1.bg === s2.bg && s1.bold === s2.bold && s1.underline === s2.underline && s1.italic === s2.italic);
    }

    styleFromState(stateStyle) {
        // stateStyle is a name of a style or a style object
        // in this code, p.style is actually a style name. j,ust return that
        return stateStyle;
    }

applyStyleToElement(el, style) {
        if (!style) return;
        // convert style fg/bg to colors
        let fgColor = this.colorToCss(style.fg);
        let bgColor = this.colorToCss(style.bg);

        if (fgColor && fgColor !== "default") {
            el.style.color = fgColor;
        }
        if (bgColor && bgColor !== "default") {
            el.style.backgroundColor = bgColor;
            el.style.display = "inline-block";
        }

        if (style.bold) {
            el.style.fontWeight = "bold";
        }
        if (style.underline) {
            el.style.textDecoration = (el.style.textDecoration ? el.style.textDecoration + " underline" : "underline");
        }
        if (style.italic) {
            el.style.fontStyle = "italic";
        }
    }

    colorToCss(c) {
        if (!c || c === "default") return null;
        // if 3 hex chars (like '222') => expand to #222
        if (c.length === 3 && /^[0-9a-fA-F]{3}$/.test(c)) {
            return "#" + c;
        }
        // If 6 hex chars
        if (c.length === 6 && /^[0-9a-fA-F]{6}$/.test(c)) {
            return "#" + c;
        }
        // If grayscale 'gxx'
        if (c.length === 3 && c[0] === 'g') {
            // treat xx as a number and map to gray
            let val = parseInt(c.slice(1), 10);
            if (isNaN(val)) val = 50;
            // map 0-99 scale to a gray hex
            let h = Math.floor(val * 2.55).toString(16).padStart(2, '0');
            return "#" + h + h + h;
        }

        // fallback: just return a known CSS color or tailwind class if not known
        return null;
    }

    makeOutput(state, line) {
        if (state.literal) {
            // literal mode: output as is, except if `= line
            if (line === "\\`=") {
                line = "`=";
            }
            if(this.enableForceMonospace) {
                return [[this.stateToStyle(state), this.splitAtSpaces(line)]];
            } else {
                return [[this.stateToStyle(state), line]];
            }
        }

        let output = [];
        let part = "";
        let mode = "text";
        let escape = false;
        let skip = 0;

        const flushPart = () => {
            if (part.length > 0) {
                if(this.enableForceMonospace) {
                    output.push([this.stateToStyle(state), this.splitAtSpaces(part)]);
                } else {
                    output.push([this.stateToStyle(state), part]);
                }
                part = "";
            }
        };

        let i = 0;
        while (i < line.length) {
            let c = line[i];

            if (skip > 0) {
                skip--;
                i++;
                continue;
            }

            if (mode === "formatting") {
                switch (c) {
                    case '_':
                        state.formatting.underline = !state.formatting.underline;
                        break;
                    case '!':
                        state.formatting.bold = !state.formatting.bold;
                        break;
                    case '*':
                        state.formatting.italic = !state.formatting.italic;
                        break;

                    case 'F':
                        // next 3 chars => fg color
                        if (line.length >= i + 4) {
                            let color = line.substr(i + 1, 3);
                            state.fg_color = color;
                            skip = 3;
                        }
                        break;
                    case 'f':
                        // reset fg to page default
                        state.fg_color = state.default_fg;
                        break;
                    case 'B':
                        // next 3 chars => bg color
                        if (line.length >= i + 4) {
                            let color = line.substr(i + 1, 3);
                            state.bg_color = color;
                            skip = 3;
                            flushPart(); // flush current part when background color changes
                        }
                        break;
                     case 'b':
                        // reset bg to page default
                        state.bg_color = state.default_bg;
                        flushPart(); // flush to allow for ` tags on same line
                        break;
                    case '`':
                        state.formatting.bold = false;
                        state.formatting.underline = false;
                        state.formatting.italic = false;
                        state.fg_color = state.default_fg;
                        state.bg_color = state.default_bg;
                        state.align = state.default_align;
                        mode = "text";
                        break;
                    case 'c':
                        state.align = 'center';
                        break;
                    case 'l':
                        state.align = 'left';
                        break;
                    case 'r':
                        state.align = 'right';
                        break;
                    case 'a':
                        state.align = state.default_align;
                        break;

                    case '<':
                        // if there's already text, flush it
                        flushPart();
                        let fieldData = this.parseField(line, i, state);
                        if (fieldData) {
                            output.push(fieldData.obj);
                            i += fieldData.skip;
                            // do not i++ here or we'll skip an extra char
                            continue;
                        }
                        break;

                    case '[':
                        // flush current text first
                        flushPart();
                        let linkData = this.parseLink(line, i, state);
                        if (linkData) {
                            output.push(linkData.obj);
                            i += linkData.skip;
                            continue;
                        }
                        break;

                    default:
                        // unknown formatting char, ignore
                        break;
                }
                mode = "text";
                i++;
                continue;

            } else {
                // mode === "text"
                if (escape) {
                    part += c;
                    escape = false;
                } else if (c === '\\') {
                    escape = true;
                } else if (c === '`') {
                    if (i + 1 < line.length && line[i + 1] === '`') {
                        flushPart();
                        state.formatting.bold = false;
                        state.formatting.underline = false;
                        state.formatting.italic = false;
                        state.fg_color = state.default_fg;
                        state.bg_color = state.default_bg;
                        state.align = state.default_align;
                        i += 2;
                        continue;
                    } else {
                        flushPart();
                        mode = "formatting";
                        i++;
                        continue;
                    }
                } else {
                    // normal text char
                    part += c;
                }
                i++;
            }
        }
        // end of line
        if (part.length > 0) {
            if(this.enableForceMonospace) {
                output.push([this.stateToStyle(state), this.splitAtSpaces(part)]);
            } else {
                output.push([this.stateToStyle(state), part]);
            }
        }

        return output;
    }

    parseField(line, startIndex, state) {
        let field_start = startIndex + 1;
        let backtick_pos = line.indexOf('`', field_start);
        if (backtick_pos === -1) return null;

        let field_content = line.substring(field_start, backtick_pos);
        let field_masked = false;
        let field_width = 24;
        let field_type = "field";
        let field_name = field_content;
        let field_value = "";
        let field_prechecked = false;

        if (field_content.includes('|')) {
            let f_components = field_content.split('|');
            let field_flags = f_components[0];
            field_name = f_components[1];

            if (field_flags.includes('^')) {
                field_type = "radio";
                field_flags = field_flags.replace('^', '');
            } else if (field_flags.includes('?')) {
                field_type = "checkbox";
                field_flags = field_flags.replace('?', '');
            } else if (field_flags.includes('!')) {
                field_masked = true;
                field_flags = field_flags.replace('!', '');
            }

            if (field_flags.length > 0) {
                let w = parseInt(field_flags, 10);
                if (!isNaN(w)) {
                    field_width = Math.min(w, 256);
                }
            }

            if (f_components.length > 2) {
                field_value = f_components[2];
            }

            if (f_components.length > 3) {
                if (f_components[3] === '*') {
                    field_prechecked = true;
                }
            }
        }

        let field_end = line.indexOf('>', backtick_pos);
        if (field_end === -1) return null;

        let field_data = line.substring(backtick_pos + 1, field_end);
        let style = this.stateToStyle(state);

        let obj = null;
        if (field_type === "checkbox" || field_type === "radio") {
            obj = {
                type: field_type,
                name: field_name,
                value: field_value || field_data,
                label: field_data,
                prechecked: field_prechecked,
                style: style
            };
        } else {
            obj = {
                type: "field",
                name: field_name,
                width: field_width,
                masked: field_masked,
                data: field_data,
                style: style
            };
        }

        let skip = (field_end - startIndex);
        return {obj: obj, skip: skip};
    }

    parseLink(line, startIndex, state) {
        let endpos = line.indexOf(']', startIndex);
        if (endpos === -1) return null;

        let link_data = line.substring(startIndex + 1, endpos);
        let link_components = link_data.split('`');
        let link_label = "";
        let link_url = "";
        let link_fields = "";

        if (link_components.length === 1) {
            link_label = "";
            link_url = link_data;
        } else if (link_components.length === 2) {
            link_label = link_components[0];
            link_url = link_components[1];
        } else if (link_components.length === 3) {
            link_label = link_components[0];
            link_url = link_components[1];
            link_fields = link_components[2];
        }

        if (link_url.length === 0) {
            return null;
        }

        if (link_label === "") {
            link_label = link_url;
        }

        // format the URL
        link_url = MicronParser.formatNomadnetworkUrl(link_url);

        // Apply forceMonospace
        if(this.enableForceMonospace) {
            link_label = this.splitAtSpaces(link_label);
        }

        let style = this.stateToStyle(state);
        let obj = {
            type: "link",
            url: link_url,
            label: link_label,
            fields: (link_fields ? link_fields.split("|") : []),
            style: style
        };

        let skip = (endpos - startIndex);
        return {obj: obj, skip: skip};
    }

    splitAtSpaces(line) {
        let out = "";
        let wordArr = line.split(/(?<= )/g);
        for (let i = 0; i < wordArr.length; i++) {
            out += "<span class='Mu-mws'>" + this.forceMonospace(wordArr[i]) + "</span>";
        }
        return out;
    }

    forceMonospace(line) {
        let out = "";
        // Properly split compount emoji, source: https://stackoverflow.com/a/71619350
        let charArr = [...new Intl.Segmenter().segment(line)].map(x => x.segment);
        for (let char of charArr) {
            out += "<span class='Mu-mnt'>" + char + "</span>";
        }
        return out;
    }
}

export default MicronParser;
