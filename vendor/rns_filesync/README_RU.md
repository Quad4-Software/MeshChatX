# RNS FileSync (RU)

English README is the source of truth: [README.md](README.md).

Кратко: библиотека и CLI для синхронизации каталогов через Reticulum (`rns>=1.4.0`).
Конфиг и ACL как у rngit: `~/.rns_filesync/config`, правила `r:hash` / `w:all`, файлы `.allowed`.

```bash
pip install -e ".[dev]"
rns-filesync -d ~/shared -p <identity_hash>
rns-filesync --config ~/.rns_filesync --rnsconfig ~/.reticulum -d ~/shared
```
