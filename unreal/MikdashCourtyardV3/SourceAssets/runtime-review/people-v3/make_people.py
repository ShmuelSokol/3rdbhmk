"""Author Content/Distribution/People/people.json for the people-v3 review.

Geometry is generated so every loop provably satisfies the shipped rules in
ResidentRouteLoop.h / MikdashPeopleDirectory.h (4..6 waypoints, 60..120 m closed loop,
3..5 s pauses, >= 2 m between consecutive waypoints, inside the authored zone).
Names, missions and dialog are authored by hand below.
"""
import json
import math
from pathlib import Path

OUT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3\SourceAssets\runtime-review\people-v3\people.json')

SANCTUARY = [0.0, 0.0, 300.0]
EAST_GATE = [7800.0, 0.0, 300.0]
DECK_GATE = [8600.0, 0.0, 0.0]
DECK_OUT = [11500.0, 0.0, 0.0]

PAUSES = [4.0, 3.0, 5.0, 4.0, 3.5, 4.5]


def rect(cx, cy, w, h, z):
    hw, hh = w / 2.0, h / 2.0
    return [[cx - hw, cy - hh, z], [cx + hw, cy - hh, z], [cx + hw, cy + hh, z], [cx - hw, cy + hh, z]]


def zigzag(x0, x1, ys, z):
    pts = []
    for i, y in enumerate(ys):
        pts.append([x0 if i % 2 == 0 else x1, y, z])
    return pts


def loop_len(points):
    n = len(points)
    return sum(math.hypot(points[i][0] - points[(i + 1) % n][0], points[i][1] - points[(i + 1) % n][1]) for i in range(n))


def build_route(points, labels, actions, looks):
    assert len(points) == len(labels) == len(actions) == len(looks), 'route arrays differ'
    out = []
    for i, p in enumerate(points):
        out.append(dict(at=[float(p[0]), float(p[1]), float(p[2])],
                        pause=PAUSES[i % len(PAUSES)],
                        label=labels[i], action=actions[i],
                        look=[float(looks[i][0]), float(looks[i][1]), float(looks[i][2])]))
    return out


