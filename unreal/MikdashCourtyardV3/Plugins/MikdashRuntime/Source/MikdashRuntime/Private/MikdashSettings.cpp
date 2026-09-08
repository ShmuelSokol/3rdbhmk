#include "MikdashSettings.h"

#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/GameViewportClient.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "GameFramework/GameUserSettings.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Kismet/KismetInternationalizationLibrary.h"
#include "Misc/App.h"
#include "Sound/SoundClass.h"

DEFINE_LOG_CATEGORY_STATIC(LogMikdashFrontEnd, Log, All);

namespace MS = MikdashSettings;

// ---------------------------------------------------------------------------
// FMikdashSettingsRecord
// ---------------------------------------------------------------------------

MS::FSettings FMikdashSettingsRecord::ToMath() const
{
    MS::FSettings Out;
    Out.Version = Version;
    Out.Preset = static_cast<MS::EPreset>(Preset);
    Out.Groups.ViewDistance = ViewDistance;
    Out.Groups.Shadows = Shadows;
    Out.Groups.GlobalIllumination = GlobalIllumination;
    Out.Groups.Reflections = Reflections;
    Out.Groups.PostProcess = PostProcess;
    Out.Groups.Textures = Textures;
    Out.Groups.Effects = Effects;
    Out.Groups.Foliage = Foliage;
    Out.Groups.Shading = Shading;
    Out.ResolutionX = ResolutionX;
    Out.ResolutionY = ResolutionY;
    Out.WindowMode = static_cast<MS::EWindowMode>(WindowMode);
    Out.FrameRateCap = FrameRateCap;
    Out.UpscaleMethod = static_cast<MS::EUpscaleMethod>(UpscaleMethod);
    Out.UpscaleQuality = static_cast<MS::EUpscaleQuality>(UpscaleQuality);
    Out.ScreenPercentage = ScreenPercentage;
    Out.FieldOfView = FieldOfView;
    Out.MouseSensitivity = MouseSensitivity;
    Out.bInvertY = bInvertY;
    Out.MasterVolume = MasterVolume;
    Out.MusicVolume = MusicVolume;
    Out.EffectsVolume = EffectsVolume;
    Out.VoiceVolume = VoiceVolume;
    Out.bSubtitles = bSubtitles;
    Out.SubtitleScale = SubtitleScale;
    Out.Language = static_cast<MS::ELanguage>(Language);
    Out.TextScale = TextScale;
    Out.bCameraShake = bCameraShake;
    Out.bHeadBob = bHeadBob;
    Out.bVignetteOnMovement = bVignetteOnMovement;
    Out.bSnapTurn = bSnapTurn;
    Out.SnapTurnDegrees = SnapTurnDegrees;
    Out.ColourVision = static_cast<MS::EColourVision>(ColourVision);
    Out.SprintMode = static_cast<MS::EHoldMode>(SprintMode);
    Out.CrouchMode = static_cast<MS::EHoldMode>(CrouchMode);
    return Out;
}

void FMikdashSettingsRecord::FromMath(const MS::FSettings& In)
{
    Version = In.Version;
    Preset = static_cast<int32>(In.Preset);
    ViewDistance = In.Groups.ViewDistance;
    Shadows = In.Groups.Shadows;
    GlobalIllumination = In.Groups.GlobalIllumination;
    Reflections = In.Groups.Reflections;
    PostProcess = In.Groups.PostProcess;
    Textures = In.Groups.Textures;
    Effects = In.Groups.Effects;
    Foliage = In.Groups.Foliage;
    Shading = In.Groups.Shading;
    ResolutionX = In.ResolutionX;
    ResolutionY = In.ResolutionY;
    WindowMode = static_cast<int32>(In.WindowMode);
    FrameRateCap = In.FrameRateCap;
    UpscaleMethod = static_cast<int32>(In.UpscaleMethod);
    UpscaleQuality = static_cast<int32>(In.UpscaleQuality);
    ScreenPercentage = In.ScreenPercentage;
    FieldOfView = In.FieldOfView;
    MouseSensitivity = In.MouseSensitivity;
    bInvertY = In.bInvertY;
    MasterVolume = In.MasterVolume;
    MusicVolume = In.MusicVolume;
    EffectsVolume = In.EffectsVolume;
    VoiceVolume = In.VoiceVolume;
    bSubtitles = In.bSubtitles;
    SubtitleScale = In.SubtitleScale;
    Language = static_cast<int32>(In.Language);
    TextScale = In.TextScale;
    bCameraShake = In.bCameraShake;
    bHeadBob = In.bHeadBob;
    bVignetteOnMovement = In.bVignetteOnMovement;
    bSnapTurn = In.bSnapTurn;
    SnapTurnDegrees = In.SnapTurnDegrees;
    ColourVision = static_cast<int32>(In.ColourVision);
    SprintMode = static_cast<int32>(In.SprintMode);
    CrouchMode = static_cast<int32>(In.CrouchMode);
}

