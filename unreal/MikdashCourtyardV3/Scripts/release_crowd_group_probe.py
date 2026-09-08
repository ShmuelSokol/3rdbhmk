"""Read-only PIE observations of stable visitor parties; no map/save mutation."""
import math

def snapshot(crowd):
    rows=[]
    for index in range(crowd.get_total_instance_count()):
        result=crowd.get_visitor_social_state(index)
        # UE Python can consume the return bool as an optional-success wrapper.
        if result is None:continue
        assert isinstance(result,tuple) and len(result) in (4,5), 'Unexpected social-state API: '+repr(result)
        if len(result)==5:
            if not result[0]:continue
            _,party,member,position,standing=result
        else:party,member,position,standing=result
        assert isinstance(party,int) and isinstance(member,int) and isinstance(standing,bool),'Invalid social-state field types'
        rows.append(dict(index=index,party=party,member=member,position=[position.x,position.y,position.z],standing=standing))
    assert len(rows)==crowd.get_seeded_agent_count(),'Valid social states disagree with seed count'
    return dict(agents=rows,groups=crowd.get_visitor_group_count(),grouped=crowd.get_grouped_visitor_count(),
                pausedGroups=crowd.get_paused_visitor_group_count(),
                partyStates={str(p):crowd.get_visitor_group_state(p) for p in {r['party'] for r in rows if r['party']>=0}},
                individuals=crowd.get_individual_visitor_count(),refusedGroups=crowd.get_refused_group_count(),
                sweeps=crowd.get_group_sweeps_last_frame(),rejections=crowd.get_group_rejected_moves_last_frame(),
                waits=crowd.get_group_wait_visits_last_frame(),budget=crowd.get_editor_property('update_budget_per_frame'),
                maximumWalkSpeed=crowd.get_editor_property('max_walk_speed_cm_per_second'))

def assess(samples):
    assert len(samples)>=8,'Need sustained observations'
    first=samples[0]['state'];last=samples[-1]['state']
    assert first['grouped']>first['individuals']>0,'Need majority grouped with occasional individuals'
    parties={}
    for person in first['agents']:
        if person['party']>=0:parties.setdefault(person['party'],[]).append(person)
    assert len(parties)==first['groups'] and sum(map(len,parties.values()))==first['grouped']
    assert all(2<=len(p)<=6 for p in parties.values()),'Unexpected party size'
    identities=[(p['index'],p['party'],p['member']) for p in first['agents']]
    min_gap=float('inf');max_step=0
    for sample in samples:
        current=sample['state']
        assert [(p['index'],p['party'],p['member']) for p in current['agents']]==identities,'Party membership changed'
        assert current['sweeps']<=current['budget'],'Obstacle sweeps exceed update budget'
        # Read-only review of240 people; runtime uses bounded spatial hashing.
        for i,a in enumerate(current['agents']):
            for b in current['agents'][i+1:]:
                if abs(a['position'][2]-b['position'][2])<50:
                    min_gap=min(min_gap,math.hypot(a['position'][0]-b['position'][0],a['position'][1]-b['position'][1]))
    moved=sum(math.dist(a['position'],b['position'])>50 for a,b in zip(first['agents'],last['agents']) if a['party']>=0 and not a['standing'])
    assert moved>0,'No walking group member moved meaningfully'
    for previous,current in zip(samples,samples[1:]):
        interval=current['seconds']-previous['seconds']
        for a,b in zip(previous['state']['agents'],current['state']['agents']):
            displacement=math.dist(a['position'],b['position']);max_step=max(max_step,displacement)
            assert displacement<=interval*first['maximumWalkSpeed']*1.15+150,'Possible unsampled teleport or excessive movement'
    assert min_gap>=79.9,'Visitor spacing below the configured80cm in sampled states'
    return dict(groups=first['groups'],grouped=first['grouped'],individuals=first['individuals'],
                movingGroupMembers=moved,minimumSampledGapCm=min_gap,maxSampleDisplacementCm=max_step,
                maxSweepsPerFrame=max(s['state']['sweeps'] for s in samples),pausedGroupsAtEnd=last['pausedGroups'],
                scope='Sampled native stable membership, movement, spacing and trace budget; not long-route, all-frame collision, visual quality or performance acceptance')
