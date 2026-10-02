#pragma once
#include <cmath>
#include <algorithm>
struct float3 {float x,y,z;float3(float X=0,float Y=0,float Z=0):x(X),y(Y),z(Z){} };
inline float3 operator+(float3 a,float3 b){return {a.x+b.x,a.y+b.y,a.z+b.z};}
inline float3 operator-(float3 a,float3 b){return {a.x-b.x,a.y-b.y,a.z-b.z};}
inline float3 operator*(float3 a,float b){return {a.x*b,a.y*b,a.z*b};}
using std::min;using std::max;using std::sin;using std::cos;
inline float clamp(float v,float a,float b){return min(max(v,a),b);}
inline float saturate(float v){return clamp(v,0.f,1.f);}
inline float frac(float v){return v-std::floor(v);}
inline float length(float3 v){return std::sqrt(v.x*v.x+v.y*v.y+v.z*v.z);}
inline float3 normalize(float3 v){return v*(1.f/length(v));}
inline float3 lerp(float3 a,float3 b,float x){return a+(b-a)*x;}