// ---------------------------------------------------------------------------
// FMikdashPalette
// ---------------------------------------------------------------------------

FMikdashPalette FMikdashPalette::Make(MS::EColourVision Mode)
{
    FMikdashPalette P;
    switch (Mode)
    {
    case MS::EColourVision::Deuteranope:
    case MS::EColourVision::Protanope:
        // Red and green collapse together. Move the accent to a warm yellow and the
        // warning to a blue that no red-green deficiency confuses with it, and keep a
        // large lightness gap between the two.
        P.Accent = FLinearColor(0.94f, 0.80f, 0.28f, 1.0f);
        P.Selected = FLinearColor(1.00f, 0.92f, 0.55f, 1.0f);
        P.Warning = FLinearColor(0.20f, 0.48f, 0.86f, 1.0f);
        P.Disabled = FLinearColor(0.40f, 0.40f, 0.42f, 1.0f);
        break;
    case MS::EColourVision::Tritanope:
        // Blue and yellow collapse. Keep the accent warm-red and the warning magenta.
        P.Accent = FLinearColor(0.88f, 0.45f, 0.35f, 1.0f);
        P.Selected = FLinearColor(1.00f, 0.66f, 0.56f, 1.0f);
        P.Warning = FLinearColor(0.84f, 0.24f, 0.60f, 1.0f);
        P.Disabled = FLinearColor(0.40f, 0.40f, 0.42f, 1.0f);
        break;
    case MS::EColourVision::Off:
    default:
        break;
    }
    return P;
}

// ---------------------------------------------------------------------------
// UMikdashSettingsSubsystem
// ---------------------------------------------------------------------------

void UMikdashSettingsSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    Load();
    ApplyAll();
}

void UMikdashSettingsSubsystem::Deinitialize()
{
    OnSettingsChanged.Clear();
    Super::Deinitialize();
}

UMikdashSettingsSubsystem* UMikdashSettingsSubsystem::Get(const UObject* WorldContext)
{
    if (!WorldContext) { return nullptr; }
    const UWorld* World = GEngine ? GEngine->GetWorldFromContextObject(WorldContext, EGetWorldErrorMode::ReturnNull) : nullptr;
    UGameInstance* Instance = World ? World->GetGameInstance() : nullptr;
    return Instance ? Instance->GetSubsystem<UMikdashSettingsSubsystem>() : nullptr;
}

FMikdashSettingsRecord UMikdashSettingsSubsystem::GetRecord() const
{
    FMikdashSettingsRecord Record;
    Record.FromMath(Current);
    return Record;
}

FMikdashPalette UMikdashSettingsSubsystem::GetPalette() const
{
    return FMikdashPalette::Make(Current.ColourVision);
}

