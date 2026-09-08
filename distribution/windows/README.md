# Windows preview distribution

Walkthrough-09 uses two standard ZIP archives because the complete archive exceeds GitHub's per-asset size limit. Both ZIPs extract into the same root; the Data ZIP contains the game's large UCAS file at its native Paks path.

`SHA256SUMS.txt` records the exact published archives. The extraction receipt verifies every installed payload hash and independently compares all 49 distributable original runtime files with the original packaged Windows build. All 55 distribution files are accounted for, including credits and notices. The test deliberately does not launch the game.

Run the reproducible check using Python 3.9 or later:

```text
python verify_download.py App.zip Data.zip NEW_EMPTY_DESTINATION receipt.json --original ORIGINAL_WINDOWS_BUILD
```

The destination must not exist. ZIP extraction and original-runtime comparison run locally; no registry, firewall or other security settings are modified. GUI/menu controls in the standalone packaged game remain unverified; see the release notes.

A trial custom downloader was blocked by Windows antivirus during its real executable test. It was not allowed or distributed. Only the original packaged game and ordinary ZIP archives are released.
