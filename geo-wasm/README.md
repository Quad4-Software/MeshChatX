# geo-wasm

Go packages for MeshChatX map coordinate formats, compiled to WebAssembly.

- mgrs copied from https://git.quad4.io/libraries/mgrs-go (UTM, MGRS, UPS)
- olc copied from https://git.quad4.io/libraries/olc-go (Plus Codes)
- internal/geoparse auto-detect parse/format helpers
- cmd/wasm browser bridge (`meshchatxGeo*`)

Official OLC CSV corpora under `olc/testdata/` are Apache-2.0. See NOTICE.

Build: `task build:geo-wasm`
Test: `task test:geo-wasm`
