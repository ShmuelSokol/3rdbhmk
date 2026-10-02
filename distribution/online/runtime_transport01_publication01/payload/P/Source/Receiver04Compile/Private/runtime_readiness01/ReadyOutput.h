#pragma once
#include "../runtime_settings05/NativeLease.h"
namespace MikdashOnline::Adoption01 { class FParsedAdmission; }
namespace MikdashOnline::Readiness01 {
TSharedPtr<const Adoption01::FParsedAdmission> TakeParsedAdmission();
bool Admit(const TArray<uint8>& Body,double Now,Receiver03::Bootstrap& Out,double StartupDeadline);
bool SignalStopped(const Owner& ExactOwner,double AdmissionDeadline,double OwnerDeadline);
bool Close();
}
