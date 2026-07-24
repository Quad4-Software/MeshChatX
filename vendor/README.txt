Vendored third-party trees shipped inside the reticulum-meshchatx distribution.

lxmfy/
  Upstream: https://git.quad4.io/LXMFy/LXMFy
  Bundled revision: 483b6928ce2e3cdacd415be92d0f38ae13dca651
  Declared version (pyproject): see vendor/lxmfy/pyproject.toml
  Update: clone default branch, replace vendor/lxmfy (omit .git), align vendor/README
  commit above, run poetry lock / uv lock, regenerate THIRD_PARTY_NOTICES if needed.
  Note: MeshChatX keeps its Landlock ABI hardening in vendor/lxmfy/lxmfy/landlock_sandbox.py
  (and matching tests) when refreshing from upstream.

rns_filesync/
  Upstream: https://github.com/Quad4-Software/RNS-Filesync
  Bundled revision: 12161f3f47d4c7421990e5790aa3d41e08fd623a
  Declared version (pyproject): see vendor/rns_filesync/pyproject.toml
  Update: clone default branch, replace vendor/rns_filesync (omit .git), align vendor/README
  commit above, regenerate THIRD_PARTY_NOTICES if needed.

rns_over_http/
  Upstream: https://github.com/Quad4-Software/RNS-over-HTTP
  Bundled revision: 530aca499fb7442910f691629670f6f9f4b67221
  Declared version (pyproject): see vendor/rns_over_http/pyproject.toml
  Update: clone default branch, replace vendor/rns_over_http (omit .git), copy
  HTTPInterface.py and LICENSE into meshchatx/src/backend/data/interfaces/
  (as HTTPInterface.py and HTTPInterface.LICENSE), align vendor/README commit above,
  regenerate THIRD_PARTY_NOTICES if needed.
  Runtime: MeshChatX installs HTTPInterface.py into Reticulum interfacepath on startup.