float UMikdashSettingsSubsystem::GetLookMultiplier() const { return MS::SensitivityMultiplier(Current.MouseSensitivity); }
float UMikdashSettingsSubsystem::GetPitchSign() const { return Current.bInvertY ? -1.0f : 1.0f; }
bool  UMikdashSettingsSubsystem::IsHeadBobEnabled() const { return Current.bHeadBob; }
bool  UMikdashSettingsSubsystem::IsCameraShakeEnabled() const { return Current.bCameraShake; }
bool  UMikdashSettingsSubsystem::IsMovementVignetteEnabled() const { return Current.bVignetteOnMovement; }
bool  UMikdashSettingsSubsystem::IsSnapTurnEnabled() const { return Current.bSnapTurn; }
float UMikdashSettingsSubsystem::GetSnapTurnDegrees() const { return Current.SnapTurnDegrees; }
bool  UMikdashSettingsSubsystem::IsSprintToggle() const { return Current.SprintMode == MS::EHoldMode::Toggle; }
bool  UMikdashSettingsSubsystem::IsCrouchToggle() const { return Current.CrouchMode == MS::EHoldMode::Toggle; }
bool  UMikdashSettingsSubsystem::AreSubtitlesEnabled() const { return Current.bSubtitles; }
float UMikdashSettingsSubsystem::GetTextScale() const { return Current.TextScale; }
float UMikdashSettingsSubsystem::GetSubtitleScale() const { return Current.SubtitleScale; }
bool  UMikdashSettingsSubsystem::IsRightToLeft() const { return Current.Language == MS::ELanguage::Hebrew; }

float UMikdashSettingsSubsystem::GetMusicGain() const
{
    return MS::VolumeToGain(Current.MusicVolume) * MS::VolumeToGain(Current.MasterVolume);
}
float UMikdashSettingsSubsystem::GetEffectsGain() const
{
    return MS::VolumeToGain(Current.EffectsVolume) * MS::VolumeToGain(Current.MasterVolume);
}
float UMikdashSettingsSubsystem::GetVoiceGain() const
{
    return MS::VolumeToGain(Current.VoiceVolume) * MS::VolumeToGain(Current.MasterVolume);
}

void UMikdashSettingsSubsystem::Set(const MS::FSettings& In)
{
    Current = In;
    Commit();
}

void UMikdashSettingsSubsystem::Commit()
{
    MS::Clamp(Current);
    ApplyAll();
    Save();
    OnSettingsChanged.Broadcast();
}

void UMikdashSettingsSubsystem::Preview()
{
    MS::Clamp(Current);
    ApplyAll();
    OnSettingsChanged.Broadcast();
}

void UMikdashSettingsSubsystem::ResetToDefaults()
{
    Current = MS::MakeDefaults();
    Commit();
}

bool UMikdashSettingsSubsystem::Load()
{
    bLoadedFromDisk = false;
    bMigratedOnLoad = false;
    LoadedVersion = 0;

    Current = MS::MakeDefaults();

    if (!UGameplayStatics::DoesSaveGameExist(SaveSlot, SaveUserIndex))
    {
        UE_LOG(LogMikdashFrontEnd, Log, TEXT("No settings save in slot '%s'; using defaults."), *SaveSlot);
        return false;
    }

    UMikdashSettingsSave* Loaded = Cast<UMikdashSettingsSave>(UGameplayStatics::LoadGameFromSlot(SaveSlot, SaveUserIndex));
    if (!Loaded)
    {
        // A file that exists but will not deserialise is treated as absent rather than
        // as a reason to refuse to boot.
        UE_LOG(LogMikdashFrontEnd, Warning, TEXT("Settings slot '%s' exists but did not load; using defaults."), *SaveSlot);
        return false;
    }

    LoadedVersion = Loaded->Record.Version;
    MS::FSettings Incoming = Loaded->Record.ToMath();
    bMigratedOnLoad = MS::Migrate(Incoming);
    Current = Incoming;
    bLoadedFromDisk = true;

    UE_LOG(LogMikdashFrontEnd, Log, TEXT("Loaded settings v%d from '%s'%s."),
           LoadedVersion, *SaveSlot, bMigratedOnLoad ? TEXT(" (migrated)") : TEXT(""));
    return true;
}

