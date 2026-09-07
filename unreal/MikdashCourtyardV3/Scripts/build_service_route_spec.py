"""Deterministic, offline scene inputs. No Unreal import or runtime permission grant.

python Scripts/build_service_route_spec.py
python Scripts/build_service_route_spec.py --check
Only this script and SourceAssets/experience-review/service-routes are owned.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'SourceAssets/experience-review/service-routes'
RESEARCH = Path('C:/Mikdash/GitHub/3rdbhmk/unreal/Research')
MANIFEST = ROOT / 'SourceAssets/architecture-manifest.json'


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + '\n').encode('utf-8')


def fingerprint(path, label):
    data = path.read_bytes()
    return dict(path=label, bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def build():
    meshes = {m['assetName']: m for m in json.loads(MANIFEST.read_text())['meshes']}
    sources = {}

    def source(key, category, reference, url, claim, dossier):
        sources[key] = dict(category=category, reference=reference, url=url, claim=claim,
                            dossier=dossier, verification='reused_local_dossier_2026-09-07',
                            futureApplication='needs_review')

    source('PREP', 'H', 'Numbers 19:11-19; Biat HaMikdash 3:3-7,14',
           'https://www.chabad.org/library/article_cdo/aid/1008244/jewish/Biat-Hamikdash-Chapter-3.htm',
           'Independent preparation states and sacred zones; immersion is not a universal reset.', 'halacha-and-service.md')
    source('SERVICE_IMMERSION', 'H', 'Mishnah Yoma 3:3-4', 'https://www.sefaria.org/Mishnah_Yoma.3.3-4',
           'Service immersion has its own purpose; privacy precedent does not specify our screen treatment.', 'halacha-and-service.md')
    source('HANDS_FEET', 'H', 'Biat HaMikdash 5:1-2',
           'https://www.chabad.org/torah-texts/1008246/Mishneh-Torah-Rambam/Sefer-Avodah/Biat-Hamikdash/Biat-Hamikdash-Chapter-5',
           'Hands-and-feet sanctification is a separate service prerequisite.', 'halacha-and-service.md')
    source('ACCESS', 'H', 'Mishnah Kelim 1:8-9', 'https://www.sefaria.org/Mishnah_Kelim.1.8-9',
           'Role, task and zone matter; ordinary visitors do not enter the innermost sanctuary.', 'halacha-and-service.md')
    source('REVERENCE', 'H', 'Beit HaBechirah 7:1-2',
           'https://www.chabad.org/library/article_cdo/aid/1007200/jewish/Beit-Habechirah-Chapter-7.htm',
           'An unrelated business shortcut is not a sacred-precinct journey purpose.', 'halacha-and-service.md')
    source('GARMENTS', 'P', 'Ezekiel 42:13-14; 44:17-19',
           'https://www.chabad.org/library/bible_cdo/aid/16140/jewish/Chapter-42.htm',
           'Holy-food/service-garment chambers differ from family housing; exact room assignment unresolved.', 'halacha-and-service.md')
    source('GARMENT_PROFILE', 'H', 'Klei HaMikdash 8:1-3,11',
           'https://www.chabad.org/library/article_cdo/aid/1008233/jewish/Klei-Hamikdash-Chapter-8.htm',
           'Garment sets depend on role/service; reconcile with the selected prophetic interpretation.', 'halacha-and-service.md')
    source('HOMES', 'P', 'Ezekiel 45:4', 'https://www.chabad.org/library/bible_cdo/aid/16143/jewish/Chapter-45.htm',
           'Priestly residential land is described; individual addresses and floor plans are not supplied.', 'people-and-city.md')
    source('LODGING', 'H', 'Mishnah Tamid 1:1', 'https://www.sefaria.org/Mishnah_Tamid.1.1',
           'Duty lodging, bedding and discreet immersion access are earlier-Temple practices, not family housing.', 'people-and-city.md')
    source('ROTATION', 'H', 'Mishnah Taanit 4:2', 'https://www.sefaria.org/Mishnah_Taanit.4.2',
           'Watches explain duty rotation, not future watch population.', 'people-and-city.md')
    source('DAYLIGHT', 'H', 'Mishnah Tamid 1:2; 3:2', 'https://www.sefaria.org/Mishnah_Tamid.3.2',
           'Supervisor arrival is variable; daylight is checked before morning slaughter.', 'halacha-and-service.md')
    source('LOTTERY', 'H', 'Mishnah Tamid 5:2', 'https://www.sefaria.org/Mishnah_Tamid.5.2',
           'New-to-incense eligibility matters for the described lottery; retain prior duty history.', 'halacha-and-service.md')
    source('PM_ORDER', 'H', 'Mishnah Pesachim 5:1', 'https://www.sefaria.org/Mishnah_Pesachim.5.1',
           'Ordinary afternoon timing uses seasonal hours; Erev Pesach profiles differ.', 'halacha-and-service.md')
    source('GATES', 'P', 'Ezekiel 46:1-3,9-10', 'https://www.chabad.org/library/bible_cdo/aid/16144/jewish/Chapter-46.htm',
           'Inner east gate and opposite-gate gathering routes are calendar-specific; future mapping requires review.', 'people-and-city.md')
    source('KITCHENS', 'P', 'Ezekiel 46:19-24', 'https://www.chabad.org/library/bible_cdo/aid/16144/jewish/Chapter-46.htm',
           'Priestly and people-offering kitchens have different purposes; neither is a cafe.', 'people-and-city.md')
    source('KET_LOCATION', 'H', 'Temidin uMusafim 3:1,3,9',
           'https://www.chabad.org/library/article_cdo/aid/1013255/jewish/Temidin-uMusafim-Chapter-3.htm',
           'Daily incense is on the Golden Altar; withdrawal and supervisor cue precede it, clearance lasts until officiant exit.', 'ketores-service-and-smoke.md')
    source('KET_ORDER', 'H', 'Mishnah Yoma 3:5', 'https://www.sefaria.org/Mishnah_Yoma.3.5',
           'Morning incense is between blood and limbs; afternoon incense between limbs and libations.', 'ketores-service-and-smoke.md')
    source('YK', 'H', 'Avodat Yom HaKippurim 4:1-2',
           'https://www.chabad.org/library/article_cdo/aid/1062926/jewish/Avodat-Yom-haKippurim-Chapter-4.htm',
           'Inner incense is a separate Kohen Gadol service with its own garments, prerequisites and withdrawal.', 'ketores-service-and-smoke.md')
    source('SMOKE', 'H', 'Yoma 53a:4-11', 'https://www.sefaria.org/Yoma.53a.4-11',
           'Qualitative rising/spreading smoke description supplies no particle seconds or authenticated botanical identity.', 'ketores-service-and-smoke.md')
    source('HOSTING', 'H', 'Yoma 12a', 'https://www.sefaria.org/Yoma.12a',
           'Hosting has a legal context; do not assume ordinary paid hotel quests.', 'people-and-city.md')
    source('CHARITY', 'H', 'Mishnah Shekalim 5:6', 'https://www.sefaria.org/Mishnah_Shekalim.5.6',
           'Discreet assistance is described; no exact chamber in this measured model is identified.', 'people-and-city.md')
    source('ABUNDANCE', 'H', 'Melachim uMilchamot 12:2,5',
           'https://www.chabad.org/library/article_cdo/aid/1188357/jewish/Melachim-uMilchamot-Chapter-12.htm',
           'Future abundance and uncertainty require review before importing historical poverty as ambient scenery.', 'people-and-city.md')
    source('SUPPLY', 'H', 'Mishnah Shekalim 5:3-5; Maaser Sheni 5:2',
           'https://www.sefaria.org/Mishnah_Shekalim.5.3-5',
           'Temple supply administration differs from an ordinary city provisioning scene.', 'people-and-city.md')
    sources['DESIGN'] = dict(category='D', reference='Original authored scene specification', url=None,
                             claim='All named individuals, personality, pacing and logical connections are authored.',
                             dossier=None, verification='authored_here', futureApplication='illustrative_not_predicted')
    for key in ['KET_LOCATION', 'GATES', 'KITCHENS']:
        sources[key]['verification'] = 'primary_page_reopened_2026-09-07_plus_local_dossier'

    destinations = {}

    def measured(key, asset, zone, purpose, refs, xy=None):
        m = meshes[asset]
        bounds = m['expectedBoundsUnrealCm']
        point = (xy or [(bounds['min'][i] + bounds['max'][i]) / 2 for i in range(2)]) + [bounds['max'][2]]
        destinations[key] = dict(id=key, label=m['sourceName'], assetId=asset,
            nativeAsset='/Game/MikdashV3/Architecture/architecture_' + asset,
            boundsCm=bounds, candidateFloorPointCm=point, zone=zone, purpose=purpose,
            sourceIds=refs, mapping='measured_geometry_purpose_interpretation_needs_review',
            navigation='not_traced_not_path_validated', spawnAllowed=False)

    measured('outer_north', 'SM_0275_floor_Outer_N_vestibule_floor', 'outer_gate', 'Candidate ordinary arrival gate; not a mandated historical itinerary', ['GATES', 'DESIGN'])
    measured('outer_court', 'SM_0129_floor_Outer_court_floor', 'outer_court', 'Candidate waiting point outside inner court', ['ACCESS', 'DESIGN'], [5000, 0])
    measured('inner_north', 'SM_0571_floor_Inner_N_vestibule_floor', 'inner_gate', 'Candidate assigned kohen approach; access still reviewed', ['ACCESS', 'DESIGN'])
    measured('visitor_lane', 'SM_0130_floor_Inner_court_clear_floor', 'visitor_lane', 'Measured lane; permission and connecting north route remain separate', ['ACCESS', 'DESIGN'], [2100, 0])
    measured('priestly_court', 'SM_0071_floor_Ezras_Kohanim_floor', 'priestly_court', 'Assigned service staging; centroid not used because altar occupies center', ['ACCESS', 'DESIGN'], [1200, 1500])
    measured('ulam', 'SM_0145_floor_Ulam_clear_floor', 'ulam', 'Logical sanctuary approach; preserve twelve stair risers', ['ACCESS', 'DESIGN'])
    measured('heikhal', 'SM_0146_floor_Heichal_clear_floor', 'heikhal', 'Daily incense room; candidate point is not officiant pose or altar top', ['KET_LOCATION', 'DESIGN'], [-4400, 0])
    measured('kodesh', 'SM_0147_floor_Kodesh_clear_floor', 'kodesh', 'Excluded from ordinary-day routes; reserved separate reviewed YK module', ['YK', 'ACCESS'])
    measured('song_chamber', 'SM_0041_architecture_Song_chamber', 'priestly_court', 'Source-named song chamber; rehearsal scheduling is authored', ['DESIGN'])
    measured('priestly_room_candidate', 'SM_1265_floor_Priestly_room_floor', 'priestly_room', 'Candidate only: generic room label does not establish garment storage or lodging', ['GARMENTS', 'DESIGN'])
    unresolved = {
        'family_home': ('city', 'Priestly family home: residential allocation is sourced; exact model location absent', ['HOMES']),
        'host_home': ('city', 'Authored host meeting/home location outside precinct; no measured address', ['HOSTING', 'DESIGN']),
        'duty_lodging': ('unmapped', 'Earlier-Temple duty lodging, not identified in this future geometry', ['LODGING']),
        'mikvah_entry': ('unmapped', 'Opaque preparation entrance: no measured room ID established', ['SERVICE_IMMERSION', 'DESIGN']),
        'mikvah_exit': ('unmapped', 'Fully dressed exit; no measured room or bodily depiction', ['SERVICE_IMMERSION', 'DESIGN']),
        'garment_storage': ('unmapped', 'Review exact chamber; do not silently choose priestly_room_candidate', ['GARMENTS', 'GARMENT_PROFILE']),
        'laver': ('unmapped', 'Hands-and-feet preparation fixture anchor not established by this audit', ['HANDS_FEET']),
        'city_supply': ('city', 'Interpretive provisioning/ordinary food area outside precinct; no modern prices', ['SUPPLY', 'DESIGN']),
        'hospitality_help': ('city', 'Discrete practical assistance meeting; no public need labels', ['ABUNDANCE', 'DESIGN']),
        'historical_charity': ('unmapped', 'Separate earlier-Temple lesson only; no future beggar placement', ['CHARITY', 'ABUNDANCE']),
        'priestly_kitchen': ('unmapped', 'Sacred food preparation; exact mesh purpose not mapped', ['KITCHENS']),
    }
    for key, (zone, purpose, refs) in unresolved.items():
        destinations[key] = dict(id=key, label=key.replace('_', ' '), assetId=None, nativeAsset=None,
            boundsCm=None, candidateFloorPointCm=None, zone=zone, purpose=purpose, sourceIds=refs,
            mapping='unresolved_no_coordinate', navigation='unavailable', spawnAllowed=False)

    conditions = {}
    for key, description, refs in [
        ('scenario_reviewed', 'Selected future/historical interpretation approved for this activity', ['DESIGN']),
        ('location_reviewed', 'Exact destination purpose/zone reviewed, including unresolved rooms', ['ACCESS']),
        ('navigation_verified', 'Actual continuous nav route, collision, stairs and occupancy passed', ['DESIGN']),
        ('purpose_authorized', 'Current intended task permits this journey; no unrelated shortcut', ['ACCESS', 'REVERENCE']),
        ('preparation_reviewed', 'All independent fictional preparation states known and satisfied', ['PREP']),
        ('immersion_for_service', 'Service immersion complete without erasing other preparation requirements', ['SERVICE_IMMERSION']),
        ('assigned_kohen', 'Qualified kohen with this current service assignment', ['ROTATION', 'ACCESS']),
        ('garments_reviewed', 'Selected role/service garment profile reviewed and worn', ['GARMENTS', 'GARMENT_PROFILE']),
        ('hands_feet_ready', 'Separate sanctification state valid for this service', ['HANDS_FEET']),
        ('incense_assignment', 'Incense duty assignment and relevant prior-duty history reviewed', ['LOTTERY']),
        ('daily_withdrawal_complete', 'Heikhal and Ulam-to-altar withdrawal complete under reviewed geometry policy', ['KET_LOCATION']),
        ('supervisor_cue', 'Supervisor cue received for this cycle and service', ['KET_LOCATION']),
        ('daylight_confirmed', 'Actual modeled daylight cue confirmed, not arbitrary wall-clock hour', ['DAYLIGHT']),
        ('ordinary_day', 'Selected calendar profile is ordinary weekday, not special event', ['GATES', 'PM_ORDER']),
        ('privacy_ready', 'Closed opaque presentation ready; equivalent skip available', ['SERVICE_IMMERSION', 'DESIGN']),
        ('sacred_food_authorized', 'Correct role/item/task/consumption boundary independently checked', ['KITCHENS']),
        ('off_duty_clothes', 'Reviewed changing/storage transition complete before public return', ['GARMENTS', 'GARMENT_PROFILE']),
    ]:
        conditions[key] = dict(description=description, sourceIds=refs, default=None,
                               unknownResult='needs_review', falseResult='denied', authority='external_reviewed_adapter')

    phase_rows = [
        ('day_open', [], ['DESIGN']),
        ('preparation_window', ['day_open'], ['SERVICE_IMMERSION', 'DAYLIGHT']),
        ('assignments_ready', ['preparation_window'], ['LOTTERY', 'ROTATION']),
        ('daylight_confirmed', ['day_open'], ['DAYLIGHT']),
        ('morning_blood_completed', ['assignments_ready', 'daylight_confirmed'], ['KET_ORDER']),
        ('morning_incense_cue', ['morning_blood_completed'], ['KET_LOCATION', 'KET_ORDER']),
        ('morning_officiant_exit', ['morning_incense_cue'], ['KET_LOCATION']),
        ('morning_limbs_completed', ['morning_officiant_exit'], ['KET_ORDER', 'DESIGN']),
        ('between_services', ['morning_limbs_completed'], ['DESIGN']),
        ('afternoon_limbs_completed', ['between_services'], ['PM_ORDER', 'KET_ORDER']),
        ('afternoon_incense_cue', ['afternoon_limbs_completed'], ['KET_LOCATION', 'KET_ORDER']),
        ('afternoon_officiant_exit', ['afternoon_incense_cue'], ['KET_LOCATION']),
        ('afternoon_libations_completed', ['afternoon_officiant_exit'], ['KET_ORDER', 'DESIGN']),
        ('remaining_duties_reviewed', ['afternoon_libations_completed'], ['DESIGN']),
        ('return_home_window', ['remaining_duties_reviewed'], ['DESIGN']),
    ]
    phases = {key: dict(id=key, after=after, sourceIds=refs, absoluteClock=None,
        detail='Authored partial-order cue; not an exhaustive liturgical chronology or duration',
        dispatch='external_event_not_elapsed_seconds') for key, after, refs in phase_rows}
    common = ['scenario_reviewed', 'location_reviewed', 'navigation_verified', 'purpose_authorized']
    sacred = common + ['preparation_reviewed']
    priest = sacred + ['assigned_kohen', 'immersion_for_service', 'garments_reviewed', 'hands_feet_ready']
    routes = {}
    people = []

    def person(key, name, role, start, personality, steps, refs):
        location = start
        goals = []
        for index, (destination, action, phase, needs) in enumerate(steps):
            route_id = None
            if location != destination:
                route_id = key + '_leg_' + str(index + 1).zfill(2)
                routes[route_id] = dict(id=route_id, **{'from': location, 'to': destination},
                    resource='review_' + '_'.join(sorted([location, destination])), capacity=None,
                    timeoutSeconds=None, requiredConditions=list(dict.fromkeys(common + needs)),
                    sourceIds=list(dict.fromkeys(refs + ['DESIGN'])), waypointsCm=[],
                    connection='logical_only_no_straight_line_interpolation', enabled=False,
                    blockReason='needs_measured_path_and_access_review')
            goals.append(dict(id=key + '_goal_' + str(index + 1).zfill(2), destination=destination,
                action=action, phase=phase, routeId=route_id,
                requiredConditions=list(dict.fromkeys(['scenario_reviewed', 'location_reviewed'] + needs)),
                sourceIds=list(dict.fromkeys(refs + ['DESIGN'])), durationSeconds=None,
                completion='external_confirmed_action', evidenceCategory='D', nativeEnabled=False))
            location = destination
        people.append(dict(id=key, name=name, fictional=True, role=role, start=start,
            personality=personality, sourceIds=list(dict.fromkeys(refs + ['DESIGN'])), goals=goals,
            memory=['completed_goal_ids', 'relationships', 'assigned_duty', 'prior_incense_service', 'privacy_preferences'],
            personalityCannotOverride='access, preparation, service order or privacy',
            populationClaim='authored_cast_not_future_census'))

    def step(dest, action, phase='preparation_window', needs=None):
        return (dest, action, phase, needs or [])

    prep = [step('mikvah_entry', 'Read fictional preparation card; choose equivalent skip or opaque transition', needs=['preparation_reviewed', 'privacy_ready']),
            step('mikvah_exit', 'Return fully dressed; record only this modeled immersion step', needs=['privacy_ready']),
            step('garment_storage', 'Use reviewed service garment profile', needs=['immersion_for_service', 'garments_reviewed']),
            step('outer_north', 'Approach via candidate north gate', needs=sacred),
            step('outer_court', 'Wait for current duty assignment', 'assignments_ready', sacred),
            step('inner_north', 'Enter reviewed priestly route', 'assignments_ready', sacred + ['assigned_kohen']),
            step('laver', 'Record independent hands-and-feet sanctification', 'assignments_ready', sacred + ['assigned_kohen']),
            step('priestly_court', 'Join reviewed service staging', 'assignments_ready', priest)]
    am = [step('ulam', 'Approach sanctuary for assigned morning incense', 'morning_blood_completed', priest + ['incense_assignment']),
          step('heikhal', 'Wait for cue then dispatch Morning once for this cycle', 'morning_incense_cue', priest + ['incense_assignment', 'daily_withdrawal_complete', 'supervisor_cue']),
          step('ulam', 'Exit Heikhal; withdrawal remains until reviewed exit boundary', 'morning_officiant_exit', priest),
          step('priestly_court', 'Confirm officiant exit at reviewed boundary', 'morning_officiant_exit', priest)]
    pm = [step('ulam', 'Approach for separately assigned afternoon incense', 'afternoon_limbs_completed', priest + ['incense_assignment']),
          step('heikhal', 'Wait for cue then dispatch Afternoon once for this cycle', 'afternoon_incense_cue', priest + ['incense_assignment', 'daily_withdrawal_complete', 'supervisor_cue']),
          step('ulam', 'Exit; residual particles never decide entry permission', 'afternoon_officiant_exit', priest),
          step('priestly_court', 'Confirm reviewed officiant exit', 'afternoon_officiant_exit', priest)]
    home = [step('inner_north', 'Finish assigned duty and depart', 'remaining_duties_reviewed', priest),
            step('outer_court', 'Follow reviewed garment-change route', 'remaining_duties_reviewed', sacred),
            step('garment_storage', 'Change/store according to reviewed profile', 'remaining_duties_reviewed', ['garments_reviewed']),
            step('outer_north', 'Return to public life in off-duty clothes', 'return_home_window', ['off_duty_clothes']),
            step('family_home', 'Reconnect with fictional family; retain duty history', 'return_home_window', ['off_duty_clothes'])]
    person('kohen_am', 'Natan', 'Kohen', 'family_home',
           dict(speakingStyle='careful and concise', motivation='check each new assignment', relationship='knows host Tamar'),
           prep + am + [step('priestly_court', 'Wait for remaining reviewed duties; no automatic second incense assignment', 'between_services', priest)] + home,
           ['HOMES', 'ROTATION', 'SERVICE_IMMERSION', 'HANDS_FEET', 'GARMENTS', 'KET_LOCATION', 'KET_ORDER', 'LOTTERY'])
    person('kohen_pm', 'Avi', 'Kohen', 'duty_lodging',
           dict(speakingStyle='quiet and methodical', motivation='arrive prepared for afternoon assignment'),
           prep + [step('priestly_court', 'Remain available for reviewed duties; no invented idle service', 'between_services', priest)] + pm + home,
           ['LODGING', 'ROTATION', 'SERVICE_IMMERSION', 'HANDS_FEET', 'GARMENTS', 'KET_LOCATION', 'KET_ORDER'])
    person('pilgrim', 'Ezra', 'Visitor', 'host_home',
           dict(speakingStyle='curious first-time visitor', motivation='stay with group and understand preparation'),
           [step('mikvah_entry', 'Review previously authored purification history; no personal questionnaire', needs=['preparation_reviewed', 'privacy_ready']),
            step('mikvah_exit', 'Offscreen optional immersion lesson; retain outstanding requirements', needs=['privacy_ready']),
            step('outer_north', 'Meet group for meaningful visit', needs=sacred),
            step('outer_court', 'Wait for individually reviewed zone access', 'between_services', sacred),
            step('visitor_lane', 'Guided view only through reviewed route; never Heikhal entry', 'between_services', sacred),
            step('outer_court', 'Leave with group', 'between_services', sacred),
            step('outer_north', 'Retrace candidate weekday itinerary; opposite gate is not universally required', 'between_services', sacred),
            step('host_home', 'Return to host and remember meeting', 'between_services')], ['PREP', 'ACCESS', 'GATES', 'HOSTING'])
    person('host', 'Tamar', 'Visitor', 'host_home',
           dict(speakingStyle='welcoming and unhurried', motivation='remember guests and useful meeting places'),
           [step('city_supply', 'Collect ordinary provisions; no sacred-food substitution'),
            step('hospitality_help', 'Offer discreet directions and practical help', 'between_services'),
            step('host_home', 'Welcome returning group; no assumed paid lodging economy', 'return_home_window')], ['HOSTING', 'ABUNDANCE', 'SUPPLY'])
    person('supplier', 'Oren', 'Visitor', 'city_supply',
           dict(speakingStyle='organized and specific', motivation='keep ordinary supplies separate from sacred ingredients'),
           [step('city_supply', 'Prepare authored ordinary-food display outside precinct'),
            step('host_home', 'Deliver host provisions without sacred-precinct shortcut', 'between_services'),
            step('city_supply', 'Reconcile supplies; prices and future economy remain unset', 'return_home_window')], ['SUPPLY', 'REVERENCE'])
    person('levi', 'Yedidya', 'Levi', 'family_home',
           dict(speakingStyle='patient teacher', motivation='help colleagues prepare without blocking passage'),
           [step('outer_north', 'Join assigned rotation', needs=sacred),
            step('outer_court', 'Await reviewed route and assigned musical duty', 'assignments_ready', sacred),
            step('song_chamber', 'Authored rehearsal; service song/time needs separate review', 'between_services', sacred),
            step('outer_court', 'Finish reviewed duties', 'remaining_duties_reviewed', sacred),
            step('outer_north', 'Depart without unrelated shortcut', 'return_home_window', sacred),
            step('family_home', 'Return to authored household', 'return_home_window')], ['ROTATION', 'ACCESS', 'DESIGN'])

    return dict(schemaVersion=1, status='offline_inputs_native_review_required', sources=sources,
        destinations=destinations, conditions=conditions, phases=phases, routes=routes, identities=people,
        scenario=dict(id='ordinary_weekday_interpretive_v1', sourceCategory='D',
            futureInterpretationReviewed=False, literalClockTimes=False, defaultSpawnCount=0,
            exactFuturePopulation=None, innerEastGate='not_used_pending_Ezekiel46_mapping',
            completeJourneyMeaning='Authored departure-preparation-duty-return chains; unresolved destinations stay blocked',
            historicalCompleteness='Selected service anchors only; not all daily rites or all halachic exceptions'),
        incense=dict(events=[dict(id='DAILY_AM', runtimeService='Morning', trigger='morning_incense_cue',
                                 predecessor='morning_blood_completed', exit='morning_officiant_exit'),
                            dict(id='DAILY_PM', runtimeService='Afternoon', trigger='afternoon_incense_cue',
                                 predecessor='afternoon_limbs_completed', exit='afternoon_officiant_exit')],
            destination='heikhal', altarPlacementReceipt='SourceAssets/vessels-review/HeikhalKeilimV1/placement-20260907T143211410537Z.json',
            sourceIds=['KET_LOCATION', 'KET_ORDER', 'SMOKE'], executionKey=['cycle_id', 'service'],
            requirements=priest + ['incense_assignment', 'daily_withdrawal_complete', 'supervisor_cue'],
            withdrawalBoundary='needs_explicit_polygon_and_officiant_exit_review',
            smokeEmissionSeconds=None, smokeResidualSeconds=None,
            pause='freeze_shared_simulation_clock', load='restore_once_only_state_and_residual_remaining',
            reentry='never_retrigger', fastForward='evaluate_each_event_boundary_once',
            ordinaryDayInnerService=False, yomKippur='separate_unimplemented_profile_with_own_withdrawal'),
        privacy=dict(scene='opaque_door_or_neutral_fade_then_fully_dressed_exit', skipEquivalent=True,
            noPersonalQuestionnaire=True, excludes=['nude_body', 'wet_clothing_silhouette', 'underwater_body', 'changing_animation', 'intimate_audio'],
            completionEffect='record_modeled_step_only_no_universal_purity_grant', sourceIds=['SERVICE_IMMERSION', 'PREP', 'DESIGN']),
        charity=dict(futureDefault='practical_help_hospitality_not_ambient_destitution',
            historicalLessonDestination='historical_charity', historicalLessonEnabled=False,
            noPublicNeedLabels=True, noPovertyPopulationClaim=True, sourceIds=['CHARITY', 'ABUNDANCE', 'DESIGN']),
        vendorPolicy=dict(precinctRetail=False, prices=None, ordinaryAndSacredItemsSeparate=True,
            kitchenDestination='priestly_kitchen', kitchenIsCafe=False, sourceIds=['SUPPLY', 'KITCHENS', 'DESIGN']),
        adapter=dict(target='MikdashCrowd::Identity/Goal/Route in ResidentCrowdRuntime.h',
            roleMap=dict(Visitor='Visitor', Kohen='Kohen', Levi='Levi'),
            unresolvedDuration='Do not convert null to zero or fabricate ritual clocktimes; require an explicit authored pacing profile',
            externalChecks='Gate dispatch by named phase plus all three-valued conditions on every transition; runtime Access boolean alone is insufficient',
            locationMismatch='SourceNpcPointPermitted(Kohen) X>-48amot excludes Heikhal X=-88amot candidate; it is a placement envelope, not service authority',
            routeAdapter='No straight-line movement between endpoints. Resolve actual measured portals/stairs/nav corridors and resource capacity first',
            persistence='Stable IDs plus spec hash, phase events, role/preparation/garment facts, service cycle and prior duty history must survive save/load',
            currentRuntimeIntegration=False),
        inputFiles=[fingerprint(MANIFEST, 'SourceAssets/architecture-manifest.json')] +
                   [fingerprint(RESEARCH / name, 'unreal/Research/' + name) for name in
                    ['people-and-city.md', 'halacha-and-service.md', 'ketores-service-and-smoke.md']])


def require(condition, message):
    if not condition:
        raise ValueError(message)


def evaluate(required, facts):
    """A denied fact wins; missing/nonboolean facts remain unknown, never permit."""
    if any(facts.get(key) is False for key in required):
        return 'denied'
    if any(facts.get(key) is not True for key in required):
        return 'needs_review'
    return 'ready_for_external_validation'


def validate(spec):
    sources, destinations = spec['sources'], spec['destinations']
    conditions, phases, routes = spec['conditions'], spec['phases'], spec['routes']

    def refs(obj):
        require(bool(obj.get('sourceIds')), 'missing provenance')
        require(set(obj['sourceIds']) <= set(sources), 'unknown source reference')

    def needs(items):
        require(set(items) <= set(conditions), 'unknown condition')

    for key, d in destinations.items():
        require(d['id'] == key, 'destination key mismatch')
        refs(d)
        require(d['spawnAllowed'] is False, 'unreviewed destination enabled')
        if d['assetId'] is None:
            require(d['candidateFloorPointCm'] is None, 'unmapped destination has fabricated coordinate')
        else:
            require(d['assetId'] in json.loads(MANIFEST.read_text())['meshes'][0]['assetName'] or
                    d['assetId'] in {m['assetName'] for m in json.loads(MANIFEST.read_text())['meshes']}, 'missing measured asset')
            b, p = d['boundsCm'], d['candidateFloorPointCm']
            require(all(b['min'][i] <= p[i] <= b['max'][i] for i in range(3)), 'candidate outside bounds')
    for c in conditions.values():
        refs(c)
        require(c['default'] is None and c['unknownResult'] == 'needs_review', 'unsafe condition default')
    seen, visiting = set(), set()

    def visit(key):
        require(key in phases, 'unknown phase')
        require(key not in visiting, 'phase cycle')
        if key in seen:
            return
        visiting.add(key)
        for predecessor in phases[key]['after']:
            visit(predecessor)
        visiting.remove(key)
        seen.add(key)

    for key, phase in phases.items():
        refs(phase)
        require(phase['absoluteClock'] is None, 'invented clock time')
        visit(key)
    for key, route in routes.items():
        refs(route)
        needs(route['requiredConditions'])
        require(route['id'] == key, 'route key mismatch')
        require(route['from'] in destinations and route['to'] in destinations, 'unknown route destination')
        require(route['from'] != route['to'], 'self route')
        require(route['enabled'] is False and not route['waypointsCm'], 'unverified movement enabled')
        require('navigation_verified' in route['requiredConditions'], 'route missing navigation gate')
    ids = set()
    for person in spec['identities']:
        require(person['id'] not in ids, 'duplicate identity')
        ids.add(person['id'])
        refs(person)
        location, goal_ids = person['start'], set()
        require(location in destinations, 'unknown start')
        for goal in person['goals']:
            refs(goal)
            needs(goal['requiredConditions'])
            require(goal['id'] not in goal_ids, 'duplicate goal')
            goal_ids.add(goal['id'])
            require(goal['phase'] in phases, 'unknown goal phase')
            require(goal['destination'] in destinations, 'unknown goal destination')
            require(goal['durationSeconds'] is None and goal['nativeEnabled'] is False, 'unreviewed pacing/enabling')
            if location != goal['destination']:
                require(goal['routeId'] in routes, 'missing journey leg')
                route = routes[goal['routeId']]
                require(route['from'] == location and route['to'] == goal['destination'], 'disconnected journey leg')
            else:
                require(goal['routeId'] is None, 'stationary goal has route')
            require(goal['destination'] != 'kodesh', 'ordinary day enters Kodesh')
            if goal['destination'] == 'heikhal':
                require(person['role'] == 'Kohen' and 'assigned_kohen' in goal['requiredConditions'], 'unqualified Heikhal entry')
            location = goal['destination']
    needs(spec['incense']['requirements'])
    require(len(spec['incense']['events']) == 2 and not spec['incense']['ordinaryDayInnerService'], 'wrong ordinary incense profile')
    for e in spec['incense']['events']:
        require(e['predecessor'] in phases[e['trigger']]['after'], 'incense predecessor missing')
        require(e['exit'] in phases, 'incense exit missing')
    require(evaluate(['scenario_reviewed'], {}) == 'needs_review', 'unknown granted access')


def test(spec):
    validate(spec)
    checks = ['valid_spec', 'measured_asset_references', 'journey_continuity', 'phase_DAG', 'provenance_references']
    mutations = [
        ('missing_condition', lambda s: s['identities'][0]['goals'][0]['requiredConditions'].append('absent')),
        ('missing_source', lambda s: s['destinations']['heikhal']['sourceIds'].append('absent')),
        ('missing_destination', lambda s: s['routes'][next(iter(s['routes']))].update(to='absent')),
        ('phase_cycle', lambda s: s['phases']['day_open']['after'].append('return_home_window')),
        ('fabricated_mikvah', lambda s: s['destinations']['mikvah_entry'].update(candidateFloorPointCm=[0, 0, 0])),
        ('disconnected_route', lambda s: s['routes'][next(iter(s['routes']))].update(**{'from': 'heikhal'})),
        ('literal_clock', lambda s: s['phases']['morning_incense_cue'].update(absoluteClock='09:00')),
        ('missing_incense_predecessor', lambda s: s['phases']['morning_incense_cue'].update(after=[])),
        ('unsafe_condition_default', lambda s: s['conditions']['preparation_reviewed'].update(default=True)),
        ('unreviewed_route', lambda s: s['routes'][next(iter(s['routes']))].update(enabled=True)),
    ]
    for label, mutation in mutations:
        candidate = copy.deepcopy(spec)
        mutation(candidate)
        try:
            validate(candidate)
        except ValueError:
            checks.append('reject_' + label)
        else:
            raise ValueError('negative check unexpectedly passed: ' + label)
    for facts, expected in [({}, 'needs_review'), ({'a': True}, 'needs_review'),
                            ({'a': True, 'b': False}, 'denied'),
                            ({'a': True, 'b': 1}, 'needs_review'),
                            ({'a': True, 'b': True}, 'ready_for_external_validation')]:
        require(evaluate(['a', 'b'], facts) == expected, 'three-valued condition failure')
    checks.append('three_valued_unknown_denied_true_and_nonboolean')
    return dict(status='PASS_OFFLINE_ONLY', checks=checks, identities=len(spec['identities']),
        goals=sum(len(p['goals']) for p in spec['identities']), logicalRoutes=len(spec['routes']),
        measuredDestinations=sum(d['assetId'] is not None for d in spec['destinations'].values()),
        unresolvedDestinations=sum(d['assetId'] is None for d in spec['destinations'].values()),
        limits='No native navigation, source signoff, runtime binding, rendered people or packaged acceptance')


README = '''# Service-route inputs V1

Offline authored inputs for ordinary-day departure, preparation, service and return
journeys. Six fictional people are not a future census. No NPC is spawned here.

Run `python Scripts/build_service_route_spec.py` from the working project to build;
run the same command with `--check` to verify deterministic bytes and negative tests.
Only this script and this output directory are owned. No third-party imagery is copied.

`service-route-spec.json` is the integration contract. Each measured destination has
an exact frozen architecture asset ID and bounds. Its candidate floor point is an
offline bounding-box candidate, not a native floor hit or actor spawn. Home, mikvah,
garment-storage, laver, kitchen and charity anchors remain explicitly unresolved;
generic priestly rooms are not silently assigned these purposes. Logical legs have
no interpolated waypoints, capacities or durations and stay disabled. These omissions
are data the native integrator must resolve, not permission to skip route segments.

P=prophetic text, H=earlier Temple source, D=authored design. Every future application
requires review. Named phases encode partial order, not an exhaustive rite sequence.
All names, personalities, domestic routines and journey connections are authored.
The local research dossiers are preserved by input hashes; primary source URLs and
passages remain attached. GATES/KITCHENS and KET_LOCATION were additionally reopened.

Runtime adapter: map stable identities and route endpoints to ResidentCrowdRuntime,
but supply a reviewed authored pacing profile for its numeric Earliest/Duration fields.
Never map null to zero. Named service cues and three-valued conditions must gate every
transition separately. Its legacy kohen placement envelope excludes Heikhal and cannot
serve as the service access rule. A route timeout is navigation design, not ritual time.
Save/load must also preserve source/spec version, service-cycle events, preparation,
garment state and duty history. The current runtime does not acquire these by reading
this file automatically. Shared simulation pause and once-only service keys are required.

The two incense cues use distinct Morning/Afternoon services and predecessor phases.
Residual smoke never grants permission. Yom Kippur is excluded from ordinary journeys.
The mikvah presentation is opaque/offscreen with equivalent skip and a dressed return;
it records one modeled step without clearing unrelated preparation states.
Charity is a disabled historical lesson; default future activity is practical help.
Provisioning stays outside the precinct; sacred kitchens never become retail cafes.

`offline-validation.json` records structural and mutation checks. `frozen-files.json`
lists explicit SHA256/bytes for this generator, README, spec and verification receipt;
it excludes itself to avoid a recursive hash. `--check` also checks that manifest.

Next bounded task: read-only source-geometry portal/corridor audit for outer_north ->
outer_court -> visitor_lane and inner_north -> priestly_court -> Ulam; return actual
triangle/threshold references and stair landings without moving actors. Native owner
then traces and walks those corridors serially before enabling one dressed NPC.
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    spec = build()
    receipt = test(spec)
    require(encoded(spec) == encoded(build()), 'non-deterministic build')
    receipt['checks'].append('deterministic_rebuild')
    files = {'service-route-spec.json': encoded(spec), 'offline-validation.json': encoded(receipt),
             'README.md': README.encode('utf-8')}
    explicit = [fingerprint(Path(__file__), 'Scripts/build_service_route_spec.py')]
    for name, data in files.items():
        explicit.append(dict(path='SourceAssets/experience-review/service-routes/' + name,
                             bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
    files['frozen-files.json'] = encoded(dict(version=1, files=explicit, selfExcluded=True))
    if args.check:
        for name, data in files.items():
            require((OUT / name).read_bytes() == data, 'stale or changed output: ' + name)
    else:
        OUT.mkdir(parents=True, exist_ok=True)
        for name, data in files.items():
            (OUT / name).write_bytes(data)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == '__main__':
    main()
