# Welcome to MeshChatX

A fork of Reticulum Meshchat, with many more features, new UI/UX, better security and integrity.

## Backend overview

The main Python entrypoint is **`meshchatx/meshchat.py`**. Shared helpers live in **`meshchatx/src/path_utils.py`**, **`meshchatx/src/ssl_self_signed.py`**, and **`meshchatx/src/env_utils.py`**. Optional Reticulum (RNS) log verbosity uses **`--rns-log-level`** or **`MESHCHAT_RNS_LOG_LEVEL`** (the flag overrides the environment when both are set). Full architecture notes are in the repository **`docs/meshchatx.md`**.
