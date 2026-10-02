"""Bounded structural checks of actual UE source; NOT C++/UHT/native validation."""
from pathlib import Path
import json,hashlib
p=Path(__file__).resolve().parent
c=(p/'Source/PairedRenderHost/Private/PairedVatComponent.cpp').read_text()
h=(p/'Source/PairedRenderHost/Public/PairedVatComponent.h').read_text()
a=json.loads((p/'assessment.json').read_text())
checks=0
def check(x):
 global checks
 checks+=1
 assert x,checks
for needle in ['UpdateInstances_RenderThread','GetInstanceSceneDataBuffers()','V.InstanceCustomData','V.PrevInstanceToPrimitiveRelative','Paired10::HasToken(Actual,77,P.Serial)','Paired10::HasToken(Actual,81,P.Generation)','Paired10::ExactWire','Same(Current','Same(Previous','Tx->Protocol.Finish(Both)','Tx->Retained.Add','Tx->Retained.Num()>=64','DestroyRenderState_Concurrent','OnUnregister','IsRenderStateDirty()','IsRegistered()','CheckPSOPrecachingAndBoostPriority()','!Lease','ValidateAndHold','MaterialConsumes9001PrefixOnTransport10001','Matched==0','Matched==S.Wires.Num()']:
 check(needle in c)
check(c.index('if(Tx->Retained.Num()>=64)')<c.index('Tx->Protocol.Begin(Serial,true)')<c.index('Tx->Retained.Add(Tx->Pending)')<c.index('const bool Held=Lease->ValidateAndHold'))
check('if(!Held||Session!=Tx||Tx->Protocol.Closed' in c)
check('return EPairedVatSubmit::Hold' not in c[c.index('const bool Held=Lease->ValidateAndHold'):c.index('bool UPairedVatComponent::PollConsumed')])
check('if(bCreateNanite||!IsInGameThread()||CheckPSOPrecachingAndBoostPriority()||!EnsureSafeGeneration())return nullptr;' in c)
check('FRenderCommandFence' not in c)
check(c.index('SetCustomData(I')<c.index('Both=Both&&BatchUpdateInstancesTransforms')<c.index('Tx->Protocol.Finish(Both)'))
check(c.index('FInstancedStaticMeshSceneProxy::UpdateInstances_RenderThread')<c.index('const FInstanceSceneDataBuffers* B=GetInstanceSceneDataBuffers()'))
check('RequiresGameThreadEndOfFrameUpdates() const override{return true;}' in h)
check('if(Session->Protocol.Closed||Session->Protocol.State==Paired10::Phase::Writing)return;' in c)
check('virtual bool ValidateAndHold' in h and 'Serial)=0;' in h)
check(a['transport']['floats']==85 and a['transport']['compatibleExistingComponents']==False)
check(a['nativeRuns']==a['ubtRuns']==0 and not a['stockHismExactAckSupported'])
check(hashlib.sha256((p/'Source/PairedRenderHost/Public/CurvePacket09.h').read_bytes()).hexdigest()=='14c17c09d1b016d93a288bedfaa8acd4074f1547e2adce6c0894c1136523960d')
check('Current.Orthogonalize();Previous.Orthogonalize();' not in c)
check('FinishExpectedTransform(Current,V.PrimitiveToRelativeWorld.IsScaleNonUniform())' in c)
check('FinishExpectedTransform(Previous,V.PrimitiveToRelativeWorld.IsScaleNonUniform())' in c)
check('Paired10::MayRenew(Session->Protocol,Session->Retained.Num())' in c)
check('RetiredSessions.Add(Session);' in c)
check('RequiresGameThreadEndOfFrameRecreate() const override{return true;}' in h)
create=c[c.index('void UPairedVatComponent::CreateRenderState_Concurrent'):c.index('void UPairedVatComponent::OnUnregister')]
check(create.index('EnsureSafeGeneration();')<create.index('Super::CreateRenderState_Concurrent(Context);'))
check('Same(V.PrimitiveToRelativeWorld,FRenderTransform::Identity)' in c)
print(json.dumps({'sourceChecks':checks,'failures':0,'scope':'Structural source decisions only. UE-facing module uncompiled/render unproved.'}))
