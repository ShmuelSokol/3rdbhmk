#pragma once
#include "AngularControllerPort.h"
namespace AngularWalkingStudy {
using namespace MikdashCrowd;using namespace MikdashCrowdGroups;
struct ScheduledTurn {
    AngularControllerStudy::Port Core;double Target=0;bool Ready=false,Held=false;
    MotionReservation DrainedLinear{},PreviousLinear{};
    bool HasHistory=false;
    void SnapshotLinear(double Now,const MotionReservation& OldLinear) {
        if(!HasHistory||Core.HistoryUpdatedAt!=static_cast<float>(Now)){
            Core.Snapshot(Now);PreviousLinear=OldLinear;HasHistory=true;
        }
        DrainedLinear=OldLinear;
    }
    int Starts=0,Commits=0;double LastVisible=0,LastTime=0;
    // Never change the fixed instance basis between Begin and scheduled Rebase.
    template<class Hold> bool Align(double Desired,double Now,const MotionReservation& Linear,Hold&& Reserve) {
        if(Core.Current.TurnDeltaDegrees!=0)return false;
        if((Ready&&Desired==Target)||Desired==Core.Current.Yaw)return true;
        const bool Keep=HasHistory&&Core.HistoryUpdatedAt==static_cast<float>(Now);
        const auto Saved=Core.Previous;
        if(!Core.Begin(Desired,Now,Linear,Reserve))return false;
        if(Keep)Core.Previous=Saved;else PreviousLinear=DrainedLinear;
        HasHistory=true;
        Target=Desired;Ready=false;Held=true;++Starts;return false;
    }
    double End(double Now)const {
        auto S=Core.Current;
        const double Raw=static_cast<double>(S.TurnStartGameTime)+std::abs(static_cast<double>(S.TurnDeltaDegrees))/90.;
        float E=static_cast<float>(Raw);if(E<Raw)E=std::nextafter(E,INFINITY);
        E=std::nextafter(E,INFINITY);return std::max(Now,static_cast<double>(E));
    }
    bool CanCommit(double Now,const MotionReservation& Hold)const {
        return Now>=Hold.End&&AngularControllerStudy::Complete(Core.Current,Now);
    }
    bool Commit(double Now,const MotionReservation& Hold) {
        if(!Held)return true;
        if(!CanCommit(Now,Hold))return false;
        const bool Keep=HasHistory&&Core.HistoryUpdatedAt==static_cast<float>(Now);
        const auto Saved=Core.Previous;
        if(!Keep)PreviousLinear=Hold;
        if(!Core.Rebase(Now))return false;
        if(Keep)Core.Previous=Saved;HasHistory=true;
        Held=false;Ready=true;++Commits;return true;
    }
    double Visible(double Now)const{return WrapDegrees(Core.Current.Yaw+AngularControllerStudy::Angle(Core.Current,static_cast<float>(Now)));}
    Vec2 PreviousPosed(Vec2 Rest,Vec2 OldVatDelta,Vec2 NewVatDelta,double PreviousTime,
                       const MotionReservation& CurrentLinear)const {
        // Preserve legacy linear drift alongside the appended angular history.
        // The frozen angular math reconstructs the complete posed point/basis;
        // CD0..25's corresponding old/current linear segment supplies root drift.
        const bool Old=PreviousTime<Core.HistoryUpdatedAt;
        const Vec2 BasisRoot=Old?Core.Previous.Root:Core.Current.Root;
        const Vec2 Root=(Old?PreviousLinear:CurrentLinear).At(PreviousTime);
        return AngularControllerStudy::PreviousPosedWorld(Core,Rest,OldVatDelta,NewVatDelta,PreviousTime)+Root-BasisRoot;
    }
};
}