# --------------------------------------------------------------------------------------
# Authored cast. Names are original fiction; no historical sage is impersonated, and no
# character quotes a ruling. Origins are described as regions, not real modern towns.
# --------------------------------------------------------------------------------------
# (id, name, role, garment, zone, origin, presence, mission, [dialog lines])
CAST = [
    ('yoav-ben-shimi', 'Yoav ben Shimi', 'pilgrim', 'linen-undyed', 'outer-court',
     'the northern valleys', '',
     'Keep his household together on the walk up and deliver the first fruits basket he carried from home.',
     ["I came up from the northern valleys; the walk took our household the better part of a week.",
      "This basket has been on my shoulder since the vineyard; I would rather carry it than set it down.",
      "We gathered in our district's city first, and travelled in one company from there.",
      "My father made this walk before me. I am glad my sons can see the place with their own eyes."]),

    ('miryam-bas-elyakim', 'Miryam bas Elyakim', 'pilgrim', 'wool-madder', 'outer-court',
     'the southern hill country', '',
     'Find the shaded edge of the court where her household agreed to gather after the offering.',
     ["We are from the southern hill country, and my brother is somewhere in this crowd.",
      "I have never seen this many people stand quietly in one place.",
      "We agreed to meet at the edge of the court; I am walking the line until I find them.",
      "I brought nothing heavy this time, only what we could carry and still keep the children rested."]),

    ('naftali-ben-chagai', 'Naftali ben Chagai', 'pilgrim', 'traveller-dust', 'outer-court',
     'the eastern plain', '',
     'Walk the whole length of the outer court once, slowly, because it is his first ascent.',
     ["I crossed the eastern plain to be here, and I am still shaking the dust out of my cloak.",
      "It is my first time. I am walking the court once, slowly, before I do anything else.",
      "I brought an offering with me and I am told to wait until my group is called.",
      "Someone should tell me where to stand. I would rather ask than guess."]),

    ('tzipporah-bas-menachem', 'Tzipporah bas Menachem', 'pilgrim', 'wool-indigo', 'outer-court',
     'the coastal lowland', '',
     'Keep a small child in sight while the rest of her household waits with their offering.',
     ["We came up from the coastal lowland; the sea air is a long way behind us now.",
      "My youngest has not stopped asking questions since we came through the gate.",
      "I am not going far. I only need to keep her where I can see her.",
      "We brought what our fields gave this year, and we are grateful it was enough to bring."]),

    ('elchanan-ben-uriya', 'Elchanan ben Uriya', 'pilgrim', 'mantle-olive', 'outer-court',
     'the river districts', '',
     'Carry his household\'s offering to the appointed place and then wait with the group.',
     ["We travelled from the river districts. Four days of walking, and two of waiting for the ferry.",
      "I am carrying my household's offering; the rest of them are resting near the wall.",
      "The elders in my group know the order of things. I follow where they lead.",
      "I keep looking up at the building and forgetting to keep walking."]),

    ('shulamis-bas-yechiel', 'Shulamis bas Yechiel', 'pilgrim', 'linen-bleached', 'outer-court',
     'the northern lake shore', '',
     'Walk the northern side of the court and count her group back together before evening.',
     ["We came from the northern lake shore, nine of us, and I have counted eight twice now.",
      "I brought dried fruit for the road and almost nothing of it is left.",
      "We immersed before we came up, as our household always does before ascending.",
      "I am not going to sit down until I have all nine."]),

    ('gad-ben-peleth', 'Gad ben Peleth', 'pilgrim', 'wool-umber', 'outer-court',
     'the high pastures', '',
     'Bring the animal his household set aside as far as the place his group was told to wait.',
     ["I came down out of the high pastures. My flock is with my brothers; only this one came up.",
      "It is a long way to carry anything, and a longer way to carry it carefully.",
      "I have been told where my group waits, and I am walking there now.",
      "My grandfather described this court to me. He did not exaggerate."]),

    ('devorah-bas-amram', 'Devorah bas Amram', 'pilgrim', 'mantle-saffron', 'outer-court',
     'the western foothills', '',
     'Stay near the group leader who carries their district\'s basket, and help the older women keep pace.',
     ["Our company came from the western foothills and we walked in behind the leading ox.",
      "There was a flute ahead of us for part of the way; I can still hear it when it is quiet.",
      "I walk beside the older women in our group so nobody is left behind at the turns.",
      "I have no idea where I am, only who I am following."]),

    ('yigal-ben-zerach', 'Yigal ben Zerach', 'pilgrim', 'traveller-dust', 'outer-court',
     'the desert edge', '',
     'Reach the eastern side of the court and wait there for the rest of his travelling company.',
     ["I came up along the desert edge. The road is quiet and the water is scarce.",
      "My company is behind me by half a day; I am holding a place for them.",
      "I brought what a man can carry alone, which is not much, but it is mine to bring.",
      "I would rather stand here and wait than lose them in this crowd."]),

    ('techiya-bas-nadav', 'Techiya bas Nadav', 'pilgrim', 'wool-indigo', 'outer-court',
     'the terraced slopes', '',
     'Walk the quiet western side of the court while her household rests, and return before they move.',
     ["We came from the terraced slopes; our fruit ripens late, so we came late.",
      "My household is resting. I wanted to walk while there was still light.",
      "I did not expect it to be this large, or this quiet in the corners.",
      "I will be back before they move; I have walked this side twice already."]),

    ('amitai-ben-kalev', 'Amitai ben Kalev', 'pilgrim', 'linen-undyed', 'outer-court',
     'the southern grain country', '',
     'Deliver his district\'s basket to the group leader and stay with the basket until he does.',
     ["I am from the southern grain country; the harvest was good and we said so with this basket.",
      "Our district gathered in one town and came up together, as the group always does.",
      "I am carrying it to our leader. Until then it does not leave my hands.",
      "Ask me again in an hour and I will still be holding it."]),

    ('yehudis-bas-ovadya', 'Yehudis bas Ovadya', 'pilgrim', 'wool-madder', 'outer-court',
     'the northern ridges', '',
     'Find the group of women from her district and walk the court with them before evening.',
     ["We came down off the northern ridges, and the last part of the road is all uphill again.",
      "I am looking for the women of my district; we said we would walk the court together.",
      "We brought what we had. It was a hard year, but we did not come empty.",
      "If you see a company with a red-bordered cloth, that is us."]),

    ('pinchas-ben-achituv', 'Pinchas ben Achituv', 'kohen', 'linen-undyed', 'outer-court',
     '', 'Crossing the public court on his way to his watch; not serving and not stationed here.',
     'Cross the outer court to reach the place his watch assembles before his turn begins.',
     ["My watch is called up this week, so I am crossing to where we assemble.",
      "I am not serving at this moment; I am only walking to my turn.",
      "The order of who does what is settled by lot, not by asking, and I would not want it otherwise.",
      "If you need an answer about what you may do, ask one of the teachers, not a man in a hurry."]),

    ('yedidya-ben-chilkiya', 'Yedidya ben Chilkiya', 'kohen', 'linen-bleached', 'outer-court',
     '', 'Off duty and changed out of service garments before coming out among the people.',
     'Walk out among the people after his watch, in ordinary clothes, and answer what he can.',
     ["My watch finished its turn. I changed before coming out here, as we do.",
      "What I am wearing now is ordinary cloth. Service garments do not leave their place.",
      "People ask me things all day. Half of them I answer, and half of them I send to a teacher.",
      "It is a strange thing to walk slowly in a place where you usually walk quickly."]),

    ('uriel-ben-shemaya', 'Uriel ben Shemaya', 'kohen', 'linen-undyed', 'outer-court',
     '', 'Newly assigned; walking the public court to learn its approaches before his watch is called.',
     'Learn the approaches of the court on foot before his watch is called up for its turn.',
     ["I am newly assigned, so I am walking the approaches until I know them without thinking.",
      "My watch has not been called yet. When it is, I would rather not be counting doorways.",
      "An older kohen told me to walk it twice before I ask anyone anything. I am on my second.",
      "I check my assignment more often than I need to. That is probably obvious."]),

    ('assaf-ben-berachya', 'Assaf ben Berachya', 'levite', 'wool-indigo', 'outer-court',
     '', 'Waiting in the public court for a gate or music assignment; no assignment yet given.',
     'Wait where assignments are passed on, and keep himself ready for whichever one comes.',
     ["I am waiting to hear what I am assigned to today. It has not come down yet.",
      "It might be a gate. It might be with the singers. I get ready for both.",
      "Waiting is most of it, honestly. Then all at once it is not.",
      "I would rather stand here ready than be found somewhere else when the word comes."]),

    ('chananel-ben-mattisyahu', 'Chananel ben Mattisyahu', 'levite', 'wool-umber', 'outer-court',
     '', 'Between duties in the public court; walking to where the day\'s assignments are given out.',
     'Walk to the place where the day\'s assignments are given and take whatever he is handed.',
     ["I am between duties, so I am walking over to where the day's assignments are given.",
      "Some days it is the gate, some days it is standing with the others and keeping time.",
      "You learn to hear the start of a thing from a long way off.",
      "Ask me tomorrow and I may be standing somewhere else entirely."]),

    ('rivka-bas-yoezer', 'Rivka bas Yoezer', 'host', 'mantle-saffron', 'outer-court',
     '', '',
     'Find the family she agreed to lodge and walk them back to the room she has prepared.',
     ["I keep a room in the city and I said I would meet a family here today.",
      "They are from far off and they have never come up before, so I said I would find them.",
      "The room is ready. It is small, but it is swept and there is water.",
      "I have described them to myself so many times I will probably walk past them."]),

    ('nechemya-ben-tzuriel', 'Nechemya ben Tzuriel', 'guide', 'mantle-olive', 'outer-court',
     '', '',
     'Walk the court answering questions about where things are, and send harder questions on.',
     ["I walk this court and answer what I can about where things are and how to get there.",
      "If the question is about what you may do, I take you to someone who teaches. I do not rule.",
      "Most people only want to know where their group went. I can usually help with that.",
      "I have been asked the same three questions since morning, and I do not mind at all."]),

    ('shmaya-ben-nachshon', 'Shmaya ben Nachshon', 'host', 'wool-umber', 'mount-deck',
     '', '',
     'Meet arriving households on the platform approach and walk them to lodging in the city.',
     ["I meet people out here on the approach, before the crowd swallows them.",
      "I keep rooms in the city for households coming up; there is a long argument about what may be charged, and I do not settle it.",
      "You look like you have walked a long way. Most people out here have.",
      "Rest here first. Nothing you need to do is helped by arriving out of breath."]),

    ('aviela-bas-refael', 'Aviela bas Refael', 'guide', 'linen-bleached', 'mount-deck',
     '', '',
     'Stand on the approach and orient first-time arrivals before they walk up to the gate.',
     ["I stand out here so first-time visitors have someone to ask before they go up.",
      "I can tell you which way to walk. What you may do when you get there is not mine to say.",
      "People arrive and stop right in the middle of the path. It happens all day.",
      "Take a moment out here. It is a better place to gather your household than the gateway."]),

    ('ovadya-ben-ephrayim', 'Ovadya ben Ephrayim', 'vendor', 'traveller-dust', 'mount-deck',
     '', '',
     'Sell mats and carrying baskets to arriving travellers, out here and never inside the precinct.',
     ["I sell mats and carrying baskets, and I sell them out here, not in there.",
      "Nothing of mine goes past the approach. That is not where my work belongs.",
      "A traveller who has slept on stone for four nights buys a mat without much persuasion.",
      "I have been set up on this stretch since before dawn."]),

    ('machla-bas-yiftach', 'Machla bas Yiftach', 'vendor', 'wool-madder', 'mount-deck',
     '', '',
     'Provision arriving households with dried food for the road, keeping her stall off the precinct.',
     ["Dried figs, dates, hard bread. Road food, for people who are still on the road.",
      "My stall stays out here on the approach. It does not go up with you.",
      "Most of what I sell is bought by someone who is about to give it to somebody else.",
      "I close early. Everyone I am here for has already walked past by then."]),

    ('elad-ben-yishai', 'Elad ben Yishai', 'vendor', 'mantle-olive', 'mount-deck',
     '', '',
     'Repair sandals and refill water skins for travellers before they walk up from the approach.',
     ["Sandals and water skins. Both fail on the last day of a long walk, every time.",
      "I work out here on the approach. That is the right side of the line for a trade like mine.",
      "Sit down, give me the sandal, and tell me where you walked from.",
      "I have mended more straps this week than in the whole month before it."]),
]

