# Mikdash walkthrough: plan to a lifelike experience you can share

Written 1 October 2026 for shmuel. Repo: github.com/ShmuelSokol/3rdbhmk. Work runs on the
PC at C:\Mikdash (16 GB RAM, RTX 2070 with 8 GB of video memory).

## Decided 1 October 2026: no money

shmuel said not to spend any money. So the phone version uses only free options:
- **Walk-it-yourself link streamed from the PC at C:\Mikdash.** Free, but only 1-2 visitors at a time,
  and only while the PC is on. Good for showing family and friends live.
- **A free 360-degree photo tour** from key spots that anyone can open on any phone, any time, hosted
  free (GitHub Pages). This is the version to share widely.
Paid cloud hosting stays off the table unless shmuel raises it again.

## What you asked for

1. A **phone link**: someone taps it and walks through the Mikdash themselves on their phone.
2. A **desktop version** you can share.
3. **Nothing is shared until it works**, and looks like you are really there:
   - no leftover objects from earlier builds (floating water heaters, stray domes, slabs);
   - physics that is right (people stand on the ground, water flows down, smoke rises, nobody walks through walls);
   - people who look like real people in any single frame, not mannequins.

## Where it stands today (honest)

- **There is a desktop download already**, but it is old. Walkthrough-09 (7 Sept) is public on GitHub
  Releases. Since then about a dozen local "checkpoint" builds exist on the PC, none shared.
- **Leftover objects are a known, partly fixed problem.** The floating tank/panel by the Kotel was traced to
  old roof decorations from the earlier square-wall design and removed on 18 Sept. The finish-line list still
  has open leftovers: a pale slab on the north-east horizon, souq arches and stalls sunk 10-45 cm into the new
  paving, floating foundations, and 1.1 million triangles of old placeholder trees still shipped.
- **People are the weakest part.** About 1,600-2,500 background figures are "baked" animated statues (cheap,
  but they look angular up close). Six residents and the Kohen Gadol are real characters. The Kohen has a
  photoreal MetaHuman head on cartoon-shaded garments. The last verdict was "people at 3-5 m, carved figures
  face-on at 2 m".
- **Nothing walks on a navigation mesh.** There is none in the map, so people follow fixed routes.
- **The phone link does not exist yet.** Unreal is enabled for it (Pixel Streaming is installed), but nothing
  has been built or tested.
- **The memory blocker is gone.** McAfee was leaking up to 16 GB and blocked most of the last two weeks.
  It was removed today; 14.6 GB is free. The Kohen review is running again in the device thread.
- **The biggest problem is process, not technology.** Weeks went into narrow studies (crowd shading normals,
  robe clearance to the tenth of a millimetre) while nothing new reached you. Work also stops whenever you
  stop messaging. The plan below fixes both.

## The ground rules every session follows from now on

1. **One target: Release Candidate 1 (RC1).** Every task has to move RC1 closer. Studies that do not change
   what a visitor sees get parked.
2. **Done means you saw it.** A fix counts when a screenshot or short clip from the real game shows it.
   A passing test log alone is not done.
3. **One map, one build line.** The shipping map is the only thing that matters. Old study maps, legacy
   actors and old roof and plaza layers either get deleted from that map or are moved out of the cook.
4. **A weekly build you can open.** Every week ends with a new playable build on the PC and a short clip of
   the walk route, even if it is not ready to share.
5. **One Unreal process at a time** on the PC (16 GB). Load assets before the map. Launch cooks detached.
6. **No money spent and nothing published** without your yes.

## Phase 1. Clean world (no leftovers)

Goal: walk anywhere and see nothing floating, sunken, doubled or left over.

1. **Build a "world sanity scan"** that runs inside Unreal over the shipping map and lists every object that:
   - has empty air under it (more than 5 cm above the surface below), unless it is meant to fly
     (birds, the dove, roof ornaments sitting on a roof);
   - is buried in the ground more than it should be;
   - overlaps an identical copy of itself (duplicate placement);
   - comes from an old layer (square-wall era, old plaza deck, study folders, placeholder trees);
   - is never visible in any of the three display states yet is still cooked.
   The scan writes a list with a thumbnail of each hit, so you can see them too.
2. **Fix or delete each hit**, starting with what is visible from the walk route.
3. **Fix the known ones**: the north-east slab, sunken stalls and arches, floating foundations,
   placeholder trees, bare-earth patches in the Old City, the hard paved/dirt diagonal.
4. **Re-run the scan on every build.** Zero unexplained hits is a requirement for RC1.

## Phase 2. Physics that is right

1. **Ground and collision.** Every walkable surface has collision; the player cannot fall through or walk
   through walls, columns or vessels. Run the existing walk probe over all 13 gates, stairs, courts and the
   sanctuary.
2. **Navigation mesh.** Build one for the shipping map (including the plaza deck that is created at start-up)
   so people find their own way and step around each other instead of following rails.
3. **Feet on the ground.** Foot placement (foot IK) on every character, so feet land on stairs and slopes
   rather than hovering or sinking. This is the most visible flaw on stairs today.
4. **Cloth that moves.** Robes and garments use cloth simulation for nearby characters so they swing and fold
   instead of being rigid shells.
5. **Fire, smoke and water behave.** Altar fire flickers and lights its surroundings, incense smoke rises and
   spreads, the stream from under the threshold flows downhill, the laver holds water. These were listed as
   the biggest "it looks like a model" gap.
6. **Scale check.** Doors, steps and railings against a 1.75 m person, using the 48 cm amah the project already
   adopted.

## Phase 3. People who look real

The honest limit: no PC with an RTX 2070 can draw thousands of fully photoreal people at once. Films and
top games solve this by making the **nearby** people real and the far ones cheap but convincing.
The plan does the same, in three tiers.

