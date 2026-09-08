#include "SaveSceneIdentity.h"
#include <iostream>
#include <limits>
namespace
{
int Checks=0, Failures=0;
void Expect(bool Passed,const char* Name)
{ ++Checks; if (!Passed) { ++Failures; std::cerr << "FAIL " << Name << '\n'; } }
}
int main()
{
    using namespace MikdashSaveScene;
    const std::string Map = "/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough";
    const std::string CandidateMap = "/Game/MikdashV3/Amah48Candidate/Maps/Walkthrough";
    MikdashSceneUnits::Frame Legacy, Selected;
    Selected.CoordinateRevision = MikdashSceneUnits::Revision::Selected48V1;
    MikdashSave::FSaveRecord Old;
    Old.MapName = "UEDPIE_3_Walkthrough";
    Old.CompletedTourStops = {"outer-court","menorah"};
    Old.CurrentTourStop = "menorah";
    Old.UnlockedCodexEntries = {"paroches"};
    Old.PlayTimeSeconds = 900;
    Old.Photo.Aperture = 5.6f;
    Old.PlayerTransform.X=-15442.86; Old.PlayerTransform.Y=11962.316; Old.PlayerTransform.Z=712.4;
    MikdashSave::FOptionValue Setting;
    Setting.Key="settings.MasterVolume"; Setting.Type=MikdashSave::EOptionType::Float; Setting.FloatValue=.75f;
    Old.Options.push_back(Setting);
    Expect(Evaluate(Old,&Legacy,Map)==Decision::RestoreLegacyPosition,"absent metadata preserves same legacy scene");
    Expect(Evaluate(Old,&Selected,CandidateMap)==Decision::DifferentLayout,"old50 never implicitly restores into48");
    Expect(Evaluate(Old,nullptr,Map)==Decision::InvalidCurrentIdentity,"invalid/duplicate descriptor never becomes50");
    auto Shifted=Legacy; Shifted.FixedOrigin.Z=1;
    Expect(Evaluate(Old,&Shifted,Map)==Decision::DifferentLayout,"legacy absent metadata rejects shifted origin");
    auto EmptyMap=Old; EmptyMap.MapName.clear();
    Expect(Evaluate(EmptyMap,&Legacy,Map)==Decision::RestoreLegacyPosition,"oldest absent map retains legacy compatibility");
    Identity Saved; Saved.Frame=Legacy; Saved.MapPackage=Map; Saved.HasWalkingPosition=true;
    auto Current=Old;
    Expect(Store(Current,&Saved),"add metadata without changing old container");
    Expect(Current.Options.size()==2 && Current.Options[0].Key==Setting.Key
        && Current.Options[0].FloatValue==Setting.FloatValue,"all nonmetadata settings retained");
    Expect(Evaluate(Current,&Legacy,Map)==Decision::RestorePosition,"new same-layout position restorable");
    Expect(Evaluate(Current,&Selected,Map)==Decision::DifferentLayout,"same map changed unit refused");
    Expect(Evaluate(Current,&Shifted,Map)==Decision::DifferentLayout,"same map changed origin refused");
    Expect(Evaluate(Current,&Legacy,CandidateMap)==Decision::DifferentLayout,"same unit different full map path refused");
    const auto Before=MikdashSave::Encode(Current);
    (void)Evaluate(Current,&Selected,CandidateMap);
    Expect(MikdashSave::Encode(Current)==Before,"identity decision never changes save bytes or arbitrary city coordinates");
    MikdashSave::FSaveRecord RoundTrip;
    MikdashSave::FMigrationReport Report;
    Expect(MikdashSave::Decode(Before.data(),Before.size(),RoundTrip,Report)==MikdashSave::ESaveDecodeError::Ok,
        "actual CRC protected save roundtrip");
    Expect(Evaluate(RoundTrip,&Legacy,Map)==Decision::RestorePosition,"metadata survives production save encoder and decoder");
    Expect(RoundTrip.CompletedTourStops==Old.CompletedTourStops && RoundTrip.UnlockedCodexEntries==Old.UnlockedCodexEntries
        && RoundTrip.CurrentTourStop==Old.CurrentTourStop && RoundTrip.PlayTimeSeconds==Old.PlayTimeSeconds
        && RoundTrip.Photo.Aperture==Old.Photo.Aperture,"nonpositional progress survives metadata roundtrip");
    Saved.Frame=Selected; Saved.MapPackage=CandidateMap;
    Saved.Frame.FixedOrigin={123.12345678901234,-234.98765432109876,.00000000000031};
    Identity Parsed;
    Expect(Decode(Encode(Saved),Parsed) && SameFrame(Parsed.Frame,Saved.Frame),"17 digit origin serialization preserves identity exactly");
    auto SelectedRecord=Old; Expect(Store(SelectedRecord,&Saved),"selected identity stored");
    Expect(Evaluate(SelectedRecord,&Saved.Frame,CandidateMap)==Decision::RestorePosition,"selected same-layout resume preserved");
    Saved.HasWalkingPosition=false; Store(SelectedRecord,&Saved);
    Expect(Evaluate(SelectedRecord,&Saved.Frame,CandidateMap)==Decision::NoWalkingPosition,"dove/camera save cannot become walking teleport");
    auto Invalid=Old; Store(Invalid,nullptr);
    Expect(Evaluate(Invalid,&Legacy,Map)==Decision::InvalidSavedIdentity,"invalid descriptor explicitly saved as invalid");
    Invalid=Current; Invalid.Options.push_back(Invalid.Options.back());
    Expect(Evaluate(Invalid,&Legacy,Map)==Decision::InvalidSavedIdentity,"duplicate scene identity fails closed");
    Invalid=Current; Invalid.Options.back().Type=MikdashSave::EOptionType::Bool;
    Expect(Evaluate(Invalid,&Legacy,Map)==Decision::InvalidSavedIdentity,"wrong metadata type refused");
    const char* Bad[] = {
        "2|Legacy50.v1|0|0|0|/Game/Map|1", "1|FutureUnit.v1|0|0|0|/Game/Map|1",
        "1|Legacy50.v1|nan|0|0|/Game/Map|1", "1|Legacy50.v1|0 |0|0|/Game/Map|1",
        "1|Legacy50.v1|0|0|0|/Game/Map|yes", "1|Legacy50.v1|0|0|0|/Game/Map|1|extra",
        "1|Legacy50.v1|0|0|0|Map|1", "1|Legacy50.v1|0|0|0|/Game/Map"
    };
    for (const auto* Text : Bad)
    {
        Invalid=Current; Invalid.Options.back().StringValue=Text;
        Expect(Evaluate(Invalid,&Legacy,Map)==Decision::InvalidSavedIdentity,"malformed/future metadata refuses spatial restore");
    }
    auto BadCurrent=Legacy; BadCurrent.SchemaVersion=2;
    Expect(Evaluate(Current,&BadCurrent,Map)==Decision::InvalidCurrentIdentity,"unsupported world schema refused");
    BadCurrent=Legacy; BadCurrent.FixedOrigin.X=std::numeric_limits<double>::infinity();
    Expect(Evaluate(Current,&BadCurrent,Map)==Decision::InvalidCurrentIdentity,"nonfinite world origin refused");
    auto Full=Old; Full.Options.assign(MikdashSave::MaxOptionCount,Setting);
    const auto FullBefore=MikdashSave::Encode(Full);
    Expect(!Store(Full,&Saved) && MikdashSave::Encode(Full)==FullBefore,"full extension list refuses without discarding settings");
    Expect(Store(Current,&Saved) && Current.Options.size()==2,"metadata replacement does not accumulate duplicate keys");
    std::cout << "SaveSceneIdentity: " << Checks << " checks, " << Failures << " failures\n";
    return Failures ? 1 : 0;
}
