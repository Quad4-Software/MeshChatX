Vendored third-party trees shipped inside the reticulum-meshchatx distribution.

lxmfy/
  Upstream: https://git.quad4.io/LXMFy/LXMFy
  Bundled revision: d92cfe0e1ad07fbf6928cf2e02438fe9f0d14384
  Declared version (pyproject): see vendor/lxmfy/pyproject.toml
  Update: clone default branch, replace vendor/lxmfy (omit .git), align vendor/README
  commit above, run poetry lock / uv lock, regenerate THIRD_PARTY_NOTICES if needed.

rns_filesync/
  Upstream: https://github.com/Quad4-Software/RNS-Filesync
  Bundled revision: 12161f3f47d4c7421990e5790aa3d41e08fd623a
  Declared version (pyproject): see vendor/rns_filesync/pyproject.toml
  Update: clone default branch, replace vendor/rns_filesync (omit .git), align vendor/README
  commit above, regenerate THIRD_PARTY_NOTICES if needed.