| Tier | Distance | What they are | How many at once |
|---|---|---|---|
| Hero | 0-15 m | Full MetaHumans: real skin, hair, eyes, faces, cloth | 8-16 |
| Mid | 15-40 m | Lighter MetaHuman versions, same bodies and clothes | 40-80 |
| Far | 40 m+ | Baked crowd made **from the same MetaHumans** so nothing changes as you approach | 2,000+ |

Steps:
1. **Switch the residents to MetaHuman bodies.** MetaHuman is already in the project (it made the Kohen's
   face), so the hand-built resident bodies get replaced rather than repaired further.
2. **Use motion matching for walking.** Unreal's motion-matching locomotion picks real captured motion for
   every step and turn, which ends the "stilting" and foot sliding. This replaces the hand-tuned walk loops.
3. **Clothing from period references**, with real fabric materials (wool, linen weave, gems that sparkle on the
   Kohen's choshen). The Kohen's garments go first, since his head is already photoreal.
4. **Variety**: at least 30 distinct faces and builds, different ages, varied walk speeds, groups and families,
   people stopping, talking and looking around. No two neighbours in step.
5. **The "any snapshot" test**: 50 random frames from a recorded walk, at full screen, reviewed by you.
   Any frame where a person looks like a mannequin is a defect.
6. **Measure before choosing counts.** Test 1 hero MetaHuman, then 8, then 16, recording memory and frame rate,
   and set the tier counts from the numbers, not from hope.

## Phase 4. Look and light

- Exposure that adapts naturally between bright courts and the darker Heikhal (the rear wall is still washed out).
- Stone that varies block to block instead of one repeating tile across the city.
- Clouds are now the most expensive thing in each frame (about 6 ms); trade them for a cheaper sky that looks the same.
- Trees: correct species colours, fuller crowns.
- Sound pass: footsteps by surface, crowd murmur, birds, the Leviim. (The old rejected loop stays off.)

## Phase 5. Desktop version (RC1)

1. Fresh full build from the cleaned map.
2. Target: 60 fps in courts and sanctuary, 45 fps on the city overlook, on the RTX 2070 at 1080p.
   Graphics presets (Low/Medium/High) so weaker PCs can run it.
3. Menu, pause, settings, a guided-tour mode and free-walk mode, a short how-to-move card.
4. **You walk it end to end** on the PC and say "share" or list what is wrong.
5. Only then: publish it as Walkthrough-13 on GitHub Releases, with a one-page "how to install".
   Optional later: a free Itch.io page, which is easier for non-technical people than GitHub.

## Phase 6. Phone link

A phone cannot run this Unreal build itself. The way to give people a real walk-through-it-yourself link is
**Pixel Streaming**: the game runs on a computer with a graphics card, and the phone shows a live video of it
and sends touches back. It looks exactly like the desktop version.

1. **Touch controls**: left thumb to walk, right thumb to look, tap to open info, a "reset" button. Also works with mouse and keyboard in a desktop browser.
2. **Test from your own PC first (free).** Your PC runs it, and you open the link on your phone over Wi-Fi,
   then over cellular. This proves the controls and quality.
3. **Then decide hosting (your decision, it costs money).** Each visitor needs their own copy of the game
   running on a cloud graphics card.

| Option | Cost | Visitors at once | Notes |
|---|---|---|---|
| Your own PC | free | 1, maybe 2 | PC must stay on and connected; your upload speed limits quality |
| Rented cloud GPU, on demand | roughly $0.50-$1.50 per visitor-hour | as many machines as you pay for | starts when someone opens the link, stops after; needs a waiting room |
| Managed streaming service | monthly plan plus usage | depends on plan | least setup work, least control |

   My recommendation is to start with the on-demand cloud option with a hard monthly spending cap and a
   "you are next in line" waiting room. Prices are rough and need checking before you commit.
4. **A no-cost companion link (optional)**: a set of 360-degree photos from key spots, viewable on any phone
   with no server cost. Good for sharing widely; it does not replace the walk-yourself link.
5. Test with two people at the same time on separate phones, each walking separately, before sharing.

## Phase 7. Share

You do a final walk on desktop and on your phone. Only after your yes: publish the desktop download and
turn on the phone link.

## Keeping all sessions on board

- This plan is saved in the repo (`unreal/MikdashCourtyardV3/SHAREABLE-WALKTHROUGH-PLAN.md`) so every session,
  including the one on the PC and any Codex session, reads the same thing, and in project memory.
- The device thread "Resume temple build in Mikdash" has been told to work to this plan.
- **Keep work moving while you are away.** Right now the PC session only works while you are messaging it.
  A scheduled check-in (for example every 3 hours while the PC is on) can tell it to continue the next
  plan step and post a short update. Say yes and it will be set up.

## Decisions only you can make

1. **Phone hosting money**: free own-PC test only for now, or a monthly cap for cloud streaming (and how much).
2. **Scheduled check-ins** so work continues without you messaging.
3. **Disk space**: about 253 GB of old build archives; pruning superseded ones frees roughly 150 GB.
4. **Still open from before**: the rock elevation under the Kodesh HaKodashim.

## Order of work, in one line each

1. Finish the current Kohen review, then freeze new studies.
2. World sanity scan, then fix every leftover it finds.
3. Ground, collision, navigation mesh, foot placement.
4. MetaHuman residents with motion matching; one hero test, then counts from measurements.
5. Fire, smoke, water, cloth.
6. Light, stone, sky, sound.
7. RC1 desktop build, your walk-through, then publish.
8. Phone touch controls, own-PC stream test, hosting decision, then the link.
