# Offline Translation

MeshChatX uses the Bergamot Translator WebAssembly runtime for offline,
browser-side translation. No translation requests leave your device and no
language packs are bundled with MeshChatX releases.

## How it works

- The Bergamot WASM engine is shipped with MeshChatX so it is available offline.
- Language packs are separate archives you obtain and import yourself.
- Imported packs are stored under the MeshChatX storage directory in
  `translation-packs/` and served same-origin to the WASM worker.
- Translation happens locally in the page: conversation messages, Relay chat
  messages and the standalone Translator tool all use the same engine and pack
  set.

## Getting packs

The Translator page can fetch packs directly. Open **Download packs** to list
the available language pairs, then download a single pair or use
**Download all**. Downloads are verified against their published checksums
before install.

Pack downloads are outbound HTTPS requests, so they are blocked while privacy
mode is enabled. Translations themselves remain local and keep working with
privacy mode on.

You can also import pack archives you obtained elsewhere. A friend or
organisation can share ready pack archives over the mesh, or a dedicated
website or CDN can host them.

Packs are ordinary zip or tar archives containing a `model`, `lex` and `vocab`
file for a four-letter language pair such as `enes` (English to Spanish).

A pack archive can contain one of the following:

- A top-level `pack.json` plus a directory named with the pair code.
- A top-level `registry.json` describing multiple pair directories.
- A single directory named with the pair code, with files named like
  `model.<pair>.npz`, `lex.<pair>.s2t.bin` and `vocab.<pair>.spm`.

## Importing a pack

1. Open the **Tools > Translator** page.
2. Choose **Import pack** and select a `.zip` or `.tar` archive.
3. The pack is validated, extracted and listed under **Pack library**.

You can import as many packs as you like. The standalone translator and message
translation pick from all installed packs.

## Translating messages

Translation is opt-in and quiet:

- Right-click or long-press a message and choose **Translate message**.
- Pick a target language pair.
- The translated text appears inline. Tap **Show original** to switch back.
- The last target pair is remembered.
- If no pack is installed for the source/target pair, the UI explains the
  situation and links to the pack library.

Relay chat messages and the standalone translator work the same way.

## Privacy

Because packs are local, translation works in privacy mode. No outbound network
requests are made for translation. The Bergamot worker and pack files are served
from the same origin. The remote model registry is only contacted when you
choose to download packs, and that download path is blocked while privacy mode
is enabled.

## Platform notes

WASM performance depends on the device. Some older or constrained platforms may
load packs slowly or have limited memory for large models. If a pack import
fails, check that the archive contains the required `model`, `lex` and `vocab`
files and that the pair code is exactly four letters.
