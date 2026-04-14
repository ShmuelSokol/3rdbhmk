# 3rd Beis HaMikdash Translation -- Project Wiki

This wiki documents the full architecture, methodology, and decision history of the **Lishchno Tidreshu** English typeset PDF project. It is intended for any developer or AI agent continuing the work.

## Pages

1. [Project Overview](overview.md) -- What this project is, the Hebrew source book, the English translation goal
2. [System Architecture](architecture.md) -- Next.js app, Supabase, Railway, Prisma schema, pipeline stages
3. [Typeset System](typeset-system.md) -- PDF generation: the typeset route, content elements, rendering pipeline, page layout
4. [Illustration System](illustration-system.md) -- OCR to pixel analysis to blob detection to autoresearch optimization to crop editor to PDF insertion
5. [Translation Rules](translation-rules.md) -- ArtScroll style, Hebrew inline quotes, pesukim format, terminology conventions
6. [Layout Rules](layout-rules.md) -- Image placement, page breaks, justification, margins, blank page avoidance
7. [Crop Editor](crop-editor.md) -- The crop editor UI: mobile touch support, approve/lock workflow, save to Supabase
8. [Autoresearch](autoresearch.md) -- Ground truth from user edits, IoU scoring, parameter sweeps, algorithm racing
9. [Distribution](distribution.md) -- Print-on-demand plans: Lulu, IngramSpark, KDP, Judaica stores
10. [Decisions Log](decisions-log.md) -- Key decisions and their rationales

## Quick Reference

| Item | Value |
|------|-------|
| Domain | https://3rdbhmk.ksavyad.com |
| Repo | https://github.com/ShmuelSokol/3rdbhmk |
| Root dir | `web/` |
| Book ID | `jcqje5aut5wve5w5b8hv6fcq8` |
| Railway project | `5d90489e-8dfb-4a60-8b19-28c9e603c61b` |
| Railway service | `a1b9d33c-7764-487b-92f3-11ba1d2a30f2` |
| Supabase bucket | `bhmk` |
| Hebrew source pages | 367 |
| English PDF pages | ~353 (after duplicate skip) |
