#include "CurvePacket.ush"
StructuredBuffer<float> Input:register(t0);RWStructuredBuffer<float4> Output:register(u0);
[numthreads(1,1,1)] void Main(uint3 Id:SV_DispatchThreadID){float P[77];for(int i=0;i<77;++i)P[i]=Input[i];CurvePose V=CurveEvaluatePose(P,Input[77],Input[78]>0,float3(20,7,170),float3(4,2,3),float3(1,0,0),Input[79],Input[80]);Output[0]=float4(V.Wpo,V.Phase);Output[1]=float4(V.Normal,1);}
