// SPDX-License-Identifier: 0BSD

/**
 * Tab identifiers supported by the Call view
 */
export const CALL_TAB_IDS = [
    "phone",
    "phonebook",
    "voicemail",
    "contacts",
    "ringtone",
    "recordings",
] as const;

/**
 * Call status numeric codes from Reticulum LXST
 */
export const CALL_STATUS_BUSY = 0;
export const CALL_STATUS_REJECTED = 1;
export const CALL_STATUS_CALLING = 2;
export const CALL_STATUS_AVAILABLE = 3;
export const CALL_STATUS_RINGING = 4;
export const CALL_STATUS_ESTABLISHING_LINK = 5;
export const CALL_STATUS_CONNECTED = 6;

/**
 * Polling and timer intervals in milliseconds
 */
export const STATUS_POLL_INTERVAL_MS = 1000;
export const STATUS_POLL_LIVE_TRANSPORT_INTERVAL_MS = 15000;
export const HISTORY_POLL_INTERVAL_MS = 10000;
export const ELAPSED_TIME_INTERVAL_MS = 1000;
export const CALL_ENDED_RESET_TIMEOUT_MS = 5000;
export const SEARCH_DEBOUNCE_MS = 500;
export const SEARCH_DEBOUNCE_SHORT_MS = 300;
export const CALL_INPUT_BLUR_DELAY_MS = 200;
export const MIC_MUTE_DEBOUNCE_MS = 500;
export const SPEAKER_MUTE_DEBOUNCE_MS = 500;
export const RECONNECT_ATTACH_DELAY_MS = 150;

/**
 * Local storage keys
 */
export const CALL_ACTIVE_TAB_STORAGE_KEY = "meshchatx_call_active_tab";
export const CALL_SELECTED_INPUT_DEVICE_KEY = "meshchatx_call_selected_audio_input";
export const CALL_SELECTED_OUTPUT_DEVICE_KEY = "meshchatx_call_selected_audio_output";

/**
 * Audio WebSocket and asset paths
 */
export const TELEPHONE_AUDIO_WS_PATH = "/ws/telephone/audio";
export const TELEPHONE_PCM_CAPTURE_WORKLET_URL = "/assets/js/telephone-pcm-capture.worklet.js";
export const DEFAULT_AUDIO_INPUT_DEVICE_ID = "__meshchat_default_in__";
export const DEFAULT_AUDIO_OUTPUT_DEVICE_ID = "__meshchat_default_out__";
export const DEFAULT_AUDIO_INPUT_DEVICE_LABEL = "Default";
export const DEFAULT_AUDIO_OUTPUT_DEVICE_LABEL = "Default";
export const DEFAULT_AUDIO_SAMPLE_RATE = 48000;
export const DEFAULT_AUDIO_FRAME_MS = 60;
export const SCRIPT_PROCESSOR_BUFFER_SIZE = 4096;
export const INT16_SAMPLE_MAX = 32767;
export const WEB_AUDIO_MIC_TOAST_KEY = "call-web-audio-mic";

/**
 * Noise filter parameters
 */
export const HIGHPASS_FILTER_FREQ = 120;
export const HIGHPASS_FILTER_Q = 0.707;
export const COMPRESSOR_THRESHOLD = -45;
export const COMPRESSOR_KNEE = 30;
export const COMPRESSOR_RATIO = 3;
export const COMPRESSOR_ATTACK = 0.003;
export const COMPRESSOR_RELEASE = 0.25;

/**
 * Visualizer layout and decay constants
 */
export const VISUALIZER_MIN_WIDTH = 160;
export const VISUALIZER_MIN_HEIGHT = 56;
export const VISUALIZER_DEFAULT_WIDTH = 256;
export const VISUALIZER_DEFAULT_HEIGHT = 72;
export const VISUALIZER_PHASE_STEP = 0.065;
export const VISUALIZER_DECAY_TARGET = 0.985;
export const VISUALIZER_DECAY_LEVEL = 0.965;
export const VISUALIZER_STEP = 4;
export const VISUALIZER_LOCAL_COLOR = "rgba(34, 211, 238, 0.95)";
export const VISUALIZER_REMOTE_COLOR = "rgba(167, 139, 250, 0.95)";
export const VISUALIZER_BG_COLOR = "rgba(10, 12, 18, 0.9)";
export const VISUALIZER_CENTER_LINE_COLOR = "rgba(156, 163, 175, 0.22)";

/**
 * Destination hash format and query bounds
 */
