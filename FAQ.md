# FAQ - Frequently Asked Questions

...and questions that will likely be asked at some point.

**Why can't I reach you over LXMF all the time?**

Grow some patience, send it to a propagation node, and chill. Sometimes I go offline or travel for a few hours, days, or maybe a week. Your message will make it to me; just be patient.

**Why did you create MeshChatX?**

I noticed Liam Cottle became busy with MeshCore stuff, but I also wanted something modern and easier to use for myself and some friends. Eventually more people discovered my fork and started using it. I have since reworked the architecture and modernized most of the frontend and backend. I am not a fan of Electron, but I do what I can to make it a worthy Electron application by taking advantage of everything it has to offer, from packaging to security and integrity.

**Will MeshChatX move to a different implementation?**

Not for the foreseeable future. MeshChatX will continue to use the official Reticulum Network Stack by Mark Qvist. That goes for LXMF and LXST as well.

**Can you move your repository under a community organization?**

No. Until the day I stop maintaining MeshChatX, it will remain under Quad4 control. The official source code is both on `git.quad4.io` and on Reticulum via rngit, while GitHub and other places are mirrors only. You are always welcome to fork if you do not like the way I do things.

**Why are PRs disabled on GitHub?**

GitHub is a mirror to use CI and push out releases only. Submitting a patch over LXMF is also a filter for the low-effort and purely vibe-coded crap that people submit these days. It has actually been working quite well, especially for low-effort social engineering.

**Do you use AI?**

In some places of the codebase, yes, but I apply my own judgment. I mostly use local models with some custom tooling. If I use external providers for more complex tasks, I choose open-weight models and zero-retention, zero-training providers that are in my jurisdiction and can be held accountable in court if necessary. I also use linting, SAST, DAST, and tests to ensure LLM code is properly validated, implemented, and follows best practices.

**Will MeshChatX support legacy systems?**

Electron has to be kept up-to-date with a stable release cycle in order to get any CVE fixes for the bundled Chromium or other Electron-related security and performance fixes. You can use the Python wheels if your system supports Python 3.11. I would like to support all systems, but that is just not possible with Electron and the values of this project (security).

**Can you make it so MeshChatX uses system RNS/LXMF packages?**

The Python wheels can use system RNS/LXMF, and you can update them easily. With Docker, you can grab the Dockerfile, update it, and build manually. You can also build from source. As for Electron builds, there is not much that can be done right now, but I will keep exploring options.

