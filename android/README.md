# MeshChatX Android App

This directory contains the Android app build configuration using Chaquopy to embed the Python MeshChatX server.

## Architecture

The app uses a **WebView** to display the existing Vue.js frontend. The Python server runs in the background via Chaquopy and serves the web interface on `https://127.0.0.1:8000`.