export const TRUNCATED_HASH_LENGTH = 8;
export const HASH_BYTES_PER_SIDE = 4;
export const MIN_HASH_HEX_LENGTH = 32;
export const MAX_HASH_HEX_LENGTH = 64;
export const DEFAULT_CALL_HISTORY_LIMIT = 10;
export const DEFAULT_DISCOVERY_LIMIT = 10;
export const DEFAULT_VOICEMAIL_LIMIT = 50;
export const DEFAULT_RECORDINGS_LIMIT = 10;
export const MAX_CALL_SUGGESTIONS = 8;
export const TELEPHONY_ASPECT = "lxst.telephony";

/**
 * Backend API endpoints
 */
export const CONFIG_API_ENDPOINT = "/api/v1/config";
export const BLOCKED_DESTINATIONS_API_ENDPOINT = "/api/v1/blocked-destinations";
export const ANNOUNCES_API_ENDPOINT = "/api/v1/announces";
export const TELEPHONE_STATUS_ENDPOINT = "/api/v1/telephone/status";
export const TELEPHONE_CALL_ENDPOINT = "/api/v1/telephone/call";
export const TELEPHONE_ANSWER_ENDPOINT = "/api/v1/telephone/answer";
export const TELEPHONE_HANGUP_ENDPOINT = "/api/v1/telephone/hangup";
export const TELEPHONE_SEND_TO_VOICEMAIL_ENDPOINT = "/api/v1/telephone/send-to-voicemail";
export const TELEPHONE_MUTE_TRANSMIT_ENDPOINT = "/api/v1/telephone/mute-transmit";
export const TELEPHONE_UNMUTE_TRANSMIT_ENDPOINT = "/api/v1/telephone/unmute-transmit";
export const TELEPHONE_MUTE_RECEIVE_ENDPOINT = "/api/v1/telephone/mute-receive";
export const TELEPHONE_UNMUTE_RECEIVE_ENDPOINT = "/api/v1/telephone/unmute-receive";
export const TELEPHONE_CALL_MODES_ENDPOINT = "/api/v1/telephone/call-modes";
export const TELEPHONE_SWITCH_CALL_MODE_ENDPOINT = "/api/v1/telephone/switch-call-mode";
export const TELEPHONE_PTT_ENDPOINT = "/api/v1/telephone/ptt";
export const TELEPHONE_HISTORY_ENDPOINT = "/api/v1/telephone/history";
export const TELEPHONE_MISSED_CALLS_MARK_VIEWED_ENDPOINT = "/api/v1/telephone/missed-calls/mark-viewed";
export const TELEPHONE_AUDIO_PROFILES_ENDPOINT = "/api/v1/telephone/audio-profiles";
export const TELEPHONE_SWITCH_AUDIO_PROFILE_ENDPOINT = "/api/v1/telephone/switch-audio-profile";
export const TELEPHONE_CODEC2_STATUS_ENDPOINT = "/api/v1/telephone/codec2/status";
export const TELEPHONE_VOICEMAIL_STATUS_ENDPOINT = "/api/v1/telephone/voicemail/status";
export const TELEPHONE_VOICEMAIL_RECORD_START_ENDPOINT = "/api/v1/telephone/voicemail/greeting/record/start";
export const TELEPHONE_VOICEMAIL_RECORD_STOP_ENDPOINT = "/api/v1/telephone/voicemail/greeting/record/stop";
export const TELEPHONE_VOICEMAILS_ENDPOINT = "/api/v1/telephone/voicemails";
export const TELEPHONE_VOICEMAIL_GENERATE_GREETING_ENDPOINT = "/api/v1/telephone/voicemail/generate-greeting";
export const TELEPHONE_VOICEMAIL_GREETING_UPLOAD_ENDPOINT = "/api/v1/telephone/voicemail/greeting/upload";
export const TELEPHONE_VOICEMAIL_GREETING_ENDPOINT = "/api/v1/telephone/voicemail/greeting";
export const TELEPHONE_VOICEMAIL_GREETING_AUDIO_ENDPOINT = "/api/v1/telephone/voicemail/greeting/audio";
export const TELEPHONE_RECORDINGS_ENDPOINT = "/api/v1/telephone/recordings";
export const TELEPHONE_RINGTONES_ENDPOINT = "/api/v1/telephone/ringtones";
export const TELEPHONE_RINGTONES_STATUS_ENDPOINT = "/api/v1/telephone/ringtones/status";
export const TELEPHONE_RINGTONES_UPLOAD_ENDPOINT = "/api/v1/telephone/ringtones/upload";
export const TELEPHONE_CONTACTS_ENDPOINT = "/api/v1/telephone/contacts";
