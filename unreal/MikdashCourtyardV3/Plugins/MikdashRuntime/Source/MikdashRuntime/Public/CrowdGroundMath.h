#pragma once
#include <cmath>
#include <cstddef>
#include <limits>

namespace MikdashCrowdGround {
struct Point { double X,Y,Z; };
struct Triangle { Point A,B,C; };
struct DeckRect { double MinX,MinY,MaxX,MaxY,Z; };
inline double Missing() { return std::numeric_limits<double>::quiet_NaN(); }

template<std::size_t N>
inline double DeckHeight(const DeckRect (&Rects)[N], double X, double Y)
{
    double Z=Missing();
    if(!std::isfinite(X)||!std::isfinite(Y)) return Z;
    for(const auto& R:Rects)
        if(X>=R.MinX && X<=R.MaxX && Y>=R.MinY && Y<=R.MaxY)
            if(!std::isfinite(Z)||R.Z>Z) Z=R.Z;
    return Z;
}

template<std::size_t N>
inline double TerrainHeight(const Triangle (&Faces)[N], double X, double Y)
{
    double Z=Missing();
    if(!std::isfinite(X)||!std::isfinite(Y)) return Z;
    for(const auto& T:Faces)
    {
        const auto& A=T.A;const auto& B=T.B;const auto& C=T.C;
        const double D=(B.Y-C.Y)*(A.X-C.X)+(C.X-B.X)*(A.Y-C.Y);
        if(!std::isfinite(D)||std::abs(D)<1e-8) continue;
        const double U=((B.Y-C.Y)*(X-C.X)+(C.X-B.X)*(Y-C.Y))/D;
        const double V=((C.Y-A.Y)*(X-C.X)+(A.X-C.X)*(Y-C.Y))/D;
        const double W=1-U-V;
        if(U>=-1e-8 && V>=-1e-8 && W>=-1e-8)
        {
            const double Candidate=U*A.Z+V*B.Z+W*C.Z;
            if(std::isfinite(Candidate)&&(!std::isfinite(Z)||Candidate>Z)) Z=Candidate;
        }
    }
    return Z;
}
}
