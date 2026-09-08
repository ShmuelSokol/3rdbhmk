# Mikdash Walkthrough 09 — Windows preview

Download **both ZIPs** below: **Mikdash-Walkthrough-09-App.zip** and **Mikdash-Walkthrough-09-Data.zip**. You do not need Unreal Engine, Visual Studio, a GitHub account, or access to the developer's computer to play.

## Install and play

1. Download both ZIP files and create an empty folder such as `C:\Games\Mikdash`. Allow **8 GB free space**.
2. Use Windows **Extract All** on each ZIP, selecting the **same destination folder** for both. Replace the suggested destination if it includes the ZIP filename.
3. Open **MikdashCourtyardV3.exe** directly inside that folder.
4. Choose **Start** or **Explore as a white dove**.

The data file belongs at `MikdashCourtyardV3\Content\Paks\MikdashCourtyardV3-Windows.ucas` inside the game folder. Keep the whole folder together. GitHub's Source code archives are not the playable game.

**Controls:** WASD/arrows to move, mouse to look, F for dove/return, Space/Ctrl for flight altitude, Shift for faster flight, P/Escape to pause, M for sound.

Intended for Windows 10/11 x64 gaming PCs. Development hardware: RTX 2070 and 16 GB RAM. Formal minimum requirements and performance across other devices are not yet established. If the game reports a missing Visual C++ runtime, use [Microsoft's official x64 runtime download](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist). Incoming network access is not needed for the local walkthrough.

## Preview status

This early development preview includes ground walking, white-dove exploration, a first photograph-based Kotel surface, interior lighting improvements, and a five-visitor movement pilot.

Fresh Unreal game/editor compilation and cook passed. Main-world movement tests passed for the entrance/platform route, sanctuary round trip, dove movement/ascent/pause/exact return, and all five visitors reaching their destinations. Distribution files are checked against the original packaged build.

Packaged visual and input checks remain incomplete: the initial standalone menu was covered by a Windows Firewall prompt. This preview still has unfinished visuals, source-accuracy questions, simple visitor routines, a stylized dove and a soft/flat Kotel photo surface. It is not a finished reconstruction or halachic ruling.

Attribution and license notices are included with the game. Release download checksums are in **SHA256SUMS.txt**. [Full installation guide](https://github.com/ShmuelSokol/3rdbhmk/blob/main/unreal/DOWNLOAD.md).