bool UMikdashSettingsSubsystem::Save()
{
    UMikdashSettingsSave* Payload = Cast<UMikdashSettingsSave>(
        UGameplayStatics::CreateSaveGameObject(UMikdashSettingsSave::StaticClass()));
    if (!Payload) { return false; }

    Payload->Record.FromMath(Current);
    Payload->WrittenBy = FString::Printf(TEXT("MikdashRuntime front end, settings v%d"), MS::CurrentVersion);

    const bool bSaved = UGameplayStatics::SaveGameToSlot(Payload, SaveSlot, SaveUserIndex);
    if (!bSaved)
    {
        UE_LOG(LogMikdashFrontEnd, Warning, TEXT("Failed to write settings to slot '%s'."), *SaveSlot);
    }
    return bSaved;
}

void UMikdashSettingsSubsystem::ApplyAll()
{
    ApplyGraphics();
    ApplyAudio();
    ApplyLanguage();
    ApplyCameraEverywhere();
}

void UMikdashSettingsSubsystem::ApplyGraphics()
{
    if (!bApplyGraphicsToEngine) { return; }

    UGameUserSettings* User = GEngine ? GEngine->GetGameUserSettings() : nullptr;
    if (User)
    {
        User->SetViewDistanceQuality(Current.Groups.ViewDistance);
        User->SetShadowQuality(Current.Groups.Shadows);
        User->SetGlobalIlluminationQuality(Current.Groups.GlobalIllumination);
        User->SetReflectionQuality(Current.Groups.Reflections);
        User->SetPostProcessingQuality(Current.Groups.PostProcess);
        User->SetTextureQuality(Current.Groups.Textures);
        User->SetVisualEffectQuality(Current.Groups.Effects);
        User->SetFoliageQuality(Current.Groups.Foliage);
        User->SetShadingQuality(Current.Groups.Shading);

        User->SetScreenResolution(FIntPoint(Current.ResolutionX, Current.ResolutionY));
        User->SetFullscreenMode(static_cast<EWindowMode::Type>(static_cast<int32>(Current.WindowMode)));
        User->SetFrameRateLimit(Current.FrameRateCap);

        // false: do not let a -ResX style command line silently win over what the
        // visitor just chose in the menu.
        User->ApplySettings(false);
    }

    // Upscaling. UE has no UGameUserSettings API for this, so it goes through the
    // console variables the renderer actually reads.
    //   r.AntiAliasingMethod : 0 none, 1 FXAA, 2 TAA, 3 MSAA, 4 TSR
    int32 AntiAliasing = 2;
    int32 TemporalUpsampling = 0;
    switch (Current.UpscaleMethod)
    {
    case MS::EUpscaleMethod::Off:                     AntiAliasing = 2; TemporalUpsampling = 0; break;
    case MS::EUpscaleMethod::TemporalAA:              AntiAliasing = 2; TemporalUpsampling = 1; break;
    case MS::EUpscaleMethod::TemporalSuperResolution: AntiAliasing = 4; TemporalUpsampling = 1; break;
    case MS::EUpscaleMethod::Spatial:                 AntiAliasing = 1; TemporalUpsampling = 0; break;
    }

    IConsoleManager& Console = IConsoleManager::Get();
    if (IConsoleVariable* CVar = Console.FindConsoleVariable(TEXT("r.AntiAliasingMethod")))
    {
        CVar->Set(AntiAliasing, ECVF_SetByGameSetting);
    }
    if (IConsoleVariable* CVar = Console.FindConsoleVariable(TEXT("r.TemporalAA.Upsampling")))
    {
        CVar->Set(TemporalUpsampling, ECVF_SetByGameSetting);
    }
    if (IConsoleVariable* CVar = Console.FindConsoleVariable(TEXT("r.ScreenPercentage")))
    {
        CVar->Set(Current.ScreenPercentage, ECVF_SetByGameSetting);
    }
}

