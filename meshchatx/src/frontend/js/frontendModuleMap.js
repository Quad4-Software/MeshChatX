/**
 * Frontend module map: primary entry points, large feature surfaces, and shared layers.
 *
 * Entry: meshchatx/src/frontend/main.js
 *
 * Application shell: components/App.vue (routing, WebSocket shell, sidebar, global modals)
 *
 * Feature surfaces (orchestration-heavy .vue files):
 * - components/messages/ConversationViewer.vue
 * - components/settings/SettingsPage.vue
 * - components/call/CallPage.vue
 * - components/map/MapPage.vue
 *
 * Shared state and events:
 * - js/GlobalState.js, js/GlobalEmitter.js
 * - js/KeyboardShortcuts.js, js/WebSocketConnection.js
 *
 * Extracted domain helpers (non-UI):
 * - js/settings/settingsConfigService.js
 * - js/settings/settingsTransportService.js
 * - js/settings/settingsMaintenanceClient.js
 * - js/settings/settingsVisualiserPrefs.js
 * - components/messages/conversationMessageHelpers.js
 * - components/messages/conversationScroll.js
 */

export const FRONTEND_MODULE_MAP_VERSION = 1;
