# Rejected candidate

`Murmur_MallLessCrowded_natalie.ogg` — *Shopping mall, less crowded*, natalie, public
domain, from
https://commons.wikimedia.org/wiki/File:Shopping_mall_less_crowded.ogg
(direct: https://upload.wikimedia.org/wikipedia/commons/d/d5/Shopping_mall_less_crowded.ogg).

Downloaded, header-verified and measured like every other candidate, then **rejected by
the bed transient rule in `Scripts/release_soundscape_v2.py`**:

| measurement | value | limit |
|---|---|---|
| transient windows per minute | **10.00** | 6.0 |
| four-fold RMS jumps per minute | 2.00 | 4.0 |
| crest factor | 20.9 dB | 30.0 dB |
| duration | 30.1 s | — |
| mean spectral centroid | 1631 Hz | — |

Ten windows per minute sitting more than 18 dB above the median level means something in
it strikes repeatedly — trolley wheels, a door, hard footfalls. That is the impulsive
character the user described as "banging", so it is not shipped and is never imported. It
was replaced by *Church, people walking, steps with reverb* (stephan, public domain),
which measured zero flagged windows.

The bytes, the publisher page snapshot and the original provenance are kept here as
evidence of the check, not as a source. Nothing in `sources/` references them.

**Nobody listened to this file either.** It was rejected on numbers alone.
