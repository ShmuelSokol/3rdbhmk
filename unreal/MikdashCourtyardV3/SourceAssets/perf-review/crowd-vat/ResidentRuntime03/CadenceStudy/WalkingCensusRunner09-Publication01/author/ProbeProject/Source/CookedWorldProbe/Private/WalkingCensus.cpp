#include "CookedWorldPort.h"
#include "Dom/JsonObject.h"
#include "Misc/LexToString.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
namespace CookedWorldPort {
FString DescribeWalkingCapture(const FCapture& C){
 auto R=MakeShared<FJsonObject>();
 R->SetStringField(TEXT("scope"),TEXT("bounded selected-box cooked-shape observation; not world certification"));
 R->SetBoolField(TEXT("diagnosticOnly"),C.DiagnosticOnly);
 R->SetBoolField(TEXT("observedEnumerationExhausted"),C.ObservedBoxEnumerationExhausted);
 R->SetBoolField(TEXT("publishedEnumerationExhausted"),C.PublishedBoxEnumerationExhausted);
 R->SetBoolField(TEXT("worldComplete"),false);R->SetBoolField(TEXT("obstaclesComplete"),false);
 R->SetNumberField(TEXT("refusal"),static_cast<uint8>(C.Refusal));
 // Identities remain exact decimal strings, avoiding JSON binary64 truncation.
 R->SetStringField(TEXT("agent"),LexToString(C.OwnerAgent));R->SetStringField(TEXT("incarnation"),LexToString(C.OwnerIncarnation));
 R->SetNumberField(TEXT("profile"),C.Profile);R->SetStringField(TEXT("walkingFilter"),C.WalkingFilter);
 R->SetNumberField(TEXT("payloadVisits"),C.PayloadVisits);R->SetNumberField(TEXT("nodeVisits"),C.NodeVisits);
 R->SetNumberField(TEXT("boundsTests"),C.BoundsTests);R->SetNumberField(TEXT("sourceFaceTests"),C.SourceFaceTests);
 R->SetNumberField(TEXT("exhaustedMeshes"),C.ExhaustedMeshes);
 R->SetBoolField(TEXT("candidateCopyAvailable"),C.Data.Get()!=nullptr);
 if(C.Data){R->SetNumberField(TEXT("candidateVertices"),C.Data->vertices);R->SetNumberField(TEXT("candidateFaces"),C.Data->faces);}
 TArray<TSharedPtr<FJsonValue>> Rows;
 for(const auto& S:C.Shapes){auto V=MakeShared<FJsonObject>();
  V->SetStringField(TEXT("component"),S.ComponentPath);V->SetStringField(TEXT("componentUid"),LexToString(S.Component));
  V->SetStringField(TEXT("instance"),LexToString(S.Instance));V->SetStringField(TEXT("shapeOrdinal"),LexToString(S.Ordinal));
  V->SetBoolField(TEXT("queryEnabled"),S.Query);V->SetNumberField(TEXT("classification"),static_cast<uint8>(S.Classification));
  V->SetNumberField(TEXT("geometryType"),S.GeometryType);V->SetNumberField(TEXT("objectChannel"),S.ObjectChannel);
  V->SetStringField(TEXT("blockChannels"),LexToString(S.BlockChannels));V->SetStringField(TEXT("overlapChannels"),LexToString(S.OverlapChannels));
  Rows.Add(MakeShared<FJsonValueObject>(V));
 }
 R->SetArrayField(TEXT("observedShapes"),Rows);
 FString Text;const auto Writer=TJsonWriterFactory<>::Create(&Text);
 if(!FJsonSerializer::Serialize(R,Writer))return FString();return Text;
}
}
