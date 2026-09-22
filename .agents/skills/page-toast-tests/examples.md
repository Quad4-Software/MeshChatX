# Example Triggers

Use this skill when user requests resemble:

- "Create a new tools page for X."
- "Add a page and wire it into navigation."
- "Add toasts for save and error states."
- "Add tests for this new page flow."
- "Add frontend and backend coverage for this feature."

# Example Outcomes

Typical outputs from this skill:

- new page component in meshchatx/src/frontend/features/<id>/
- registerFeature route in features/<id>/index.ts (wired from registerAllFeatures.ts)
- navigation entry via navRegistry or toolsRegistry when needed
- locale keys in meshchatx/src/frontend/locales/*.json
- toast usage through meshchatx/src/frontend/js/ToastUtils.js
- frontend and backend test updates in tests/frontend/ and tests/backend/