# --------------------------------------------------------------------------------------
# Loops, in cast order. Outer court first (19), then the mount deck (5).
# --------------------------------------------------------------------------------------
Z = 300.0
DZ = 0.0
LOOPS = [
    # 3 columns x 2 rows on the north side, 1450 x 1700 (63.0 m)
    rect(2400, 1900, 1450, 1700, Z),
    rect(4250, 1900, 1450, 1700, Z),
    rect(6100, 1900, 1450, 1700, Z),
    rect(2400, 4400, 1450, 1700, Z),
    rect(4250, 4400, 1450, 1700, Z),
    rect(6100, 4400, 1450, 1700, Z),
    # mirrored on the south side
    rect(2400, -1900, 1450, 1700, Z),
    rect(4250, -1900, 1450, 1700, Z),
    rect(6100, -1900, 1450, 1700, Z),
    rect(2400, -4400, 1450, 1700, Z),
    rect(4250, -4400, 1450, 1700, Z),
    rect(6100, -4400, 1450, 1700, Z),
    # long circuits, 116 m
    rect(4250, 3200, 3600, 2200, Z),
    rect(4400, -3100, 3200, 2600, Z),
    rect(4100, 3050, 3200, 2600, Z),
    rect(4350, -3250, 3600, 2200, Z),
    # three medium loops in the gaps
    rect(6200, 2600, 1200, 1900, Z),
    rect(2200, -2600, 1300, 1800, Z),
    rect(2300, 4600, 1300, 1800, Z),
    # mount deck: two zigzags and three narrow rectangles
    zigzag(9360, 9940, [-2600.0, -1500.0, -400.0, 700.0, 1800.0], DZ),
    zigzag(9400, 9900, [2700.0, 1600.0, 500.0, -600.0, -1700.0], DZ),
    rect(9650, 0, 600, 2500, DZ),
    rect(9640, 1400, 560, 2600, DZ),
    rect(9660, -1100, 660, 2400, DZ),
]

