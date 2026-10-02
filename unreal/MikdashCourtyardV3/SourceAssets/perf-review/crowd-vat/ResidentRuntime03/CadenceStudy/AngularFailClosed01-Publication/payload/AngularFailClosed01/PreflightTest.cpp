#include "RotatingEnvelope.h"
#include <iostream>
#include <iomanip>
using namespace MikdashCrowd;using namespace MikdashCrowdGroups;
int main(){std::cout<<std::setprecision(17);
for(int Members:{2,3,6})for(int TerminalBudget:{48,17})for(double Scale:{1.,.92,1.08,0.})for(bool TerminalStart:{false,true}){
struct P{Vec2 Anchor;double Yaw=0;};P People[6];const Vec2 SeedAnchor{400,-100};
for(int I=0;I<Members;++I){People[I].Anchor=SeedAnchor+Offset(I,13,47,120);
            if(TerminalStart&&Members==2&&TerminalBudget==48&&I==0) {People[I].Anchor={864.46278065540162,452.59594546197394};People[I].Yaw=-84.44125391380669;}
            if(TerminalStart&&Members==2&&TerminalBudget==48&&I==1) {People[I].Anchor={878.46298790686126,540.63783535343327};People[I].Yaw=-88.213687213697455;}
            if(TerminalStart&&Members==2&&TerminalBudget==17&&I==0) {People[I].Anchor={854.2521943754665,460.67915373000648};People[I].Yaw=-93.000000156462193;}
            if(TerminalStart&&Members==2&&TerminalBudget==17&&I==1) {People[I].Anchor={878.87948909459544,543.18002935040249};People[I].Yaw=-179.4682838978288;}
            if(TerminalStart&&Members==3&&TerminalBudget==48&&I==0) {People[I].Anchor={866.0184030482659,450.9520904432847};People[I].Yaw=-84.619574652272718;}
            if(TerminalStart&&Members==3&&TerminalBudget==48&&I==1) {People[I].Anchor={391.46070914735481,38.111174326725425};People[I].Yaw=-122.68224992078925;}
            if(TerminalStart&&Members==3&&TerminalBudget==48&&I==2) {People[I].Anchor={287.88643097387887,-136.49594744523159};People[I].Yaw=-108.64046542041913;}
            if(TerminalStart&&Members==3&&TerminalBudget==17&&I==0) {People[I].Anchor={410.78599086880047,-89.821773758782157};People[I].Yaw=-136.66057226527838;}
            if(TerminalStart&&Members==3&&TerminalBudget==17&&I==1) {People[I].Anchor={392.96814122439241,36.560109189424232};People[I].Yaw=-129.7333573631158;}
            if(TerminalStart&&Members==3&&TerminalBudget==17&&I==2) {People[I].Anchor={862.3038293471825,456.31036344761327};People[I].Yaw=-133.38065078346676;}
            if(TerminalStart&&Members==6&&TerminalBudget==48&&I==0) {People[I].Anchor={843.31135972634581,591.87732659553308};People[I].Yaw=-122.64918724785468;}
            if(TerminalStart&&Members==6&&TerminalBudget==48&&I==1) {People[I].Anchor={392.83387519558954,40.331771454327303};People[I].Yaw=-122.55897400548338;}
            if(TerminalStart&&Members==6&&TerminalBudget==48&&I==2) {People[I].Anchor={290.44587453279172,-145.44045805809222};People[I].Yaw=-125.89151241292066;}
            if(TerminalStart&&Members==6&&TerminalBudget==48&&I==3) {People[I].Anchor={270.25302985344956,-17.752390168353593};People[I].Yaw=-125.37153220655807;}
            if(TerminalStart&&Members==6&&TerminalBudget==48&&I==4) {People[I].Anchor={177.57377272962091,-157.87240248812279};People[I].Yaw=-141.11035263713316;}
            if(TerminalStart&&Members==6&&TerminalBudget==48&&I==5) {People[I].Anchor={151.22620051051547,3.9567110798885814};People[I].Yaw=-123.98595885946403;}
            if(TerminalStart&&Members==6&&TerminalBudget==17&&I==0) {People[I].Anchor={865.12068416853776,454.17640070795989};People[I].Yaw=-130.00676239224597;}
            if(TerminalStart&&Members==6&&TerminalBudget==17&&I==1) {People[I].Anchor={864.9346925101288,574.36201157432095};People[I].Yaw=-85.487194358473488;}
            if(TerminalStart&&Members==6&&TerminalBudget==17&&I==2) {People[I].Anchor={288.93691664069689,-144.64280441121045};People[I].Yaw=-120.40006710761938;}
            if(TerminalStart&&Members==6&&TerminalBudget==17&&I==3) {People[I].Anchor={270.75922470439531,-17.701067807939324};People[I].Yaw=-126.87525400367628;}
            if(TerminalStart&&Members==6&&TerminalBudget==17&&I==4) {People[I].Anchor={167.45049700860847,-151.85415147993365};People[I].Yaw=-110.25202686125922;}
            if(TerminalStart&&Members==6&&TerminalBudget==17&&I==5) {People[I].Anchor={153.53989574997991,7.4521687420803477};People[I].Yaw=-123.88777261618941;}
}
double Minimum=1e9;int A=-1,B=-1;
for(int I=0;I<Members;++I){const double R=50*(Scale>0?Scale:(I%2?.92:1.08));for(int J=I+1;J<Members+2;++J){const Vec2 Q=J<Members?People[J].Anchor:Vec2{800,400.+(J-Members)*120};const double R2=J<Members?50*(Scale>0?Scale:(J%2?.92:1.08)):50;const double Margin=Length(People[I].Anchor-Q)-std::max(80.,R+R2);if(Margin<Minimum){Minimum=Margin;A=I;B=J;}}}
std::cout<<Members<<','<<TerminalBudget<<','<<Scale<<','<<TerminalStart<<','<<Minimum<<','<<A<<','<<B<<'\n';}}
