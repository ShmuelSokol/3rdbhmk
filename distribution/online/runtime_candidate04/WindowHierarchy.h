#pragma once
#include "CoreMinimal.h"
#include "Widgets/SWindow.h"

namespace MikdashOnline::RuntimeCandidate04 {
// Consumes the actual Slate top-level array and SWindow hierarchy. Any immediate
// child implies an unauthorized subtree; hidden children are also refused.
inline bool IsSoleChildlessWindow(const TArray<TSharedRef<SWindow>>& Roots,
                                  const TSharedPtr<SWindow>& Expected) {
    return Expected.IsValid()&&Roots.Num()==1&&Roots[0]==Expected.ToSharedRef()&&
        Expected->GetChildWindows().Num()==0;
}
}