ROLE_STEPS = {
    'pilgrim': (["Walk along the court toward the meeting place",
                 "Follow the edge of the court",
                 "Cross toward the quieter side",
                 "Turn back along the court",
                 "Walk the last stretch of the circuit",
                 "Return to where the group agreed to wait"],
                ["Stand and look toward the sanctuary",
                 "Look back the way the group came",
                 "Wait and scan the crowd",
                 "Rest a moment and look up",
                 "Stand quietly at the turn",
                 "Look for a familiar face"]),
    'kohen': (["Cross the court on the way to the watch",
               "Continue along the court",
               "Take the turn toward the assembly place",
               "Walk the return stretch",
               "Carry on around the circuit",
               "Come back around to the start"],
              ["Pause and check the way ahead",
               "Look toward the sanctuary",
               "Stand a moment and let a group pass",
               "Look back across the court",
               "Wait at the turn",
               "Look toward the gate"]),
    'levite': (["Walk toward where assignments are given",
                "Continue along the court",
                "Turn along the far side",
                "Walk back across the court",
                "Carry on around the circuit",
                "Return to the waiting place"],
               ["Stand ready and listen",
                "Look toward the sanctuary",
                "Wait at the corner",
                "Look back along the court",
                "Stand still and wait",
                "Look toward the gate"]),
    'host': (["Walk the meeting line looking for the family",
              "Continue along the court",
              "Turn and search the far side",
              "Walk back toward the arrival side",
              "Carry on around the circuit",
              "Return to the agreed meeting point"],
             ["Stop and scan the arriving faces",
              "Look toward the gate",
              "Wait and watch the path",
              "Look back across the court",
              "Stand and wait a moment",
              "Look toward the approach"]),
    'guide': (["Walk the court where questions are asked",
               "Continue along the edge of the court",
               "Turn toward the busier side",
               "Walk back along the court",
               "Carry on around the circuit",
               "Return to the usual standing place"],
              ["Stand where visitors can find you",
               "Look toward the sanctuary",
               "Wait for someone to ask",
               "Look back along the path",
               "Stand and watch the crowd",
               "Look toward the gate"]),
    'vendor': (["Walk the approach beside the stall",
                "Carry goods along the platform",
                "Turn back along the approach",
                "Walk the far end of the pitch",
                "Carry on along the platform",
                "Return to the stall"],
               ["Set the load down and rest",
                "Look out along the arrival road",
                "Wait for travellers to come up",
                "Look back toward the gate approach",
                "Stand beside the goods",
                "Look along the platform"]),
}


