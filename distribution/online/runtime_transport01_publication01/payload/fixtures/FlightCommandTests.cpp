#include "FlightCommand.h"
#include <cstdio>
using MikdashOnline::Flight01::Command;
int Checks=0,Failures=0;
void check(bool V){++Checks;if(!V)++Failures;}
int main(){
    double at=0;bool handoff=false;
    {Command c;check(c.Queue(1,2,3,4,100,100.5));check(c.Consume(1,2,3,100.1));
     check(c.Complete(1,2,3,100.2,true));check(c.Take(4,1,2,3,100.3,at,handoff));check(!handoff);}
    // Actual flight and rollback-to-same-object both invalidate the native pawn
    // incarnation. Object sameness/outcome is checked by real controller hooks.
    for(int rollback=0;rollback<2;++rollback){Command c;
     check(c.Queue(1,2,3,4,100,100.5));check(c.Consume(1,2,3,100.1));
     check(!c.Begin(1,2,3,100.11)); // nested callback before last-branch fence
     check(c.Fence(1,2,3,100.12));check(c.Begin(1,2,3,100.13));
     check(!c.Begin(1,2,3,100.14));check(c.Complete(1,3,4,100.2,true));
     check(c.Take(4,1,3,4,100.3,at,handoff));check(handoff);check(at==100.12);
     check(!c.Take(4,1,3,4,100.31,at,handoff));}
    {Command c;check(c.Queue(1,2,3,4,100,100.5));check(c.Consume(1,2,3,100.1));
     check(!c.Complete(1,2,3,100.2,false));check(!c.Take(4,1,2,3,100.3,at,handoff));}
    {Command c;check(c.Queue(1,2,3,4,100,100.5));check(c.Consume(1,2,3,100.1));
     check(!c.Complete(9,2,3,100.2,true));}
    {Command c;check(c.Queue(1,2,3,4,100,100.5));check(c.Consume(1,2,3,100.1));
     check(c.Fence(1,2,3,100.12));check(c.Begin(1,2,3,100.13));
     check(!c.Complete(1,2,4,100.2,true));}
    {Command c;check(c.Queue(1,2,3,4,100,100.5));check(c.Consume(1,2,3,100.1));
     check(!c.Complete(1,2,3,100.5,true));}
    {Command c;check(c.Queue(1,2,3,4,100,100.5));check(c.Consume(1,2,3,100.1));
     check(c.Complete(1,2,3,100.2,true));check(!c.Take(4,1,2,3,100.5,at,handoff));}
    {Command c;check(c.Queue(1,2,3,4,100,100.5));c.Cancel();
     check(c.Queue(1,2,5,5,100.2,100.6));check(!c.Consume(1,2,3,100.3));
     check(c.Consume(1,2,5,100.3));c.Abort();check(!c.Complete(1,2,5,100.4,true));}
    {Command c;check(c.Queue(1,2,3,4,100,100.5));check(c.Consume(1,2,3,100.1));
     check(!c.Fence(1,2,3,100.09));}
    std::printf("FlightCommand actual header: checks=%d failures=%d\n",Checks,Failures);
    return Failures?1:0;
}
