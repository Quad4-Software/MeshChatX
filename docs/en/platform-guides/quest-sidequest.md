# Meta Quest with SideQuest

The MeshChatX Android APK runs on Meta Quest 2, Quest 3, Quest 3S, and Quest Pro. Quest headsets run a modified Android runtime, so the same universal APK published for phones and tablets can be installed by sideloading.

MeshChatX opens as a **2D panel** inside your VR environment. It is not a native VR application. You get the full MeshChatX web UI in a floating window while you remain in your Quest home space.

![MeshChatX running on Meta Quest 2](../../../screenshots/vr/meshchatx-quest2.jpeg)

## What you need

- A Meta Quest 2 or newer headset
- A Meta account with **Developer Mode** enabled
- [SideQuest](https://sidequestvr.com/) on your PC (desktop app) or access to the SideQuest web installer
- A USB-C cable (for wired sideloading) or a working wireless ADB setup

## Get the APK

Download the latest signed Android APK from the [MeshChatX releases page](https://github.com/Quad4-Software/MeshChatX/releases). Release assets are named like `ReticulumMeshChatX-v*-android-universal.apk`.

You can also build the APK yourself. See [`android/README.md`](../../../android/README.md).

## Enable Developer Mode

1. Install the Meta Horizon app on your phone and pair your headset.
2. Open **Menu** -> **Devices** -> select your headset -> **Developer Mode**.
3. Turn Developer Mode on and accept the prompt on the headset if asked.

Developer Mode is required for sideloading and for SideQuest to see the device.

## Install with SideQuest

Wired install (typical path):

1. Connect the Quest to your PC with USB-C.
2. Put on the headset. Accept **Allow USB debugging** when Meta prompts you.
3. Open the SideQuest desktop app. Confirm the headset shows as connected (green dot).
4. Click **Install APK file from folder on computer** (or drag the APK onto SideQuest).
5. Select the `ReticulumMeshChatX-v*-android-universal.apk` file you downloaded.

Wireless ADB works when your PC and headset share a network and SideQuest can pair over Wi-Fi. Follow SideQuest's wireless pairing steps if you prefer that over USB.

## Launch on the headset

1. Open the **Apps** library on the Quest.
2. Filter to **Unknown Sources** (or **Unknown** on newer Horizon builds).
3. Select **MeshChatX**.

The app opens as a 2D panel. Grant microphone permission if you plan to use LXST calls.

## First run

MeshChatX stores data under the Android app sandbox like any other APK build. Add a Reticulum interface from **Interfaces** before you expect mesh traffic. Quest Wi-Fi only reaches your LAN and the internet. It does not replace a mesh uplink unless you configure one (for example a TCP client to a known peer).

For native Android builds (not Termux), see [`android/README.md`](../../../android/README.md).