void UMikdashSettingsSubsystem::ApplyAudio()
{
    // Master: a global multiplier on everything the engine mixes. Needs no asset.
    FApp::SetVolumeMultiplier(MS::VolumeToGain(Current.MasterVolume));

    // The three sub-buses only move if a SoundClass has been named in config. Setting
    // Properties.Volume on a SoundClass is a live change; sounds already playing pick
    // it up on their next update.
    struct FBus { const FSoftObjectPath& Path; float Volume; };
    const FBus Buses[] = {
        { MusicSoundClass,   MS::VolumeToGain(Current.MusicVolume) },
        { EffectsSoundClass, MS::VolumeToGain(Current.EffectsVolume) },
        { VoiceSoundClass,   MS::VolumeToGain(Current.VoiceVolume) },
    };
    for (const FBus& Bus : Buses)
    {
        if (Bus.Path.IsNull()) { continue; }
        if (USoundClass* Class = Cast<USoundClass>(Bus.Path.TryLoad()))
        {
            Class->Properties.Volume = Bus.Volume;
        }
    }
}

void UMikdashSettingsSubsystem::ApplyLanguage()
{
    const FString Culture = (Current.Language == MS::ELanguage::Hebrew) ? HebrewCulture : EnglishCulture;
    if (Culture.IsEmpty()) { return; }
    if (UKismetInternationalizationLibrary::GetCurrentLanguage() == Culture) { return; }
    UKismetInternationalizationLibrary::SetCurrentLanguageAndLocale(Culture, /*SaveToConfig*/ false);
}

void UMikdashSettingsSubsystem::ApplyCameraEverywhere()
{
    const UGameInstance* Instance = GetGameInstance();
    if (!Instance) { return; }
    for (const ULocalPlayer* Player : Instance->GetLocalPlayers())
    {
        if (Player)
        {
            ApplyCameraTo(Player->PlayerController);
        }
    }
}

void UMikdashSettingsSubsystem::ApplyCameraTo(APlayerController* Controller)
{
    if (!Controller) { return; }

    // Hor+ on the real viewport aspect, so a 21:9 monitor shows more to the sides
    // rather than cropping the top and bottom of the court.
    float Aspect = MS::ReferenceAspect;
    if (const ULocalPlayer* Player = Controller->GetLocalPlayer())
    {
        if (const UGameViewportClient* Viewport = Player->ViewportClient)
        {
            FVector2D Size = FVector2D::ZeroVector;
            Viewport->GetViewportSize(Size);
            if (Size.X > 0.0 && Size.Y > 0.0)
            {
                Aspect = static_cast<float>(Size.X / Size.Y);
            }
        }
    }
    const float Fov = MS::HorPlusFovForAspect(Current.FieldOfView, Aspect);

    // Prefer the pawn's own camera component: setting it leaves the camera manager
    // free to blend, which matters because the front end retargets the view.
    bool bSetOnComponent = false;
    if (const APawn* Pawn = Controller->GetPawn())
    {
        TArray<UCameraComponent*> Cameras;
        Pawn->GetComponents<UCameraComponent>(Cameras);
        for (UCameraComponent* Camera : Cameras)
        {
            if (Camera)
            {
                Camera->SetFieldOfView(Fov);
                bSetOnComponent = true;
            }
        }
    }
    if (!bSetOnComponent && Controller->PlayerCameraManager)
    {
        Controller->PlayerCameraManager->SetFOV(Fov);
    }

    // Motion sickness: stop anything currently shaking. This cannot prevent a future
    // shake that some other system starts -- that system has to read
    // IsCameraShakeEnabled() -- so the honest description of this line is "stops the
    // shakes that are running", not "disables camera shake".
    if (!Current.bCameraShake && Controller->PlayerCameraManager)
    {
        Controller->PlayerCameraManager->StopAllCameraShakes(true);
    }

    // Legacy look scaling, applied only when the project still uses it. Projects on
    // Enhanced Input should read GetLookMultiplier()/GetPitchSign() instead.
    PRAGMA_DISABLE_DEPRECATION_WARNINGS
    const float Look = GetLookMultiplier();
    Controller->SetDeprecatedInputYawScale(Look * 2.5f);
    Controller->SetDeprecatedInputPitchScale(Look * 2.5f * GetPitchSign());
    PRAGMA_ENABLE_DEPRECATION_WARNINGS
}