def look_for(zone, index, action):
    """The point faced during a pause must agree with what the pause says it is doing."""
    text = action.lower()
    gate = DECK_GATE if zone == 'mount-deck' else EAST_GATE
    away = DECK_OUT if zone == 'mount-deck' else SANCTUARY
    if 'sanctuary' in text:
        return SANCTUARY
    if 'gate' in text or 'approach' in text:
        return gate
    if 'arrival road' in text or 'travellers' in text or 'platform' in text:
        return away
    return away if index % 2 == 0 else gate


def looks_for(person_zone, actions):
    return [look_for(person_zone, i, a) for i, a in enumerate(actions)]


def main():
    assert len(CAST) == 24, 'expected 24 individuals'
    assert len(LOOPS) == len(CAST), 'one loop per individual'
    people = []
    for index, entry in enumerate(CAST):
        pid, name, role, garment, zone, origin, presence, mission, dialog = entry
        points = LOOPS[index]
        steps, actions = ROLE_STEPS[role]
        labels = [steps[i % len(steps)] for i in range(len(points))]
        acts = [actions[i % len(actions)] for i in range(len(points))]
        looks = looks_for(zone, acts)
        length = loop_len(points)
        assert 6000.0 <= length <= 12000.0, '%s loop %.1f cm' % (pid, length)
        for i in range(len(points)):
            nxt = points[(i + 1) % len(points)]
            assert math.hypot(nxt[0] - points[i][0], nxt[1] - points[i][1]) >= 200.0, pid
            x, y, z = points[i]
            if zone == 'outer-court':
                assert 1500 <= x <= 7000 and 900 <= abs(y) < 6000 and abs(z - 300) <= 12, (pid, points[i])
            else:
                assert 9300 <= x <= 10000 and abs(y) <= 3000 and abs(z) <= 12, (pid, points[i])
        laps = 12 if len(points) <= 5 else 10
        assert len(points) * laps <= 64
        person = dict(id=pid, name=name, role=role, garment=garment, zone=zone,
                      mission=mission, dialog=list(dialog), laps=laps,
                      route=build_route(points, labels, acts, looks))
        if origin:
            person['origin'] = origin
        if presence:
            person['presence'] = presence
        people.append(person)

    starts = [(p['id'], p['route'][0]['at']) for p in people]
    for i in range(len(starts)):
        for j in range(i + 1, len(starts)):
            gap = math.hypot(starts[i][1][0] - starts[j][1][0], starts[i][1][1] - starts[j][1][1])
            assert gap >= 150.0, 'start points %s/%s only %.1f cm apart' % (starts[i][0], starts[j][0], gap)

    document = {
        'version': 'people-v3',
        'note': ('Twenty-four fictional inhabitants for the walkthrough. Names, households, origins, '
                 'missions and dialogue are authored fiction and are not source facts. No character '
                 'issues a halachic ruling, quotes a measurement as settled, names a Second Temple court '
                 'on the Yechezkel reconstruction, or states a future attendance number. Each route is a '
                 'closed 4 to 6 point loop with authored pauses; this is scripted waypoint behaviour with '
                 'written lines, not a mind.'),
        'placementBasis': {
            'pilgrim': {
                'decision': ('Pilgrims stand and walk on the outer court floor (Z 300, x 1500..7000, '
                             '900 <= |y| < 6000), off the y=0 east gate corridor. This repeats the envelope '
                             'already reviewed for the five-figure pilot rather than opening new ground.'),
                'evidence': ['Chagigah 1:1 and Devarim 16:11 via Research/people-and-city.md:44',
                             'Bikkurim 3:2-3 district gathering and travel distance via Research/people-and-city.md:48',
                             'Reviewed outer-court placement envelope, Scripts/release_place_assets.spec.json'],
                'notClaimed': ['No court on this reconstruction is labelled with a Second Temple name',
                               'No pilgrim is placed in the inner court or in any gate corridor'],
                'reviewFlag': 'R: court naming and boundary mapping still require a reviewer (halacha-and-service.md:26)'
            },
            'kohen': {
                'decision': ('Kohanim appear on the public outer court floor only in transit to a watch or '
                             'off duty in ordinary garments, never stationed, never serving, and never inside '
                             'a chamber. Yechezkel describes kohanim changing out of service garments before '
                             'going out to the people, which is the specific hook used here; the twenty-four '
                             'watches supply the arrival and departure movement.'),
                'evidence': ['Yechezkel 42:13-14, changing before going out to the people, via Research/halacha-and-service.md:50',
                             'Taanit 4:2 twenty-four watches going up when their turn arrives, via Research/people-and-city.md:36',
                             'Arrival, preparation, task and return arc via Research/people-and-city.md:38'],
                'notClaimed': ['Not stationed in an outer-court chamber',
                               'No teaching post or chamber occupancy is claimed',
                               'No priestly vestments are depicted; these are ordinary garments',
                               'No kohen here performs or narrates any service'],
                'reviewFlag': 'R: nothing in this project sources kohanim posted in the outer court, so only transit and off-duty states are used'
            },
            'levite': {
                'decision': ('Leviim appear on the outer court floor waiting for a gate or music assignment '
                             'that has not yet been given. No psalm, instrument or duty is named, because the '
                             'project has no reviewed source for the daily song or its assignment procedure.'),
                'evidence': ['Twenty-four watches and representative maamadot via Research/people-and-city.md:36',
                             'Cast intention: a Levi waiting for a musical or gate assignment, Research/experience-production-plan.md:118'],
                'notClaimed': ['No psalm of the day is named', 'No instrument other than travel context is depicted',
                               'No assignment procedure is asserted'],
                'reviewFlag': 'D: design-class cast intention, not a sourced posting'
            },
            'host': {
                'decision': ('Hosts meet arriving households, one on the outer court floor and one on the Mount '
                             'platform approach. Lodging is offered, never priced: the sources preserve differing '
                             'views on charging for accommodation and the project does not settle them.'),
                'evidence': ['Yoma 12a and R. Elazar bar Tzadok on charging for houses and beds, via Research/people-and-city.md:46',
                             'Cast intention: a host preparing a meeting place, Research/people-and-city.md:50'],
                'notClaimed': ['No price, rent or payment is quoted', 'No paid lodging quest exists'],
                'reviewFlag': 'R: the lodging economy premise is unresolved and is left unresolved in the dialogue'
            },
            'guide': {
                'decision': ('Guides answer where things are and explicitly refuse to answer what a visitor may '
                             'do, sending that question to a teacher. Dialogue may carry personality; it may not '
                             'become the authority that changes eligibility or teaches an unreviewed halachah.'),
                'evidence': ['Ask the guide as the correct action for missing status, Research/halacha-and-service.md:60',
                             'Dialogue must not invent a halachic ruling, Research/people-and-city.md:84'],
                'notClaimed': ['No guide states a rule, a permission or a prohibition'],
                'reviewFlag': 'D: authored characterisation only'
            },
            'vendor': {
                'decision': ('Vendors are placed only on the Mount platform deck near the east gate approach '
                             '(x 9300..10000, Z 0), outside the walled precinct, and each one says so. Commerce '
                             'is kept out of the sacred precinct: the sources do not support ordinary stalls in '
                             'the court, and the acceptance test is that no retail marker appears inside it.'),
                'evidence': ['Libation seals are not evidence for ordinary stalls in the courtyard, Research/people-and-city.md:64',
                             'Do not repurpose the kitchens as cafes, taverns or retail counters, Research/people-and-city.md:68',
                             'Interpretive provisioning area outside the Temple precinct, Research/people-and-city.md:70',
                             'Acceptance test: no retail marker in the Azarah without a reviewed basis, Research/people-and-city.md:72'],
                'notClaimed': ['No vendor is placed inside the precinct', 'No price is quoted and no economy is modelled',
                               'No vendor grants purity, eligibility or access'],
                'reviewFlag': 'R: the provisioning economy premise itself is not yet approved; these are presence and dialogue only'
            }
        },
        'people': people,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(document, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print('wrote %s (%d people)' % (OUT, len(people)))
    for p in people:
        print('  %-26s %-8s %-12s %s %5.1f m' % (p['id'], p['role'], p['garment'], p['zone'],
                                                 loop_len([w['at'] for w in p['route']]) / 100.0))


if __name__ == '__main__':
    main()
