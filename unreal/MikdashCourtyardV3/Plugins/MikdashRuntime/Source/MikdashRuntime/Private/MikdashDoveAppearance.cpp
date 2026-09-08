#include "MikdashDoveAppearance.h"
#include "Components/SceneComponent.h"

AMikdashDoveAppearance::AMikdashDoveAppearance()
{
    PrimaryActorTick.bCanEverTick = false;
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
    SetHidden(true);
    SetActorEnableCollision(false);
    // Not editor-only: it must survive cooking because it carries the dove mesh references.
}
