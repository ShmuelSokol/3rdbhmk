#pragma once
#include <cmath>
#include <cstdint>
#include <functional>
#include <string>

namespace MikdashOnline {
// Trusted IPC decoder must bound frame <=4096 bytes and every identity <=128.
// It fills these typed fields only after authenticating the exact owned process.
struct Owner {
    std::string session_id, process_key, stream_id, save_prefix, settings_slot;
    double expires_at = 0; // wire identity, NOT the native clock deadline
    bool operator==(const Owner& b) const {
        return session_id==b.session_id && process_key==b.process_key && stream_id==b.stream_id &&
            save_prefix==b.save_prefix && settings_slot==b.settings_slot && expires_at==b.expires_at;
    }
};
struct Packet {
    int version=1;
    Owner owner;
    uint64_t sequence=0;
    std::string operation, connection_id, action;
    double x=0,y=0;
};
struct Ack {
    int version=1;
    Owner owner;
    uint64_t sequence=0;
    std::string operation, connection_id, status="rejected";
};
struct InputSink {
    virtual ~InputSink() = default;
    virtual bool Release() = 0;
    virtual bool Apply(const std::string& action, double x, double y) = 0;
};

// Single owned UE process, game thread only, no queue and no network.
// Bootstrapped nativeDeadline is conservative and immutable, <=24h from now.
// Host must tick on real time even while gameplay is paused; stalled process is
// killed by the future external watchdog. ACK follows actual sink application.
class SessionBridge {
    Owner owner; InputSink& sink; std::function<double()> clock;
    double deadline, last=-1, inputUntil=0;
    uint64_t sequence=0;
    std::string connection;
    bool opened=false, closed=false;
    static bool Id(const std::string& s) { return !s.empty() && s.size()<=128; }
    double Now() {
        const double n=clock();
        if (!std::isfinite(n) || n<0 || n<last || n>1099511627776.0) {
            closed=true; sink.Release(); return -1;
        }
        last=n; return n;
    }
public:
    SessionBridge(Owner o, double nativeDeadline, InputSink& s, std::function<double()> c)
        : owner(o), sink(s), clock(c), deadline(nativeDeadline) {
        const double n=Now();
        closed=n<0 || !std::isfinite(deadline) || deadline<=n || deadline-n>86400 ||
            !Id(owner.session_id)||!Id(owner.process_key)||!Id(owner.stream_id)||
            !Id(owner.save_prefix)||!Id(owner.settings_slot)||!std::isfinite(owner.expires_at)||
            owner.expires_at<0||owner.expires_at>1099511627776.0;
    }
    void Tick() {
        const double n=Now();
        if (closed || n<0 || n>=deadline) { closed=true; sink.Release(); connection.clear(); }
        else if (!connection.empty() && n>=inputUntil) sink.Release();
    }
    Ack Handle(const Packet& p) {
        Ack a{1,p.owner,p.sequence,p.operation,p.connection_id,"rejected"};
        const double n=Now();
        if (p.version!=1 || !(p.owner==owner) || p.sequence<=sequence || p.sequence>9007199254740991ULL ||
            p.connection_id.size()>128 || p.operation.size()>16 || p.action.size()>16) return a;
        const bool cleanup=p.operation=="release" || p.operation=="close";
        if (n<0 || (!cleanup && (closed || n>=deadline))) { Tick(); return a; }
        // Consume sequence before side effects, including failed ones. Retries use
        // a fresh sequence; input is never replayed after an ambiguous timeout.
        sequence=p.sequence;
        bool applied=false;
        if (p.operation=="open" && !opened && p.connection_id.empty()) {
            applied=sink.Release(); opened=applied;
        } else if (p.operation=="bind" && opened && connection.empty() && Id(p.connection_id)) {
            applied=sink.Release();
            if (applied) { connection=p.connection_id; inputUntil=n+2; }
        } else if (p.operation=="release" && (connection.empty() || p.connection_id==connection)) {
            applied=sink.Release(); connection.clear();
        } else if (p.operation=="close") {
            closed=true; connection.clear(); applied=sink.Release();
        } else if (p.operation=="input" && opened && !connection.empty() && p.connection_id==connection &&
                   std::isfinite(p.x) && std::isfinite(p.y) && std::abs(p.x)<=1 && std::abs(p.y)<=1) {
            const bool axes=p.action=="move" || p.action=="look";
            const bool button=p.action=="interact" || p.action=="pause" || p.action=="mute";
            if (axes || (button && p.x==0 && p.y==0)) {
                // Check again at actual application, not IPC enqueue time.
                const double fresh=Now();
                if (fresh>=0 && fresh<deadline && !closed) {
                    applied=sink.Apply(p.action,p.x,p.y); inputUntil=fresh+2;
                }
            }
        }
        if (!applied) { closed=true; sink.Release(); }
        else a.status="applied";
        return a;
    }
};
}
