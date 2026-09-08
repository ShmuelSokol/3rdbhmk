# Download and play the Mikdash walkthrough

**[Open the Windows download page](https://github.com/ShmuelSokol/3rdbhmk/releases/tag/walkthrough-09-preview)**

This release is a Windows development preview. It is not a Mac, phone or browser build.

1. Download **both** `Mikdash-Walkthrough-09-App.zip` and `Mikdash-Walkthrough-09-Data.zip`. Do not choose GitHub's Source code archives.
2. Create a new empty folder, for example `C:\Games\Mikdash`. Allow **8 GB free space** for downloads and extraction.
3. Right-click the App ZIP and choose **Extract All**. Set the destination to `C:\Games\Mikdash`.
4. Extract the Data ZIP to that **exact same destination**. Change Windows' suggested destination if it includes the ZIP filename. The game data must end up at `C:\Games\Mikdash\MikdashCourtyardV3\Content\Paks\MikdashCourtyardV3-Windows.ucas`.
5. Open `C:\Games\Mikdash\MikdashCourtyardV3.exe`. Choose **Start** to walk, or **Explore as a white dove** to fly.

Keep the entire game folder together. Unreal Engine, Visual Studio and a GitHub account are not required to play. Once downloaded, the game runs locally without the developer's computer online. This is a single-player experience.

If Windows reports a missing Visual C++ runtime, install the **x64 Visual C++ Redistributable** from [Microsoft's official download page](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist). A prerequisite installer is not bundled. Incoming network access is not needed for the local walkthrough.

## Controls

- **WASD / arrow keys:** move.
- **Mouse:** look around.
- **F:** switch to white-dove flight, or return to the original walking position.
- **Space / Ctrl in flight:** ascend / descend.
- **Shift in flight:** faster movement.
- **P / Escape:** pause and release the mouse.
- **M:** mute / restore sound.
- **Alt+F4:** close.

## Hardware and preview status

Intended for Windows 10/11 x64 gaming PCs. The development machine has an RTX 2070 and 16 GB RAM; formal minimum requirements and performance on other hardware have not been established.

The fresh game/editor build and cook passed. Live Unreal tests verified the entrance/platform route, sanctuary round trip, dove movement/ascent/pause/return, and five visitors reaching their destinations. Packaged menu/input and visual checks remain incomplete; the initial packaged launch was covered by a Windows Firewall prompt. The photo-based Kotel is a first surface pass, and the dove is a stylized model. This is not final production-quality or source-accuracy certification.

Attribution is included in **CREDITS.txt** and the accompanying notices. **SHA256SUMS.txt** on the release page provides hashes for both ZIP downloads. [Detailed release notes](MikdashCourtyardV3/RELEASE-NOTE-Walkthrough-09.md).
