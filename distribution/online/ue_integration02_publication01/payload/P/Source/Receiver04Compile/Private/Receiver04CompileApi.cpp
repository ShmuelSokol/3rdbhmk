#include "Native/receiver04/Bootstrap.h"
#include "IPixelStreaming2Module.h"
#include "PixelStreaming2VideoProducers.h"
#include <type_traits>

static_assert(!std::is_abstract_v<FOnlineInputGate>, "Installed PS2 input interface must be fully implemented");
static_assert(std::is_base_of_v<AMikdashPlayerController,AReceiver04Controller>);
static_assert(std::is_base_of_v<UCharacterMovementComponent,UReceiver04WalkerMovement>);
static_assert(std::is_base_of_v<UMikdashDoveMovement,UReceiver04DoveMovement>);

// Deliberately never registered/called. Compiles real public API expressions;
// this is not a runtime adapter and makes no ownership/authentication claim.
void Receiver04CompileMediaApi(IPixelStreaming2Module& Module,
    const FString& OwnedId, const FString& ApprovedUrl)
{
    auto Streamer = Module.CreateStreamer(OwnedId, TOptional<FString>(FString(TEXT("DefaultRtc"))));
    auto Producer = UE::PixelStreaming2::CreateVideoProducerBackBuffer();
    if (Streamer.IsValid() && Producer.IsValid())
    {
        auto Gate = FOnlineInputGate::Install(Streamer);
        Streamer->SetVideoProducer(Producer);
        Streamer->SetConnectionURL(ApprovedUrl);
        Streamer->StartStreaming();
        Streamer->StopStreaming();
        Module.DeleteStreamer(Streamer);
    }
}
