#pragma once
#include "CoreMinimal.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "CurvePacket09.h"
#include "PairProtocol.h"
#include "Misc/ScopeLock.h"
#include "PairedVatComponent.generated.h"

// Physical admission is a separate REQUIRED host. Caller retains this shared
// lease and session through destroy/quarantine. No callback here releases it.
struct FPairedVatItem {CurvedVat09::Publication Packet; FTransform PreviousLocal;};
class IPairedVatLease {
public:
 virtual ~IPairedVatLease()=default;
 // Validate exact full batch, both histories, component mapping, measured swept
 // body/support/world epoch+immutable lease and irrevocable reservation coverage.
 // A false/uncertain acquisition is quarantined with this lease retained; there
 // is no post-acquisition early HOLD or automatic reservation release.
 // Must also attest exclusive enrollment: no outside Set/Add/Remove/transform writer.
 virtual bool ValidateAndHold(const UInstancedStaticMeshComponent&,const TArray<FPairedVatItem>&,uint64 Generation,uint64 Serial)=0;
 virtual bool MaterialConsumes9001PrefixOnTransport10001(const UInstancedStaticMeshComponent&) const=0;
};
struct FPairedVatSnapshot {
 TArray<FPairedVatItem> Items;
 TArray<Paired10::Wire> Wires;
 TArray<FTransform> Current,Previous;
 TSharedPtr<IPairedVatLease,ESPMode::ThreadSafe> Lease;
};
struct FPairedVatSession {
 FCriticalSection Lock;
 Paired10::Protocol Protocol;
 FPairedVatSnapshot Pending,LastObserved;
 // Bounded retained journal. No automatic lease/history eviction on render ACK.
 TArray<FPairedVatSnapshot> Retained;
 explicit FPairedVatSession(uint64 Generation):Protocol(Generation){}
 // Quarantine never clears any packet, history or reservation-owning lease.
 void Close(){FScopeLock Guard(&Lock);Protocol.Quarantine();}
};
enum class EPairedVatSubmit {Hold,Pending,Quarantined};

// Project-owned non-Nanite ISM proxy alternative. Stock HISM proxy is final.
// Fixed topology, bounded<=64 batch; no production density/performance claim.
UCLASS(NotBlueprintable,Transient)
class PAIREDRENDERHOST_API UPairedVatComponent final : public UInstancedStaticMeshComponent {
 GENERATED_BODY()
public:
 UPairedVatComponent();
 // Initialize instances/material in isolated owner BEFORE registering; caller
 // retains Session handle before first submission, including on failure.
 TSharedPtr<FPairedVatSession,ESPMode::ThreadSafe> GetRetentionHandle() const{return Session;}
 EPairedVatSubmit Submit(const TArray<FPairedVatItem>& Items,uint64 Serial,TSharedPtr<IPairedVatLease,ESPMode::ThreadSafe> Lease);
 bool PollConsumed(uint64 Generation,uint64 Serial);
 virtual bool RequiresGameThreadEndOfFrameUpdates() const override{return true;}
protected:
 virtual void SendRenderInstanceData_Concurrent() override;
 virtual void OnRegister() override;
 virtual void OnUnregister() override;
 virtual void DestroyRenderState_Concurrent() override;
 virtual FPrimitiveSceneProxy* CreateStaticMeshSceneProxy(Nanite::FMaterialAudit&,bool bCreateNanite) override;
private:
 TSharedPtr<FPairedVatSession,ESPMode::ThreadSafe> Session;
};
