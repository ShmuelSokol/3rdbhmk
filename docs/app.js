var Xd=0,lh=1,qd=2;var Ma=1,Vo=2,ri=3,pn=0,Dt=1,Mt=2,Ti=0,es=1,ds=2,hh=3,uh=4,jd=5,Fi=100,Kd=101,Zd=102,Jd=103,$d=104,Qd=200,ef=201,tf=202,nf=203,Mo=204,So=205,sf=206,rf=207,af=208,of=209,cf=210,lf=211,hf=212,uf=213,df=214,Go=0,Wo=1,Yo=2,ts=3,Xo=4,qo=5,jo=6,Ko=7,Zo=0,ff=1,pf=2,Ei=0,mf=1,gf=2,bf=3,Jo=4,yf=5,xf=6,vf=7,Jl="attached",_f="detached",dh=300,fs=301,ps=302,$o=303,Qo=304,Sa=306,Ui=1e3,$n=1001,js=1002,qt=1003,ec=1004;var ms=1005;var jt=1006,hr=1007;var qn=1008;var jn=1009,fh=1010,ph=1011,ur=1012,tc=1013,Oi=1014,Fn=1015,zi=1016,nc=1017,ic=1018,dr=1020,mh=35902,gh=35899,bh=1021,yh=1022,Tn=1023,Ks=1026,fr=1027,pr=1028,sc=1029,xh=1030,rc=1031;var ac=1033,Ta=33776,Ea=33777,Aa=33778,Ra=33779,oc=35840,cc=35841,lc=35842,hc=35843,uc=36196,dc=37492,fc=37496,pc=37808,mc=37809,gc=37810,bc=37811,yc=37812,xc=37813,vc=37814,_c=37815,wc=37816,Mc=37817,Sc=37818,Tc=37819,Ec=37820,Ac=37821,Rc=36492,Cc=36494,Ic=36495,Pc=36283,kc=36284,Lc=36285,Dc=36286;var ns=2300,is=2301,wo=2302,$l=2400,Ql=2401,eh=2402,wf=2500;var vh=0,Ca=1,mr=2,Mf=3200,Sf=3201;var Nc=0,Tf=1,Ai="",kt="srgb",Kt="srgb-linear",Kr="linear",pt="srgb";var Qi=7680;var th=519,Ef=512,Af=513,Rf=514,_h=515,Cf=516,If=517,Pf=518,kf=519,To=35044;var wh="300 es",Wn=2e3,Zr=2001;var xi=class{addEventListener(e,t){this._listeners===void 0&&(this._listeners={});let n=this._listeners;n[e]===void 0&&(n[e]=[]),n[e].indexOf(t)===-1&&n[e].push(t)}hasEventListener(e,t){let n=this._listeners;return n===void 0?!1:n[e]!==void 0&&n[e].indexOf(t)!==-1}removeEventListener(e,t){let n=this._listeners;if(n===void 0)return;let i=n[e];if(i!==void 0){let r=i.indexOf(t);r!==-1&&i.splice(r,1)}}dispatchEvent(e){let t=this._listeners;if(t===void 0)return;let n=t[e.type];if(n!==void 0){e.target=this;let i=n.slice(0);for(let r=0,a=i.length;r<a;r++)i[r].call(this,e);e.target=null}}},$t=["00","01","02","03","04","05","06","07","08","09","0a","0b","0c","0d","0e","0f","10","11","12","13","14","15","16","17","18","19","1a","1b","1c","1d","1e","1f","20","21","22","23","24","25","26","27","28","29","2a","2b","2c","2d","2e","2f","30","31","32","33","34","35","36","37","38","39","3a","3b","3c","3d","3e","3f","40","41","42","43","44","45","46","47","48","49","4a","4b","4c","4d","4e","4f","50","51","52","53","54","55","56","57","58","59","5a","5b","5c","5d","5e","5f","60","61","62","63","64","65","66","67","68","69","6a","6b","6c","6d","6e","6f","70","71","72","73","74","75","76","77","78","79","7a","7b","7c","7d","7e","7f","80","81","82","83","84","85","86","87","88","89","8a","8b","8c","8d","8e","8f","90","91","92","93","94","95","96","97","98","99","9a","9b","9c","9d","9e","9f","a0","a1","a2","a3","a4","a5","a6","a7","a8","a9","aa","ab","ac","ad","ae","af","b0","b1","b2","b3","b4","b5","b6","b7","b8","b9","ba","bb","bc","bd","be","bf","c0","c1","c2","c3","c4","c5","c6","c7","c8","c9","ca","cb","cc","cd","ce","cf","d0","d1","d2","d3","d4","d5","d6","d7","d8","d9","da","db","dc","dd","de","df","e0","e1","e2","e3","e4","e5","e6","e7","e8","e9","ea","eb","ec","ed","ee","ef","f0","f1","f2","f3","f4","f5","f6","f7","f8","f9","fa","fb","fc","fd","fe","ff"],od=1234567,qr=Math.PI/180,ss=180/Math.PI;function Yn(){let s=Math.random()*4294967295|0,e=Math.random()*4294967295|0,t=Math.random()*4294967295|0,n=Math.random()*4294967295|0;return($t[s&255]+$t[s>>8&255]+$t[s>>16&255]+$t[s>>24&255]+"-"+$t[e&255]+$t[e>>8&255]+"-"+$t[e>>16&15|64]+$t[e>>24&255]+"-"+$t[t&63|128]+$t[t>>8&255]+"-"+$t[t>>16&255]+$t[t>>24&255]+$t[n&255]+$t[n>>8&255]+$t[n>>16&255]+$t[n>>24&255]).toLowerCase()}function We(s,e,t){return Math.max(e,Math.min(t,s))}function Mh(s,e){return(s%e+e)%e}function Um(s,e,t,n,i){return n+(s-e)*(i-n)/(t-e)}function Bm(s,e,t){return s!==e?(t-s)/(e-s):0}function jr(s,e,t){return(1-t)*s+t*e}function Om(s,e,t,n){return jr(s,e,1-Math.exp(-t*n))}function zm(s,e=1){return e-Math.abs(Mh(s,e*2)-e)}function Hm(s,e,t){return s<=e?0:s>=t?1:(s=(s-e)/(t-e),s*s*(3-2*s))}function Vm(s,e,t){return s<=e?0:s>=t?1:(s=(s-e)/(t-e),s*s*s*(s*(s*6-15)+10))}function Gm(s,e){return s+Math.floor(Math.random()*(e-s+1))}function Wm(s,e){return s+Math.random()*(e-s)}function Ym(s){return s*(.5-Math.random())}function Xm(s){s!==void 0&&(od=s);let e=od+=1831565813;return e=Math.imul(e^e>>>15,e|1),e^=e+Math.imul(e^e>>>7,e|61),((e^e>>>14)>>>0)/4294967296}function qm(s){return s*qr}function jm(s){return s*ss}function Km(s){return(s&s-1)===0&&s!==0}function Zm(s){return Math.pow(2,Math.ceil(Math.log(s)/Math.LN2))}function Jm(s){return Math.pow(2,Math.floor(Math.log(s)/Math.LN2))}function $m(s,e,t,n,i){let r=Math.cos,a=Math.sin,o=r(t/2),c=a(t/2),l=r((e+n)/2),u=a((e+n)/2),h=r((e-n)/2),d=a((e-n)/2),f=r((n-e)/2),g=a((n-e)/2);switch(i){case"XYX":s.set(o*u,c*h,c*d,o*l);break;case"YZY":s.set(c*d,o*u,c*h,o*l);break;case"ZXZ":s.set(c*h,c*d,o*u,o*l);break;case"XZX":s.set(o*u,c*g,c*f,o*l);break;case"YXY":s.set(c*f,o*u,c*g,o*l);break;case"ZYZ":s.set(c*g,c*f,o*u,o*l);break;default:console.warn("THREE.MathUtils: .setQuaternionFromProperEuler() encountered an unknown order: "+i)}}function Gn(s,e){switch(e.constructor){case Float32Array:return s;case Uint32Array:return s/4294967295;case Uint16Array:return s/65535;case Uint8Array:return s/255;case Int32Array:return Math.max(s/2147483647,-1);case Int16Array:return Math.max(s/32767,-1);case Int8Array:return Math.max(s/127,-1);default:throw new Error("Invalid component type.")}}function ft(s,e){switch(e.constructor){case Float32Array:return s;case Uint32Array:return Math.round(s*4294967295);case Uint16Array:return Math.round(s*65535);case Uint8Array:return Math.round(s*255);case Int32Array:return Math.round(s*2147483647);case Int16Array:return Math.round(s*32767);case Int8Array:return Math.round(s*127);default:throw new Error("Invalid component type.")}}var Ct={DEG2RAD:qr,RAD2DEG:ss,generateUUID:Yn,clamp:We,euclideanModulo:Mh,mapLinear:Um,inverseLerp:Bm,lerp:jr,damp:Om,pingpong:zm,smoothstep:Hm,smootherstep:Vm,randInt:Gm,randFloat:Wm,randFloatSpread:Ym,seededRandom:Xm,degToRad:qm,radToDeg:jm,isPowerOfTwo:Km,ceilPowerOfTwo:Zm,floorPowerOfTwo:Jm,setQuaternionFromProperEuler:$m,normalize:ft,denormalize:Gn},Ne=class s{constructor(e=0,t=0){s.prototype.isVector2=!0,this.x=e,this.y=t}get width(){return this.x}set width(e){this.x=e}get height(){return this.y}set height(e){this.y=e}set(e,t){return this.x=e,this.y=t,this}setScalar(e){return this.x=e,this.y=e,this}setX(e){return this.x=e,this}setY(e){return this.y=e,this}setComponent(e,t){switch(e){case 0:this.x=t;break;case 1:this.y=t;break;default:throw new Error("index is out of range: "+e)}return this}getComponent(e){switch(e){case 0:return this.x;case 1:return this.y;default:throw new Error("index is out of range: "+e)}}clone(){return new this.constructor(this.x,this.y)}copy(e){return this.x=e.x,this.y=e.y,this}add(e){return this.x+=e.x,this.y+=e.y,this}addScalar(e){return this.x+=e,this.y+=e,this}addVectors(e,t){return this.x=e.x+t.x,this.y=e.y+t.y,this}addScaledVector(e,t){return this.x+=e.x*t,this.y+=e.y*t,this}sub(e){return this.x-=e.x,this.y-=e.y,this}subScalar(e){return this.x-=e,this.y-=e,this}subVectors(e,t){return this.x=e.x-t.x,this.y=e.y-t.y,this}multiply(e){return this.x*=e.x,this.y*=e.y,this}multiplyScalar(e){return this.x*=e,this.y*=e,this}divide(e){return this.x/=e.x,this.y/=e.y,this}divideScalar(e){return this.multiplyScalar(1/e)}applyMatrix3(e){let t=this.x,n=this.y,i=e.elements;return this.x=i[0]*t+i[3]*n+i[6],this.y=i[1]*t+i[4]*n+i[7],this}min(e){return this.x=Math.min(this.x,e.x),this.y=Math.min(this.y,e.y),this}max(e){return this.x=Math.max(this.x,e.x),this.y=Math.max(this.y,e.y),this}clamp(e,t){return this.x=We(this.x,e.x,t.x),this.y=We(this.y,e.y,t.y),this}clampScalar(e,t){return this.x=We(this.x,e,t),this.y=We(this.y,e,t),this}clampLength(e,t){let n=this.length();return this.divideScalar(n||1).multiplyScalar(We(n,e,t))}floor(){return this.x=Math.floor(this.x),this.y=Math.floor(this.y),this}ceil(){return this.x=Math.ceil(this.x),this.y=Math.ceil(this.y),this}round(){return this.x=Math.round(this.x),this.y=Math.round(this.y),this}roundToZero(){return this.x=Math.trunc(this.x),this.y=Math.trunc(this.y),this}negate(){return this.x=-this.x,this.y=-this.y,this}dot(e){return this.x*e.x+this.y*e.y}cross(e){return this.x*e.y-this.y*e.x}lengthSq(){return this.x*this.x+this.y*this.y}length(){return Math.sqrt(this.x*this.x+this.y*this.y)}manhattanLength(){return Math.abs(this.x)+Math.abs(this.y)}normalize(){return this.divideScalar(this.length()||1)}angle(){return Math.atan2(-this.y,-this.x)+Math.PI}angleTo(e){let t=Math.sqrt(this.lengthSq()*e.lengthSq());if(t===0)return Math.PI/2;let n=this.dot(e)/t;return Math.acos(We(n,-1,1))}distanceTo(e){return Math.sqrt(this.distanceToSquared(e))}distanceToSquared(e){let t=this.x-e.x,n=this.y-e.y;return t*t+n*n}manhattanDistanceTo(e){return Math.abs(this.x-e.x)+Math.abs(this.y-e.y)}setLength(e){return this.normalize().multiplyScalar(e)}lerp(e,t){return this.x+=(e.x-this.x)*t,this.y+=(e.y-this.y)*t,this}lerpVectors(e,t,n){return this.x=e.x+(t.x-e.x)*n,this.y=e.y+(t.y-e.y)*n,this}equals(e){return e.x===this.x&&e.y===this.y}fromArray(e,t=0){return this.x=e[t],this.y=e[t+1],this}toArray(e=[],t=0){return e[t]=this.x,e[t+1]=this.y,e}fromBufferAttribute(e,t){return this.x=e.getX(t),this.y=e.getY(t),this}rotateAround(e,t){let n=Math.cos(t),i=Math.sin(t),r=this.x-e.x,a=this.y-e.y;return this.x=r*n-a*i+e.x,this.y=r*i+a*n+e.y,this}random(){return this.x=Math.random(),this.y=Math.random(),this}*[Symbol.iterator](){yield this.x,yield this.y}},Ln=class{constructor(e=0,t=0,n=0,i=1){this.isQuaternion=!0,this._x=e,this._y=t,this._z=n,this._w=i}static slerpFlat(e,t,n,i,r,a,o){let c=n[i+0],l=n[i+1],u=n[i+2],h=n[i+3],d=r[a+0],f=r[a+1],g=r[a+2],y=r[a+3];if(o===0){e[t+0]=c,e[t+1]=l,e[t+2]=u,e[t+3]=h;return}if(o===1){e[t+0]=d,e[t+1]=f,e[t+2]=g,e[t+3]=y;return}if(h!==y||c!==d||l!==f||u!==g){let m=1-o,p=c*d+l*f+u*g+h*y,x=p>=0?1:-1,v=1-p*p;if(v>Number.EPSILON){let S=Math.sqrt(v),w=Math.atan2(S,p*x);m=Math.sin(m*w)/S,o=Math.sin(o*w)/S}let b=o*x;if(c=c*m+d*b,l=l*m+f*b,u=u*m+g*b,h=h*m+y*b,m===1-o){let S=1/Math.sqrt(c*c+l*l+u*u+h*h);c*=S,l*=S,u*=S,h*=S}}e[t]=c,e[t+1]=l,e[t+2]=u,e[t+3]=h}static multiplyQuaternionsFlat(e,t,n,i,r,a){let o=n[i],c=n[i+1],l=n[i+2],u=n[i+3],h=r[a],d=r[a+1],f=r[a+2],g=r[a+3];return e[t]=o*g+u*h+c*f-l*d,e[t+1]=c*g+u*d+l*h-o*f,e[t+2]=l*g+u*f+o*d-c*h,e[t+3]=u*g-o*h-c*d-l*f,e}get x(){return this._x}set x(e){this._x=e,this._onChangeCallback()}get y(){return this._y}set y(e){this._y=e,this._onChangeCallback()}get z(){return this._z}set z(e){this._z=e,this._onChangeCallback()}get w(){return this._w}set w(e){this._w=e,this._onChangeCallback()}set(e,t,n,i){return this._x=e,this._y=t,this._z=n,this._w=i,this._onChangeCallback(),this}clone(){return new this.constructor(this._x,this._y,this._z,this._w)}copy(e){return this._x=e.x,this._y=e.y,this._z=e.z,this._w=e.w,this._onChangeCallback(),this}setFromEuler(e,t=!0){let n=e._x,i=e._y,r=e._z,a=e._order,o=Math.cos,c=Math.sin,l=o(n/2),u=o(i/2),h=o(r/2),d=c(n/2),f=c(i/2),g=c(r/2);switch(a){case"XYZ":this._x=d*u*h+l*f*g,this._y=l*f*h-d*u*g,this._z=l*u*g+d*f*h,this._w=l*u*h-d*f*g;break;case"YXZ":this._x=d*u*h+l*f*g,this._y=l*f*h-d*u*g,this._z=l*u*g-d*f*h,this._w=l*u*h+d*f*g;break;case"ZXY":this._x=d*u*h-l*f*g,this._y=l*f*h+d*u*g,this._z=l*u*g+d*f*h,this._w=l*u*h-d*f*g;break;case"ZYX":this._x=d*u*h-l*f*g,this._y=l*f*h+d*u*g,this._z=l*u*g-d*f*h,this._w=l*u*h+d*f*g;break;case"YZX":this._x=d*u*h+l*f*g,this._y=l*f*h+d*u*g,this._z=l*u*g-d*f*h,this._w=l*u*h-d*f*g;break;case"XZY":this._x=d*u*h-l*f*g,this._y=l*f*h-d*u*g,this._z=l*u*g+d*f*h,this._w=l*u*h+d*f*g;break;default:console.warn("THREE.Quaternion: .setFromEuler() encountered an unknown order: "+a)}return t===!0&&this._onChangeCallback(),this}setFromAxisAngle(e,t){let n=t/2,i=Math.sin(n);return this._x=e.x*i,this._y=e.y*i,this._z=e.z*i,this._w=Math.cos(n),this._onChangeCallback(),this}setFromRotationMatrix(e){let t=e.elements,n=t[0],i=t[4],r=t[8],a=t[1],o=t[5],c=t[9],l=t[2],u=t[6],h=t[10],d=n+o+h;if(d>0){let f=.5/Math.sqrt(d+1);this._w=.25/f,this._x=(u-c)*f,this._y=(r-l)*f,this._z=(a-i)*f}else if(n>o&&n>h){let f=2*Math.sqrt(1+n-o-h);this._w=(u-c)/f,this._x=.25*f,this._y=(i+a)/f,this._z=(r+l)/f}else if(o>h){let f=2*Math.sqrt(1+o-n-h);this._w=(r-l)/f,this._x=(i+a)/f,this._y=.25*f,this._z=(c+u)/f}else{let f=2*Math.sqrt(1+h-n-o);this._w=(a-i)/f,this._x=(r+l)/f,this._y=(c+u)/f,this._z=.25*f}return this._onChangeCallback(),this}setFromUnitVectors(e,t){let n=e.dot(t)+1;return n<1e-8?(n=0,Math.abs(e.x)>Math.abs(e.z)?(this._x=-e.y,this._y=e.x,this._z=0,this._w=n):(this._x=0,this._y=-e.z,this._z=e.y,this._w=n)):(this._x=e.y*t.z-e.z*t.y,this._y=e.z*t.x-e.x*t.z,this._z=e.x*t.y-e.y*t.x,this._w=n),this.normalize()}angleTo(e){return 2*Math.acos(Math.abs(We(this.dot(e),-1,1)))}rotateTowards(e,t){let n=this.angleTo(e);if(n===0)return this;let i=Math.min(1,t/n);return this.slerp(e,i),this}identity(){return this.set(0,0,0,1)}invert(){return this.conjugate()}conjugate(){return this._x*=-1,this._y*=-1,this._z*=-1,this._onChangeCallback(),this}dot(e){return this._x*e._x+this._y*e._y+this._z*e._z+this._w*e._w}lengthSq(){return this._x*this._x+this._y*this._y+this._z*this._z+this._w*this._w}length(){return Math.sqrt(this._x*this._x+this._y*this._y+this._z*this._z+this._w*this._w)}normalize(){let e=this.length();return e===0?(this._x=0,this._y=0,this._z=0,this._w=1):(e=1/e,this._x=this._x*e,this._y=this._y*e,this._z=this._z*e,this._w=this._w*e),this._onChangeCallback(),this}multiply(e){return this.multiplyQuaternions(this,e)}premultiply(e){return this.multiplyQuaternions(e,this)}multiplyQuaternions(e,t){let n=e._x,i=e._y,r=e._z,a=e._w,o=t._x,c=t._y,l=t._z,u=t._w;return this._x=n*u+a*o+i*l-r*c,this._y=i*u+a*c+r*o-n*l,this._z=r*u+a*l+n*c-i*o,this._w=a*u-n*o-i*c-r*l,this._onChangeCallback(),this}slerp(e,t){if(t===0)return this;if(t===1)return this.copy(e);let n=this._x,i=this._y,r=this._z,a=this._w,o=a*e._w+n*e._x+i*e._y+r*e._z;if(o<0?(this._w=-e._w,this._x=-e._x,this._y=-e._y,this._z=-e._z,o=-o):this.copy(e),o>=1)return this._w=a,this._x=n,this._y=i,this._z=r,this;let c=1-o*o;if(c<=Number.EPSILON){let f=1-t;return this._w=f*a+t*this._w,this._x=f*n+t*this._x,this._y=f*i+t*this._y,this._z=f*r+t*this._z,this.normalize(),this}let l=Math.sqrt(c),u=Math.atan2(l,o),h=Math.sin((1-t)*u)/l,d=Math.sin(t*u)/l;return this._w=a*h+this._w*d,this._x=n*h+this._x*d,this._y=i*h+this._y*d,this._z=r*h+this._z*d,this._onChangeCallback(),this}slerpQuaternions(e,t,n){return this.copy(e).slerp(t,n)}random(){let e=2*Math.PI*Math.random(),t=2*Math.PI*Math.random(),n=Math.random(),i=Math.sqrt(1-n),r=Math.sqrt(n);return this.set(i*Math.sin(e),i*Math.cos(e),r*Math.sin(t),r*Math.cos(t))}equals(e){return e._x===this._x&&e._y===this._y&&e._z===this._z&&e._w===this._w}fromArray(e,t=0){return this._x=e[t],this._y=e[t+1],this._z=e[t+2],this._w=e[t+3],this._onChangeCallback(),this}toArray(e=[],t=0){return e[t]=this._x,e[t+1]=this._y,e[t+2]=this._z,e[t+3]=this._w,e}fromBufferAttribute(e,t){return this._x=e.getX(t),this._y=e.getY(t),this._z=e.getZ(t),this._w=e.getW(t),this._onChangeCallback(),this}toJSON(){return this.toArray()}_onChange(e){return this._onChangeCallback=e,this}_onChangeCallback(){}*[Symbol.iterator](){yield this._x,yield this._y,yield this._z,yield this._w}},L=class s{constructor(e=0,t=0,n=0){s.prototype.isVector3=!0,this.x=e,this.y=t,this.z=n}set(e,t,n){return n===void 0&&(n=this.z),this.x=e,this.y=t,this.z=n,this}setScalar(e){return this.x=e,this.y=e,this.z=e,this}setX(e){return this.x=e,this}setY(e){return this.y=e,this}setZ(e){return this.z=e,this}setComponent(e,t){switch(e){case 0:this.x=t;break;case 1:this.y=t;break;case 2:this.z=t;break;default:throw new Error("index is out of range: "+e)}return this}getComponent(e){switch(e){case 0:return this.x;case 1:return this.y;case 2:return this.z;default:throw new Error("index is out of range: "+e)}}clone(){return new this.constructor(this.x,this.y,this.z)}copy(e){return this.x=e.x,this.y=e.y,this.z=e.z,this}add(e){return this.x+=e.x,this.y+=e.y,this.z+=e.z,this}addScalar(e){return this.x+=e,this.y+=e,this.z+=e,this}addVectors(e,t){return this.x=e.x+t.x,this.y=e.y+t.y,this.z=e.z+t.z,this}addScaledVector(e,t){return this.x+=e.x*t,this.y+=e.y*t,this.z+=e.z*t,this}sub(e){return this.x-=e.x,this.y-=e.y,this.z-=e.z,this}subScalar(e){return this.x-=e,this.y-=e,this.z-=e,this}subVectors(e,t){return this.x=e.x-t.x,this.y=e.y-t.y,this.z=e.z-t.z,this}multiply(e){return this.x*=e.x,this.y*=e.y,this.z*=e.z,this}multiplyScalar(e){return this.x*=e,this.y*=e,this.z*=e,this}multiplyVectors(e,t){return this.x=e.x*t.x,this.y=e.y*t.y,this.z=e.z*t.z,this}applyEuler(e){return this.applyQuaternion(cd.setFromEuler(e))}applyAxisAngle(e,t){return this.applyQuaternion(cd.setFromAxisAngle(e,t))}applyMatrix3(e){let t=this.x,n=this.y,i=this.z,r=e.elements;return this.x=r[0]*t+r[3]*n+r[6]*i,this.y=r[1]*t+r[4]*n+r[7]*i,this.z=r[2]*t+r[5]*n+r[8]*i,this}applyNormalMatrix(e){return this.applyMatrix3(e).normalize()}applyMatrix4(e){let t=this.x,n=this.y,i=this.z,r=e.elements,a=1/(r[3]*t+r[7]*n+r[11]*i+r[15]);return this.x=(r[0]*t+r[4]*n+r[8]*i+r[12])*a,this.y=(r[1]*t+r[5]*n+r[9]*i+r[13])*a,this.z=(r[2]*t+r[6]*n+r[10]*i+r[14])*a,this}applyQuaternion(e){let t=this.x,n=this.y,i=this.z,r=e.x,a=e.y,o=e.z,c=e.w,l=2*(a*i-o*n),u=2*(o*t-r*i),h=2*(r*n-a*t);return this.x=t+c*l+a*h-o*u,this.y=n+c*u+o*l-r*h,this.z=i+c*h+r*u-a*l,this}project(e){return this.applyMatrix4(e.matrixWorldInverse).applyMatrix4(e.projectionMatrix)}unproject(e){return this.applyMatrix4(e.projectionMatrixInverse).applyMatrix4(e.matrixWorld)}transformDirection(e){let t=this.x,n=this.y,i=this.z,r=e.elements;return this.x=r[0]*t+r[4]*n+r[8]*i,this.y=r[1]*t+r[5]*n+r[9]*i,this.z=r[2]*t+r[6]*n+r[10]*i,this.normalize()}divide(e){return this.x/=e.x,this.y/=e.y,this.z/=e.z,this}divideScalar(e){return this.multiplyScalar(1/e)}min(e){return this.x=Math.min(this.x,e.x),this.y=Math.min(this.y,e.y),this.z=Math.min(this.z,e.z),this}max(e){return this.x=Math.max(this.x,e.x),this.y=Math.max(this.y,e.y),this.z=Math.max(this.z,e.z),this}clamp(e,t){return this.x=We(this.x,e.x,t.x),this.y=We(this.y,e.y,t.y),this.z=We(this.z,e.z,t.z),this}clampScalar(e,t){return this.x=We(this.x,e,t),this.y=We(this.y,e,t),this.z=We(this.z,e,t),this}clampLength(e,t){let n=this.length();return this.divideScalar(n||1).multiplyScalar(We(n,e,t))}floor(){return this.x=Math.floor(this.x),this.y=Math.floor(this.y),this.z=Math.floor(this.z),this}ceil(){return this.x=Math.ceil(this.x),this.y=Math.ceil(this.y),this.z=Math.ceil(this.z),this}round(){return this.x=Math.round(this.x),this.y=Math.round(this.y),this.z=Math.round(this.z),this}roundToZero(){return this.x=Math.trunc(this.x),this.y=Math.trunc(this.y),this.z=Math.trunc(this.z),this}negate(){return this.x=-this.x,this.y=-this.y,this.z=-this.z,this}dot(e){return this.x*e.x+this.y*e.y+this.z*e.z}lengthSq(){return this.x*this.x+this.y*this.y+this.z*this.z}length(){return Math.sqrt(this.x*this.x+this.y*this.y+this.z*this.z)}manhattanLength(){return Math.abs(this.x)+Math.abs(this.y)+Math.abs(this.z)}normalize(){return this.divideScalar(this.length()||1)}setLength(e){return this.normalize().multiplyScalar(e)}lerp(e,t){return this.x+=(e.x-this.x)*t,this.y+=(e.y-this.y)*t,this.z+=(e.z-this.z)*t,this}lerpVectors(e,t,n){return this.x=e.x+(t.x-e.x)*n,this.y=e.y+(t.y-e.y)*n,this.z=e.z+(t.z-e.z)*n,this}cross(e){return this.crossVectors(this,e)}crossVectors(e,t){let n=e.x,i=e.y,r=e.z,a=t.x,o=t.y,c=t.z;return this.x=i*c-r*o,this.y=r*a-n*c,this.z=n*o-i*a,this}projectOnVector(e){let t=e.lengthSq();if(t===0)return this.set(0,0,0);let n=e.dot(this)/t;return this.copy(e).multiplyScalar(n)}projectOnPlane(e){return Ml.copy(this).projectOnVector(e),this.sub(Ml)}reflect(e){return this.sub(Ml.copy(e).multiplyScalar(2*this.dot(e)))}angleTo(e){let t=Math.sqrt(this.lengthSq()*e.lengthSq());if(t===0)return Math.PI/2;let n=this.dot(e)/t;return Math.acos(We(n,-1,1))}distanceTo(e){return Math.sqrt(this.distanceToSquared(e))}distanceToSquared(e){let t=this.x-e.x,n=this.y-e.y,i=this.z-e.z;return t*t+n*n+i*i}manhattanDistanceTo(e){return Math.abs(this.x-e.x)+Math.abs(this.y-e.y)+Math.abs(this.z-e.z)}setFromSpherical(e){return this.setFromSphericalCoords(e.radius,e.phi,e.theta)}setFromSphericalCoords(e,t,n){let i=Math.sin(t)*e;return this.x=i*Math.sin(n),this.y=Math.cos(t)*e,this.z=i*Math.cos(n),this}setFromCylindrical(e){return this.setFromCylindricalCoords(e.radius,e.theta,e.y)}setFromCylindricalCoords(e,t,n){return this.x=e*Math.sin(t),this.y=n,this.z=e*Math.cos(t),this}setFromMatrixPosition(e){let t=e.elements;return this.x=t[12],this.y=t[13],this.z=t[14],this}setFromMatrixScale(e){let t=this.setFromMatrixColumn(e,0).length(),n=this.setFromMatrixColumn(e,1).length(),i=this.setFromMatrixColumn(e,2).length();return this.x=t,this.y=n,this.z=i,this}setFromMatrixColumn(e,t){return this.fromArray(e.elements,t*4)}setFromMatrix3Column(e,t){return this.fromArray(e.elements,t*3)}setFromEuler(e){return this.x=e._x,this.y=e._y,this.z=e._z,this}setFromColor(e){return this.x=e.r,this.y=e.g,this.z=e.b,this}equals(e){return e.x===this.x&&e.y===this.y&&e.z===this.z}fromArray(e,t=0){return this.x=e[t],this.y=e[t+1],this.z=e[t+2],this}toArray(e=[],t=0){return e[t]=this.x,e[t+1]=this.y,e[t+2]=this.z,e}fromBufferAttribute(e,t){return this.x=e.getX(t),this.y=e.getY(t),this.z=e.getZ(t),this}random(){return this.x=Math.random(),this.y=Math.random(),this.z=Math.random(),this}randomDirection(){let e=Math.random()*Math.PI*2,t=Math.random()*2-1,n=Math.sqrt(1-t*t);return this.x=n*Math.cos(e),this.y=t,this.z=n*Math.sin(e),this}*[Symbol.iterator](){yield this.x,yield this.y,yield this.z}},Ml=new L,cd=new Ln,qe=class s{constructor(e,t,n,i,r,a,o,c,l){s.prototype.isMatrix3=!0,this.elements=[1,0,0,0,1,0,0,0,1],e!==void 0&&this.set(e,t,n,i,r,a,o,c,l)}set(e,t,n,i,r,a,o,c,l){let u=this.elements;return u[0]=e,u[1]=i,u[2]=o,u[3]=t,u[4]=r,u[5]=c,u[6]=n,u[7]=a,u[8]=l,this}identity(){return this.set(1,0,0,0,1,0,0,0,1),this}copy(e){let t=this.elements,n=e.elements;return t[0]=n[0],t[1]=n[1],t[2]=n[2],t[3]=n[3],t[4]=n[4],t[5]=n[5],t[6]=n[6],t[7]=n[7],t[8]=n[8],this}extractBasis(e,t,n){return e.setFromMatrix3Column(this,0),t.setFromMatrix3Column(this,1),n.setFromMatrix3Column(this,2),this}setFromMatrix4(e){let t=e.elements;return this.set(t[0],t[4],t[8],t[1],t[5],t[9],t[2],t[6],t[10]),this}multiply(e){return this.multiplyMatrices(this,e)}premultiply(e){return this.multiplyMatrices(e,this)}multiplyMatrices(e,t){let n=e.elements,i=t.elements,r=this.elements,a=n[0],o=n[3],c=n[6],l=n[1],u=n[4],h=n[7],d=n[2],f=n[5],g=n[8],y=i[0],m=i[3],p=i[6],x=i[1],v=i[4],b=i[7],S=i[2],w=i[5],T=i[8];return r[0]=a*y+o*x+c*S,r[3]=a*m+o*v+c*w,r[6]=a*p+o*b+c*T,r[1]=l*y+u*x+h*S,r[4]=l*m+u*v+h*w,r[7]=l*p+u*b+h*T,r[2]=d*y+f*x+g*S,r[5]=d*m+f*v+g*w,r[8]=d*p+f*b+g*T,this}multiplyScalar(e){let t=this.elements;return t[0]*=e,t[3]*=e,t[6]*=e,t[1]*=e,t[4]*=e,t[7]*=e,t[2]*=e,t[5]*=e,t[8]*=e,this}determinant(){let e=this.elements,t=e[0],n=e[1],i=e[2],r=e[3],a=e[4],o=e[5],c=e[6],l=e[7],u=e[8];return t*a*u-t*o*l-n*r*u+n*o*c+i*r*l-i*a*c}invert(){let e=this.elements,t=e[0],n=e[1],i=e[2],r=e[3],a=e[4],o=e[5],c=e[6],l=e[7],u=e[8],h=u*a-o*l,d=o*c-u*r,f=l*r-a*c,g=t*h+n*d+i*f;if(g===0)return this.set(0,0,0,0,0,0,0,0,0);let y=1/g;return e[0]=h*y,e[1]=(i*l-u*n)*y,e[2]=(o*n-i*a)*y,e[3]=d*y,e[4]=(u*t-i*c)*y,e[5]=(i*r-o*t)*y,e[6]=f*y,e[7]=(n*c-l*t)*y,e[8]=(a*t-n*r)*y,this}transpose(){let e,t=this.elements;return e=t[1],t[1]=t[3],t[3]=e,e=t[2],t[2]=t[6],t[6]=e,e=t[5],t[5]=t[7],t[7]=e,this}getNormalMatrix(e){return this.setFromMatrix4(e).invert().transpose()}transposeIntoArray(e){let t=this.elements;return e[0]=t[0],e[1]=t[3],e[2]=t[6],e[3]=t[1],e[4]=t[4],e[5]=t[7],e[6]=t[2],e[7]=t[5],e[8]=t[8],this}setUvTransform(e,t,n,i,r,a,o){let c=Math.cos(r),l=Math.sin(r);return this.set(n*c,n*l,-n*(c*a+l*o)+a+e,-i*l,i*c,-i*(-l*a+c*o)+o+t,0,0,1),this}scale(e,t){return this.premultiply(Sl.makeScale(e,t)),this}rotate(e){return this.premultiply(Sl.makeRotation(-e)),this}translate(e,t){return this.premultiply(Sl.makeTranslation(e,t)),this}makeTranslation(e,t){return e.isVector2?this.set(1,0,e.x,0,1,e.y,0,0,1):this.set(1,0,e,0,1,t,0,0,1),this}makeRotation(e){let t=Math.cos(e),n=Math.sin(e);return this.set(t,-n,0,n,t,0,0,0,1),this}makeScale(e,t){return this.set(e,0,0,0,t,0,0,0,1),this}equals(e){let t=this.elements,n=e.elements;for(let i=0;i<9;i++)if(t[i]!==n[i])return!1;return!0}fromArray(e,t=0){for(let n=0;n<9;n++)this.elements[n]=e[n+t];return this}toArray(e=[],t=0){let n=this.elements;return e[t]=n[0],e[t+1]=n[1],e[t+2]=n[2],e[t+3]=n[3],e[t+4]=n[4],e[t+5]=n[5],e[t+6]=n[6],e[t+7]=n[7],e[t+8]=n[8],e}clone(){return new this.constructor().fromArray(this.elements)}},Sl=new qe;function Sh(s){for(let e=s.length-1;e>=0;--e)if(s[e]>=65535)return!0;return!1}function Zs(s){return document.createElementNS("http://www.w3.org/1999/xhtml",s)}function Lf(){let s=Zs("canvas");return s.style.display="block",s}var ld={};function Js(s){s in ld||(ld[s]=!0,console.warn(s))}function Df(s,e,t){return new Promise(function(n,i){function r(){switch(s.clientWaitSync(e,s.SYNC_FLUSH_COMMANDS_BIT,0)){case s.WAIT_FAILED:i();break;case s.TIMEOUT_EXPIRED:setTimeout(r,t);break;default:n()}}setTimeout(r,t)})}var hd=new qe().set(.4123908,.3575843,.1804808,.212639,.7151687,.0721923,.0193308,.1191948,.9505322),ud=new qe().set(3.2409699,-1.5373832,-.4986108,-.9692436,1.8759675,.0415551,.0556301,-.203977,1.0569715);function Qm(){let s={enabled:!0,workingColorSpace:Kt,spaces:{},convert:function(i,r,a){return this.enabled===!1||r===a||!r||!a||(this.spaces[r].transfer===pt&&(i.r=yi(i.r),i.g=yi(i.g),i.b=yi(i.b)),this.spaces[r].primaries!==this.spaces[a].primaries&&(i.applyMatrix3(this.spaces[r].toXYZ),i.applyMatrix3(this.spaces[a].fromXYZ)),this.spaces[a].transfer===pt&&(i.r=qs(i.r),i.g=qs(i.g),i.b=qs(i.b))),i},workingToColorSpace:function(i,r){return this.convert(i,this.workingColorSpace,r)},colorSpaceToWorking:function(i,r){return this.convert(i,r,this.workingColorSpace)},getPrimaries:function(i){return this.spaces[i].primaries},getTransfer:function(i){return i===Ai?Kr:this.spaces[i].transfer},getToneMappingMode:function(i){return this.spaces[i].outputColorSpaceConfig.toneMappingMode||"standard"},getLuminanceCoefficients:function(i,r=this.workingColorSpace){return i.fromArray(this.spaces[r].luminanceCoefficients)},define:function(i){Object.assign(this.spaces,i)},_getMatrix:function(i,r,a){return i.copy(this.spaces[r].toXYZ).multiply(this.spaces[a].fromXYZ)},_getDrawingBufferColorSpace:function(i){return this.spaces[i].outputColorSpaceConfig.drawingBufferColorSpace},_getUnpackColorSpace:function(i=this.workingColorSpace){return this.spaces[i].workingColorSpaceConfig.unpackColorSpace},fromWorkingColorSpace:function(i,r){return Js("THREE.ColorManagement: .fromWorkingColorSpace() has been renamed to .workingToColorSpace()."),s.workingToColorSpace(i,r)},toWorkingColorSpace:function(i,r){return Js("THREE.ColorManagement: .toWorkingColorSpace() has been renamed to .colorSpaceToWorking()."),s.colorSpaceToWorking(i,r)}},e=[.64,.33,.3,.6,.15,.06],t=[.2126,.7152,.0722],n=[.3127,.329];return s.define({[Kt]:{primaries:e,whitePoint:n,transfer:Kr,toXYZ:hd,fromXYZ:ud,luminanceCoefficients:t,workingColorSpaceConfig:{unpackColorSpace:kt},outputColorSpaceConfig:{drawingBufferColorSpace:kt}},[kt]:{primaries:e,whitePoint:n,transfer:pt,toXYZ:hd,fromXYZ:ud,luminanceCoefficients:t,outputColorSpaceConfig:{drawingBufferColorSpace:kt}}}),s}var et=Qm();function yi(s){return s<.04045?s*.0773993808:Math.pow(s*.9478672986+.0521327014,2.4)}function qs(s){return s<.0031308?s*12.92:1.055*Math.pow(s,.41666)-.055}var Ps,Eo=class{static getDataURL(e,t="image/png"){if(/^data:/i.test(e.src)||typeof HTMLCanvasElement>"u")return e.src;let n;if(e instanceof HTMLCanvasElement)n=e;else{Ps===void 0&&(Ps=Zs("canvas")),Ps.width=e.width,Ps.height=e.height;let i=Ps.getContext("2d");e instanceof ImageData?i.putImageData(e,0,0):i.drawImage(e,0,0,e.width,e.height),n=Ps}return n.toDataURL(t)}static sRGBToLinear(e){if(typeof HTMLImageElement<"u"&&e instanceof HTMLImageElement||typeof HTMLCanvasElement<"u"&&e instanceof HTMLCanvasElement||typeof ImageBitmap<"u"&&e instanceof ImageBitmap){let t=Zs("canvas");t.width=e.width,t.height=e.height;let n=t.getContext("2d");n.drawImage(e,0,0,e.width,e.height);let i=n.getImageData(0,0,e.width,e.height),r=i.data;for(let a=0;a<r.length;a++)r[a]=yi(r[a]/255)*255;return n.putImageData(i,0,0),t}else if(e.data){let t=e.data.slice(0);for(let n=0;n<t.length;n++)t instanceof Uint8Array||t instanceof Uint8ClampedArray?t[n]=Math.floor(yi(t[n]/255)*255):t[n]=yi(t[n]);return{data:t,width:e.width,height:e.height}}else return console.warn("THREE.ImageUtils.sRGBToLinear(): Unsupported image type. No color space conversion applied."),e}},eg=0,$s=class{constructor(e=null){this.isSource=!0,Object.defineProperty(this,"id",{value:eg++}),this.uuid=Yn(),this.data=e,this.dataReady=!0,this.version=0}getSize(e){let t=this.data;return typeof HTMLVideoElement<"u"&&t instanceof HTMLVideoElement?e.set(t.videoWidth,t.videoHeight,0):t instanceof VideoFrame?e.set(t.displayHeight,t.displayWidth,0):t!==null?e.set(t.width,t.height,t.depth||0):e.set(0,0,0),e}set needsUpdate(e){e===!0&&this.version++}toJSON(e){let t=e===void 0||typeof e=="string";if(!t&&e.images[this.uuid]!==void 0)return e.images[this.uuid];let n={uuid:this.uuid,url:""},i=this.data;if(i!==null){let r;if(Array.isArray(i)){r=[];for(let a=0,o=i.length;a<o;a++)i[a].isDataTexture?r.push(Tl(i[a].image)):r.push(Tl(i[a]))}else r=Tl(i);n.url=r}return t||(e.images[this.uuid]=n),n}};function Tl(s){return typeof HTMLImageElement<"u"&&s instanceof HTMLImageElement||typeof HTMLCanvasElement<"u"&&s instanceof HTMLCanvasElement||typeof ImageBitmap<"u"&&s instanceof ImageBitmap?Eo.getDataURL(s):s.data?{data:Array.from(s.data),width:s.width,height:s.height,type:s.data.constructor.name}:(console.warn("THREE.Texture: Unable to serialize Texture."),{})}var tg=0,El=new L,Wt=class s extends xi{constructor(e=s.DEFAULT_IMAGE,t=s.DEFAULT_MAPPING,n=$n,i=$n,r=jt,a=qn,o=Tn,c=jn,l=s.DEFAULT_ANISOTROPY,u=Ai){super(),this.isTexture=!0,Object.defineProperty(this,"id",{value:tg++}),this.uuid=Yn(),this.name="",this.source=new $s(e),this.mipmaps=[],this.mapping=t,this.channel=0,this.wrapS=n,this.wrapT=i,this.magFilter=r,this.minFilter=a,this.anisotropy=l,this.format=o,this.internalFormat=null,this.type=c,this.offset=new Ne(0,0),this.repeat=new Ne(1,1),this.center=new Ne(0,0),this.rotation=0,this.matrixAutoUpdate=!0,this.matrix=new qe,this.generateMipmaps=!0,this.premultiplyAlpha=!1,this.flipY=!0,this.unpackAlignment=4,this.colorSpace=u,this.userData={},this.updateRanges=[],this.version=0,this.onUpdate=null,this.renderTarget=null,this.isRenderTargetTexture=!1,this.isArrayTexture=!!(e&&e.depth&&e.depth>1),this.pmremVersion=0}get width(){return this.source.getSize(El).x}get height(){return this.source.getSize(El).y}get depth(){return this.source.getSize(El).z}get image(){return this.source.data}set image(e=null){this.source.data=e}updateMatrix(){this.matrix.setUvTransform(this.offset.x,this.offset.y,this.repeat.x,this.repeat.y,this.rotation,this.center.x,this.center.y)}addUpdateRange(e,t){this.updateRanges.push({start:e,count:t})}clearUpdateRanges(){this.updateRanges.length=0}clone(){return new this.constructor().copy(this)}copy(e){return this.name=e.name,this.source=e.source,this.mipmaps=e.mipmaps.slice(0),this.mapping=e.mapping,this.channel=e.channel,this.wrapS=e.wrapS,this.wrapT=e.wrapT,this.magFilter=e.magFilter,this.minFilter=e.minFilter,this.anisotropy=e.anisotropy,this.format=e.format,this.internalFormat=e.internalFormat,this.type=e.type,this.offset.copy(e.offset),this.repeat.copy(e.repeat),this.center.copy(e.center),this.rotation=e.rotation,this.matrixAutoUpdate=e.matrixAutoUpdate,this.matrix.copy(e.matrix),this.generateMipmaps=e.generateMipmaps,this.premultiplyAlpha=e.premultiplyAlpha,this.flipY=e.flipY,this.unpackAlignment=e.unpackAlignment,this.colorSpace=e.colorSpace,this.renderTarget=e.renderTarget,this.isRenderTargetTexture=e.isRenderTargetTexture,this.isArrayTexture=e.isArrayTexture,this.userData=JSON.parse(JSON.stringify(e.userData)),this.needsUpdate=!0,this}setValues(e){for(let t in e){let n=e[t];if(n===void 0){console.warn(`THREE.Texture.setValues(): parameter '${t}' has value of undefined.`);continue}let i=this[t];if(i===void 0){console.warn(`THREE.Texture.setValues(): property '${t}' does not exist.`);continue}i&&n&&i.isVector2&&n.isVector2||i&&n&&i.isVector3&&n.isVector3||i&&n&&i.isMatrix3&&n.isMatrix3?i.copy(n):this[t]=n}}toJSON(e){let t=e===void 0||typeof e=="string";if(!t&&e.textures[this.uuid]!==void 0)return e.textures[this.uuid];let n={metadata:{version:4.7,type:"Texture",generator:"Texture.toJSON"},uuid:this.uuid,name:this.name,image:this.source.toJSON(e).uuid,mapping:this.mapping,channel:this.channel,repeat:[this.repeat.x,this.repeat.y],offset:[this.offset.x,this.offset.y],center:[this.center.x,this.center.y],rotation:this.rotation,wrap:[this.wrapS,this.wrapT],format:this.format,internalFormat:this.internalFormat,type:this.type,colorSpace:this.colorSpace,minFilter:this.minFilter,magFilter:this.magFilter,anisotropy:this.anisotropy,flipY:this.flipY,generateMipmaps:this.generateMipmaps,premultiplyAlpha:this.premultiplyAlpha,unpackAlignment:this.unpackAlignment};return Object.keys(this.userData).length>0&&(n.userData=this.userData),t||(e.textures[this.uuid]=n),n}dispose(){this.dispatchEvent({type:"dispose"})}transformUv(e){if(this.mapping!==dh)return e;if(e.applyMatrix3(this.matrix),e.x<0||e.x>1)switch(this.wrapS){case Ui:e.x=e.x-Math.floor(e.x);break;case $n:e.x=e.x<0?0:1;break;case js:Math.abs(Math.floor(e.x)%2)===1?e.x=Math.ceil(e.x)-e.x:e.x=e.x-Math.floor(e.x);break}if(e.y<0||e.y>1)switch(this.wrapT){case Ui:e.y=e.y-Math.floor(e.y);break;case $n:e.y=e.y<0?0:1;break;case js:Math.abs(Math.floor(e.y)%2)===1?e.y=Math.ceil(e.y)-e.y:e.y=e.y-Math.floor(e.y);break}return this.flipY&&(e.y=1-e.y),e}set needsUpdate(e){e===!0&&(this.version++,this.source.needsUpdate=!0)}set needsPMREMUpdate(e){e===!0&&this.pmremVersion++}};Wt.DEFAULT_IMAGE=null;Wt.DEFAULT_MAPPING=dh;Wt.DEFAULT_ANISOTROPY=1;var tt=class s{constructor(e=0,t=0,n=0,i=1){s.prototype.isVector4=!0,this.x=e,this.y=t,this.z=n,this.w=i}get width(){return this.z}set width(e){this.z=e}get height(){return this.w}set height(e){this.w=e}set(e,t,n,i){return this.x=e,this.y=t,this.z=n,this.w=i,this}setScalar(e){return this.x=e,this.y=e,this.z=e,this.w=e,this}setX(e){return this.x=e,this}setY(e){return this.y=e,this}setZ(e){return this.z=e,this}setW(e){return this.w=e,this}setComponent(e,t){switch(e){case 0:this.x=t;break;case 1:this.y=t;break;case 2:this.z=t;break;case 3:this.w=t;break;default:throw new Error("index is out of range: "+e)}return this}getComponent(e){switch(e){case 0:return this.x;case 1:return this.y;case 2:return this.z;case 3:return this.w;default:throw new Error("index is out of range: "+e)}}clone(){return new this.constructor(this.x,this.y,this.z,this.w)}copy(e){return this.x=e.x,this.y=e.y,this.z=e.z,this.w=e.w!==void 0?e.w:1,this}add(e){return this.x+=e.x,this.y+=e.y,this.z+=e.z,this.w+=e.w,this}addScalar(e){return this.x+=e,this.y+=e,this.z+=e,this.w+=e,this}addVectors(e,t){return this.x=e.x+t.x,this.y=e.y+t.y,this.z=e.z+t.z,this.w=e.w+t.w,this}addScaledVector(e,t){return this.x+=e.x*t,this.y+=e.y*t,this.z+=e.z*t,this.w+=e.w*t,this}sub(e){return this.x-=e.x,this.y-=e.y,this.z-=e.z,this.w-=e.w,this}subScalar(e){return this.x-=e,this.y-=e,this.z-=e,this.w-=e,this}subVectors(e,t){return this.x=e.x-t.x,this.y=e.y-t.y,this.z=e.z-t.z,this.w=e.w-t.w,this}multiply(e){return this.x*=e.x,this.y*=e.y,this.z*=e.z,this.w*=e.w,this}multiplyScalar(e){return this.x*=e,this.y*=e,this.z*=e,this.w*=e,this}applyMatrix4(e){let t=this.x,n=this.y,i=this.z,r=this.w,a=e.elements;return this.x=a[0]*t+a[4]*n+a[8]*i+a[12]*r,this.y=a[1]*t+a[5]*n+a[9]*i+a[13]*r,this.z=a[2]*t+a[6]*n+a[10]*i+a[14]*r,this.w=a[3]*t+a[7]*n+a[11]*i+a[15]*r,this}divide(e){return this.x/=e.x,this.y/=e.y,this.z/=e.z,this.w/=e.w,this}divideScalar(e){return this.multiplyScalar(1/e)}setAxisAngleFromQuaternion(e){this.w=2*Math.acos(e.w);let t=Math.sqrt(1-e.w*e.w);return t<1e-4?(this.x=1,this.y=0,this.z=0):(this.x=e.x/t,this.y=e.y/t,this.z=e.z/t),this}setAxisAngleFromRotationMatrix(e){let t,n,i,r,c=e.elements,l=c[0],u=c[4],h=c[8],d=c[1],f=c[5],g=c[9],y=c[2],m=c[6],p=c[10];if(Math.abs(u-d)<.01&&Math.abs(h-y)<.01&&Math.abs(g-m)<.01){if(Math.abs(u+d)<.1&&Math.abs(h+y)<.1&&Math.abs(g+m)<.1&&Math.abs(l+f+p-3)<.1)return this.set(1,0,0,0),this;t=Math.PI;let v=(l+1)/2,b=(f+1)/2,S=(p+1)/2,w=(u+d)/4,T=(h+y)/4,A=(g+m)/4;return v>b&&v>S?v<.01?(n=0,i=.707106781,r=.707106781):(n=Math.sqrt(v),i=w/n,r=T/n):b>S?b<.01?(n=.707106781,i=0,r=.707106781):(i=Math.sqrt(b),n=w/i,r=A/i):S<.01?(n=.707106781,i=.707106781,r=0):(r=Math.sqrt(S),n=T/r,i=A/r),this.set(n,i,r,t),this}let x=Math.sqrt((m-g)*(m-g)+(h-y)*(h-y)+(d-u)*(d-u));return Math.abs(x)<.001&&(x=1),this.x=(m-g)/x,this.y=(h-y)/x,this.z=(d-u)/x,this.w=Math.acos((l+f+p-1)/2),this}setFromMatrixPosition(e){let t=e.elements;return this.x=t[12],this.y=t[13],this.z=t[14],this.w=t[15],this}min(e){return this.x=Math.min(this.x,e.x),this.y=Math.min(this.y,e.y),this.z=Math.min(this.z,e.z),this.w=Math.min(this.w,e.w),this}max(e){return this.x=Math.max(this.x,e.x),this.y=Math.max(this.y,e.y),this.z=Math.max(this.z,e.z),this.w=Math.max(this.w,e.w),this}clamp(e,t){return this.x=We(this.x,e.x,t.x),this.y=We(this.y,e.y,t.y),this.z=We(this.z,e.z,t.z),this.w=We(this.w,e.w,t.w),this}clampScalar(e,t){return this.x=We(this.x,e,t),this.y=We(this.y,e,t),this.z=We(this.z,e,t),this.w=We(this.w,e,t),this}clampLength(e,t){let n=this.length();return this.divideScalar(n||1).multiplyScalar(We(n,e,t))}floor(){return this.x=Math.floor(this.x),this.y=Math.floor(this.y),this.z=Math.floor(this.z),this.w=Math.floor(this.w),this}ceil(){return this.x=Math.ceil(this.x),this.y=Math.ceil(this.y),this.z=Math.ceil(this.z),this.w=Math.ceil(this.w),this}round(){return this.x=Math.round(this.x),this.y=Math.round(this.y),this.z=Math.round(this.z),this.w=Math.round(this.w),this}roundToZero(){return this.x=Math.trunc(this.x),this.y=Math.trunc(this.y),this.z=Math.trunc(this.z),this.w=Math.trunc(this.w),this}negate(){return this.x=-this.x,this.y=-this.y,this.z=-this.z,this.w=-this.w,this}dot(e){return this.x*e.x+this.y*e.y+this.z*e.z+this.w*e.w}lengthSq(){return this.x*this.x+this.y*this.y+this.z*this.z+this.w*this.w}length(){return Math.sqrt(this.x*this.x+this.y*this.y+this.z*this.z+this.w*this.w)}manhattanLength(){return Math.abs(this.x)+Math.abs(this.y)+Math.abs(this.z)+Math.abs(this.w)}normalize(){return this.divideScalar(this.length()||1)}setLength(e){return this.normalize().multiplyScalar(e)}lerp(e,t){return this.x+=(e.x-this.x)*t,this.y+=(e.y-this.y)*t,this.z+=(e.z-this.z)*t,this.w+=(e.w-this.w)*t,this}lerpVectors(e,t,n){return this.x=e.x+(t.x-e.x)*n,this.y=e.y+(t.y-e.y)*n,this.z=e.z+(t.z-e.z)*n,this.w=e.w+(t.w-e.w)*n,this}equals(e){return e.x===this.x&&e.y===this.y&&e.z===this.z&&e.w===this.w}fromArray(e,t=0){return this.x=e[t],this.y=e[t+1],this.z=e[t+2],this.w=e[t+3],this}toArray(e=[],t=0){return e[t]=this.x,e[t+1]=this.y,e[t+2]=this.z,e[t+3]=this.w,e}fromBufferAttribute(e,t){return this.x=e.getX(t),this.y=e.getY(t),this.z=e.getZ(t),this.w=e.getW(t),this}random(){return this.x=Math.random(),this.y=Math.random(),this.z=Math.random(),this.w=Math.random(),this}*[Symbol.iterator](){yield this.x,yield this.y,yield this.z,yield this.w}},Ao=class extends xi{constructor(e=1,t=1,n={}){super(),n=Object.assign({generateMipmaps:!1,internalFormat:null,minFilter:jt,depthBuffer:!0,stencilBuffer:!1,resolveDepthBuffer:!0,resolveStencilBuffer:!0,depthTexture:null,samples:0,count:1,depth:1,multiview:!1},n),this.isRenderTarget=!0,this.width=e,this.height=t,this.depth=n.depth,this.scissor=new tt(0,0,e,t),this.scissorTest=!1,this.viewport=new tt(0,0,e,t);let i={width:e,height:t,depth:n.depth},r=new Wt(i);this.textures=[];let a=n.count;for(let o=0;o<a;o++)this.textures[o]=r.clone(),this.textures[o].isRenderTargetTexture=!0,this.textures[o].renderTarget=this;this._setTextureOptions(n),this.depthBuffer=n.depthBuffer,this.stencilBuffer=n.stencilBuffer,this.resolveDepthBuffer=n.resolveDepthBuffer,this.resolveStencilBuffer=n.resolveStencilBuffer,this._depthTexture=null,this.depthTexture=n.depthTexture,this.samples=n.samples,this.multiview=n.multiview}_setTextureOptions(e={}){let t={minFilter:jt,generateMipmaps:!1,flipY:!1,internalFormat:null};e.mapping!==void 0&&(t.mapping=e.mapping),e.wrapS!==void 0&&(t.wrapS=e.wrapS),e.wrapT!==void 0&&(t.wrapT=e.wrapT),e.wrapR!==void 0&&(t.wrapR=e.wrapR),e.magFilter!==void 0&&(t.magFilter=e.magFilter),e.minFilter!==void 0&&(t.minFilter=e.minFilter),e.format!==void 0&&(t.format=e.format),e.type!==void 0&&(t.type=e.type),e.anisotropy!==void 0&&(t.anisotropy=e.anisotropy),e.colorSpace!==void 0&&(t.colorSpace=e.colorSpace),e.flipY!==void 0&&(t.flipY=e.flipY),e.generateMipmaps!==void 0&&(t.generateMipmaps=e.generateMipmaps),e.internalFormat!==void 0&&(t.internalFormat=e.internalFormat);for(let n=0;n<this.textures.length;n++)this.textures[n].setValues(t)}get texture(){return this.textures[0]}set texture(e){this.textures[0]=e}set depthTexture(e){this._depthTexture!==null&&(this._depthTexture.renderTarget=null),e!==null&&(e.renderTarget=this),this._depthTexture=e}get depthTexture(){return this._depthTexture}setSize(e,t,n=1){if(this.width!==e||this.height!==t||this.depth!==n){this.width=e,this.height=t,this.depth=n;for(let i=0,r=this.textures.length;i<r;i++)this.textures[i].image.width=e,this.textures[i].image.height=t,this.textures[i].image.depth=n,this.textures[i].isArrayTexture=this.textures[i].image.depth>1;this.dispose()}this.viewport.set(0,0,e,t),this.scissor.set(0,0,e,t)}clone(){return new this.constructor().copy(this)}copy(e){this.width=e.width,this.height=e.height,this.depth=e.depth,this.scissor.copy(e.scissor),this.scissorTest=e.scissorTest,this.viewport.copy(e.viewport),this.textures.length=0;for(let t=0,n=e.textures.length;t<n;t++){this.textures[t]=e.textures[t].clone(),this.textures[t].isRenderTargetTexture=!0,this.textures[t].renderTarget=this;let i=Object.assign({},e.textures[t].image);this.textures[t].source=new $s(i)}return this.depthBuffer=e.depthBuffer,this.stencilBuffer=e.stencilBuffer,this.resolveDepthBuffer=e.resolveDepthBuffer,this.resolveStencilBuffer=e.resolveStencilBuffer,e.depthTexture!==null&&(this.depthTexture=e.depthTexture.clone()),this.samples=e.samples,this}dispose(){this.dispatchEvent({type:"dispose"})}},ei=class extends Ao{constructor(e=1,t=1,n={}){super(e,t,n),this.isWebGLRenderTarget=!0}},Jr=class extends Wt{constructor(e=null,t=1,n=1,i=1){super(null),this.isDataArrayTexture=!0,this.image={data:e,width:t,height:n,depth:i},this.magFilter=qt,this.minFilter=qt,this.wrapR=$n,this.generateMipmaps=!1,this.flipY=!1,this.unpackAlignment=1,this.layerUpdates=new Set}addLayerUpdate(e){this.layerUpdates.add(e)}clearLayerUpdates(){this.layerUpdates.clear()}};var Ro=class extends Wt{constructor(e=null,t=1,n=1,i=1){super(null),this.isData3DTexture=!0,this.image={data:e,width:t,height:n,depth:i},this.magFilter=qt,this.minFilter=qt,this.wrapR=$n,this.generateMipmaps=!1,this.flipY=!1,this.unpackAlignment=1}};var ot=class{constructor(e=new L(1/0,1/0,1/0),t=new L(-1/0,-1/0,-1/0)){this.isBox3=!0,this.min=e,this.max=t}set(e,t){return this.min.copy(e),this.max.copy(t),this}setFromArray(e){this.makeEmpty();for(let t=0,n=e.length;t<n;t+=3)this.expandByPoint(zn.fromArray(e,t));return this}setFromBufferAttribute(e){this.makeEmpty();for(let t=0,n=e.count;t<n;t++)this.expandByPoint(zn.fromBufferAttribute(e,t));return this}setFromPoints(e){this.makeEmpty();for(let t=0,n=e.length;t<n;t++)this.expandByPoint(e[t]);return this}setFromCenterAndSize(e,t){let n=zn.copy(t).multiplyScalar(.5);return this.min.copy(e).sub(n),this.max.copy(e).add(n),this}setFromObject(e,t=!1){return this.makeEmpty(),this.expandByObject(e,t)}clone(){return new this.constructor().copy(this)}copy(e){return this.min.copy(e.min),this.max.copy(e.max),this}makeEmpty(){return this.min.x=this.min.y=this.min.z=1/0,this.max.x=this.max.y=this.max.z=-1/0,this}isEmpty(){return this.max.x<this.min.x||this.max.y<this.min.y||this.max.z<this.min.z}getCenter(e){return this.isEmpty()?e.set(0,0,0):e.addVectors(this.min,this.max).multiplyScalar(.5)}getSize(e){return this.isEmpty()?e.set(0,0,0):e.subVectors(this.max,this.min)}expandByPoint(e){return this.min.min(e),this.max.max(e),this}expandByVector(e){return this.min.sub(e),this.max.add(e),this}expandByScalar(e){return this.min.addScalar(-e),this.max.addScalar(e),this}expandByObject(e,t=!1){e.updateWorldMatrix(!1,!1);let n=e.geometry;if(n!==void 0){let r=n.getAttribute("position");if(t===!0&&r!==void 0&&e.isInstancedMesh!==!0)for(let a=0,o=r.count;a<o;a++)e.isMesh===!0?e.getVertexPosition(a,zn):zn.fromBufferAttribute(r,a),zn.applyMatrix4(e.matrixWorld),this.expandByPoint(zn);else e.boundingBox!==void 0?(e.boundingBox===null&&e.computeBoundingBox(),Za.copy(e.boundingBox)):(n.boundingBox===null&&n.computeBoundingBox(),Za.copy(n.boundingBox)),Za.applyMatrix4(e.matrixWorld),this.union(Za)}let i=e.children;for(let r=0,a=i.length;r<a;r++)this.expandByObject(i[r],t);return this}containsPoint(e){return e.x>=this.min.x&&e.x<=this.max.x&&e.y>=this.min.y&&e.y<=this.max.y&&e.z>=this.min.z&&e.z<=this.max.z}containsBox(e){return this.min.x<=e.min.x&&e.max.x<=this.max.x&&this.min.y<=e.min.y&&e.max.y<=this.max.y&&this.min.z<=e.min.z&&e.max.z<=this.max.z}getParameter(e,t){return t.set((e.x-this.min.x)/(this.max.x-this.min.x),(e.y-this.min.y)/(this.max.y-this.min.y),(e.z-this.min.z)/(this.max.z-this.min.z))}intersectsBox(e){return e.max.x>=this.min.x&&e.min.x<=this.max.x&&e.max.y>=this.min.y&&e.min.y<=this.max.y&&e.max.z>=this.min.z&&e.min.z<=this.max.z}intersectsSphere(e){return this.clampPoint(e.center,zn),zn.distanceToSquared(e.center)<=e.radius*e.radius}intersectsPlane(e){let t,n;return e.normal.x>0?(t=e.normal.x*this.min.x,n=e.normal.x*this.max.x):(t=e.normal.x*this.max.x,n=e.normal.x*this.min.x),e.normal.y>0?(t+=e.normal.y*this.min.y,n+=e.normal.y*this.max.y):(t+=e.normal.y*this.max.y,n+=e.normal.y*this.min.y),e.normal.z>0?(t+=e.normal.z*this.min.z,n+=e.normal.z*this.max.z):(t+=e.normal.z*this.max.z,n+=e.normal.z*this.min.z),t<=-e.constant&&n>=-e.constant}intersectsTriangle(e){if(this.isEmpty())return!1;this.getCenter(Or),Ja.subVectors(this.max,Or),ks.subVectors(e.a,Or),Ls.subVectors(e.b,Or),Ds.subVectors(e.c,Or),Ii.subVectors(Ls,ks),Pi.subVectors(Ds,Ls),Ki.subVectors(ks,Ds);let t=[0,-Ii.z,Ii.y,0,-Pi.z,Pi.y,0,-Ki.z,Ki.y,Ii.z,0,-Ii.x,Pi.z,0,-Pi.x,Ki.z,0,-Ki.x,-Ii.y,Ii.x,0,-Pi.y,Pi.x,0,-Ki.y,Ki.x,0];return!Al(t,ks,Ls,Ds,Ja)||(t=[1,0,0,0,1,0,0,0,1],!Al(t,ks,Ls,Ds,Ja))?!1:($a.crossVectors(Ii,Pi),t=[$a.x,$a.y,$a.z],Al(t,ks,Ls,Ds,Ja))}clampPoint(e,t){return t.copy(e).clamp(this.min,this.max)}distanceToPoint(e){return this.clampPoint(e,zn).distanceTo(e)}getBoundingSphere(e){return this.isEmpty()?e.makeEmpty():(this.getCenter(e.center),e.radius=this.getSize(zn).length()*.5),e}intersect(e){return this.min.max(e.min),this.max.min(e.max),this.isEmpty()&&this.makeEmpty(),this}union(e){return this.min.min(e.min),this.max.max(e.max),this}applyMatrix4(e){return this.isEmpty()?this:(ui[0].set(this.min.x,this.min.y,this.min.z).applyMatrix4(e),ui[1].set(this.min.x,this.min.y,this.max.z).applyMatrix4(e),ui[2].set(this.min.x,this.max.y,this.min.z).applyMatrix4(e),ui[3].set(this.min.x,this.max.y,this.max.z).applyMatrix4(e),ui[4].set(this.max.x,this.min.y,this.min.z).applyMatrix4(e),ui[5].set(this.max.x,this.min.y,this.max.z).applyMatrix4(e),ui[6].set(this.max.x,this.max.y,this.min.z).applyMatrix4(e),ui[7].set(this.max.x,this.max.y,this.max.z).applyMatrix4(e),this.setFromPoints(ui),this)}translate(e){return this.min.add(e),this.max.add(e),this}equals(e){return e.min.equals(this.min)&&e.max.equals(this.max)}toJSON(){return{min:this.min.toArray(),max:this.max.toArray()}}fromJSON(e){return this.min.fromArray(e.min),this.max.fromArray(e.max),this}},ui=[new L,new L,new L,new L,new L,new L,new L,new L],zn=new L,Za=new ot,ks=new L,Ls=new L,Ds=new L,Ii=new L,Pi=new L,Ki=new L,Or=new L,Ja=new L,$a=new L,Zi=new L;function Al(s,e,t,n,i){for(let r=0,a=s.length-3;r<=a;r+=3){Zi.fromArray(s,r);let o=i.x*Math.abs(Zi.x)+i.y*Math.abs(Zi.y)+i.z*Math.abs(Zi.z),c=e.dot(Zi),l=t.dot(Zi),u=n.dot(Zi);if(Math.max(-Math.max(c,l,u),Math.min(c,l,u))>o)return!1}return!0}var ng=new ot,zr=new L,Rl=new L,tn=class{constructor(e=new L,t=-1){this.isSphere=!0,this.center=e,this.radius=t}set(e,t){return this.center.copy(e),this.radius=t,this}setFromPoints(e,t){let n=this.center;t!==void 0?n.copy(t):ng.setFromPoints(e).getCenter(n);let i=0;for(let r=0,a=e.length;r<a;r++)i=Math.max(i,n.distanceToSquared(e[r]));return this.radius=Math.sqrt(i),this}copy(e){return this.center.copy(e.center),this.radius=e.radius,this}isEmpty(){return this.radius<0}makeEmpty(){return this.center.set(0,0,0),this.radius=-1,this}containsPoint(e){return e.distanceToSquared(this.center)<=this.radius*this.radius}distanceToPoint(e){return e.distanceTo(this.center)-this.radius}intersectsSphere(e){let t=this.radius+e.radius;return e.center.distanceToSquared(this.center)<=t*t}intersectsBox(e){return e.intersectsSphere(this)}intersectsPlane(e){return Math.abs(e.distanceToPoint(this.center))<=this.radius}clampPoint(e,t){let n=this.center.distanceToSquared(e);return t.copy(e),n>this.radius*this.radius&&(t.sub(this.center).normalize(),t.multiplyScalar(this.radius).add(this.center)),t}getBoundingBox(e){return this.isEmpty()?(e.makeEmpty(),e):(e.set(this.center,this.center),e.expandByScalar(this.radius),e)}applyMatrix4(e){return this.center.applyMatrix4(e),this.radius=this.radius*e.getMaxScaleOnAxis(),this}translate(e){return this.center.add(e),this}expandByPoint(e){if(this.isEmpty())return this.center.copy(e),this.radius=0,this;zr.subVectors(e,this.center);let t=zr.lengthSq();if(t>this.radius*this.radius){let n=Math.sqrt(t),i=(n-this.radius)*.5;this.center.addScaledVector(zr,i/n),this.radius+=i}return this}union(e){return e.isEmpty()?this:this.isEmpty()?(this.copy(e),this):(this.center.equals(e.center)===!0?this.radius=Math.max(this.radius,e.radius):(Rl.subVectors(e.center,this.center).setLength(e.radius),this.expandByPoint(zr.copy(e.center).add(Rl)),this.expandByPoint(zr.copy(e.center).sub(Rl))),this)}equals(e){return e.center.equals(this.center)&&e.radius===this.radius}clone(){return new this.constructor().copy(this)}toJSON(){return{radius:this.radius,center:this.center.toArray()}}fromJSON(e){return this.radius=e.radius,this.center.fromArray(e.center),this}},di=new L,Cl=new L,Qa=new L,ki=new L,Il=new L,eo=new L,Pl=new L,Sn=class{constructor(e=new L,t=new L(0,0,-1)){this.origin=e,this.direction=t}set(e,t){return this.origin.copy(e),this.direction.copy(t),this}copy(e){return this.origin.copy(e.origin),this.direction.copy(e.direction),this}at(e,t){return t.copy(this.origin).addScaledVector(this.direction,e)}lookAt(e){return this.direction.copy(e).sub(this.origin).normalize(),this}recast(e){return this.origin.copy(this.at(e,di)),this}closestPointToPoint(e,t){t.subVectors(e,this.origin);let n=t.dot(this.direction);return n<0?t.copy(this.origin):t.copy(this.origin).addScaledVector(this.direction,n)}distanceToPoint(e){return Math.sqrt(this.distanceSqToPoint(e))}distanceSqToPoint(e){let t=di.subVectors(e,this.origin).dot(this.direction);return t<0?this.origin.distanceToSquared(e):(di.copy(this.origin).addScaledVector(this.direction,t),di.distanceToSquared(e))}distanceSqToSegment(e,t,n,i){Cl.copy(e).add(t).multiplyScalar(.5),Qa.copy(t).sub(e).normalize(),ki.copy(this.origin).sub(Cl);let r=e.distanceTo(t)*.5,a=-this.direction.dot(Qa),o=ki.dot(this.direction),c=-ki.dot(Qa),l=ki.lengthSq(),u=Math.abs(1-a*a),h,d,f,g;if(u>0)if(h=a*c-o,d=a*o-c,g=r*u,h>=0)if(d>=-g)if(d<=g){let y=1/u;h*=y,d*=y,f=h*(h+a*d+2*o)+d*(a*h+d+2*c)+l}else d=r,h=Math.max(0,-(a*d+o)),f=-h*h+d*(d+2*c)+l;else d=-r,h=Math.max(0,-(a*d+o)),f=-h*h+d*(d+2*c)+l;else d<=-g?(h=Math.max(0,-(-a*r+o)),d=h>0?-r:Math.min(Math.max(-r,-c),r),f=-h*h+d*(d+2*c)+l):d<=g?(h=0,d=Math.min(Math.max(-r,-c),r),f=d*(d+2*c)+l):(h=Math.max(0,-(a*r+o)),d=h>0?r:Math.min(Math.max(-r,-c),r),f=-h*h+d*(d+2*c)+l);else d=a>0?-r:r,h=Math.max(0,-(a*d+o)),f=-h*h+d*(d+2*c)+l;return n&&n.copy(this.origin).addScaledVector(this.direction,h),i&&i.copy(Cl).addScaledVector(Qa,d),f}intersectSphere(e,t){di.subVectors(e.center,this.origin);let n=di.dot(this.direction),i=di.dot(di)-n*n,r=e.radius*e.radius;if(i>r)return null;let a=Math.sqrt(r-i),o=n-a,c=n+a;return c<0?null:o<0?this.at(c,t):this.at(o,t)}intersectsSphere(e){return e.radius<0?!1:this.distanceSqToPoint(e.center)<=e.radius*e.radius}distanceToPlane(e){let t=e.normal.dot(this.direction);if(t===0)return e.distanceToPoint(this.origin)===0?0:null;let n=-(this.origin.dot(e.normal)+e.constant)/t;return n>=0?n:null}intersectPlane(e,t){let n=this.distanceToPlane(e);return n===null?null:this.at(n,t)}intersectsPlane(e){let t=e.distanceToPoint(this.origin);return t===0||e.normal.dot(this.direction)*t<0}intersectBox(e,t){let n,i,r,a,o,c,l=1/this.direction.x,u=1/this.direction.y,h=1/this.direction.z,d=this.origin;return l>=0?(n=(e.min.x-d.x)*l,i=(e.max.x-d.x)*l):(n=(e.max.x-d.x)*l,i=(e.min.x-d.x)*l),u>=0?(r=(e.min.y-d.y)*u,a=(e.max.y-d.y)*u):(r=(e.max.y-d.y)*u,a=(e.min.y-d.y)*u),n>a||r>i||((r>n||isNaN(n))&&(n=r),(a<i||isNaN(i))&&(i=a),h>=0?(o=(e.min.z-d.z)*h,c=(e.max.z-d.z)*h):(o=(e.max.z-d.z)*h,c=(e.min.z-d.z)*h),n>c||o>i)||((o>n||n!==n)&&(n=o),(c<i||i!==i)&&(i=c),i<0)?null:this.at(n>=0?n:i,t)}intersectsBox(e){return this.intersectBox(e,di)!==null}intersectTriangle(e,t,n,i,r){Il.subVectors(t,e),eo.subVectors(n,e),Pl.crossVectors(Il,eo);let a=this.direction.dot(Pl),o;if(a>0){if(i)return null;o=1}else if(a<0)o=-1,a=-a;else return null;ki.subVectors(this.origin,e);let c=o*this.direction.dot(eo.crossVectors(ki,eo));if(c<0)return null;let l=o*this.direction.dot(Il.cross(ki));if(l<0||c+l>a)return null;let u=-o*ki.dot(Pl);return u<0?null:this.at(u/a,r)}applyMatrix4(e){return this.origin.applyMatrix4(e),this.direction.transformDirection(e),this}equals(e){return e.origin.equals(this.origin)&&e.direction.equals(this.direction)}clone(){return new this.constructor().copy(this)}},ke=class s{constructor(e,t,n,i,r,a,o,c,l,u,h,d,f,g,y,m){s.prototype.isMatrix4=!0,this.elements=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1],e!==void 0&&this.set(e,t,n,i,r,a,o,c,l,u,h,d,f,g,y,m)}set(e,t,n,i,r,a,o,c,l,u,h,d,f,g,y,m){let p=this.elements;return p[0]=e,p[4]=t,p[8]=n,p[12]=i,p[1]=r,p[5]=a,p[9]=o,p[13]=c,p[2]=l,p[6]=u,p[10]=h,p[14]=d,p[3]=f,p[7]=g,p[11]=y,p[15]=m,this}identity(){return this.set(1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1),this}clone(){return new s().fromArray(this.elements)}copy(e){let t=this.elements,n=e.elements;return t[0]=n[0],t[1]=n[1],t[2]=n[2],t[3]=n[3],t[4]=n[4],t[5]=n[5],t[6]=n[6],t[7]=n[7],t[8]=n[8],t[9]=n[9],t[10]=n[10],t[11]=n[11],t[12]=n[12],t[13]=n[13],t[14]=n[14],t[15]=n[15],this}copyPosition(e){let t=this.elements,n=e.elements;return t[12]=n[12],t[13]=n[13],t[14]=n[14],this}setFromMatrix3(e){let t=e.elements;return this.set(t[0],t[3],t[6],0,t[1],t[4],t[7],0,t[2],t[5],t[8],0,0,0,0,1),this}extractBasis(e,t,n){return e.setFromMatrixColumn(this,0),t.setFromMatrixColumn(this,1),n.setFromMatrixColumn(this,2),this}makeBasis(e,t,n){return this.set(e.x,t.x,n.x,0,e.y,t.y,n.y,0,e.z,t.z,n.z,0,0,0,0,1),this}extractRotation(e){let t=this.elements,n=e.elements,i=1/Ns.setFromMatrixColumn(e,0).length(),r=1/Ns.setFromMatrixColumn(e,1).length(),a=1/Ns.setFromMatrixColumn(e,2).length();return t[0]=n[0]*i,t[1]=n[1]*i,t[2]=n[2]*i,t[3]=0,t[4]=n[4]*r,t[5]=n[5]*r,t[6]=n[6]*r,t[7]=0,t[8]=n[8]*a,t[9]=n[9]*a,t[10]=n[10]*a,t[11]=0,t[12]=0,t[13]=0,t[14]=0,t[15]=1,this}makeRotationFromEuler(e){let t=this.elements,n=e.x,i=e.y,r=e.z,a=Math.cos(n),o=Math.sin(n),c=Math.cos(i),l=Math.sin(i),u=Math.cos(r),h=Math.sin(r);if(e.order==="XYZ"){let d=a*u,f=a*h,g=o*u,y=o*h;t[0]=c*u,t[4]=-c*h,t[8]=l,t[1]=f+g*l,t[5]=d-y*l,t[9]=-o*c,t[2]=y-d*l,t[6]=g+f*l,t[10]=a*c}else if(e.order==="YXZ"){let d=c*u,f=c*h,g=l*u,y=l*h;t[0]=d+y*o,t[4]=g*o-f,t[8]=a*l,t[1]=a*h,t[5]=a*u,t[9]=-o,t[2]=f*o-g,t[6]=y+d*o,t[10]=a*c}else if(e.order==="ZXY"){let d=c*u,f=c*h,g=l*u,y=l*h;t[0]=d-y*o,t[4]=-a*h,t[8]=g+f*o,t[1]=f+g*o,t[5]=a*u,t[9]=y-d*o,t[2]=-a*l,t[6]=o,t[10]=a*c}else if(e.order==="ZYX"){let d=a*u,f=a*h,g=o*u,y=o*h;t[0]=c*u,t[4]=g*l-f,t[8]=d*l+y,t[1]=c*h,t[5]=y*l+d,t[9]=f*l-g,t[2]=-l,t[6]=o*c,t[10]=a*c}else if(e.order==="YZX"){let d=a*c,f=a*l,g=o*c,y=o*l;t[0]=c*u,t[4]=y-d*h,t[8]=g*h+f,t[1]=h,t[5]=a*u,t[9]=-o*u,t[2]=-l*u,t[6]=f*h+g,t[10]=d-y*h}else if(e.order==="XZY"){let d=a*c,f=a*l,g=o*c,y=o*l;t[0]=c*u,t[4]=-h,t[8]=l*u,t[1]=d*h+y,t[5]=a*u,t[9]=f*h-g,t[2]=g*h-f,t[6]=o*u,t[10]=y*h+d}return t[3]=0,t[7]=0,t[11]=0,t[12]=0,t[13]=0,t[14]=0,t[15]=1,this}makeRotationFromQuaternion(e){return this.compose(ig,e,sg)}lookAt(e,t,n){let i=this.elements;return wn.subVectors(e,t),wn.lengthSq()===0&&(wn.z=1),wn.normalize(),Li.crossVectors(n,wn),Li.lengthSq()===0&&(Math.abs(n.z)===1?wn.x+=1e-4:wn.z+=1e-4,wn.normalize(),Li.crossVectors(n,wn)),Li.normalize(),to.crossVectors(wn,Li),i[0]=Li.x,i[4]=to.x,i[8]=wn.x,i[1]=Li.y,i[5]=to.y,i[9]=wn.y,i[2]=Li.z,i[6]=to.z,i[10]=wn.z,this}multiply(e){return this.multiplyMatrices(this,e)}premultiply(e){return this.multiplyMatrices(e,this)}multiplyMatrices(e,t){let n=e.elements,i=t.elements,r=this.elements,a=n[0],o=n[4],c=n[8],l=n[12],u=n[1],h=n[5],d=n[9],f=n[13],g=n[2],y=n[6],m=n[10],p=n[14],x=n[3],v=n[7],b=n[11],S=n[15],w=i[0],T=i[4],A=i[8],M=i[12],_=i[1],I=i[5],C=i[9],D=i[13],N=i[2],U=i[6],B=i[10],J=i[14],V=i[3],ne=i[7],ue=i[11],_e=i[15];return r[0]=a*w+o*_+c*N+l*V,r[4]=a*T+o*I+c*U+l*ne,r[8]=a*A+o*C+c*B+l*ue,r[12]=a*M+o*D+c*J+l*_e,r[1]=u*w+h*_+d*N+f*V,r[5]=u*T+h*I+d*U+f*ne,r[9]=u*A+h*C+d*B+f*ue,r[13]=u*M+h*D+d*J+f*_e,r[2]=g*w+y*_+m*N+p*V,r[6]=g*T+y*I+m*U+p*ne,r[10]=g*A+y*C+m*B+p*ue,r[14]=g*M+y*D+m*J+p*_e,r[3]=x*w+v*_+b*N+S*V,r[7]=x*T+v*I+b*U+S*ne,r[11]=x*A+v*C+b*B+S*ue,r[15]=x*M+v*D+b*J+S*_e,this}multiplyScalar(e){let t=this.elements;return t[0]*=e,t[4]*=e,t[8]*=e,t[12]*=e,t[1]*=e,t[5]*=e,t[9]*=e,t[13]*=e,t[2]*=e,t[6]*=e,t[10]*=e,t[14]*=e,t[3]*=e,t[7]*=e,t[11]*=e,t[15]*=e,this}determinant(){let e=this.elements,t=e[0],n=e[4],i=e[8],r=e[12],a=e[1],o=e[5],c=e[9],l=e[13],u=e[2],h=e[6],d=e[10],f=e[14],g=e[3],y=e[7],m=e[11],p=e[15];return g*(+r*c*h-i*l*h-r*o*d+n*l*d+i*o*f-n*c*f)+y*(+t*c*f-t*l*d+r*a*d-i*a*f+i*l*u-r*c*u)+m*(+t*l*h-t*o*f-r*a*h+n*a*f+r*o*u-n*l*u)+p*(-i*o*u-t*c*h+t*o*d+i*a*h-n*a*d+n*c*u)}transpose(){let e=this.elements,t;return t=e[1],e[1]=e[4],e[4]=t,t=e[2],e[2]=e[8],e[8]=t,t=e[6],e[6]=e[9],e[9]=t,t=e[3],e[3]=e[12],e[12]=t,t=e[7],e[7]=e[13],e[13]=t,t=e[11],e[11]=e[14],e[14]=t,this}setPosition(e,t,n){let i=this.elements;return e.isVector3?(i[12]=e.x,i[13]=e.y,i[14]=e.z):(i[12]=e,i[13]=t,i[14]=n),this}invert(){let e=this.elements,t=e[0],n=e[1],i=e[2],r=e[3],a=e[4],o=e[5],c=e[6],l=e[7],u=e[8],h=e[9],d=e[10],f=e[11],g=e[12],y=e[13],m=e[14],p=e[15],x=h*m*l-y*d*l+y*c*f-o*m*f-h*c*p+o*d*p,v=g*d*l-u*m*l-g*c*f+a*m*f+u*c*p-a*d*p,b=u*y*l-g*h*l+g*o*f-a*y*f-u*o*p+a*h*p,S=g*h*c-u*y*c-g*o*d+a*y*d+u*o*m-a*h*m,w=t*x+n*v+i*b+r*S;if(w===0)return this.set(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0);let T=1/w;return e[0]=x*T,e[1]=(y*d*r-h*m*r-y*i*f+n*m*f+h*i*p-n*d*p)*T,e[2]=(o*m*r-y*c*r+y*i*l-n*m*l-o*i*p+n*c*p)*T,e[3]=(h*c*r-o*d*r-h*i*l+n*d*l+o*i*f-n*c*f)*T,e[4]=v*T,e[5]=(u*m*r-g*d*r+g*i*f-t*m*f-u*i*p+t*d*p)*T,e[6]=(g*c*r-a*m*r-g*i*l+t*m*l+a*i*p-t*c*p)*T,e[7]=(a*d*r-u*c*r+u*i*l-t*d*l-a*i*f+t*c*f)*T,e[8]=b*T,e[9]=(g*h*r-u*y*r-g*n*f+t*y*f+u*n*p-t*h*p)*T,e[10]=(a*y*r-g*o*r+g*n*l-t*y*l-a*n*p+t*o*p)*T,e[11]=(u*o*r-a*h*r-u*n*l+t*h*l+a*n*f-t*o*f)*T,e[12]=S*T,e[13]=(u*y*i-g*h*i+g*n*d-t*y*d-u*n*m+t*h*m)*T,e[14]=(g*o*i-a*y*i-g*n*c+t*y*c+a*n*m-t*o*m)*T,e[15]=(a*h*i-u*o*i+u*n*c-t*h*c-a*n*d+t*o*d)*T,this}scale(e){let t=this.elements,n=e.x,i=e.y,r=e.z;return t[0]*=n,t[4]*=i,t[8]*=r,t[1]*=n,t[5]*=i,t[9]*=r,t[2]*=n,t[6]*=i,t[10]*=r,t[3]*=n,t[7]*=i,t[11]*=r,this}getMaxScaleOnAxis(){let e=this.elements,t=e[0]*e[0]+e[1]*e[1]+e[2]*e[2],n=e[4]*e[4]+e[5]*e[5]+e[6]*e[6],i=e[8]*e[8]+e[9]*e[9]+e[10]*e[10];return Math.sqrt(Math.max(t,n,i))}makeTranslation(e,t,n){return e.isVector3?this.set(1,0,0,e.x,0,1,0,e.y,0,0,1,e.z,0,0,0,1):this.set(1,0,0,e,0,1,0,t,0,0,1,n,0,0,0,1),this}makeRotationX(e){let t=Math.cos(e),n=Math.sin(e);return this.set(1,0,0,0,0,t,-n,0,0,n,t,0,0,0,0,1),this}makeRotationY(e){let t=Math.cos(e),n=Math.sin(e);return this.set(t,0,n,0,0,1,0,0,-n,0,t,0,0,0,0,1),this}makeRotationZ(e){let t=Math.cos(e),n=Math.sin(e);return this.set(t,-n,0,0,n,t,0,0,0,0,1,0,0,0,0,1),this}makeRotationAxis(e,t){let n=Math.cos(t),i=Math.sin(t),r=1-n,a=e.x,o=e.y,c=e.z,l=r*a,u=r*o;return this.set(l*a+n,l*o-i*c,l*c+i*o,0,l*o+i*c,u*o+n,u*c-i*a,0,l*c-i*o,u*c+i*a,r*c*c+n,0,0,0,0,1),this}makeScale(e,t,n){return this.set(e,0,0,0,0,t,0,0,0,0,n,0,0,0,0,1),this}makeShear(e,t,n,i,r,a){return this.set(1,n,r,0,e,1,a,0,t,i,1,0,0,0,0,1),this}compose(e,t,n){let i=this.elements,r=t._x,a=t._y,o=t._z,c=t._w,l=r+r,u=a+a,h=o+o,d=r*l,f=r*u,g=r*h,y=a*u,m=a*h,p=o*h,x=c*l,v=c*u,b=c*h,S=n.x,w=n.y,T=n.z;return i[0]=(1-(y+p))*S,i[1]=(f+b)*S,i[2]=(g-v)*S,i[3]=0,i[4]=(f-b)*w,i[5]=(1-(d+p))*w,i[6]=(m+x)*w,i[7]=0,i[8]=(g+v)*T,i[9]=(m-x)*T,i[10]=(1-(d+y))*T,i[11]=0,i[12]=e.x,i[13]=e.y,i[14]=e.z,i[15]=1,this}decompose(e,t,n){let i=this.elements,r=Ns.set(i[0],i[1],i[2]).length(),a=Ns.set(i[4],i[5],i[6]).length(),o=Ns.set(i[8],i[9],i[10]).length();this.determinant()<0&&(r=-r),e.x=i[12],e.y=i[13],e.z=i[14],Hn.copy(this);let l=1/r,u=1/a,h=1/o;return Hn.elements[0]*=l,Hn.elements[1]*=l,Hn.elements[2]*=l,Hn.elements[4]*=u,Hn.elements[5]*=u,Hn.elements[6]*=u,Hn.elements[8]*=h,Hn.elements[9]*=h,Hn.elements[10]*=h,t.setFromRotationMatrix(Hn),n.x=r,n.y=a,n.z=o,this}makePerspective(e,t,n,i,r,a,o=Wn,c=!1){let l=this.elements,u=2*r/(t-e),h=2*r/(n-i),d=(t+e)/(t-e),f=(n+i)/(n-i),g,y;if(c)g=r/(a-r),y=a*r/(a-r);else if(o===Wn)g=-(a+r)/(a-r),y=-2*a*r/(a-r);else if(o===Zr)g=-a/(a-r),y=-a*r/(a-r);else throw new Error("THREE.Matrix4.makePerspective(): Invalid coordinate system: "+o);return l[0]=u,l[4]=0,l[8]=d,l[12]=0,l[1]=0,l[5]=h,l[9]=f,l[13]=0,l[2]=0,l[6]=0,l[10]=g,l[14]=y,l[3]=0,l[7]=0,l[11]=-1,l[15]=0,this}makeOrthographic(e,t,n,i,r,a,o=Wn,c=!1){let l=this.elements,u=2/(t-e),h=2/(n-i),d=-(t+e)/(t-e),f=-(n+i)/(n-i),g,y;if(c)g=1/(a-r),y=a/(a-r);else if(o===Wn)g=-2/(a-r),y=-(a+r)/(a-r);else if(o===Zr)g=-1/(a-r),y=-r/(a-r);else throw new Error("THREE.Matrix4.makeOrthographic(): Invalid coordinate system: "+o);return l[0]=u,l[4]=0,l[8]=0,l[12]=d,l[1]=0,l[5]=h,l[9]=0,l[13]=f,l[2]=0,l[6]=0,l[10]=g,l[14]=y,l[3]=0,l[7]=0,l[11]=0,l[15]=1,this}equals(e){let t=this.elements,n=e.elements;for(let i=0;i<16;i++)if(t[i]!==n[i])return!1;return!0}fromArray(e,t=0){for(let n=0;n<16;n++)this.elements[n]=e[n+t];return this}toArray(e=[],t=0){let n=this.elements;return e[t]=n[0],e[t+1]=n[1],e[t+2]=n[2],e[t+3]=n[3],e[t+4]=n[4],e[t+5]=n[5],e[t+6]=n[6],e[t+7]=n[7],e[t+8]=n[8],e[t+9]=n[9],e[t+10]=n[10],e[t+11]=n[11],e[t+12]=n[12],e[t+13]=n[13],e[t+14]=n[14],e[t+15]=n[15],e}},Ns=new L,Hn=new ke,ig=new L(0,0,0),sg=new L(1,1,1),Li=new L,to=new L,wn=new L,dd=new ke,fd=new Ln,Dn=class s{constructor(e=0,t=0,n=0,i=s.DEFAULT_ORDER){this.isEuler=!0,this._x=e,this._y=t,this._z=n,this._order=i}get x(){return this._x}set x(e){this._x=e,this._onChangeCallback()}get y(){return this._y}set y(e){this._y=e,this._onChangeCallback()}get z(){return this._z}set z(e){this._z=e,this._onChangeCallback()}get order(){return this._order}set order(e){this._order=e,this._onChangeCallback()}set(e,t,n,i=this._order){return this._x=e,this._y=t,this._z=n,this._order=i,this._onChangeCallback(),this}clone(){return new this.constructor(this._x,this._y,this._z,this._order)}copy(e){return this._x=e._x,this._y=e._y,this._z=e._z,this._order=e._order,this._onChangeCallback(),this}setFromRotationMatrix(e,t=this._order,n=!0){let i=e.elements,r=i[0],a=i[4],o=i[8],c=i[1],l=i[5],u=i[9],h=i[2],d=i[6],f=i[10];switch(t){case"XYZ":this._y=Math.asin(We(o,-1,1)),Math.abs(o)<.9999999?(this._x=Math.atan2(-u,f),this._z=Math.atan2(-a,r)):(this._x=Math.atan2(d,l),this._z=0);break;case"YXZ":this._x=Math.asin(-We(u,-1,1)),Math.abs(u)<.9999999?(this._y=Math.atan2(o,f),this._z=Math.atan2(c,l)):(this._y=Math.atan2(-h,r),this._z=0);break;case"ZXY":this._x=Math.asin(We(d,-1,1)),Math.abs(d)<.9999999?(this._y=Math.atan2(-h,f),this._z=Math.atan2(-a,l)):(this._y=0,this._z=Math.atan2(c,r));break;case"ZYX":this._y=Math.asin(-We(h,-1,1)),Math.abs(h)<.9999999?(this._x=Math.atan2(d,f),this._z=Math.atan2(c,r)):(this._x=0,this._z=Math.atan2(-a,l));break;case"YZX":this._z=Math.asin(We(c,-1,1)),Math.abs(c)<.9999999?(this._x=Math.atan2(-u,l),this._y=Math.atan2(-h,r)):(this._x=0,this._y=Math.atan2(o,f));break;case"XZY":this._z=Math.asin(-We(a,-1,1)),Math.abs(a)<.9999999?(this._x=Math.atan2(d,l),this._y=Math.atan2(o,r)):(this._x=Math.atan2(-u,f),this._y=0);break;default:console.warn("THREE.Euler: .setFromRotationMatrix() encountered an unknown order: "+t)}return this._order=t,n===!0&&this._onChangeCallback(),this}setFromQuaternion(e,t,n){return dd.makeRotationFromQuaternion(e),this.setFromRotationMatrix(dd,t,n)}setFromVector3(e,t=this._order){return this.set(e.x,e.y,e.z,t)}reorder(e){return fd.setFromEuler(this),this.setFromQuaternion(fd,e)}equals(e){return e._x===this._x&&e._y===this._y&&e._z===this._z&&e._order===this._order}fromArray(e){return this._x=e[0],this._y=e[1],this._z=e[2],e[3]!==void 0&&(this._order=e[3]),this._onChangeCallback(),this}toArray(e=[],t=0){return e[t]=this._x,e[t+1]=this._y,e[t+2]=this._z,e[t+3]=this._order,e}_onChange(e){return this._onChangeCallback=e,this}_onChangeCallback(){}*[Symbol.iterator](){yield this._x,yield this._y,yield this._z,yield this._order}};Dn.DEFAULT_ORDER="XYZ";var Qs=class{constructor(){this.mask=1}set(e){this.mask=(1<<e|0)>>>0}enable(e){this.mask|=1<<e|0}enableAll(){this.mask=-1}toggle(e){this.mask^=1<<e|0}disable(e){this.mask&=~(1<<e|0)}disableAll(){this.mask=0}test(e){return(this.mask&e.mask)!==0}isEnabled(e){return(this.mask&(1<<e|0))!==0}},rg=0,pd=new L,Fs=new Ln,fi=new ke,no=new L,Hr=new L,ag=new L,og=new Ln,md=new L(1,0,0),gd=new L(0,1,0),bd=new L(0,0,1),yd={type:"added"},cg={type:"removed"},Us={type:"childadded",child:null},kl={type:"childremoved",child:null},Et=class s extends xi{constructor(){super(),this.isObject3D=!0,Object.defineProperty(this,"id",{value:rg++}),this.uuid=Yn(),this.name="",this.type="Object3D",this.parent=null,this.children=[],this.up=s.DEFAULT_UP.clone();let e=new L,t=new Dn,n=new Ln,i=new L(1,1,1);function r(){n.setFromEuler(t,!1)}function a(){t.setFromQuaternion(n,void 0,!1)}t._onChange(r),n._onChange(a),Object.defineProperties(this,{position:{configurable:!0,enumerable:!0,value:e},rotation:{configurable:!0,enumerable:!0,value:t},quaternion:{configurable:!0,enumerable:!0,value:n},scale:{configurable:!0,enumerable:!0,value:i},modelViewMatrix:{value:new ke},normalMatrix:{value:new qe}}),this.matrix=new ke,this.matrixWorld=new ke,this.matrixAutoUpdate=s.DEFAULT_MATRIX_AUTO_UPDATE,this.matrixWorldAutoUpdate=s.DEFAULT_MATRIX_WORLD_AUTO_UPDATE,this.matrixWorldNeedsUpdate=!1,this.layers=new Qs,this.visible=!0,this.castShadow=!1,this.receiveShadow=!1,this.frustumCulled=!0,this.renderOrder=0,this.animations=[],this.customDepthMaterial=void 0,this.customDistanceMaterial=void 0,this.userData={}}onBeforeShadow(){}onAfterShadow(){}onBeforeRender(){}onAfterRender(){}applyMatrix4(e){this.matrixAutoUpdate&&this.updateMatrix(),this.matrix.premultiply(e),this.matrix.decompose(this.position,this.quaternion,this.scale)}applyQuaternion(e){return this.quaternion.premultiply(e),this}setRotationFromAxisAngle(e,t){this.quaternion.setFromAxisAngle(e,t)}setRotationFromEuler(e){this.quaternion.setFromEuler(e,!0)}setRotationFromMatrix(e){this.quaternion.setFromRotationMatrix(e)}setRotationFromQuaternion(e){this.quaternion.copy(e)}rotateOnAxis(e,t){return Fs.setFromAxisAngle(e,t),this.quaternion.multiply(Fs),this}rotateOnWorldAxis(e,t){return Fs.setFromAxisAngle(e,t),this.quaternion.premultiply(Fs),this}rotateX(e){return this.rotateOnAxis(md,e)}rotateY(e){return this.rotateOnAxis(gd,e)}rotateZ(e){return this.rotateOnAxis(bd,e)}translateOnAxis(e,t){return pd.copy(e).applyQuaternion(this.quaternion),this.position.add(pd.multiplyScalar(t)),this}translateX(e){return this.translateOnAxis(md,e)}translateY(e){return this.translateOnAxis(gd,e)}translateZ(e){return this.translateOnAxis(bd,e)}localToWorld(e){return this.updateWorldMatrix(!0,!1),e.applyMatrix4(this.matrixWorld)}worldToLocal(e){return this.updateWorldMatrix(!0,!1),e.applyMatrix4(fi.copy(this.matrixWorld).invert())}lookAt(e,t,n){e.isVector3?no.copy(e):no.set(e,t,n);let i=this.parent;this.updateWorldMatrix(!0,!1),Hr.setFromMatrixPosition(this.matrixWorld),this.isCamera||this.isLight?fi.lookAt(Hr,no,this.up):fi.lookAt(no,Hr,this.up),this.quaternion.setFromRotationMatrix(fi),i&&(fi.extractRotation(i.matrixWorld),Fs.setFromRotationMatrix(fi),this.quaternion.premultiply(Fs.invert()))}add(e){if(arguments.length>1){for(let t=0;t<arguments.length;t++)this.add(arguments[t]);return this}return e===this?(console.error("THREE.Object3D.add: object can't be added as a child of itself.",e),this):(e&&e.isObject3D?(e.removeFromParent(),e.parent=this,this.children.push(e),e.dispatchEvent(yd),Us.child=e,this.dispatchEvent(Us),Us.child=null):console.error("THREE.Object3D.add: object not an instance of THREE.Object3D.",e),this)}remove(e){if(arguments.length>1){for(let n=0;n<arguments.length;n++)this.remove(arguments[n]);return this}let t=this.children.indexOf(e);return t!==-1&&(e.parent=null,this.children.splice(t,1),e.dispatchEvent(cg),kl.child=e,this.dispatchEvent(kl),kl.child=null),this}removeFromParent(){let e=this.parent;return e!==null&&e.remove(this),this}clear(){return this.remove(...this.children)}attach(e){return this.updateWorldMatrix(!0,!1),fi.copy(this.matrixWorld).invert(),e.parent!==null&&(e.parent.updateWorldMatrix(!0,!1),fi.multiply(e.parent.matrixWorld)),e.applyMatrix4(fi),e.removeFromParent(),e.parent=this,this.children.push(e),e.updateWorldMatrix(!1,!0),e.dispatchEvent(yd),Us.child=e,this.dispatchEvent(Us),Us.child=null,this}getObjectById(e){return this.getObjectByProperty("id",e)}getObjectByName(e){return this.getObjectByProperty("name",e)}getObjectByProperty(e,t){if(this[e]===t)return this;for(let n=0,i=this.children.length;n<i;n++){let a=this.children[n].getObjectByProperty(e,t);if(a!==void 0)return a}}getObjectsByProperty(e,t,n=[]){this[e]===t&&n.push(this);let i=this.children;for(let r=0,a=i.length;r<a;r++)i[r].getObjectsByProperty(e,t,n);return n}getWorldPosition(e){return this.updateWorldMatrix(!0,!1),e.setFromMatrixPosition(this.matrixWorld)}getWorldQuaternion(e){return this.updateWorldMatrix(!0,!1),this.matrixWorld.decompose(Hr,e,ag),e}getWorldScale(e){return this.updateWorldMatrix(!0,!1),this.matrixWorld.decompose(Hr,og,e),e}getWorldDirection(e){this.updateWorldMatrix(!0,!1);let t=this.matrixWorld.elements;return e.set(t[8],t[9],t[10]).normalize()}raycast(){}traverse(e){e(this);let t=this.children;for(let n=0,i=t.length;n<i;n++)t[n].traverse(e)}traverseVisible(e){if(this.visible===!1)return;e(this);let t=this.children;for(let n=0,i=t.length;n<i;n++)t[n].traverseVisible(e)}traverseAncestors(e){let t=this.parent;t!==null&&(e(t),t.traverseAncestors(e))}updateMatrix(){this.matrix.compose(this.position,this.quaternion,this.scale),this.matrixWorldNeedsUpdate=!0}updateMatrixWorld(e){this.matrixAutoUpdate&&this.updateMatrix(),(this.matrixWorldNeedsUpdate||e)&&(this.matrixWorldAutoUpdate===!0&&(this.parent===null?this.matrixWorld.copy(this.matrix):this.matrixWorld.multiplyMatrices(this.parent.matrixWorld,this.matrix)),this.matrixWorldNeedsUpdate=!1,e=!0);let t=this.children;for(let n=0,i=t.length;n<i;n++)t[n].updateMatrixWorld(e)}updateWorldMatrix(e,t){let n=this.parent;if(e===!0&&n!==null&&n.updateWorldMatrix(!0,!1),this.matrixAutoUpdate&&this.updateMatrix(),this.matrixWorldAutoUpdate===!0&&(this.parent===null?this.matrixWorld.copy(this.matrix):this.matrixWorld.multiplyMatrices(this.parent.matrixWorld,this.matrix)),t===!0){let i=this.children;for(let r=0,a=i.length;r<a;r++)i[r].updateWorldMatrix(!1,!0)}}toJSON(e){let t=e===void 0||typeof e=="string",n={};t&&(e={geometries:{},materials:{},textures:{},images:{},shapes:{},skeletons:{},animations:{},nodes:{}},n.metadata={version:4.7,type:"Object",generator:"Object3D.toJSON"});let i={};i.uuid=this.uuid,i.type=this.type,this.name!==""&&(i.name=this.name),this.castShadow===!0&&(i.castShadow=!0),this.receiveShadow===!0&&(i.receiveShadow=!0),this.visible===!1&&(i.visible=!1),this.frustumCulled===!1&&(i.frustumCulled=!1),this.renderOrder!==0&&(i.renderOrder=this.renderOrder),Object.keys(this.userData).length>0&&(i.userData=this.userData),i.layers=this.layers.mask,i.matrix=this.matrix.toArray(),i.up=this.up.toArray(),this.matrixAutoUpdate===!1&&(i.matrixAutoUpdate=!1),this.isInstancedMesh&&(i.type="InstancedMesh",i.count=this.count,i.instanceMatrix=this.instanceMatrix.toJSON(),this.instanceColor!==null&&(i.instanceColor=this.instanceColor.toJSON())),this.isBatchedMesh&&(i.type="BatchedMesh",i.perObjectFrustumCulled=this.perObjectFrustumCulled,i.sortObjects=this.sortObjects,i.drawRanges=this._drawRanges,i.reservedRanges=this._reservedRanges,i.geometryInfo=this._geometryInfo.map(o=>({...o,boundingBox:o.boundingBox?o.boundingBox.toJSON():void 0,boundingSphere:o.boundingSphere?o.boundingSphere.toJSON():void 0})),i.instanceInfo=this._instanceInfo.map(o=>({...o})),i.availableInstanceIds=this._availableInstanceIds.slice(),i.availableGeometryIds=this._availableGeometryIds.slice(),i.nextIndexStart=this._nextIndexStart,i.nextVertexStart=this._nextVertexStart,i.geometryCount=this._geometryCount,i.maxInstanceCount=this._maxInstanceCount,i.maxVertexCount=this._maxVertexCount,i.maxIndexCount=this._maxIndexCount,i.geometryInitialized=this._geometryInitialized,i.matricesTexture=this._matricesTexture.toJSON(e),i.indirectTexture=this._indirectTexture.toJSON(e),this._colorsTexture!==null&&(i.colorsTexture=this._colorsTexture.toJSON(e)),this.boundingSphere!==null&&(i.boundingSphere=this.boundingSphere.toJSON()),this.boundingBox!==null&&(i.boundingBox=this.boundingBox.toJSON()));function r(o,c){return o[c.uuid]===void 0&&(o[c.uuid]=c.toJSON(e)),c.uuid}if(this.isScene)this.background&&(this.background.isColor?i.background=this.background.toJSON():this.background.isTexture&&(i.background=this.background.toJSON(e).uuid)),this.environment&&this.environment.isTexture&&this.environment.isRenderTargetTexture!==!0&&(i.environment=this.environment.toJSON(e).uuid);else if(this.isMesh||this.isLine||this.isPoints){i.geometry=r(e.geometries,this.geometry);let o=this.geometry.parameters;if(o!==void 0&&o.shapes!==void 0){let c=o.shapes;if(Array.isArray(c))for(let l=0,u=c.length;l<u;l++){let h=c[l];r(e.shapes,h)}else r(e.shapes,c)}}if(this.isSkinnedMesh&&(i.bindMode=this.bindMode,i.bindMatrix=this.bindMatrix.toArray(),this.skeleton!==void 0&&(r(e.skeletons,this.skeleton),i.skeleton=this.skeleton.uuid)),this.material!==void 0)if(Array.isArray(this.material)){let o=[];for(let c=0,l=this.material.length;c<l;c++)o.push(r(e.materials,this.material[c]));i.material=o}else i.material=r(e.materials,this.material);if(this.children.length>0){i.children=[];for(let o=0;o<this.children.length;o++)i.children.push(this.children[o].toJSON(e).object)}if(this.animations.length>0){i.animations=[];for(let o=0;o<this.animations.length;o++){let c=this.animations[o];i.animations.push(r(e.animations,c))}}if(t){let o=a(e.geometries),c=a(e.materials),l=a(e.textures),u=a(e.images),h=a(e.shapes),d=a(e.skeletons),f=a(e.animations),g=a(e.nodes);o.length>0&&(n.geometries=o),c.length>0&&(n.materials=c),l.length>0&&(n.textures=l),u.length>0&&(n.images=u),h.length>0&&(n.shapes=h),d.length>0&&(n.skeletons=d),f.length>0&&(n.animations=f),g.length>0&&(n.nodes=g)}return n.object=i,n;function a(o){let c=[];for(let l in o){let u=o[l];delete u.metadata,c.push(u)}return c}}clone(e){return new this.constructor().copy(this,e)}copy(e,t=!0){if(this.name=e.name,this.up.copy(e.up),this.position.copy(e.position),this.rotation.order=e.rotation.order,this.quaternion.copy(e.quaternion),this.scale.copy(e.scale),this.matrix.copy(e.matrix),this.matrixWorld.copy(e.matrixWorld),this.matrixAutoUpdate=e.matrixAutoUpdate,this.matrixWorldAutoUpdate=e.matrixWorldAutoUpdate,this.matrixWorldNeedsUpdate=e.matrixWorldNeedsUpdate,this.layers.mask=e.layers.mask,this.visible=e.visible,this.castShadow=e.castShadow,this.receiveShadow=e.receiveShadow,this.frustumCulled=e.frustumCulled,this.renderOrder=e.renderOrder,this.animations=e.animations.slice(),this.userData=JSON.parse(JSON.stringify(e.userData)),t===!0)for(let n=0;n<e.children.length;n++){let i=e.children[n];this.add(i.clone())}return this}};Et.DEFAULT_UP=new L(0,1,0);Et.DEFAULT_MATRIX_AUTO_UPDATE=!0;Et.DEFAULT_MATRIX_WORLD_AUTO_UPDATE=!0;var Vn=new L,pi=new L,Ll=new L,mi=new L,Bs=new L,Os=new L,xd=new L,Dl=new L,Nl=new L,Fl=new L,Ul=new tt,Bl=new tt,Ol=new tt,en=class s{constructor(e=new L,t=new L,n=new L){this.a=e,this.b=t,this.c=n}static getNormal(e,t,n,i){i.subVectors(n,t),Vn.subVectors(e,t),i.cross(Vn);let r=i.lengthSq();return r>0?i.multiplyScalar(1/Math.sqrt(r)):i.set(0,0,0)}static getBarycoord(e,t,n,i,r){Vn.subVectors(i,t),pi.subVectors(n,t),Ll.subVectors(e,t);let a=Vn.dot(Vn),o=Vn.dot(pi),c=Vn.dot(Ll),l=pi.dot(pi),u=pi.dot(Ll),h=a*l-o*o;if(h===0)return r.set(0,0,0),null;let d=1/h,f=(l*c-o*u)*d,g=(a*u-o*c)*d;return r.set(1-f-g,g,f)}static containsPoint(e,t,n,i){return this.getBarycoord(e,t,n,i,mi)===null?!1:mi.x>=0&&mi.y>=0&&mi.x+mi.y<=1}static getInterpolation(e,t,n,i,r,a,o,c){return this.getBarycoord(e,t,n,i,mi)===null?(c.x=0,c.y=0,"z"in c&&(c.z=0),"w"in c&&(c.w=0),null):(c.setScalar(0),c.addScaledVector(r,mi.x),c.addScaledVector(a,mi.y),c.addScaledVector(o,mi.z),c)}static getInterpolatedAttribute(e,t,n,i,r,a){return Ul.setScalar(0),Bl.setScalar(0),Ol.setScalar(0),Ul.fromBufferAttribute(e,t),Bl.fromBufferAttribute(e,n),Ol.fromBufferAttribute(e,i),a.setScalar(0),a.addScaledVector(Ul,r.x),a.addScaledVector(Bl,r.y),a.addScaledVector(Ol,r.z),a}static isFrontFacing(e,t,n,i){return Vn.subVectors(n,t),pi.subVectors(e,t),Vn.cross(pi).dot(i)<0}set(e,t,n){return this.a.copy(e),this.b.copy(t),this.c.copy(n),this}setFromPointsAndIndices(e,t,n,i){return this.a.copy(e[t]),this.b.copy(e[n]),this.c.copy(e[i]),this}setFromAttributeAndIndices(e,t,n,i){return this.a.fromBufferAttribute(e,t),this.b.fromBufferAttribute(e,n),this.c.fromBufferAttribute(e,i),this}clone(){return new this.constructor().copy(this)}copy(e){return this.a.copy(e.a),this.b.copy(e.b),this.c.copy(e.c),this}getArea(){return Vn.subVectors(this.c,this.b),pi.subVectors(this.a,this.b),Vn.cross(pi).length()*.5}getMidpoint(e){return e.addVectors(this.a,this.b).add(this.c).multiplyScalar(1/3)}getNormal(e){return s.getNormal(this.a,this.b,this.c,e)}getPlane(e){return e.setFromCoplanarPoints(this.a,this.b,this.c)}getBarycoord(e,t){return s.getBarycoord(e,this.a,this.b,this.c,t)}getInterpolation(e,t,n,i,r){return s.getInterpolation(e,this.a,this.b,this.c,t,n,i,r)}containsPoint(e){return s.containsPoint(e,this.a,this.b,this.c)}isFrontFacing(e){return s.isFrontFacing(this.a,this.b,this.c,e)}intersectsBox(e){return e.intersectsTriangle(this)}closestPointToPoint(e,t){let n=this.a,i=this.b,r=this.c,a,o;Bs.subVectors(i,n),Os.subVectors(r,n),Dl.subVectors(e,n);let c=Bs.dot(Dl),l=Os.dot(Dl);if(c<=0&&l<=0)return t.copy(n);Nl.subVectors(e,i);let u=Bs.dot(Nl),h=Os.dot(Nl);if(u>=0&&h<=u)return t.copy(i);let d=c*h-u*l;if(d<=0&&c>=0&&u<=0)return a=c/(c-u),t.copy(n).addScaledVector(Bs,a);Fl.subVectors(e,r);let f=Bs.dot(Fl),g=Os.dot(Fl);if(g>=0&&f<=g)return t.copy(r);let y=f*l-c*g;if(y<=0&&l>=0&&g<=0)return o=l/(l-g),t.copy(n).addScaledVector(Os,o);let m=u*g-f*h;if(m<=0&&h-u>=0&&f-g>=0)return xd.subVectors(r,i),o=(h-u)/(h-u+(f-g)),t.copy(i).addScaledVector(xd,o);let p=1/(m+y+d);return a=y*p,o=d*p,t.copy(n).addScaledVector(Bs,a).addScaledVector(Os,o)}equals(e){return e.a.equals(this.a)&&e.b.equals(this.b)&&e.c.equals(this.c)}},Nf={aliceblue:15792383,antiquewhite:16444375,aqua:65535,aquamarine:8388564,azure:15794175,beige:16119260,bisque:16770244,black:0,blanchedalmond:16772045,blue:255,blueviolet:9055202,brown:10824234,burlywood:14596231,cadetblue:6266528,chartreuse:8388352,chocolate:13789470,coral:16744272,cornflowerblue:6591981,cornsilk:16775388,crimson:14423100,cyan:65535,darkblue:139,darkcyan:35723,darkgoldenrod:12092939,darkgray:11119017,darkgreen:25600,darkgrey:11119017,darkkhaki:12433259,darkmagenta:9109643,darkolivegreen:5597999,darkorange:16747520,darkorchid:10040012,darkred:9109504,darksalmon:15308410,darkseagreen:9419919,darkslateblue:4734347,darkslategray:3100495,darkslategrey:3100495,darkturquoise:52945,darkviolet:9699539,deeppink:16716947,deepskyblue:49151,dimgray:6908265,dimgrey:6908265,dodgerblue:2003199,firebrick:11674146,floralwhite:16775920,forestgreen:2263842,fuchsia:16711935,gainsboro:14474460,ghostwhite:16316671,gold:16766720,goldenrod:14329120,gray:8421504,green:32768,greenyellow:11403055,grey:8421504,honeydew:15794160,hotpink:16738740,indianred:13458524,indigo:4915330,ivory:16777200,khaki:15787660,lavender:15132410,lavenderblush:16773365,lawngreen:8190976,lemonchiffon:16775885,lightblue:11393254,lightcoral:15761536,lightcyan:14745599,lightgoldenrodyellow:16448210,lightgray:13882323,lightgreen:9498256,lightgrey:13882323,lightpink:16758465,lightsalmon:16752762,lightseagreen:2142890,lightskyblue:8900346,lightslategray:7833753,lightslategrey:7833753,lightsteelblue:11584734,lightyellow:16777184,lime:65280,limegreen:3329330,linen:16445670,magenta:16711935,maroon:8388608,mediumaquamarine:6737322,mediumblue:205,mediumorchid:12211667,mediumpurple:9662683,mediumseagreen:3978097,mediumslateblue:8087790,mediumspringgreen:64154,mediumturquoise:4772300,mediumvioletred:13047173,midnightblue:1644912,mintcream:16121850,mistyrose:16770273,moccasin:16770229,navajowhite:16768685,navy:128,oldlace:16643558,olive:8421376,olivedrab:7048739,orange:16753920,orangered:16729344,orchid:14315734,palegoldenrod:15657130,palegreen:10025880,paleturquoise:11529966,palevioletred:14381203,papayawhip:16773077,peachpuff:16767673,peru:13468991,pink:16761035,plum:14524637,powderblue:11591910,purple:8388736,rebeccapurple:6697881,red:16711680,rosybrown:12357519,royalblue:4286945,saddlebrown:9127187,salmon:16416882,sandybrown:16032864,seagreen:3050327,seashell:16774638,sienna:10506797,silver:12632256,skyblue:8900331,slateblue:6970061,slategray:7372944,slategrey:7372944,snow:16775930,springgreen:65407,steelblue:4620980,tan:13808780,teal:32896,thistle:14204888,tomato:16737095,turquoise:4251856,violet:15631086,wheat:16113331,white:16777215,whitesmoke:16119285,yellow:16776960,yellowgreen:10145074},Di={h:0,s:0,l:0},io={h:0,s:0,l:0};function zl(s,e,t){return t<0&&(t+=1),t>1&&(t-=1),t<1/6?s+(e-s)*6*t:t<1/2?e:t<2/3?s+(e-s)*6*(2/3-t):s}var Ue=class{constructor(e,t,n){return this.isColor=!0,this.r=1,this.g=1,this.b=1,this.set(e,t,n)}set(e,t,n){if(t===void 0&&n===void 0){let i=e;i&&i.isColor?this.copy(i):typeof i=="number"?this.setHex(i):typeof i=="string"&&this.setStyle(i)}else this.setRGB(e,t,n);return this}setScalar(e){return this.r=e,this.g=e,this.b=e,this}setHex(e,t=kt){return e=Math.floor(e),this.r=(e>>16&255)/255,this.g=(e>>8&255)/255,this.b=(e&255)/255,et.colorSpaceToWorking(this,t),this}setRGB(e,t,n,i=et.workingColorSpace){return this.r=e,this.g=t,this.b=n,et.colorSpaceToWorking(this,i),this}setHSL(e,t,n,i=et.workingColorSpace){if(e=Mh(e,1),t=We(t,0,1),n=We(n,0,1),t===0)this.r=this.g=this.b=n;else{let r=n<=.5?n*(1+t):n+t-n*t,a=2*n-r;this.r=zl(a,r,e+1/3),this.g=zl(a,r,e),this.b=zl(a,r,e-1/3)}return et.colorSpaceToWorking(this,i),this}setStyle(e,t=kt){function n(r){r!==void 0&&parseFloat(r)<1&&console.warn("THREE.Color: Alpha component of "+e+" will be ignored.")}let i;if(i=/^(\w+)\(([^\)]*)\)/.exec(e)){let r,a=i[1],o=i[2];switch(a){case"rgb":case"rgba":if(r=/^\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(o))return n(r[4]),this.setRGB(Math.min(255,parseInt(r[1],10))/255,Math.min(255,parseInt(r[2],10))/255,Math.min(255,parseInt(r[3],10))/255,t);if(r=/^\s*(\d+)\%\s*,\s*(\d+)\%\s*,\s*(\d+)\%\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(o))return n(r[4]),this.setRGB(Math.min(100,parseInt(r[1],10))/100,Math.min(100,parseInt(r[2],10))/100,Math.min(100,parseInt(r[3],10))/100,t);break;case"hsl":case"hsla":if(r=/^\s*(\d*\.?\d+)\s*,\s*(\d*\.?\d+)\%\s*,\s*(\d*\.?\d+)\%\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(o))return n(r[4]),this.setHSL(parseFloat(r[1])/360,parseFloat(r[2])/100,parseFloat(r[3])/100,t);break;default:console.warn("THREE.Color: Unknown color model "+e)}}else if(i=/^\#([A-Fa-f\d]+)$/.exec(e)){let r=i[1],a=r.length;if(a===3)return this.setRGB(parseInt(r.charAt(0),16)/15,parseInt(r.charAt(1),16)/15,parseInt(r.charAt(2),16)/15,t);if(a===6)return this.setHex(parseInt(r,16),t);console.warn("THREE.Color: Invalid hex color "+e)}else if(e&&e.length>0)return this.setColorName(e,t);return this}setColorName(e,t=kt){let n=Nf[e.toLowerCase()];return n!==void 0?this.setHex(n,t):console.warn("THREE.Color: Unknown color "+e),this}clone(){return new this.constructor(this.r,this.g,this.b)}copy(e){return this.r=e.r,this.g=e.g,this.b=e.b,this}copySRGBToLinear(e){return this.r=yi(e.r),this.g=yi(e.g),this.b=yi(e.b),this}copyLinearToSRGB(e){return this.r=qs(e.r),this.g=qs(e.g),this.b=qs(e.b),this}convertSRGBToLinear(){return this.copySRGBToLinear(this),this}convertLinearToSRGB(){return this.copyLinearToSRGB(this),this}getHex(e=kt){return et.workingToColorSpace(Qt.copy(this),e),Math.round(We(Qt.r*255,0,255))*65536+Math.round(We(Qt.g*255,0,255))*256+Math.round(We(Qt.b*255,0,255))}getHexString(e=kt){return("000000"+this.getHex(e).toString(16)).slice(-6)}getHSL(e,t=et.workingColorSpace){et.workingToColorSpace(Qt.copy(this),t);let n=Qt.r,i=Qt.g,r=Qt.b,a=Math.max(n,i,r),o=Math.min(n,i,r),c,l,u=(o+a)/2;if(o===a)c=0,l=0;else{let h=a-o;switch(l=u<=.5?h/(a+o):h/(2-a-o),a){case n:c=(i-r)/h+(i<r?6:0);break;case i:c=(r-n)/h+2;break;case r:c=(n-i)/h+4;break}c/=6}return e.h=c,e.s=l,e.l=u,e}getRGB(e,t=et.workingColorSpace){return et.workingToColorSpace(Qt.copy(this),t),e.r=Qt.r,e.g=Qt.g,e.b=Qt.b,e}getStyle(e=kt){et.workingToColorSpace(Qt.copy(this),e);let t=Qt.r,n=Qt.g,i=Qt.b;return e!==kt?`color(${e} ${t.toFixed(3)} ${n.toFixed(3)} ${i.toFixed(3)})`:`rgb(${Math.round(t*255)},${Math.round(n*255)},${Math.round(i*255)})`}offsetHSL(e,t,n){return this.getHSL(Di),this.setHSL(Di.h+e,Di.s+t,Di.l+n)}add(e){return this.r+=e.r,this.g+=e.g,this.b+=e.b,this}addColors(e,t){return this.r=e.r+t.r,this.g=e.g+t.g,this.b=e.b+t.b,this}addScalar(e){return this.r+=e,this.g+=e,this.b+=e,this}sub(e){return this.r=Math.max(0,this.r-e.r),this.g=Math.max(0,this.g-e.g),this.b=Math.max(0,this.b-e.b),this}multiply(e){return this.r*=e.r,this.g*=e.g,this.b*=e.b,this}multiplyScalar(e){return this.r*=e,this.g*=e,this.b*=e,this}lerp(e,t){return this.r+=(e.r-this.r)*t,this.g+=(e.g-this.g)*t,this.b+=(e.b-this.b)*t,this}lerpColors(e,t,n){return this.r=e.r+(t.r-e.r)*n,this.g=e.g+(t.g-e.g)*n,this.b=e.b+(t.b-e.b)*n,this}lerpHSL(e,t){this.getHSL(Di),e.getHSL(io);let n=jr(Di.h,io.h,t),i=jr(Di.s,io.s,t),r=jr(Di.l,io.l,t);return this.setHSL(n,i,r),this}setFromVector3(e){return this.r=e.x,this.g=e.y,this.b=e.z,this}applyMatrix3(e){let t=this.r,n=this.g,i=this.b,r=e.elements;return this.r=r[0]*t+r[3]*n+r[6]*i,this.g=r[1]*t+r[4]*n+r[7]*i,this.b=r[2]*t+r[5]*n+r[8]*i,this}equals(e){return e.r===this.r&&e.g===this.g&&e.b===this.b}fromArray(e,t=0){return this.r=e[t],this.g=e[t+1],this.b=e[t+2],this}toArray(e=[],t=0){return e[t]=this.r,e[t+1]=this.g,e[t+2]=this.b,e}fromBufferAttribute(e,t){return this.r=e.getX(t),this.g=e.getY(t),this.b=e.getZ(t),this}toJSON(){return this.getHex()}*[Symbol.iterator](){yield this.r,yield this.g,yield this.b}},Qt=new Ue;Ue.NAMES=Nf;var lg=0,cn=class extends xi{constructor(){super(),this.isMaterial=!0,Object.defineProperty(this,"id",{value:lg++}),this.uuid=Yn(),this.name="",this.type="Material",this.blending=es,this.side=pn,this.vertexColors=!1,this.opacity=1,this.transparent=!1,this.alphaHash=!1,this.blendSrc=Mo,this.blendDst=So,this.blendEquation=Fi,this.blendSrcAlpha=null,this.blendDstAlpha=null,this.blendEquationAlpha=null,this.blendColor=new Ue(0,0,0),this.blendAlpha=0,this.depthFunc=ts,this.depthTest=!0,this.depthWrite=!0,this.stencilWriteMask=255,this.stencilFunc=th,this.stencilRef=0,this.stencilFuncMask=255,this.stencilFail=Qi,this.stencilZFail=Qi,this.stencilZPass=Qi,this.stencilWrite=!1,this.clippingPlanes=null,this.clipIntersection=!1,this.clipShadows=!1,this.shadowSide=null,this.colorWrite=!0,this.precision=null,this.polygonOffset=!1,this.polygonOffsetFactor=0,this.polygonOffsetUnits=0,this.dithering=!1,this.alphaToCoverage=!1,this.premultipliedAlpha=!1,this.forceSinglePass=!1,this.allowOverride=!0,this.visible=!0,this.toneMapped=!0,this.userData={},this.version=0,this._alphaTest=0}get alphaTest(){return this._alphaTest}set alphaTest(e){this._alphaTest>0!=e>0&&this.version++,this._alphaTest=e}onBeforeRender(){}onBeforeCompile(){}customProgramCacheKey(){return this.onBeforeCompile.toString()}setValues(e){if(e!==void 0)for(let t in e){let n=e[t];if(n===void 0){console.warn(`THREE.Material: parameter '${t}' has value of undefined.`);continue}let i=this[t];if(i===void 0){console.warn(`THREE.Material: '${t}' is not a property of THREE.${this.type}.`);continue}i&&i.isColor?i.set(n):i&&i.isVector3&&n&&n.isVector3?i.copy(n):this[t]=n}}toJSON(e){let t=e===void 0||typeof e=="string";t&&(e={textures:{},images:{}});let n={metadata:{version:4.7,type:"Material",generator:"Material.toJSON"}};n.uuid=this.uuid,n.type=this.type,this.name!==""&&(n.name=this.name),this.color&&this.color.isColor&&(n.color=this.color.getHex()),this.roughness!==void 0&&(n.roughness=this.roughness),this.metalness!==void 0&&(n.metalness=this.metalness),this.sheen!==void 0&&(n.sheen=this.sheen),this.sheenColor&&this.sheenColor.isColor&&(n.sheenColor=this.sheenColor.getHex()),this.sheenRoughness!==void 0&&(n.sheenRoughness=this.sheenRoughness),this.emissive&&this.emissive.isColor&&(n.emissive=this.emissive.getHex()),this.emissiveIntensity!==void 0&&this.emissiveIntensity!==1&&(n.emissiveIntensity=this.emissiveIntensity),this.specular&&this.specular.isColor&&(n.specular=this.specular.getHex()),this.specularIntensity!==void 0&&(n.specularIntensity=this.specularIntensity),this.specularColor&&this.specularColor.isColor&&(n.specularColor=this.specularColor.getHex()),this.shininess!==void 0&&(n.shininess=this.shininess),this.clearcoat!==void 0&&(n.clearcoat=this.clearcoat),this.clearcoatRoughness!==void 0&&(n.clearcoatRoughness=this.clearcoatRoughness),this.clearcoatMap&&this.clearcoatMap.isTexture&&(n.clearcoatMap=this.clearcoatMap.toJSON(e).uuid),this.clearcoatRoughnessMap&&this.clearcoatRoughnessMap.isTexture&&(n.clearcoatRoughnessMap=this.clearcoatRoughnessMap.toJSON(e).uuid),this.clearcoatNormalMap&&this.clearcoatNormalMap.isTexture&&(n.clearcoatNormalMap=this.clearcoatNormalMap.toJSON(e).uuid,n.clearcoatNormalScale=this.clearcoatNormalScale.toArray()),this.sheenColorMap&&this.sheenColorMap.isTexture&&(n.sheenColorMap=this.sheenColorMap.toJSON(e).uuid),this.sheenRoughnessMap&&this.sheenRoughnessMap.isTexture&&(n.sheenRoughnessMap=this.sheenRoughnessMap.toJSON(e).uuid),this.dispersion!==void 0&&(n.dispersion=this.dispersion),this.iridescence!==void 0&&(n.iridescence=this.iridescence),this.iridescenceIOR!==void 0&&(n.iridescenceIOR=this.iridescenceIOR),this.iridescenceThicknessRange!==void 0&&(n.iridescenceThicknessRange=this.iridescenceThicknessRange),this.iridescenceMap&&this.iridescenceMap.isTexture&&(n.iridescenceMap=this.iridescenceMap.toJSON(e).uuid),this.iridescenceThicknessMap&&this.iridescenceThicknessMap.isTexture&&(n.iridescenceThicknessMap=this.iridescenceThicknessMap.toJSON(e).uuid),this.anisotropy!==void 0&&(n.anisotropy=this.anisotropy),this.anisotropyRotation!==void 0&&(n.anisotropyRotation=this.anisotropyRotation),this.anisotropyMap&&this.anisotropyMap.isTexture&&(n.anisotropyMap=this.anisotropyMap.toJSON(e).uuid),this.map&&this.map.isTexture&&(n.map=this.map.toJSON(e).uuid),this.matcap&&this.matcap.isTexture&&(n.matcap=this.matcap.toJSON(e).uuid),this.alphaMap&&this.alphaMap.isTexture&&(n.alphaMap=this.alphaMap.toJSON(e).uuid),this.lightMap&&this.lightMap.isTexture&&(n.lightMap=this.lightMap.toJSON(e).uuid,n.lightMapIntensity=this.lightMapIntensity),this.aoMap&&this.aoMap.isTexture&&(n.aoMap=this.aoMap.toJSON(e).uuid,n.aoMapIntensity=this.aoMapIntensity),this.bumpMap&&this.bumpMap.isTexture&&(n.bumpMap=this.bumpMap.toJSON(e).uuid,n.bumpScale=this.bumpScale),this.normalMap&&this.normalMap.isTexture&&(n.normalMap=this.normalMap.toJSON(e).uuid,n.normalMapType=this.normalMapType,n.normalScale=this.normalScale.toArray()),this.displacementMap&&this.displacementMap.isTexture&&(n.displacementMap=this.displacementMap.toJSON(e).uuid,n.displacementScale=this.displacementScale,n.displacementBias=this.displacementBias),this.roughnessMap&&this.roughnessMap.isTexture&&(n.roughnessMap=this.roughnessMap.toJSON(e).uuid),this.metalnessMap&&this.metalnessMap.isTexture&&(n.metalnessMap=this.metalnessMap.toJSON(e).uuid),this.emissiveMap&&this.emissiveMap.isTexture&&(n.emissiveMap=this.emissiveMap.toJSON(e).uuid),this.specularMap&&this.specularMap.isTexture&&(n.specularMap=this.specularMap.toJSON(e).uuid),this.specularIntensityMap&&this.specularIntensityMap.isTexture&&(n.specularIntensityMap=this.specularIntensityMap.toJSON(e).uuid),this.specularColorMap&&this.specularColorMap.isTexture&&(n.specularColorMap=this.specularColorMap.toJSON(e).uuid),this.envMap&&this.envMap.isTexture&&(n.envMap=this.envMap.toJSON(e).uuid,this.combine!==void 0&&(n.combine=this.combine)),this.envMapRotation!==void 0&&(n.envMapRotation=this.envMapRotation.toArray()),this.envMapIntensity!==void 0&&(n.envMapIntensity=this.envMapIntensity),this.reflectivity!==void 0&&(n.reflectivity=this.reflectivity),this.refractionRatio!==void 0&&(n.refractionRatio=this.refractionRatio),this.gradientMap&&this.gradientMap.isTexture&&(n.gradientMap=this.gradientMap.toJSON(e).uuid),this.transmission!==void 0&&(n.transmission=this.transmission),this.transmissionMap&&this.transmissionMap.isTexture&&(n.transmissionMap=this.transmissionMap.toJSON(e).uuid),this.thickness!==void 0&&(n.thickness=this.thickness),this.thicknessMap&&this.thicknessMap.isTexture&&(n.thicknessMap=this.thicknessMap.toJSON(e).uuid),this.attenuationDistance!==void 0&&this.attenuationDistance!==1/0&&(n.attenuationDistance=this.attenuationDistance),this.attenuationColor!==void 0&&(n.attenuationColor=this.attenuationColor.getHex()),this.size!==void 0&&(n.size=this.size),this.shadowSide!==null&&(n.shadowSide=this.shadowSide),this.sizeAttenuation!==void 0&&(n.sizeAttenuation=this.sizeAttenuation),this.blending!==es&&(n.blending=this.blending),this.side!==pn&&(n.side=this.side),this.vertexColors===!0&&(n.vertexColors=!0),this.opacity<1&&(n.opacity=this.opacity),this.transparent===!0&&(n.transparent=!0),this.blendSrc!==Mo&&(n.blendSrc=this.blendSrc),this.blendDst!==So&&(n.blendDst=this.blendDst),this.blendEquation!==Fi&&(n.blendEquation=this.blendEquation),this.blendSrcAlpha!==null&&(n.blendSrcAlpha=this.blendSrcAlpha),this.blendDstAlpha!==null&&(n.blendDstAlpha=this.blendDstAlpha),this.blendEquationAlpha!==null&&(n.blendEquationAlpha=this.blendEquationAlpha),this.blendColor&&this.blendColor.isColor&&(n.blendColor=this.blendColor.getHex()),this.blendAlpha!==0&&(n.blendAlpha=this.blendAlpha),this.depthFunc!==ts&&(n.depthFunc=this.depthFunc),this.depthTest===!1&&(n.depthTest=this.depthTest),this.depthWrite===!1&&(n.depthWrite=this.depthWrite),this.colorWrite===!1&&(n.colorWrite=this.colorWrite),this.stencilWriteMask!==255&&(n.stencilWriteMask=this.stencilWriteMask),this.stencilFunc!==th&&(n.stencilFunc=this.stencilFunc),this.stencilRef!==0&&(n.stencilRef=this.stencilRef),this.stencilFuncMask!==255&&(n.stencilFuncMask=this.stencilFuncMask),this.stencilFail!==Qi&&(n.stencilFail=this.stencilFail),this.stencilZFail!==Qi&&(n.stencilZFail=this.stencilZFail),this.stencilZPass!==Qi&&(n.stencilZPass=this.stencilZPass),this.stencilWrite===!0&&(n.stencilWrite=this.stencilWrite),this.rotation!==void 0&&this.rotation!==0&&(n.rotation=this.rotation),this.polygonOffset===!0&&(n.polygonOffset=!0),this.polygonOffsetFactor!==0&&(n.polygonOffsetFactor=this.polygonOffsetFactor),this.polygonOffsetUnits!==0&&(n.polygonOffsetUnits=this.polygonOffsetUnits),this.linewidth!==void 0&&this.linewidth!==1&&(n.linewidth=this.linewidth),this.dashSize!==void 0&&(n.dashSize=this.dashSize),this.gapSize!==void 0&&(n.gapSize=this.gapSize),this.scale!==void 0&&(n.scale=this.scale),this.dithering===!0&&(n.dithering=!0),this.alphaTest>0&&(n.alphaTest=this.alphaTest),this.alphaHash===!0&&(n.alphaHash=!0),this.alphaToCoverage===!0&&(n.alphaToCoverage=!0),this.premultipliedAlpha===!0&&(n.premultipliedAlpha=!0),this.forceSinglePass===!0&&(n.forceSinglePass=!0),this.wireframe===!0&&(n.wireframe=!0),this.wireframeLinewidth>1&&(n.wireframeLinewidth=this.wireframeLinewidth),this.wireframeLinecap!=="round"&&(n.wireframeLinecap=this.wireframeLinecap),this.wireframeLinejoin!=="round"&&(n.wireframeLinejoin=this.wireframeLinejoin),this.flatShading===!0&&(n.flatShading=!0),this.visible===!1&&(n.visible=!1),this.toneMapped===!1&&(n.toneMapped=!1),this.fog===!1&&(n.fog=!1),Object.keys(this.userData).length>0&&(n.userData=this.userData);function i(r){let a=[];for(let o in r){let c=r[o];delete c.metadata,a.push(c)}return a}if(t){let r=i(e.textures),a=i(e.images);r.length>0&&(n.textures=r),a.length>0&&(n.images=a)}return n}clone(){return new this.constructor().copy(this)}copy(e){this.name=e.name,this.blending=e.blending,this.side=e.side,this.vertexColors=e.vertexColors,this.opacity=e.opacity,this.transparent=e.transparent,this.blendSrc=e.blendSrc,this.blendDst=e.blendDst,this.blendEquation=e.blendEquation,this.blendSrcAlpha=e.blendSrcAlpha,this.blendDstAlpha=e.blendDstAlpha,this.blendEquationAlpha=e.blendEquationAlpha,this.blendColor.copy(e.blendColor),this.blendAlpha=e.blendAlpha,this.depthFunc=e.depthFunc,this.depthTest=e.depthTest,this.depthWrite=e.depthWrite,this.stencilWriteMask=e.stencilWriteMask,this.stencilFunc=e.stencilFunc,this.stencilRef=e.stencilRef,this.stencilFuncMask=e.stencilFuncMask,this.stencilFail=e.stencilFail,this.stencilZFail=e.stencilZFail,this.stencilZPass=e.stencilZPass,this.stencilWrite=e.stencilWrite;let t=e.clippingPlanes,n=null;if(t!==null){let i=t.length;n=new Array(i);for(let r=0;r!==i;++r)n[r]=t[r].clone()}return this.clippingPlanes=n,this.clipIntersection=e.clipIntersection,this.clipShadows=e.clipShadows,this.shadowSide=e.shadowSide,this.colorWrite=e.colorWrite,this.precision=e.precision,this.polygonOffset=e.polygonOffset,this.polygonOffsetFactor=e.polygonOffsetFactor,this.polygonOffsetUnits=e.polygonOffsetUnits,this.dithering=e.dithering,this.alphaTest=e.alphaTest,this.alphaHash=e.alphaHash,this.alphaToCoverage=e.alphaToCoverage,this.premultipliedAlpha=e.premultipliedAlpha,this.forceSinglePass=e.forceSinglePass,this.visible=e.visible,this.toneMapped=e.toneMapped,this.userData=JSON.parse(JSON.stringify(e.userData)),this}dispose(){this.dispatchEvent({type:"dispose"})}set needsUpdate(e){e===!0&&this.version++}},nn=class extends cn{constructor(e){super(),this.isMeshBasicMaterial=!0,this.type="MeshBasicMaterial",this.color=new Ue(16777215),this.map=null,this.lightMap=null,this.lightMapIntensity=1,this.aoMap=null,this.aoMapIntensity=1,this.specularMap=null,this.alphaMap=null,this.envMap=null,this.envMapRotation=new Dn,this.combine=Zo,this.reflectivity=1,this.refractionRatio=.98,this.wireframe=!1,this.wireframeLinewidth=1,this.wireframeLinecap="round",this.wireframeLinejoin="round",this.fog=!0,this.setValues(e)}copy(e){return super.copy(e),this.color.copy(e.color),this.map=e.map,this.lightMap=e.lightMap,this.lightMapIntensity=e.lightMapIntensity,this.aoMap=e.aoMap,this.aoMapIntensity=e.aoMapIntensity,this.specularMap=e.specularMap,this.alphaMap=e.alphaMap,this.envMap=e.envMap,this.envMapRotation.copy(e.envMapRotation),this.combine=e.combine,this.reflectivity=e.reflectivity,this.refractionRatio=e.refractionRatio,this.wireframe=e.wireframe,this.wireframeLinewidth=e.wireframeLinewidth,this.wireframeLinecap=e.wireframeLinecap,this.wireframeLinejoin=e.wireframeLinejoin,this.fog=e.fog,this}},bi=hg();function hg(){let s=new ArrayBuffer(4),e=new Float32Array(s),t=new Uint32Array(s),n=new Uint32Array(512),i=new Uint32Array(512);for(let c=0;c<256;++c){let l=c-127;l<-27?(n[c]=0,n[c|256]=32768,i[c]=24,i[c|256]=24):l<-14?(n[c]=1024>>-l-14,n[c|256]=1024>>-l-14|32768,i[c]=-l-1,i[c|256]=-l-1):l<=15?(n[c]=l+15<<10,n[c|256]=l+15<<10|32768,i[c]=13,i[c|256]=13):l<128?(n[c]=31744,n[c|256]=64512,i[c]=24,i[c|256]=24):(n[c]=31744,n[c|256]=64512,i[c]=13,i[c|256]=13)}let r=new Uint32Array(2048),a=new Uint32Array(64),o=new Uint32Array(64);for(let c=1;c<1024;++c){let l=c<<13,u=0;for(;(l&8388608)===0;)l<<=1,u-=8388608;l&=-8388609,u+=947912704,r[c]=l|u}for(let c=1024;c<2048;++c)r[c]=939524096+(c-1024<<13);for(let c=1;c<31;++c)a[c]=c<<23;a[31]=1199570944,a[32]=2147483648;for(let c=33;c<63;++c)a[c]=2147483648+(c-32<<23);a[63]=3347054592;for(let c=1;c<64;++c)c!==32&&(o[c]=1024);return{floatView:e,uint32View:t,baseTable:n,shiftTable:i,mantissaTable:r,exponentTable:a,offsetTable:o}}function ug(s){Math.abs(s)>65504&&console.warn("THREE.DataUtils.toHalfFloat(): Value out of range."),s=We(s,-65504,65504),bi.floatView[0]=s;let e=bi.uint32View[0],t=e>>23&511;return bi.baseTable[t]+((e&8388607)>>bi.shiftTable[t])}function dg(s){let e=s>>10;return bi.uint32View[0]=bi.mantissaTable[bi.offsetTable[e]+(s&1023)]+bi.exponentTable[e],bi.floatView[0]}var $r=class{static toHalfFloat(e){return ug(e)}static fromHalfFloat(e){return dg(e)}},Ft=new L,so=new Ne,fg=0,xt=class{constructor(e,t,n=!1){if(Array.isArray(e))throw new TypeError("THREE.BufferAttribute: array should be a Typed Array.");this.isBufferAttribute=!0,Object.defineProperty(this,"id",{value:fg++}),this.name="",this.array=e,this.itemSize=t,this.count=e!==void 0?e.length/t:0,this.normalized=n,this.usage=To,this.updateRanges=[],this.gpuType=Fn,this.version=0}onUploadCallback(){}set needsUpdate(e){e===!0&&this.version++}setUsage(e){return this.usage=e,this}addUpdateRange(e,t){this.updateRanges.push({start:e,count:t})}clearUpdateRanges(){this.updateRanges.length=0}copy(e){return this.name=e.name,this.array=new e.array.constructor(e.array),this.itemSize=e.itemSize,this.count=e.count,this.normalized=e.normalized,this.usage=e.usage,this.gpuType=e.gpuType,this}copyAt(e,t,n){e*=this.itemSize,n*=t.itemSize;for(let i=0,r=this.itemSize;i<r;i++)this.array[e+i]=t.array[n+i];return this}copyArray(e){return this.array.set(e),this}applyMatrix3(e){if(this.itemSize===2)for(let t=0,n=this.count;t<n;t++)so.fromBufferAttribute(this,t),so.applyMatrix3(e),this.setXY(t,so.x,so.y);else if(this.itemSize===3)for(let t=0,n=this.count;t<n;t++)Ft.fromBufferAttribute(this,t),Ft.applyMatrix3(e),this.setXYZ(t,Ft.x,Ft.y,Ft.z);return this}applyMatrix4(e){for(let t=0,n=this.count;t<n;t++)Ft.fromBufferAttribute(this,t),Ft.applyMatrix4(e),this.setXYZ(t,Ft.x,Ft.y,Ft.z);return this}applyNormalMatrix(e){for(let t=0,n=this.count;t<n;t++)Ft.fromBufferAttribute(this,t),Ft.applyNormalMatrix(e),this.setXYZ(t,Ft.x,Ft.y,Ft.z);return this}transformDirection(e){for(let t=0,n=this.count;t<n;t++)Ft.fromBufferAttribute(this,t),Ft.transformDirection(e),this.setXYZ(t,Ft.x,Ft.y,Ft.z);return this}set(e,t=0){return this.array.set(e,t),this}getComponent(e,t){let n=this.array[e*this.itemSize+t];return this.normalized&&(n=Gn(n,this.array)),n}setComponent(e,t,n){return this.normalized&&(n=ft(n,this.array)),this.array[e*this.itemSize+t]=n,this}getX(e){let t=this.array[e*this.itemSize];return this.normalized&&(t=Gn(t,this.array)),t}setX(e,t){return this.normalized&&(t=ft(t,this.array)),this.array[e*this.itemSize]=t,this}getY(e){let t=this.array[e*this.itemSize+1];return this.normalized&&(t=Gn(t,this.array)),t}setY(e,t){return this.normalized&&(t=ft(t,this.array)),this.array[e*this.itemSize+1]=t,this}getZ(e){let t=this.array[e*this.itemSize+2];return this.normalized&&(t=Gn(t,this.array)),t}setZ(e,t){return this.normalized&&(t=ft(t,this.array)),this.array[e*this.itemSize+2]=t,this}getW(e){let t=this.array[e*this.itemSize+3];return this.normalized&&(t=Gn(t,this.array)),t}setW(e,t){return this.normalized&&(t=ft(t,this.array)),this.array[e*this.itemSize+3]=t,this}setXY(e,t,n){return e*=this.itemSize,this.normalized&&(t=ft(t,this.array),n=ft(n,this.array)),this.array[e+0]=t,this.array[e+1]=n,this}setXYZ(e,t,n,i){return e*=this.itemSize,this.normalized&&(t=ft(t,this.array),n=ft(n,this.array),i=ft(i,this.array)),this.array[e+0]=t,this.array[e+1]=n,this.array[e+2]=i,this}setXYZW(e,t,n,i,r){return e*=this.itemSize,this.normalized&&(t=ft(t,this.array),n=ft(n,this.array),i=ft(i,this.array),r=ft(r,this.array)),this.array[e+0]=t,this.array[e+1]=n,this.array[e+2]=i,this.array[e+3]=r,this}onUpload(e){return this.onUploadCallback=e,this}clone(){return new this.constructor(this.array,this.itemSize).copy(this)}toJSON(){let e={itemSize:this.itemSize,type:this.array.constructor.name,array:Array.from(this.array),normalized:this.normalized};return this.name!==""&&(e.name=this.name),this.usage!==To&&(e.usage=this.usage),e}};var Qr=class extends xt{constructor(e,t,n){super(new Uint16Array(e),t,n)}};var ea=class extends xt{constructor(e,t,n){super(new Uint32Array(e),t,n)}};var Tt=class extends xt{constructor(e,t,n){super(new Float32Array(e),t,n)}},pg=0,kn=new ke,Hl=new Et,zs=new L,Mn=new ot,Vr=new ot,Vt=new L,Bt=class s extends xi{constructor(){super(),this.isBufferGeometry=!0,Object.defineProperty(this,"id",{value:pg++}),this.uuid=Yn(),this.name="",this.type="BufferGeometry",this.index=null,this.indirect=null,this.attributes={},this.morphAttributes={},this.morphTargetsRelative=!1,this.groups=[],this.boundingBox=null,this.boundingSphere=null,this.drawRange={start:0,count:1/0},this.userData={}}getIndex(){return this.index}setIndex(e){return Array.isArray(e)?this.index=new(Sh(e)?ea:Qr)(e,1):this.index=e,this}setIndirect(e){return this.indirect=e,this}getIndirect(){return this.indirect}getAttribute(e){return this.attributes[e]}setAttribute(e,t){return this.attributes[e]=t,this}deleteAttribute(e){return delete this.attributes[e],this}hasAttribute(e){return this.attributes[e]!==void 0}addGroup(e,t,n=0){this.groups.push({start:e,count:t,materialIndex:n})}clearGroups(){this.groups=[]}setDrawRange(e,t){this.drawRange.start=e,this.drawRange.count=t}applyMatrix4(e){let t=this.attributes.position;t!==void 0&&(t.applyMatrix4(e),t.needsUpdate=!0);let n=this.attributes.normal;if(n!==void 0){let r=new qe().getNormalMatrix(e);n.applyNormalMatrix(r),n.needsUpdate=!0}let i=this.attributes.tangent;return i!==void 0&&(i.transformDirection(e),i.needsUpdate=!0),this.boundingBox!==null&&this.computeBoundingBox(),this.boundingSphere!==null&&this.computeBoundingSphere(),this}applyQuaternion(e){return kn.makeRotationFromQuaternion(e),this.applyMatrix4(kn),this}rotateX(e){return kn.makeRotationX(e),this.applyMatrix4(kn),this}rotateY(e){return kn.makeRotationY(e),this.applyMatrix4(kn),this}rotateZ(e){return kn.makeRotationZ(e),this.applyMatrix4(kn),this}translate(e,t,n){return kn.makeTranslation(e,t,n),this.applyMatrix4(kn),this}scale(e,t,n){return kn.makeScale(e,t,n),this.applyMatrix4(kn),this}lookAt(e){return Hl.lookAt(e),Hl.updateMatrix(),this.applyMatrix4(Hl.matrix),this}center(){return this.computeBoundingBox(),this.boundingBox.getCenter(zs).negate(),this.translate(zs.x,zs.y,zs.z),this}setFromPoints(e){let t=this.getAttribute("position");if(t===void 0){let n=[];for(let i=0,r=e.length;i<r;i++){let a=e[i];n.push(a.x,a.y,a.z||0)}this.setAttribute("position",new Tt(n,3))}else{let n=Math.min(e.length,t.count);for(let i=0;i<n;i++){let r=e[i];t.setXYZ(i,r.x,r.y,r.z||0)}e.length>t.count&&console.warn("THREE.BufferGeometry: Buffer size too small for points data. Use .dispose() and create a new geometry."),t.needsUpdate=!0}return this}computeBoundingBox(){this.boundingBox===null&&(this.boundingBox=new ot);let e=this.attributes.position,t=this.morphAttributes.position;if(e&&e.isGLBufferAttribute){console.error("THREE.BufferGeometry.computeBoundingBox(): GLBufferAttribute requires a manual bounding box.",this),this.boundingBox.set(new L(-1/0,-1/0,-1/0),new L(1/0,1/0,1/0));return}if(e!==void 0){if(this.boundingBox.setFromBufferAttribute(e),t)for(let n=0,i=t.length;n<i;n++){let r=t[n];Mn.setFromBufferAttribute(r),this.morphTargetsRelative?(Vt.addVectors(this.boundingBox.min,Mn.min),this.boundingBox.expandByPoint(Vt),Vt.addVectors(this.boundingBox.max,Mn.max),this.boundingBox.expandByPoint(Vt)):(this.boundingBox.expandByPoint(Mn.min),this.boundingBox.expandByPoint(Mn.max))}}else this.boundingBox.makeEmpty();(isNaN(this.boundingBox.min.x)||isNaN(this.boundingBox.min.y)||isNaN(this.boundingBox.min.z))&&console.error('THREE.BufferGeometry.computeBoundingBox(): Computed min/max have NaN values. The "position" attribute is likely to have NaN values.',this)}computeBoundingSphere(){this.boundingSphere===null&&(this.boundingSphere=new tn);let e=this.attributes.position,t=this.morphAttributes.position;if(e&&e.isGLBufferAttribute){console.error("THREE.BufferGeometry.computeBoundingSphere(): GLBufferAttribute requires a manual bounding sphere.",this),this.boundingSphere.set(new L,1/0);return}if(e){let n=this.boundingSphere.center;if(Mn.setFromBufferAttribute(e),t)for(let r=0,a=t.length;r<a;r++){let o=t[r];Vr.setFromBufferAttribute(o),this.morphTargetsRelative?(Vt.addVectors(Mn.min,Vr.min),Mn.expandByPoint(Vt),Vt.addVectors(Mn.max,Vr.max),Mn.expandByPoint(Vt)):(Mn.expandByPoint(Vr.min),Mn.expandByPoint(Vr.max))}Mn.getCenter(n);let i=0;for(let r=0,a=e.count;r<a;r++)Vt.fromBufferAttribute(e,r),i=Math.max(i,n.distanceToSquared(Vt));if(t)for(let r=0,a=t.length;r<a;r++){let o=t[r],c=this.morphTargetsRelative;for(let l=0,u=o.count;l<u;l++)Vt.fromBufferAttribute(o,l),c&&(zs.fromBufferAttribute(e,l),Vt.add(zs)),i=Math.max(i,n.distanceToSquared(Vt))}this.boundingSphere.radius=Math.sqrt(i),isNaN(this.boundingSphere.radius)&&console.error('THREE.BufferGeometry.computeBoundingSphere(): Computed radius is NaN. The "position" attribute is likely to have NaN values.',this)}}computeTangents(){let e=this.index,t=this.attributes;if(e===null||t.position===void 0||t.normal===void 0||t.uv===void 0){console.error("THREE.BufferGeometry: .computeTangents() failed. Missing required attributes (index, position, normal or uv)");return}let n=t.position,i=t.normal,r=t.uv;this.hasAttribute("tangent")===!1&&this.setAttribute("tangent",new xt(new Float32Array(4*n.count),4));let a=this.getAttribute("tangent"),o=[],c=[];for(let A=0;A<n.count;A++)o[A]=new L,c[A]=new L;let l=new L,u=new L,h=new L,d=new Ne,f=new Ne,g=new Ne,y=new L,m=new L;function p(A,M,_){l.fromBufferAttribute(n,A),u.fromBufferAttribute(n,M),h.fromBufferAttribute(n,_),d.fromBufferAttribute(r,A),f.fromBufferAttribute(r,M),g.fromBufferAttribute(r,_),u.sub(l),h.sub(l),f.sub(d),g.sub(d);let I=1/(f.x*g.y-g.x*f.y);isFinite(I)&&(y.copy(u).multiplyScalar(g.y).addScaledVector(h,-f.y).multiplyScalar(I),m.copy(h).multiplyScalar(f.x).addScaledVector(u,-g.x).multiplyScalar(I),o[A].add(y),o[M].add(y),o[_].add(y),c[A].add(m),c[M].add(m),c[_].add(m))}let x=this.groups;x.length===0&&(x=[{start:0,count:e.count}]);for(let A=0,M=x.length;A<M;++A){let _=x[A],I=_.start,C=_.count;for(let D=I,N=I+C;D<N;D+=3)p(e.getX(D+0),e.getX(D+1),e.getX(D+2))}let v=new L,b=new L,S=new L,w=new L;function T(A){S.fromBufferAttribute(i,A),w.copy(S);let M=o[A];v.copy(M),v.sub(S.multiplyScalar(S.dot(M))).normalize(),b.crossVectors(w,M);let I=b.dot(c[A])<0?-1:1;a.setXYZW(A,v.x,v.y,v.z,I)}for(let A=0,M=x.length;A<M;++A){let _=x[A],I=_.start,C=_.count;for(let D=I,N=I+C;D<N;D+=3)T(e.getX(D+0)),T(e.getX(D+1)),T(e.getX(D+2))}}computeVertexNormals(){let e=this.index,t=this.getAttribute("position");if(t!==void 0){let n=this.getAttribute("normal");if(n===void 0)n=new xt(new Float32Array(t.count*3),3),this.setAttribute("normal",n);else for(let d=0,f=n.count;d<f;d++)n.setXYZ(d,0,0,0);let i=new L,r=new L,a=new L,o=new L,c=new L,l=new L,u=new L,h=new L;if(e)for(let d=0,f=e.count;d<f;d+=3){let g=e.getX(d+0),y=e.getX(d+1),m=e.getX(d+2);i.fromBufferAttribute(t,g),r.fromBufferAttribute(t,y),a.fromBufferAttribute(t,m),u.subVectors(a,r),h.subVectors(i,r),u.cross(h),o.fromBufferAttribute(n,g),c.fromBufferAttribute(n,y),l.fromBufferAttribute(n,m),o.add(u),c.add(u),l.add(u),n.setXYZ(g,o.x,o.y,o.z),n.setXYZ(y,c.x,c.y,c.z),n.setXYZ(m,l.x,l.y,l.z)}else for(let d=0,f=t.count;d<f;d+=3)i.fromBufferAttribute(t,d+0),r.fromBufferAttribute(t,d+1),a.fromBufferAttribute(t,d+2),u.subVectors(a,r),h.subVectors(i,r),u.cross(h),n.setXYZ(d+0,u.x,u.y,u.z),n.setXYZ(d+1,u.x,u.y,u.z),n.setXYZ(d+2,u.x,u.y,u.z);this.normalizeNormals(),n.needsUpdate=!0}}normalizeNormals(){let e=this.attributes.normal;for(let t=0,n=e.count;t<n;t++)Vt.fromBufferAttribute(e,t),Vt.normalize(),e.setXYZ(t,Vt.x,Vt.y,Vt.z)}toNonIndexed(){function e(o,c){let l=o.array,u=o.itemSize,h=o.normalized,d=new l.constructor(c.length*u),f=0,g=0;for(let y=0,m=c.length;y<m;y++){o.isInterleavedBufferAttribute?f=c[y]*o.data.stride+o.offset:f=c[y]*u;for(let p=0;p<u;p++)d[g++]=l[f++]}return new xt(d,u,h)}if(this.index===null)return console.warn("THREE.BufferGeometry.toNonIndexed(): BufferGeometry is already non-indexed."),this;let t=new s,n=this.index.array,i=this.attributes;for(let o in i){let c=i[o],l=e(c,n);t.setAttribute(o,l)}let r=this.morphAttributes;for(let o in r){let c=[],l=r[o];for(let u=0,h=l.length;u<h;u++){let d=l[u],f=e(d,n);c.push(f)}t.morphAttributes[o]=c}t.morphTargetsRelative=this.morphTargetsRelative;let a=this.groups;for(let o=0,c=a.length;o<c;o++){let l=a[o];t.addGroup(l.start,l.count,l.materialIndex)}return t}toJSON(){let e={metadata:{version:4.7,type:"BufferGeometry",generator:"BufferGeometry.toJSON"}};if(e.uuid=this.uuid,e.type=this.type,this.name!==""&&(e.name=this.name),Object.keys(this.userData).length>0&&(e.userData=this.userData),this.parameters!==void 0){let c=this.parameters;for(let l in c)c[l]!==void 0&&(e[l]=c[l]);return e}e.data={attributes:{}};let t=this.index;t!==null&&(e.data.index={type:t.array.constructor.name,array:Array.prototype.slice.call(t.array)});let n=this.attributes;for(let c in n){let l=n[c];e.data.attributes[c]=l.toJSON(e.data)}let i={},r=!1;for(let c in this.morphAttributes){let l=this.morphAttributes[c],u=[];for(let h=0,d=l.length;h<d;h++){let f=l[h];u.push(f.toJSON(e.data))}u.length>0&&(i[c]=u,r=!0)}r&&(e.data.morphAttributes=i,e.data.morphTargetsRelative=this.morphTargetsRelative);let a=this.groups;a.length>0&&(e.data.groups=JSON.parse(JSON.stringify(a)));let o=this.boundingSphere;return o!==null&&(e.data.boundingSphere=o.toJSON()),e}clone(){return new this.constructor().copy(this)}copy(e){this.index=null,this.attributes={},this.morphAttributes={},this.groups=[],this.boundingBox=null,this.boundingSphere=null;let t={};this.name=e.name;let n=e.index;n!==null&&this.setIndex(n.clone());let i=e.attributes;for(let l in i){let u=i[l];this.setAttribute(l,u.clone(t))}let r=e.morphAttributes;for(let l in r){let u=[],h=r[l];for(let d=0,f=h.length;d<f;d++)u.push(h[d].clone(t));this.morphAttributes[l]=u}this.morphTargetsRelative=e.morphTargetsRelative;let a=e.groups;for(let l=0,u=a.length;l<u;l++){let h=a[l];this.addGroup(h.start,h.count,h.materialIndex)}let o=e.boundingBox;o!==null&&(this.boundingBox=o.clone());let c=e.boundingSphere;return c!==null&&(this.boundingSphere=c.clone()),this.drawRange.start=e.drawRange.start,this.drawRange.count=e.drawRange.count,this.userData=e.userData,this}dispose(){this.dispatchEvent({type:"dispose"})}},vd=new ke,Ji=new Sn,ro=new tn,_d=new L,ao=new L,oo=new L,co=new L,Vl=new L,lo=new L,wd=new L,ho=new L,at=class extends Et{constructor(e=new Bt,t=new nn){super(),this.isMesh=!0,this.type="Mesh",this.geometry=e,this.material=t,this.morphTargetDictionary=void 0,this.morphTargetInfluences=void 0,this.count=1,this.updateMorphTargets()}copy(e,t){return super.copy(e,t),e.morphTargetInfluences!==void 0&&(this.morphTargetInfluences=e.morphTargetInfluences.slice()),e.morphTargetDictionary!==void 0&&(this.morphTargetDictionary=Object.assign({},e.morphTargetDictionary)),this.material=Array.isArray(e.material)?e.material.slice():e.material,this.geometry=e.geometry,this}updateMorphTargets(){let t=this.geometry.morphAttributes,n=Object.keys(t);if(n.length>0){let i=t[n[0]];if(i!==void 0){this.morphTargetInfluences=[],this.morphTargetDictionary={};for(let r=0,a=i.length;r<a;r++){let o=i[r].name||String(r);this.morphTargetInfluences.push(0),this.morphTargetDictionary[o]=r}}}}getVertexPosition(e,t){let n=this.geometry,i=n.attributes.position,r=n.morphAttributes.position,a=n.morphTargetsRelative;t.fromBufferAttribute(i,e);let o=this.morphTargetInfluences;if(r&&o){lo.set(0,0,0);for(let c=0,l=r.length;c<l;c++){let u=o[c],h=r[c];u!==0&&(Vl.fromBufferAttribute(h,e),a?lo.addScaledVector(Vl,u):lo.addScaledVector(Vl.sub(t),u))}t.add(lo)}return t}raycast(e,t){let n=this.geometry,i=this.material,r=this.matrixWorld;i!==void 0&&(n.boundingSphere===null&&n.computeBoundingSphere(),ro.copy(n.boundingSphere),ro.applyMatrix4(r),Ji.copy(e.ray).recast(e.near),!(ro.containsPoint(Ji.origin)===!1&&(Ji.intersectSphere(ro,_d)===null||Ji.origin.distanceToSquared(_d)>(e.far-e.near)**2))&&(vd.copy(r).invert(),Ji.copy(e.ray).applyMatrix4(vd),!(n.boundingBox!==null&&Ji.intersectsBox(n.boundingBox)===!1)&&this._computeIntersections(e,t,Ji)))}_computeIntersections(e,t,n){let i,r=this.geometry,a=this.material,o=r.index,c=r.attributes.position,l=r.attributes.uv,u=r.attributes.uv1,h=r.attributes.normal,d=r.groups,f=r.drawRange;if(o!==null)if(Array.isArray(a))for(let g=0,y=d.length;g<y;g++){let m=d[g],p=a[m.materialIndex],x=Math.max(m.start,f.start),v=Math.min(o.count,Math.min(m.start+m.count,f.start+f.count));for(let b=x,S=v;b<S;b+=3){let w=o.getX(b),T=o.getX(b+1),A=o.getX(b+2);i=uo(this,p,e,n,l,u,h,w,T,A),i&&(i.faceIndex=Math.floor(b/3),i.face.materialIndex=m.materialIndex,t.push(i))}}else{let g=Math.max(0,f.start),y=Math.min(o.count,f.start+f.count);for(let m=g,p=y;m<p;m+=3){let x=o.getX(m),v=o.getX(m+1),b=o.getX(m+2);i=uo(this,a,e,n,l,u,h,x,v,b),i&&(i.faceIndex=Math.floor(m/3),t.push(i))}}else if(c!==void 0)if(Array.isArray(a))for(let g=0,y=d.length;g<y;g++){let m=d[g],p=a[m.materialIndex],x=Math.max(m.start,f.start),v=Math.min(c.count,Math.min(m.start+m.count,f.start+f.count));for(let b=x,S=v;b<S;b+=3){let w=b,T=b+1,A=b+2;i=uo(this,p,e,n,l,u,h,w,T,A),i&&(i.faceIndex=Math.floor(b/3),i.face.materialIndex=m.materialIndex,t.push(i))}}else{let g=Math.max(0,f.start),y=Math.min(c.count,f.start+f.count);for(let m=g,p=y;m<p;m+=3){let x=m,v=m+1,b=m+2;i=uo(this,a,e,n,l,u,h,x,v,b),i&&(i.faceIndex=Math.floor(m/3),t.push(i))}}}};function mg(s,e,t,n,i,r,a,o){let c;if(e.side===Dt?c=n.intersectTriangle(a,r,i,!0,o):c=n.intersectTriangle(i,r,a,e.side===pn,o),c===null)return null;ho.copy(o),ho.applyMatrix4(s.matrixWorld);let l=t.ray.origin.distanceTo(ho);return l<t.near||l>t.far?null:{distance:l,point:ho.clone(),object:s}}function uo(s,e,t,n,i,r,a,o,c,l){s.getVertexPosition(o,ao),s.getVertexPosition(c,oo),s.getVertexPosition(l,co);let u=mg(s,e,t,n,ao,oo,co,wd);if(u){let h=new L;en.getBarycoord(wd,ao,oo,co,h),i&&(u.uv=en.getInterpolatedAttribute(i,o,c,l,h,new Ne)),r&&(u.uv1=en.getInterpolatedAttribute(r,o,c,l,h,new Ne)),a&&(u.normal=en.getInterpolatedAttribute(a,o,c,l,h,new L),u.normal.dot(n.direction)>0&&u.normal.multiplyScalar(-1));let d={a:o,b:c,c:l,normal:new L,materialIndex:0};en.getNormal(ao,oo,co,d.normal),u.face=d,u.barycoord=h}return u}var Xn=class s extends Bt{constructor(e=1,t=1,n=1,i=1,r=1,a=1){super(),this.type="BoxGeometry",this.parameters={width:e,height:t,depth:n,widthSegments:i,heightSegments:r,depthSegments:a};let o=this;i=Math.floor(i),r=Math.floor(r),a=Math.floor(a);let c=[],l=[],u=[],h=[],d=0,f=0;g("z","y","x",-1,-1,n,t,e,a,r,0),g("z","y","x",1,-1,n,t,-e,a,r,1),g("x","z","y",1,1,e,n,t,i,a,2),g("x","z","y",1,-1,e,n,-t,i,a,3),g("x","y","z",1,-1,e,t,n,i,r,4),g("x","y","z",-1,-1,e,t,-n,i,r,5),this.setIndex(c),this.setAttribute("position",new Tt(l,3)),this.setAttribute("normal",new Tt(u,3)),this.setAttribute("uv",new Tt(h,2));function g(y,m,p,x,v,b,S,w,T,A,M){let _=b/T,I=S/A,C=b/2,D=S/2,N=w/2,U=T+1,B=A+1,J=0,V=0,ne=new L;for(let ue=0;ue<B;ue++){let _e=ue*I-D;for(let ze=0;ze<U;ze++){let $e=ze*_-C;ne[y]=$e*x,ne[m]=_e*v,ne[p]=N,l.push(ne.x,ne.y,ne.z),ne[y]=0,ne[m]=0,ne[p]=w>0?1:-1,u.push(ne.x,ne.y,ne.z),h.push(ze/T),h.push(1-ue/A),J+=1}}for(let ue=0;ue<A;ue++)for(let _e=0;_e<T;_e++){let ze=d+_e+U*ue,$e=d+_e+U*(ue+1),ht=d+(_e+1)+U*(ue+1),Ye=d+(_e+1)+U*ue;c.push(ze,$e,Ye),c.push($e,ht,Ye),V+=6}o.addGroup(f,V,M),f+=V,d+=J}}copy(e){return super.copy(e),this.parameters=Object.assign({},e.parameters),this}static fromJSON(e){return new s(e.width,e.height,e.depth,e.widthSegments,e.heightSegments,e.depthSegments)}};function gs(s){let e={};for(let t in s){e[t]={};for(let n in s[t]){let i=s[t][n];i&&(i.isColor||i.isMatrix3||i.isMatrix4||i.isVector2||i.isVector3||i.isVector4||i.isTexture||i.isQuaternion)?i.isRenderTargetTexture?(console.warn("UniformsUtils: Textures of render targets cannot be cloned via cloneUniforms() or mergeUniforms()."),e[t][n]=null):e[t][n]=i.clone():Array.isArray(i)?e[t][n]=i.slice():e[t][n]=i}}return e}function sn(s){let e={};for(let t=0;t<s.length;t++){let n=gs(s[t]);for(let i in n)e[i]=n[i]}return e}function gg(s){let e=[];for(let t=0;t<s.length;t++)e.push(s[t].clone());return e}function Th(s){let e=s.getRenderTarget();return e===null?s.outputColorSpace:e.isXRRenderTarget===!0?e.texture.colorSpace:et.workingColorSpace}var Fc={clone:gs,merge:sn},bg=`void main() {
	gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );
}`,yg=`void main() {
	gl_FragColor = vec4( 1.0, 0.0, 0.0, 1.0 );
}`,Yt=class extends cn{constructor(e){super(),this.isShaderMaterial=!0,this.type="ShaderMaterial",this.defines={},this.uniforms={},this.uniformsGroups=[],this.vertexShader=bg,this.fragmentShader=yg,this.linewidth=1,this.wireframe=!1,this.wireframeLinewidth=1,this.fog=!1,this.lights=!1,this.clipping=!1,this.forceSinglePass=!0,this.extensions={clipCullDistance:!1,multiDraw:!1},this.defaultAttributeValues={color:[1,1,1],uv:[0,0],uv1:[0,0]},this.index0AttributeName=void 0,this.uniformsNeedUpdate=!1,this.glslVersion=null,e!==void 0&&this.setValues(e)}copy(e){return super.copy(e),this.fragmentShader=e.fragmentShader,this.vertexShader=e.vertexShader,this.uniforms=gs(e.uniforms),this.uniformsGroups=gg(e.uniformsGroups),this.defines=Object.assign({},e.defines),this.wireframe=e.wireframe,this.wireframeLinewidth=e.wireframeLinewidth,this.fog=e.fog,this.lights=e.lights,this.clipping=e.clipping,this.extensions=Object.assign({},e.extensions),this.glslVersion=e.glslVersion,this}toJSON(e){let t=super.toJSON(e);t.glslVersion=this.glslVersion,t.uniforms={};for(let i in this.uniforms){let a=this.uniforms[i].value;a&&a.isTexture?t.uniforms[i]={type:"t",value:a.toJSON(e).uuid}:a&&a.isColor?t.uniforms[i]={type:"c",value:a.getHex()}:a&&a.isVector2?t.uniforms[i]={type:"v2",value:a.toArray()}:a&&a.isVector3?t.uniforms[i]={type:"v3",value:a.toArray()}:a&&a.isVector4?t.uniforms[i]={type:"v4",value:a.toArray()}:a&&a.isMatrix3?t.uniforms[i]={type:"m3",value:a.toArray()}:a&&a.isMatrix4?t.uniforms[i]={type:"m4",value:a.toArray()}:t.uniforms[i]={value:a}}Object.keys(this.defines).length>0&&(t.defines=this.defines),t.vertexShader=this.vertexShader,t.fragmentShader=this.fragmentShader,t.lights=this.lights,t.clipping=this.clipping;let n={};for(let i in this.extensions)this.extensions[i]===!0&&(n[i]=!0);return Object.keys(n).length>0&&(t.extensions=n),t}},ta=class extends Et{constructor(){super(),this.isCamera=!0,this.type="Camera",this.matrixWorldInverse=new ke,this.projectionMatrix=new ke,this.projectionMatrixInverse=new ke,this.coordinateSystem=Wn,this._reversedDepth=!1}get reversedDepth(){return this._reversedDepth}copy(e,t){return super.copy(e,t),this.matrixWorldInverse.copy(e.matrixWorldInverse),this.projectionMatrix.copy(e.projectionMatrix),this.projectionMatrixInverse.copy(e.projectionMatrixInverse),this.coordinateSystem=e.coordinateSystem,this}getWorldDirection(e){return super.getWorldDirection(e).negate()}updateMatrixWorld(e){super.updateMatrixWorld(e),this.matrixWorldInverse.copy(this.matrixWorld).invert()}updateWorldMatrix(e,t){super.updateWorldMatrix(e,t),this.matrixWorldInverse.copy(this.matrixWorld).invert()}clone(){return new this.constructor().copy(this)}},Ni=new L,Md=new Ne,Sd=new Ne,Ut=class extends ta{constructor(e=50,t=1,n=.1,i=2e3){super(),this.isPerspectiveCamera=!0,this.type="PerspectiveCamera",this.fov=e,this.zoom=1,this.near=n,this.far=i,this.focus=10,this.aspect=t,this.view=null,this.filmGauge=35,this.filmOffset=0,this.updateProjectionMatrix()}copy(e,t){return super.copy(e,t),this.fov=e.fov,this.zoom=e.zoom,this.near=e.near,this.far=e.far,this.focus=e.focus,this.aspect=e.aspect,this.view=e.view===null?null:Object.assign({},e.view),this.filmGauge=e.filmGauge,this.filmOffset=e.filmOffset,this}setFocalLength(e){let t=.5*this.getFilmHeight()/e;this.fov=ss*2*Math.atan(t),this.updateProjectionMatrix()}getFocalLength(){let e=Math.tan(qr*.5*this.fov);return .5*this.getFilmHeight()/e}getEffectiveFOV(){return ss*2*Math.atan(Math.tan(qr*.5*this.fov)/this.zoom)}getFilmWidth(){return this.filmGauge*Math.min(this.aspect,1)}getFilmHeight(){return this.filmGauge/Math.max(this.aspect,1)}getViewBounds(e,t,n){Ni.set(-1,-1,.5).applyMatrix4(this.projectionMatrixInverse),t.set(Ni.x,Ni.y).multiplyScalar(-e/Ni.z),Ni.set(1,1,.5).applyMatrix4(this.projectionMatrixInverse),n.set(Ni.x,Ni.y).multiplyScalar(-e/Ni.z)}getViewSize(e,t){return this.getViewBounds(e,Md,Sd),t.subVectors(Sd,Md)}setViewOffset(e,t,n,i,r,a){this.aspect=e/t,this.view===null&&(this.view={enabled:!0,fullWidth:1,fullHeight:1,offsetX:0,offsetY:0,width:1,height:1}),this.view.enabled=!0,this.view.fullWidth=e,this.view.fullHeight=t,this.view.offsetX=n,this.view.offsetY=i,this.view.width=r,this.view.height=a,this.updateProjectionMatrix()}clearViewOffset(){this.view!==null&&(this.view.enabled=!1),this.updateProjectionMatrix()}updateProjectionMatrix(){let e=this.near,t=e*Math.tan(qr*.5*this.fov)/this.zoom,n=2*t,i=this.aspect*n,r=-.5*i,a=this.view;if(this.view!==null&&this.view.enabled){let c=a.fullWidth,l=a.fullHeight;r+=a.offsetX*i/c,t-=a.offsetY*n/l,i*=a.width/c,n*=a.height/l}let o=this.filmOffset;o!==0&&(r+=e*o/this.getFilmWidth()),this.projectionMatrix.makePerspective(r,r+i,t,t-n,e,this.far,this.coordinateSystem,this.reversedDepth),this.projectionMatrixInverse.copy(this.projectionMatrix).invert()}toJSON(e){let t=super.toJSON(e);return t.object.fov=this.fov,t.object.zoom=this.zoom,t.object.near=this.near,t.object.far=this.far,t.object.focus=this.focus,t.object.aspect=this.aspect,this.view!==null&&(t.object.view=Object.assign({},this.view)),t.object.filmGauge=this.filmGauge,t.object.filmOffset=this.filmOffset,t}},Hs=-90,Vs=1,Co=class extends Et{constructor(e,t,n){super(),this.type="CubeCamera",this.renderTarget=n,this.coordinateSystem=null,this.activeMipmapLevel=0;let i=new Ut(Hs,Vs,e,t);i.layers=this.layers,this.add(i);let r=new Ut(Hs,Vs,e,t);r.layers=this.layers,this.add(r);let a=new Ut(Hs,Vs,e,t);a.layers=this.layers,this.add(a);let o=new Ut(Hs,Vs,e,t);o.layers=this.layers,this.add(o);let c=new Ut(Hs,Vs,e,t);c.layers=this.layers,this.add(c);let l=new Ut(Hs,Vs,e,t);l.layers=this.layers,this.add(l)}updateCoordinateSystem(){let e=this.coordinateSystem,t=this.children.concat(),[n,i,r,a,o,c]=t;for(let l of t)this.remove(l);if(e===Wn)n.up.set(0,1,0),n.lookAt(1,0,0),i.up.set(0,1,0),i.lookAt(-1,0,0),r.up.set(0,0,-1),r.lookAt(0,1,0),a.up.set(0,0,1),a.lookAt(0,-1,0),o.up.set(0,1,0),o.lookAt(0,0,1),c.up.set(0,1,0),c.lookAt(0,0,-1);else if(e===Zr)n.up.set(0,-1,0),n.lookAt(-1,0,0),i.up.set(0,-1,0),i.lookAt(1,0,0),r.up.set(0,0,1),r.lookAt(0,1,0),a.up.set(0,0,-1),a.lookAt(0,-1,0),o.up.set(0,-1,0),o.lookAt(0,0,1),c.up.set(0,-1,0),c.lookAt(0,0,-1);else throw new Error("THREE.CubeCamera.updateCoordinateSystem(): Invalid coordinate system: "+e);for(let l of t)this.add(l),l.updateMatrixWorld()}update(e,t){this.parent===null&&this.updateMatrixWorld();let{renderTarget:n,activeMipmapLevel:i}=this;this.coordinateSystem!==e.coordinateSystem&&(this.coordinateSystem=e.coordinateSystem,this.updateCoordinateSystem());let[r,a,o,c,l,u]=this.children,h=e.getRenderTarget(),d=e.getActiveCubeFace(),f=e.getActiveMipmapLevel(),g=e.xr.enabled;e.xr.enabled=!1;let y=n.texture.generateMipmaps;n.texture.generateMipmaps=!1,e.setRenderTarget(n,0,i),e.render(t,r),e.setRenderTarget(n,1,i),e.render(t,a),e.setRenderTarget(n,2,i),e.render(t,o),e.setRenderTarget(n,3,i),e.render(t,c),e.setRenderTarget(n,4,i),e.render(t,l),n.texture.generateMipmaps=y,e.setRenderTarget(n,5,i),e.render(t,u),e.setRenderTarget(h,d,f),e.xr.enabled=g,n.texture.needsPMREMUpdate=!0}},na=class extends Wt{constructor(e=[],t=fs,n,i,r,a,o,c,l,u){super(e,t,n,i,r,a,o,c,l,u),this.isCubeTexture=!0,this.flipY=!1}get images(){return this.image}set images(e){this.image=e}},Io=class extends ei{constructor(e=1,t={}){super(e,e,t),this.isWebGLCubeRenderTarget=!0;let n={width:e,height:e,depth:1},i=[n,n,n,n,n,n];this.texture=new na(i),this._setTextureOptions(t),this.texture.isRenderTargetTexture=!0}fromEquirectangularTexture(e,t){this.texture.type=t.type,this.texture.colorSpace=t.colorSpace,this.texture.generateMipmaps=t.generateMipmaps,this.texture.minFilter=t.minFilter,this.texture.magFilter=t.magFilter;let n={uniforms:{tEquirect:{value:null}},vertexShader:`

				varying vec3 vWorldDirection;

				vec3 transformDirection( in vec3 dir, in mat4 matrix ) {

					return normalize( ( matrix * vec4( dir, 0.0 ) ).xyz );

				}

				void main() {

					vWorldDirection = transformDirection( position, modelMatrix );

					#include <begin_vertex>
					#include <project_vertex>

				}
			`,fragmentShader:`

				uniform sampler2D tEquirect;

				varying vec3 vWorldDirection;

				#include <common>

				void main() {

					vec3 direction = normalize( vWorldDirection );

					vec2 sampleUV = equirectUv( direction );

					gl_FragColor = texture2D( tEquirect, sampleUV );

				}
			`},i=new Xn(5,5,5),r=new Yt({name:"CubemapFromEquirect",uniforms:gs(n.uniforms),vertexShader:n.vertexShader,fragmentShader:n.fragmentShader,side:Dt,blending:Ti});r.uniforms.tEquirect.value=t;let a=new at(i,r),o=t.minFilter;return t.minFilter===qn&&(t.minFilter=jt),new Co(1,10,this).update(e,a),t.minFilter=o,a.geometry.dispose(),a.material.dispose(),this}clear(e,t=!0,n=!0,i=!0){let r=e.getRenderTarget();for(let a=0;a<6;a++)e.setRenderTarget(this,a),e.clear(t,n,i);e.setRenderTarget(r)}},Gt=class extends Et{constructor(){super(),this.isGroup=!0,this.type="Group"}},xg={type:"move"},er=class{constructor(){this._targetRay=null,this._grip=null,this._hand=null}getHandSpace(){return this._hand===null&&(this._hand=new Gt,this._hand.matrixAutoUpdate=!1,this._hand.visible=!1,this._hand.joints={},this._hand.inputState={pinching:!1}),this._hand}getTargetRaySpace(){return this._targetRay===null&&(this._targetRay=new Gt,this._targetRay.matrixAutoUpdate=!1,this._targetRay.visible=!1,this._targetRay.hasLinearVelocity=!1,this._targetRay.linearVelocity=new L,this._targetRay.hasAngularVelocity=!1,this._targetRay.angularVelocity=new L),this._targetRay}getGripSpace(){return this._grip===null&&(this._grip=new Gt,this._grip.matrixAutoUpdate=!1,this._grip.visible=!1,this._grip.hasLinearVelocity=!1,this._grip.linearVelocity=new L,this._grip.hasAngularVelocity=!1,this._grip.angularVelocity=new L),this._grip}dispatchEvent(e){return this._targetRay!==null&&this._targetRay.dispatchEvent(e),this._grip!==null&&this._grip.dispatchEvent(e),this._hand!==null&&this._hand.dispatchEvent(e),this}connect(e){if(e&&e.hand){let t=this._hand;if(t)for(let n of e.hand.values())this._getHandJoint(t,n)}return this.dispatchEvent({type:"connected",data:e}),this}disconnect(e){return this.dispatchEvent({type:"disconnected",data:e}),this._targetRay!==null&&(this._targetRay.visible=!1),this._grip!==null&&(this._grip.visible=!1),this._hand!==null&&(this._hand.visible=!1),this}update(e,t,n){let i=null,r=null,a=null,o=this._targetRay,c=this._grip,l=this._hand;if(e&&t.session.visibilityState!=="visible-blurred"){if(l&&e.hand){a=!0;for(let y of e.hand.values()){let m=t.getJointPose(y,n),p=this._getHandJoint(l,y);m!==null&&(p.matrix.fromArray(m.transform.matrix),p.matrix.decompose(p.position,p.rotation,p.scale),p.matrixWorldNeedsUpdate=!0,p.jointRadius=m.radius),p.visible=m!==null}let u=l.joints["index-finger-tip"],h=l.joints["thumb-tip"],d=u.position.distanceTo(h.position),f=.02,g=.005;l.inputState.pinching&&d>f+g?(l.inputState.pinching=!1,this.dispatchEvent({type:"pinchend",handedness:e.handedness,target:this})):!l.inputState.pinching&&d<=f-g&&(l.inputState.pinching=!0,this.dispatchEvent({type:"pinchstart",handedness:e.handedness,target:this}))}else c!==null&&e.gripSpace&&(r=t.getPose(e.gripSpace,n),r!==null&&(c.matrix.fromArray(r.transform.matrix),c.matrix.decompose(c.position,c.rotation,c.scale),c.matrixWorldNeedsUpdate=!0,r.linearVelocity?(c.hasLinearVelocity=!0,c.linearVelocity.copy(r.linearVelocity)):c.hasLinearVelocity=!1,r.angularVelocity?(c.hasAngularVelocity=!0,c.angularVelocity.copy(r.angularVelocity)):c.hasAngularVelocity=!1));o!==null&&(i=t.getPose(e.targetRaySpace,n),i===null&&r!==null&&(i=r),i!==null&&(o.matrix.fromArray(i.transform.matrix),o.matrix.decompose(o.position,o.rotation,o.scale),o.matrixWorldNeedsUpdate=!0,i.linearVelocity?(o.hasLinearVelocity=!0,o.linearVelocity.copy(i.linearVelocity)):o.hasLinearVelocity=!1,i.angularVelocity?(o.hasAngularVelocity=!0,o.angularVelocity.copy(i.angularVelocity)):o.hasAngularVelocity=!1,this.dispatchEvent(xg)))}return o!==null&&(o.visible=i!==null),c!==null&&(c.visible=r!==null),l!==null&&(l.visible=a!==null),this}_getHandJoint(e,t){if(e.joints[t.jointName]===void 0){let n=new Gt;n.matrixAutoUpdate=!1,n.visible=!1,e.joints[t.jointName]=n,e.add(n)}return e.joints[t.jointName]}},ia=class s{constructor(e,t=25e-5){this.isFogExp2=!0,this.name="",this.color=new Ue(e),this.density=t}clone(){return new s(this.color,this.density)}toJSON(){return{type:"FogExp2",name:this.name,color:this.color.getHex(),density:this.density}}};var tr=class extends Et{constructor(){super(),this.isScene=!0,this.type="Scene",this.background=null,this.environment=null,this.fog=null,this.backgroundBlurriness=0,this.backgroundIntensity=1,this.backgroundRotation=new Dn,this.environmentIntensity=1,this.environmentRotation=new Dn,this.overrideMaterial=null,typeof __THREE_DEVTOOLS__<"u"&&__THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("observe",{detail:this}))}copy(e,t){return super.copy(e,t),e.background!==null&&(this.background=e.background.clone()),e.environment!==null&&(this.environment=e.environment.clone()),e.fog!==null&&(this.fog=e.fog.clone()),this.backgroundBlurriness=e.backgroundBlurriness,this.backgroundIntensity=e.backgroundIntensity,this.backgroundRotation.copy(e.backgroundRotation),this.environmentIntensity=e.environmentIntensity,this.environmentRotation.copy(e.environmentRotation),e.overrideMaterial!==null&&(this.overrideMaterial=e.overrideMaterial.clone()),this.matrixAutoUpdate=e.matrixAutoUpdate,this}toJSON(e){let t=super.toJSON(e);return this.fog!==null&&(t.object.fog=this.fog.toJSON()),this.backgroundBlurriness>0&&(t.object.backgroundBlurriness=this.backgroundBlurriness),this.backgroundIntensity!==1&&(t.object.backgroundIntensity=this.backgroundIntensity),t.object.backgroundRotation=this.backgroundRotation.toArray(),this.environmentIntensity!==1&&(t.object.environmentIntensity=this.environmentIntensity),t.object.environmentRotation=this.environmentRotation.toArray(),t}},nr=class{constructor(e,t){this.isInterleavedBuffer=!0,this.array=e,this.stride=t,this.count=e!==void 0?e.length/t:0,this.usage=To,this.updateRanges=[],this.version=0,this.uuid=Yn()}onUploadCallback(){}set needsUpdate(e){e===!0&&this.version++}setUsage(e){return this.usage=e,this}addUpdateRange(e,t){this.updateRanges.push({start:e,count:t})}clearUpdateRanges(){this.updateRanges.length=0}copy(e){return this.array=new e.array.constructor(e.array),this.count=e.count,this.stride=e.stride,this.usage=e.usage,this}copyAt(e,t,n){e*=this.stride,n*=t.stride;for(let i=0,r=this.stride;i<r;i++)this.array[e+i]=t.array[n+i];return this}set(e,t=0){return this.array.set(e,t),this}clone(e){e.arrayBuffers===void 0&&(e.arrayBuffers={}),this.array.buffer._uuid===void 0&&(this.array.buffer._uuid=Yn()),e.arrayBuffers[this.array.buffer._uuid]===void 0&&(e.arrayBuffers[this.array.buffer._uuid]=this.array.slice(0).buffer);let t=new this.array.constructor(e.arrayBuffers[this.array.buffer._uuid]),n=new this.constructor(t,this.stride);return n.setUsage(this.usage),n}onUpload(e){return this.onUploadCallback=e,this}toJSON(e){return e.arrayBuffers===void 0&&(e.arrayBuffers={}),this.array.buffer._uuid===void 0&&(this.array.buffer._uuid=Yn()),e.arrayBuffers[this.array.buffer._uuid]===void 0&&(e.arrayBuffers[this.array.buffer._uuid]=Array.from(new Uint32Array(this.array.buffer))),{uuid:this.uuid,buffer:this.array.buffer._uuid,type:this.array.constructor.name,stride:this.stride}}},on=new L,ir=class s{constructor(e,t,n,i=!1){this.isInterleavedBufferAttribute=!0,this.name="",this.data=e,this.itemSize=t,this.offset=n,this.normalized=i}get count(){return this.data.count}get array(){return this.data.array}set needsUpdate(e){this.data.needsUpdate=e}applyMatrix4(e){for(let t=0,n=this.data.count;t<n;t++)on.fromBufferAttribute(this,t),on.applyMatrix4(e),this.setXYZ(t,on.x,on.y,on.z);return this}applyNormalMatrix(e){for(let t=0,n=this.count;t<n;t++)on.fromBufferAttribute(this,t),on.applyNormalMatrix(e),this.setXYZ(t,on.x,on.y,on.z);return this}transformDirection(e){for(let t=0,n=this.count;t<n;t++)on.fromBufferAttribute(this,t),on.transformDirection(e),this.setXYZ(t,on.x,on.y,on.z);return this}getComponent(e,t){let n=this.array[e*this.data.stride+this.offset+t];return this.normalized&&(n=Gn(n,this.array)),n}setComponent(e,t,n){return this.normalized&&(n=ft(n,this.array)),this.data.array[e*this.data.stride+this.offset+t]=n,this}setX(e,t){return this.normalized&&(t=ft(t,this.array)),this.data.array[e*this.data.stride+this.offset]=t,this}setY(e,t){return this.normalized&&(t=ft(t,this.array)),this.data.array[e*this.data.stride+this.offset+1]=t,this}setZ(e,t){return this.normalized&&(t=ft(t,this.array)),this.data.array[e*this.data.stride+this.offset+2]=t,this}setW(e,t){return this.normalized&&(t=ft(t,this.array)),this.data.array[e*this.data.stride+this.offset+3]=t,this}getX(e){let t=this.data.array[e*this.data.stride+this.offset];return this.normalized&&(t=Gn(t,this.array)),t}getY(e){let t=this.data.array[e*this.data.stride+this.offset+1];return this.normalized&&(t=Gn(t,this.array)),t}getZ(e){let t=this.data.array[e*this.data.stride+this.offset+2];return this.normalized&&(t=Gn(t,this.array)),t}getW(e){let t=this.data.array[e*this.data.stride+this.offset+3];return this.normalized&&(t=Gn(t,this.array)),t}setXY(e,t,n){return e=e*this.data.stride+this.offset,this.normalized&&(t=ft(t,this.array),n=ft(n,this.array)),this.data.array[e+0]=t,this.data.array[e+1]=n,this}setXYZ(e,t,n,i){return e=e*this.data.stride+this.offset,this.normalized&&(t=ft(t,this.array),n=ft(n,this.array),i=ft(i,this.array)),this.data.array[e+0]=t,this.data.array[e+1]=n,this.data.array[e+2]=i,this}setXYZW(e,t,n,i,r){return e=e*this.data.stride+this.offset,this.normalized&&(t=ft(t,this.array),n=ft(n,this.array),i=ft(i,this.array),r=ft(r,this.array)),this.data.array[e+0]=t,this.data.array[e+1]=n,this.data.array[e+2]=i,this.data.array[e+3]=r,this}clone(e){if(e===void 0){console.log("THREE.InterleavedBufferAttribute.clone(): Cloning an interleaved buffer attribute will de-interleave buffer data.");let t=[];for(let n=0;n<this.count;n++){let i=n*this.data.stride+this.offset;for(let r=0;r<this.itemSize;r++)t.push(this.data.array[i+r])}return new xt(new this.array.constructor(t),this.itemSize,this.normalized)}else return e.interleavedBuffers===void 0&&(e.interleavedBuffers={}),e.interleavedBuffers[this.data.uuid]===void 0&&(e.interleavedBuffers[this.data.uuid]=this.data.clone(e)),new s(e.interleavedBuffers[this.data.uuid],this.itemSize,this.offset,this.normalized)}toJSON(e){if(e===void 0){console.log("THREE.InterleavedBufferAttribute.toJSON(): Serializing an interleaved buffer attribute will de-interleave buffer data.");let t=[];for(let n=0;n<this.count;n++){let i=n*this.data.stride+this.offset;for(let r=0;r<this.itemSize;r++)t.push(this.data.array[i+r])}return{itemSize:this.itemSize,type:this.array.constructor.name,array:t,normalized:this.normalized}}else return e.interleavedBuffers===void 0&&(e.interleavedBuffers={}),e.interleavedBuffers[this.data.uuid]===void 0&&(e.interleavedBuffers[this.data.uuid]=this.data.toJSON(e)),{isInterleavedBufferAttribute:!0,itemSize:this.itemSize,data:this.data.uuid,offset:this.offset,normalized:this.normalized}}};var Td=new L,Ed=new tt,Ad=new tt,vg=new L,Rd=new ke,fo=new L,Gl=new tn,Cd=new ke,Wl=new Sn,sa=class extends at{constructor(e,t){super(e,t),this.isSkinnedMesh=!0,this.type="SkinnedMesh",this.bindMode=Jl,this.bindMatrix=new ke,this.bindMatrixInverse=new ke,this.boundingBox=null,this.boundingSphere=null}computeBoundingBox(){let e=this.geometry;this.boundingBox===null&&(this.boundingBox=new ot),this.boundingBox.makeEmpty();let t=e.getAttribute("position");for(let n=0;n<t.count;n++)this.getVertexPosition(n,fo),this.boundingBox.expandByPoint(fo)}computeBoundingSphere(){let e=this.geometry;this.boundingSphere===null&&(this.boundingSphere=new tn),this.boundingSphere.makeEmpty();let t=e.getAttribute("position");for(let n=0;n<t.count;n++)this.getVertexPosition(n,fo),this.boundingSphere.expandByPoint(fo)}copy(e,t){return super.copy(e,t),this.bindMode=e.bindMode,this.bindMatrix.copy(e.bindMatrix),this.bindMatrixInverse.copy(e.bindMatrixInverse),this.skeleton=e.skeleton,e.boundingBox!==null&&(this.boundingBox=e.boundingBox.clone()),e.boundingSphere!==null&&(this.boundingSphere=e.boundingSphere.clone()),this}raycast(e,t){let n=this.material,i=this.matrixWorld;n!==void 0&&(this.boundingSphere===null&&this.computeBoundingSphere(),Gl.copy(this.boundingSphere),Gl.applyMatrix4(i),e.ray.intersectsSphere(Gl)!==!1&&(Cd.copy(i).invert(),Wl.copy(e.ray).applyMatrix4(Cd),!(this.boundingBox!==null&&Wl.intersectsBox(this.boundingBox)===!1)&&this._computeIntersections(e,t,Wl)))}getVertexPosition(e,t){return super.getVertexPosition(e,t),this.applyBoneTransform(e,t),t}bind(e,t){this.skeleton=e,t===void 0&&(this.updateMatrixWorld(!0),this.skeleton.calculateInverses(),t=this.matrixWorld),this.bindMatrix.copy(t),this.bindMatrixInverse.copy(t).invert()}pose(){this.skeleton.pose()}normalizeSkinWeights(){let e=new tt,t=this.geometry.attributes.skinWeight;for(let n=0,i=t.count;n<i;n++){e.fromBufferAttribute(t,n);let r=1/e.manhattanLength();r!==1/0?e.multiplyScalar(r):e.set(1,0,0,0),t.setXYZW(n,e.x,e.y,e.z,e.w)}}updateMatrixWorld(e){super.updateMatrixWorld(e),this.bindMode===Jl?this.bindMatrixInverse.copy(this.matrixWorld).invert():this.bindMode===_f?this.bindMatrixInverse.copy(this.bindMatrix).invert():console.warn("THREE.SkinnedMesh: Unrecognized bindMode: "+this.bindMode)}applyBoneTransform(e,t){let n=this.skeleton,i=this.geometry;Ed.fromBufferAttribute(i.attributes.skinIndex,e),Ad.fromBufferAttribute(i.attributes.skinWeight,e),Td.copy(t).applyMatrix4(this.bindMatrix),t.set(0,0,0);for(let r=0;r<4;r++){let a=Ad.getComponent(r);if(a!==0){let o=Ed.getComponent(r);Rd.multiplyMatrices(n.bones[o].matrixWorld,n.boneInverses[o]),t.addScaledVector(vg.copy(Td).applyMatrix4(Rd),a)}}return t.applyMatrix4(this.bindMatrixInverse)}},sr=class extends Et{constructor(){super(),this.isBone=!0,this.type="Bone"}},rs=class extends Wt{constructor(e=null,t=1,n=1,i,r,a,o,c,l=qt,u=qt,h,d){super(null,a,o,c,l,u,i,r,h,d),this.isDataTexture=!0,this.image={data:e,width:t,height:n},this.generateMipmaps=!1,this.flipY=!1,this.unpackAlignment=1}},Id=new ke,_g=new ke,ra=class s{constructor(e=[],t=[]){this.uuid=Yn(),this.bones=e.slice(0),this.boneInverses=t,this.boneMatrices=null,this.boneTexture=null,this.init()}init(){let e=this.bones,t=this.boneInverses;if(this.boneMatrices=new Float32Array(e.length*16),t.length===0)this.calculateInverses();else if(e.length!==t.length){console.warn("THREE.Skeleton: Number of inverse bone matrices does not match amount of bones."),this.boneInverses=[];for(let n=0,i=this.bones.length;n<i;n++)this.boneInverses.push(new ke)}}calculateInverses(){this.boneInverses.length=0;for(let e=0,t=this.bones.length;e<t;e++){let n=new ke;this.bones[e]&&n.copy(this.bones[e].matrixWorld).invert(),this.boneInverses.push(n)}}pose(){for(let e=0,t=this.bones.length;e<t;e++){let n=this.bones[e];n&&n.matrixWorld.copy(this.boneInverses[e]).invert()}for(let e=0,t=this.bones.length;e<t;e++){let n=this.bones[e];n&&(n.parent&&n.parent.isBone?(n.matrix.copy(n.parent.matrixWorld).invert(),n.matrix.multiply(n.matrixWorld)):n.matrix.copy(n.matrixWorld),n.matrix.decompose(n.position,n.quaternion,n.scale))}}update(){let e=this.bones,t=this.boneInverses,n=this.boneMatrices,i=this.boneTexture;for(let r=0,a=e.length;r<a;r++){let o=e[r]?e[r].matrixWorld:_g;Id.multiplyMatrices(o,t[r]),Id.toArray(n,r*16)}i!==null&&(i.needsUpdate=!0)}clone(){return new s(this.bones,this.boneInverses)}computeBoneTexture(){let e=Math.sqrt(this.bones.length*4);e=Math.ceil(e/4)*4,e=Math.max(e,4);let t=new Float32Array(e*e*4);t.set(this.boneMatrices);let n=new rs(t,e,e,Tn,Fn);return n.needsUpdate=!0,this.boneMatrices=t,this.boneTexture=n,this}getBoneByName(e){for(let t=0,n=this.bones.length;t<n;t++){let i=this.bones[t];if(i.name===e)return i}}dispose(){this.boneTexture!==null&&(this.boneTexture.dispose(),this.boneTexture=null)}fromJSON(e,t){this.uuid=e.uuid;for(let n=0,i=e.bones.length;n<i;n++){let r=e.bones[n],a=t[r];a===void 0&&(console.warn("THREE.Skeleton: No bone found with UUID:",r),a=new sr),this.bones.push(a),this.boneInverses.push(new ke().fromArray(e.boneInverses[n]))}return this.init(),this}toJSON(){let e={metadata:{version:4.7,type:"Skeleton",generator:"Skeleton.toJSON"},bones:[],boneInverses:[]};e.uuid=this.uuid;let t=this.bones,n=this.boneInverses;for(let i=0,r=t.length;i<r;i++){let a=t[i];e.bones.push(a.uuid);let o=n[i];e.boneInverses.push(o.toArray())}return e}},Nn=class extends xt{constructor(e,t,n,i=1){super(e,t,n),this.isInstancedBufferAttribute=!0,this.meshPerAttribute=i}copy(e){return super.copy(e),this.meshPerAttribute=e.meshPerAttribute,this}toJSON(){let e=super.toJSON();return e.meshPerAttribute=this.meshPerAttribute,e.isInstancedBufferAttribute=!0,e}},Gs=new ke,Pd=new ke,po=[],kd=new ot,wg=new ke,Gr=new at,Wr=new tn,aa=class extends at{constructor(e,t,n){super(e,t),this.isInstancedMesh=!0,this.instanceMatrix=new Nn(new Float32Array(n*16),16),this.instanceColor=null,this.morphTexture=null,this.count=n,this.boundingBox=null,this.boundingSphere=null;for(let i=0;i<n;i++)this.setMatrixAt(i,wg)}computeBoundingBox(){let e=this.geometry,t=this.count;this.boundingBox===null&&(this.boundingBox=new ot),e.boundingBox===null&&e.computeBoundingBox(),this.boundingBox.makeEmpty();for(let n=0;n<t;n++)this.getMatrixAt(n,Gs),kd.copy(e.boundingBox).applyMatrix4(Gs),this.boundingBox.union(kd)}computeBoundingSphere(){let e=this.geometry,t=this.count;this.boundingSphere===null&&(this.boundingSphere=new tn),e.boundingSphere===null&&e.computeBoundingSphere(),this.boundingSphere.makeEmpty();for(let n=0;n<t;n++)this.getMatrixAt(n,Gs),Wr.copy(e.boundingSphere).applyMatrix4(Gs),this.boundingSphere.union(Wr)}copy(e,t){return super.copy(e,t),this.instanceMatrix.copy(e.instanceMatrix),e.morphTexture!==null&&(this.morphTexture=e.morphTexture.clone()),e.instanceColor!==null&&(this.instanceColor=e.instanceColor.clone()),this.count=e.count,e.boundingBox!==null&&(this.boundingBox=e.boundingBox.clone()),e.boundingSphere!==null&&(this.boundingSphere=e.boundingSphere.clone()),this}getColorAt(e,t){t.fromArray(this.instanceColor.array,e*3)}getMatrixAt(e,t){t.fromArray(this.instanceMatrix.array,e*16)}getMorphAt(e,t){let n=t.morphTargetInfluences,i=this.morphTexture.source.data.data,r=n.length+1,a=e*r+1;for(let o=0;o<n.length;o++)n[o]=i[a+o]}raycast(e,t){let n=this.matrixWorld,i=this.count;if(Gr.geometry=this.geometry,Gr.material=this.material,Gr.material!==void 0&&(this.boundingSphere===null&&this.computeBoundingSphere(),Wr.copy(this.boundingSphere),Wr.applyMatrix4(n),e.ray.intersectsSphere(Wr)!==!1))for(let r=0;r<i;r++){this.getMatrixAt(r,Gs),Pd.multiplyMatrices(n,Gs),Gr.matrixWorld=Pd,Gr.raycast(e,po);for(let a=0,o=po.length;a<o;a++){let c=po[a];c.instanceId=r,c.object=this,t.push(c)}po.length=0}}setColorAt(e,t){this.instanceColor===null&&(this.instanceColor=new Nn(new Float32Array(this.instanceMatrix.count*3).fill(1),3)),t.toArray(this.instanceColor.array,e*3)}setMatrixAt(e,t){t.toArray(this.instanceMatrix.array,e*16)}setMorphAt(e,t){let n=t.morphTargetInfluences,i=n.length+1;this.morphTexture===null&&(this.morphTexture=new rs(new Float32Array(i*this.count),i,this.count,pr,Fn));let r=this.morphTexture.source.data.data,a=0;for(let l=0;l<n.length;l++)a+=n[l];let o=this.geometry.morphTargetsRelative?1:1-a,c=i*e;r[c]=o,r.set(n,c+1)}updateMorphTargets(){}dispose(){this.dispatchEvent({type:"dispose"}),this.morphTexture!==null&&(this.morphTexture.dispose(),this.morphTexture=null)}},Yl=new L,Mg=new L,Sg=new qe,fn=class{constructor(e=new L(1,0,0),t=0){this.isPlane=!0,this.normal=e,this.constant=t}set(e,t){return this.normal.copy(e),this.constant=t,this}setComponents(e,t,n,i){return this.normal.set(e,t,n),this.constant=i,this}setFromNormalAndCoplanarPoint(e,t){return this.normal.copy(e),this.constant=-t.dot(this.normal),this}setFromCoplanarPoints(e,t,n){let i=Yl.subVectors(n,t).cross(Mg.subVectors(e,t)).normalize();return this.setFromNormalAndCoplanarPoint(i,e),this}copy(e){return this.normal.copy(e.normal),this.constant=e.constant,this}normalize(){let e=1/this.normal.length();return this.normal.multiplyScalar(e),this.constant*=e,this}negate(){return this.constant*=-1,this.normal.negate(),this}distanceToPoint(e){return this.normal.dot(e)+this.constant}distanceToSphere(e){return this.distanceToPoint(e.center)-e.radius}projectPoint(e,t){return t.copy(e).addScaledVector(this.normal,-this.distanceToPoint(e))}intersectLine(e,t){let n=e.delta(Yl),i=this.normal.dot(n);if(i===0)return this.distanceToPoint(e.start)===0?t.copy(e.start):null;let r=-(e.start.dot(this.normal)+this.constant)/i;return r<0||r>1?null:t.copy(e.start).addScaledVector(n,r)}intersectsLine(e){let t=this.distanceToPoint(e.start),n=this.distanceToPoint(e.end);return t<0&&n>0||n<0&&t>0}intersectsBox(e){return e.intersectsPlane(this)}intersectsSphere(e){return e.intersectsPlane(this)}coplanarPoint(e){return e.copy(this.normal).multiplyScalar(-this.constant)}applyMatrix4(e,t){let n=t||Sg.getNormalMatrix(e),i=this.coplanarPoint(Yl).applyMatrix4(e),r=this.normal.applyMatrix3(n).normalize();return this.constant=-i.dot(r),this}translate(e){return this.constant-=e.dot(this.normal),this}equals(e){return e.normal.equals(this.normal)&&e.constant===this.constant}clone(){return new this.constructor().copy(this)}},$i=new tn,Tg=new Ne(.5,.5),mo=new L,rr=class{constructor(e=new fn,t=new fn,n=new fn,i=new fn,r=new fn,a=new fn){this.planes=[e,t,n,i,r,a]}set(e,t,n,i,r,a){let o=this.planes;return o[0].copy(e),o[1].copy(t),o[2].copy(n),o[3].copy(i),o[4].copy(r),o[5].copy(a),this}copy(e){let t=this.planes;for(let n=0;n<6;n++)t[n].copy(e.planes[n]);return this}setFromProjectionMatrix(e,t=Wn,n=!1){let i=this.planes,r=e.elements,a=r[0],o=r[1],c=r[2],l=r[3],u=r[4],h=r[5],d=r[6],f=r[7],g=r[8],y=r[9],m=r[10],p=r[11],x=r[12],v=r[13],b=r[14],S=r[15];if(i[0].setComponents(l-a,f-u,p-g,S-x).normalize(),i[1].setComponents(l+a,f+u,p+g,S+x).normalize(),i[2].setComponents(l+o,f+h,p+y,S+v).normalize(),i[3].setComponents(l-o,f-h,p-y,S-v).normalize(),n)i[4].setComponents(c,d,m,b).normalize(),i[5].setComponents(l-c,f-d,p-m,S-b).normalize();else if(i[4].setComponents(l-c,f-d,p-m,S-b).normalize(),t===Wn)i[5].setComponents(l+c,f+d,p+m,S+b).normalize();else if(t===Zr)i[5].setComponents(c,d,m,b).normalize();else throw new Error("THREE.Frustum.setFromProjectionMatrix(): Invalid coordinate system: "+t);return this}intersectsObject(e){if(e.boundingSphere!==void 0)e.boundingSphere===null&&e.computeBoundingSphere(),$i.copy(e.boundingSphere).applyMatrix4(e.matrixWorld);else{let t=e.geometry;t.boundingSphere===null&&t.computeBoundingSphere(),$i.copy(t.boundingSphere).applyMatrix4(e.matrixWorld)}return this.intersectsSphere($i)}intersectsSprite(e){$i.center.set(0,0,0);let t=Tg.distanceTo(e.center);return $i.radius=.7071067811865476+t,$i.applyMatrix4(e.matrixWorld),this.intersectsSphere($i)}intersectsSphere(e){let t=this.planes,n=e.center,i=-e.radius;for(let r=0;r<6;r++)if(t[r].distanceToPoint(n)<i)return!1;return!0}intersectsBox(e){let t=this.planes;for(let n=0;n<6;n++){let i=t[n];if(mo.x=i.normal.x>0?e.max.x:e.min.x,mo.y=i.normal.y>0?e.max.y:e.min.y,mo.z=i.normal.z>0?e.max.z:e.min.z,i.distanceToPoint(mo)<0)return!1}return!0}containsPoint(e){let t=this.planes;for(let n=0;n<6;n++)if(t[n].distanceToPoint(e)<0)return!1;return!0}clone(){return new this.constructor().copy(this)}};var ar=class extends cn{constructor(e){super(),this.isLineBasicMaterial=!0,this.type="LineBasicMaterial",this.color=new Ue(16777215),this.map=null,this.linewidth=1,this.linecap="round",this.linejoin="round",this.fog=!0,this.setValues(e)}copy(e){return super.copy(e),this.color.copy(e.color),this.map=e.map,this.linewidth=e.linewidth,this.linecap=e.linecap,this.linejoin=e.linejoin,this.fog=e.fog,this}},Po=new L,ko=new L,Ld=new ke,Yr=new Sn,go=new tn,Xl=new L,Dd=new L,as=class extends Et{constructor(e=new Bt,t=new ar){super(),this.isLine=!0,this.type="Line",this.geometry=e,this.material=t,this.morphTargetDictionary=void 0,this.morphTargetInfluences=void 0,this.updateMorphTargets()}copy(e,t){return super.copy(e,t),this.material=Array.isArray(e.material)?e.material.slice():e.material,this.geometry=e.geometry,this}computeLineDistances(){let e=this.geometry;if(e.index===null){let t=e.attributes.position,n=[0];for(let i=1,r=t.count;i<r;i++)Po.fromBufferAttribute(t,i-1),ko.fromBufferAttribute(t,i),n[i]=n[i-1],n[i]+=Po.distanceTo(ko);e.setAttribute("lineDistance",new Tt(n,1))}else console.warn("THREE.Line.computeLineDistances(): Computation only possible with non-indexed BufferGeometry.");return this}raycast(e,t){let n=this.geometry,i=this.matrixWorld,r=e.params.Line.threshold,a=n.drawRange;if(n.boundingSphere===null&&n.computeBoundingSphere(),go.copy(n.boundingSphere),go.applyMatrix4(i),go.radius+=r,e.ray.intersectsSphere(go)===!1)return;Ld.copy(i).invert(),Yr.copy(e.ray).applyMatrix4(Ld);let o=r/((this.scale.x+this.scale.y+this.scale.z)/3),c=o*o,l=this.isLineSegments?2:1,u=n.index,d=n.attributes.position;if(u!==null){let f=Math.max(0,a.start),g=Math.min(u.count,a.start+a.count);for(let y=f,m=g-1;y<m;y+=l){let p=u.getX(y),x=u.getX(y+1),v=bo(this,e,Yr,c,p,x,y);v&&t.push(v)}if(this.isLineLoop){let y=u.getX(g-1),m=u.getX(f),p=bo(this,e,Yr,c,y,m,g-1);p&&t.push(p)}}else{let f=Math.max(0,a.start),g=Math.min(d.count,a.start+a.count);for(let y=f,m=g-1;y<m;y+=l){let p=bo(this,e,Yr,c,y,y+1,y);p&&t.push(p)}if(this.isLineLoop){let y=bo(this,e,Yr,c,g-1,f,g-1);y&&t.push(y)}}}updateMorphTargets(){let t=this.geometry.morphAttributes,n=Object.keys(t);if(n.length>0){let i=t[n[0]];if(i!==void 0){this.morphTargetInfluences=[],this.morphTargetDictionary={};for(let r=0,a=i.length;r<a;r++){let o=i[r].name||String(r);this.morphTargetInfluences.push(0),this.morphTargetDictionary[o]=r}}}}};function bo(s,e,t,n,i,r,a){let o=s.geometry.attributes.position;if(Po.fromBufferAttribute(o,i),ko.fromBufferAttribute(o,r),t.distanceSqToSegment(Po,ko,Xl,Dd)>n)return;Xl.applyMatrix4(s.matrixWorld);let l=e.ray.origin.distanceTo(Xl);if(!(l<e.near||l>e.far))return{distance:l,point:Dd.clone().applyMatrix4(s.matrixWorld),index:a,face:null,faceIndex:null,barycoord:null,object:s}}var Nd=new L,Fd=new L,oa=class extends as{constructor(e,t){super(e,t),this.isLineSegments=!0,this.type="LineSegments"}computeLineDistances(){let e=this.geometry;if(e.index===null){let t=e.attributes.position,n=[];for(let i=0,r=t.count;i<r;i+=2)Nd.fromBufferAttribute(t,i),Fd.fromBufferAttribute(t,i+1),n[i]=i===0?0:n[i-1],n[i+1]=n[i]+Nd.distanceTo(Fd);e.setAttribute("lineDistance",new Tt(n,1))}else console.warn("THREE.LineSegments.computeLineDistances(): Computation only possible with non-indexed BufferGeometry.");return this}},ca=class extends as{constructor(e,t){super(e,t),this.isLineLoop=!0,this.type="LineLoop"}},or=class extends cn{constructor(e){super(),this.isPointsMaterial=!0,this.type="PointsMaterial",this.color=new Ue(16777215),this.map=null,this.alphaMap=null,this.size=1,this.sizeAttenuation=!0,this.fog=!0,this.setValues(e)}copy(e){return super.copy(e),this.color.copy(e.color),this.map=e.map,this.alphaMap=e.alphaMap,this.size=e.size,this.sizeAttenuation=e.sizeAttenuation,this.fog=e.fog,this}},Ud=new ke,nh=new Sn,yo=new tn,xo=new L,la=class extends Et{constructor(e=new Bt,t=new or){super(),this.isPoints=!0,this.type="Points",this.geometry=e,this.material=t,this.morphTargetDictionary=void 0,this.morphTargetInfluences=void 0,this.updateMorphTargets()}copy(e,t){return super.copy(e,t),this.material=Array.isArray(e.material)?e.material.slice():e.material,this.geometry=e.geometry,this}raycast(e,t){let n=this.geometry,i=this.matrixWorld,r=e.params.Points.threshold,a=n.drawRange;if(n.boundingSphere===null&&n.computeBoundingSphere(),yo.copy(n.boundingSphere),yo.applyMatrix4(i),yo.radius+=r,e.ray.intersectsSphere(yo)===!1)return;Ud.copy(i).invert(),nh.copy(e.ray).applyMatrix4(Ud);let o=r/((this.scale.x+this.scale.y+this.scale.z)/3),c=o*o,l=n.index,h=n.attributes.position;if(l!==null){let d=Math.max(0,a.start),f=Math.min(l.count,a.start+a.count);for(let g=d,y=f;g<y;g++){let m=l.getX(g);xo.fromBufferAttribute(h,m),Bd(xo,m,c,i,e,t,this)}}else{let d=Math.max(0,a.start),f=Math.min(h.count,a.start+a.count);for(let g=d,y=f;g<y;g++)xo.fromBufferAttribute(h,g),Bd(xo,g,c,i,e,t,this)}}updateMorphTargets(){let t=this.geometry.morphAttributes,n=Object.keys(t);if(n.length>0){let i=t[n[0]];if(i!==void 0){this.morphTargetInfluences=[],this.morphTargetDictionary={};for(let r=0,a=i.length;r<a;r++){let o=i[r].name||String(r);this.morphTargetInfluences.push(0),this.morphTargetDictionary[o]=r}}}}};function Bd(s,e,t,n,i,r,a){let o=nh.distanceSqToPoint(s);if(o<t){let c=new L;nh.closestPointToPoint(s,c),c.applyMatrix4(n);let l=i.ray.origin.distanceTo(c);if(l<i.near||l>i.far)return;r.push({distance:l,distanceToRay:Math.sqrt(o),point:c,index:e,face:null,faceIndex:null,barycoord:null,object:a})}}var ha=class extends Wt{constructor(e,t,n=Oi,i,r,a,o=qt,c=qt,l,u=Ks,h=1){if(u!==Ks&&u!==fr)throw new Error("DepthTexture format must be either THREE.DepthFormat or THREE.DepthStencilFormat");let d={width:e,height:t,depth:h};super(d,i,r,a,o,c,u,n,l),this.isDepthTexture=!0,this.flipY=!1,this.generateMipmaps=!1,this.compareFunction=null}copy(e){return super.copy(e),this.source=new $s(Object.assign({},e.image)),this.compareFunction=e.compareFunction,this}toJSON(e){let t=super.toJSON(e);return this.compareFunction!==null&&(t.compareFunction=this.compareFunction),t}},ua=class extends Wt{constructor(e=null){super(),this.sourceTexture=e,this.isExternalTexture=!0}copy(e){return super.copy(e),this.sourceTexture=e.sourceTexture,this}};var da=class s extends Bt{constructor(e=1,t=32,n=0,i=Math.PI*2){super(),this.type="CircleGeometry",this.parameters={radius:e,segments:t,thetaStart:n,thetaLength:i},t=Math.max(3,t);let r=[],a=[],o=[],c=[],l=new L,u=new Ne;a.push(0,0,0),o.push(0,0,1),c.push(.5,.5);for(let h=0,d=3;h<=t;h++,d+=3){let f=n+h/t*i;l.x=e*Math.cos(f),l.y=e*Math.sin(f),a.push(l.x,l.y,l.z),o.push(0,0,1),u.x=(a[d]/e+1)/2,u.y=(a[d+1]/e+1)/2,c.push(u.x,u.y)}for(let h=1;h<=t;h++)r.push(h,h+1,0);this.setIndex(r),this.setAttribute("position",new Tt(a,3)),this.setAttribute("normal",new Tt(o,3)),this.setAttribute("uv",new Tt(c,2))}copy(e){return super.copy(e),this.parameters=Object.assign({},e.parameters),this}static fromJSON(e){return new s(e.radius,e.segments,e.thetaStart,e.thetaLength)}},os=class s extends Bt{constructor(e=1,t=1,n=1,i=32,r=1,a=!1,o=0,c=Math.PI*2){super(),this.type="CylinderGeometry",this.parameters={radiusTop:e,radiusBottom:t,height:n,radialSegments:i,heightSegments:r,openEnded:a,thetaStart:o,thetaLength:c};let l=this;i=Math.floor(i),r=Math.floor(r);let u=[],h=[],d=[],f=[],g=0,y=[],m=n/2,p=0;x(),a===!1&&(e>0&&v(!0),t>0&&v(!1)),this.setIndex(u),this.setAttribute("position",new Tt(h,3)),this.setAttribute("normal",new Tt(d,3)),this.setAttribute("uv",new Tt(f,2));function x(){let b=new L,S=new L,w=0,T=(t-e)/n;for(let A=0;A<=r;A++){let M=[],_=A/r,I=_*(t-e)+e;for(let C=0;C<=i;C++){let D=C/i,N=D*c+o,U=Math.sin(N),B=Math.cos(N);S.x=I*U,S.y=-_*n+m,S.z=I*B,h.push(S.x,S.y,S.z),b.set(U,T,B).normalize(),d.push(b.x,b.y,b.z),f.push(D,1-_),M.push(g++)}y.push(M)}for(let A=0;A<i;A++)for(let M=0;M<r;M++){let _=y[M][A],I=y[M+1][A],C=y[M+1][A+1],D=y[M][A+1];(e>0||M!==0)&&(u.push(_,I,D),w+=3),(t>0||M!==r-1)&&(u.push(I,C,D),w+=3)}l.addGroup(p,w,0),p+=w}function v(b){let S=g,w=new Ne,T=new L,A=0,M=b===!0?e:t,_=b===!0?1:-1;for(let C=1;C<=i;C++)h.push(0,m*_,0),d.push(0,_,0),f.push(.5,.5),g++;let I=g;for(let C=0;C<=i;C++){let N=C/i*c+o,U=Math.cos(N),B=Math.sin(N);T.x=M*B,T.y=m*_,T.z=M*U,h.push(T.x,T.y,T.z),d.push(0,_,0),w.x=U*.5+.5,w.y=B*.5*_+.5,f.push(w.x,w.y),g++}for(let C=0;C<i;C++){let D=S+C,N=I+C;b===!0?u.push(N,N+1,D):u.push(N+1,N,D),A+=3}l.addGroup(p,A,b===!0?1:2),p+=A}}copy(e){return super.copy(e),this.parameters=Object.assign({},e.parameters),this}static fromJSON(e){return new s(e.radiusTop,e.radiusBottom,e.height,e.radialSegments,e.heightSegments,e.openEnded,e.thetaStart,e.thetaLength)}};var Bi=class s extends Bt{constructor(e=1,t=1,n=1,i=1){super(),this.type="PlaneGeometry",this.parameters={width:e,height:t,widthSegments:n,heightSegments:i};let r=e/2,a=t/2,o=Math.floor(n),c=Math.floor(i),l=o+1,u=c+1,h=e/o,d=t/c,f=[],g=[],y=[],m=[];for(let p=0;p<u;p++){let x=p*d-a;for(let v=0;v<l;v++){let b=v*h-r;g.push(b,-x,0),y.push(0,0,1),m.push(v/o),m.push(1-p/c)}}for(let p=0;p<c;p++)for(let x=0;x<o;x++){let v=x+l*p,b=x+l*(p+1),S=x+1+l*(p+1),w=x+1+l*p;f.push(v,b,w),f.push(b,S,w)}this.setIndex(f),this.setAttribute("position",new Tt(g,3)),this.setAttribute("normal",new Tt(y,3)),this.setAttribute("uv",new Tt(m,2))}copy(e){return super.copy(e),this.parameters=Object.assign({},e.parameters),this}static fromJSON(e){return new s(e.width,e.height,e.widthSegments,e.heightSegments)}},fa=class s extends Bt{constructor(e=.5,t=1,n=32,i=1,r=0,a=Math.PI*2){super(),this.type="RingGeometry",this.parameters={innerRadius:e,outerRadius:t,thetaSegments:n,phiSegments:i,thetaStart:r,thetaLength:a},n=Math.max(3,n),i=Math.max(1,i);let o=[],c=[],l=[],u=[],h=e,d=(t-e)/i,f=new L,g=new Ne;for(let y=0;y<=i;y++){for(let m=0;m<=n;m++){let p=r+m/n*a;f.x=h*Math.cos(p),f.y=h*Math.sin(p),c.push(f.x,f.y,f.z),l.push(0,0,1),g.x=(f.x/t+1)/2,g.y=(f.y/t+1)/2,u.push(g.x,g.y)}h+=d}for(let y=0;y<i;y++){let m=y*(n+1);for(let p=0;p<n;p++){let x=p+m,v=x,b=x+n+1,S=x+n+2,w=x+1;o.push(v,b,w),o.push(b,S,w)}}this.setIndex(o),this.setAttribute("position",new Tt(c,3)),this.setAttribute("normal",new Tt(l,3)),this.setAttribute("uv",new Tt(u,2))}copy(e){return super.copy(e),this.parameters=Object.assign({},e.parameters),this}static fromJSON(e){return new s(e.innerRadius,e.outerRadius,e.thetaSegments,e.phiSegments,e.thetaStart,e.thetaLength)}};var Lt=class extends cn{constructor(e){super(),this.isMeshStandardMaterial=!0,this.type="MeshStandardMaterial",this.defines={STANDARD:""},this.color=new Ue(16777215),this.roughness=1,this.metalness=0,this.map=null,this.lightMap=null,this.lightMapIntensity=1,this.aoMap=null,this.aoMapIntensity=1,this.emissive=new Ue(0),this.emissiveIntensity=1,this.emissiveMap=null,this.bumpMap=null,this.bumpScale=1,this.normalMap=null,this.normalMapType=Nc,this.normalScale=new Ne(1,1),this.displacementMap=null,this.displacementScale=1,this.displacementBias=0,this.roughnessMap=null,this.metalnessMap=null,this.alphaMap=null,this.envMap=null,this.envMapRotation=new Dn,this.envMapIntensity=1,this.wireframe=!1,this.wireframeLinewidth=1,this.wireframeLinecap="round",this.wireframeLinejoin="round",this.flatShading=!1,this.fog=!0,this.setValues(e)}copy(e){return super.copy(e),this.defines={STANDARD:""},this.color.copy(e.color),this.roughness=e.roughness,this.metalness=e.metalness,this.map=e.map,this.lightMap=e.lightMap,this.lightMapIntensity=e.lightMapIntensity,this.aoMap=e.aoMap,this.aoMapIntensity=e.aoMapIntensity,this.emissive.copy(e.emissive),this.emissiveMap=e.emissiveMap,this.emissiveIntensity=e.emissiveIntensity,this.bumpMap=e.bumpMap,this.bumpScale=e.bumpScale,this.normalMap=e.normalMap,this.normalMapType=e.normalMapType,this.normalScale.copy(e.normalScale),this.displacementMap=e.displacementMap,this.displacementScale=e.displacementScale,this.displacementBias=e.displacementBias,this.roughnessMap=e.roughnessMap,this.metalnessMap=e.metalnessMap,this.alphaMap=e.alphaMap,this.envMap=e.envMap,this.envMapRotation.copy(e.envMapRotation),this.envMapIntensity=e.envMapIntensity,this.wireframe=e.wireframe,this.wireframeLinewidth=e.wireframeLinewidth,this.wireframeLinecap=e.wireframeLinecap,this.wireframeLinejoin=e.wireframeLinejoin,this.flatShading=e.flatShading,this.fog=e.fog,this}},mn=class extends Lt{constructor(e){super(),this.isMeshPhysicalMaterial=!0,this.defines={STANDARD:"",PHYSICAL:""},this.type="MeshPhysicalMaterial",this.anisotropyRotation=0,this.anisotropyMap=null,this.clearcoatMap=null,this.clearcoatRoughness=0,this.clearcoatRoughnessMap=null,this.clearcoatNormalScale=new Ne(1,1),this.clearcoatNormalMap=null,this.ior=1.5,Object.defineProperty(this,"reflectivity",{get:function(){return We(2.5*(this.ior-1)/(this.ior+1),0,1)},set:function(t){this.ior=(1+.4*t)/(1-.4*t)}}),this.iridescenceMap=null,this.iridescenceIOR=1.3,this.iridescenceThicknessRange=[100,400],this.iridescenceThicknessMap=null,this.sheenColor=new Ue(0),this.sheenColorMap=null,this.sheenRoughness=1,this.sheenRoughnessMap=null,this.transmissionMap=null,this.thickness=0,this.thicknessMap=null,this.attenuationDistance=1/0,this.attenuationColor=new Ue(1,1,1),this.specularIntensity=1,this.specularIntensityMap=null,this.specularColor=new Ue(1,1,1),this.specularColorMap=null,this._anisotropy=0,this._clearcoat=0,this._dispersion=0,this._iridescence=0,this._sheen=0,this._transmission=0,this.setValues(e)}get anisotropy(){return this._anisotropy}set anisotropy(e){this._anisotropy>0!=e>0&&this.version++,this._anisotropy=e}get clearcoat(){return this._clearcoat}set clearcoat(e){this._clearcoat>0!=e>0&&this.version++,this._clearcoat=e}get iridescence(){return this._iridescence}set iridescence(e){this._iridescence>0!=e>0&&this.version++,this._iridescence=e}get dispersion(){return this._dispersion}set dispersion(e){this._dispersion>0!=e>0&&this.version++,this._dispersion=e}get sheen(){return this._sheen}set sheen(e){this._sheen>0!=e>0&&this.version++,this._sheen=e}get transmission(){return this._transmission}set transmission(e){this._transmission>0!=e>0&&this.version++,this._transmission=e}copy(e){return super.copy(e),this.defines={STANDARD:"",PHYSICAL:""},this.anisotropy=e.anisotropy,this.anisotropyRotation=e.anisotropyRotation,this.anisotropyMap=e.anisotropyMap,this.clearcoat=e.clearcoat,this.clearcoatMap=e.clearcoatMap,this.clearcoatRoughness=e.clearcoatRoughness,this.clearcoatRoughnessMap=e.clearcoatRoughnessMap,this.clearcoatNormalMap=e.clearcoatNormalMap,this.clearcoatNormalScale.copy(e.clearcoatNormalScale),this.dispersion=e.dispersion,this.ior=e.ior,this.iridescence=e.iridescence,this.iridescenceMap=e.iridescenceMap,this.iridescenceIOR=e.iridescenceIOR,this.iridescenceThicknessRange=[...e.iridescenceThicknessRange],this.iridescenceThicknessMap=e.iridescenceThicknessMap,this.sheen=e.sheen,this.sheenColor.copy(e.sheenColor),this.sheenColorMap=e.sheenColorMap,this.sheenRoughness=e.sheenRoughness,this.sheenRoughnessMap=e.sheenRoughnessMap,this.transmission=e.transmission,this.transmissionMap=e.transmissionMap,this.thickness=e.thickness,this.thicknessMap=e.thicknessMap,this.attenuationDistance=e.attenuationDistance,this.attenuationColor.copy(e.attenuationColor),this.specularIntensity=e.specularIntensity,this.specularIntensityMap=e.specularIntensityMap,this.specularColor.copy(e.specularColor),this.specularColorMap=e.specularColorMap,this}};var pa=class extends cn{constructor(e){super(),this.isMeshLambertMaterial=!0,this.type="MeshLambertMaterial",this.color=new Ue(16777215),this.map=null,this.lightMap=null,this.lightMapIntensity=1,this.aoMap=null,this.aoMapIntensity=1,this.emissive=new Ue(0),this.emissiveIntensity=1,this.emissiveMap=null,this.bumpMap=null,this.bumpScale=1,this.normalMap=null,this.normalMapType=Nc,this.normalScale=new Ne(1,1),this.displacementMap=null,this.displacementScale=1,this.displacementBias=0,this.specularMap=null,this.alphaMap=null,this.envMap=null,this.envMapRotation=new Dn,this.combine=Zo,this.reflectivity=1,this.refractionRatio=.98,this.wireframe=!1,this.wireframeLinewidth=1,this.wireframeLinecap="round",this.wireframeLinejoin="round",this.flatShading=!1,this.fog=!0,this.setValues(e)}copy(e){return super.copy(e),this.color.copy(e.color),this.map=e.map,this.lightMap=e.lightMap,this.lightMapIntensity=e.lightMapIntensity,this.aoMap=e.aoMap,this.aoMapIntensity=e.aoMapIntensity,this.emissive.copy(e.emissive),this.emissiveMap=e.emissiveMap,this.emissiveIntensity=e.emissiveIntensity,this.bumpMap=e.bumpMap,this.bumpScale=e.bumpScale,this.normalMap=e.normalMap,this.normalMapType=e.normalMapType,this.normalScale.copy(e.normalScale),this.displacementMap=e.displacementMap,this.displacementScale=e.displacementScale,this.displacementBias=e.displacementBias,this.specularMap=e.specularMap,this.alphaMap=e.alphaMap,this.envMap=e.envMap,this.envMapRotation.copy(e.envMapRotation),this.combine=e.combine,this.reflectivity=e.reflectivity,this.refractionRatio=e.refractionRatio,this.wireframe=e.wireframe,this.wireframeLinewidth=e.wireframeLinewidth,this.wireframeLinecap=e.wireframeLinecap,this.wireframeLinejoin=e.wireframeLinejoin,this.flatShading=e.flatShading,this.fog=e.fog,this}},Lo=class extends cn{constructor(e){super(),this.isMeshDepthMaterial=!0,this.type="MeshDepthMaterial",this.depthPacking=Mf,this.map=null,this.alphaMap=null,this.displacementMap=null,this.displacementScale=1,this.displacementBias=0,this.wireframe=!1,this.wireframeLinewidth=1,this.setValues(e)}copy(e){return super.copy(e),this.depthPacking=e.depthPacking,this.map=e.map,this.alphaMap=e.alphaMap,this.displacementMap=e.displacementMap,this.displacementScale=e.displacementScale,this.displacementBias=e.displacementBias,this.wireframe=e.wireframe,this.wireframeLinewidth=e.wireframeLinewidth,this}},Do=class extends cn{constructor(e){super(),this.isMeshDistanceMaterial=!0,this.type="MeshDistanceMaterial",this.map=null,this.alphaMap=null,this.displacementMap=null,this.displacementScale=1,this.displacementBias=0,this.setValues(e)}copy(e){return super.copy(e),this.map=e.map,this.alphaMap=e.alphaMap,this.displacementMap=e.displacementMap,this.displacementScale=e.displacementScale,this.displacementBias=e.displacementBias,this}};function vo(s,e){return!s||s.constructor===e?s:typeof e.BYTES_PER_ELEMENT=="number"?new e(s):Array.prototype.slice.call(s)}function Eg(s){return ArrayBuffer.isView(s)&&!(s instanceof DataView)}function Ag(s){function e(i,r){return s[i]-s[r]}let t=s.length,n=new Array(t);for(let i=0;i!==t;++i)n[i]=i;return n.sort(e),n}function Od(s,e,t){let n=s.length,i=new s.constructor(n);for(let r=0,a=0;a!==n;++r){let o=t[r]*e;for(let c=0;c!==e;++c)i[a++]=s[o+c]}return i}function Ff(s,e,t,n){let i=1,r=s[0];for(;r!==void 0&&r[n]===void 0;)r=s[i++];if(r===void 0)return;let a=r[n];if(a!==void 0)if(Array.isArray(a))do a=r[n],a!==void 0&&(e.push(r.time),t.push(...a)),r=s[i++];while(r!==void 0);else if(a.toArray!==void 0)do a=r[n],a!==void 0&&(e.push(r.time),a.toArray(t,t.length)),r=s[i++];while(r!==void 0);else do a=r[n],a!==void 0&&(e.push(r.time),t.push(a)),r=s[i++];while(r!==void 0)}var vi=class{constructor(e,t,n,i){this.parameterPositions=e,this._cachedIndex=0,this.resultBuffer=i!==void 0?i:new t.constructor(n),this.sampleValues=t,this.valueSize=n,this.settings=null,this.DefaultSettings_={}}evaluate(e){let t=this.parameterPositions,n=this._cachedIndex,i=t[n],r=t[n-1];n:{e:{let a;t:{i:if(!(e<i)){for(let o=n+2;;){if(i===void 0){if(e<r)break i;return n=t.length,this._cachedIndex=n,this.copySampleValue_(n-1)}if(n===o)break;if(r=i,i=t[++n],e<i)break e}a=t.length;break t}if(!(e>=r)){let o=t[1];e<o&&(n=2,r=o);for(let c=n-2;;){if(r===void 0)return this._cachedIndex=0,this.copySampleValue_(0);if(n===c)break;if(i=r,r=t[--n-1],e>=r)break e}a=n,n=0;break t}break n}for(;n<a;){let o=n+a>>>1;e<t[o]?a=o:n=o+1}if(i=t[n],r=t[n-1],r===void 0)return this._cachedIndex=0,this.copySampleValue_(0);if(i===void 0)return n=t.length,this._cachedIndex=n,this.copySampleValue_(n-1)}this._cachedIndex=n,this.intervalChanged_(n,r,i)}return this.interpolate_(n,r,e,i)}getSettings_(){return this.settings||this.DefaultSettings_}copySampleValue_(e){let t=this.resultBuffer,n=this.sampleValues,i=this.valueSize,r=e*i;for(let a=0;a!==i;++a)t[a]=n[r+a];return t}interpolate_(){throw new Error("call to abstract method")}intervalChanged_(){}},No=class extends vi{constructor(e,t,n,i){super(e,t,n,i),this._weightPrev=-0,this._offsetPrev=-0,this._weightNext=-0,this._offsetNext=-0,this.DefaultSettings_={endingStart:$l,endingEnd:$l}}intervalChanged_(e,t,n){let i=this.parameterPositions,r=e-2,a=e+1,o=i[r],c=i[a];if(o===void 0)switch(this.getSettings_().endingStart){case Ql:r=e,o=2*t-n;break;case eh:r=i.length-2,o=t+i[r]-i[r+1];break;default:r=e,o=n}if(c===void 0)switch(this.getSettings_().endingEnd){case Ql:a=e,c=2*n-t;break;case eh:a=1,c=n+i[1]-i[0];break;default:a=e-1,c=t}let l=(n-t)*.5,u=this.valueSize;this._weightPrev=l/(t-o),this._weightNext=l/(c-n),this._offsetPrev=r*u,this._offsetNext=a*u}interpolate_(e,t,n,i){let r=this.resultBuffer,a=this.sampleValues,o=this.valueSize,c=e*o,l=c-o,u=this._offsetPrev,h=this._offsetNext,d=this._weightPrev,f=this._weightNext,g=(n-t)/(i-t),y=g*g,m=y*g,p=-d*m+2*d*y-d*g,x=(1+d)*m+(-1.5-2*d)*y+(-.5+d)*g+1,v=(-1-f)*m+(1.5+f)*y+.5*g,b=f*m-f*y;for(let S=0;S!==o;++S)r[S]=p*a[u+S]+x*a[l+S]+v*a[c+S]+b*a[h+S];return r}},Fo=class extends vi{constructor(e,t,n,i){super(e,t,n,i)}interpolate_(e,t,n,i){let r=this.resultBuffer,a=this.sampleValues,o=this.valueSize,c=e*o,l=c-o,u=(n-t)/(i-t),h=1-u;for(let d=0;d!==o;++d)r[d]=a[l+d]*h+a[c+d]*u;return r}},Uo=class extends vi{constructor(e,t,n,i){super(e,t,n,i)}interpolate_(e){return this.copySampleValue_(e-1)}},gn=class{constructor(e,t,n,i){if(e===void 0)throw new Error("THREE.KeyframeTrack: track name is undefined");if(t===void 0||t.length===0)throw new Error("THREE.KeyframeTrack: no keyframes in track named "+e);this.name=e,this.times=vo(t,this.TimeBufferType),this.values=vo(n,this.ValueBufferType),this.setInterpolation(i||this.DefaultInterpolation)}static toJSON(e){let t=e.constructor,n;if(t.toJSON!==this.toJSON)n=t.toJSON(e);else{n={name:e.name,times:vo(e.times,Array),values:vo(e.values,Array)};let i=e.getInterpolation();i!==e.DefaultInterpolation&&(n.interpolation=i)}return n.type=e.ValueTypeName,n}InterpolantFactoryMethodDiscrete(e){return new Uo(this.times,this.values,this.getValueSize(),e)}InterpolantFactoryMethodLinear(e){return new Fo(this.times,this.values,this.getValueSize(),e)}InterpolantFactoryMethodSmooth(e){return new No(this.times,this.values,this.getValueSize(),e)}setInterpolation(e){let t;switch(e){case ns:t=this.InterpolantFactoryMethodDiscrete;break;case is:t=this.InterpolantFactoryMethodLinear;break;case wo:t=this.InterpolantFactoryMethodSmooth;break}if(t===void 0){let n="unsupported interpolation for "+this.ValueTypeName+" keyframe track named "+this.name;if(this.createInterpolant===void 0)if(e!==this.DefaultInterpolation)this.setInterpolation(this.DefaultInterpolation);else throw new Error(n);return console.warn("THREE.KeyframeTrack:",n),this}return this.createInterpolant=t,this}getInterpolation(){switch(this.createInterpolant){case this.InterpolantFactoryMethodDiscrete:return ns;case this.InterpolantFactoryMethodLinear:return is;case this.InterpolantFactoryMethodSmooth:return wo}}getValueSize(){return this.values.length/this.times.length}shift(e){if(e!==0){let t=this.times;for(let n=0,i=t.length;n!==i;++n)t[n]+=e}return this}scale(e){if(e!==1){let t=this.times;for(let n=0,i=t.length;n!==i;++n)t[n]*=e}return this}trim(e,t){let n=this.times,i=n.length,r=0,a=i-1;for(;r!==i&&n[r]<e;)++r;for(;a!==-1&&n[a]>t;)--a;if(++a,r!==0||a!==i){r>=a&&(a=Math.max(a,1),r=a-1);let o=this.getValueSize();this.times=n.slice(r,a),this.values=this.values.slice(r*o,a*o)}return this}validate(){let e=!0,t=this.getValueSize();t-Math.floor(t)!==0&&(console.error("THREE.KeyframeTrack: Invalid value size in track.",this),e=!1);let n=this.times,i=this.values,r=n.length;r===0&&(console.error("THREE.KeyframeTrack: Track is empty.",this),e=!1);let a=null;for(let o=0;o!==r;o++){let c=n[o];if(typeof c=="number"&&isNaN(c)){console.error("THREE.KeyframeTrack: Time is not a valid number.",this,o,c),e=!1;break}if(a!==null&&a>c){console.error("THREE.KeyframeTrack: Out of order keys.",this,o,c,a),e=!1;break}a=c}if(i!==void 0&&Eg(i))for(let o=0,c=i.length;o!==c;++o){let l=i[o];if(isNaN(l)){console.error("THREE.KeyframeTrack: Value is not a valid number.",this,o,l),e=!1;break}}return e}optimize(){let e=this.times.slice(),t=this.values.slice(),n=this.getValueSize(),i=this.getInterpolation()===wo,r=e.length-1,a=1;for(let o=1;o<r;++o){let c=!1,l=e[o],u=e[o+1];if(l!==u&&(o!==1||l!==e[0]))if(i)c=!0;else{let h=o*n,d=h-n,f=h+n;for(let g=0;g!==n;++g){let y=t[h+g];if(y!==t[d+g]||y!==t[f+g]){c=!0;break}}}if(c){if(o!==a){e[a]=e[o];let h=o*n,d=a*n;for(let f=0;f!==n;++f)t[d+f]=t[h+f]}++a}}if(r>0){e[a]=e[r];for(let o=r*n,c=a*n,l=0;l!==n;++l)t[c+l]=t[o+l];++a}return a!==e.length?(this.times=e.slice(0,a),this.values=t.slice(0,a*n)):(this.times=e,this.values=t),this}clone(){let e=this.times.slice(),t=this.values.slice(),n=this.constructor,i=new n(this.name,e,t);return i.createInterpolant=this.createInterpolant,i}};gn.prototype.ValueTypeName="";gn.prototype.TimeBufferType=Float32Array;gn.prototype.ValueBufferType=Float32Array;gn.prototype.DefaultInterpolation=is;var _i=class extends gn{constructor(e,t,n){super(e,t,n)}};_i.prototype.ValueTypeName="bool";_i.prototype.ValueBufferType=Array;_i.prototype.DefaultInterpolation=ns;_i.prototype.InterpolantFactoryMethodLinear=void 0;_i.prototype.InterpolantFactoryMethodSmooth=void 0;var ma=class extends gn{constructor(e,t,n,i){super(e,t,n,i)}};ma.prototype.ValueTypeName="color";var ti=class extends gn{constructor(e,t,n,i){super(e,t,n,i)}};ti.prototype.ValueTypeName="number";var Bo=class extends vi{constructor(e,t,n,i){super(e,t,n,i)}interpolate_(e,t,n,i){let r=this.resultBuffer,a=this.sampleValues,o=this.valueSize,c=(n-t)/(i-t),l=e*o;for(let u=l+o;l!==u;l+=4)Ln.slerpFlat(r,0,a,l-o,a,l,c);return r}},ni=class extends gn{constructor(e,t,n,i){super(e,t,n,i)}InterpolantFactoryMethodLinear(e){return new Bo(this.times,this.values,this.getValueSize(),e)}};ni.prototype.ValueTypeName="quaternion";ni.prototype.InterpolantFactoryMethodSmooth=void 0;var wi=class extends gn{constructor(e,t,n){super(e,t,n)}};wi.prototype.ValueTypeName="string";wi.prototype.ValueBufferType=Array;wi.prototype.DefaultInterpolation=ns;wi.prototype.InterpolantFactoryMethodLinear=void 0;wi.prototype.InterpolantFactoryMethodSmooth=void 0;var ii=class extends gn{constructor(e,t,n,i){super(e,t,n,i)}};ii.prototype.ValueTypeName="vector";var ga=class{constructor(e="",t=-1,n=[],i=wf){this.name=e,this.tracks=n,this.duration=t,this.blendMode=i,this.uuid=Yn(),this.userData={},this.duration<0&&this.resetDuration()}static parse(e){let t=[],n=e.tracks,i=1/(e.fps||1);for(let a=0,o=n.length;a!==o;++a)t.push(Cg(n[a]).scale(i));let r=new this(e.name,e.duration,t,e.blendMode);return r.uuid=e.uuid,r.userData=JSON.parse(e.userData||"{}"),r}static toJSON(e){let t=[],n=e.tracks,i={name:e.name,duration:e.duration,tracks:t,uuid:e.uuid,blendMode:e.blendMode,userData:JSON.stringify(e.userData)};for(let r=0,a=n.length;r!==a;++r)t.push(gn.toJSON(n[r]));return i}static CreateFromMorphTargetSequence(e,t,n,i){let r=t.length,a=[];for(let o=0;o<r;o++){let c=[],l=[];c.push((o+r-1)%r,o,(o+1)%r),l.push(0,1,0);let u=Ag(c);c=Od(c,1,u),l=Od(l,1,u),!i&&c[0]===0&&(c.push(r),l.push(l[0])),a.push(new ti(".morphTargetInfluences["+t[o].name+"]",c,l).scale(1/n))}return new this(e,-1,a)}static findByName(e,t){let n=e;if(!Array.isArray(e)){let i=e;n=i.geometry&&i.geometry.animations||i.animations}for(let i=0;i<n.length;i++)if(n[i].name===t)return n[i];return null}static CreateClipsFromMorphTargetSequences(e,t,n){let i={},r=/^([\w-]*?)([\d]+)$/;for(let o=0,c=e.length;o<c;o++){let l=e[o],u=l.name.match(r);if(u&&u.length>1){let h=u[1],d=i[h];d||(i[h]=d=[]),d.push(l)}}let a=[];for(let o in i)a.push(this.CreateFromMorphTargetSequence(o,i[o],t,n));return a}static parseAnimation(e,t){if(console.warn("THREE.AnimationClip: parseAnimation() is deprecated and will be removed with r185"),!e)return console.error("THREE.AnimationClip: No animation in JSONLoader data."),null;let n=function(h,d,f,g,y){if(f.length!==0){let m=[],p=[];Ff(f,m,p,g),m.length!==0&&y.push(new h(d,m,p))}},i=[],r=e.name||"default",a=e.fps||30,o=e.blendMode,c=e.length||-1,l=e.hierarchy||[];for(let h=0;h<l.length;h++){let d=l[h].keys;if(!(!d||d.length===0))if(d[0].morphTargets){let f={},g;for(g=0;g<d.length;g++)if(d[g].morphTargets)for(let y=0;y<d[g].morphTargets.length;y++)f[d[g].morphTargets[y]]=-1;for(let y in f){let m=[],p=[];for(let x=0;x!==d[g].morphTargets.length;++x){let v=d[g];m.push(v.time),p.push(v.morphTarget===y?1:0)}i.push(new ti(".morphTargetInfluence["+y+"]",m,p))}c=f.length*a}else{let f=".bones["+t[h].name+"]";n(ii,f+".position",d,"pos",i),n(ni,f+".quaternion",d,"rot",i),n(ii,f+".scale",d,"scl",i)}}return i.length===0?null:new this(r,c,i,o)}resetDuration(){let e=this.tracks,t=0;for(let n=0,i=e.length;n!==i;++n){let r=this.tracks[n];t=Math.max(t,r.times[r.times.length-1])}return this.duration=t,this}trim(){for(let e=0;e<this.tracks.length;e++)this.tracks[e].trim(0,this.duration);return this}validate(){let e=!0;for(let t=0;t<this.tracks.length;t++)e=e&&this.tracks[t].validate();return e}optimize(){for(let e=0;e<this.tracks.length;e++)this.tracks[e].optimize();return this}clone(){let e=[];for(let n=0;n<this.tracks.length;n++)e.push(this.tracks[n].clone());let t=new this.constructor(this.name,this.duration,e,this.blendMode);return t.userData=JSON.parse(JSON.stringify(this.userData)),t}toJSON(){return this.constructor.toJSON(this)}};function Rg(s){switch(s.toLowerCase()){case"scalar":case"double":case"float":case"number":case"integer":return ti;case"vector":case"vector2":case"vector3":case"vector4":return ii;case"color":return ma;case"quaternion":return ni;case"bool":case"boolean":return _i;case"string":return wi}throw new Error("THREE.KeyframeTrack: Unsupported typeName: "+s)}function Cg(s){if(s.type===void 0)throw new Error("THREE.KeyframeTrack: track type undefined, can not parse");let e=Rg(s.type);if(s.times===void 0){let t=[],n=[];Ff(s.keys,t,n,"value"),s.times=t,s.values=n}return e.parse!==void 0?e.parse(s):new e(s.name,s.times,s.values,s.interpolation)}var Qn={enabled:!1,files:{},add:function(s,e){this.enabled!==!1&&(this.files[s]=e)},get:function(s){if(this.enabled!==!1)return this.files[s]},remove:function(s){delete this.files[s]},clear:function(){this.files={}}},Oo=class{constructor(e,t,n){let i=this,r=!1,a=0,o=0,c,l=[];this.onStart=void 0,this.onLoad=e,this.onProgress=t,this.onError=n,this.abortController=new AbortController,this.itemStart=function(u){o++,r===!1&&i.onStart!==void 0&&i.onStart(u,a,o),r=!0},this.itemEnd=function(u){a++,i.onProgress!==void 0&&i.onProgress(u,a,o),a===o&&(r=!1,i.onLoad!==void 0&&i.onLoad())},this.itemError=function(u){i.onError!==void 0&&i.onError(u)},this.resolveURL=function(u){return c?c(u):u},this.setURLModifier=function(u){return c=u,this},this.addHandler=function(u,h){return l.push(u,h),this},this.removeHandler=function(u){let h=l.indexOf(u);return h!==-1&&l.splice(h,2),this},this.getHandler=function(u){for(let h=0,d=l.length;h<d;h+=2){let f=l[h],g=l[h+1];if(f.global&&(f.lastIndex=0),f.test(u))return g}return null},this.abort=function(){return this.abortController.abort(),this.abortController=new AbortController,this}}},Uf=new Oo,si=class{constructor(e){this.manager=e!==void 0?e:Uf,this.crossOrigin="anonymous",this.withCredentials=!1,this.path="",this.resourcePath="",this.requestHeader={}}load(){}loadAsync(e,t){let n=this;return new Promise(function(i,r){n.load(e,i,t,r)})}parse(){}setCrossOrigin(e){return this.crossOrigin=e,this}setWithCredentials(e){return this.withCredentials=e,this}setPath(e){return this.path=e,this}setResourcePath(e){return this.resourcePath=e,this}setRequestHeader(e){return this.requestHeader=e,this}abort(){return this}};si.DEFAULT_MATERIAL_NAME="__DEFAULT";var gi={},ih=class extends Error{constructor(e,t){super(e),this.response=t}},cr=class extends si{constructor(e){super(e),this.mimeType="",this.responseType="",this._abortController=new AbortController}load(e,t,n,i){e===void 0&&(e=""),this.path!==void 0&&(e=this.path+e),e=this.manager.resolveURL(e);let r=Qn.get(`file:${e}`);if(r!==void 0)return this.manager.itemStart(e),setTimeout(()=>{t&&t(r),this.manager.itemEnd(e)},0),r;if(gi[e]!==void 0){gi[e].push({onLoad:t,onProgress:n,onError:i});return}gi[e]=[],gi[e].push({onLoad:t,onProgress:n,onError:i});let a=new Request(e,{headers:new Headers(this.requestHeader),credentials:this.withCredentials?"include":"same-origin",signal:typeof AbortSignal.any=="function"?AbortSignal.any([this._abortController.signal,this.manager.abortController.signal]):this._abortController.signal}),o=this.mimeType,c=this.responseType;fetch(a).then(l=>{if(l.status===200||l.status===0){if(l.status===0&&console.warn("THREE.FileLoader: HTTP Status 0 received."),typeof ReadableStream>"u"||l.body===void 0||l.body.getReader===void 0)return l;let u=gi[e],h=l.body.getReader(),d=l.headers.get("X-File-Size")||l.headers.get("Content-Length"),f=d?parseInt(d):0,g=f!==0,y=0,m=new ReadableStream({start(p){x();function x(){h.read().then(({done:v,value:b})=>{if(v)p.close();else{y+=b.byteLength;let S=new ProgressEvent("progress",{lengthComputable:g,loaded:y,total:f});for(let w=0,T=u.length;w<T;w++){let A=u[w];A.onProgress&&A.onProgress(S)}p.enqueue(b),x()}},v=>{p.error(v)})}}});return new Response(m)}else throw new ih(`fetch for "${l.url}" responded with ${l.status}: ${l.statusText}`,l)}).then(l=>{switch(c){case"arraybuffer":return l.arrayBuffer();case"blob":return l.blob();case"document":return l.text().then(u=>new DOMParser().parseFromString(u,o));case"json":return l.json();default:if(o==="")return l.text();{let h=/charset="?([^;"\s]*)"?/i.exec(o),d=h&&h[1]?h[1].toLowerCase():void 0,f=new TextDecoder(d);return l.arrayBuffer().then(g=>f.decode(g))}}}).then(l=>{Qn.add(`file:${e}`,l);let u=gi[e];delete gi[e];for(let h=0,d=u.length;h<d;h++){let f=u[h];f.onLoad&&f.onLoad(l)}}).catch(l=>{let u=gi[e];if(u===void 0)throw this.manager.itemError(e),l;delete gi[e];for(let h=0,d=u.length;h<d;h++){let f=u[h];f.onError&&f.onError(l)}this.manager.itemError(e)}).finally(()=>{this.manager.itemEnd(e)}),this.manager.itemStart(e)}setResponseType(e){return this.responseType=e,this}setMimeType(e){return this.mimeType=e,this}abort(){return this._abortController.abort(),this._abortController=new AbortController,this}};var Ws=new WeakMap,zo=class extends si{constructor(e){super(e)}load(e,t,n,i){this.path!==void 0&&(e=this.path+e),e=this.manager.resolveURL(e);let r=this,a=Qn.get(`image:${e}`);if(a!==void 0){if(a.complete===!0)r.manager.itemStart(e),setTimeout(function(){t&&t(a),r.manager.itemEnd(e)},0);else{let h=Ws.get(a);h===void 0&&(h=[],Ws.set(a,h)),h.push({onLoad:t,onError:i})}return a}let o=Zs("img");function c(){u(),t&&t(this);let h=Ws.get(this)||[];for(let d=0;d<h.length;d++){let f=h[d];f.onLoad&&f.onLoad(this)}Ws.delete(this),r.manager.itemEnd(e)}function l(h){u(),i&&i(h),Qn.remove(`image:${e}`);let d=Ws.get(this)||[];for(let f=0;f<d.length;f++){let g=d[f];g.onError&&g.onError(h)}Ws.delete(this),r.manager.itemError(e),r.manager.itemEnd(e)}function u(){o.removeEventListener("load",c,!1),o.removeEventListener("error",l,!1)}return o.addEventListener("load",c,!1),o.addEventListener("error",l,!1),e.slice(0,5)!=="data:"&&this.crossOrigin!==void 0&&(o.crossOrigin=this.crossOrigin),Qn.add(`image:${e}`,o),r.manager.itemStart(e),o.src=e,o}};var cs=class extends si{constructor(e){super(e)}load(e,t,n,i){let r=new Wt,a=new zo(this.manager);return a.setCrossOrigin(this.crossOrigin),a.setPath(this.path),a.load(e,function(o){r.image=o,r.needsUpdate=!0,t!==void 0&&t(r)},n,i),r}},ls=class extends Et{constructor(e,t=1){super(),this.isLight=!0,this.type="Light",this.color=new Ue(e),this.intensity=t}dispose(){}copy(e,t){return super.copy(e,t),this.color.copy(e.color),this.intensity=e.intensity,this}toJSON(e){let t=super.toJSON(e);return t.object.color=this.color.getHex(),t.object.intensity=this.intensity,this.groundColor!==void 0&&(t.object.groundColor=this.groundColor.getHex()),this.distance!==void 0&&(t.object.distance=this.distance),this.angle!==void 0&&(t.object.angle=this.angle),this.decay!==void 0&&(t.object.decay=this.decay),this.penumbra!==void 0&&(t.object.penumbra=this.penumbra),this.shadow!==void 0&&(t.object.shadow=this.shadow.toJSON()),this.target!==void 0&&(t.object.target=this.target.uuid),t}},ba=class extends ls{constructor(e,t,n){super(e,n),this.isHemisphereLight=!0,this.type="HemisphereLight",this.position.copy(Et.DEFAULT_UP),this.updateMatrix(),this.groundColor=new Ue(t)}copy(e,t){return super.copy(e,t),this.groundColor.copy(e.groundColor),this}},ql=new ke,zd=new L,Hd=new L,ya=class{constructor(e){this.camera=e,this.intensity=1,this.bias=0,this.normalBias=0,this.radius=1,this.blurSamples=8,this.mapSize=new Ne(512,512),this.mapType=jn,this.map=null,this.mapPass=null,this.matrix=new ke,this.autoUpdate=!0,this.needsUpdate=!1,this._frustum=new rr,this._frameExtents=new Ne(1,1),this._viewportCount=1,this._viewports=[new tt(0,0,1,1)]}getViewportCount(){return this._viewportCount}getFrustum(){return this._frustum}updateMatrices(e){let t=this.camera,n=this.matrix;zd.setFromMatrixPosition(e.matrixWorld),t.position.copy(zd),Hd.setFromMatrixPosition(e.target.matrixWorld),t.lookAt(Hd),t.updateMatrixWorld(),ql.multiplyMatrices(t.projectionMatrix,t.matrixWorldInverse),this._frustum.setFromProjectionMatrix(ql,t.coordinateSystem,t.reversedDepth),t.reversedDepth?n.set(.5,0,0,.5,0,.5,0,.5,0,0,1,0,0,0,0,1):n.set(.5,0,0,.5,0,.5,0,.5,0,0,.5,.5,0,0,0,1),n.multiply(ql)}getViewport(e){return this._viewports[e]}getFrameExtents(){return this._frameExtents}dispose(){this.map&&this.map.dispose(),this.mapPass&&this.mapPass.dispose()}copy(e){return this.camera=e.camera.clone(),this.intensity=e.intensity,this.bias=e.bias,this.radius=e.radius,this.autoUpdate=e.autoUpdate,this.needsUpdate=e.needsUpdate,this.normalBias=e.normalBias,this.blurSamples=e.blurSamples,this.mapSize.copy(e.mapSize),this}clone(){return new this.constructor().copy(this)}toJSON(){let e={};return this.intensity!==1&&(e.intensity=this.intensity),this.bias!==0&&(e.bias=this.bias),this.normalBias!==0&&(e.normalBias=this.normalBias),this.radius!==1&&(e.radius=this.radius),(this.mapSize.x!==512||this.mapSize.y!==512)&&(e.mapSize=this.mapSize.toArray()),e.camera=this.camera.toJSON(!1).object,delete e.camera.matrix,e}},sh=class extends ya{constructor(){super(new Ut(50,1,.5,500)),this.isSpotLightShadow=!0,this.focus=1,this.aspect=1}updateMatrices(e){let t=this.camera,n=ss*2*e.angle*this.focus,i=this.mapSize.width/this.mapSize.height*this.aspect,r=e.distance||t.far;(n!==t.fov||i!==t.aspect||r!==t.far)&&(t.fov=n,t.aspect=i,t.far=r,t.updateProjectionMatrix()),super.updateMatrices(e)}copy(e){return super.copy(e),this.focus=e.focus,this}},xa=class extends ls{constructor(e,t,n=0,i=Math.PI/3,r=0,a=2){super(e,t),this.isSpotLight=!0,this.type="SpotLight",this.position.copy(Et.DEFAULT_UP),this.updateMatrix(),this.target=new Et,this.distance=n,this.angle=i,this.penumbra=r,this.decay=a,this.map=null,this.shadow=new sh}get power(){return this.intensity*Math.PI}set power(e){this.intensity=e/Math.PI}dispose(){this.shadow.dispose()}copy(e,t){return super.copy(e,t),this.distance=e.distance,this.angle=e.angle,this.penumbra=e.penumbra,this.decay=e.decay,this.target=e.target.clone(),this.shadow=e.shadow.clone(),this}},Vd=new ke,Xr=new L,jl=new L,rh=class extends ya{constructor(){super(new Ut(90,1,.5,500)),this.isPointLightShadow=!0,this._frameExtents=new Ne(4,2),this._viewportCount=6,this._viewports=[new tt(2,1,1,1),new tt(0,1,1,1),new tt(3,1,1,1),new tt(1,1,1,1),new tt(3,0,1,1),new tt(1,0,1,1)],this._cubeDirections=[new L(1,0,0),new L(-1,0,0),new L(0,0,1),new L(0,0,-1),new L(0,1,0),new L(0,-1,0)],this._cubeUps=[new L(0,1,0),new L(0,1,0),new L(0,1,0),new L(0,1,0),new L(0,0,1),new L(0,0,-1)]}updateMatrices(e,t=0){let n=this.camera,i=this.matrix,r=e.distance||n.far;r!==n.far&&(n.far=r,n.updateProjectionMatrix()),Xr.setFromMatrixPosition(e.matrixWorld),n.position.copy(Xr),jl.copy(n.position),jl.add(this._cubeDirections[t]),n.up.copy(this._cubeUps[t]),n.lookAt(jl),n.updateMatrixWorld(),i.makeTranslation(-Xr.x,-Xr.y,-Xr.z),Vd.multiplyMatrices(n.projectionMatrix,n.matrixWorldInverse),this._frustum.setFromProjectionMatrix(Vd,n.coordinateSystem,n.reversedDepth)}},Mi=class extends ls{constructor(e,t,n=0,i=2){super(e,t),this.isPointLight=!0,this.type="PointLight",this.distance=n,this.decay=i,this.shadow=new rh}get power(){return this.intensity*4*Math.PI}set power(e){this.intensity=e/(4*Math.PI)}dispose(){this.shadow.dispose()}copy(e,t){return super.copy(e,t),this.distance=e.distance,this.decay=e.decay,this.shadow=e.shadow.clone(),this}},hs=class extends ta{constructor(e=-1,t=1,n=1,i=-1,r=.1,a=2e3){super(),this.isOrthographicCamera=!0,this.type="OrthographicCamera",this.zoom=1,this.view=null,this.left=e,this.right=t,this.top=n,this.bottom=i,this.near=r,this.far=a,this.updateProjectionMatrix()}copy(e,t){return super.copy(e,t),this.left=e.left,this.right=e.right,this.top=e.top,this.bottom=e.bottom,this.near=e.near,this.far=e.far,this.zoom=e.zoom,this.view=e.view===null?null:Object.assign({},e.view),this}setViewOffset(e,t,n,i,r,a){this.view===null&&(this.view={enabled:!0,fullWidth:1,fullHeight:1,offsetX:0,offsetY:0,width:1,height:1}),this.view.enabled=!0,this.view.fullWidth=e,this.view.fullHeight=t,this.view.offsetX=n,this.view.offsetY=i,this.view.width=r,this.view.height=a,this.updateProjectionMatrix()}clearViewOffset(){this.view!==null&&(this.view.enabled=!1),this.updateProjectionMatrix()}updateProjectionMatrix(){let e=(this.right-this.left)/(2*this.zoom),t=(this.top-this.bottom)/(2*this.zoom),n=(this.right+this.left)/2,i=(this.top+this.bottom)/2,r=n-e,a=n+e,o=i+t,c=i-t;if(this.view!==null&&this.view.enabled){let l=(this.right-this.left)/this.view.fullWidth/this.zoom,u=(this.top-this.bottom)/this.view.fullHeight/this.zoom;r+=l*this.view.offsetX,a=r+l*this.view.width,o-=u*this.view.offsetY,c=o-u*this.view.height}this.projectionMatrix.makeOrthographic(r,a,o,c,this.near,this.far,this.coordinateSystem,this.reversedDepth),this.projectionMatrixInverse.copy(this.projectionMatrix).invert()}toJSON(e){let t=super.toJSON(e);return t.object.zoom=this.zoom,t.object.left=this.left,t.object.right=this.right,t.object.top=this.top,t.object.bottom=this.bottom,t.object.near=this.near,t.object.far=this.far,this.view!==null&&(t.object.view=Object.assign({},this.view)),t}},ah=class extends ya{constructor(){super(new hs(-5,5,5,-5,.5,500)),this.isDirectionalLightShadow=!0}},us=class extends ls{constructor(e,t){super(e,t),this.isDirectionalLight=!0,this.type="DirectionalLight",this.position.copy(Et.DEFAULT_UP),this.updateMatrix(),this.target=new Et,this.shadow=new ah}dispose(){this.shadow.dispose()}copy(e){return super.copy(e),this.target=e.target.clone(),this.shadow=e.shadow.clone(),this}};var Si=class{static extractUrlBase(e){let t=e.lastIndexOf("/");return t===-1?"./":e.slice(0,t+1)}static resolveURL(e,t){return typeof e!="string"||e===""?"":(/^https?:\/\//i.test(t)&&/^\//.test(e)&&(t=t.replace(/(^https?:\/\/[^\/]+).*/i,"$1")),/^(https?:)?\/\//i.test(e)||/^data:.*,.*$/i.test(e)||/^blob:.*$/i.test(e)?e:t+e)}},lr=class extends Bt{constructor(){super(),this.isInstancedBufferGeometry=!0,this.type="InstancedBufferGeometry",this.instanceCount=1/0}copy(e){return super.copy(e),this.instanceCount=e.instanceCount,this}toJSON(){let e=super.toJSON();return e.instanceCount=this.instanceCount,e.isInstancedBufferGeometry=!0,e}};var Kl=new WeakMap,va=class extends si{constructor(e){super(e),this.isImageBitmapLoader=!0,typeof createImageBitmap>"u"&&console.warn("THREE.ImageBitmapLoader: createImageBitmap() not supported."),typeof fetch>"u"&&console.warn("THREE.ImageBitmapLoader: fetch() not supported."),this.options={premultiplyAlpha:"none"},this._abortController=new AbortController}setOptions(e){return this.options=e,this}load(e,t,n,i){e===void 0&&(e=""),this.path!==void 0&&(e=this.path+e),e=this.manager.resolveURL(e);let r=this,a=Qn.get(`image-bitmap:${e}`);if(a!==void 0){if(r.manager.itemStart(e),a.then){a.then(l=>{if(Kl.has(a)===!0)i&&i(Kl.get(a)),r.manager.itemError(e),r.manager.itemEnd(e);else return t&&t(l),r.manager.itemEnd(e),l});return}return setTimeout(function(){t&&t(a),r.manager.itemEnd(e)},0),a}let o={};o.credentials=this.crossOrigin==="anonymous"?"same-origin":"include",o.headers=this.requestHeader,o.signal=typeof AbortSignal.any=="function"?AbortSignal.any([this._abortController.signal,this.manager.abortController.signal]):this._abortController.signal;let c=fetch(e,o).then(function(l){return l.blob()}).then(function(l){return createImageBitmap(l,Object.assign(r.options,{colorSpaceConversion:"none"}))}).then(function(l){return Qn.add(`image-bitmap:${e}`,l),t&&t(l),r.manager.itemEnd(e),l}).catch(function(l){i&&i(l),Kl.set(c,l),Qn.remove(`image-bitmap:${e}`),r.manager.itemError(e),r.manager.itemEnd(e)});Qn.add(`image-bitmap:${e}`,c),r.manager.itemStart(e)}abort(){return this._abortController.abort(),this._abortController=new AbortController,this}};var Ho=class extends Ut{constructor(e=[]){super(),this.isArrayCamera=!0,this.isMultiViewCamera=!1,this.cameras=e}},_a=class{constructor(e=!0){this.autoStart=e,this.startTime=0,this.oldTime=0,this.elapsedTime=0,this.running=!1}start(){this.startTime=performance.now(),this.oldTime=this.startTime,this.elapsedTime=0,this.running=!0}stop(){this.getElapsedTime(),this.running=!1,this.autoStart=!1}getElapsedTime(){return this.getDelta(),this.elapsedTime}getDelta(){let e=0;if(this.autoStart&&!this.running)return this.start(),0;if(this.running){let t=performance.now();e=(t-this.oldTime)/1e3,this.oldTime=t,this.elapsedTime+=e}return e}};var Eh="\\[\\]\\.:\\/",Ig=new RegExp("["+Eh+"]","g"),Ah="[^"+Eh+"]",Pg="[^"+Eh.replace("\\.","")+"]",kg=/((?:WC+[\/:])*)/.source.replace("WC",Ah),Lg=/(WCOD+)?/.source.replace("WCOD",Pg),Dg=/(?:\.(WC+)(?:\[(.+)\])?)?/.source.replace("WC",Ah),Ng=/\.(WC+)(?:\[(.+)\])?/.source.replace("WC",Ah),Fg=new RegExp("^"+kg+Lg+Dg+Ng+"$"),Ug=["material","materials","bones","map"],oh=class{constructor(e,t,n){let i=n||yt.parseTrackName(t);this._targetGroup=e,this._bindings=e.subscribe_(t,i)}getValue(e,t){this.bind();let n=this._targetGroup.nCachedObjects_,i=this._bindings[n];i!==void 0&&i.getValue(e,t)}setValue(e,t){let n=this._bindings;for(let i=this._targetGroup.nCachedObjects_,r=n.length;i!==r;++i)n[i].setValue(e,t)}bind(){let e=this._bindings;for(let t=this._targetGroup.nCachedObjects_,n=e.length;t!==n;++t)e[t].bind()}unbind(){let e=this._bindings;for(let t=this._targetGroup.nCachedObjects_,n=e.length;t!==n;++t)e[t].unbind()}},yt=class s{constructor(e,t,n){this.path=t,this.parsedPath=n||s.parseTrackName(t),this.node=s.findNode(e,this.parsedPath.nodeName),this.rootNode=e,this.getValue=this._getValue_unbound,this.setValue=this._setValue_unbound}static create(e,t,n){return e&&e.isAnimationObjectGroup?new s.Composite(e,t,n):new s(e,t,n)}static sanitizeNodeName(e){return e.replace(/\s/g,"_").replace(Ig,"")}static parseTrackName(e){let t=Fg.exec(e);if(t===null)throw new Error("PropertyBinding: Cannot parse trackName: "+e);let n={nodeName:t[2],objectName:t[3],objectIndex:t[4],propertyName:t[5],propertyIndex:t[6]},i=n.nodeName&&n.nodeName.lastIndexOf(".");if(i!==void 0&&i!==-1){let r=n.nodeName.substring(i+1);Ug.indexOf(r)!==-1&&(n.nodeName=n.nodeName.substring(0,i),n.objectName=r)}if(n.propertyName===null||n.propertyName.length===0)throw new Error("PropertyBinding: can not parse propertyName from trackName: "+e);return n}static findNode(e,t){if(t===void 0||t===""||t==="."||t===-1||t===e.name||t===e.uuid)return e;if(e.skeleton){let n=e.skeleton.getBoneByName(t);if(n!==void 0)return n}if(e.children){let n=function(r){for(let a=0;a<r.length;a++){let o=r[a];if(o.name===t||o.uuid===t)return o;let c=n(o.children);if(c)return c}return null},i=n(e.children);if(i)return i}return null}_getValue_unavailable(){}_setValue_unavailable(){}_getValue_direct(e,t){e[t]=this.targetObject[this.propertyName]}_getValue_array(e,t){let n=this.resolvedProperty;for(let i=0,r=n.length;i!==r;++i)e[t++]=n[i]}_getValue_arrayElement(e,t){e[t]=this.resolvedProperty[this.propertyIndex]}_getValue_toArray(e,t){this.resolvedProperty.toArray(e,t)}_setValue_direct(e,t){this.targetObject[this.propertyName]=e[t]}_setValue_direct_setNeedsUpdate(e,t){this.targetObject[this.propertyName]=e[t],this.targetObject.needsUpdate=!0}_setValue_direct_setMatrixWorldNeedsUpdate(e,t){this.targetObject[this.propertyName]=e[t],this.targetObject.matrixWorldNeedsUpdate=!0}_setValue_array(e,t){let n=this.resolvedProperty;for(let i=0,r=n.length;i!==r;++i)n[i]=e[t++]}_setValue_array_setNeedsUpdate(e,t){let n=this.resolvedProperty;for(let i=0,r=n.length;i!==r;++i)n[i]=e[t++];this.targetObject.needsUpdate=!0}_setValue_array_setMatrixWorldNeedsUpdate(e,t){let n=this.resolvedProperty;for(let i=0,r=n.length;i!==r;++i)n[i]=e[t++];this.targetObject.matrixWorldNeedsUpdate=!0}_setValue_arrayElement(e,t){this.resolvedProperty[this.propertyIndex]=e[t]}_setValue_arrayElement_setNeedsUpdate(e,t){this.resolvedProperty[this.propertyIndex]=e[t],this.targetObject.needsUpdate=!0}_setValue_arrayElement_setMatrixWorldNeedsUpdate(e,t){this.resolvedProperty[this.propertyIndex]=e[t],this.targetObject.matrixWorldNeedsUpdate=!0}_setValue_fromArray(e,t){this.resolvedProperty.fromArray(e,t)}_setValue_fromArray_setNeedsUpdate(e,t){this.resolvedProperty.fromArray(e,t),this.targetObject.needsUpdate=!0}_setValue_fromArray_setMatrixWorldNeedsUpdate(e,t){this.resolvedProperty.fromArray(e,t),this.targetObject.matrixWorldNeedsUpdate=!0}_getValue_unbound(e,t){this.bind(),this.getValue(e,t)}_setValue_unbound(e,t){this.bind(),this.setValue(e,t)}bind(){let e=this.node,t=this.parsedPath,n=t.objectName,i=t.propertyName,r=t.propertyIndex;if(e||(e=s.findNode(this.rootNode,t.nodeName),this.node=e),this.getValue=this._getValue_unavailable,this.setValue=this._setValue_unavailable,!e){console.warn("THREE.PropertyBinding: No target node found for track: "+this.path+".");return}if(n){let l=t.objectIndex;switch(n){case"materials":if(!e.material){console.error("THREE.PropertyBinding: Can not bind to material as node does not have a material.",this);return}if(!e.material.materials){console.error("THREE.PropertyBinding: Can not bind to material.materials as node.material does not have a materials array.",this);return}e=e.material.materials;break;case"bones":if(!e.skeleton){console.error("THREE.PropertyBinding: Can not bind to bones as node does not have a skeleton.",this);return}e=e.skeleton.bones;for(let u=0;u<e.length;u++)if(e[u].name===l){l=u;break}break;case"map":if("map"in e){e=e.map;break}if(!e.material){console.error("THREE.PropertyBinding: Can not bind to material as node does not have a material.",this);return}if(!e.material.map){console.error("THREE.PropertyBinding: Can not bind to material.map as node.material does not have a map.",this);return}e=e.material.map;break;default:if(e[n]===void 0){console.error("THREE.PropertyBinding: Can not bind to objectName of node undefined.",this);return}e=e[n]}if(l!==void 0){if(e[l]===void 0){console.error("THREE.PropertyBinding: Trying to bind to objectIndex of objectName, but is undefined.",this,e);return}e=e[l]}}let a=e[i];if(a===void 0){let l=t.nodeName;console.error("THREE.PropertyBinding: Trying to update property for track: "+l+"."+i+" but it wasn't found.",e);return}let o=this.Versioning.None;this.targetObject=e,e.isMaterial===!0?o=this.Versioning.NeedsUpdate:e.isObject3D===!0&&(o=this.Versioning.MatrixWorldNeedsUpdate);let c=this.BindingType.Direct;if(r!==void 0){if(i==="morphTargetInfluences"){if(!e.geometry){console.error("THREE.PropertyBinding: Can not bind to morphTargetInfluences because node does not have a geometry.",this);return}if(!e.geometry.morphAttributes){console.error("THREE.PropertyBinding: Can not bind to morphTargetInfluences because node does not have a geometry.morphAttributes.",this);return}e.morphTargetDictionary[r]!==void 0&&(r=e.morphTargetDictionary[r])}c=this.BindingType.ArrayElement,this.resolvedProperty=a,this.propertyIndex=r}else a.fromArray!==void 0&&a.toArray!==void 0?(c=this.BindingType.HasFromToArray,this.resolvedProperty=a):Array.isArray(a)?(c=this.BindingType.EntireArray,this.resolvedProperty=a):this.propertyName=i;this.getValue=this.GetterByBindingType[c],this.setValue=this.SetterByBindingTypeAndVersioning[c][o]}unbind(){this.node=null,this.getValue=this._getValue_unbound,this.setValue=this._setValue_unbound}};yt.Composite=oh;yt.prototype.BindingType={Direct:0,EntireArray:1,ArrayElement:2,HasFromToArray:3};yt.prototype.Versioning={None:0,NeedsUpdate:1,MatrixWorldNeedsUpdate:2};yt.prototype.GetterByBindingType=[yt.prototype._getValue_direct,yt.prototype._getValue_array,yt.prototype._getValue_arrayElement,yt.prototype._getValue_toArray];yt.prototype.SetterByBindingTypeAndVersioning=[[yt.prototype._setValue_direct,yt.prototype._setValue_direct_setNeedsUpdate,yt.prototype._setValue_direct_setMatrixWorldNeedsUpdate],[yt.prototype._setValue_array,yt.prototype._setValue_array_setNeedsUpdate,yt.prototype._setValue_array_setMatrixWorldNeedsUpdate],[yt.prototype._setValue_arrayElement,yt.prototype._setValue_arrayElement_setNeedsUpdate,yt.prototype._setValue_arrayElement_setMatrixWorldNeedsUpdate],[yt.prototype._setValue_fromArray,yt.prototype._setValue_fromArray_setNeedsUpdate,yt.prototype._setValue_fromArray_setMatrixWorldNeedsUpdate]];var S_=new Float32Array(1);var Gd=new ke,wa=class{constructor(e,t,n=0,i=1/0){this.ray=new Sn(e,t),this.near=n,this.far=i,this.camera=null,this.layers=new Qs,this.params={Mesh:{},Line:{threshold:1},LOD:{},Points:{threshold:1},Sprite:{}}}set(e,t){this.ray.set(e,t)}setFromCamera(e,t){t.isPerspectiveCamera?(this.ray.origin.setFromMatrixPosition(t.matrixWorld),this.ray.direction.set(e.x,e.y,.5).unproject(t).sub(this.ray.origin).normalize(),this.camera=t):t.isOrthographicCamera?(this.ray.origin.set(e.x,e.y,(t.near+t.far)/(t.near-t.far)).unproject(t),this.ray.direction.set(0,0,-1).transformDirection(t.matrixWorld),this.camera=t):console.error("THREE.Raycaster: Unsupported camera type: "+t.type)}setFromXRController(e){return Gd.identity().extractRotation(e.matrixWorld),this.ray.origin.setFromMatrixPosition(e.matrixWorld),this.ray.direction.set(0,0,-1).applyMatrix4(Gd),this}intersectObject(e,t=!0,n=[]){return ch(e,this,n,t),n.sort(Wd),n}intersectObjects(e,t=!0,n=[]){for(let i=0,r=e.length;i<r;i++)ch(e[i],this,n,t);return n.sort(Wd),n}};function Wd(s,e){return s.distance-e.distance}function ch(s,e,t,n){let i=!0;if(s.layers.test(e.layers)&&s.raycast(e,t)===!1&&(i=!1),i===!0&&n===!0){let r=s.children;for(let a=0,o=r.length;a<o;a++)ch(r[a],e,t,!0)}}var Yd=new L,_o=new L,Ys=new L,Xs=new L,Zl=new L,Bg=new L,Og=new L,Zt=class{constructor(e=new L,t=new L){this.start=e,this.end=t}set(e,t){return this.start.copy(e),this.end.copy(t),this}copy(e){return this.start.copy(e.start),this.end.copy(e.end),this}getCenter(e){return e.addVectors(this.start,this.end).multiplyScalar(.5)}delta(e){return e.subVectors(this.end,this.start)}distanceSq(){return this.start.distanceToSquared(this.end)}distance(){return this.start.distanceTo(this.end)}at(e,t){return this.delta(t).multiplyScalar(e).add(this.start)}closestPointToPointParameter(e,t){Yd.subVectors(e,this.start),_o.subVectors(this.end,this.start);let n=_o.dot(_o),r=_o.dot(Yd)/n;return t&&(r=We(r,0,1)),r}closestPointToPoint(e,t,n){let i=this.closestPointToPointParameter(e,t);return this.delta(n).multiplyScalar(i).add(this.start)}distanceSqToLine3(e,t=Bg,n=Og){let i=10000000000000001e-32,r,a,o=this.start,c=e.start,l=this.end,u=e.end;Ys.subVectors(l,o),Xs.subVectors(u,c),Zl.subVectors(o,c);let h=Ys.dot(Ys),d=Xs.dot(Xs),f=Xs.dot(Zl);if(h<=i&&d<=i)return t.copy(o),n.copy(c),t.sub(n),t.dot(t);if(h<=i)r=0,a=f/d,a=We(a,0,1);else{let g=Ys.dot(Zl);if(d<=i)a=0,r=We(-g/h,0,1);else{let y=Ys.dot(Xs),m=h*d-y*y;m!==0?r=We((y*f-g*d)/m,0,1):r=0,a=(y*r+f)/d,a<0?(a=0,r=We(-g/h,0,1)):a>1&&(a=1,r=We((y-g)/h,0,1))}}return t.copy(o).add(Ys.multiplyScalar(r)),n.copy(c).add(Xs.multiplyScalar(a)),t.sub(n),t.dot(t)}applyMatrix4(e){return this.start.applyMatrix4(e),this.end.applyMatrix4(e),this}equals(e){return e.start.equals(this.start)&&e.end.equals(this.end)}clone(){return new this.constructor().copy(this)}};function Rh(s,e,t,n){let i=zg(n);switch(t){case bh:return s*e;case pr:return s*e/i.components*i.byteLength;case sc:return s*e/i.components*i.byteLength;case xh:return s*e*2/i.components*i.byteLength;case rc:return s*e*2/i.components*i.byteLength;case yh:return s*e*3/i.components*i.byteLength;case Tn:return s*e*4/i.components*i.byteLength;case ac:return s*e*4/i.components*i.byteLength;case Ta:case Ea:return Math.floor((s+3)/4)*Math.floor((e+3)/4)*8;case Aa:case Ra:return Math.floor((s+3)/4)*Math.floor((e+3)/4)*16;case cc:case hc:return Math.max(s,16)*Math.max(e,8)/4;case oc:case lc:return Math.max(s,8)*Math.max(e,8)/2;case uc:case dc:return Math.floor((s+3)/4)*Math.floor((e+3)/4)*8;case fc:return Math.floor((s+3)/4)*Math.floor((e+3)/4)*16;case pc:return Math.floor((s+3)/4)*Math.floor((e+3)/4)*16;case mc:return Math.floor((s+4)/5)*Math.floor((e+3)/4)*16;case gc:return Math.floor((s+4)/5)*Math.floor((e+4)/5)*16;case bc:return Math.floor((s+5)/6)*Math.floor((e+4)/5)*16;case yc:return Math.floor((s+5)/6)*Math.floor((e+5)/6)*16;case xc:return Math.floor((s+7)/8)*Math.floor((e+4)/5)*16;case vc:return Math.floor((s+7)/8)*Math.floor((e+5)/6)*16;case _c:return Math.floor((s+7)/8)*Math.floor((e+7)/8)*16;case wc:return Math.floor((s+9)/10)*Math.floor((e+4)/5)*16;case Mc:return Math.floor((s+9)/10)*Math.floor((e+5)/6)*16;case Sc:return Math.floor((s+9)/10)*Math.floor((e+7)/8)*16;case Tc:return Math.floor((s+9)/10)*Math.floor((e+9)/10)*16;case Ec:return Math.floor((s+11)/12)*Math.floor((e+9)/10)*16;case Ac:return Math.floor((s+11)/12)*Math.floor((e+11)/12)*16;case Rc:case Cc:case Ic:return Math.ceil(s/4)*Math.ceil(e/4)*16;case Pc:case kc:return Math.ceil(s/4)*Math.ceil(e/4)*8;case Lc:case Dc:return Math.ceil(s/4)*Math.ceil(e/4)*16}throw new Error(`Unable to determine texture byte length for ${t} format.`)}function zg(s){switch(s){case jn:case fh:return{byteLength:1,components:1};case ur:case ph:case zi:return{byteLength:2,components:1};case nc:case ic:return{byteLength:2,components:4};case Oi:case tc:case Fn:return{byteLength:4,components:1};case mh:case gh:return{byteLength:4,components:3}}throw new Error(`Unknown texture type ${s}.`)}typeof __THREE_DEVTOOLS__<"u"&&__THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("register",{detail:{revision:"180"}}));typeof window<"u"&&(window.__THREE__?console.warn("WARNING: Multiple instances of Three.js being imported."):window.__THREE__="180");function op(){let s=null,e=!1,t=null,n=null;function i(r,a){t(r,a),n=s.requestAnimationFrame(i)}return{start:function(){e!==!0&&t!==null&&(n=s.requestAnimationFrame(i),e=!0)},stop:function(){s.cancelAnimationFrame(n),e=!1},setAnimationLoop:function(r){t=r},setContext:function(r){s=r}}}function Hg(s){let e=new WeakMap;function t(o,c){let l=o.array,u=o.usage,h=l.byteLength,d=s.createBuffer();s.bindBuffer(c,d),s.bufferData(c,l,u),o.onUploadCallback();let f;if(l instanceof Float32Array)f=s.FLOAT;else if(typeof Float16Array<"u"&&l instanceof Float16Array)f=s.HALF_FLOAT;else if(l instanceof Uint16Array)o.isFloat16BufferAttribute?f=s.HALF_FLOAT:f=s.UNSIGNED_SHORT;else if(l instanceof Int16Array)f=s.SHORT;else if(l instanceof Uint32Array)f=s.UNSIGNED_INT;else if(l instanceof Int32Array)f=s.INT;else if(l instanceof Int8Array)f=s.BYTE;else if(l instanceof Uint8Array)f=s.UNSIGNED_BYTE;else if(l instanceof Uint8ClampedArray)f=s.UNSIGNED_BYTE;else throw new Error("THREE.WebGLAttributes: Unsupported buffer data format: "+l);return{buffer:d,type:f,bytesPerElement:l.BYTES_PER_ELEMENT,version:o.version,size:h}}function n(o,c,l){let u=c.array,h=c.updateRanges;if(s.bindBuffer(l,o),h.length===0)s.bufferSubData(l,0,u);else{h.sort((f,g)=>f.start-g.start);let d=0;for(let f=1;f<h.length;f++){let g=h[d],y=h[f];y.start<=g.start+g.count+1?g.count=Math.max(g.count,y.start+y.count-g.start):(++d,h[d]=y)}h.length=d+1;for(let f=0,g=h.length;f<g;f++){let y=h[f];s.bufferSubData(l,y.start*u.BYTES_PER_ELEMENT,u,y.start,y.count)}c.clearUpdateRanges()}c.onUploadCallback()}function i(o){return o.isInterleavedBufferAttribute&&(o=o.data),e.get(o)}function r(o){o.isInterleavedBufferAttribute&&(o=o.data);let c=e.get(o);c&&(s.deleteBuffer(c.buffer),e.delete(o))}function a(o,c){if(o.isInterleavedBufferAttribute&&(o=o.data),o.isGLBufferAttribute){let u=e.get(o);(!u||u.version<o.version)&&e.set(o,{buffer:o.buffer,type:o.type,bytesPerElement:o.elementSize,version:o.version});return}let l=e.get(o);if(l===void 0)e.set(o,t(o,c));else if(l.version<o.version){if(l.size!==o.array.byteLength)throw new Error("THREE.WebGLAttributes: The size of the buffer attribute's array buffer does not match the original size. Resizing buffer attributes is not supported.");n(l.buffer,o,c),l.version=o.version}}return{get:i,remove:r,update:a}}var Vg=`#ifdef USE_ALPHAHASH
	if ( diffuseColor.a < getAlphaHashThreshold( vPosition ) ) discard;
#endif`,Gg=`#ifdef USE_ALPHAHASH
	const float ALPHA_HASH_SCALE = 0.05;
	float hash2D( vec2 value ) {
		return fract( 1.0e4 * sin( 17.0 * value.x + 0.1 * value.y ) * ( 0.1 + abs( sin( 13.0 * value.y + value.x ) ) ) );
	}
	float hash3D( vec3 value ) {
		return hash2D( vec2( hash2D( value.xy ), value.z ) );
	}
	float getAlphaHashThreshold( vec3 position ) {
		float maxDeriv = max(
			length( dFdx( position.xyz ) ),
			length( dFdy( position.xyz ) )
		);
		float pixScale = 1.0 / ( ALPHA_HASH_SCALE * maxDeriv );
		vec2 pixScales = vec2(
			exp2( floor( log2( pixScale ) ) ),
			exp2( ceil( log2( pixScale ) ) )
		);
		vec2 alpha = vec2(
			hash3D( floor( pixScales.x * position.xyz ) ),
			hash3D( floor( pixScales.y * position.xyz ) )
		);
		float lerpFactor = fract( log2( pixScale ) );
		float x = ( 1.0 - lerpFactor ) * alpha.x + lerpFactor * alpha.y;
		float a = min( lerpFactor, 1.0 - lerpFactor );
		vec3 cases = vec3(
			x * x / ( 2.0 * a * ( 1.0 - a ) ),
			( x - 0.5 * a ) / ( 1.0 - a ),
			1.0 - ( ( 1.0 - x ) * ( 1.0 - x ) / ( 2.0 * a * ( 1.0 - a ) ) )
		);
		float threshold = ( x < ( 1.0 - a ) )
			? ( ( x < a ) ? cases.x : cases.y )
			: cases.z;
		return clamp( threshold , 1.0e-6, 1.0 );
	}
#endif`,Wg=`#ifdef USE_ALPHAMAP
	diffuseColor.a *= texture2D( alphaMap, vAlphaMapUv ).g;
#endif`,Yg=`#ifdef USE_ALPHAMAP
	uniform sampler2D alphaMap;
#endif`,Xg=`#ifdef USE_ALPHATEST
	#ifdef ALPHA_TO_COVERAGE
	diffuseColor.a = smoothstep( alphaTest, alphaTest + fwidth( diffuseColor.a ), diffuseColor.a );
	if ( diffuseColor.a == 0.0 ) discard;
	#else
	if ( diffuseColor.a < alphaTest ) discard;
	#endif
#endif`,qg=`#ifdef USE_ALPHATEST
	uniform float alphaTest;
#endif`,jg=`#ifdef USE_AOMAP
	float ambientOcclusion = ( texture2D( aoMap, vAoMapUv ).r - 1.0 ) * aoMapIntensity + 1.0;
	reflectedLight.indirectDiffuse *= ambientOcclusion;
	#if defined( USE_CLEARCOAT ) 
		clearcoatSpecularIndirect *= ambientOcclusion;
	#endif
	#if defined( USE_SHEEN ) 
		sheenSpecularIndirect *= ambientOcclusion;
	#endif
	#if defined( USE_ENVMAP ) && defined( STANDARD )
		float dotNV = saturate( dot( geometryNormal, geometryViewDir ) );
		reflectedLight.indirectSpecular *= computeSpecularOcclusion( dotNV, ambientOcclusion, material.roughness );
	#endif
#endif`,Kg=`#ifdef USE_AOMAP
	uniform sampler2D aoMap;
	uniform float aoMapIntensity;
#endif`,Zg=`#ifdef USE_BATCHING
	#if ! defined( GL_ANGLE_multi_draw )
	#define gl_DrawID _gl_DrawID
	uniform int _gl_DrawID;
	#endif
	uniform highp sampler2D batchingTexture;
	uniform highp usampler2D batchingIdTexture;
	mat4 getBatchingMatrix( const in float i ) {
		int size = textureSize( batchingTexture, 0 ).x;
		int j = int( i ) * 4;
		int x = j % size;
		int y = j / size;
		vec4 v1 = texelFetch( batchingTexture, ivec2( x, y ), 0 );
		vec4 v2 = texelFetch( batchingTexture, ivec2( x + 1, y ), 0 );
		vec4 v3 = texelFetch( batchingTexture, ivec2( x + 2, y ), 0 );
		vec4 v4 = texelFetch( batchingTexture, ivec2( x + 3, y ), 0 );
		return mat4( v1, v2, v3, v4 );
	}
	float getIndirectIndex( const in int i ) {
		int size = textureSize( batchingIdTexture, 0 ).x;
		int x = i % size;
		int y = i / size;
		return float( texelFetch( batchingIdTexture, ivec2( x, y ), 0 ).r );
	}
#endif
#ifdef USE_BATCHING_COLOR
	uniform sampler2D batchingColorTexture;
	vec3 getBatchingColor( const in float i ) {
		int size = textureSize( batchingColorTexture, 0 ).x;
		int j = int( i );
		int x = j % size;
		int y = j / size;
		return texelFetch( batchingColorTexture, ivec2( x, y ), 0 ).rgb;
	}
#endif`,Jg=`#ifdef USE_BATCHING
	mat4 batchingMatrix = getBatchingMatrix( getIndirectIndex( gl_DrawID ) );
#endif`,$g=`vec3 transformed = vec3( position );
#ifdef USE_ALPHAHASH
	vPosition = vec3( position );
#endif`,Qg=`vec3 objectNormal = vec3( normal );
#ifdef USE_TANGENT
	vec3 objectTangent = vec3( tangent.xyz );
#endif`,e0=`float G_BlinnPhong_Implicit( ) {
	return 0.25;
}
float D_BlinnPhong( const in float shininess, const in float dotNH ) {
	return RECIPROCAL_PI * ( shininess * 0.5 + 1.0 ) * pow( dotNH, shininess );
}
vec3 BRDF_BlinnPhong( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in vec3 specularColor, const in float shininess ) {
	vec3 halfDir = normalize( lightDir + viewDir );
	float dotNH = saturate( dot( normal, halfDir ) );
	float dotVH = saturate( dot( viewDir, halfDir ) );
	vec3 F = F_Schlick( specularColor, 1.0, dotVH );
	float G = G_BlinnPhong_Implicit( );
	float D = D_BlinnPhong( shininess, dotNH );
	return F * ( G * D );
} // validated`,t0=`#ifdef USE_IRIDESCENCE
	const mat3 XYZ_TO_REC709 = mat3(
		 3.2404542, -0.9692660,  0.0556434,
		-1.5371385,  1.8760108, -0.2040259,
		-0.4985314,  0.0415560,  1.0572252
	);
	vec3 Fresnel0ToIor( vec3 fresnel0 ) {
		vec3 sqrtF0 = sqrt( fresnel0 );
		return ( vec3( 1.0 ) + sqrtF0 ) / ( vec3( 1.0 ) - sqrtF0 );
	}
	vec3 IorToFresnel0( vec3 transmittedIor, float incidentIor ) {
		return pow2( ( transmittedIor - vec3( incidentIor ) ) / ( transmittedIor + vec3( incidentIor ) ) );
	}
	float IorToFresnel0( float transmittedIor, float incidentIor ) {
		return pow2( ( transmittedIor - incidentIor ) / ( transmittedIor + incidentIor ));
	}
	vec3 evalSensitivity( float OPD, vec3 shift ) {
		float phase = 2.0 * PI * OPD * 1.0e-9;
		vec3 val = vec3( 5.4856e-13, 4.4201e-13, 5.2481e-13 );
		vec3 pos = vec3( 1.6810e+06, 1.7953e+06, 2.2084e+06 );
		vec3 var = vec3( 4.3278e+09, 9.3046e+09, 6.6121e+09 );
		vec3 xyz = val * sqrt( 2.0 * PI * var ) * cos( pos * phase + shift ) * exp( - pow2( phase ) * var );
		xyz.x += 9.7470e-14 * sqrt( 2.0 * PI * 4.5282e+09 ) * cos( 2.2399e+06 * phase + shift[ 0 ] ) * exp( - 4.5282e+09 * pow2( phase ) );
		xyz /= 1.0685e-7;
		vec3 rgb = XYZ_TO_REC709 * xyz;
		return rgb;
	}
	vec3 evalIridescence( float outsideIOR, float eta2, float cosTheta1, float thinFilmThickness, vec3 baseF0 ) {
		vec3 I;
		float iridescenceIOR = mix( outsideIOR, eta2, smoothstep( 0.0, 0.03, thinFilmThickness ) );
		float sinTheta2Sq = pow2( outsideIOR / iridescenceIOR ) * ( 1.0 - pow2( cosTheta1 ) );
		float cosTheta2Sq = 1.0 - sinTheta2Sq;
		if ( cosTheta2Sq < 0.0 ) {
			return vec3( 1.0 );
		}
		float cosTheta2 = sqrt( cosTheta2Sq );
		float R0 = IorToFresnel0( iridescenceIOR, outsideIOR );
		float R12 = F_Schlick( R0, 1.0, cosTheta1 );
		float T121 = 1.0 - R12;
		float phi12 = 0.0;
		if ( iridescenceIOR < outsideIOR ) phi12 = PI;
		float phi21 = PI - phi12;
		vec3 baseIOR = Fresnel0ToIor( clamp( baseF0, 0.0, 0.9999 ) );		vec3 R1 = IorToFresnel0( baseIOR, iridescenceIOR );
		vec3 R23 = F_Schlick( R1, 1.0, cosTheta2 );
		vec3 phi23 = vec3( 0.0 );
		if ( baseIOR[ 0 ] < iridescenceIOR ) phi23[ 0 ] = PI;
		if ( baseIOR[ 1 ] < iridescenceIOR ) phi23[ 1 ] = PI;
		if ( baseIOR[ 2 ] < iridescenceIOR ) phi23[ 2 ] = PI;
		float OPD = 2.0 * iridescenceIOR * thinFilmThickness * cosTheta2;
		vec3 phi = vec3( phi21 ) + phi23;
		vec3 R123 = clamp( R12 * R23, 1e-5, 0.9999 );
		vec3 r123 = sqrt( R123 );
		vec3 Rs = pow2( T121 ) * R23 / ( vec3( 1.0 ) - R123 );
		vec3 C0 = R12 + Rs;
		I = C0;
		vec3 Cm = Rs - T121;
		for ( int m = 1; m <= 2; ++ m ) {
			Cm *= r123;
			vec3 Sm = 2.0 * evalSensitivity( float( m ) * OPD, float( m ) * phi );
			I += Cm * Sm;
		}
		return max( I, vec3( 0.0 ) );
	}
#endif`,n0=`#ifdef USE_BUMPMAP
	uniform sampler2D bumpMap;
	uniform float bumpScale;
	vec2 dHdxy_fwd() {
		vec2 dSTdx = dFdx( vBumpMapUv );
		vec2 dSTdy = dFdy( vBumpMapUv );
		float Hll = bumpScale * texture2D( bumpMap, vBumpMapUv ).x;
		float dBx = bumpScale * texture2D( bumpMap, vBumpMapUv + dSTdx ).x - Hll;
		float dBy = bumpScale * texture2D( bumpMap, vBumpMapUv + dSTdy ).x - Hll;
		return vec2( dBx, dBy );
	}
	vec3 perturbNormalArb( vec3 surf_pos, vec3 surf_norm, vec2 dHdxy, float faceDirection ) {
		vec3 vSigmaX = normalize( dFdx( surf_pos.xyz ) );
		vec3 vSigmaY = normalize( dFdy( surf_pos.xyz ) );
		vec3 vN = surf_norm;
		vec3 R1 = cross( vSigmaY, vN );
		vec3 R2 = cross( vN, vSigmaX );
		float fDet = dot( vSigmaX, R1 ) * faceDirection;
		vec3 vGrad = sign( fDet ) * ( dHdxy.x * R1 + dHdxy.y * R2 );
		return normalize( abs( fDet ) * surf_norm - vGrad );
	}
#endif`,i0=`#if NUM_CLIPPING_PLANES > 0
	vec4 plane;
	#ifdef ALPHA_TO_COVERAGE
		float distanceToPlane, distanceGradient;
		float clipOpacity = 1.0;
		#pragma unroll_loop_start
		for ( int i = 0; i < UNION_CLIPPING_PLANES; i ++ ) {
			plane = clippingPlanes[ i ];
			distanceToPlane = - dot( vClipPosition, plane.xyz ) + plane.w;
			distanceGradient = fwidth( distanceToPlane ) / 2.0;
			clipOpacity *= smoothstep( - distanceGradient, distanceGradient, distanceToPlane );
			if ( clipOpacity == 0.0 ) discard;
		}
		#pragma unroll_loop_end
		#if UNION_CLIPPING_PLANES < NUM_CLIPPING_PLANES
			float unionClipOpacity = 1.0;
			#pragma unroll_loop_start
			for ( int i = UNION_CLIPPING_PLANES; i < NUM_CLIPPING_PLANES; i ++ ) {
				plane = clippingPlanes[ i ];
				distanceToPlane = - dot( vClipPosition, plane.xyz ) + plane.w;
				distanceGradient = fwidth( distanceToPlane ) / 2.0;
				unionClipOpacity *= 1.0 - smoothstep( - distanceGradient, distanceGradient, distanceToPlane );
			}
			#pragma unroll_loop_end
			clipOpacity *= 1.0 - unionClipOpacity;
		#endif
		diffuseColor.a *= clipOpacity;
		if ( diffuseColor.a == 0.0 ) discard;
	#else
		#pragma unroll_loop_start
		for ( int i = 0; i < UNION_CLIPPING_PLANES; i ++ ) {
			plane = clippingPlanes[ i ];
			if ( dot( vClipPosition, plane.xyz ) > plane.w ) discard;
		}
		#pragma unroll_loop_end
		#if UNION_CLIPPING_PLANES < NUM_CLIPPING_PLANES
			bool clipped = true;
			#pragma unroll_loop_start
			for ( int i = UNION_CLIPPING_PLANES; i < NUM_CLIPPING_PLANES; i ++ ) {
				plane = clippingPlanes[ i ];
				clipped = ( dot( vClipPosition, plane.xyz ) > plane.w ) && clipped;
			}
			#pragma unroll_loop_end
			if ( clipped ) discard;
		#endif
	#endif
#endif`,s0=`#if NUM_CLIPPING_PLANES > 0
	varying vec3 vClipPosition;
	uniform vec4 clippingPlanes[ NUM_CLIPPING_PLANES ];
#endif`,r0=`#if NUM_CLIPPING_PLANES > 0
	varying vec3 vClipPosition;
#endif`,a0=`#if NUM_CLIPPING_PLANES > 0
	vClipPosition = - mvPosition.xyz;
#endif`,o0=`#if defined( USE_COLOR_ALPHA )
	diffuseColor *= vColor;
#elif defined( USE_COLOR )
	diffuseColor.rgb *= vColor;
#endif`,c0=`#if defined( USE_COLOR_ALPHA )
	varying vec4 vColor;
#elif defined( USE_COLOR )
	varying vec3 vColor;
#endif`,l0=`#if defined( USE_COLOR_ALPHA )
	varying vec4 vColor;
#elif defined( USE_COLOR ) || defined( USE_INSTANCING_COLOR ) || defined( USE_BATCHING_COLOR )
	varying vec3 vColor;
#endif`,h0=`#if defined( USE_COLOR_ALPHA )
	vColor = vec4( 1.0 );
#elif defined( USE_COLOR ) || defined( USE_INSTANCING_COLOR ) || defined( USE_BATCHING_COLOR )
	vColor = vec3( 1.0 );
#endif
#ifdef USE_COLOR
	vColor *= color;
#endif
#ifdef USE_INSTANCING_COLOR
	vColor.xyz *= instanceColor.xyz;
#endif
#ifdef USE_BATCHING_COLOR
	vec3 batchingColor = getBatchingColor( getIndirectIndex( gl_DrawID ) );
	vColor.xyz *= batchingColor.xyz;
#endif`,u0=`#define PI 3.141592653589793
#define PI2 6.283185307179586
#define PI_HALF 1.5707963267948966
#define RECIPROCAL_PI 0.3183098861837907
#define RECIPROCAL_PI2 0.15915494309189535
#define EPSILON 1e-6
#ifndef saturate
#define saturate( a ) clamp( a, 0.0, 1.0 )
#endif
#define whiteComplement( a ) ( 1.0 - saturate( a ) )
float pow2( const in float x ) { return x*x; }
vec3 pow2( const in vec3 x ) { return x*x; }
float pow3( const in float x ) { return x*x*x; }
float pow4( const in float x ) { float x2 = x*x; return x2*x2; }
float max3( const in vec3 v ) { return max( max( v.x, v.y ), v.z ); }
float average( const in vec3 v ) { return dot( v, vec3( 0.3333333 ) ); }
highp float rand( const in vec2 uv ) {
	const highp float a = 12.9898, b = 78.233, c = 43758.5453;
	highp float dt = dot( uv.xy, vec2( a,b ) ), sn = mod( dt, PI );
	return fract( sin( sn ) * c );
}
#ifdef HIGH_PRECISION
	float precisionSafeLength( vec3 v ) { return length( v ); }
#else
	float precisionSafeLength( vec3 v ) {
		float maxComponent = max3( abs( v ) );
		return length( v / maxComponent ) * maxComponent;
	}
#endif
struct IncidentLight {
	vec3 color;
	vec3 direction;
	bool visible;
};
struct ReflectedLight {
	vec3 directDiffuse;
	vec3 directSpecular;
	vec3 indirectDiffuse;
	vec3 indirectSpecular;
};
#ifdef USE_ALPHAHASH
	varying vec3 vPosition;
#endif
vec3 transformDirection( in vec3 dir, in mat4 matrix ) {
	return normalize( ( matrix * vec4( dir, 0.0 ) ).xyz );
}
vec3 inverseTransformDirection( in vec3 dir, in mat4 matrix ) {
	return normalize( ( vec4( dir, 0.0 ) * matrix ).xyz );
}
mat3 transposeMat3( const in mat3 m ) {
	mat3 tmp;
	tmp[ 0 ] = vec3( m[ 0 ].x, m[ 1 ].x, m[ 2 ].x );
	tmp[ 1 ] = vec3( m[ 0 ].y, m[ 1 ].y, m[ 2 ].y );
	tmp[ 2 ] = vec3( m[ 0 ].z, m[ 1 ].z, m[ 2 ].z );
	return tmp;
}
bool isPerspectiveMatrix( mat4 m ) {
	return m[ 2 ][ 3 ] == - 1.0;
}
vec2 equirectUv( in vec3 dir ) {
	float u = atan( dir.z, dir.x ) * RECIPROCAL_PI2 + 0.5;
	float v = asin( clamp( dir.y, - 1.0, 1.0 ) ) * RECIPROCAL_PI + 0.5;
	return vec2( u, v );
}
vec3 BRDF_Lambert( const in vec3 diffuseColor ) {
	return RECIPROCAL_PI * diffuseColor;
}
vec3 F_Schlick( const in vec3 f0, const in float f90, const in float dotVH ) {
	float fresnel = exp2( ( - 5.55473 * dotVH - 6.98316 ) * dotVH );
	return f0 * ( 1.0 - fresnel ) + ( f90 * fresnel );
}
float F_Schlick( const in float f0, const in float f90, const in float dotVH ) {
	float fresnel = exp2( ( - 5.55473 * dotVH - 6.98316 ) * dotVH );
	return f0 * ( 1.0 - fresnel ) + ( f90 * fresnel );
} // validated`,d0=`#ifdef ENVMAP_TYPE_CUBE_UV
	#define cubeUV_minMipLevel 4.0
	#define cubeUV_minTileSize 16.0
	float getFace( vec3 direction ) {
		vec3 absDirection = abs( direction );
		float face = - 1.0;
		if ( absDirection.x > absDirection.z ) {
			if ( absDirection.x > absDirection.y )
				face = direction.x > 0.0 ? 0.0 : 3.0;
			else
				face = direction.y > 0.0 ? 1.0 : 4.0;
		} else {
			if ( absDirection.z > absDirection.y )
				face = direction.z > 0.0 ? 2.0 : 5.0;
			else
				face = direction.y > 0.0 ? 1.0 : 4.0;
		}
		return face;
	}
	vec2 getUV( vec3 direction, float face ) {
		vec2 uv;
		if ( face == 0.0 ) {
			uv = vec2( direction.z, direction.y ) / abs( direction.x );
		} else if ( face == 1.0 ) {
			uv = vec2( - direction.x, - direction.z ) / abs( direction.y );
		} else if ( face == 2.0 ) {
			uv = vec2( - direction.x, direction.y ) / abs( direction.z );
		} else if ( face == 3.0 ) {
			uv = vec2( - direction.z, direction.y ) / abs( direction.x );
		} else if ( face == 4.0 ) {
			uv = vec2( - direction.x, direction.z ) / abs( direction.y );
		} else {
			uv = vec2( direction.x, direction.y ) / abs( direction.z );
		}
		return 0.5 * ( uv + 1.0 );
	}
	vec3 bilinearCubeUV( sampler2D envMap, vec3 direction, float mipInt ) {
		float face = getFace( direction );
		float filterInt = max( cubeUV_minMipLevel - mipInt, 0.0 );
		mipInt = max( mipInt, cubeUV_minMipLevel );
		float faceSize = exp2( mipInt );
		highp vec2 uv = getUV( direction, face ) * ( faceSize - 2.0 ) + 1.0;
		if ( face > 2.0 ) {
			uv.y += faceSize;
			face -= 3.0;
		}
		uv.x += face * faceSize;
		uv.x += filterInt * 3.0 * cubeUV_minTileSize;
		uv.y += 4.0 * ( exp2( CUBEUV_MAX_MIP ) - faceSize );
		uv.x *= CUBEUV_TEXEL_WIDTH;
		uv.y *= CUBEUV_TEXEL_HEIGHT;
		#ifdef texture2DGradEXT
			return texture2DGradEXT( envMap, uv, vec2( 0.0 ), vec2( 0.0 ) ).rgb;
		#else
			return texture2D( envMap, uv ).rgb;
		#endif
	}
	#define cubeUV_r0 1.0
	#define cubeUV_m0 - 2.0
	#define cubeUV_r1 0.8
	#define cubeUV_m1 - 1.0
	#define cubeUV_r4 0.4
	#define cubeUV_m4 2.0
	#define cubeUV_r5 0.305
	#define cubeUV_m5 3.0
	#define cubeUV_r6 0.21
	#define cubeUV_m6 4.0
	float roughnessToMip( float roughness ) {
		float mip = 0.0;
		if ( roughness >= cubeUV_r1 ) {
			mip = ( cubeUV_r0 - roughness ) * ( cubeUV_m1 - cubeUV_m0 ) / ( cubeUV_r0 - cubeUV_r1 ) + cubeUV_m0;
		} else if ( roughness >= cubeUV_r4 ) {
			mip = ( cubeUV_r1 - roughness ) * ( cubeUV_m4 - cubeUV_m1 ) / ( cubeUV_r1 - cubeUV_r4 ) + cubeUV_m1;
		} else if ( roughness >= cubeUV_r5 ) {
			mip = ( cubeUV_r4 - roughness ) * ( cubeUV_m5 - cubeUV_m4 ) / ( cubeUV_r4 - cubeUV_r5 ) + cubeUV_m4;
		} else if ( roughness >= cubeUV_r6 ) {
			mip = ( cubeUV_r5 - roughness ) * ( cubeUV_m6 - cubeUV_m5 ) / ( cubeUV_r5 - cubeUV_r6 ) + cubeUV_m5;
		} else {
			mip = - 2.0 * log2( 1.16 * roughness );		}
		return mip;
	}
	vec4 textureCubeUV( sampler2D envMap, vec3 sampleDir, float roughness ) {
		float mip = clamp( roughnessToMip( roughness ), cubeUV_m0, CUBEUV_MAX_MIP );
		float mipF = fract( mip );
		float mipInt = floor( mip );
		vec3 color0 = bilinearCubeUV( envMap, sampleDir, mipInt );
		if ( mipF == 0.0 ) {
			return vec4( color0, 1.0 );
		} else {
			vec3 color1 = bilinearCubeUV( envMap, sampleDir, mipInt + 1.0 );
			return vec4( mix( color0, color1, mipF ), 1.0 );
		}
	}
#endif`,f0=`vec3 transformedNormal = objectNormal;
#ifdef USE_TANGENT
	vec3 transformedTangent = objectTangent;
#endif
#ifdef USE_BATCHING
	mat3 bm = mat3( batchingMatrix );
	transformedNormal /= vec3( dot( bm[ 0 ], bm[ 0 ] ), dot( bm[ 1 ], bm[ 1 ] ), dot( bm[ 2 ], bm[ 2 ] ) );
	transformedNormal = bm * transformedNormal;
	#ifdef USE_TANGENT
		transformedTangent = bm * transformedTangent;
	#endif
#endif
#ifdef USE_INSTANCING
	mat3 im = mat3( instanceMatrix );
	transformedNormal /= vec3( dot( im[ 0 ], im[ 0 ] ), dot( im[ 1 ], im[ 1 ] ), dot( im[ 2 ], im[ 2 ] ) );
	transformedNormal = im * transformedNormal;
	#ifdef USE_TANGENT
		transformedTangent = im * transformedTangent;
	#endif
#endif
transformedNormal = normalMatrix * transformedNormal;
#ifdef FLIP_SIDED
	transformedNormal = - transformedNormal;
#endif
#ifdef USE_TANGENT
	transformedTangent = ( modelViewMatrix * vec4( transformedTangent, 0.0 ) ).xyz;
	#ifdef FLIP_SIDED
		transformedTangent = - transformedTangent;
	#endif
#endif`,p0=`#ifdef USE_DISPLACEMENTMAP
	uniform sampler2D displacementMap;
	uniform float displacementScale;
	uniform float displacementBias;
#endif`,m0=`#ifdef USE_DISPLACEMENTMAP
	transformed += normalize( objectNormal ) * ( texture2D( displacementMap, vDisplacementMapUv ).x * displacementScale + displacementBias );
#endif`,g0=`#ifdef USE_EMISSIVEMAP
	vec4 emissiveColor = texture2D( emissiveMap, vEmissiveMapUv );
	#ifdef DECODE_VIDEO_TEXTURE_EMISSIVE
		emissiveColor = sRGBTransferEOTF( emissiveColor );
	#endif
	totalEmissiveRadiance *= emissiveColor.rgb;
#endif`,b0=`#ifdef USE_EMISSIVEMAP
	uniform sampler2D emissiveMap;
#endif`,y0="gl_FragColor = linearToOutputTexel( gl_FragColor );",x0=`vec4 LinearTransferOETF( in vec4 value ) {
	return value;
}
vec4 sRGBTransferEOTF( in vec4 value ) {
	return vec4( mix( pow( value.rgb * 0.9478672986 + vec3( 0.0521327014 ), vec3( 2.4 ) ), value.rgb * 0.0773993808, vec3( lessThanEqual( value.rgb, vec3( 0.04045 ) ) ) ), value.a );
}
vec4 sRGBTransferOETF( in vec4 value ) {
	return vec4( mix( pow( value.rgb, vec3( 0.41666 ) ) * 1.055 - vec3( 0.055 ), value.rgb * 12.92, vec3( lessThanEqual( value.rgb, vec3( 0.0031308 ) ) ) ), value.a );
}`,v0=`#ifdef USE_ENVMAP
	#ifdef ENV_WORLDPOS
		vec3 cameraToFrag;
		if ( isOrthographic ) {
			cameraToFrag = normalize( vec3( - viewMatrix[ 0 ][ 2 ], - viewMatrix[ 1 ][ 2 ], - viewMatrix[ 2 ][ 2 ] ) );
		} else {
			cameraToFrag = normalize( vWorldPosition - cameraPosition );
		}
		vec3 worldNormal = inverseTransformDirection( normal, viewMatrix );
		#ifdef ENVMAP_MODE_REFLECTION
			vec3 reflectVec = reflect( cameraToFrag, worldNormal );
		#else
			vec3 reflectVec = refract( cameraToFrag, worldNormal, refractionRatio );
		#endif
	#else
		vec3 reflectVec = vReflect;
	#endif
	#ifdef ENVMAP_TYPE_CUBE
		vec4 envColor = textureCube( envMap, envMapRotation * vec3( flipEnvMap * reflectVec.x, reflectVec.yz ) );
	#else
		vec4 envColor = vec4( 0.0 );
	#endif
	#ifdef ENVMAP_BLENDING_MULTIPLY
		outgoingLight = mix( outgoingLight, outgoingLight * envColor.xyz, specularStrength * reflectivity );
	#elif defined( ENVMAP_BLENDING_MIX )
		outgoingLight = mix( outgoingLight, envColor.xyz, specularStrength * reflectivity );
	#elif defined( ENVMAP_BLENDING_ADD )
		outgoingLight += envColor.xyz * specularStrength * reflectivity;
	#endif
#endif`,_0=`#ifdef USE_ENVMAP
	uniform float envMapIntensity;
	uniform float flipEnvMap;
	uniform mat3 envMapRotation;
	#ifdef ENVMAP_TYPE_CUBE
		uniform samplerCube envMap;
	#else
		uniform sampler2D envMap;
	#endif
	
#endif`,w0=`#ifdef USE_ENVMAP
	uniform float reflectivity;
	#if defined( USE_BUMPMAP ) || defined( USE_NORMALMAP ) || defined( PHONG ) || defined( LAMBERT )
		#define ENV_WORLDPOS
	#endif
	#ifdef ENV_WORLDPOS
		varying vec3 vWorldPosition;
		uniform float refractionRatio;
	#else
		varying vec3 vReflect;
	#endif
#endif`,M0=`#ifdef USE_ENVMAP
	#if defined( USE_BUMPMAP ) || defined( USE_NORMALMAP ) || defined( PHONG ) || defined( LAMBERT )
		#define ENV_WORLDPOS
	#endif
	#ifdef ENV_WORLDPOS
		
		varying vec3 vWorldPosition;
	#else
		varying vec3 vReflect;
		uniform float refractionRatio;
	#endif
#endif`,S0=`#ifdef USE_ENVMAP
	#ifdef ENV_WORLDPOS
		vWorldPosition = worldPosition.xyz;
	#else
		vec3 cameraToVertex;
		if ( isOrthographic ) {
			cameraToVertex = normalize( vec3( - viewMatrix[ 0 ][ 2 ], - viewMatrix[ 1 ][ 2 ], - viewMatrix[ 2 ][ 2 ] ) );
		} else {
			cameraToVertex = normalize( worldPosition.xyz - cameraPosition );
		}
		vec3 worldNormal = inverseTransformDirection( transformedNormal, viewMatrix );
		#ifdef ENVMAP_MODE_REFLECTION
			vReflect = reflect( cameraToVertex, worldNormal );
		#else
			vReflect = refract( cameraToVertex, worldNormal, refractionRatio );
		#endif
	#endif
#endif`,T0=`#ifdef USE_FOG
	vFogDepth = - mvPosition.z;
#endif`,E0=`#ifdef USE_FOG
	varying float vFogDepth;
#endif`,A0=`#ifdef USE_FOG
	#ifdef FOG_EXP2
		float fogFactor = 1.0 - exp( - fogDensity * fogDensity * vFogDepth * vFogDepth );
	#else
		float fogFactor = smoothstep( fogNear, fogFar, vFogDepth );
	#endif
	gl_FragColor.rgb = mix( gl_FragColor.rgb, fogColor, fogFactor );
#endif`,R0=`#ifdef USE_FOG
	uniform vec3 fogColor;
	varying float vFogDepth;
	#ifdef FOG_EXP2
		uniform float fogDensity;
	#else
		uniform float fogNear;
		uniform float fogFar;
	#endif
#endif`,C0=`#ifdef USE_GRADIENTMAP
	uniform sampler2D gradientMap;
#endif
vec3 getGradientIrradiance( vec3 normal, vec3 lightDirection ) {
	float dotNL = dot( normal, lightDirection );
	vec2 coord = vec2( dotNL * 0.5 + 0.5, 0.0 );
	#ifdef USE_GRADIENTMAP
		return vec3( texture2D( gradientMap, coord ).r );
	#else
		vec2 fw = fwidth( coord ) * 0.5;
		return mix( vec3( 0.7 ), vec3( 1.0 ), smoothstep( 0.7 - fw.x, 0.7 + fw.x, coord.x ) );
	#endif
}`,I0=`#ifdef USE_LIGHTMAP
	uniform sampler2D lightMap;
	uniform float lightMapIntensity;
#endif`,P0=`LambertMaterial material;
material.diffuseColor = diffuseColor.rgb;
material.specularStrength = specularStrength;`,k0=`varying vec3 vViewPosition;
struct LambertMaterial {
	vec3 diffuseColor;
	float specularStrength;
};
void RE_Direct_Lambert( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in LambertMaterial material, inout ReflectedLight reflectedLight ) {
	float dotNL = saturate( dot( geometryNormal, directLight.direction ) );
	vec3 irradiance = dotNL * directLight.color;
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
void RE_IndirectDiffuse_Lambert( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in LambertMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
#define RE_Direct				RE_Direct_Lambert
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Lambert`,L0=`uniform bool receiveShadow;
uniform vec3 ambientLightColor;
#if defined( USE_LIGHT_PROBES )
	uniform vec3 lightProbe[ 9 ];
#endif
vec3 shGetIrradianceAt( in vec3 normal, in vec3 shCoefficients[ 9 ] ) {
	float x = normal.x, y = normal.y, z = normal.z;
	vec3 result = shCoefficients[ 0 ] * 0.886227;
	result += shCoefficients[ 1 ] * 2.0 * 0.511664 * y;
	result += shCoefficients[ 2 ] * 2.0 * 0.511664 * z;
	result += shCoefficients[ 3 ] * 2.0 * 0.511664 * x;
	result += shCoefficients[ 4 ] * 2.0 * 0.429043 * x * y;
	result += shCoefficients[ 5 ] * 2.0 * 0.429043 * y * z;
	result += shCoefficients[ 6 ] * ( 0.743125 * z * z - 0.247708 );
	result += shCoefficients[ 7 ] * 2.0 * 0.429043 * x * z;
	result += shCoefficients[ 8 ] * 0.429043 * ( x * x - y * y );
	return result;
}
vec3 getLightProbeIrradiance( const in vec3 lightProbe[ 9 ], const in vec3 normal ) {
	vec3 worldNormal = inverseTransformDirection( normal, viewMatrix );
	vec3 irradiance = shGetIrradianceAt( worldNormal, lightProbe );
	return irradiance;
}
vec3 getAmbientLightIrradiance( const in vec3 ambientLightColor ) {
	vec3 irradiance = ambientLightColor;
	return irradiance;
}
float getDistanceAttenuation( const in float lightDistance, const in float cutoffDistance, const in float decayExponent ) {
	float distanceFalloff = 1.0 / max( pow( lightDistance, decayExponent ), 0.01 );
	if ( cutoffDistance > 0.0 ) {
		distanceFalloff *= pow2( saturate( 1.0 - pow4( lightDistance / cutoffDistance ) ) );
	}
	return distanceFalloff;
}
float getSpotAttenuation( const in float coneCosine, const in float penumbraCosine, const in float angleCosine ) {
	return smoothstep( coneCosine, penumbraCosine, angleCosine );
}
#if NUM_DIR_LIGHTS > 0
	struct DirectionalLight {
		vec3 direction;
		vec3 color;
	};
	uniform DirectionalLight directionalLights[ NUM_DIR_LIGHTS ];
	void getDirectionalLightInfo( const in DirectionalLight directionalLight, out IncidentLight light ) {
		light.color = directionalLight.color;
		light.direction = directionalLight.direction;
		light.visible = true;
	}
#endif
#if NUM_POINT_LIGHTS > 0
	struct PointLight {
		vec3 position;
		vec3 color;
		float distance;
		float decay;
	};
	uniform PointLight pointLights[ NUM_POINT_LIGHTS ];
	void getPointLightInfo( const in PointLight pointLight, const in vec3 geometryPosition, out IncidentLight light ) {
		vec3 lVector = pointLight.position - geometryPosition;
		light.direction = normalize( lVector );
		float lightDistance = length( lVector );
		light.color = pointLight.color;
		light.color *= getDistanceAttenuation( lightDistance, pointLight.distance, pointLight.decay );
		light.visible = ( light.color != vec3( 0.0 ) );
	}
#endif
#if NUM_SPOT_LIGHTS > 0
	struct SpotLight {
		vec3 position;
		vec3 direction;
		vec3 color;
		float distance;
		float decay;
		float coneCos;
		float penumbraCos;
	};
	uniform SpotLight spotLights[ NUM_SPOT_LIGHTS ];
	void getSpotLightInfo( const in SpotLight spotLight, const in vec3 geometryPosition, out IncidentLight light ) {
		vec3 lVector = spotLight.position - geometryPosition;
		light.direction = normalize( lVector );
		float angleCos = dot( light.direction, spotLight.direction );
		float spotAttenuation = getSpotAttenuation( spotLight.coneCos, spotLight.penumbraCos, angleCos );
		if ( spotAttenuation > 0.0 ) {
			float lightDistance = length( lVector );
			light.color = spotLight.color * spotAttenuation;
			light.color *= getDistanceAttenuation( lightDistance, spotLight.distance, spotLight.decay );
			light.visible = ( light.color != vec3( 0.0 ) );
		} else {
			light.color = vec3( 0.0 );
			light.visible = false;
		}
	}
#endif
#if NUM_RECT_AREA_LIGHTS > 0
	struct RectAreaLight {
		vec3 color;
		vec3 position;
		vec3 halfWidth;
		vec3 halfHeight;
	};
	uniform sampler2D ltc_1;	uniform sampler2D ltc_2;
	uniform RectAreaLight rectAreaLights[ NUM_RECT_AREA_LIGHTS ];
#endif
#if NUM_HEMI_LIGHTS > 0
	struct HemisphereLight {
		vec3 direction;
		vec3 skyColor;
		vec3 groundColor;
	};
	uniform HemisphereLight hemisphereLights[ NUM_HEMI_LIGHTS ];
	vec3 getHemisphereLightIrradiance( const in HemisphereLight hemiLight, const in vec3 normal ) {
		float dotNL = dot( normal, hemiLight.direction );
		float hemiDiffuseWeight = 0.5 * dotNL + 0.5;
		vec3 irradiance = mix( hemiLight.groundColor, hemiLight.skyColor, hemiDiffuseWeight );
		return irradiance;
	}
#endif`,D0=`#ifdef USE_ENVMAP
	vec3 getIBLIrradiance( const in vec3 normal ) {
		#ifdef ENVMAP_TYPE_CUBE_UV
			vec3 worldNormal = inverseTransformDirection( normal, viewMatrix );
			vec4 envMapColor = textureCubeUV( envMap, envMapRotation * worldNormal, 1.0 );
			return PI * envMapColor.rgb * envMapIntensity;
		#else
			return vec3( 0.0 );
		#endif
	}
	vec3 getIBLRadiance( const in vec3 viewDir, const in vec3 normal, const in float roughness ) {
		#ifdef ENVMAP_TYPE_CUBE_UV
			vec3 reflectVec = reflect( - viewDir, normal );
			reflectVec = normalize( mix( reflectVec, normal, roughness * roughness) );
			reflectVec = inverseTransformDirection( reflectVec, viewMatrix );
			vec4 envMapColor = textureCubeUV( envMap, envMapRotation * reflectVec, roughness );
			return envMapColor.rgb * envMapIntensity;
		#else
			return vec3( 0.0 );
		#endif
	}
	#ifdef USE_ANISOTROPY
		vec3 getIBLAnisotropyRadiance( const in vec3 viewDir, const in vec3 normal, const in float roughness, const in vec3 bitangent, const in float anisotropy ) {
			#ifdef ENVMAP_TYPE_CUBE_UV
				vec3 bentNormal = cross( bitangent, viewDir );
				bentNormal = normalize( cross( bentNormal, bitangent ) );
				bentNormal = normalize( mix( bentNormal, normal, pow2( pow2( 1.0 - anisotropy * ( 1.0 - roughness ) ) ) ) );
				return getIBLRadiance( viewDir, bentNormal, roughness );
			#else
				return vec3( 0.0 );
			#endif
		}
	#endif
#endif`,N0=`ToonMaterial material;
material.diffuseColor = diffuseColor.rgb;`,F0=`varying vec3 vViewPosition;
struct ToonMaterial {
	vec3 diffuseColor;
};
void RE_Direct_Toon( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in ToonMaterial material, inout ReflectedLight reflectedLight ) {
	vec3 irradiance = getGradientIrradiance( geometryNormal, directLight.direction ) * directLight.color;
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
void RE_IndirectDiffuse_Toon( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in ToonMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
#define RE_Direct				RE_Direct_Toon
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Toon`,U0=`BlinnPhongMaterial material;
material.diffuseColor = diffuseColor.rgb;
material.specularColor = specular;
material.specularShininess = shininess;
material.specularStrength = specularStrength;`,B0=`varying vec3 vViewPosition;
struct BlinnPhongMaterial {
	vec3 diffuseColor;
	vec3 specularColor;
	float specularShininess;
	float specularStrength;
};
void RE_Direct_BlinnPhong( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in BlinnPhongMaterial material, inout ReflectedLight reflectedLight ) {
	float dotNL = saturate( dot( geometryNormal, directLight.direction ) );
	vec3 irradiance = dotNL * directLight.color;
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
	reflectedLight.directSpecular += irradiance * BRDF_BlinnPhong( directLight.direction, geometryViewDir, geometryNormal, material.specularColor, material.specularShininess ) * material.specularStrength;
}
void RE_IndirectDiffuse_BlinnPhong( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in BlinnPhongMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
#define RE_Direct				RE_Direct_BlinnPhong
#define RE_IndirectDiffuse		RE_IndirectDiffuse_BlinnPhong`,O0=`PhysicalMaterial material;
material.diffuseColor = diffuseColor.rgb * ( 1.0 - metalnessFactor );
vec3 dxy = max( abs( dFdx( nonPerturbedNormal ) ), abs( dFdy( nonPerturbedNormal ) ) );
float geometryRoughness = max( max( dxy.x, dxy.y ), dxy.z );
material.roughness = max( roughnessFactor, 0.0525 );material.roughness += geometryRoughness;
material.roughness = min( material.roughness, 1.0 );
#ifdef IOR
	material.ior = ior;
	#ifdef USE_SPECULAR
		float specularIntensityFactor = specularIntensity;
		vec3 specularColorFactor = specularColor;
		#ifdef USE_SPECULAR_COLORMAP
			specularColorFactor *= texture2D( specularColorMap, vSpecularColorMapUv ).rgb;
		#endif
		#ifdef USE_SPECULAR_INTENSITYMAP
			specularIntensityFactor *= texture2D( specularIntensityMap, vSpecularIntensityMapUv ).a;
		#endif
		material.specularF90 = mix( specularIntensityFactor, 1.0, metalnessFactor );
	#else
		float specularIntensityFactor = 1.0;
		vec3 specularColorFactor = vec3( 1.0 );
		material.specularF90 = 1.0;
	#endif
	material.specularColor = mix( min( pow2( ( material.ior - 1.0 ) / ( material.ior + 1.0 ) ) * specularColorFactor, vec3( 1.0 ) ) * specularIntensityFactor, diffuseColor.rgb, metalnessFactor );
#else
	material.specularColor = mix( vec3( 0.04 ), diffuseColor.rgb, metalnessFactor );
	material.specularF90 = 1.0;
#endif
#ifdef USE_CLEARCOAT
	material.clearcoat = clearcoat;
	material.clearcoatRoughness = clearcoatRoughness;
	material.clearcoatF0 = vec3( 0.04 );
	material.clearcoatF90 = 1.0;
	#ifdef USE_CLEARCOATMAP
		material.clearcoat *= texture2D( clearcoatMap, vClearcoatMapUv ).x;
	#endif
	#ifdef USE_CLEARCOAT_ROUGHNESSMAP
		material.clearcoatRoughness *= texture2D( clearcoatRoughnessMap, vClearcoatRoughnessMapUv ).y;
	#endif
	material.clearcoat = saturate( material.clearcoat );	material.clearcoatRoughness = max( material.clearcoatRoughness, 0.0525 );
	material.clearcoatRoughness += geometryRoughness;
	material.clearcoatRoughness = min( material.clearcoatRoughness, 1.0 );
#endif
#ifdef USE_DISPERSION
	material.dispersion = dispersion;
#endif
#ifdef USE_IRIDESCENCE
	material.iridescence = iridescence;
	material.iridescenceIOR = iridescenceIOR;
	#ifdef USE_IRIDESCENCEMAP
		material.iridescence *= texture2D( iridescenceMap, vIridescenceMapUv ).r;
	#endif
	#ifdef USE_IRIDESCENCE_THICKNESSMAP
		material.iridescenceThickness = (iridescenceThicknessMaximum - iridescenceThicknessMinimum) * texture2D( iridescenceThicknessMap, vIridescenceThicknessMapUv ).g + iridescenceThicknessMinimum;
	#else
		material.iridescenceThickness = iridescenceThicknessMaximum;
	#endif
#endif
#ifdef USE_SHEEN
	material.sheenColor = sheenColor;
	#ifdef USE_SHEEN_COLORMAP
		material.sheenColor *= texture2D( sheenColorMap, vSheenColorMapUv ).rgb;
	#endif
	material.sheenRoughness = clamp( sheenRoughness, 0.07, 1.0 );
	#ifdef USE_SHEEN_ROUGHNESSMAP
		material.sheenRoughness *= texture2D( sheenRoughnessMap, vSheenRoughnessMapUv ).a;
	#endif
#endif
#ifdef USE_ANISOTROPY
	#ifdef USE_ANISOTROPYMAP
		mat2 anisotropyMat = mat2( anisotropyVector.x, anisotropyVector.y, - anisotropyVector.y, anisotropyVector.x );
		vec3 anisotropyPolar = texture2D( anisotropyMap, vAnisotropyMapUv ).rgb;
		vec2 anisotropyV = anisotropyMat * normalize( 2.0 * anisotropyPolar.rg - vec2( 1.0 ) ) * anisotropyPolar.b;
	#else
		vec2 anisotropyV = anisotropyVector;
	#endif
	material.anisotropy = length( anisotropyV );
	if( material.anisotropy == 0.0 ) {
		anisotropyV = vec2( 1.0, 0.0 );
	} else {
		anisotropyV /= material.anisotropy;
		material.anisotropy = saturate( material.anisotropy );
	}
	material.alphaT = mix( pow2( material.roughness ), 1.0, pow2( material.anisotropy ) );
	material.anisotropyT = tbn[ 0 ] * anisotropyV.x + tbn[ 1 ] * anisotropyV.y;
	material.anisotropyB = tbn[ 1 ] * anisotropyV.x - tbn[ 0 ] * anisotropyV.y;
#endif`,z0=`struct PhysicalMaterial {
	vec3 diffuseColor;
	float roughness;
	vec3 specularColor;
	float specularF90;
	float dispersion;
	#ifdef USE_CLEARCOAT
		float clearcoat;
		float clearcoatRoughness;
		vec3 clearcoatF0;
		float clearcoatF90;
	#endif
	#ifdef USE_IRIDESCENCE
		float iridescence;
		float iridescenceIOR;
		float iridescenceThickness;
		vec3 iridescenceFresnel;
		vec3 iridescenceF0;
	#endif
	#ifdef USE_SHEEN
		vec3 sheenColor;
		float sheenRoughness;
	#endif
	#ifdef IOR
		float ior;
	#endif
	#ifdef USE_TRANSMISSION
		float transmission;
		float transmissionAlpha;
		float thickness;
		float attenuationDistance;
		vec3 attenuationColor;
	#endif
	#ifdef USE_ANISOTROPY
		float anisotropy;
		float alphaT;
		vec3 anisotropyT;
		vec3 anisotropyB;
	#endif
};
vec3 clearcoatSpecularDirect = vec3( 0.0 );
vec3 clearcoatSpecularIndirect = vec3( 0.0 );
vec3 sheenSpecularDirect = vec3( 0.0 );
vec3 sheenSpecularIndirect = vec3(0.0 );
vec3 Schlick_to_F0( const in vec3 f, const in float f90, const in float dotVH ) {
    float x = clamp( 1.0 - dotVH, 0.0, 1.0 );
    float x2 = x * x;
    float x5 = clamp( x * x2 * x2, 0.0, 0.9999 );
    return ( f - vec3( f90 ) * x5 ) / ( 1.0 - x5 );
}
float V_GGX_SmithCorrelated( const in float alpha, const in float dotNL, const in float dotNV ) {
	float a2 = pow2( alpha );
	float gv = dotNL * sqrt( a2 + ( 1.0 - a2 ) * pow2( dotNV ) );
	float gl = dotNV * sqrt( a2 + ( 1.0 - a2 ) * pow2( dotNL ) );
	return 0.5 / max( gv + gl, EPSILON );
}
float D_GGX( const in float alpha, const in float dotNH ) {
	float a2 = pow2( alpha );
	float denom = pow2( dotNH ) * ( a2 - 1.0 ) + 1.0;
	return RECIPROCAL_PI * a2 / pow2( denom );
}
#ifdef USE_ANISOTROPY
	float V_GGX_SmithCorrelated_Anisotropic( const in float alphaT, const in float alphaB, const in float dotTV, const in float dotBV, const in float dotTL, const in float dotBL, const in float dotNV, const in float dotNL ) {
		float gv = dotNL * length( vec3( alphaT * dotTV, alphaB * dotBV, dotNV ) );
		float gl = dotNV * length( vec3( alphaT * dotTL, alphaB * dotBL, dotNL ) );
		float v = 0.5 / ( gv + gl );
		return saturate(v);
	}
	float D_GGX_Anisotropic( const in float alphaT, const in float alphaB, const in float dotNH, const in float dotTH, const in float dotBH ) {
		float a2 = alphaT * alphaB;
		highp vec3 v = vec3( alphaB * dotTH, alphaT * dotBH, a2 * dotNH );
		highp float v2 = dot( v, v );
		float w2 = a2 / v2;
		return RECIPROCAL_PI * a2 * pow2 ( w2 );
	}
#endif
#ifdef USE_CLEARCOAT
	vec3 BRDF_GGX_Clearcoat( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in PhysicalMaterial material) {
		vec3 f0 = material.clearcoatF0;
		float f90 = material.clearcoatF90;
		float roughness = material.clearcoatRoughness;
		float alpha = pow2( roughness );
		vec3 halfDir = normalize( lightDir + viewDir );
		float dotNL = saturate( dot( normal, lightDir ) );
		float dotNV = saturate( dot( normal, viewDir ) );
		float dotNH = saturate( dot( normal, halfDir ) );
		float dotVH = saturate( dot( viewDir, halfDir ) );
		vec3 F = F_Schlick( f0, f90, dotVH );
		float V = V_GGX_SmithCorrelated( alpha, dotNL, dotNV );
		float D = D_GGX( alpha, dotNH );
		return F * ( V * D );
	}
#endif
vec3 BRDF_GGX( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in PhysicalMaterial material ) {
	vec3 f0 = material.specularColor;
	float f90 = material.specularF90;
	float roughness = material.roughness;
	float alpha = pow2( roughness );
	vec3 halfDir = normalize( lightDir + viewDir );
	float dotNL = saturate( dot( normal, lightDir ) );
	float dotNV = saturate( dot( normal, viewDir ) );
	float dotNH = saturate( dot( normal, halfDir ) );
	float dotVH = saturate( dot( viewDir, halfDir ) );
	vec3 F = F_Schlick( f0, f90, dotVH );
	#ifdef USE_IRIDESCENCE
		F = mix( F, material.iridescenceFresnel, material.iridescence );
	#endif
	#ifdef USE_ANISOTROPY
		float dotTL = dot( material.anisotropyT, lightDir );
		float dotTV = dot( material.anisotropyT, viewDir );
		float dotTH = dot( material.anisotropyT, halfDir );
		float dotBL = dot( material.anisotropyB, lightDir );
		float dotBV = dot( material.anisotropyB, viewDir );
		float dotBH = dot( material.anisotropyB, halfDir );
		float V = V_GGX_SmithCorrelated_Anisotropic( material.alphaT, alpha, dotTV, dotBV, dotTL, dotBL, dotNV, dotNL );
		float D = D_GGX_Anisotropic( material.alphaT, alpha, dotNH, dotTH, dotBH );
	#else
		float V = V_GGX_SmithCorrelated( alpha, dotNL, dotNV );
		float D = D_GGX( alpha, dotNH );
	#endif
	return F * ( V * D );
}
vec2 LTC_Uv( const in vec3 N, const in vec3 V, const in float roughness ) {
	const float LUT_SIZE = 64.0;
	const float LUT_SCALE = ( LUT_SIZE - 1.0 ) / LUT_SIZE;
	const float LUT_BIAS = 0.5 / LUT_SIZE;
	float dotNV = saturate( dot( N, V ) );
	vec2 uv = vec2( roughness, sqrt( 1.0 - dotNV ) );
	uv = uv * LUT_SCALE + LUT_BIAS;
	return uv;
}
float LTC_ClippedSphereFormFactor( const in vec3 f ) {
	float l = length( f );
	return max( ( l * l + f.z ) / ( l + 1.0 ), 0.0 );
}
vec3 LTC_EdgeVectorFormFactor( const in vec3 v1, const in vec3 v2 ) {
	float x = dot( v1, v2 );
	float y = abs( x );
	float a = 0.8543985 + ( 0.4965155 + 0.0145206 * y ) * y;
	float b = 3.4175940 + ( 4.1616724 + y ) * y;
	float v = a / b;
	float theta_sintheta = ( x > 0.0 ) ? v : 0.5 * inversesqrt( max( 1.0 - x * x, 1e-7 ) ) - v;
	return cross( v1, v2 ) * theta_sintheta;
}
vec3 LTC_Evaluate( const in vec3 N, const in vec3 V, const in vec3 P, const in mat3 mInv, const in vec3 rectCoords[ 4 ] ) {
	vec3 v1 = rectCoords[ 1 ] - rectCoords[ 0 ];
	vec3 v2 = rectCoords[ 3 ] - rectCoords[ 0 ];
	vec3 lightNormal = cross( v1, v2 );
	if( dot( lightNormal, P - rectCoords[ 0 ] ) < 0.0 ) return vec3( 0.0 );
	vec3 T1, T2;
	T1 = normalize( V - N * dot( V, N ) );
	T2 = - cross( N, T1 );
	mat3 mat = mInv * transposeMat3( mat3( T1, T2, N ) );
	vec3 coords[ 4 ];
	coords[ 0 ] = mat * ( rectCoords[ 0 ] - P );
	coords[ 1 ] = mat * ( rectCoords[ 1 ] - P );
	coords[ 2 ] = mat * ( rectCoords[ 2 ] - P );
	coords[ 3 ] = mat * ( rectCoords[ 3 ] - P );
	coords[ 0 ] = normalize( coords[ 0 ] );
	coords[ 1 ] = normalize( coords[ 1 ] );
	coords[ 2 ] = normalize( coords[ 2 ] );
	coords[ 3 ] = normalize( coords[ 3 ] );
	vec3 vectorFormFactor = vec3( 0.0 );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 0 ], coords[ 1 ] );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 1 ], coords[ 2 ] );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 2 ], coords[ 3 ] );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 3 ], coords[ 0 ] );
	float result = LTC_ClippedSphereFormFactor( vectorFormFactor );
	return vec3( result );
}
#if defined( USE_SHEEN )
float D_Charlie( float roughness, float dotNH ) {
	float alpha = pow2( roughness );
	float invAlpha = 1.0 / alpha;
	float cos2h = dotNH * dotNH;
	float sin2h = max( 1.0 - cos2h, 0.0078125 );
	return ( 2.0 + invAlpha ) * pow( sin2h, invAlpha * 0.5 ) / ( 2.0 * PI );
}
float V_Neubelt( float dotNV, float dotNL ) {
	return saturate( 1.0 / ( 4.0 * ( dotNL + dotNV - dotNL * dotNV ) ) );
}
vec3 BRDF_Sheen( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, vec3 sheenColor, const in float sheenRoughness ) {
	vec3 halfDir = normalize( lightDir + viewDir );
	float dotNL = saturate( dot( normal, lightDir ) );
	float dotNV = saturate( dot( normal, viewDir ) );
	float dotNH = saturate( dot( normal, halfDir ) );
	float D = D_Charlie( sheenRoughness, dotNH );
	float V = V_Neubelt( dotNV, dotNL );
	return sheenColor * ( D * V );
}
#endif
float IBLSheenBRDF( const in vec3 normal, const in vec3 viewDir, const in float roughness ) {
	float dotNV = saturate( dot( normal, viewDir ) );
	float r2 = roughness * roughness;
	float a = roughness < 0.25 ? -339.2 * r2 + 161.4 * roughness - 25.9 : -8.48 * r2 + 14.3 * roughness - 9.95;
	float b = roughness < 0.25 ? 44.0 * r2 - 23.7 * roughness + 3.26 : 1.97 * r2 - 3.27 * roughness + 0.72;
	float DG = exp( a * dotNV + b ) + ( roughness < 0.25 ? 0.0 : 0.1 * ( roughness - 0.25 ) );
	return saturate( DG * RECIPROCAL_PI );
}
vec2 DFGApprox( const in vec3 normal, const in vec3 viewDir, const in float roughness ) {
	float dotNV = saturate( dot( normal, viewDir ) );
	const vec4 c0 = vec4( - 1, - 0.0275, - 0.572, 0.022 );
	const vec4 c1 = vec4( 1, 0.0425, 1.04, - 0.04 );
	vec4 r = roughness * c0 + c1;
	float a004 = min( r.x * r.x, exp2( - 9.28 * dotNV ) ) * r.x + r.y;
	vec2 fab = vec2( - 1.04, 1.04 ) * a004 + r.zw;
	return fab;
}
vec3 EnvironmentBRDF( const in vec3 normal, const in vec3 viewDir, const in vec3 specularColor, const in float specularF90, const in float roughness ) {
	vec2 fab = DFGApprox( normal, viewDir, roughness );
	return specularColor * fab.x + specularF90 * fab.y;
}
#ifdef USE_IRIDESCENCE
void computeMultiscatteringIridescence( const in vec3 normal, const in vec3 viewDir, const in vec3 specularColor, const in float specularF90, const in float iridescence, const in vec3 iridescenceF0, const in float roughness, inout vec3 singleScatter, inout vec3 multiScatter ) {
#else
void computeMultiscattering( const in vec3 normal, const in vec3 viewDir, const in vec3 specularColor, const in float specularF90, const in float roughness, inout vec3 singleScatter, inout vec3 multiScatter ) {
#endif
	vec2 fab = DFGApprox( normal, viewDir, roughness );
	#ifdef USE_IRIDESCENCE
		vec3 Fr = mix( specularColor, iridescenceF0, iridescence );
	#else
		vec3 Fr = specularColor;
	#endif
	vec3 FssEss = Fr * fab.x + specularF90 * fab.y;
	float Ess = fab.x + fab.y;
	float Ems = 1.0 - Ess;
	vec3 Favg = Fr + ( 1.0 - Fr ) * 0.047619;	vec3 Fms = FssEss * Favg / ( 1.0 - Ems * Favg );
	singleScatter += FssEss;
	multiScatter += Fms * Ems;
}
#if NUM_RECT_AREA_LIGHTS > 0
	void RE_Direct_RectArea_Physical( const in RectAreaLight rectAreaLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {
		vec3 normal = geometryNormal;
		vec3 viewDir = geometryViewDir;
		vec3 position = geometryPosition;
		vec3 lightPos = rectAreaLight.position;
		vec3 halfWidth = rectAreaLight.halfWidth;
		vec3 halfHeight = rectAreaLight.halfHeight;
		vec3 lightColor = rectAreaLight.color;
		float roughness = material.roughness;
		vec3 rectCoords[ 4 ];
		rectCoords[ 0 ] = lightPos + halfWidth - halfHeight;		rectCoords[ 1 ] = lightPos - halfWidth - halfHeight;
		rectCoords[ 2 ] = lightPos - halfWidth + halfHeight;
		rectCoords[ 3 ] = lightPos + halfWidth + halfHeight;
		vec2 uv = LTC_Uv( normal, viewDir, roughness );
		vec4 t1 = texture2D( ltc_1, uv );
		vec4 t2 = texture2D( ltc_2, uv );
		mat3 mInv = mat3(
			vec3( t1.x, 0, t1.y ),
			vec3(    0, 1,    0 ),
			vec3( t1.z, 0, t1.w )
		);
		vec3 fresnel = ( material.specularColor * t2.x + ( vec3( 1.0 ) - material.specularColor ) * t2.y );
		reflectedLight.directSpecular += lightColor * fresnel * LTC_Evaluate( normal, viewDir, position, mInv, rectCoords );
		reflectedLight.directDiffuse += lightColor * material.diffuseColor * LTC_Evaluate( normal, viewDir, position, mat3( 1.0 ), rectCoords );
	}
#endif
void RE_Direct_Physical( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {
	float dotNL = saturate( dot( geometryNormal, directLight.direction ) );
	vec3 irradiance = dotNL * directLight.color;
	#ifdef USE_CLEARCOAT
		float dotNLcc = saturate( dot( geometryClearcoatNormal, directLight.direction ) );
		vec3 ccIrradiance = dotNLcc * directLight.color;
		clearcoatSpecularDirect += ccIrradiance * BRDF_GGX_Clearcoat( directLight.direction, geometryViewDir, geometryClearcoatNormal, material );
	#endif
	#ifdef USE_SHEEN
		sheenSpecularDirect += irradiance * BRDF_Sheen( directLight.direction, geometryViewDir, geometryNormal, material.sheenColor, material.sheenRoughness );
	#endif
	reflectedLight.directSpecular += irradiance * BRDF_GGX( directLight.direction, geometryViewDir, geometryNormal, material );
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
void RE_IndirectDiffuse_Physical( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
void RE_IndirectSpecular_Physical( const in vec3 radiance, const in vec3 irradiance, const in vec3 clearcoatRadiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight) {
	#ifdef USE_CLEARCOAT
		clearcoatSpecularIndirect += clearcoatRadiance * EnvironmentBRDF( geometryClearcoatNormal, geometryViewDir, material.clearcoatF0, material.clearcoatF90, material.clearcoatRoughness );
	#endif
	#ifdef USE_SHEEN
		sheenSpecularIndirect += irradiance * material.sheenColor * IBLSheenBRDF( geometryNormal, geometryViewDir, material.sheenRoughness );
	#endif
	vec3 singleScattering = vec3( 0.0 );
	vec3 multiScattering = vec3( 0.0 );
	vec3 cosineWeightedIrradiance = irradiance * RECIPROCAL_PI;
	#ifdef USE_IRIDESCENCE
		computeMultiscatteringIridescence( geometryNormal, geometryViewDir, material.specularColor, material.specularF90, material.iridescence, material.iridescenceFresnel, material.roughness, singleScattering, multiScattering );
	#else
		computeMultiscattering( geometryNormal, geometryViewDir, material.specularColor, material.specularF90, material.roughness, singleScattering, multiScattering );
	#endif
	vec3 totalScattering = singleScattering + multiScattering;
	vec3 diffuse = material.diffuseColor * ( 1.0 - max( max( totalScattering.r, totalScattering.g ), totalScattering.b ) );
	reflectedLight.indirectSpecular += radiance * singleScattering;
	reflectedLight.indirectSpecular += multiScattering * cosineWeightedIrradiance;
	reflectedLight.indirectDiffuse += diffuse * cosineWeightedIrradiance;
}
#define RE_Direct				RE_Direct_Physical
#define RE_Direct_RectArea		RE_Direct_RectArea_Physical
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Physical
#define RE_IndirectSpecular		RE_IndirectSpecular_Physical
float computeSpecularOcclusion( const in float dotNV, const in float ambientOcclusion, const in float roughness ) {
	return saturate( pow( dotNV + ambientOcclusion, exp2( - 16.0 * roughness - 1.0 ) ) - 1.0 + ambientOcclusion );
}`,H0=`
vec3 geometryPosition = - vViewPosition;
vec3 geometryNormal = normal;
vec3 geometryViewDir = ( isOrthographic ) ? vec3( 0, 0, 1 ) : normalize( vViewPosition );
vec3 geometryClearcoatNormal = vec3( 0.0 );
#ifdef USE_CLEARCOAT
	geometryClearcoatNormal = clearcoatNormal;
#endif
#ifdef USE_IRIDESCENCE
	float dotNVi = saturate( dot( normal, geometryViewDir ) );
	if ( material.iridescenceThickness == 0.0 ) {
		material.iridescence = 0.0;
	} else {
		material.iridescence = saturate( material.iridescence );
	}
	if ( material.iridescence > 0.0 ) {
		material.iridescenceFresnel = evalIridescence( 1.0, material.iridescenceIOR, dotNVi, material.iridescenceThickness, material.specularColor );
		material.iridescenceF0 = Schlick_to_F0( material.iridescenceFresnel, 1.0, dotNVi );
	}
#endif
IncidentLight directLight;
#if ( NUM_POINT_LIGHTS > 0 ) && defined( RE_Direct )
	PointLight pointLight;
	#if defined( USE_SHADOWMAP ) && NUM_POINT_LIGHT_SHADOWS > 0
	PointLightShadow pointLightShadow;
	#endif
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_POINT_LIGHTS; i ++ ) {
		pointLight = pointLights[ i ];
		getPointLightInfo( pointLight, geometryPosition, directLight );
		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_POINT_LIGHT_SHADOWS )
		pointLightShadow = pointLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getPointShadow( pointShadowMap[ i ], pointLightShadow.shadowMapSize, pointLightShadow.shadowIntensity, pointLightShadow.shadowBias, pointLightShadow.shadowRadius, vPointShadowCoord[ i ], pointLightShadow.shadowCameraNear, pointLightShadow.shadowCameraFar ) : 1.0;
		#endif
		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if ( NUM_SPOT_LIGHTS > 0 ) && defined( RE_Direct )
	SpotLight spotLight;
	vec4 spotColor;
	vec3 spotLightCoord;
	bool inSpotLightMap;
	#if defined( USE_SHADOWMAP ) && NUM_SPOT_LIGHT_SHADOWS > 0
	SpotLightShadow spotLightShadow;
	#endif
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SPOT_LIGHTS; i ++ ) {
		spotLight = spotLights[ i ];
		getSpotLightInfo( spotLight, geometryPosition, directLight );
		#if ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS )
		#define SPOT_LIGHT_MAP_INDEX UNROLLED_LOOP_INDEX
		#elif ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
		#define SPOT_LIGHT_MAP_INDEX NUM_SPOT_LIGHT_MAPS
		#else
		#define SPOT_LIGHT_MAP_INDEX ( UNROLLED_LOOP_INDEX - NUM_SPOT_LIGHT_SHADOWS + NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS )
		#endif
		#if ( SPOT_LIGHT_MAP_INDEX < NUM_SPOT_LIGHT_MAPS )
			spotLightCoord = vSpotLightCoord[ i ].xyz / vSpotLightCoord[ i ].w;
			inSpotLightMap = all( lessThan( abs( spotLightCoord * 2. - 1. ), vec3( 1.0 ) ) );
			spotColor = texture2D( spotLightMap[ SPOT_LIGHT_MAP_INDEX ], spotLightCoord.xy );
			directLight.color = inSpotLightMap ? directLight.color * spotColor.rgb : directLight.color;
		#endif
		#undef SPOT_LIGHT_MAP_INDEX
		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
		spotLightShadow = spotLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getShadow( spotShadowMap[ i ], spotLightShadow.shadowMapSize, spotLightShadow.shadowIntensity, spotLightShadow.shadowBias, spotLightShadow.shadowRadius, vSpotLightCoord[ i ] ) : 1.0;
		#endif
		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if ( NUM_DIR_LIGHTS > 0 ) && defined( RE_Direct )
	DirectionalLight directionalLight;
	#if defined( USE_SHADOWMAP ) && NUM_DIR_LIGHT_SHADOWS > 0
	DirectionalLightShadow directionalLightShadow;
	#endif
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_DIR_LIGHTS; i ++ ) {
		directionalLight = directionalLights[ i ];
		getDirectionalLightInfo( directionalLight, directLight );
		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_DIR_LIGHT_SHADOWS )
		directionalLightShadow = directionalLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getShadow( directionalShadowMap[ i ], directionalLightShadow.shadowMapSize, directionalLightShadow.shadowIntensity, directionalLightShadow.shadowBias, directionalLightShadow.shadowRadius, vDirectionalShadowCoord[ i ] ) : 1.0;
		#endif
		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if ( NUM_RECT_AREA_LIGHTS > 0 ) && defined( RE_Direct_RectArea )
	RectAreaLight rectAreaLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_RECT_AREA_LIGHTS; i ++ ) {
		rectAreaLight = rectAreaLights[ i ];
		RE_Direct_RectArea( rectAreaLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if defined( RE_IndirectDiffuse )
	vec3 iblIrradiance = vec3( 0.0 );
	vec3 irradiance = getAmbientLightIrradiance( ambientLightColor );
	#if defined( USE_LIGHT_PROBES )
		irradiance += getLightProbeIrradiance( lightProbe, geometryNormal );
	#endif
	#if ( NUM_HEMI_LIGHTS > 0 )
		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_HEMI_LIGHTS; i ++ ) {
			irradiance += getHemisphereLightIrradiance( hemisphereLights[ i ], geometryNormal );
		}
		#pragma unroll_loop_end
	#endif
#endif
#if defined( RE_IndirectSpecular )
	vec3 radiance = vec3( 0.0 );
	vec3 clearcoatRadiance = vec3( 0.0 );
#endif`,V0=`#if defined( RE_IndirectDiffuse )
	#ifdef USE_LIGHTMAP
		vec4 lightMapTexel = texture2D( lightMap, vLightMapUv );
		vec3 lightMapIrradiance = lightMapTexel.rgb * lightMapIntensity;
		irradiance += lightMapIrradiance;
	#endif
	#if defined( USE_ENVMAP ) && defined( STANDARD ) && defined( ENVMAP_TYPE_CUBE_UV )
		iblIrradiance += getIBLIrradiance( geometryNormal );
	#endif
#endif
#if defined( USE_ENVMAP ) && defined( RE_IndirectSpecular )
	#ifdef USE_ANISOTROPY
		radiance += getIBLAnisotropyRadiance( geometryViewDir, geometryNormal, material.roughness, material.anisotropyB, material.anisotropy );
	#else
		radiance += getIBLRadiance( geometryViewDir, geometryNormal, material.roughness );
	#endif
	#ifdef USE_CLEARCOAT
		clearcoatRadiance += getIBLRadiance( geometryViewDir, geometryClearcoatNormal, material.clearcoatRoughness );
	#endif
#endif`,G0=`#if defined( RE_IndirectDiffuse )
	RE_IndirectDiffuse( irradiance, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
#endif
#if defined( RE_IndirectSpecular )
	RE_IndirectSpecular( radiance, iblIrradiance, clearcoatRadiance, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
#endif`,W0=`#if defined( USE_LOGARITHMIC_DEPTH_BUFFER )
	gl_FragDepth = vIsPerspective == 0.0 ? gl_FragCoord.z : log2( vFragDepth ) * logDepthBufFC * 0.5;
#endif`,Y0=`#if defined( USE_LOGARITHMIC_DEPTH_BUFFER )
	uniform float logDepthBufFC;
	varying float vFragDepth;
	varying float vIsPerspective;
#endif`,X0=`#ifdef USE_LOGARITHMIC_DEPTH_BUFFER
	varying float vFragDepth;
	varying float vIsPerspective;
#endif`,q0=`#ifdef USE_LOGARITHMIC_DEPTH_BUFFER
	vFragDepth = 1.0 + gl_Position.w;
	vIsPerspective = float( isPerspectiveMatrix( projectionMatrix ) );
#endif`,j0=`#ifdef USE_MAP
	vec4 sampledDiffuseColor = texture2D( map, vMapUv );
	#ifdef DECODE_VIDEO_TEXTURE
		sampledDiffuseColor = sRGBTransferEOTF( sampledDiffuseColor );
	#endif
	diffuseColor *= sampledDiffuseColor;
#endif`,K0=`#ifdef USE_MAP
	uniform sampler2D map;
#endif`,Z0=`#if defined( USE_MAP ) || defined( USE_ALPHAMAP )
	#if defined( USE_POINTS_UV )
		vec2 uv = vUv;
	#else
		vec2 uv = ( uvTransform * vec3( gl_PointCoord.x, 1.0 - gl_PointCoord.y, 1 ) ).xy;
	#endif
#endif
#ifdef USE_MAP
	diffuseColor *= texture2D( map, uv );
#endif
#ifdef USE_ALPHAMAP
	diffuseColor.a *= texture2D( alphaMap, uv ).g;
#endif`,J0=`#if defined( USE_POINTS_UV )
	varying vec2 vUv;
#else
	#if defined( USE_MAP ) || defined( USE_ALPHAMAP )
		uniform mat3 uvTransform;
	#endif
#endif
#ifdef USE_MAP
	uniform sampler2D map;
#endif
#ifdef USE_ALPHAMAP
	uniform sampler2D alphaMap;
#endif`,$0=`float metalnessFactor = metalness;
#ifdef USE_METALNESSMAP
	vec4 texelMetalness = texture2D( metalnessMap, vMetalnessMapUv );
	metalnessFactor *= texelMetalness.b;
#endif`,Q0=`#ifdef USE_METALNESSMAP
	uniform sampler2D metalnessMap;
#endif`,eb=`#ifdef USE_INSTANCING_MORPH
	float morphTargetInfluences[ MORPHTARGETS_COUNT ];
	float morphTargetBaseInfluence = texelFetch( morphTexture, ivec2( 0, gl_InstanceID ), 0 ).r;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		morphTargetInfluences[i] =  texelFetch( morphTexture, ivec2( i + 1, gl_InstanceID ), 0 ).r;
	}
#endif`,tb=`#if defined( USE_MORPHCOLORS )
	vColor *= morphTargetBaseInfluence;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		#if defined( USE_COLOR_ALPHA )
			if ( morphTargetInfluences[ i ] != 0.0 ) vColor += getMorph( gl_VertexID, i, 2 ) * morphTargetInfluences[ i ];
		#elif defined( USE_COLOR )
			if ( morphTargetInfluences[ i ] != 0.0 ) vColor += getMorph( gl_VertexID, i, 2 ).rgb * morphTargetInfluences[ i ];
		#endif
	}
#endif`,nb=`#ifdef USE_MORPHNORMALS
	objectNormal *= morphTargetBaseInfluence;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		if ( morphTargetInfluences[ i ] != 0.0 ) objectNormal += getMorph( gl_VertexID, i, 1 ).xyz * morphTargetInfluences[ i ];
	}
#endif`,ib=`#ifdef USE_MORPHTARGETS
	#ifndef USE_INSTANCING_MORPH
		uniform float morphTargetBaseInfluence;
		uniform float morphTargetInfluences[ MORPHTARGETS_COUNT ];
	#endif
	uniform sampler2DArray morphTargetsTexture;
	uniform ivec2 morphTargetsTextureSize;
	vec4 getMorph( const in int vertexIndex, const in int morphTargetIndex, const in int offset ) {
		int texelIndex = vertexIndex * MORPHTARGETS_TEXTURE_STRIDE + offset;
		int y = texelIndex / morphTargetsTextureSize.x;
		int x = texelIndex - y * morphTargetsTextureSize.x;
		ivec3 morphUV = ivec3( x, y, morphTargetIndex );
		return texelFetch( morphTargetsTexture, morphUV, 0 );
	}
#endif`,sb=`#ifdef USE_MORPHTARGETS
	transformed *= morphTargetBaseInfluence;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		if ( morphTargetInfluences[ i ] != 0.0 ) transformed += getMorph( gl_VertexID, i, 0 ).xyz * morphTargetInfluences[ i ];
	}
#endif`,rb=`float faceDirection = gl_FrontFacing ? 1.0 : - 1.0;
#ifdef FLAT_SHADED
	vec3 fdx = dFdx( vViewPosition );
	vec3 fdy = dFdy( vViewPosition );
	vec3 normal = normalize( cross( fdx, fdy ) );
#else
	vec3 normal = normalize( vNormal );
	#ifdef DOUBLE_SIDED
		normal *= faceDirection;
	#endif
#endif
#if defined( USE_NORMALMAP_TANGENTSPACE ) || defined( USE_CLEARCOAT_NORMALMAP ) || defined( USE_ANISOTROPY )
	#ifdef USE_TANGENT
		mat3 tbn = mat3( normalize( vTangent ), normalize( vBitangent ), normal );
	#else
		mat3 tbn = getTangentFrame( - vViewPosition, normal,
		#if defined( USE_NORMALMAP )
			vNormalMapUv
		#elif defined( USE_CLEARCOAT_NORMALMAP )
			vClearcoatNormalMapUv
		#else
			vUv
		#endif
		);
	#endif
	#if defined( DOUBLE_SIDED ) && ! defined( FLAT_SHADED )
		tbn[0] *= faceDirection;
		tbn[1] *= faceDirection;
	#endif
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	#ifdef USE_TANGENT
		mat3 tbn2 = mat3( normalize( vTangent ), normalize( vBitangent ), normal );
	#else
		mat3 tbn2 = getTangentFrame( - vViewPosition, normal, vClearcoatNormalMapUv );
	#endif
	#if defined( DOUBLE_SIDED ) && ! defined( FLAT_SHADED )
		tbn2[0] *= faceDirection;
		tbn2[1] *= faceDirection;
	#endif
#endif
vec3 nonPerturbedNormal = normal;`,ab=`#ifdef USE_NORMALMAP_OBJECTSPACE
	normal = texture2D( normalMap, vNormalMapUv ).xyz * 2.0 - 1.0;
	#ifdef FLIP_SIDED
		normal = - normal;
	#endif
	#ifdef DOUBLE_SIDED
		normal = normal * faceDirection;
	#endif
	normal = normalize( normalMatrix * normal );
#elif defined( USE_NORMALMAP_TANGENTSPACE )
	vec3 mapN = texture2D( normalMap, vNormalMapUv ).xyz * 2.0 - 1.0;
	mapN.xy *= normalScale;
	normal = normalize( tbn * mapN );
#elif defined( USE_BUMPMAP )
	normal = perturbNormalArb( - vViewPosition, normal, dHdxy_fwd(), faceDirection );
#endif`,ob=`#ifndef FLAT_SHADED
	varying vec3 vNormal;
	#ifdef USE_TANGENT
		varying vec3 vTangent;
		varying vec3 vBitangent;
	#endif
#endif`,cb=`#ifndef FLAT_SHADED
	varying vec3 vNormal;
	#ifdef USE_TANGENT
		varying vec3 vTangent;
		varying vec3 vBitangent;
	#endif
#endif`,lb=`#ifndef FLAT_SHADED
	vNormal = normalize( transformedNormal );
	#ifdef USE_TANGENT
		vTangent = normalize( transformedTangent );
		vBitangent = normalize( cross( vNormal, vTangent ) * tangent.w );
	#endif
#endif`,hb=`#ifdef USE_NORMALMAP
	uniform sampler2D normalMap;
	uniform vec2 normalScale;
#endif
#ifdef USE_NORMALMAP_OBJECTSPACE
	uniform mat3 normalMatrix;
#endif
#if ! defined ( USE_TANGENT ) && ( defined ( USE_NORMALMAP_TANGENTSPACE ) || defined ( USE_CLEARCOAT_NORMALMAP ) || defined( USE_ANISOTROPY ) )
	mat3 getTangentFrame( vec3 eye_pos, vec3 surf_norm, vec2 uv ) {
		vec3 q0 = dFdx( eye_pos.xyz );
		vec3 q1 = dFdy( eye_pos.xyz );
		vec2 st0 = dFdx( uv.st );
		vec2 st1 = dFdy( uv.st );
		vec3 N = surf_norm;
		vec3 q1perp = cross( q1, N );
		vec3 q0perp = cross( N, q0 );
		vec3 T = q1perp * st0.x + q0perp * st1.x;
		vec3 B = q1perp * st0.y + q0perp * st1.y;
		float det = max( dot( T, T ), dot( B, B ) );
		float scale = ( det == 0.0 ) ? 0.0 : inversesqrt( det );
		return mat3( T * scale, B * scale, N );
	}
#endif`,ub=`#ifdef USE_CLEARCOAT
	vec3 clearcoatNormal = nonPerturbedNormal;
#endif`,db=`#ifdef USE_CLEARCOAT_NORMALMAP
	vec3 clearcoatMapN = texture2D( clearcoatNormalMap, vClearcoatNormalMapUv ).xyz * 2.0 - 1.0;
	clearcoatMapN.xy *= clearcoatNormalScale;
	clearcoatNormal = normalize( tbn2 * clearcoatMapN );
#endif`,fb=`#ifdef USE_CLEARCOATMAP
	uniform sampler2D clearcoatMap;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	uniform sampler2D clearcoatNormalMap;
	uniform vec2 clearcoatNormalScale;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	uniform sampler2D clearcoatRoughnessMap;
#endif`,pb=`#ifdef USE_IRIDESCENCEMAP
	uniform sampler2D iridescenceMap;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	uniform sampler2D iridescenceThicknessMap;
#endif`,mb=`#ifdef OPAQUE
diffuseColor.a = 1.0;
#endif
#ifdef USE_TRANSMISSION
diffuseColor.a *= material.transmissionAlpha;
#endif
gl_FragColor = vec4( outgoingLight, diffuseColor.a );`,gb=`vec3 packNormalToRGB( const in vec3 normal ) {
	return normalize( normal ) * 0.5 + 0.5;
}
vec3 unpackRGBToNormal( const in vec3 rgb ) {
	return 2.0 * rgb.xyz - 1.0;
}
const float PackUpscale = 256. / 255.;const float UnpackDownscale = 255. / 256.;const float ShiftRight8 = 1. / 256.;
const float Inv255 = 1. / 255.;
const vec4 PackFactors = vec4( 1.0, 256.0, 256.0 * 256.0, 256.0 * 256.0 * 256.0 );
const vec2 UnpackFactors2 = vec2( UnpackDownscale, 1.0 / PackFactors.g );
const vec3 UnpackFactors3 = vec3( UnpackDownscale / PackFactors.rg, 1.0 / PackFactors.b );
const vec4 UnpackFactors4 = vec4( UnpackDownscale / PackFactors.rgb, 1.0 / PackFactors.a );
vec4 packDepthToRGBA( const in float v ) {
	if( v <= 0.0 )
		return vec4( 0., 0., 0., 0. );
	if( v >= 1.0 )
		return vec4( 1., 1., 1., 1. );
	float vuf;
	float af = modf( v * PackFactors.a, vuf );
	float bf = modf( vuf * ShiftRight8, vuf );
	float gf = modf( vuf * ShiftRight8, vuf );
	return vec4( vuf * Inv255, gf * PackUpscale, bf * PackUpscale, af );
}
vec3 packDepthToRGB( const in float v ) {
	if( v <= 0.0 )
		return vec3( 0., 0., 0. );
	if( v >= 1.0 )
		return vec3( 1., 1., 1. );
	float vuf;
	float bf = modf( v * PackFactors.b, vuf );
	float gf = modf( vuf * ShiftRight8, vuf );
	return vec3( vuf * Inv255, gf * PackUpscale, bf );
}
vec2 packDepthToRG( const in float v ) {
	if( v <= 0.0 )
		return vec2( 0., 0. );
	if( v >= 1.0 )
		return vec2( 1., 1. );
	float vuf;
	float gf = modf( v * 256., vuf );
	return vec2( vuf * Inv255, gf );
}
float unpackRGBAToDepth( const in vec4 v ) {
	return dot( v, UnpackFactors4 );
}
float unpackRGBToDepth( const in vec3 v ) {
	return dot( v, UnpackFactors3 );
}
float unpackRGToDepth( const in vec2 v ) {
	return v.r * UnpackFactors2.r + v.g * UnpackFactors2.g;
}
vec4 pack2HalfToRGBA( const in vec2 v ) {
	vec4 r = vec4( v.x, fract( v.x * 255.0 ), v.y, fract( v.y * 255.0 ) );
	return vec4( r.x - r.y / 255.0, r.y, r.z - r.w / 255.0, r.w );
}
vec2 unpackRGBATo2Half( const in vec4 v ) {
	return vec2( v.x + ( v.y / 255.0 ), v.z + ( v.w / 255.0 ) );
}
float viewZToOrthographicDepth( const in float viewZ, const in float near, const in float far ) {
	return ( viewZ + near ) / ( near - far );
}
float orthographicDepthToViewZ( const in float depth, const in float near, const in float far ) {
	return depth * ( near - far ) - near;
}
float viewZToPerspectiveDepth( const in float viewZ, const in float near, const in float far ) {
	return ( ( near + viewZ ) * far ) / ( ( far - near ) * viewZ );
}
float perspectiveDepthToViewZ( const in float depth, const in float near, const in float far ) {
	return ( near * far ) / ( ( far - near ) * depth - far );
}`,bb=`#ifdef PREMULTIPLIED_ALPHA
	gl_FragColor.rgb *= gl_FragColor.a;
#endif`,yb=`vec4 mvPosition = vec4( transformed, 1.0 );
#ifdef USE_BATCHING
	mvPosition = batchingMatrix * mvPosition;
#endif
#ifdef USE_INSTANCING
	mvPosition = instanceMatrix * mvPosition;
#endif
mvPosition = modelViewMatrix * mvPosition;
gl_Position = projectionMatrix * mvPosition;`,xb=`#ifdef DITHERING
	gl_FragColor.rgb = dithering( gl_FragColor.rgb );
#endif`,vb=`#ifdef DITHERING
	vec3 dithering( vec3 color ) {
		float grid_position = rand( gl_FragCoord.xy );
		vec3 dither_shift_RGB = vec3( 0.25 / 255.0, -0.25 / 255.0, 0.25 / 255.0 );
		dither_shift_RGB = mix( 2.0 * dither_shift_RGB, -2.0 * dither_shift_RGB, grid_position );
		return color + dither_shift_RGB;
	}
#endif`,_b=`float roughnessFactor = roughness;
#ifdef USE_ROUGHNESSMAP
	vec4 texelRoughness = texture2D( roughnessMap, vRoughnessMapUv );
	roughnessFactor *= texelRoughness.g;
#endif`,wb=`#ifdef USE_ROUGHNESSMAP
	uniform sampler2D roughnessMap;
#endif`,Mb=`#if NUM_SPOT_LIGHT_COORDS > 0
	varying vec4 vSpotLightCoord[ NUM_SPOT_LIGHT_COORDS ];
#endif
#if NUM_SPOT_LIGHT_MAPS > 0
	uniform sampler2D spotLightMap[ NUM_SPOT_LIGHT_MAPS ];
#endif
#ifdef USE_SHADOWMAP
	#if NUM_DIR_LIGHT_SHADOWS > 0
		uniform sampler2D directionalShadowMap[ NUM_DIR_LIGHT_SHADOWS ];
		varying vec4 vDirectionalShadowCoord[ NUM_DIR_LIGHT_SHADOWS ];
		struct DirectionalLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform DirectionalLightShadow directionalLightShadows[ NUM_DIR_LIGHT_SHADOWS ];
	#endif
	#if NUM_SPOT_LIGHT_SHADOWS > 0
		uniform sampler2D spotShadowMap[ NUM_SPOT_LIGHT_SHADOWS ];
		struct SpotLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform SpotLightShadow spotLightShadows[ NUM_SPOT_LIGHT_SHADOWS ];
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
		uniform sampler2D pointShadowMap[ NUM_POINT_LIGHT_SHADOWS ];
		varying vec4 vPointShadowCoord[ NUM_POINT_LIGHT_SHADOWS ];
		struct PointLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
			float shadowCameraNear;
			float shadowCameraFar;
		};
		uniform PointLightShadow pointLightShadows[ NUM_POINT_LIGHT_SHADOWS ];
	#endif
	float texture2DCompare( sampler2D depths, vec2 uv, float compare ) {
		float depth = unpackRGBAToDepth( texture2D( depths, uv ) );
		#ifdef USE_REVERSED_DEPTH_BUFFER
			return step( depth, compare );
		#else
			return step( compare, depth );
		#endif
	}
	vec2 texture2DDistribution( sampler2D shadow, vec2 uv ) {
		return unpackRGBATo2Half( texture2D( shadow, uv ) );
	}
	float VSMShadow( sampler2D shadow, vec2 uv, float compare ) {
		float occlusion = 1.0;
		vec2 distribution = texture2DDistribution( shadow, uv );
		#ifdef USE_REVERSED_DEPTH_BUFFER
			float hard_shadow = step( distribution.x, compare );
		#else
			float hard_shadow = step( compare, distribution.x );
		#endif
		if ( hard_shadow != 1.0 ) {
			float distance = compare - distribution.x;
			float variance = max( 0.00000, distribution.y * distribution.y );
			float softness_probability = variance / (variance + distance * distance );			softness_probability = clamp( ( softness_probability - 0.3 ) / ( 0.95 - 0.3 ), 0.0, 1.0 );			occlusion = clamp( max( hard_shadow, softness_probability ), 0.0, 1.0 );
		}
		return occlusion;
	}
	float getShadow( sampler2D shadowMap, vec2 shadowMapSize, float shadowIntensity, float shadowBias, float shadowRadius, vec4 shadowCoord ) {
		float shadow = 1.0;
		shadowCoord.xyz /= shadowCoord.w;
		shadowCoord.z += shadowBias;
		bool inFrustum = shadowCoord.x >= 0.0 && shadowCoord.x <= 1.0 && shadowCoord.y >= 0.0 && shadowCoord.y <= 1.0;
		bool frustumTest = inFrustum && shadowCoord.z <= 1.0;
		if ( frustumTest ) {
		#if defined( SHADOWMAP_TYPE_PCF )
			vec2 texelSize = vec2( 1.0 ) / shadowMapSize;
			float dx0 = - texelSize.x * shadowRadius;
			float dy0 = - texelSize.y * shadowRadius;
			float dx1 = + texelSize.x * shadowRadius;
			float dy1 = + texelSize.y * shadowRadius;
			float dx2 = dx0 / 2.0;
			float dy2 = dy0 / 2.0;
			float dx3 = dx1 / 2.0;
			float dy3 = dy1 / 2.0;
			shadow = (
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx0, dy0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( 0.0, dy0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx1, dy0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx2, dy2 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( 0.0, dy2 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx3, dy2 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx0, 0.0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx2, 0.0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy, shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx3, 0.0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx1, 0.0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx2, dy3 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( 0.0, dy3 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx3, dy3 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx0, dy1 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( 0.0, dy1 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx1, dy1 ), shadowCoord.z )
			) * ( 1.0 / 17.0 );
		#elif defined( SHADOWMAP_TYPE_PCF_SOFT )
			vec2 texelSize = vec2( 1.0 ) / shadowMapSize;
			float dx = texelSize.x;
			float dy = texelSize.y;
			vec2 uv = shadowCoord.xy;
			vec2 f = fract( uv * shadowMapSize + 0.5 );
			uv -= f * texelSize;
			shadow = (
				texture2DCompare( shadowMap, uv, shadowCoord.z ) +
				texture2DCompare( shadowMap, uv + vec2( dx, 0.0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, uv + vec2( 0.0, dy ), shadowCoord.z ) +
				texture2DCompare( shadowMap, uv + texelSize, shadowCoord.z ) +
				mix( texture2DCompare( shadowMap, uv + vec2( -dx, 0.0 ), shadowCoord.z ),
					 texture2DCompare( shadowMap, uv + vec2( 2.0 * dx, 0.0 ), shadowCoord.z ),
					 f.x ) +
				mix( texture2DCompare( shadowMap, uv + vec2( -dx, dy ), shadowCoord.z ),
					 texture2DCompare( shadowMap, uv + vec2( 2.0 * dx, dy ), shadowCoord.z ),
					 f.x ) +
				mix( texture2DCompare( shadowMap, uv + vec2( 0.0, -dy ), shadowCoord.z ),
					 texture2DCompare( shadowMap, uv + vec2( 0.0, 2.0 * dy ), shadowCoord.z ),
					 f.y ) +
				mix( texture2DCompare( shadowMap, uv + vec2( dx, -dy ), shadowCoord.z ),
					 texture2DCompare( shadowMap, uv + vec2( dx, 2.0 * dy ), shadowCoord.z ),
					 f.y ) +
				mix( mix( texture2DCompare( shadowMap, uv + vec2( -dx, -dy ), shadowCoord.z ),
						  texture2DCompare( shadowMap, uv + vec2( 2.0 * dx, -dy ), shadowCoord.z ),
						  f.x ),
					 mix( texture2DCompare( shadowMap, uv + vec2( -dx, 2.0 * dy ), shadowCoord.z ),
						  texture2DCompare( shadowMap, uv + vec2( 2.0 * dx, 2.0 * dy ), shadowCoord.z ),
						  f.x ),
					 f.y )
			) * ( 1.0 / 9.0 );
		#elif defined( SHADOWMAP_TYPE_VSM )
			shadow = VSMShadow( shadowMap, shadowCoord.xy, shadowCoord.z );
		#else
			shadow = texture2DCompare( shadowMap, shadowCoord.xy, shadowCoord.z );
		#endif
		}
		return mix( 1.0, shadow, shadowIntensity );
	}
	vec2 cubeToUV( vec3 v, float texelSizeY ) {
		vec3 absV = abs( v );
		float scaleToCube = 1.0 / max( absV.x, max( absV.y, absV.z ) );
		absV *= scaleToCube;
		v *= scaleToCube * ( 1.0 - 2.0 * texelSizeY );
		vec2 planar = v.xy;
		float almostATexel = 1.5 * texelSizeY;
		float almostOne = 1.0 - almostATexel;
		if ( absV.z >= almostOne ) {
			if ( v.z > 0.0 )
				planar.x = 4.0 - v.x;
		} else if ( absV.x >= almostOne ) {
			float signX = sign( v.x );
			planar.x = v.z * signX + 2.0 * signX;
		} else if ( absV.y >= almostOne ) {
			float signY = sign( v.y );
			planar.x = v.x + 2.0 * signY + 2.0;
			planar.y = v.z * signY - 2.0;
		}
		return vec2( 0.125, 0.25 ) * planar + vec2( 0.375, 0.75 );
	}
	float getPointShadow( sampler2D shadowMap, vec2 shadowMapSize, float shadowIntensity, float shadowBias, float shadowRadius, vec4 shadowCoord, float shadowCameraNear, float shadowCameraFar ) {
		float shadow = 1.0;
		vec3 lightToPosition = shadowCoord.xyz;
		
		float lightToPositionLength = length( lightToPosition );
		if ( lightToPositionLength - shadowCameraFar <= 0.0 && lightToPositionLength - shadowCameraNear >= 0.0 ) {
			float dp = ( lightToPositionLength - shadowCameraNear ) / ( shadowCameraFar - shadowCameraNear );			dp += shadowBias;
			vec3 bd3D = normalize( lightToPosition );
			vec2 texelSize = vec2( 1.0 ) / ( shadowMapSize * vec2( 4.0, 2.0 ) );
			#if defined( SHADOWMAP_TYPE_PCF ) || defined( SHADOWMAP_TYPE_PCF_SOFT ) || defined( SHADOWMAP_TYPE_VSM )
				vec2 offset = vec2( - 1, 1 ) * shadowRadius * texelSize.y;
				shadow = (
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.xyy, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.yyy, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.xyx, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.yyx, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.xxy, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.yxy, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.xxx, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.yxx, texelSize.y ), dp )
				) * ( 1.0 / 9.0 );
			#else
				shadow = texture2DCompare( shadowMap, cubeToUV( bd3D, texelSize.y ), dp );
			#endif
		}
		return mix( 1.0, shadow, shadowIntensity );
	}
#endif`,Sb=`#if NUM_SPOT_LIGHT_COORDS > 0
	uniform mat4 spotLightMatrix[ NUM_SPOT_LIGHT_COORDS ];
	varying vec4 vSpotLightCoord[ NUM_SPOT_LIGHT_COORDS ];
#endif
#ifdef USE_SHADOWMAP
	#if NUM_DIR_LIGHT_SHADOWS > 0
		uniform mat4 directionalShadowMatrix[ NUM_DIR_LIGHT_SHADOWS ];
		varying vec4 vDirectionalShadowCoord[ NUM_DIR_LIGHT_SHADOWS ];
		struct DirectionalLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform DirectionalLightShadow directionalLightShadows[ NUM_DIR_LIGHT_SHADOWS ];
	#endif
	#if NUM_SPOT_LIGHT_SHADOWS > 0
		struct SpotLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform SpotLightShadow spotLightShadows[ NUM_SPOT_LIGHT_SHADOWS ];
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
		uniform mat4 pointShadowMatrix[ NUM_POINT_LIGHT_SHADOWS ];
		varying vec4 vPointShadowCoord[ NUM_POINT_LIGHT_SHADOWS ];
		struct PointLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
			float shadowCameraNear;
			float shadowCameraFar;
		};
		uniform PointLightShadow pointLightShadows[ NUM_POINT_LIGHT_SHADOWS ];
	#endif
#endif`,Tb=`#if ( defined( USE_SHADOWMAP ) && ( NUM_DIR_LIGHT_SHADOWS > 0 || NUM_POINT_LIGHT_SHADOWS > 0 ) ) || ( NUM_SPOT_LIGHT_COORDS > 0 )
	vec3 shadowWorldNormal = inverseTransformDirection( transformedNormal, viewMatrix );
	vec4 shadowWorldPosition;
#endif
#if defined( USE_SHADOWMAP )
	#if NUM_DIR_LIGHT_SHADOWS > 0
		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_DIR_LIGHT_SHADOWS; i ++ ) {
			shadowWorldPosition = worldPosition + vec4( shadowWorldNormal * directionalLightShadows[ i ].shadowNormalBias, 0 );
			vDirectionalShadowCoord[ i ] = directionalShadowMatrix[ i ] * shadowWorldPosition;
		}
		#pragma unroll_loop_end
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_POINT_LIGHT_SHADOWS; i ++ ) {
			shadowWorldPosition = worldPosition + vec4( shadowWorldNormal * pointLightShadows[ i ].shadowNormalBias, 0 );
			vPointShadowCoord[ i ] = pointShadowMatrix[ i ] * shadowWorldPosition;
		}
		#pragma unroll_loop_end
	#endif
#endif
#if NUM_SPOT_LIGHT_COORDS > 0
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SPOT_LIGHT_COORDS; i ++ ) {
		shadowWorldPosition = worldPosition;
		#if ( defined( USE_SHADOWMAP ) && UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
			shadowWorldPosition.xyz += shadowWorldNormal * spotLightShadows[ i ].shadowNormalBias;
		#endif
		vSpotLightCoord[ i ] = spotLightMatrix[ i ] * shadowWorldPosition;
	}
	#pragma unroll_loop_end
#endif`,Eb=`float getShadowMask() {
	float shadow = 1.0;
	#ifdef USE_SHADOWMAP
	#if NUM_DIR_LIGHT_SHADOWS > 0
	DirectionalLightShadow directionalLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_DIR_LIGHT_SHADOWS; i ++ ) {
		directionalLight = directionalLightShadows[ i ];
		shadow *= receiveShadow ? getShadow( directionalShadowMap[ i ], directionalLight.shadowMapSize, directionalLight.shadowIntensity, directionalLight.shadowBias, directionalLight.shadowRadius, vDirectionalShadowCoord[ i ] ) : 1.0;
	}
	#pragma unroll_loop_end
	#endif
	#if NUM_SPOT_LIGHT_SHADOWS > 0
	SpotLightShadow spotLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SPOT_LIGHT_SHADOWS; i ++ ) {
		spotLight = spotLightShadows[ i ];
		shadow *= receiveShadow ? getShadow( spotShadowMap[ i ], spotLight.shadowMapSize, spotLight.shadowIntensity, spotLight.shadowBias, spotLight.shadowRadius, vSpotLightCoord[ i ] ) : 1.0;
	}
	#pragma unroll_loop_end
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
	PointLightShadow pointLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_POINT_LIGHT_SHADOWS; i ++ ) {
		pointLight = pointLightShadows[ i ];
		shadow *= receiveShadow ? getPointShadow( pointShadowMap[ i ], pointLight.shadowMapSize, pointLight.shadowIntensity, pointLight.shadowBias, pointLight.shadowRadius, vPointShadowCoord[ i ], pointLight.shadowCameraNear, pointLight.shadowCameraFar ) : 1.0;
	}
	#pragma unroll_loop_end
	#endif
	#endif
	return shadow;
}`,Ab=`#ifdef USE_SKINNING
	mat4 boneMatX = getBoneMatrix( skinIndex.x );
	mat4 boneMatY = getBoneMatrix( skinIndex.y );
	mat4 boneMatZ = getBoneMatrix( skinIndex.z );
	mat4 boneMatW = getBoneMatrix( skinIndex.w );
#endif`,Rb=`#ifdef USE_SKINNING
	uniform mat4 bindMatrix;
	uniform mat4 bindMatrixInverse;
	uniform highp sampler2D boneTexture;
	mat4 getBoneMatrix( const in float i ) {
		int size = textureSize( boneTexture, 0 ).x;
		int j = int( i ) * 4;
		int x = j % size;
		int y = j / size;
		vec4 v1 = texelFetch( boneTexture, ivec2( x, y ), 0 );
		vec4 v2 = texelFetch( boneTexture, ivec2( x + 1, y ), 0 );
		vec4 v3 = texelFetch( boneTexture, ivec2( x + 2, y ), 0 );
		vec4 v4 = texelFetch( boneTexture, ivec2( x + 3, y ), 0 );
		return mat4( v1, v2, v3, v4 );
	}
#endif`,Cb=`#ifdef USE_SKINNING
	vec4 skinVertex = bindMatrix * vec4( transformed, 1.0 );
	vec4 skinned = vec4( 0.0 );
	skinned += boneMatX * skinVertex * skinWeight.x;
	skinned += boneMatY * skinVertex * skinWeight.y;
	skinned += boneMatZ * skinVertex * skinWeight.z;
	skinned += boneMatW * skinVertex * skinWeight.w;
	transformed = ( bindMatrixInverse * skinned ).xyz;
#endif`,Ib=`#ifdef USE_SKINNING
	mat4 skinMatrix = mat4( 0.0 );
	skinMatrix += skinWeight.x * boneMatX;
	skinMatrix += skinWeight.y * boneMatY;
	skinMatrix += skinWeight.z * boneMatZ;
	skinMatrix += skinWeight.w * boneMatW;
	skinMatrix = bindMatrixInverse * skinMatrix * bindMatrix;
	objectNormal = vec4( skinMatrix * vec4( objectNormal, 0.0 ) ).xyz;
	#ifdef USE_TANGENT
		objectTangent = vec4( skinMatrix * vec4( objectTangent, 0.0 ) ).xyz;
	#endif
#endif`,Pb=`float specularStrength;
#ifdef USE_SPECULARMAP
	vec4 texelSpecular = texture2D( specularMap, vSpecularMapUv );
	specularStrength = texelSpecular.r;
#else
	specularStrength = 1.0;
#endif`,kb=`#ifdef USE_SPECULARMAP
	uniform sampler2D specularMap;
#endif`,Lb=`#if defined( TONE_MAPPING )
	gl_FragColor.rgb = toneMapping( gl_FragColor.rgb );
#endif`,Db=`#ifndef saturate
#define saturate( a ) clamp( a, 0.0, 1.0 )
#endif
uniform float toneMappingExposure;
vec3 LinearToneMapping( vec3 color ) {
	return saturate( toneMappingExposure * color );
}
vec3 ReinhardToneMapping( vec3 color ) {
	color *= toneMappingExposure;
	return saturate( color / ( vec3( 1.0 ) + color ) );
}
vec3 CineonToneMapping( vec3 color ) {
	color *= toneMappingExposure;
	color = max( vec3( 0.0 ), color - 0.004 );
	return pow( ( color * ( 6.2 * color + 0.5 ) ) / ( color * ( 6.2 * color + 1.7 ) + 0.06 ), vec3( 2.2 ) );
}
vec3 RRTAndODTFit( vec3 v ) {
	vec3 a = v * ( v + 0.0245786 ) - 0.000090537;
	vec3 b = v * ( 0.983729 * v + 0.4329510 ) + 0.238081;
	return a / b;
}
vec3 ACESFilmicToneMapping( vec3 color ) {
	const mat3 ACESInputMat = mat3(
		vec3( 0.59719, 0.07600, 0.02840 ),		vec3( 0.35458, 0.90834, 0.13383 ),
		vec3( 0.04823, 0.01566, 0.83777 )
	);
	const mat3 ACESOutputMat = mat3(
		vec3(  1.60475, -0.10208, -0.00327 ),		vec3( -0.53108,  1.10813, -0.07276 ),
		vec3( -0.07367, -0.00605,  1.07602 )
	);
	color *= toneMappingExposure / 0.6;
	color = ACESInputMat * color;
	color = RRTAndODTFit( color );
	color = ACESOutputMat * color;
	return saturate( color );
}
const mat3 LINEAR_REC2020_TO_LINEAR_SRGB = mat3(
	vec3( 1.6605, - 0.1246, - 0.0182 ),
	vec3( - 0.5876, 1.1329, - 0.1006 ),
	vec3( - 0.0728, - 0.0083, 1.1187 )
);
const mat3 LINEAR_SRGB_TO_LINEAR_REC2020 = mat3(
	vec3( 0.6274, 0.0691, 0.0164 ),
	vec3( 0.3293, 0.9195, 0.0880 ),
	vec3( 0.0433, 0.0113, 0.8956 )
);
vec3 agxDefaultContrastApprox( vec3 x ) {
	vec3 x2 = x * x;
	vec3 x4 = x2 * x2;
	return + 15.5 * x4 * x2
		- 40.14 * x4 * x
		+ 31.96 * x4
		- 6.868 * x2 * x
		+ 0.4298 * x2
		+ 0.1191 * x
		- 0.00232;
}
vec3 AgXToneMapping( vec3 color ) {
	const mat3 AgXInsetMatrix = mat3(
		vec3( 0.856627153315983, 0.137318972929847, 0.11189821299995 ),
		vec3( 0.0951212405381588, 0.761241990602591, 0.0767994186031903 ),
		vec3( 0.0482516061458583, 0.101439036467562, 0.811302368396859 )
	);
	const mat3 AgXOutsetMatrix = mat3(
		vec3( 1.1271005818144368, - 0.1413297634984383, - 0.14132976349843826 ),
		vec3( - 0.11060664309660323, 1.157823702216272, - 0.11060664309660294 ),
		vec3( - 0.016493938717834573, - 0.016493938717834257, 1.2519364065950405 )
	);
	const float AgxMinEv = - 12.47393;	const float AgxMaxEv = 4.026069;
	color *= toneMappingExposure;
	color = LINEAR_SRGB_TO_LINEAR_REC2020 * color;
	color = AgXInsetMatrix * color;
	color = max( color, 1e-10 );	color = log2( color );
	color = ( color - AgxMinEv ) / ( AgxMaxEv - AgxMinEv );
	color = clamp( color, 0.0, 1.0 );
	color = agxDefaultContrastApprox( color );
	color = AgXOutsetMatrix * color;
	color = pow( max( vec3( 0.0 ), color ), vec3( 2.2 ) );
	color = LINEAR_REC2020_TO_LINEAR_SRGB * color;
	color = clamp( color, 0.0, 1.0 );
	return color;
}
vec3 NeutralToneMapping( vec3 color ) {
	const float StartCompression = 0.8 - 0.04;
	const float Desaturation = 0.15;
	color *= toneMappingExposure;
	float x = min( color.r, min( color.g, color.b ) );
	float offset = x < 0.08 ? x - 6.25 * x * x : 0.04;
	color -= offset;
	float peak = max( color.r, max( color.g, color.b ) );
	if ( peak < StartCompression ) return color;
	float d = 1. - StartCompression;
	float newPeak = 1. - d * d / ( peak + d - StartCompression );
	color *= newPeak / peak;
	float g = 1. - 1. / ( Desaturation * ( peak - newPeak ) + 1. );
	return mix( color, vec3( newPeak ), g );
}
vec3 CustomToneMapping( vec3 color ) { return color; }`,Nb=`#ifdef USE_TRANSMISSION
	material.transmission = transmission;
	material.transmissionAlpha = 1.0;
	material.thickness = thickness;
	material.attenuationDistance = attenuationDistance;
	material.attenuationColor = attenuationColor;
	#ifdef USE_TRANSMISSIONMAP
		material.transmission *= texture2D( transmissionMap, vTransmissionMapUv ).r;
	#endif
	#ifdef USE_THICKNESSMAP
		material.thickness *= texture2D( thicknessMap, vThicknessMapUv ).g;
	#endif
	vec3 pos = vWorldPosition;
	vec3 v = normalize( cameraPosition - pos );
	vec3 n = inverseTransformDirection( normal, viewMatrix );
	vec4 transmitted = getIBLVolumeRefraction(
		n, v, material.roughness, material.diffuseColor, material.specularColor, material.specularF90,
		pos, modelMatrix, viewMatrix, projectionMatrix, material.dispersion, material.ior, material.thickness,
		material.attenuationColor, material.attenuationDistance );
	material.transmissionAlpha = mix( material.transmissionAlpha, transmitted.a, material.transmission );
	totalDiffuse = mix( totalDiffuse, transmitted.rgb, material.transmission );
#endif`,Fb=`#ifdef USE_TRANSMISSION
	uniform float transmission;
	uniform float thickness;
	uniform float attenuationDistance;
	uniform vec3 attenuationColor;
	#ifdef USE_TRANSMISSIONMAP
		uniform sampler2D transmissionMap;
	#endif
	#ifdef USE_THICKNESSMAP
		uniform sampler2D thicknessMap;
	#endif
	uniform vec2 transmissionSamplerSize;
	uniform sampler2D transmissionSamplerMap;
	uniform mat4 modelMatrix;
	uniform mat4 projectionMatrix;
	varying vec3 vWorldPosition;
	float w0( float a ) {
		return ( 1.0 / 6.0 ) * ( a * ( a * ( - a + 3.0 ) - 3.0 ) + 1.0 );
	}
	float w1( float a ) {
		return ( 1.0 / 6.0 ) * ( a *  a * ( 3.0 * a - 6.0 ) + 4.0 );
	}
	float w2( float a ){
		return ( 1.0 / 6.0 ) * ( a * ( a * ( - 3.0 * a + 3.0 ) + 3.0 ) + 1.0 );
	}
	float w3( float a ) {
		return ( 1.0 / 6.0 ) * ( a * a * a );
	}
	float g0( float a ) {
		return w0( a ) + w1( a );
	}
	float g1( float a ) {
		return w2( a ) + w3( a );
	}
	float h0( float a ) {
		return - 1.0 + w1( a ) / ( w0( a ) + w1( a ) );
	}
	float h1( float a ) {
		return 1.0 + w3( a ) / ( w2( a ) + w3( a ) );
	}
	vec4 bicubic( sampler2D tex, vec2 uv, vec4 texelSize, float lod ) {
		uv = uv * texelSize.zw + 0.5;
		vec2 iuv = floor( uv );
		vec2 fuv = fract( uv );
		float g0x = g0( fuv.x );
		float g1x = g1( fuv.x );
		float h0x = h0( fuv.x );
		float h1x = h1( fuv.x );
		float h0y = h0( fuv.y );
		float h1y = h1( fuv.y );
		vec2 p0 = ( vec2( iuv.x + h0x, iuv.y + h0y ) - 0.5 ) * texelSize.xy;
		vec2 p1 = ( vec2( iuv.x + h1x, iuv.y + h0y ) - 0.5 ) * texelSize.xy;
		vec2 p2 = ( vec2( iuv.x + h0x, iuv.y + h1y ) - 0.5 ) * texelSize.xy;
		vec2 p3 = ( vec2( iuv.x + h1x, iuv.y + h1y ) - 0.5 ) * texelSize.xy;
		return g0( fuv.y ) * ( g0x * textureLod( tex, p0, lod ) + g1x * textureLod( tex, p1, lod ) ) +
			g1( fuv.y ) * ( g0x * textureLod( tex, p2, lod ) + g1x * textureLod( tex, p3, lod ) );
	}
	vec4 textureBicubic( sampler2D sampler, vec2 uv, float lod ) {
		vec2 fLodSize = vec2( textureSize( sampler, int( lod ) ) );
		vec2 cLodSize = vec2( textureSize( sampler, int( lod + 1.0 ) ) );
		vec2 fLodSizeInv = 1.0 / fLodSize;
		vec2 cLodSizeInv = 1.0 / cLodSize;
		vec4 fSample = bicubic( sampler, uv, vec4( fLodSizeInv, fLodSize ), floor( lod ) );
		vec4 cSample = bicubic( sampler, uv, vec4( cLodSizeInv, cLodSize ), ceil( lod ) );
		return mix( fSample, cSample, fract( lod ) );
	}
	vec3 getVolumeTransmissionRay( const in vec3 n, const in vec3 v, const in float thickness, const in float ior, const in mat4 modelMatrix ) {
		vec3 refractionVector = refract( - v, normalize( n ), 1.0 / ior );
		vec3 modelScale;
		modelScale.x = length( vec3( modelMatrix[ 0 ].xyz ) );
		modelScale.y = length( vec3( modelMatrix[ 1 ].xyz ) );
		modelScale.z = length( vec3( modelMatrix[ 2 ].xyz ) );
		return normalize( refractionVector ) * thickness * modelScale;
	}
	float applyIorToRoughness( const in float roughness, const in float ior ) {
		return roughness * clamp( ior * 2.0 - 2.0, 0.0, 1.0 );
	}
	vec4 getTransmissionSample( const in vec2 fragCoord, const in float roughness, const in float ior ) {
		float lod = log2( transmissionSamplerSize.x ) * applyIorToRoughness( roughness, ior );
		return textureBicubic( transmissionSamplerMap, fragCoord.xy, lod );
	}
	vec3 volumeAttenuation( const in float transmissionDistance, const in vec3 attenuationColor, const in float attenuationDistance ) {
		if ( isinf( attenuationDistance ) ) {
			return vec3( 1.0 );
		} else {
			vec3 attenuationCoefficient = -log( attenuationColor ) / attenuationDistance;
			vec3 transmittance = exp( - attenuationCoefficient * transmissionDistance );			return transmittance;
		}
	}
	vec4 getIBLVolumeRefraction( const in vec3 n, const in vec3 v, const in float roughness, const in vec3 diffuseColor,
		const in vec3 specularColor, const in float specularF90, const in vec3 position, const in mat4 modelMatrix,
		const in mat4 viewMatrix, const in mat4 projMatrix, const in float dispersion, const in float ior, const in float thickness,
		const in vec3 attenuationColor, const in float attenuationDistance ) {
		vec4 transmittedLight;
		vec3 transmittance;
		#ifdef USE_DISPERSION
			float halfSpread = ( ior - 1.0 ) * 0.025 * dispersion;
			vec3 iors = vec3( ior - halfSpread, ior, ior + halfSpread );
			for ( int i = 0; i < 3; i ++ ) {
				vec3 transmissionRay = getVolumeTransmissionRay( n, v, thickness, iors[ i ], modelMatrix );
				vec3 refractedRayExit = position + transmissionRay;
				vec4 ndcPos = projMatrix * viewMatrix * vec4( refractedRayExit, 1.0 );
				vec2 refractionCoords = ndcPos.xy / ndcPos.w;
				refractionCoords += 1.0;
				refractionCoords /= 2.0;
				vec4 transmissionSample = getTransmissionSample( refractionCoords, roughness, iors[ i ] );
				transmittedLight[ i ] = transmissionSample[ i ];
				transmittedLight.a += transmissionSample.a;
				transmittance[ i ] = diffuseColor[ i ] * volumeAttenuation( length( transmissionRay ), attenuationColor, attenuationDistance )[ i ];
			}
			transmittedLight.a /= 3.0;
		#else
			vec3 transmissionRay = getVolumeTransmissionRay( n, v, thickness, ior, modelMatrix );
			vec3 refractedRayExit = position + transmissionRay;
			vec4 ndcPos = projMatrix * viewMatrix * vec4( refractedRayExit, 1.0 );
			vec2 refractionCoords = ndcPos.xy / ndcPos.w;
			refractionCoords += 1.0;
			refractionCoords /= 2.0;
			transmittedLight = getTransmissionSample( refractionCoords, roughness, ior );
			transmittance = diffuseColor * volumeAttenuation( length( transmissionRay ), attenuationColor, attenuationDistance );
		#endif
		vec3 attenuatedColor = transmittance * transmittedLight.rgb;
		vec3 F = EnvironmentBRDF( n, v, specularColor, specularF90, roughness );
		float transmittanceFactor = ( transmittance.r + transmittance.g + transmittance.b ) / 3.0;
		return vec4( ( 1.0 - F ) * attenuatedColor, 1.0 - ( 1.0 - transmittedLight.a ) * transmittanceFactor );
	}
#endif`,Ub=`#if defined( USE_UV ) || defined( USE_ANISOTROPY )
	varying vec2 vUv;
#endif
#ifdef USE_MAP
	varying vec2 vMapUv;
#endif
#ifdef USE_ALPHAMAP
	varying vec2 vAlphaMapUv;
#endif
#ifdef USE_LIGHTMAP
	varying vec2 vLightMapUv;
#endif
#ifdef USE_AOMAP
	varying vec2 vAoMapUv;
#endif
#ifdef USE_BUMPMAP
	varying vec2 vBumpMapUv;
#endif
#ifdef USE_NORMALMAP
	varying vec2 vNormalMapUv;
#endif
#ifdef USE_EMISSIVEMAP
	varying vec2 vEmissiveMapUv;
#endif
#ifdef USE_METALNESSMAP
	varying vec2 vMetalnessMapUv;
#endif
#ifdef USE_ROUGHNESSMAP
	varying vec2 vRoughnessMapUv;
#endif
#ifdef USE_ANISOTROPYMAP
	varying vec2 vAnisotropyMapUv;
#endif
#ifdef USE_CLEARCOATMAP
	varying vec2 vClearcoatMapUv;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	varying vec2 vClearcoatNormalMapUv;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	varying vec2 vClearcoatRoughnessMapUv;
#endif
#ifdef USE_IRIDESCENCEMAP
	varying vec2 vIridescenceMapUv;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	varying vec2 vIridescenceThicknessMapUv;
#endif
#ifdef USE_SHEEN_COLORMAP
	varying vec2 vSheenColorMapUv;
#endif
#ifdef USE_SHEEN_ROUGHNESSMAP
	varying vec2 vSheenRoughnessMapUv;
#endif
#ifdef USE_SPECULARMAP
	varying vec2 vSpecularMapUv;
#endif
#ifdef USE_SPECULAR_COLORMAP
	varying vec2 vSpecularColorMapUv;
#endif
#ifdef USE_SPECULAR_INTENSITYMAP
	varying vec2 vSpecularIntensityMapUv;
#endif
#ifdef USE_TRANSMISSIONMAP
	uniform mat3 transmissionMapTransform;
	varying vec2 vTransmissionMapUv;
#endif
#ifdef USE_THICKNESSMAP
	uniform mat3 thicknessMapTransform;
	varying vec2 vThicknessMapUv;
#endif`,Bb=`#if defined( USE_UV ) || defined( USE_ANISOTROPY )
	varying vec2 vUv;
#endif
#ifdef USE_MAP
	uniform mat3 mapTransform;
	varying vec2 vMapUv;
#endif
#ifdef USE_ALPHAMAP
	uniform mat3 alphaMapTransform;
	varying vec2 vAlphaMapUv;
#endif
#ifdef USE_LIGHTMAP
	uniform mat3 lightMapTransform;
	varying vec2 vLightMapUv;
#endif
#ifdef USE_AOMAP
	uniform mat3 aoMapTransform;
	varying vec2 vAoMapUv;
#endif
#ifdef USE_BUMPMAP
	uniform mat3 bumpMapTransform;
	varying vec2 vBumpMapUv;
#endif
#ifdef USE_NORMALMAP
	uniform mat3 normalMapTransform;
	varying vec2 vNormalMapUv;
#endif
#ifdef USE_DISPLACEMENTMAP
	uniform mat3 displacementMapTransform;
	varying vec2 vDisplacementMapUv;
#endif
#ifdef USE_EMISSIVEMAP
	uniform mat3 emissiveMapTransform;
	varying vec2 vEmissiveMapUv;
#endif
#ifdef USE_METALNESSMAP
	uniform mat3 metalnessMapTransform;
	varying vec2 vMetalnessMapUv;
#endif
#ifdef USE_ROUGHNESSMAP
	uniform mat3 roughnessMapTransform;
	varying vec2 vRoughnessMapUv;
#endif
#ifdef USE_ANISOTROPYMAP
	uniform mat3 anisotropyMapTransform;
	varying vec2 vAnisotropyMapUv;
#endif
#ifdef USE_CLEARCOATMAP
	uniform mat3 clearcoatMapTransform;
	varying vec2 vClearcoatMapUv;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	uniform mat3 clearcoatNormalMapTransform;
	varying vec2 vClearcoatNormalMapUv;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	uniform mat3 clearcoatRoughnessMapTransform;
	varying vec2 vClearcoatRoughnessMapUv;
#endif
#ifdef USE_SHEEN_COLORMAP
	uniform mat3 sheenColorMapTransform;
	varying vec2 vSheenColorMapUv;
#endif
#ifdef USE_SHEEN_ROUGHNESSMAP
	uniform mat3 sheenRoughnessMapTransform;
	varying vec2 vSheenRoughnessMapUv;
#endif
#ifdef USE_IRIDESCENCEMAP
	uniform mat3 iridescenceMapTransform;
	varying vec2 vIridescenceMapUv;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	uniform mat3 iridescenceThicknessMapTransform;
	varying vec2 vIridescenceThicknessMapUv;
#endif
#ifdef USE_SPECULARMAP
	uniform mat3 specularMapTransform;
	varying vec2 vSpecularMapUv;
#endif
#ifdef USE_SPECULAR_COLORMAP
	uniform mat3 specularColorMapTransform;
	varying vec2 vSpecularColorMapUv;
#endif
#ifdef USE_SPECULAR_INTENSITYMAP
	uniform mat3 specularIntensityMapTransform;
	varying vec2 vSpecularIntensityMapUv;
#endif
#ifdef USE_TRANSMISSIONMAP
	uniform mat3 transmissionMapTransform;
	varying vec2 vTransmissionMapUv;
#endif
#ifdef USE_THICKNESSMAP
	uniform mat3 thicknessMapTransform;
	varying vec2 vThicknessMapUv;
#endif`,Ob=`#if defined( USE_UV ) || defined( USE_ANISOTROPY )
	vUv = vec3( uv, 1 ).xy;
#endif
#ifdef USE_MAP
	vMapUv = ( mapTransform * vec3( MAP_UV, 1 ) ).xy;
#endif
#ifdef USE_ALPHAMAP
	vAlphaMapUv = ( alphaMapTransform * vec3( ALPHAMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_LIGHTMAP
	vLightMapUv = ( lightMapTransform * vec3( LIGHTMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_AOMAP
	vAoMapUv = ( aoMapTransform * vec3( AOMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_BUMPMAP
	vBumpMapUv = ( bumpMapTransform * vec3( BUMPMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_NORMALMAP
	vNormalMapUv = ( normalMapTransform * vec3( NORMALMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_DISPLACEMENTMAP
	vDisplacementMapUv = ( displacementMapTransform * vec3( DISPLACEMENTMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_EMISSIVEMAP
	vEmissiveMapUv = ( emissiveMapTransform * vec3( EMISSIVEMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_METALNESSMAP
	vMetalnessMapUv = ( metalnessMapTransform * vec3( METALNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_ROUGHNESSMAP
	vRoughnessMapUv = ( roughnessMapTransform * vec3( ROUGHNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_ANISOTROPYMAP
	vAnisotropyMapUv = ( anisotropyMapTransform * vec3( ANISOTROPYMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_CLEARCOATMAP
	vClearcoatMapUv = ( clearcoatMapTransform * vec3( CLEARCOATMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	vClearcoatNormalMapUv = ( clearcoatNormalMapTransform * vec3( CLEARCOAT_NORMALMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	vClearcoatRoughnessMapUv = ( clearcoatRoughnessMapTransform * vec3( CLEARCOAT_ROUGHNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_IRIDESCENCEMAP
	vIridescenceMapUv = ( iridescenceMapTransform * vec3( IRIDESCENCEMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	vIridescenceThicknessMapUv = ( iridescenceThicknessMapTransform * vec3( IRIDESCENCE_THICKNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SHEEN_COLORMAP
	vSheenColorMapUv = ( sheenColorMapTransform * vec3( SHEEN_COLORMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SHEEN_ROUGHNESSMAP
	vSheenRoughnessMapUv = ( sheenRoughnessMapTransform * vec3( SHEEN_ROUGHNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SPECULARMAP
	vSpecularMapUv = ( specularMapTransform * vec3( SPECULARMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SPECULAR_COLORMAP
	vSpecularColorMapUv = ( specularColorMapTransform * vec3( SPECULAR_COLORMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SPECULAR_INTENSITYMAP
	vSpecularIntensityMapUv = ( specularIntensityMapTransform * vec3( SPECULAR_INTENSITYMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_TRANSMISSIONMAP
	vTransmissionMapUv = ( transmissionMapTransform * vec3( TRANSMISSIONMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_THICKNESSMAP
	vThicknessMapUv = ( thicknessMapTransform * vec3( THICKNESSMAP_UV, 1 ) ).xy;
#endif`,zb=`#if defined( USE_ENVMAP ) || defined( DISTANCE ) || defined ( USE_SHADOWMAP ) || defined ( USE_TRANSMISSION ) || NUM_SPOT_LIGHT_COORDS > 0
	vec4 worldPosition = vec4( transformed, 1.0 );
	#ifdef USE_BATCHING
		worldPosition = batchingMatrix * worldPosition;
	#endif
	#ifdef USE_INSTANCING
		worldPosition = instanceMatrix * worldPosition;
	#endif
	worldPosition = modelMatrix * worldPosition;
#endif`,Hb=`varying vec2 vUv;
uniform mat3 uvTransform;
void main() {
	vUv = ( uvTransform * vec3( uv, 1 ) ).xy;
	gl_Position = vec4( position.xy, 1.0, 1.0 );
}`,Vb=`uniform sampler2D t2D;
uniform float backgroundIntensity;
varying vec2 vUv;
void main() {
	vec4 texColor = texture2D( t2D, vUv );
	#ifdef DECODE_VIDEO_TEXTURE
		texColor = vec4( mix( pow( texColor.rgb * 0.9478672986 + vec3( 0.0521327014 ), vec3( 2.4 ) ), texColor.rgb * 0.0773993808, vec3( lessThanEqual( texColor.rgb, vec3( 0.04045 ) ) ) ), texColor.w );
	#endif
	texColor.rgb *= backgroundIntensity;
	gl_FragColor = texColor;
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,Gb=`varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
	gl_Position.z = gl_Position.w;
}`,Wb=`#ifdef ENVMAP_TYPE_CUBE
	uniform samplerCube envMap;
#elif defined( ENVMAP_TYPE_CUBE_UV )
	uniform sampler2D envMap;
#endif
uniform float flipEnvMap;
uniform float backgroundBlurriness;
uniform float backgroundIntensity;
uniform mat3 backgroundRotation;
varying vec3 vWorldDirection;
#include <cube_uv_reflection_fragment>
void main() {
	#ifdef ENVMAP_TYPE_CUBE
		vec4 texColor = textureCube( envMap, backgroundRotation * vec3( flipEnvMap * vWorldDirection.x, vWorldDirection.yz ) );
	#elif defined( ENVMAP_TYPE_CUBE_UV )
		vec4 texColor = textureCubeUV( envMap, backgroundRotation * vWorldDirection, backgroundBlurriness );
	#else
		vec4 texColor = vec4( 0.0, 0.0, 0.0, 1.0 );
	#endif
	texColor.rgb *= backgroundIntensity;
	gl_FragColor = texColor;
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,Yb=`varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
	gl_Position.z = gl_Position.w;
}`,Xb=`uniform samplerCube tCube;
uniform float tFlip;
uniform float opacity;
varying vec3 vWorldDirection;
void main() {
	vec4 texColor = textureCube( tCube, vec3( tFlip * vWorldDirection.x, vWorldDirection.yz ) );
	gl_FragColor = texColor;
	gl_FragColor.a *= opacity;
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,qb=`#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
varying vec2 vHighPrecisionZW;
void main() {
	#include <uv_vertex>
	#include <batching_vertex>
	#include <skinbase_vertex>
	#include <morphinstance_vertex>
	#ifdef USE_DISPLACEMENTMAP
		#include <beginnormal_vertex>
		#include <morphnormal_vertex>
		#include <skinnormal_vertex>
	#endif
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vHighPrecisionZW = gl_Position.zw;
}`,jb=`#if DEPTH_PACKING == 3200
	uniform float opacity;
#endif
#include <common>
#include <packing>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
varying vec2 vHighPrecisionZW;
void main() {
	vec4 diffuseColor = vec4( 1.0 );
	#include <clipping_planes_fragment>
	#if DEPTH_PACKING == 3200
		diffuseColor.a = opacity;
	#endif
	#include <map_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <logdepthbuf_fragment>
	#ifdef USE_REVERSED_DEPTH_BUFFER
		float fragCoordZ = vHighPrecisionZW[ 0 ] / vHighPrecisionZW[ 1 ];
	#else
		float fragCoordZ = 0.5 * vHighPrecisionZW[ 0 ] / vHighPrecisionZW[ 1 ] + 0.5;
	#endif
	#if DEPTH_PACKING == 3200
		gl_FragColor = vec4( vec3( 1.0 - fragCoordZ ), opacity );
	#elif DEPTH_PACKING == 3201
		gl_FragColor = packDepthToRGBA( fragCoordZ );
	#elif DEPTH_PACKING == 3202
		gl_FragColor = vec4( packDepthToRGB( fragCoordZ ), 1.0 );
	#elif DEPTH_PACKING == 3203
		gl_FragColor = vec4( packDepthToRG( fragCoordZ ), 0.0, 1.0 );
	#endif
}`,Kb=`#define DISTANCE
varying vec3 vWorldPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <batching_vertex>
	#include <skinbase_vertex>
	#include <morphinstance_vertex>
	#ifdef USE_DISPLACEMENTMAP
		#include <beginnormal_vertex>
		#include <morphnormal_vertex>
		#include <skinnormal_vertex>
	#endif
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <worldpos_vertex>
	#include <clipping_planes_vertex>
	vWorldPosition = worldPosition.xyz;
}`,Zb=`#define DISTANCE
uniform vec3 referencePosition;
uniform float nearDistance;
uniform float farDistance;
varying vec3 vWorldPosition;
#include <common>
#include <packing>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <clipping_planes_pars_fragment>
void main () {
	vec4 diffuseColor = vec4( 1.0 );
	#include <clipping_planes_fragment>
	#include <map_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	float dist = length( vWorldPosition - referencePosition );
	dist = ( dist - nearDistance ) / ( farDistance - nearDistance );
	dist = saturate( dist );
	gl_FragColor = packDepthToRGBA( dist );
}`,Jb=`varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
}`,$b=`uniform sampler2D tEquirect;
varying vec3 vWorldDirection;
#include <common>
void main() {
	vec3 direction = normalize( vWorldDirection );
	vec2 sampleUV = equirectUv( direction );
	gl_FragColor = texture2D( tEquirect, sampleUV );
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,Qb=`uniform float scale;
attribute float lineDistance;
varying float vLineDistance;
#include <common>
#include <uv_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	vLineDistance = scale * lineDistance;
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <fog_vertex>
}`,ey=`uniform vec3 diffuse;
uniform float opacity;
uniform float dashSize;
uniform float totalSize;
varying float vLineDistance;
#include <common>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <fog_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	if ( mod( vLineDistance, totalSize ) > dashSize ) {
		discard;
	}
	vec3 outgoingLight = vec3( 0.0 );
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	outgoingLight = diffuseColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
}`,ty=`#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <envmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#if defined ( USE_ENVMAP ) || defined ( USE_SKINNING )
		#include <beginnormal_vertex>
		#include <morphnormal_vertex>
		#include <skinbase_vertex>
		#include <skinnormal_vertex>
		#include <defaultnormal_vertex>
	#endif
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <worldpos_vertex>
	#include <envmap_vertex>
	#include <fog_vertex>
}`,ny=`uniform vec3 diffuse;
uniform float opacity;
#ifndef FLAT_SHADED
	varying vec3 vNormal;
#endif
#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_pars_fragment>
#include <fog_pars_fragment>
#include <specularmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <specularmap_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	#ifdef USE_LIGHTMAP
		vec4 lightMapTexel = texture2D( lightMap, vLightMapUv );
		reflectedLight.indirectDiffuse += lightMapTexel.rgb * lightMapIntensity * RECIPROCAL_PI;
	#else
		reflectedLight.indirectDiffuse += vec3( 1.0 );
	#endif
	#include <aomap_fragment>
	reflectedLight.indirectDiffuse *= diffuseColor.rgb;
	vec3 outgoingLight = reflectedLight.indirectDiffuse;
	#include <envmap_fragment>
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,iy=`#define LAMBERT
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <envmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <envmap_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`,sy=`#define LAMBERT
uniform vec3 diffuse;
uniform vec3 emissive;
uniform float opacity;
#include <common>
#include <packing>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_pars_fragment>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_lambert_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <specularmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <specularmap_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_lambert_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + totalEmissiveRadiance;
	#include <envmap_fragment>
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,ry=`#define MATCAP
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <color_pars_vertex>
#include <displacementmap_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <fog_vertex>
	vViewPosition = - mvPosition.xyz;
}`,ay=`#define MATCAP
uniform vec3 diffuse;
uniform float opacity;
uniform sampler2D matcap;
varying vec3 vViewPosition;
#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <fog_pars_fragment>
#include <normal_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	vec3 viewDir = normalize( vViewPosition );
	vec3 x = normalize( vec3( viewDir.z, 0.0, - viewDir.x ) );
	vec3 y = cross( viewDir, x );
	vec2 uv = vec2( dot( x, normal ), dot( y, normal ) ) * 0.495 + 0.5;
	#ifdef USE_MATCAP
		vec4 matcapColor = texture2D( matcap, uv );
	#else
		vec4 matcapColor = vec4( vec3( mix( 0.2, 0.8, uv.y ) ), 1.0 );
	#endif
	vec3 outgoingLight = diffuseColor.rgb * matcapColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,oy=`#define NORMAL
#if defined( FLAT_SHADED ) || defined( USE_BUMPMAP ) || defined( USE_NORMALMAP_TANGENTSPACE )
	varying vec3 vViewPosition;
#endif
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphinstance_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
#if defined( FLAT_SHADED ) || defined( USE_BUMPMAP ) || defined( USE_NORMALMAP_TANGENTSPACE )
	vViewPosition = - mvPosition.xyz;
#endif
}`,cy=`#define NORMAL
uniform float opacity;
#if defined( FLAT_SHADED ) || defined( USE_BUMPMAP ) || defined( USE_NORMALMAP_TANGENTSPACE )
	varying vec3 vViewPosition;
#endif
#include <packing>
#include <uv_pars_fragment>
#include <normal_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( 0.0, 0.0, 0.0, opacity );
	#include <clipping_planes_fragment>
	#include <logdepthbuf_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	gl_FragColor = vec4( packNormalToRGB( normal ), diffuseColor.a );
	#ifdef OPAQUE
		gl_FragColor.a = 1.0;
	#endif
}`,ly=`#define PHONG
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <envmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphinstance_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <envmap_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`,hy=`#define PHONG
uniform vec3 diffuse;
uniform vec3 emissive;
uniform vec3 specular;
uniform float shininess;
uniform float opacity;
#include <common>
#include <packing>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_pars_fragment>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_phong_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <specularmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <specularmap_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_phong_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + reflectedLight.directSpecular + reflectedLight.indirectSpecular + totalEmissiveRadiance;
	#include <envmap_fragment>
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,uy=`#define STANDARD
varying vec3 vViewPosition;
#ifdef USE_TRANSMISSION
	varying vec3 vWorldPosition;
#endif
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
#ifdef USE_TRANSMISSION
	vWorldPosition = worldPosition.xyz;
#endif
}`,dy=`#define STANDARD
#ifdef PHYSICAL
	#define IOR
	#define USE_SPECULAR
#endif
uniform vec3 diffuse;
uniform vec3 emissive;
uniform float roughness;
uniform float metalness;
uniform float opacity;
#ifdef IOR
	uniform float ior;
#endif
#ifdef USE_SPECULAR
	uniform float specularIntensity;
	uniform vec3 specularColor;
	#ifdef USE_SPECULAR_COLORMAP
		uniform sampler2D specularColorMap;
	#endif
	#ifdef USE_SPECULAR_INTENSITYMAP
		uniform sampler2D specularIntensityMap;
	#endif
#endif
#ifdef USE_CLEARCOAT
	uniform float clearcoat;
	uniform float clearcoatRoughness;
#endif
#ifdef USE_DISPERSION
	uniform float dispersion;
#endif
#ifdef USE_IRIDESCENCE
	uniform float iridescence;
	uniform float iridescenceIOR;
	uniform float iridescenceThicknessMinimum;
	uniform float iridescenceThicknessMaximum;
#endif
#ifdef USE_SHEEN
	uniform vec3 sheenColor;
	uniform float sheenRoughness;
	#ifdef USE_SHEEN_COLORMAP
		uniform sampler2D sheenColorMap;
	#endif
	#ifdef USE_SHEEN_ROUGHNESSMAP
		uniform sampler2D sheenRoughnessMap;
	#endif
#endif
#ifdef USE_ANISOTROPY
	uniform vec2 anisotropyVector;
	#ifdef USE_ANISOTROPYMAP
		uniform sampler2D anisotropyMap;
	#endif
#endif
varying vec3 vViewPosition;
#include <common>
#include <packing>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <iridescence_fragment>
#include <cube_uv_reflection_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_physical_pars_fragment>
#include <fog_pars_fragment>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_physical_pars_fragment>
#include <transmission_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <clearcoat_pars_fragment>
#include <iridescence_pars_fragment>
#include <roughnessmap_pars_fragment>
#include <metalnessmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <roughnessmap_fragment>
	#include <metalnessmap_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <clearcoat_normal_fragment_begin>
	#include <clearcoat_normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_physical_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 totalDiffuse = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse;
	vec3 totalSpecular = reflectedLight.directSpecular + reflectedLight.indirectSpecular;
	#include <transmission_fragment>
	vec3 outgoingLight = totalDiffuse + totalSpecular + totalEmissiveRadiance;
	#ifdef USE_SHEEN
		float sheenEnergyComp = 1.0 - 0.157 * max3( material.sheenColor );
		outgoingLight = outgoingLight * sheenEnergyComp + sheenSpecularDirect + sheenSpecularIndirect;
	#endif
	#ifdef USE_CLEARCOAT
		float dotNVcc = saturate( dot( geometryClearcoatNormal, geometryViewDir ) );
		vec3 Fcc = F_Schlick( material.clearcoatF0, material.clearcoatF90, dotNVcc );
		outgoingLight = outgoingLight * ( 1.0 - material.clearcoat * Fcc ) + ( clearcoatSpecularDirect + clearcoatSpecularIndirect ) * material.clearcoat;
	#endif
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,fy=`#define TOON
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`,py=`#define TOON
uniform vec3 diffuse;
uniform vec3 emissive;
uniform float opacity;
#include <common>
#include <packing>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <gradientmap_pars_fragment>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_toon_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_toon_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + totalEmissiveRadiance;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,my=`uniform float size;
uniform float scale;
#include <common>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
#ifdef USE_POINTS_UV
	varying vec2 vUv;
	uniform mat3 uvTransform;
#endif
void main() {
	#ifdef USE_POINTS_UV
		vUv = ( uvTransform * vec3( uv, 1 ) ).xy;
	#endif
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <project_vertex>
	gl_PointSize = size;
	#ifdef USE_SIZEATTENUATION
		bool isPerspective = isPerspectiveMatrix( projectionMatrix );
		if ( isPerspective ) gl_PointSize *= ( scale / - mvPosition.z );
	#endif
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <worldpos_vertex>
	#include <fog_vertex>
}`,gy=`uniform vec3 diffuse;
uniform float opacity;
#include <common>
#include <color_pars_fragment>
#include <map_particle_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <fog_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	vec3 outgoingLight = vec3( 0.0 );
	#include <logdepthbuf_fragment>
	#include <map_particle_fragment>
	#include <color_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	outgoingLight = diffuseColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
}`,by=`#include <common>
#include <batching_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <shadowmap_pars_vertex>
void main() {
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphinstance_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <worldpos_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`,yy=`uniform vec3 color;
uniform float opacity;
#include <common>
#include <packing>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <logdepthbuf_pars_fragment>
#include <shadowmap_pars_fragment>
#include <shadowmask_pars_fragment>
void main() {
	#include <logdepthbuf_fragment>
	gl_FragColor = vec4( color, opacity * ( 1.0 - getShadowMask() ) );
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
}`,xy=`uniform float rotation;
uniform vec2 center;
#include <common>
#include <uv_pars_vertex>
#include <fog_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	vec4 mvPosition = modelViewMatrix[ 3 ];
	vec2 scale = vec2( length( modelMatrix[ 0 ].xyz ), length( modelMatrix[ 1 ].xyz ) );
	#ifndef USE_SIZEATTENUATION
		bool isPerspective = isPerspectiveMatrix( projectionMatrix );
		if ( isPerspective ) scale *= - mvPosition.z;
	#endif
	vec2 alignedPosition = ( position.xy - ( center - vec2( 0.5 ) ) ) * scale;
	vec2 rotatedPosition;
	rotatedPosition.x = cos( rotation ) * alignedPosition.x - sin( rotation ) * alignedPosition.y;
	rotatedPosition.y = sin( rotation ) * alignedPosition.x + cos( rotation ) * alignedPosition.y;
	mvPosition.xy += rotatedPosition;
	gl_Position = projectionMatrix * mvPosition;
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <fog_vertex>
}`,vy=`uniform vec3 diffuse;
uniform float opacity;
#include <common>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <fog_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	vec3 outgoingLight = vec3( 0.0 );
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	outgoingLight = diffuseColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
}`,Ke={alphahash_fragment:Vg,alphahash_pars_fragment:Gg,alphamap_fragment:Wg,alphamap_pars_fragment:Yg,alphatest_fragment:Xg,alphatest_pars_fragment:qg,aomap_fragment:jg,aomap_pars_fragment:Kg,batching_pars_vertex:Zg,batching_vertex:Jg,begin_vertex:$g,beginnormal_vertex:Qg,bsdfs:e0,iridescence_fragment:t0,bumpmap_pars_fragment:n0,clipping_planes_fragment:i0,clipping_planes_pars_fragment:s0,clipping_planes_pars_vertex:r0,clipping_planes_vertex:a0,color_fragment:o0,color_pars_fragment:c0,color_pars_vertex:l0,color_vertex:h0,common:u0,cube_uv_reflection_fragment:d0,defaultnormal_vertex:f0,displacementmap_pars_vertex:p0,displacementmap_vertex:m0,emissivemap_fragment:g0,emissivemap_pars_fragment:b0,colorspace_fragment:y0,colorspace_pars_fragment:x0,envmap_fragment:v0,envmap_common_pars_fragment:_0,envmap_pars_fragment:w0,envmap_pars_vertex:M0,envmap_physical_pars_fragment:D0,envmap_vertex:S0,fog_vertex:T0,fog_pars_vertex:E0,fog_fragment:A0,fog_pars_fragment:R0,gradientmap_pars_fragment:C0,lightmap_pars_fragment:I0,lights_lambert_fragment:P0,lights_lambert_pars_fragment:k0,lights_pars_begin:L0,lights_toon_fragment:N0,lights_toon_pars_fragment:F0,lights_phong_fragment:U0,lights_phong_pars_fragment:B0,lights_physical_fragment:O0,lights_physical_pars_fragment:z0,lights_fragment_begin:H0,lights_fragment_maps:V0,lights_fragment_end:G0,logdepthbuf_fragment:W0,logdepthbuf_pars_fragment:Y0,logdepthbuf_pars_vertex:X0,logdepthbuf_vertex:q0,map_fragment:j0,map_pars_fragment:K0,map_particle_fragment:Z0,map_particle_pars_fragment:J0,metalnessmap_fragment:$0,metalnessmap_pars_fragment:Q0,morphinstance_vertex:eb,morphcolor_vertex:tb,morphnormal_vertex:nb,morphtarget_pars_vertex:ib,morphtarget_vertex:sb,normal_fragment_begin:rb,normal_fragment_maps:ab,normal_pars_fragment:ob,normal_pars_vertex:cb,normal_vertex:lb,normalmap_pars_fragment:hb,clearcoat_normal_fragment_begin:ub,clearcoat_normal_fragment_maps:db,clearcoat_pars_fragment:fb,iridescence_pars_fragment:pb,opaque_fragment:mb,packing:gb,premultiplied_alpha_fragment:bb,project_vertex:yb,dithering_fragment:xb,dithering_pars_fragment:vb,roughnessmap_fragment:_b,roughnessmap_pars_fragment:wb,shadowmap_pars_fragment:Mb,shadowmap_pars_vertex:Sb,shadowmap_vertex:Tb,shadowmask_pars_fragment:Eb,skinbase_vertex:Ab,skinning_pars_vertex:Rb,skinning_vertex:Cb,skinnormal_vertex:Ib,specularmap_fragment:Pb,specularmap_pars_fragment:kb,tonemapping_fragment:Lb,tonemapping_pars_fragment:Db,transmission_fragment:Nb,transmission_pars_fragment:Fb,uv_pars_fragment:Ub,uv_pars_vertex:Bb,uv_vertex:Ob,worldpos_vertex:zb,background_vert:Hb,background_frag:Vb,backgroundCube_vert:Gb,backgroundCube_frag:Wb,cube_vert:Yb,cube_frag:Xb,depth_vert:qb,depth_frag:jb,distanceRGBA_vert:Kb,distanceRGBA_frag:Zb,equirect_vert:Jb,equirect_frag:$b,linedashed_vert:Qb,linedashed_frag:ey,meshbasic_vert:ty,meshbasic_frag:ny,meshlambert_vert:iy,meshlambert_frag:sy,meshmatcap_vert:ry,meshmatcap_frag:ay,meshnormal_vert:oy,meshnormal_frag:cy,meshphong_vert:ly,meshphong_frag:hy,meshphysical_vert:uy,meshphysical_frag:dy,meshtoon_vert:fy,meshtoon_frag:py,points_vert:my,points_frag:gy,shadow_vert:by,shadow_frag:yy,sprite_vert:xy,sprite_frag:vy},be={common:{diffuse:{value:new Ue(16777215)},opacity:{value:1},map:{value:null},mapTransform:{value:new qe},alphaMap:{value:null},alphaMapTransform:{value:new qe},alphaTest:{value:0}},specularmap:{specularMap:{value:null},specularMapTransform:{value:new qe}},envmap:{envMap:{value:null},envMapRotation:{value:new qe},flipEnvMap:{value:-1},reflectivity:{value:1},ior:{value:1.5},refractionRatio:{value:.98}},aomap:{aoMap:{value:null},aoMapIntensity:{value:1},aoMapTransform:{value:new qe}},lightmap:{lightMap:{value:null},lightMapIntensity:{value:1},lightMapTransform:{value:new qe}},bumpmap:{bumpMap:{value:null},bumpMapTransform:{value:new qe},bumpScale:{value:1}},normalmap:{normalMap:{value:null},normalMapTransform:{value:new qe},normalScale:{value:new Ne(1,1)}},displacementmap:{displacementMap:{value:null},displacementMapTransform:{value:new qe},displacementScale:{value:1},displacementBias:{value:0}},emissivemap:{emissiveMap:{value:null},emissiveMapTransform:{value:new qe}},metalnessmap:{metalnessMap:{value:null},metalnessMapTransform:{value:new qe}},roughnessmap:{roughnessMap:{value:null},roughnessMapTransform:{value:new qe}},gradientmap:{gradientMap:{value:null}},fog:{fogDensity:{value:25e-5},fogNear:{value:1},fogFar:{value:2e3},fogColor:{value:new Ue(16777215)}},lights:{ambientLightColor:{value:[]},lightProbe:{value:[]},directionalLights:{value:[],properties:{direction:{},color:{}}},directionalLightShadows:{value:[],properties:{shadowIntensity:1,shadowBias:{},shadowNormalBias:{},shadowRadius:{},shadowMapSize:{}}},directionalShadowMap:{value:[]},directionalShadowMatrix:{value:[]},spotLights:{value:[],properties:{color:{},position:{},direction:{},distance:{},coneCos:{},penumbraCos:{},decay:{}}},spotLightShadows:{value:[],properties:{shadowIntensity:1,shadowBias:{},shadowNormalBias:{},shadowRadius:{},shadowMapSize:{}}},spotLightMap:{value:[]},spotShadowMap:{value:[]},spotLightMatrix:{value:[]},pointLights:{value:[],properties:{color:{},position:{},decay:{},distance:{}}},pointLightShadows:{value:[],properties:{shadowIntensity:1,shadowBias:{},shadowNormalBias:{},shadowRadius:{},shadowMapSize:{},shadowCameraNear:{},shadowCameraFar:{}}},pointShadowMap:{value:[]},pointShadowMatrix:{value:[]},hemisphereLights:{value:[],properties:{direction:{},skyColor:{},groundColor:{}}},rectAreaLights:{value:[],properties:{color:{},position:{},width:{},height:{}}},ltc_1:{value:null},ltc_2:{value:null}},points:{diffuse:{value:new Ue(16777215)},opacity:{value:1},size:{value:1},scale:{value:1},map:{value:null},alphaMap:{value:null},alphaMapTransform:{value:new qe},alphaTest:{value:0},uvTransform:{value:new qe}},sprite:{diffuse:{value:new Ue(16777215)},opacity:{value:1},center:{value:new Ne(.5,.5)},rotation:{value:0},map:{value:null},mapTransform:{value:new qe},alphaMap:{value:null},alphaMapTransform:{value:new qe},alphaTest:{value:0}}},ai={basic:{uniforms:sn([be.common,be.specularmap,be.envmap,be.aomap,be.lightmap,be.fog]),vertexShader:Ke.meshbasic_vert,fragmentShader:Ke.meshbasic_frag},lambert:{uniforms:sn([be.common,be.specularmap,be.envmap,be.aomap,be.lightmap,be.emissivemap,be.bumpmap,be.normalmap,be.displacementmap,be.fog,be.lights,{emissive:{value:new Ue(0)}}]),vertexShader:Ke.meshlambert_vert,fragmentShader:Ke.meshlambert_frag},phong:{uniforms:sn([be.common,be.specularmap,be.envmap,be.aomap,be.lightmap,be.emissivemap,be.bumpmap,be.normalmap,be.displacementmap,be.fog,be.lights,{emissive:{value:new Ue(0)},specular:{value:new Ue(1118481)},shininess:{value:30}}]),vertexShader:Ke.meshphong_vert,fragmentShader:Ke.meshphong_frag},standard:{uniforms:sn([be.common,be.envmap,be.aomap,be.lightmap,be.emissivemap,be.bumpmap,be.normalmap,be.displacementmap,be.roughnessmap,be.metalnessmap,be.fog,be.lights,{emissive:{value:new Ue(0)},roughness:{value:1},metalness:{value:0},envMapIntensity:{value:1}}]),vertexShader:Ke.meshphysical_vert,fragmentShader:Ke.meshphysical_frag},toon:{uniforms:sn([be.common,be.aomap,be.lightmap,be.emissivemap,be.bumpmap,be.normalmap,be.displacementmap,be.gradientmap,be.fog,be.lights,{emissive:{value:new Ue(0)}}]),vertexShader:Ke.meshtoon_vert,fragmentShader:Ke.meshtoon_frag},matcap:{uniforms:sn([be.common,be.bumpmap,be.normalmap,be.displacementmap,be.fog,{matcap:{value:null}}]),vertexShader:Ke.meshmatcap_vert,fragmentShader:Ke.meshmatcap_frag},points:{uniforms:sn([be.points,be.fog]),vertexShader:Ke.points_vert,fragmentShader:Ke.points_frag},dashed:{uniforms:sn([be.common,be.fog,{scale:{value:1},dashSize:{value:1},totalSize:{value:2}}]),vertexShader:Ke.linedashed_vert,fragmentShader:Ke.linedashed_frag},depth:{uniforms:sn([be.common,be.displacementmap]),vertexShader:Ke.depth_vert,fragmentShader:Ke.depth_frag},normal:{uniforms:sn([be.common,be.bumpmap,be.normalmap,be.displacementmap,{opacity:{value:1}}]),vertexShader:Ke.meshnormal_vert,fragmentShader:Ke.meshnormal_frag},sprite:{uniforms:sn([be.sprite,be.fog]),vertexShader:Ke.sprite_vert,fragmentShader:Ke.sprite_frag},background:{uniforms:{uvTransform:{value:new qe},t2D:{value:null},backgroundIntensity:{value:1}},vertexShader:Ke.background_vert,fragmentShader:Ke.background_frag},backgroundCube:{uniforms:{envMap:{value:null},flipEnvMap:{value:-1},backgroundBlurriness:{value:0},backgroundIntensity:{value:1},backgroundRotation:{value:new qe}},vertexShader:Ke.backgroundCube_vert,fragmentShader:Ke.backgroundCube_frag},cube:{uniforms:{tCube:{value:null},tFlip:{value:-1},opacity:{value:1}},vertexShader:Ke.cube_vert,fragmentShader:Ke.cube_frag},equirect:{uniforms:{tEquirect:{value:null}},vertexShader:Ke.equirect_vert,fragmentShader:Ke.equirect_frag},distanceRGBA:{uniforms:sn([be.common,be.displacementmap,{referencePosition:{value:new L},nearDistance:{value:1},farDistance:{value:1e3}}]),vertexShader:Ke.distanceRGBA_vert,fragmentShader:Ke.distanceRGBA_frag},shadow:{uniforms:sn([be.lights,be.fog,{color:{value:new Ue(0)},opacity:{value:1}}]),vertexShader:Ke.shadow_vert,fragmentShader:Ke.shadow_frag}};ai.physical={uniforms:sn([ai.standard.uniforms,{clearcoat:{value:0},clearcoatMap:{value:null},clearcoatMapTransform:{value:new qe},clearcoatNormalMap:{value:null},clearcoatNormalMapTransform:{value:new qe},clearcoatNormalScale:{value:new Ne(1,1)},clearcoatRoughness:{value:0},clearcoatRoughnessMap:{value:null},clearcoatRoughnessMapTransform:{value:new qe},dispersion:{value:0},iridescence:{value:0},iridescenceMap:{value:null},iridescenceMapTransform:{value:new qe},iridescenceIOR:{value:1.3},iridescenceThicknessMinimum:{value:100},iridescenceThicknessMaximum:{value:400},iridescenceThicknessMap:{value:null},iridescenceThicknessMapTransform:{value:new qe},sheen:{value:0},sheenColor:{value:new Ue(0)},sheenColorMap:{value:null},sheenColorMapTransform:{value:new qe},sheenRoughness:{value:1},sheenRoughnessMap:{value:null},sheenRoughnessMapTransform:{value:new qe},transmission:{value:0},transmissionMap:{value:null},transmissionMapTransform:{value:new qe},transmissionSamplerSize:{value:new Ne},transmissionSamplerMap:{value:null},thickness:{value:0},thicknessMap:{value:null},thicknessMapTransform:{value:new qe},attenuationDistance:{value:0},attenuationColor:{value:new Ue(0)},specularColor:{value:new Ue(1,1,1)},specularColorMap:{value:null},specularColorMapTransform:{value:new qe},specularIntensity:{value:1},specularIntensityMap:{value:null},specularIntensityMapTransform:{value:new qe},anisotropyVector:{value:new Ne},anisotropyMap:{value:null},anisotropyMapTransform:{value:new qe}}]),vertexShader:Ke.meshphysical_vert,fragmentShader:Ke.meshphysical_frag};var Uc={r:0,b:0,g:0},bs=new Dn,_y=new ke;function wy(s,e,t,n,i,r,a){let o=new Ue(0),c=r===!0?0:1,l,u,h=null,d=0,f=null;function g(v){let b=v.isScene===!0?v.background:null;return b&&b.isTexture&&(b=(v.backgroundBlurriness>0?t:e).get(b)),b}function y(v){let b=!1,S=g(v);S===null?p(o,c):S&&S.isColor&&(p(S,1),b=!0);let w=s.xr.getEnvironmentBlendMode();w==="additive"?n.buffers.color.setClear(0,0,0,1,a):w==="alpha-blend"&&n.buffers.color.setClear(0,0,0,0,a),(s.autoClear||b)&&(n.buffers.depth.setTest(!0),n.buffers.depth.setMask(!0),n.buffers.color.setMask(!0),s.clear(s.autoClearColor,s.autoClearDepth,s.autoClearStencil))}function m(v,b){let S=g(b);S&&(S.isCubeTexture||S.mapping===Sa)?(u===void 0&&(u=new at(new Xn(1,1,1),new Yt({name:"BackgroundCubeMaterial",uniforms:gs(ai.backgroundCube.uniforms),vertexShader:ai.backgroundCube.vertexShader,fragmentShader:ai.backgroundCube.fragmentShader,side:Dt,depthTest:!1,depthWrite:!1,fog:!1,allowOverride:!1})),u.geometry.deleteAttribute("normal"),u.geometry.deleteAttribute("uv"),u.onBeforeRender=function(w,T,A){this.matrixWorld.copyPosition(A.matrixWorld)},Object.defineProperty(u.material,"envMap",{get:function(){return this.uniforms.envMap.value}}),i.update(u)),bs.copy(b.backgroundRotation),bs.x*=-1,bs.y*=-1,bs.z*=-1,S.isCubeTexture&&S.isRenderTargetTexture===!1&&(bs.y*=-1,bs.z*=-1),u.material.uniforms.envMap.value=S,u.material.uniforms.flipEnvMap.value=S.isCubeTexture&&S.isRenderTargetTexture===!1?-1:1,u.material.uniforms.backgroundBlurriness.value=b.backgroundBlurriness,u.material.uniforms.backgroundIntensity.value=b.backgroundIntensity,u.material.uniforms.backgroundRotation.value.setFromMatrix4(_y.makeRotationFromEuler(bs)),u.material.toneMapped=et.getTransfer(S.colorSpace)!==pt,(h!==S||d!==S.version||f!==s.toneMapping)&&(u.material.needsUpdate=!0,h=S,d=S.version,f=s.toneMapping),u.layers.enableAll(),v.unshift(u,u.geometry,u.material,0,0,null)):S&&S.isTexture&&(l===void 0&&(l=new at(new Bi(2,2),new Yt({name:"BackgroundMaterial",uniforms:gs(ai.background.uniforms),vertexShader:ai.background.vertexShader,fragmentShader:ai.background.fragmentShader,side:pn,depthTest:!1,depthWrite:!1,fog:!1,allowOverride:!1})),l.geometry.deleteAttribute("normal"),Object.defineProperty(l.material,"map",{get:function(){return this.uniforms.t2D.value}}),i.update(l)),l.material.uniforms.t2D.value=S,l.material.uniforms.backgroundIntensity.value=b.backgroundIntensity,l.material.toneMapped=et.getTransfer(S.colorSpace)!==pt,S.matrixAutoUpdate===!0&&S.updateMatrix(),l.material.uniforms.uvTransform.value.copy(S.matrix),(h!==S||d!==S.version||f!==s.toneMapping)&&(l.material.needsUpdate=!0,h=S,d=S.version,f=s.toneMapping),l.layers.enableAll(),v.unshift(l,l.geometry,l.material,0,0,null))}function p(v,b){v.getRGB(Uc,Th(s)),n.buffers.color.setClear(Uc.r,Uc.g,Uc.b,b,a)}function x(){u!==void 0&&(u.geometry.dispose(),u.material.dispose(),u=void 0),l!==void 0&&(l.geometry.dispose(),l.material.dispose(),l=void 0)}return{getClearColor:function(){return o},setClearColor:function(v,b=1){o.set(v),c=b,p(o,c)},getClearAlpha:function(){return c},setClearAlpha:function(v){c=v,p(o,c)},render:y,addToRenderList:m,dispose:x}}function My(s,e){let t=s.getParameter(s.MAX_VERTEX_ATTRIBS),n={},i=d(null),r=i,a=!1;function o(_,I,C,D,N){let U=!1,B=h(D,C,I);r!==B&&(r=B,l(r.object)),U=f(_,D,C,N),U&&g(_,D,C,N),N!==null&&e.update(N,s.ELEMENT_ARRAY_BUFFER),(U||a)&&(a=!1,b(_,I,C,D),N!==null&&s.bindBuffer(s.ELEMENT_ARRAY_BUFFER,e.get(N).buffer))}function c(){return s.createVertexArray()}function l(_){return s.bindVertexArray(_)}function u(_){return s.deleteVertexArray(_)}function h(_,I,C){let D=C.wireframe===!0,N=n[_.id];N===void 0&&(N={},n[_.id]=N);let U=N[I.id];U===void 0&&(U={},N[I.id]=U);let B=U[D];return B===void 0&&(B=d(c()),U[D]=B),B}function d(_){let I=[],C=[],D=[];for(let N=0;N<t;N++)I[N]=0,C[N]=0,D[N]=0;return{geometry:null,program:null,wireframe:!1,newAttributes:I,enabledAttributes:C,attributeDivisors:D,object:_,attributes:{},index:null}}function f(_,I,C,D){let N=r.attributes,U=I.attributes,B=0,J=C.getAttributes();for(let V in J)if(J[V].location>=0){let ue=N[V],_e=U[V];if(_e===void 0&&(V==="instanceMatrix"&&_.instanceMatrix&&(_e=_.instanceMatrix),V==="instanceColor"&&_.instanceColor&&(_e=_.instanceColor)),ue===void 0||ue.attribute!==_e||_e&&ue.data!==_e.data)return!0;B++}return r.attributesNum!==B||r.index!==D}function g(_,I,C,D){let N={},U=I.attributes,B=0,J=C.getAttributes();for(let V in J)if(J[V].location>=0){let ue=U[V];ue===void 0&&(V==="instanceMatrix"&&_.instanceMatrix&&(ue=_.instanceMatrix),V==="instanceColor"&&_.instanceColor&&(ue=_.instanceColor));let _e={};_e.attribute=ue,ue&&ue.data&&(_e.data=ue.data),N[V]=_e,B++}r.attributes=N,r.attributesNum=B,r.index=D}function y(){let _=r.newAttributes;for(let I=0,C=_.length;I<C;I++)_[I]=0}function m(_){p(_,0)}function p(_,I){let C=r.newAttributes,D=r.enabledAttributes,N=r.attributeDivisors;C[_]=1,D[_]===0&&(s.enableVertexAttribArray(_),D[_]=1),N[_]!==I&&(s.vertexAttribDivisor(_,I),N[_]=I)}function x(){let _=r.newAttributes,I=r.enabledAttributes;for(let C=0,D=I.length;C<D;C++)I[C]!==_[C]&&(s.disableVertexAttribArray(C),I[C]=0)}function v(_,I,C,D,N,U,B){B===!0?s.vertexAttribIPointer(_,I,C,N,U):s.vertexAttribPointer(_,I,C,D,N,U)}function b(_,I,C,D){y();let N=D.attributes,U=C.getAttributes(),B=I.defaultAttributeValues;for(let J in U){let V=U[J];if(V.location>=0){let ne=N[J];if(ne===void 0&&(J==="instanceMatrix"&&_.instanceMatrix&&(ne=_.instanceMatrix),J==="instanceColor"&&_.instanceColor&&(ne=_.instanceColor)),ne!==void 0){let ue=ne.normalized,_e=ne.itemSize,ze=e.get(ne);if(ze===void 0)continue;let $e=ze.buffer,ht=ze.type,Ye=ze.bytesPerElement,Q=ht===s.INT||ht===s.UNSIGNED_INT||ne.gpuType===tc;if(ne.isInterleavedBufferAttribute){let te=ne.data,ve=te.stride,Fe=ne.offset;if(te.isInstancedInterleavedBuffer){for(let Se=0;Se<V.locationSize;Se++)p(V.location+Se,te.meshPerAttribute);_.isInstancedMesh!==!0&&D._maxInstanceCount===void 0&&(D._maxInstanceCount=te.meshPerAttribute*te.count)}else for(let Se=0;Se<V.locationSize;Se++)m(V.location+Se);s.bindBuffer(s.ARRAY_BUFFER,$e);for(let Se=0;Se<V.locationSize;Se++)v(V.location+Se,_e/V.locationSize,ht,ue,ve*Ye,(Fe+_e/V.locationSize*Se)*Ye,Q)}else{if(ne.isInstancedBufferAttribute){for(let te=0;te<V.locationSize;te++)p(V.location+te,ne.meshPerAttribute);_.isInstancedMesh!==!0&&D._maxInstanceCount===void 0&&(D._maxInstanceCount=ne.meshPerAttribute*ne.count)}else for(let te=0;te<V.locationSize;te++)m(V.location+te);s.bindBuffer(s.ARRAY_BUFFER,$e);for(let te=0;te<V.locationSize;te++)v(V.location+te,_e/V.locationSize,ht,ue,_e*Ye,_e/V.locationSize*te*Ye,Q)}}else if(B!==void 0){let ue=B[J];if(ue!==void 0)switch(ue.length){case 2:s.vertexAttrib2fv(V.location,ue);break;case 3:s.vertexAttrib3fv(V.location,ue);break;case 4:s.vertexAttrib4fv(V.location,ue);break;default:s.vertexAttrib1fv(V.location,ue)}}}}x()}function S(){A();for(let _ in n){let I=n[_];for(let C in I){let D=I[C];for(let N in D)u(D[N].object),delete D[N];delete I[C]}delete n[_]}}function w(_){if(n[_.id]===void 0)return;let I=n[_.id];for(let C in I){let D=I[C];for(let N in D)u(D[N].object),delete D[N];delete I[C]}delete n[_.id]}function T(_){for(let I in n){let C=n[I];if(C[_.id]===void 0)continue;let D=C[_.id];for(let N in D)u(D[N].object),delete D[N];delete C[_.id]}}function A(){M(),a=!0,r!==i&&(r=i,l(r.object))}function M(){i.geometry=null,i.program=null,i.wireframe=!1}return{setup:o,reset:A,resetDefaultState:M,dispose:S,releaseStatesOfGeometry:w,releaseStatesOfProgram:T,initAttributes:y,enableAttribute:m,disableUnusedAttributes:x}}function Sy(s,e,t){let n;function i(l){n=l}function r(l,u){s.drawArrays(n,l,u),t.update(u,n,1)}function a(l,u,h){h!==0&&(s.drawArraysInstanced(n,l,u,h),t.update(u,n,h))}function o(l,u,h){if(h===0)return;e.get("WEBGL_multi_draw").multiDrawArraysWEBGL(n,l,0,u,0,h);let f=0;for(let g=0;g<h;g++)f+=u[g];t.update(f,n,1)}function c(l,u,h,d){if(h===0)return;let f=e.get("WEBGL_multi_draw");if(f===null)for(let g=0;g<l.length;g++)a(l[g],u[g],d[g]);else{f.multiDrawArraysInstancedWEBGL(n,l,0,u,0,d,0,h);let g=0;for(let y=0;y<h;y++)g+=u[y]*d[y];t.update(g,n,1)}}this.setMode=i,this.render=r,this.renderInstances=a,this.renderMultiDraw=o,this.renderMultiDrawInstances=c}function Ty(s,e,t,n){let i;function r(){if(i!==void 0)return i;if(e.has("EXT_texture_filter_anisotropic")===!0){let T=e.get("EXT_texture_filter_anisotropic");i=s.getParameter(T.MAX_TEXTURE_MAX_ANISOTROPY_EXT)}else i=0;return i}function a(T){return!(T!==Tn&&n.convert(T)!==s.getParameter(s.IMPLEMENTATION_COLOR_READ_FORMAT))}function o(T){let A=T===zi&&(e.has("EXT_color_buffer_half_float")||e.has("EXT_color_buffer_float"));return!(T!==jn&&n.convert(T)!==s.getParameter(s.IMPLEMENTATION_COLOR_READ_TYPE)&&T!==Fn&&!A)}function c(T){if(T==="highp"){if(s.getShaderPrecisionFormat(s.VERTEX_SHADER,s.HIGH_FLOAT).precision>0&&s.getShaderPrecisionFormat(s.FRAGMENT_SHADER,s.HIGH_FLOAT).precision>0)return"highp";T="mediump"}return T==="mediump"&&s.getShaderPrecisionFormat(s.VERTEX_SHADER,s.MEDIUM_FLOAT).precision>0&&s.getShaderPrecisionFormat(s.FRAGMENT_SHADER,s.MEDIUM_FLOAT).precision>0?"mediump":"lowp"}let l=t.precision!==void 0?t.precision:"highp",u=c(l);u!==l&&(console.warn("THREE.WebGLRenderer:",l,"not supported, using",u,"instead."),l=u);let h=t.logarithmicDepthBuffer===!0,d=t.reversedDepthBuffer===!0&&e.has("EXT_clip_control"),f=s.getParameter(s.MAX_TEXTURE_IMAGE_UNITS),g=s.getParameter(s.MAX_VERTEX_TEXTURE_IMAGE_UNITS),y=s.getParameter(s.MAX_TEXTURE_SIZE),m=s.getParameter(s.MAX_CUBE_MAP_TEXTURE_SIZE),p=s.getParameter(s.MAX_VERTEX_ATTRIBS),x=s.getParameter(s.MAX_VERTEX_UNIFORM_VECTORS),v=s.getParameter(s.MAX_VARYING_VECTORS),b=s.getParameter(s.MAX_FRAGMENT_UNIFORM_VECTORS),S=g>0,w=s.getParameter(s.MAX_SAMPLES);return{isWebGL2:!0,getMaxAnisotropy:r,getMaxPrecision:c,textureFormatReadable:a,textureTypeReadable:o,precision:l,logarithmicDepthBuffer:h,reversedDepthBuffer:d,maxTextures:f,maxVertexTextures:g,maxTextureSize:y,maxCubemapSize:m,maxAttributes:p,maxVertexUniforms:x,maxVaryings:v,maxFragmentUniforms:b,vertexTextures:S,maxSamples:w}}function Ey(s){let e=this,t=null,n=0,i=!1,r=!1,a=new fn,o=new qe,c={value:null,needsUpdate:!1};this.uniform=c,this.numPlanes=0,this.numIntersection=0,this.init=function(h,d){let f=h.length!==0||d||n!==0||i;return i=d,n=h.length,f},this.beginShadows=function(){r=!0,u(null)},this.endShadows=function(){r=!1},this.setGlobalState=function(h,d){t=u(h,d,0)},this.setState=function(h,d,f){let g=h.clippingPlanes,y=h.clipIntersection,m=h.clipShadows,p=s.get(h);if(!i||g===null||g.length===0||r&&!m)r?u(null):l();else{let x=r?0:n,v=x*4,b=p.clippingState||null;c.value=b,b=u(g,d,v,f);for(let S=0;S!==v;++S)b[S]=t[S];p.clippingState=b,this.numIntersection=y?this.numPlanes:0,this.numPlanes+=x}};function l(){c.value!==t&&(c.value=t,c.needsUpdate=n>0),e.numPlanes=n,e.numIntersection=0}function u(h,d,f,g){let y=h!==null?h.length:0,m=null;if(y!==0){if(m=c.value,g!==!0||m===null){let p=f+y*4,x=d.matrixWorldInverse;o.getNormalMatrix(x),(m===null||m.length<p)&&(m=new Float32Array(p));for(let v=0,b=f;v!==y;++v,b+=4)a.copy(h[v]).applyMatrix4(x,o),a.normal.toArray(m,b),m[b+3]=a.constant}c.value=m,c.needsUpdate=!0}return e.numPlanes=y,e.numIntersection=0,m}}function Ay(s){let e=new WeakMap;function t(a,o){return o===$o?a.mapping=fs:o===Qo&&(a.mapping=ps),a}function n(a){if(a&&a.isTexture){let o=a.mapping;if(o===$o||o===Qo)if(e.has(a)){let c=e.get(a).texture;return t(c,a.mapping)}else{let c=a.image;if(c&&c.height>0){let l=new Io(c.height);return l.fromEquirectangularTexture(s,a),e.set(a,l),a.addEventListener("dispose",i),t(l.texture,a.mapping)}else return null}}return a}function i(a){let o=a.target;o.removeEventListener("dispose",i);let c=e.get(o);c!==void 0&&(e.delete(o),c.dispose())}function r(){e=new WeakMap}return{get:n,dispose:r}}var br=4,Bf=[.125,.215,.35,.446,.526,.582],vs=20,Ch=new hs,Of=new Ue,Ih=null,Ph=0,kh=0,Lh=!1,xs=(1+Math.sqrt(5))/2,gr=1/xs,zf=[new L(-xs,gr,0),new L(xs,gr,0),new L(-gr,0,xs),new L(gr,0,xs),new L(0,xs,-gr),new L(0,xs,gr),new L(-1,1,-1),new L(1,1,-1),new L(-1,1,1),new L(1,1,1)],Ry=new L,xr=class{constructor(e){this._renderer=e,this._pingPongRenderTarget=null,this._lodMax=0,this._cubeSize=0,this._lodPlanes=[],this._sizeLods=[],this._sigmas=[],this._blurMaterial=null,this._cubemapMaterial=null,this._equirectMaterial=null,this._compileMaterial(this._blurMaterial)}fromScene(e,t=0,n=.1,i=100,r={}){let{size:a=256,position:o=Ry}=r;Ih=this._renderer.getRenderTarget(),Ph=this._renderer.getActiveCubeFace(),kh=this._renderer.getActiveMipmapLevel(),Lh=this._renderer.xr.enabled,this._renderer.xr.enabled=!1,this._setSize(a);let c=this._allocateTargets();return c.depthBuffer=!0,this._sceneToCubeUV(e,n,i,c,o),t>0&&this._blur(c,0,0,t),this._applyPMREM(c),this._cleanup(c),c}fromEquirectangular(e,t=null){return this._fromTexture(e,t)}fromCubemap(e,t=null){return this._fromTexture(e,t)}compileCubemapShader(){this._cubemapMaterial===null&&(this._cubemapMaterial=Gf(),this._compileMaterial(this._cubemapMaterial))}compileEquirectangularShader(){this._equirectMaterial===null&&(this._equirectMaterial=Vf(),this._compileMaterial(this._equirectMaterial))}dispose(){this._dispose(),this._cubemapMaterial!==null&&this._cubemapMaterial.dispose(),this._equirectMaterial!==null&&this._equirectMaterial.dispose()}_setSize(e){this._lodMax=Math.floor(Math.log2(e)),this._cubeSize=Math.pow(2,this._lodMax)}_dispose(){this._blurMaterial!==null&&this._blurMaterial.dispose(),this._pingPongRenderTarget!==null&&this._pingPongRenderTarget.dispose();for(let e=0;e<this._lodPlanes.length;e++)this._lodPlanes[e].dispose()}_cleanup(e){this._renderer.setRenderTarget(Ih,Ph,kh),this._renderer.xr.enabled=Lh,e.scissorTest=!1,Bc(e,0,0,e.width,e.height)}_fromTexture(e,t){e.mapping===fs||e.mapping===ps?this._setSize(e.image.length===0?16:e.image[0].width||e.image[0].image.width):this._setSize(e.image.width/4),Ih=this._renderer.getRenderTarget(),Ph=this._renderer.getActiveCubeFace(),kh=this._renderer.getActiveMipmapLevel(),Lh=this._renderer.xr.enabled,this._renderer.xr.enabled=!1;let n=t||this._allocateTargets();return this._textureToCubeUV(e,n),this._applyPMREM(n),this._cleanup(n),n}_allocateTargets(){let e=3*Math.max(this._cubeSize,112),t=4*this._cubeSize,n={magFilter:jt,minFilter:jt,generateMipmaps:!1,type:zi,format:Tn,colorSpace:Kt,depthBuffer:!1},i=Hf(e,t,n);if(this._pingPongRenderTarget===null||this._pingPongRenderTarget.width!==e||this._pingPongRenderTarget.height!==t){this._pingPongRenderTarget!==null&&this._dispose(),this._pingPongRenderTarget=Hf(e,t,n);let{_lodMax:r}=this;({sizeLods:this._sizeLods,lodPlanes:this._lodPlanes,sigmas:this._sigmas}=Cy(r)),this._blurMaterial=Iy(r,e,t)}return i}_compileMaterial(e){let t=new at(this._lodPlanes[0],e);this._renderer.compile(t,Ch)}_sceneToCubeUV(e,t,n,i,r){let c=new Ut(90,1,t,n),l=[1,-1,1,1,1,1],u=[1,1,1,-1,-1,-1],h=this._renderer,d=h.autoClear,f=h.toneMapping;h.getClearColor(Of),h.toneMapping=Ei,h.autoClear=!1,h.state.buffers.depth.getReversed()&&(h.setRenderTarget(i),h.clearDepth(),h.setRenderTarget(null));let y=new nn({name:"PMREM.Background",side:Dt,depthWrite:!1,depthTest:!1}),m=new at(new Xn,y),p=!1,x=e.background;x?x.isColor&&(y.color.copy(x),e.background=null,p=!0):(y.color.copy(Of),p=!0);for(let v=0;v<6;v++){let b=v%3;b===0?(c.up.set(0,l[v],0),c.position.set(r.x,r.y,r.z),c.lookAt(r.x+u[v],r.y,r.z)):b===1?(c.up.set(0,0,l[v]),c.position.set(r.x,r.y,r.z),c.lookAt(r.x,r.y+u[v],r.z)):(c.up.set(0,l[v],0),c.position.set(r.x,r.y,r.z),c.lookAt(r.x,r.y,r.z+u[v]));let S=this._cubeSize;Bc(i,b*S,v>2?S:0,S,S),h.setRenderTarget(i),p&&h.render(m,c),h.render(e,c)}m.geometry.dispose(),m.material.dispose(),h.toneMapping=f,h.autoClear=d,e.background=x}_textureToCubeUV(e,t){let n=this._renderer,i=e.mapping===fs||e.mapping===ps;i?(this._cubemapMaterial===null&&(this._cubemapMaterial=Gf()),this._cubemapMaterial.uniforms.flipEnvMap.value=e.isRenderTargetTexture===!1?-1:1):this._equirectMaterial===null&&(this._equirectMaterial=Vf());let r=i?this._cubemapMaterial:this._equirectMaterial,a=new at(this._lodPlanes[0],r),o=r.uniforms;o.envMap.value=e;let c=this._cubeSize;Bc(t,0,0,3*c,2*c),n.setRenderTarget(t),n.render(a,Ch)}_applyPMREM(e){let t=this._renderer,n=t.autoClear;t.autoClear=!1;let i=this._lodPlanes.length;for(let r=1;r<i;r++){let a=Math.sqrt(this._sigmas[r]*this._sigmas[r]-this._sigmas[r-1]*this._sigmas[r-1]),o=zf[(i-r-1)%zf.length];this._blur(e,r-1,r,a,o)}t.autoClear=n}_blur(e,t,n,i,r){let a=this._pingPongRenderTarget;this._halfBlur(e,a,t,n,i,"latitudinal",r),this._halfBlur(a,e,n,n,i,"longitudinal",r)}_halfBlur(e,t,n,i,r,a,o){let c=this._renderer,l=this._blurMaterial;a!=="latitudinal"&&a!=="longitudinal"&&console.error("blur direction must be either latitudinal or longitudinal!");let u=3,h=new at(this._lodPlanes[i],l),d=l.uniforms,f=this._sizeLods[n]-1,g=isFinite(r)?Math.PI/(2*f):2*Math.PI/(2*vs-1),y=r/g,m=isFinite(r)?1+Math.floor(u*y):vs;m>vs&&console.warn(`sigmaRadians, ${r}, is too large and will clip, as it requested ${m} samples when the maximum is set to ${vs}`);let p=[],x=0;for(let T=0;T<vs;++T){let A=T/y,M=Math.exp(-A*A/2);p.push(M),T===0?x+=M:T<m&&(x+=2*M)}for(let T=0;T<p.length;T++)p[T]=p[T]/x;d.envMap.value=e.texture,d.samples.value=m,d.weights.value=p,d.latitudinal.value=a==="latitudinal",o&&(d.poleAxis.value=o);let{_lodMax:v}=this;d.dTheta.value=g,d.mipInt.value=v-n;let b=this._sizeLods[i],S=3*b*(i>v-br?i-v+br:0),w=4*(this._cubeSize-b);Bc(t,S,w,3*b,2*b),c.setRenderTarget(t),c.render(h,Ch)}};function Cy(s){let e=[],t=[],n=[],i=s,r=s-br+1+Bf.length;for(let a=0;a<r;a++){let o=Math.pow(2,i);t.push(o);let c=1/o;a>s-br?c=Bf[a-s+br-1]:a===0&&(c=0),n.push(c);let l=1/(o-2),u=-l,h=1+l,d=[u,u,h,u,h,h,u,u,h,h,u,h],f=6,g=6,y=3,m=2,p=1,x=new Float32Array(y*g*f),v=new Float32Array(m*g*f),b=new Float32Array(p*g*f);for(let w=0;w<f;w++){let T=w%3*2/3-1,A=w>2?0:-1,M=[T,A,0,T+2/3,A,0,T+2/3,A+1,0,T,A,0,T+2/3,A+1,0,T,A+1,0];x.set(M,y*g*w),v.set(d,m*g*w);let _=[w,w,w,w,w,w];b.set(_,p*g*w)}let S=new Bt;S.setAttribute("position",new xt(x,y)),S.setAttribute("uv",new xt(v,m)),S.setAttribute("faceIndex",new xt(b,p)),e.push(S),i>br&&i--}return{lodPlanes:e,sizeLods:t,sigmas:n}}function Hf(s,e,t){let n=new ei(s,e,t);return n.texture.mapping=Sa,n.texture.name="PMREM.cubeUv",n.scissorTest=!0,n}function Bc(s,e,t,n,i){s.viewport.set(e,t,n,i),s.scissor.set(e,t,n,i)}function Iy(s,e,t){let n=new Float32Array(vs),i=new L(0,1,0);return new Yt({name:"SphericalGaussianBlur",defines:{n:vs,CUBEUV_TEXEL_WIDTH:1/e,CUBEUV_TEXEL_HEIGHT:1/t,CUBEUV_MAX_MIP:`${s}.0`},uniforms:{envMap:{value:null},samples:{value:1},weights:{value:n},latitudinal:{value:!1},dTheta:{value:0},mipInt:{value:0},poleAxis:{value:i}},vertexShader:Gh(),fragmentShader:`

			precision mediump float;
			precision mediump int;

			varying vec3 vOutputDirection;

			uniform sampler2D envMap;
			uniform int samples;
			uniform float weights[ n ];
			uniform bool latitudinal;
			uniform float dTheta;
			uniform float mipInt;
			uniform vec3 poleAxis;

			#define ENVMAP_TYPE_CUBE_UV
			#include <cube_uv_reflection_fragment>

			vec3 getSample( float theta, vec3 axis ) {

				float cosTheta = cos( theta );
				// Rodrigues' axis-angle rotation
				vec3 sampleDirection = vOutputDirection * cosTheta
					+ cross( axis, vOutputDirection ) * sin( theta )
					+ axis * dot( axis, vOutputDirection ) * ( 1.0 - cosTheta );

				return bilinearCubeUV( envMap, sampleDirection, mipInt );

			}

			void main() {

				vec3 axis = latitudinal ? poleAxis : cross( poleAxis, vOutputDirection );

				if ( all( equal( axis, vec3( 0.0 ) ) ) ) {

					axis = vec3( vOutputDirection.z, 0.0, - vOutputDirection.x );

				}

				axis = normalize( axis );

				gl_FragColor = vec4( 0.0, 0.0, 0.0, 1.0 );
				gl_FragColor.rgb += weights[ 0 ] * getSample( 0.0, axis );

				for ( int i = 1; i < n; i++ ) {

					if ( i >= samples ) {

						break;

					}

					float theta = dTheta * float( i );
					gl_FragColor.rgb += weights[ i ] * getSample( -1.0 * theta, axis );
					gl_FragColor.rgb += weights[ i ] * getSample( theta, axis );

				}

			}
		`,blending:Ti,depthTest:!1,depthWrite:!1})}function Vf(){return new Yt({name:"EquirectangularToCubeUV",uniforms:{envMap:{value:null}},vertexShader:Gh(),fragmentShader:`

			precision mediump float;
			precision mediump int;

			varying vec3 vOutputDirection;

			uniform sampler2D envMap;

			#include <common>

			void main() {

				vec3 outputDirection = normalize( vOutputDirection );
				vec2 uv = equirectUv( outputDirection );

				gl_FragColor = vec4( texture2D ( envMap, uv ).rgb, 1.0 );

			}
		`,blending:Ti,depthTest:!1,depthWrite:!1})}function Gf(){return new Yt({name:"CubemapToCubeUV",uniforms:{envMap:{value:null},flipEnvMap:{value:-1}},vertexShader:Gh(),fragmentShader:`

			precision mediump float;
			precision mediump int;

			uniform float flipEnvMap;

			varying vec3 vOutputDirection;

			uniform samplerCube envMap;

			void main() {

				gl_FragColor = textureCube( envMap, vec3( flipEnvMap * vOutputDirection.x, vOutputDirection.yz ) );

			}
		`,blending:Ti,depthTest:!1,depthWrite:!1})}function Gh(){return`

		precision mediump float;
		precision mediump int;

		attribute float faceIndex;

		varying vec3 vOutputDirection;

		// RH coordinate system; PMREM face-indexing convention
		vec3 getDirection( vec2 uv, float face ) {

			uv = 2.0 * uv - 1.0;

			vec3 direction = vec3( uv, 1.0 );

			if ( face == 0.0 ) {

				direction = direction.zyx; // ( 1, v, u ) pos x

			} else if ( face == 1.0 ) {

				direction = direction.xzy;
				direction.xz *= -1.0; // ( -u, 1, -v ) pos y

			} else if ( face == 2.0 ) {

				direction.x *= -1.0; // ( -u, v, 1 ) pos z

			} else if ( face == 3.0 ) {

				direction = direction.zyx;
				direction.xz *= -1.0; // ( -1, v, -u ) neg x

			} else if ( face == 4.0 ) {

				direction = direction.xzy;
				direction.xy *= -1.0; // ( -u, -1, v ) neg y

			} else if ( face == 5.0 ) {

				direction.z *= -1.0; // ( u, v, -1 ) neg z

			}

			return direction;

		}

		void main() {

			vOutputDirection = getDirection( uv, faceIndex );
			gl_Position = vec4( position, 1.0 );

		}
	`}function Py(s){let e=new WeakMap,t=null;function n(o){if(o&&o.isTexture){let c=o.mapping,l=c===$o||c===Qo,u=c===fs||c===ps;if(l||u){let h=e.get(o),d=h!==void 0?h.texture.pmremVersion:0;if(o.isRenderTargetTexture&&o.pmremVersion!==d)return t===null&&(t=new xr(s)),h=l?t.fromEquirectangular(o,h):t.fromCubemap(o,h),h.texture.pmremVersion=o.pmremVersion,e.set(o,h),h.texture;if(h!==void 0)return h.texture;{let f=o.image;return l&&f&&f.height>0||u&&f&&i(f)?(t===null&&(t=new xr(s)),h=l?t.fromEquirectangular(o):t.fromCubemap(o),h.texture.pmremVersion=o.pmremVersion,e.set(o,h),o.addEventListener("dispose",r),h.texture):null}}}return o}function i(o){let c=0,l=6;for(let u=0;u<l;u++)o[u]!==void 0&&c++;return c===l}function r(o){let c=o.target;c.removeEventListener("dispose",r);let l=e.get(c);l!==void 0&&(e.delete(c),l.dispose())}function a(){e=new WeakMap,t!==null&&(t.dispose(),t=null)}return{get:n,dispose:a}}function ky(s){let e={};function t(n){if(e[n]!==void 0)return e[n];let i;switch(n){case"WEBGL_depth_texture":i=s.getExtension("WEBGL_depth_texture")||s.getExtension("MOZ_WEBGL_depth_texture")||s.getExtension("WEBKIT_WEBGL_depth_texture");break;case"EXT_texture_filter_anisotropic":i=s.getExtension("EXT_texture_filter_anisotropic")||s.getExtension("MOZ_EXT_texture_filter_anisotropic")||s.getExtension("WEBKIT_EXT_texture_filter_anisotropic");break;case"WEBGL_compressed_texture_s3tc":i=s.getExtension("WEBGL_compressed_texture_s3tc")||s.getExtension("MOZ_WEBGL_compressed_texture_s3tc")||s.getExtension("WEBKIT_WEBGL_compressed_texture_s3tc");break;case"WEBGL_compressed_texture_pvrtc":i=s.getExtension("WEBGL_compressed_texture_pvrtc")||s.getExtension("WEBKIT_WEBGL_compressed_texture_pvrtc");break;default:i=s.getExtension(n)}return e[n]=i,i}return{has:function(n){return t(n)!==null},init:function(){t("EXT_color_buffer_float"),t("WEBGL_clip_cull_distance"),t("OES_texture_float_linear"),t("EXT_color_buffer_half_float"),t("WEBGL_multisampled_render_to_texture"),t("WEBGL_render_shared_exponent")},get:function(n){let i=t(n);return i===null&&Js("THREE.WebGLRenderer: "+n+" extension not supported."),i}}}function Ly(s,e,t,n){let i={},r=new WeakMap;function a(h){let d=h.target;d.index!==null&&e.remove(d.index);for(let g in d.attributes)e.remove(d.attributes[g]);d.removeEventListener("dispose",a),delete i[d.id];let f=r.get(d);f&&(e.remove(f),r.delete(d)),n.releaseStatesOfGeometry(d),d.isInstancedBufferGeometry===!0&&delete d._maxInstanceCount,t.memory.geometries--}function o(h,d){return i[d.id]===!0||(d.addEventListener("dispose",a),i[d.id]=!0,t.memory.geometries++),d}function c(h){let d=h.attributes;for(let f in d)e.update(d[f],s.ARRAY_BUFFER)}function l(h){let d=[],f=h.index,g=h.attributes.position,y=0;if(f!==null){let x=f.array;y=f.version;for(let v=0,b=x.length;v<b;v+=3){let S=x[v+0],w=x[v+1],T=x[v+2];d.push(S,w,w,T,T,S)}}else if(g!==void 0){let x=g.array;y=g.version;for(let v=0,b=x.length/3-1;v<b;v+=3){let S=v+0,w=v+1,T=v+2;d.push(S,w,w,T,T,S)}}else return;let m=new(Sh(d)?ea:Qr)(d,1);m.version=y;let p=r.get(h);p&&e.remove(p),r.set(h,m)}function u(h){let d=r.get(h);if(d){let f=h.index;f!==null&&d.version<f.version&&l(h)}else l(h);return r.get(h)}return{get:o,update:c,getWireframeAttribute:u}}function Dy(s,e,t){let n;function i(d){n=d}let r,a;function o(d){r=d.type,a=d.bytesPerElement}function c(d,f){s.drawElements(n,f,r,d*a),t.update(f,n,1)}function l(d,f,g){g!==0&&(s.drawElementsInstanced(n,f,r,d*a,g),t.update(f,n,g))}function u(d,f,g){if(g===0)return;e.get("WEBGL_multi_draw").multiDrawElementsWEBGL(n,f,0,r,d,0,g);let m=0;for(let p=0;p<g;p++)m+=f[p];t.update(m,n,1)}function h(d,f,g,y){if(g===0)return;let m=e.get("WEBGL_multi_draw");if(m===null)for(let p=0;p<d.length;p++)l(d[p]/a,f[p],y[p]);else{m.multiDrawElementsInstancedWEBGL(n,f,0,r,d,0,y,0,g);let p=0;for(let x=0;x<g;x++)p+=f[x]*y[x];t.update(p,n,1)}}this.setMode=i,this.setIndex=o,this.render=c,this.renderInstances=l,this.renderMultiDraw=u,this.renderMultiDrawInstances=h}function Ny(s){let e={geometries:0,textures:0},t={frame:0,calls:0,triangles:0,points:0,lines:0};function n(r,a,o){switch(t.calls++,a){case s.TRIANGLES:t.triangles+=o*(r/3);break;case s.LINES:t.lines+=o*(r/2);break;case s.LINE_STRIP:t.lines+=o*(r-1);break;case s.LINE_LOOP:t.lines+=o*r;break;case s.POINTS:t.points+=o*r;break;default:console.error("THREE.WebGLInfo: Unknown draw mode:",a);break}}function i(){t.calls=0,t.triangles=0,t.points=0,t.lines=0}return{memory:e,render:t,programs:null,autoReset:!0,reset:i,update:n}}function Fy(s,e,t){let n=new WeakMap,i=new tt;function r(a,o,c){let l=a.morphTargetInfluences,u=o.morphAttributes.position||o.morphAttributes.normal||o.morphAttributes.color,h=u!==void 0?u.length:0,d=n.get(o);if(d===void 0||d.count!==h){let M=function(){T.dispose(),n.delete(o),o.removeEventListener("dispose",M)};d!==void 0&&d.texture.dispose();let f=o.morphAttributes.position!==void 0,g=o.morphAttributes.normal!==void 0,y=o.morphAttributes.color!==void 0,m=o.morphAttributes.position||[],p=o.morphAttributes.normal||[],x=o.morphAttributes.color||[],v=0;f===!0&&(v=1),g===!0&&(v=2),y===!0&&(v=3);let b=o.attributes.position.count*v,S=1;b>e.maxTextureSize&&(S=Math.ceil(b/e.maxTextureSize),b=e.maxTextureSize);let w=new Float32Array(b*S*4*h),T=new Jr(w,b,S,h);T.type=Fn,T.needsUpdate=!0;let A=v*4;for(let _=0;_<h;_++){let I=m[_],C=p[_],D=x[_],N=b*S*4*_;for(let U=0;U<I.count;U++){let B=U*A;f===!0&&(i.fromBufferAttribute(I,U),w[N+B+0]=i.x,w[N+B+1]=i.y,w[N+B+2]=i.z,w[N+B+3]=0),g===!0&&(i.fromBufferAttribute(C,U),w[N+B+4]=i.x,w[N+B+5]=i.y,w[N+B+6]=i.z,w[N+B+7]=0),y===!0&&(i.fromBufferAttribute(D,U),w[N+B+8]=i.x,w[N+B+9]=i.y,w[N+B+10]=i.z,w[N+B+11]=D.itemSize===4?i.w:1)}}d={count:h,texture:T,size:new Ne(b,S)},n.set(o,d),o.addEventListener("dispose",M)}if(a.isInstancedMesh===!0&&a.morphTexture!==null)c.getUniforms().setValue(s,"morphTexture",a.morphTexture,t);else{let f=0;for(let y=0;y<l.length;y++)f+=l[y];let g=o.morphTargetsRelative?1:1-f;c.getUniforms().setValue(s,"morphTargetBaseInfluence",g),c.getUniforms().setValue(s,"morphTargetInfluences",l)}c.getUniforms().setValue(s,"morphTargetsTexture",d.texture,t),c.getUniforms().setValue(s,"morphTargetsTextureSize",d.size)}return{update:r}}function Uy(s,e,t,n){let i=new WeakMap;function r(c){let l=n.render.frame,u=c.geometry,h=e.get(c,u);if(i.get(h)!==l&&(e.update(h),i.set(h,l)),c.isInstancedMesh&&(c.hasEventListener("dispose",o)===!1&&c.addEventListener("dispose",o),i.get(c)!==l&&(t.update(c.instanceMatrix,s.ARRAY_BUFFER),c.instanceColor!==null&&t.update(c.instanceColor,s.ARRAY_BUFFER),i.set(c,l))),c.isSkinnedMesh){let d=c.skeleton;i.get(d)!==l&&(d.update(),i.set(d,l))}return h}function a(){i=new WeakMap}function o(c){let l=c.target;l.removeEventListener("dispose",o),t.remove(l.instanceMatrix),l.instanceColor!==null&&t.remove(l.instanceColor)}return{update:r,dispose:a}}var cp=new Wt,Wf=new ha(1,1),lp=new Jr,hp=new Ro,up=new na,Yf=[],Xf=[],qf=new Float32Array(16),jf=new Float32Array(9),Kf=new Float32Array(4);function vr(s,e,t){let n=s[0];if(n<=0||n>0)return s;let i=e*t,r=Yf[i];if(r===void 0&&(r=new Float32Array(i),Yf[i]=r),e!==0){n.toArray(r,0);for(let a=1,o=0;a!==e;++a)o+=t,s[a].toArray(r,o)}return r}function zt(s,e){if(s.length!==e.length)return!1;for(let t=0,n=s.length;t<n;t++)if(s[t]!==e[t])return!1;return!0}function Ht(s,e){for(let t=0,n=e.length;t<n;t++)s[t]=e[t]}function Vc(s,e){let t=Xf[e];t===void 0&&(t=new Int32Array(e),Xf[e]=t);for(let n=0;n!==e;++n)t[n]=s.allocateTextureUnit();return t}function By(s,e){let t=this.cache;t[0]!==e&&(s.uniform1f(this.addr,e),t[0]=e)}function Oy(s,e){let t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y)&&(s.uniform2f(this.addr,e.x,e.y),t[0]=e.x,t[1]=e.y);else{if(zt(t,e))return;s.uniform2fv(this.addr,e),Ht(t,e)}}function zy(s,e){let t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y||t[2]!==e.z)&&(s.uniform3f(this.addr,e.x,e.y,e.z),t[0]=e.x,t[1]=e.y,t[2]=e.z);else if(e.r!==void 0)(t[0]!==e.r||t[1]!==e.g||t[2]!==e.b)&&(s.uniform3f(this.addr,e.r,e.g,e.b),t[0]=e.r,t[1]=e.g,t[2]=e.b);else{if(zt(t,e))return;s.uniform3fv(this.addr,e),Ht(t,e)}}function Hy(s,e){let t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y||t[2]!==e.z||t[3]!==e.w)&&(s.uniform4f(this.addr,e.x,e.y,e.z,e.w),t[0]=e.x,t[1]=e.y,t[2]=e.z,t[3]=e.w);else{if(zt(t,e))return;s.uniform4fv(this.addr,e),Ht(t,e)}}function Vy(s,e){let t=this.cache,n=e.elements;if(n===void 0){if(zt(t,e))return;s.uniformMatrix2fv(this.addr,!1,e),Ht(t,e)}else{if(zt(t,n))return;Kf.set(n),s.uniformMatrix2fv(this.addr,!1,Kf),Ht(t,n)}}function Gy(s,e){let t=this.cache,n=e.elements;if(n===void 0){if(zt(t,e))return;s.uniformMatrix3fv(this.addr,!1,e),Ht(t,e)}else{if(zt(t,n))return;jf.set(n),s.uniformMatrix3fv(this.addr,!1,jf),Ht(t,n)}}function Wy(s,e){let t=this.cache,n=e.elements;if(n===void 0){if(zt(t,e))return;s.uniformMatrix4fv(this.addr,!1,e),Ht(t,e)}else{if(zt(t,n))return;qf.set(n),s.uniformMatrix4fv(this.addr,!1,qf),Ht(t,n)}}function Yy(s,e){let t=this.cache;t[0]!==e&&(s.uniform1i(this.addr,e),t[0]=e)}function Xy(s,e){let t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y)&&(s.uniform2i(this.addr,e.x,e.y),t[0]=e.x,t[1]=e.y);else{if(zt(t,e))return;s.uniform2iv(this.addr,e),Ht(t,e)}}function qy(s,e){let t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y||t[2]!==e.z)&&(s.uniform3i(this.addr,e.x,e.y,e.z),t[0]=e.x,t[1]=e.y,t[2]=e.z);else{if(zt(t,e))return;s.uniform3iv(this.addr,e),Ht(t,e)}}function jy(s,e){let t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y||t[2]!==e.z||t[3]!==e.w)&&(s.uniform4i(this.addr,e.x,e.y,e.z,e.w),t[0]=e.x,t[1]=e.y,t[2]=e.z,t[3]=e.w);else{if(zt(t,e))return;s.uniform4iv(this.addr,e),Ht(t,e)}}function Ky(s,e){let t=this.cache;t[0]!==e&&(s.uniform1ui(this.addr,e),t[0]=e)}function Zy(s,e){let t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y)&&(s.uniform2ui(this.addr,e.x,e.y),t[0]=e.x,t[1]=e.y);else{if(zt(t,e))return;s.uniform2uiv(this.addr,e),Ht(t,e)}}function Jy(s,e){let t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y||t[2]!==e.z)&&(s.uniform3ui(this.addr,e.x,e.y,e.z),t[0]=e.x,t[1]=e.y,t[2]=e.z);else{if(zt(t,e))return;s.uniform3uiv(this.addr,e),Ht(t,e)}}function $y(s,e){let t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y||t[2]!==e.z||t[3]!==e.w)&&(s.uniform4ui(this.addr,e.x,e.y,e.z,e.w),t[0]=e.x,t[1]=e.y,t[2]=e.z,t[3]=e.w);else{if(zt(t,e))return;s.uniform4uiv(this.addr,e),Ht(t,e)}}function Qy(s,e,t){let n=this.cache,i=t.allocateTextureUnit();n[0]!==i&&(s.uniform1i(this.addr,i),n[0]=i);let r;this.type===s.SAMPLER_2D_SHADOW?(Wf.compareFunction=_h,r=Wf):r=cp,t.setTexture2D(e||r,i)}function ex(s,e,t){let n=this.cache,i=t.allocateTextureUnit();n[0]!==i&&(s.uniform1i(this.addr,i),n[0]=i),t.setTexture3D(e||hp,i)}function tx(s,e,t){let n=this.cache,i=t.allocateTextureUnit();n[0]!==i&&(s.uniform1i(this.addr,i),n[0]=i),t.setTextureCube(e||up,i)}function nx(s,e,t){let n=this.cache,i=t.allocateTextureUnit();n[0]!==i&&(s.uniform1i(this.addr,i),n[0]=i),t.setTexture2DArray(e||lp,i)}function ix(s){switch(s){case 5126:return By;case 35664:return Oy;case 35665:return zy;case 35666:return Hy;case 35674:return Vy;case 35675:return Gy;case 35676:return Wy;case 5124:case 35670:return Yy;case 35667:case 35671:return Xy;case 35668:case 35672:return qy;case 35669:case 35673:return jy;case 5125:return Ky;case 36294:return Zy;case 36295:return Jy;case 36296:return $y;case 35678:case 36198:case 36298:case 36306:case 35682:return Qy;case 35679:case 36299:case 36307:return ex;case 35680:case 36300:case 36308:case 36293:return tx;case 36289:case 36303:case 36311:case 36292:return nx}}function sx(s,e){s.uniform1fv(this.addr,e)}function rx(s,e){let t=vr(e,this.size,2);s.uniform2fv(this.addr,t)}function ax(s,e){let t=vr(e,this.size,3);s.uniform3fv(this.addr,t)}function ox(s,e){let t=vr(e,this.size,4);s.uniform4fv(this.addr,t)}function cx(s,e){let t=vr(e,this.size,4);s.uniformMatrix2fv(this.addr,!1,t)}function lx(s,e){let t=vr(e,this.size,9);s.uniformMatrix3fv(this.addr,!1,t)}function hx(s,e){let t=vr(e,this.size,16);s.uniformMatrix4fv(this.addr,!1,t)}function ux(s,e){s.uniform1iv(this.addr,e)}function dx(s,e){s.uniform2iv(this.addr,e)}function fx(s,e){s.uniform3iv(this.addr,e)}function px(s,e){s.uniform4iv(this.addr,e)}function mx(s,e){s.uniform1uiv(this.addr,e)}function gx(s,e){s.uniform2uiv(this.addr,e)}function bx(s,e){s.uniform3uiv(this.addr,e)}function yx(s,e){s.uniform4uiv(this.addr,e)}function xx(s,e,t){let n=this.cache,i=e.length,r=Vc(t,i);zt(n,r)||(s.uniform1iv(this.addr,r),Ht(n,r));for(let a=0;a!==i;++a)t.setTexture2D(e[a]||cp,r[a])}function vx(s,e,t){let n=this.cache,i=e.length,r=Vc(t,i);zt(n,r)||(s.uniform1iv(this.addr,r),Ht(n,r));for(let a=0;a!==i;++a)t.setTexture3D(e[a]||hp,r[a])}function _x(s,e,t){let n=this.cache,i=e.length,r=Vc(t,i);zt(n,r)||(s.uniform1iv(this.addr,r),Ht(n,r));for(let a=0;a!==i;++a)t.setTextureCube(e[a]||up,r[a])}function wx(s,e,t){let n=this.cache,i=e.length,r=Vc(t,i);zt(n,r)||(s.uniform1iv(this.addr,r),Ht(n,r));for(let a=0;a!==i;++a)t.setTexture2DArray(e[a]||lp,r[a])}function Mx(s){switch(s){case 5126:return sx;case 35664:return rx;case 35665:return ax;case 35666:return ox;case 35674:return cx;case 35675:return lx;case 35676:return hx;case 5124:case 35670:return ux;case 35667:case 35671:return dx;case 35668:case 35672:return fx;case 35669:case 35673:return px;case 5125:return mx;case 36294:return gx;case 36295:return bx;case 36296:return yx;case 35678:case 36198:case 36298:case 36306:case 35682:return xx;case 35679:case 36299:case 36307:return vx;case 35680:case 36300:case 36308:case 36293:return _x;case 36289:case 36303:case 36311:case 36292:return wx}}var Nh=class{constructor(e,t,n){this.id=e,this.addr=n,this.cache=[],this.type=t.type,this.setValue=ix(t.type)}},Fh=class{constructor(e,t,n){this.id=e,this.addr=n,this.cache=[],this.type=t.type,this.size=t.size,this.setValue=Mx(t.type)}},Uh=class{constructor(e){this.id=e,this.seq=[],this.map={}}setValue(e,t,n){let i=this.seq;for(let r=0,a=i.length;r!==a;++r){let o=i[r];o.setValue(e,t[o.id],n)}}},Dh=/(\w+)(\])?(\[|\.)?/g;function Zf(s,e){s.seq.push(e),s.map[e.id]=e}function Sx(s,e,t){let n=s.name,i=n.length;for(Dh.lastIndex=0;;){let r=Dh.exec(n),a=Dh.lastIndex,o=r[1],c=r[2]==="]",l=r[3];if(c&&(o=o|0),l===void 0||l==="["&&a+2===i){Zf(t,l===void 0?new Nh(o,s,e):new Fh(o,s,e));break}else{let h=t.map[o];h===void 0&&(h=new Uh(o),Zf(t,h)),t=h}}}var yr=class{constructor(e,t){this.seq=[],this.map={};let n=e.getProgramParameter(t,e.ACTIVE_UNIFORMS);for(let i=0;i<n;++i){let r=e.getActiveUniform(t,i),a=e.getUniformLocation(t,r.name);Sx(r,a,this)}}setValue(e,t,n,i){let r=this.map[t];r!==void 0&&r.setValue(e,n,i)}setOptional(e,t,n){let i=t[n];i!==void 0&&this.setValue(e,n,i)}static upload(e,t,n,i){for(let r=0,a=t.length;r!==a;++r){let o=t[r],c=n[o.id];c.needsUpdate!==!1&&o.setValue(e,c.value,i)}}static seqWithValue(e,t){let n=[];for(let i=0,r=e.length;i!==r;++i){let a=e[i];a.id in t&&n.push(a)}return n}};function Jf(s,e,t){let n=s.createShader(e);return s.shaderSource(n,t),s.compileShader(n),n}var Tx=37297,Ex=0;function Ax(s,e){let t=s.split(`
`),n=[],i=Math.max(e-6,0),r=Math.min(e+6,t.length);for(let a=i;a<r;a++){let o=a+1;n.push(`${o===e?">":" "} ${o}: ${t[a]}`)}return n.join(`
`)}var $f=new qe;function Rx(s){et._getMatrix($f,et.workingColorSpace,s);let e=`mat3( ${$f.elements.map(t=>t.toFixed(4))} )`;switch(et.getTransfer(s)){case Kr:return[e,"LinearTransferOETF"];case pt:return[e,"sRGBTransferOETF"];default:return console.warn("THREE.WebGLProgram: Unsupported color space: ",s),[e,"LinearTransferOETF"]}}function Qf(s,e,t){let n=s.getShaderParameter(e,s.COMPILE_STATUS),r=(s.getShaderInfoLog(e)||"").trim();if(n&&r==="")return"";let a=/ERROR: 0:(\d+)/.exec(r);if(a){let o=parseInt(a[1]);return t.toUpperCase()+`

`+r+`

`+Ax(s.getShaderSource(e),o)}else return r}function Cx(s,e){let t=Rx(e);return[`vec4 ${s}( vec4 value ) {`,`	return ${t[1]}( vec4( value.rgb * ${t[0]}, value.a ) );`,"}"].join(`
`)}function Ix(s,e){let t;switch(e){case mf:t="Linear";break;case gf:t="Reinhard";break;case bf:t="Cineon";break;case Jo:t="ACESFilmic";break;case xf:t="AgX";break;case vf:t="Neutral";break;case yf:t="Custom";break;default:console.warn("THREE.WebGLProgram: Unsupported toneMapping:",e),t="Linear"}return"vec3 "+s+"( vec3 color ) { return "+t+"ToneMapping( color ); }"}var Oc=new L;function Px(){et.getLuminanceCoefficients(Oc);let s=Oc.x.toFixed(4),e=Oc.y.toFixed(4),t=Oc.z.toFixed(4);return["float luminance( const in vec3 rgb ) {",`	const vec3 weights = vec3( ${s}, ${e}, ${t} );`,"	return dot( weights, rgb );","}"].join(`
`)}function kx(s){return[s.extensionClipCullDistance?"#extension GL_ANGLE_clip_cull_distance : require":"",s.extensionMultiDraw?"#extension GL_ANGLE_multi_draw : require":""].filter(Ia).join(`
`)}function Lx(s){let e=[];for(let t in s){let n=s[t];n!==!1&&e.push("#define "+t+" "+n)}return e.join(`
`)}function Dx(s,e){let t={},n=s.getProgramParameter(e,s.ACTIVE_ATTRIBUTES);for(let i=0;i<n;i++){let r=s.getActiveAttrib(e,i),a=r.name,o=1;r.type===s.FLOAT_MAT2&&(o=2),r.type===s.FLOAT_MAT3&&(o=3),r.type===s.FLOAT_MAT4&&(o=4),t[a]={type:r.type,location:s.getAttribLocation(e,a),locationSize:o}}return t}function Ia(s){return s!==""}function ep(s,e){let t=e.numSpotLightShadows+e.numSpotLightMaps-e.numSpotLightShadowsWithMaps;return s.replace(/NUM_DIR_LIGHTS/g,e.numDirLights).replace(/NUM_SPOT_LIGHTS/g,e.numSpotLights).replace(/NUM_SPOT_LIGHT_MAPS/g,e.numSpotLightMaps).replace(/NUM_SPOT_LIGHT_COORDS/g,t).replace(/NUM_RECT_AREA_LIGHTS/g,e.numRectAreaLights).replace(/NUM_POINT_LIGHTS/g,e.numPointLights).replace(/NUM_HEMI_LIGHTS/g,e.numHemiLights).replace(/NUM_DIR_LIGHT_SHADOWS/g,e.numDirLightShadows).replace(/NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS/g,e.numSpotLightShadowsWithMaps).replace(/NUM_SPOT_LIGHT_SHADOWS/g,e.numSpotLightShadows).replace(/NUM_POINT_LIGHT_SHADOWS/g,e.numPointLightShadows)}function tp(s,e){return s.replace(/NUM_CLIPPING_PLANES/g,e.numClippingPlanes).replace(/UNION_CLIPPING_PLANES/g,e.numClippingPlanes-e.numClipIntersection)}var Nx=/^[ \t]*#include +<([\w\d./]+)>/gm;function Bh(s){return s.replace(Nx,Ux)}var Fx=new Map;function Ux(s,e){let t=Ke[e];if(t===void 0){let n=Fx.get(e);if(n!==void 0)t=Ke[n],console.warn('THREE.WebGLRenderer: Shader chunk "%s" has been deprecated. Use "%s" instead.',e,n);else throw new Error("Can not resolve #include <"+e+">")}return Bh(t)}var Bx=/#pragma unroll_loop_start\s+for\s*\(\s*int\s+i\s*=\s*(\d+)\s*;\s*i\s*<\s*(\d+)\s*;\s*i\s*\+\+\s*\)\s*{([\s\S]+?)}\s+#pragma unroll_loop_end/g;function np(s){return s.replace(Bx,Ox)}function Ox(s,e,t,n){let i="";for(let r=parseInt(e);r<parseInt(t);r++)i+=n.replace(/\[\s*i\s*\]/g,"[ "+r+" ]").replace(/UNROLLED_LOOP_INDEX/g,r);return i}function ip(s){let e=`precision ${s.precision} float;
	precision ${s.precision} int;
	precision ${s.precision} sampler2D;
	precision ${s.precision} samplerCube;
	precision ${s.precision} sampler3D;
	precision ${s.precision} sampler2DArray;
	precision ${s.precision} sampler2DShadow;
	precision ${s.precision} samplerCubeShadow;
	precision ${s.precision} sampler2DArrayShadow;
	precision ${s.precision} isampler2D;
	precision ${s.precision} isampler3D;
	precision ${s.precision} isamplerCube;
	precision ${s.precision} isampler2DArray;
	precision ${s.precision} usampler2D;
	precision ${s.precision} usampler3D;
	precision ${s.precision} usamplerCube;
	precision ${s.precision} usampler2DArray;
	`;return s.precision==="highp"?e+=`
#define HIGH_PRECISION`:s.precision==="mediump"?e+=`
#define MEDIUM_PRECISION`:s.precision==="lowp"&&(e+=`
#define LOW_PRECISION`),e}function zx(s){let e="SHADOWMAP_TYPE_BASIC";return s.shadowMapType===Ma?e="SHADOWMAP_TYPE_PCF":s.shadowMapType===Vo?e="SHADOWMAP_TYPE_PCF_SOFT":s.shadowMapType===ri&&(e="SHADOWMAP_TYPE_VSM"),e}function Hx(s){let e="ENVMAP_TYPE_CUBE";if(s.envMap)switch(s.envMapMode){case fs:case ps:e="ENVMAP_TYPE_CUBE";break;case Sa:e="ENVMAP_TYPE_CUBE_UV";break}return e}function Vx(s){let e="ENVMAP_MODE_REFLECTION";return s.envMap&&s.envMapMode===ps&&(e="ENVMAP_MODE_REFRACTION"),e}function Gx(s){let e="ENVMAP_BLENDING_NONE";if(s.envMap)switch(s.combine){case Zo:e="ENVMAP_BLENDING_MULTIPLY";break;case ff:e="ENVMAP_BLENDING_MIX";break;case pf:e="ENVMAP_BLENDING_ADD";break}return e}function Wx(s){let e=s.envMapCubeUVHeight;if(e===null)return null;let t=Math.log2(e)-2,n=1/e;return{texelWidth:1/(3*Math.max(Math.pow(2,t),112)),texelHeight:n,maxMip:t}}function Yx(s,e,t,n){let i=s.getContext(),r=t.defines,a=t.vertexShader,o=t.fragmentShader,c=zx(t),l=Hx(t),u=Vx(t),h=Gx(t),d=Wx(t),f=kx(t),g=Lx(r),y=i.createProgram(),m,p,x=t.glslVersion?"#version "+t.glslVersion+`
`:"";t.isRawShaderMaterial?(m=["#define SHADER_TYPE "+t.shaderType,"#define SHADER_NAME "+t.shaderName,g].filter(Ia).join(`
`),m.length>0&&(m+=`
`),p=["#define SHADER_TYPE "+t.shaderType,"#define SHADER_NAME "+t.shaderName,g].filter(Ia).join(`
`),p.length>0&&(p+=`
`)):(m=[ip(t),"#define SHADER_TYPE "+t.shaderType,"#define SHADER_NAME "+t.shaderName,g,t.extensionClipCullDistance?"#define USE_CLIP_DISTANCE":"",t.batching?"#define USE_BATCHING":"",t.batchingColor?"#define USE_BATCHING_COLOR":"",t.instancing?"#define USE_INSTANCING":"",t.instancingColor?"#define USE_INSTANCING_COLOR":"",t.instancingMorph?"#define USE_INSTANCING_MORPH":"",t.useFog&&t.fog?"#define USE_FOG":"",t.useFog&&t.fogExp2?"#define FOG_EXP2":"",t.map?"#define USE_MAP":"",t.envMap?"#define USE_ENVMAP":"",t.envMap?"#define "+u:"",t.lightMap?"#define USE_LIGHTMAP":"",t.aoMap?"#define USE_AOMAP":"",t.bumpMap?"#define USE_BUMPMAP":"",t.normalMap?"#define USE_NORMALMAP":"",t.normalMapObjectSpace?"#define USE_NORMALMAP_OBJECTSPACE":"",t.normalMapTangentSpace?"#define USE_NORMALMAP_TANGENTSPACE":"",t.displacementMap?"#define USE_DISPLACEMENTMAP":"",t.emissiveMap?"#define USE_EMISSIVEMAP":"",t.anisotropy?"#define USE_ANISOTROPY":"",t.anisotropyMap?"#define USE_ANISOTROPYMAP":"",t.clearcoatMap?"#define USE_CLEARCOATMAP":"",t.clearcoatRoughnessMap?"#define USE_CLEARCOAT_ROUGHNESSMAP":"",t.clearcoatNormalMap?"#define USE_CLEARCOAT_NORMALMAP":"",t.iridescenceMap?"#define USE_IRIDESCENCEMAP":"",t.iridescenceThicknessMap?"#define USE_IRIDESCENCE_THICKNESSMAP":"",t.specularMap?"#define USE_SPECULARMAP":"",t.specularColorMap?"#define USE_SPECULAR_COLORMAP":"",t.specularIntensityMap?"#define USE_SPECULAR_INTENSITYMAP":"",t.roughnessMap?"#define USE_ROUGHNESSMAP":"",t.metalnessMap?"#define USE_METALNESSMAP":"",t.alphaMap?"#define USE_ALPHAMAP":"",t.alphaHash?"#define USE_ALPHAHASH":"",t.transmission?"#define USE_TRANSMISSION":"",t.transmissionMap?"#define USE_TRANSMISSIONMAP":"",t.thicknessMap?"#define USE_THICKNESSMAP":"",t.sheenColorMap?"#define USE_SHEEN_COLORMAP":"",t.sheenRoughnessMap?"#define USE_SHEEN_ROUGHNESSMAP":"",t.mapUv?"#define MAP_UV "+t.mapUv:"",t.alphaMapUv?"#define ALPHAMAP_UV "+t.alphaMapUv:"",t.lightMapUv?"#define LIGHTMAP_UV "+t.lightMapUv:"",t.aoMapUv?"#define AOMAP_UV "+t.aoMapUv:"",t.emissiveMapUv?"#define EMISSIVEMAP_UV "+t.emissiveMapUv:"",t.bumpMapUv?"#define BUMPMAP_UV "+t.bumpMapUv:"",t.normalMapUv?"#define NORMALMAP_UV "+t.normalMapUv:"",t.displacementMapUv?"#define DISPLACEMENTMAP_UV "+t.displacementMapUv:"",t.metalnessMapUv?"#define METALNESSMAP_UV "+t.metalnessMapUv:"",t.roughnessMapUv?"#define ROUGHNESSMAP_UV "+t.roughnessMapUv:"",t.anisotropyMapUv?"#define ANISOTROPYMAP_UV "+t.anisotropyMapUv:"",t.clearcoatMapUv?"#define CLEARCOATMAP_UV "+t.clearcoatMapUv:"",t.clearcoatNormalMapUv?"#define CLEARCOAT_NORMALMAP_UV "+t.clearcoatNormalMapUv:"",t.clearcoatRoughnessMapUv?"#define CLEARCOAT_ROUGHNESSMAP_UV "+t.clearcoatRoughnessMapUv:"",t.iridescenceMapUv?"#define IRIDESCENCEMAP_UV "+t.iridescenceMapUv:"",t.iridescenceThicknessMapUv?"#define IRIDESCENCE_THICKNESSMAP_UV "+t.iridescenceThicknessMapUv:"",t.sheenColorMapUv?"#define SHEEN_COLORMAP_UV "+t.sheenColorMapUv:"",t.sheenRoughnessMapUv?"#define SHEEN_ROUGHNESSMAP_UV "+t.sheenRoughnessMapUv:"",t.specularMapUv?"#define SPECULARMAP_UV "+t.specularMapUv:"",t.specularColorMapUv?"#define SPECULAR_COLORMAP_UV "+t.specularColorMapUv:"",t.specularIntensityMapUv?"#define SPECULAR_INTENSITYMAP_UV "+t.specularIntensityMapUv:"",t.transmissionMapUv?"#define TRANSMISSIONMAP_UV "+t.transmissionMapUv:"",t.thicknessMapUv?"#define THICKNESSMAP_UV "+t.thicknessMapUv:"",t.vertexTangents&&t.flatShading===!1?"#define USE_TANGENT":"",t.vertexColors?"#define USE_COLOR":"",t.vertexAlphas?"#define USE_COLOR_ALPHA":"",t.vertexUv1s?"#define USE_UV1":"",t.vertexUv2s?"#define USE_UV2":"",t.vertexUv3s?"#define USE_UV3":"",t.pointsUvs?"#define USE_POINTS_UV":"",t.flatShading?"#define FLAT_SHADED":"",t.skinning?"#define USE_SKINNING":"",t.morphTargets?"#define USE_MORPHTARGETS":"",t.morphNormals&&t.flatShading===!1?"#define USE_MORPHNORMALS":"",t.morphColors?"#define USE_MORPHCOLORS":"",t.morphTargetsCount>0?"#define MORPHTARGETS_TEXTURE_STRIDE "+t.morphTextureStride:"",t.morphTargetsCount>0?"#define MORPHTARGETS_COUNT "+t.morphTargetsCount:"",t.doubleSided?"#define DOUBLE_SIDED":"",t.flipSided?"#define FLIP_SIDED":"",t.shadowMapEnabled?"#define USE_SHADOWMAP":"",t.shadowMapEnabled?"#define "+c:"",t.sizeAttenuation?"#define USE_SIZEATTENUATION":"",t.numLightProbes>0?"#define USE_LIGHT_PROBES":"",t.logarithmicDepthBuffer?"#define USE_LOGARITHMIC_DEPTH_BUFFER":"",t.reversedDepthBuffer?"#define USE_REVERSED_DEPTH_BUFFER":"","uniform mat4 modelMatrix;","uniform mat4 modelViewMatrix;","uniform mat4 projectionMatrix;","uniform mat4 viewMatrix;","uniform mat3 normalMatrix;","uniform vec3 cameraPosition;","uniform bool isOrthographic;","#ifdef USE_INSTANCING","	attribute mat4 instanceMatrix;","#endif","#ifdef USE_INSTANCING_COLOR","	attribute vec3 instanceColor;","#endif","#ifdef USE_INSTANCING_MORPH","	uniform sampler2D morphTexture;","#endif","attribute vec3 position;","attribute vec3 normal;","attribute vec2 uv;","#ifdef USE_UV1","	attribute vec2 uv1;","#endif","#ifdef USE_UV2","	attribute vec2 uv2;","#endif","#ifdef USE_UV3","	attribute vec2 uv3;","#endif","#ifdef USE_TANGENT","	attribute vec4 tangent;","#endif","#if defined( USE_COLOR_ALPHA )","	attribute vec4 color;","#elif defined( USE_COLOR )","	attribute vec3 color;","#endif","#ifdef USE_SKINNING","	attribute vec4 skinIndex;","	attribute vec4 skinWeight;","#endif",`
`].filter(Ia).join(`
`),p=[ip(t),"#define SHADER_TYPE "+t.shaderType,"#define SHADER_NAME "+t.shaderName,g,t.useFog&&t.fog?"#define USE_FOG":"",t.useFog&&t.fogExp2?"#define FOG_EXP2":"",t.alphaToCoverage?"#define ALPHA_TO_COVERAGE":"",t.map?"#define USE_MAP":"",t.matcap?"#define USE_MATCAP":"",t.envMap?"#define USE_ENVMAP":"",t.envMap?"#define "+l:"",t.envMap?"#define "+u:"",t.envMap?"#define "+h:"",d?"#define CUBEUV_TEXEL_WIDTH "+d.texelWidth:"",d?"#define CUBEUV_TEXEL_HEIGHT "+d.texelHeight:"",d?"#define CUBEUV_MAX_MIP "+d.maxMip+".0":"",t.lightMap?"#define USE_LIGHTMAP":"",t.aoMap?"#define USE_AOMAP":"",t.bumpMap?"#define USE_BUMPMAP":"",t.normalMap?"#define USE_NORMALMAP":"",t.normalMapObjectSpace?"#define USE_NORMALMAP_OBJECTSPACE":"",t.normalMapTangentSpace?"#define USE_NORMALMAP_TANGENTSPACE":"",t.emissiveMap?"#define USE_EMISSIVEMAP":"",t.anisotropy?"#define USE_ANISOTROPY":"",t.anisotropyMap?"#define USE_ANISOTROPYMAP":"",t.clearcoat?"#define USE_CLEARCOAT":"",t.clearcoatMap?"#define USE_CLEARCOATMAP":"",t.clearcoatRoughnessMap?"#define USE_CLEARCOAT_ROUGHNESSMAP":"",t.clearcoatNormalMap?"#define USE_CLEARCOAT_NORMALMAP":"",t.dispersion?"#define USE_DISPERSION":"",t.iridescence?"#define USE_IRIDESCENCE":"",t.iridescenceMap?"#define USE_IRIDESCENCEMAP":"",t.iridescenceThicknessMap?"#define USE_IRIDESCENCE_THICKNESSMAP":"",t.specularMap?"#define USE_SPECULARMAP":"",t.specularColorMap?"#define USE_SPECULAR_COLORMAP":"",t.specularIntensityMap?"#define USE_SPECULAR_INTENSITYMAP":"",t.roughnessMap?"#define USE_ROUGHNESSMAP":"",t.metalnessMap?"#define USE_METALNESSMAP":"",t.alphaMap?"#define USE_ALPHAMAP":"",t.alphaTest?"#define USE_ALPHATEST":"",t.alphaHash?"#define USE_ALPHAHASH":"",t.sheen?"#define USE_SHEEN":"",t.sheenColorMap?"#define USE_SHEEN_COLORMAP":"",t.sheenRoughnessMap?"#define USE_SHEEN_ROUGHNESSMAP":"",t.transmission?"#define USE_TRANSMISSION":"",t.transmissionMap?"#define USE_TRANSMISSIONMAP":"",t.thicknessMap?"#define USE_THICKNESSMAP":"",t.vertexTangents&&t.flatShading===!1?"#define USE_TANGENT":"",t.vertexColors||t.instancingColor||t.batchingColor?"#define USE_COLOR":"",t.vertexAlphas?"#define USE_COLOR_ALPHA":"",t.vertexUv1s?"#define USE_UV1":"",t.vertexUv2s?"#define USE_UV2":"",t.vertexUv3s?"#define USE_UV3":"",t.pointsUvs?"#define USE_POINTS_UV":"",t.gradientMap?"#define USE_GRADIENTMAP":"",t.flatShading?"#define FLAT_SHADED":"",t.doubleSided?"#define DOUBLE_SIDED":"",t.flipSided?"#define FLIP_SIDED":"",t.shadowMapEnabled?"#define USE_SHADOWMAP":"",t.shadowMapEnabled?"#define "+c:"",t.premultipliedAlpha?"#define PREMULTIPLIED_ALPHA":"",t.numLightProbes>0?"#define USE_LIGHT_PROBES":"",t.decodeVideoTexture?"#define DECODE_VIDEO_TEXTURE":"",t.decodeVideoTextureEmissive?"#define DECODE_VIDEO_TEXTURE_EMISSIVE":"",t.logarithmicDepthBuffer?"#define USE_LOGARITHMIC_DEPTH_BUFFER":"",t.reversedDepthBuffer?"#define USE_REVERSED_DEPTH_BUFFER":"","uniform mat4 viewMatrix;","uniform vec3 cameraPosition;","uniform bool isOrthographic;",t.toneMapping!==Ei?"#define TONE_MAPPING":"",t.toneMapping!==Ei?Ke.tonemapping_pars_fragment:"",t.toneMapping!==Ei?Ix("toneMapping",t.toneMapping):"",t.dithering?"#define DITHERING":"",t.opaque?"#define OPAQUE":"",Ke.colorspace_pars_fragment,Cx("linearToOutputTexel",t.outputColorSpace),Px(),t.useDepthPacking?"#define DEPTH_PACKING "+t.depthPacking:"",`
`].filter(Ia).join(`
`)),a=Bh(a),a=ep(a,t),a=tp(a,t),o=Bh(o),o=ep(o,t),o=tp(o,t),a=np(a),o=np(o),t.isRawShaderMaterial!==!0&&(x=`#version 300 es
`,m=[f,"#define attribute in","#define varying out","#define texture2D texture"].join(`
`)+`
`+m,p=["#define varying in",t.glslVersion===wh?"":"layout(location = 0) out highp vec4 pc_fragColor;",t.glslVersion===wh?"":"#define gl_FragColor pc_fragColor","#define gl_FragDepthEXT gl_FragDepth","#define texture2D texture","#define textureCube texture","#define texture2DProj textureProj","#define texture2DLodEXT textureLod","#define texture2DProjLodEXT textureProjLod","#define textureCubeLodEXT textureLod","#define texture2DGradEXT textureGrad","#define texture2DProjGradEXT textureProjGrad","#define textureCubeGradEXT textureGrad"].join(`
`)+`
`+p);let v=x+m+a,b=x+p+o,S=Jf(i,i.VERTEX_SHADER,v),w=Jf(i,i.FRAGMENT_SHADER,b);i.attachShader(y,S),i.attachShader(y,w),t.index0AttributeName!==void 0?i.bindAttribLocation(y,0,t.index0AttributeName):t.morphTargets===!0&&i.bindAttribLocation(y,0,"position"),i.linkProgram(y);function T(I){if(s.debug.checkShaderErrors){let C=i.getProgramInfoLog(y)||"",D=i.getShaderInfoLog(S)||"",N=i.getShaderInfoLog(w)||"",U=C.trim(),B=D.trim(),J=N.trim(),V=!0,ne=!0;if(i.getProgramParameter(y,i.LINK_STATUS)===!1)if(V=!1,typeof s.debug.onShaderError=="function")s.debug.onShaderError(i,y,S,w);else{let ue=Qf(i,S,"vertex"),_e=Qf(i,w,"fragment");console.error("THREE.WebGLProgram: Shader Error "+i.getError()+" - VALIDATE_STATUS "+i.getProgramParameter(y,i.VALIDATE_STATUS)+`

Material Name: `+I.name+`
Material Type: `+I.type+`

Program Info Log: `+U+`
`+ue+`
`+_e)}else U!==""?console.warn("THREE.WebGLProgram: Program Info Log:",U):(B===""||J==="")&&(ne=!1);ne&&(I.diagnostics={runnable:V,programLog:U,vertexShader:{log:B,prefix:m},fragmentShader:{log:J,prefix:p}})}i.deleteShader(S),i.deleteShader(w),A=new yr(i,y),M=Dx(i,y)}let A;this.getUniforms=function(){return A===void 0&&T(this),A};let M;this.getAttributes=function(){return M===void 0&&T(this),M};let _=t.rendererExtensionParallelShaderCompile===!1;return this.isReady=function(){return _===!1&&(_=i.getProgramParameter(y,Tx)),_},this.destroy=function(){n.releaseStatesOfProgram(this),i.deleteProgram(y),this.program=void 0},this.type=t.shaderType,this.name=t.shaderName,this.id=Ex++,this.cacheKey=e,this.usedTimes=1,this.program=y,this.vertexShader=S,this.fragmentShader=w,this}var Xx=0,Oh=class{constructor(){this.shaderCache=new Map,this.materialCache=new Map}update(e){let t=e.vertexShader,n=e.fragmentShader,i=this._getShaderStage(t),r=this._getShaderStage(n),a=this._getShaderCacheForMaterial(e);return a.has(i)===!1&&(a.add(i),i.usedTimes++),a.has(r)===!1&&(a.add(r),r.usedTimes++),this}remove(e){let t=this.materialCache.get(e);for(let n of t)n.usedTimes--,n.usedTimes===0&&this.shaderCache.delete(n.code);return this.materialCache.delete(e),this}getVertexShaderID(e){return this._getShaderStage(e.vertexShader).id}getFragmentShaderID(e){return this._getShaderStage(e.fragmentShader).id}dispose(){this.shaderCache.clear(),this.materialCache.clear()}_getShaderCacheForMaterial(e){let t=this.materialCache,n=t.get(e);return n===void 0&&(n=new Set,t.set(e,n)),n}_getShaderStage(e){let t=this.shaderCache,n=t.get(e);return n===void 0&&(n=new zh(e),t.set(e,n)),n}},zh=class{constructor(e){this.id=Xx++,this.code=e,this.usedTimes=0}};function qx(s,e,t,n,i,r,a){let o=new Qs,c=new Oh,l=new Set,u=[],h=i.logarithmicDepthBuffer,d=i.vertexTextures,f=i.precision,g={MeshDepthMaterial:"depth",MeshDistanceMaterial:"distanceRGBA",MeshNormalMaterial:"normal",MeshBasicMaterial:"basic",MeshLambertMaterial:"lambert",MeshPhongMaterial:"phong",MeshToonMaterial:"toon",MeshStandardMaterial:"physical",MeshPhysicalMaterial:"physical",MeshMatcapMaterial:"matcap",LineBasicMaterial:"basic",LineDashedMaterial:"dashed",PointsMaterial:"points",ShadowMaterial:"shadow",SpriteMaterial:"sprite"};function y(M){return l.add(M),M===0?"uv":`uv${M}`}function m(M,_,I,C,D){let N=C.fog,U=D.geometry,B=M.isMeshStandardMaterial?C.environment:null,J=(M.isMeshStandardMaterial?t:e).get(M.envMap||B),V=J&&J.mapping===Sa?J.image.height:null,ne=g[M.type];M.precision!==null&&(f=i.getMaxPrecision(M.precision),f!==M.precision&&console.warn("THREE.WebGLProgram.getParameters:",M.precision,"not supported, using",f,"instead."));let ue=U.morphAttributes.position||U.morphAttributes.normal||U.morphAttributes.color,_e=ue!==void 0?ue.length:0,ze=0;U.morphAttributes.position!==void 0&&(ze=1),U.morphAttributes.normal!==void 0&&(ze=2),U.morphAttributes.color!==void 0&&(ze=3);let $e,ht,Ye,Q;if(ne){let ut=ai[ne];$e=ut.vertexShader,ht=ut.fragmentShader}else $e=M.vertexShader,ht=M.fragmentShader,c.update(M),Ye=c.getVertexShaderID(M),Q=c.getFragmentShaderID(M);let te=s.getRenderTarget(),ve=s.state.buffers.depth.getReversed(),Fe=D.isInstancedMesh===!0,Se=D.isBatchedMesh===!0,je=!!M.map,Z=!!M.matcap,P=!!J,ae=!!M.aoMap,me=!!M.lightMap,fe=!!M.bumpMap,W=!!M.normalMap,de=!!M.displacementMap,j=!!M.emissiveMap,re=!!M.metalnessMap,Ie=!!M.roughnessMap,Te=M.anisotropy>0,k=M.clearcoat>0,E=M.dispersion>0,O=M.iridescence>0,q=M.sheen>0,ee=M.transmission>0,K=Te&&!!M.anisotropyMap,Me=k&&!!M.clearcoatMap,he=k&&!!M.clearcoatNormalMap,Ee=k&&!!M.clearcoatRoughnessMap,Pe=O&&!!M.iridescenceMap,oe=O&&!!M.iridescenceThicknessMap,ge=q&&!!M.sheenColorMap,De=q&&!!M.sheenRoughnessMap,Ae=!!M.specularMap,pe=!!M.specularColorMap,Ve=!!M.specularIntensityMap,F=ee&&!!M.transmissionMap,se=ee&&!!M.thicknessMap,ce=!!M.gradientMap,xe=!!M.alphaMap,ie=M.alphaTest>0,$=!!M.alphaHash,Ce=!!M.extensions,Xe=Ei;M.toneMapped&&(te===null||te.isXRRenderTarget===!0)&&(Xe=s.toneMapping);let wt={shaderID:ne,shaderType:M.type,shaderName:M.name,vertexShader:$e,fragmentShader:ht,defines:M.defines,customVertexShaderID:Ye,customFragmentShaderID:Q,isRawShaderMaterial:M.isRawShaderMaterial===!0,glslVersion:M.glslVersion,precision:f,batching:Se,batchingColor:Se&&D._colorsTexture!==null,instancing:Fe,instancingColor:Fe&&D.instanceColor!==null,instancingMorph:Fe&&D.morphTexture!==null,supportsVertexTextures:d,outputColorSpace:te===null?s.outputColorSpace:te.isXRRenderTarget===!0?te.texture.colorSpace:Kt,alphaToCoverage:!!M.alphaToCoverage,map:je,matcap:Z,envMap:P,envMapMode:P&&J.mapping,envMapCubeUVHeight:V,aoMap:ae,lightMap:me,bumpMap:fe,normalMap:W,displacementMap:d&&de,emissiveMap:j,normalMapObjectSpace:W&&M.normalMapType===Tf,normalMapTangentSpace:W&&M.normalMapType===Nc,metalnessMap:re,roughnessMap:Ie,anisotropy:Te,anisotropyMap:K,clearcoat:k,clearcoatMap:Me,clearcoatNormalMap:he,clearcoatRoughnessMap:Ee,dispersion:E,iridescence:O,iridescenceMap:Pe,iridescenceThicknessMap:oe,sheen:q,sheenColorMap:ge,sheenRoughnessMap:De,specularMap:Ae,specularColorMap:pe,specularIntensityMap:Ve,transmission:ee,transmissionMap:F,thicknessMap:se,gradientMap:ce,opaque:M.transparent===!1&&M.blending===es&&M.alphaToCoverage===!1,alphaMap:xe,alphaTest:ie,alphaHash:$,combine:M.combine,mapUv:je&&y(M.map.channel),aoMapUv:ae&&y(M.aoMap.channel),lightMapUv:me&&y(M.lightMap.channel),bumpMapUv:fe&&y(M.bumpMap.channel),normalMapUv:W&&y(M.normalMap.channel),displacementMapUv:de&&y(M.displacementMap.channel),emissiveMapUv:j&&y(M.emissiveMap.channel),metalnessMapUv:re&&y(M.metalnessMap.channel),roughnessMapUv:Ie&&y(M.roughnessMap.channel),anisotropyMapUv:K&&y(M.anisotropyMap.channel),clearcoatMapUv:Me&&y(M.clearcoatMap.channel),clearcoatNormalMapUv:he&&y(M.clearcoatNormalMap.channel),clearcoatRoughnessMapUv:Ee&&y(M.clearcoatRoughnessMap.channel),iridescenceMapUv:Pe&&y(M.iridescenceMap.channel),iridescenceThicknessMapUv:oe&&y(M.iridescenceThicknessMap.channel),sheenColorMapUv:ge&&y(M.sheenColorMap.channel),sheenRoughnessMapUv:De&&y(M.sheenRoughnessMap.channel),specularMapUv:Ae&&y(M.specularMap.channel),specularColorMapUv:pe&&y(M.specularColorMap.channel),specularIntensityMapUv:Ve&&y(M.specularIntensityMap.channel),transmissionMapUv:F&&y(M.transmissionMap.channel),thicknessMapUv:se&&y(M.thicknessMap.channel),alphaMapUv:xe&&y(M.alphaMap.channel),vertexTangents:!!U.attributes.tangent&&(W||Te),vertexColors:M.vertexColors,vertexAlphas:M.vertexColors===!0&&!!U.attributes.color&&U.attributes.color.itemSize===4,pointsUvs:D.isPoints===!0&&!!U.attributes.uv&&(je||xe),fog:!!N,useFog:M.fog===!0,fogExp2:!!N&&N.isFogExp2,flatShading:M.flatShading===!0&&M.wireframe===!1,sizeAttenuation:M.sizeAttenuation===!0,logarithmicDepthBuffer:h,reversedDepthBuffer:ve,skinning:D.isSkinnedMesh===!0,morphTargets:U.morphAttributes.position!==void 0,morphNormals:U.morphAttributes.normal!==void 0,morphColors:U.morphAttributes.color!==void 0,morphTargetsCount:_e,morphTextureStride:ze,numDirLights:_.directional.length,numPointLights:_.point.length,numSpotLights:_.spot.length,numSpotLightMaps:_.spotLightMap.length,numRectAreaLights:_.rectArea.length,numHemiLights:_.hemi.length,numDirLightShadows:_.directionalShadowMap.length,numPointLightShadows:_.pointShadowMap.length,numSpotLightShadows:_.spotShadowMap.length,numSpotLightShadowsWithMaps:_.numSpotLightShadowsWithMaps,numLightProbes:_.numLightProbes,numClippingPlanes:a.numPlanes,numClipIntersection:a.numIntersection,dithering:M.dithering,shadowMapEnabled:s.shadowMap.enabled&&I.length>0,shadowMapType:s.shadowMap.type,toneMapping:Xe,decodeVideoTexture:je&&M.map.isVideoTexture===!0&&et.getTransfer(M.map.colorSpace)===pt,decodeVideoTextureEmissive:j&&M.emissiveMap.isVideoTexture===!0&&et.getTransfer(M.emissiveMap.colorSpace)===pt,premultipliedAlpha:M.premultipliedAlpha,doubleSided:M.side===Mt,flipSided:M.side===Dt,useDepthPacking:M.depthPacking>=0,depthPacking:M.depthPacking||0,index0AttributeName:M.index0AttributeName,extensionClipCullDistance:Ce&&M.extensions.clipCullDistance===!0&&n.has("WEBGL_clip_cull_distance"),extensionMultiDraw:(Ce&&M.extensions.multiDraw===!0||Se)&&n.has("WEBGL_multi_draw"),rendererExtensionParallelShaderCompile:n.has("KHR_parallel_shader_compile"),customProgramCacheKey:M.customProgramCacheKey()};return wt.vertexUv1s=l.has(1),wt.vertexUv2s=l.has(2),wt.vertexUv3s=l.has(3),l.clear(),wt}function p(M){let _=[];if(M.shaderID?_.push(M.shaderID):(_.push(M.customVertexShaderID),_.push(M.customFragmentShaderID)),M.defines!==void 0)for(let I in M.defines)_.push(I),_.push(M.defines[I]);return M.isRawShaderMaterial===!1&&(x(_,M),v(_,M),_.push(s.outputColorSpace)),_.push(M.customProgramCacheKey),_.join()}function x(M,_){M.push(_.precision),M.push(_.outputColorSpace),M.push(_.envMapMode),M.push(_.envMapCubeUVHeight),M.push(_.mapUv),M.push(_.alphaMapUv),M.push(_.lightMapUv),M.push(_.aoMapUv),M.push(_.bumpMapUv),M.push(_.normalMapUv),M.push(_.displacementMapUv),M.push(_.emissiveMapUv),M.push(_.metalnessMapUv),M.push(_.roughnessMapUv),M.push(_.anisotropyMapUv),M.push(_.clearcoatMapUv),M.push(_.clearcoatNormalMapUv),M.push(_.clearcoatRoughnessMapUv),M.push(_.iridescenceMapUv),M.push(_.iridescenceThicknessMapUv),M.push(_.sheenColorMapUv),M.push(_.sheenRoughnessMapUv),M.push(_.specularMapUv),M.push(_.specularColorMapUv),M.push(_.specularIntensityMapUv),M.push(_.transmissionMapUv),M.push(_.thicknessMapUv),M.push(_.combine),M.push(_.fogExp2),M.push(_.sizeAttenuation),M.push(_.morphTargetsCount),M.push(_.morphAttributeCount),M.push(_.numDirLights),M.push(_.numPointLights),M.push(_.numSpotLights),M.push(_.numSpotLightMaps),M.push(_.numHemiLights),M.push(_.numRectAreaLights),M.push(_.numDirLightShadows),M.push(_.numPointLightShadows),M.push(_.numSpotLightShadows),M.push(_.numSpotLightShadowsWithMaps),M.push(_.numLightProbes),M.push(_.shadowMapType),M.push(_.toneMapping),M.push(_.numClippingPlanes),M.push(_.numClipIntersection),M.push(_.depthPacking)}function v(M,_){o.disableAll(),_.supportsVertexTextures&&o.enable(0),_.instancing&&o.enable(1),_.instancingColor&&o.enable(2),_.instancingMorph&&o.enable(3),_.matcap&&o.enable(4),_.envMap&&o.enable(5),_.normalMapObjectSpace&&o.enable(6),_.normalMapTangentSpace&&o.enable(7),_.clearcoat&&o.enable(8),_.iridescence&&o.enable(9),_.alphaTest&&o.enable(10),_.vertexColors&&o.enable(11),_.vertexAlphas&&o.enable(12),_.vertexUv1s&&o.enable(13),_.vertexUv2s&&o.enable(14),_.vertexUv3s&&o.enable(15),_.vertexTangents&&o.enable(16),_.anisotropy&&o.enable(17),_.alphaHash&&o.enable(18),_.batching&&o.enable(19),_.dispersion&&o.enable(20),_.batchingColor&&o.enable(21),_.gradientMap&&o.enable(22),M.push(o.mask),o.disableAll(),_.fog&&o.enable(0),_.useFog&&o.enable(1),_.flatShading&&o.enable(2),_.logarithmicDepthBuffer&&o.enable(3),_.reversedDepthBuffer&&o.enable(4),_.skinning&&o.enable(5),_.morphTargets&&o.enable(6),_.morphNormals&&o.enable(7),_.morphColors&&o.enable(8),_.premultipliedAlpha&&o.enable(9),_.shadowMapEnabled&&o.enable(10),_.doubleSided&&o.enable(11),_.flipSided&&o.enable(12),_.useDepthPacking&&o.enable(13),_.dithering&&o.enable(14),_.transmission&&o.enable(15),_.sheen&&o.enable(16),_.opaque&&o.enable(17),_.pointsUvs&&o.enable(18),_.decodeVideoTexture&&o.enable(19),_.decodeVideoTextureEmissive&&o.enable(20),_.alphaToCoverage&&o.enable(21),M.push(o.mask)}function b(M){let _=g[M.type],I;if(_){let C=ai[_];I=Fc.clone(C.uniforms)}else I=M.uniforms;return I}function S(M,_){let I;for(let C=0,D=u.length;C<D;C++){let N=u[C];if(N.cacheKey===_){I=N,++I.usedTimes;break}}return I===void 0&&(I=new Yx(s,_,M,r),u.push(I)),I}function w(M){if(--M.usedTimes===0){let _=u.indexOf(M);u[_]=u[u.length-1],u.pop(),M.destroy()}}function T(M){c.remove(M)}function A(){c.dispose()}return{getParameters:m,getProgramCacheKey:p,getUniforms:b,acquireProgram:S,releaseProgram:w,releaseShaderCache:T,programs:u,dispose:A}}function jx(){let s=new WeakMap;function e(a){return s.has(a)}function t(a){let o=s.get(a);return o===void 0&&(o={},s.set(a,o)),o}function n(a){s.delete(a)}function i(a,o,c){s.get(a)[o]=c}function r(){s=new WeakMap}return{has:e,get:t,remove:n,update:i,dispose:r}}function Kx(s,e){return s.groupOrder!==e.groupOrder?s.groupOrder-e.groupOrder:s.renderOrder!==e.renderOrder?s.renderOrder-e.renderOrder:s.material.id!==e.material.id?s.material.id-e.material.id:s.z!==e.z?s.z-e.z:s.id-e.id}function sp(s,e){return s.groupOrder!==e.groupOrder?s.groupOrder-e.groupOrder:s.renderOrder!==e.renderOrder?s.renderOrder-e.renderOrder:s.z!==e.z?e.z-s.z:s.id-e.id}function rp(){let s=[],e=0,t=[],n=[],i=[];function r(){e=0,t.length=0,n.length=0,i.length=0}function a(h,d,f,g,y,m){let p=s[e];return p===void 0?(p={id:h.id,object:h,geometry:d,material:f,groupOrder:g,renderOrder:h.renderOrder,z:y,group:m},s[e]=p):(p.id=h.id,p.object=h,p.geometry=d,p.material=f,p.groupOrder=g,p.renderOrder=h.renderOrder,p.z=y,p.group=m),e++,p}function o(h,d,f,g,y,m){let p=a(h,d,f,g,y,m);f.transmission>0?n.push(p):f.transparent===!0?i.push(p):t.push(p)}function c(h,d,f,g,y,m){let p=a(h,d,f,g,y,m);f.transmission>0?n.unshift(p):f.transparent===!0?i.unshift(p):t.unshift(p)}function l(h,d){t.length>1&&t.sort(h||Kx),n.length>1&&n.sort(d||sp),i.length>1&&i.sort(d||sp)}function u(){for(let h=e,d=s.length;h<d;h++){let f=s[h];if(f.id===null)break;f.id=null,f.object=null,f.geometry=null,f.material=null,f.group=null}}return{opaque:t,transmissive:n,transparent:i,init:r,push:o,unshift:c,finish:u,sort:l}}function Zx(){let s=new WeakMap;function e(n,i){let r=s.get(n),a;return r===void 0?(a=new rp,s.set(n,[a])):i>=r.length?(a=new rp,r.push(a)):a=r[i],a}function t(){s=new WeakMap}return{get:e,dispose:t}}function Jx(){let s={};return{get:function(e){if(s[e.id]!==void 0)return s[e.id];let t;switch(e.type){case"DirectionalLight":t={direction:new L,color:new Ue};break;case"SpotLight":t={position:new L,direction:new L,color:new Ue,distance:0,coneCos:0,penumbraCos:0,decay:0};break;case"PointLight":t={position:new L,color:new Ue,distance:0,decay:0};break;case"HemisphereLight":t={direction:new L,skyColor:new Ue,groundColor:new Ue};break;case"RectAreaLight":t={color:new Ue,position:new L,halfWidth:new L,halfHeight:new L};break}return s[e.id]=t,t}}}function $x(){let s={};return{get:function(e){if(s[e.id]!==void 0)return s[e.id];let t;switch(e.type){case"DirectionalLight":t={shadowIntensity:1,shadowBias:0,shadowNormalBias:0,shadowRadius:1,shadowMapSize:new Ne};break;case"SpotLight":t={shadowIntensity:1,shadowBias:0,shadowNormalBias:0,shadowRadius:1,shadowMapSize:new Ne};break;case"PointLight":t={shadowIntensity:1,shadowBias:0,shadowNormalBias:0,shadowRadius:1,shadowMapSize:new Ne,shadowCameraNear:1,shadowCameraFar:1e3};break}return s[e.id]=t,t}}}var Qx=0;function ev(s,e){return(e.castShadow?2:0)-(s.castShadow?2:0)+(e.map?1:0)-(s.map?1:0)}function tv(s){let e=new Jx,t=$x(),n={version:0,hash:{directionalLength:-1,pointLength:-1,spotLength:-1,rectAreaLength:-1,hemiLength:-1,numDirectionalShadows:-1,numPointShadows:-1,numSpotShadows:-1,numSpotMaps:-1,numLightProbes:-1},ambient:[0,0,0],probe:[],directional:[],directionalShadow:[],directionalShadowMap:[],directionalShadowMatrix:[],spot:[],spotLightMap:[],spotShadow:[],spotShadowMap:[],spotLightMatrix:[],rectArea:[],rectAreaLTC1:null,rectAreaLTC2:null,point:[],pointShadow:[],pointShadowMap:[],pointShadowMatrix:[],hemi:[],numSpotLightShadowsWithMaps:0,numLightProbes:0};for(let l=0;l<9;l++)n.probe.push(new L);let i=new L,r=new ke,a=new ke;function o(l){let u=0,h=0,d=0;for(let M=0;M<9;M++)n.probe[M].set(0,0,0);let f=0,g=0,y=0,m=0,p=0,x=0,v=0,b=0,S=0,w=0,T=0;l.sort(ev);for(let M=0,_=l.length;M<_;M++){let I=l[M],C=I.color,D=I.intensity,N=I.distance,U=I.shadow&&I.shadow.map?I.shadow.map.texture:null;if(I.isAmbientLight)u+=C.r*D,h+=C.g*D,d+=C.b*D;else if(I.isLightProbe){for(let B=0;B<9;B++)n.probe[B].addScaledVector(I.sh.coefficients[B],D);T++}else if(I.isDirectionalLight){let B=e.get(I);if(B.color.copy(I.color).multiplyScalar(I.intensity),I.castShadow){let J=I.shadow,V=t.get(I);V.shadowIntensity=J.intensity,V.shadowBias=J.bias,V.shadowNormalBias=J.normalBias,V.shadowRadius=J.radius,V.shadowMapSize=J.mapSize,n.directionalShadow[f]=V,n.directionalShadowMap[f]=U,n.directionalShadowMatrix[f]=I.shadow.matrix,x++}n.directional[f]=B,f++}else if(I.isSpotLight){let B=e.get(I);B.position.setFromMatrixPosition(I.matrixWorld),B.color.copy(C).multiplyScalar(D),B.distance=N,B.coneCos=Math.cos(I.angle),B.penumbraCos=Math.cos(I.angle*(1-I.penumbra)),B.decay=I.decay,n.spot[y]=B;let J=I.shadow;if(I.map&&(n.spotLightMap[S]=I.map,S++,J.updateMatrices(I),I.castShadow&&w++),n.spotLightMatrix[y]=J.matrix,I.castShadow){let V=t.get(I);V.shadowIntensity=J.intensity,V.shadowBias=J.bias,V.shadowNormalBias=J.normalBias,V.shadowRadius=J.radius,V.shadowMapSize=J.mapSize,n.spotShadow[y]=V,n.spotShadowMap[y]=U,b++}y++}else if(I.isRectAreaLight){let B=e.get(I);B.color.copy(C).multiplyScalar(D),B.halfWidth.set(I.width*.5,0,0),B.halfHeight.set(0,I.height*.5,0),n.rectArea[m]=B,m++}else if(I.isPointLight){let B=e.get(I);if(B.color.copy(I.color).multiplyScalar(I.intensity),B.distance=I.distance,B.decay=I.decay,I.castShadow){let J=I.shadow,V=t.get(I);V.shadowIntensity=J.intensity,V.shadowBias=J.bias,V.shadowNormalBias=J.normalBias,V.shadowRadius=J.radius,V.shadowMapSize=J.mapSize,V.shadowCameraNear=J.camera.near,V.shadowCameraFar=J.camera.far,n.pointShadow[g]=V,n.pointShadowMap[g]=U,n.pointShadowMatrix[g]=I.shadow.matrix,v++}n.point[g]=B,g++}else if(I.isHemisphereLight){let B=e.get(I);B.skyColor.copy(I.color).multiplyScalar(D),B.groundColor.copy(I.groundColor).multiplyScalar(D),n.hemi[p]=B,p++}}m>0&&(s.has("OES_texture_float_linear")===!0?(n.rectAreaLTC1=be.LTC_FLOAT_1,n.rectAreaLTC2=be.LTC_FLOAT_2):(n.rectAreaLTC1=be.LTC_HALF_1,n.rectAreaLTC2=be.LTC_HALF_2)),n.ambient[0]=u,n.ambient[1]=h,n.ambient[2]=d;let A=n.hash;(A.directionalLength!==f||A.pointLength!==g||A.spotLength!==y||A.rectAreaLength!==m||A.hemiLength!==p||A.numDirectionalShadows!==x||A.numPointShadows!==v||A.numSpotShadows!==b||A.numSpotMaps!==S||A.numLightProbes!==T)&&(n.directional.length=f,n.spot.length=y,n.rectArea.length=m,n.point.length=g,n.hemi.length=p,n.directionalShadow.length=x,n.directionalShadowMap.length=x,n.pointShadow.length=v,n.pointShadowMap.length=v,n.spotShadow.length=b,n.spotShadowMap.length=b,n.directionalShadowMatrix.length=x,n.pointShadowMatrix.length=v,n.spotLightMatrix.length=b+S-w,n.spotLightMap.length=S,n.numSpotLightShadowsWithMaps=w,n.numLightProbes=T,A.directionalLength=f,A.pointLength=g,A.spotLength=y,A.rectAreaLength=m,A.hemiLength=p,A.numDirectionalShadows=x,A.numPointShadows=v,A.numSpotShadows=b,A.numSpotMaps=S,A.numLightProbes=T,n.version=Qx++)}function c(l,u){let h=0,d=0,f=0,g=0,y=0,m=u.matrixWorldInverse;for(let p=0,x=l.length;p<x;p++){let v=l[p];if(v.isDirectionalLight){let b=n.directional[h];b.direction.setFromMatrixPosition(v.matrixWorld),i.setFromMatrixPosition(v.target.matrixWorld),b.direction.sub(i),b.direction.transformDirection(m),h++}else if(v.isSpotLight){let b=n.spot[f];b.position.setFromMatrixPosition(v.matrixWorld),b.position.applyMatrix4(m),b.direction.setFromMatrixPosition(v.matrixWorld),i.setFromMatrixPosition(v.target.matrixWorld),b.direction.sub(i),b.direction.transformDirection(m),f++}else if(v.isRectAreaLight){let b=n.rectArea[g];b.position.setFromMatrixPosition(v.matrixWorld),b.position.applyMatrix4(m),a.identity(),r.copy(v.matrixWorld),r.premultiply(m),a.extractRotation(r),b.halfWidth.set(v.width*.5,0,0),b.halfHeight.set(0,v.height*.5,0),b.halfWidth.applyMatrix4(a),b.halfHeight.applyMatrix4(a),g++}else if(v.isPointLight){let b=n.point[d];b.position.setFromMatrixPosition(v.matrixWorld),b.position.applyMatrix4(m),d++}else if(v.isHemisphereLight){let b=n.hemi[y];b.direction.setFromMatrixPosition(v.matrixWorld),b.direction.transformDirection(m),y++}}}return{setup:o,setupView:c,state:n}}function ap(s){let e=new tv(s),t=[],n=[];function i(u){l.camera=u,t.length=0,n.length=0}function r(u){t.push(u)}function a(u){n.push(u)}function o(){e.setup(t)}function c(u){e.setupView(t,u)}let l={lightsArray:t,shadowsArray:n,camera:null,lights:e,transmissionRenderTarget:{}};return{init:i,state:l,setupLights:o,setupLightsView:c,pushLight:r,pushShadow:a}}function nv(s){let e=new WeakMap;function t(i,r=0){let a=e.get(i),o;return a===void 0?(o=new ap(s),e.set(i,[o])):r>=a.length?(o=new ap(s),a.push(o)):o=a[r],o}function n(){e=new WeakMap}return{get:t,dispose:n}}var iv=`void main() {
	gl_Position = vec4( position, 1.0 );
}`,sv=`uniform sampler2D shadow_pass;
uniform vec2 resolution;
uniform float radius;
#include <packing>
void main() {
	const float samples = float( VSM_SAMPLES );
	float mean = 0.0;
	float squared_mean = 0.0;
	float uvStride = samples <= 1.0 ? 0.0 : 2.0 / ( samples - 1.0 );
	float uvStart = samples <= 1.0 ? 0.0 : - 1.0;
	for ( float i = 0.0; i < samples; i ++ ) {
		float uvOffset = uvStart + i * uvStride;
		#ifdef HORIZONTAL_PASS
			vec2 distribution = unpackRGBATo2Half( texture2D( shadow_pass, ( gl_FragCoord.xy + vec2( uvOffset, 0.0 ) * radius ) / resolution ) );
			mean += distribution.x;
			squared_mean += distribution.y * distribution.y + distribution.x * distribution.x;
		#else
			float depth = unpackRGBAToDepth( texture2D( shadow_pass, ( gl_FragCoord.xy + vec2( 0.0, uvOffset ) * radius ) / resolution ) );
			mean += depth;
			squared_mean += depth * depth;
		#endif
	}
	mean = mean / samples;
	squared_mean = squared_mean / samples;
	float std_dev = sqrt( squared_mean - mean * mean );
	gl_FragColor = pack2HalfToRGBA( vec2( mean, std_dev ) );
}`;function rv(s,e,t){let n=new rr,i=new Ne,r=new Ne,a=new tt,o=new Lo({depthPacking:Sf}),c=new Do,l={},u=t.maxTextureSize,h={[pn]:Dt,[Dt]:pn,[Mt]:Mt},d=new Yt({defines:{VSM_SAMPLES:8},uniforms:{shadow_pass:{value:null},resolution:{value:new Ne},radius:{value:4}},vertexShader:iv,fragmentShader:sv}),f=d.clone();f.defines.HORIZONTAL_PASS=1;let g=new Bt;g.setAttribute("position",new xt(new Float32Array([-1,-1,.5,3,-1,.5,-1,3,.5]),3));let y=new at(g,d),m=this;this.enabled=!1,this.autoUpdate=!0,this.needsUpdate=!1,this.type=Ma;let p=this.type;this.render=function(w,T,A){if(m.enabled===!1||m.autoUpdate===!1&&m.needsUpdate===!1||w.length===0)return;let M=s.getRenderTarget(),_=s.getActiveCubeFace(),I=s.getActiveMipmapLevel(),C=s.state;C.setBlending(Ti),C.buffers.depth.getReversed()===!0?C.buffers.color.setClear(0,0,0,0):C.buffers.color.setClear(1,1,1,1),C.buffers.depth.setTest(!0),C.setScissorTest(!1);let D=p!==ri&&this.type===ri,N=p===ri&&this.type!==ri;for(let U=0,B=w.length;U<B;U++){let J=w[U],V=J.shadow;if(V===void 0){console.warn("THREE.WebGLShadowMap:",J,"has no shadow.");continue}if(V.autoUpdate===!1&&V.needsUpdate===!1)continue;i.copy(V.mapSize);let ne=V.getFrameExtents();if(i.multiply(ne),r.copy(V.mapSize),(i.x>u||i.y>u)&&(i.x>u&&(r.x=Math.floor(u/ne.x),i.x=r.x*ne.x,V.mapSize.x=r.x),i.y>u&&(r.y=Math.floor(u/ne.y),i.y=r.y*ne.y,V.mapSize.y=r.y)),V.map===null||D===!0||N===!0){let _e=this.type!==ri?{minFilter:qt,magFilter:qt}:{};V.map!==null&&V.map.dispose(),V.map=new ei(i.x,i.y,_e),V.map.texture.name=J.name+".shadowMap",V.camera.updateProjectionMatrix()}s.setRenderTarget(V.map),s.clear();let ue=V.getViewportCount();for(let _e=0;_e<ue;_e++){let ze=V.getViewport(_e);a.set(r.x*ze.x,r.y*ze.y,r.x*ze.z,r.y*ze.w),C.viewport(a),V.updateMatrices(J,_e),n=V.getFrustum(),b(T,A,V.camera,J,this.type)}V.isPointLightShadow!==!0&&this.type===ri&&x(V,A),V.needsUpdate=!1}p=this.type,m.needsUpdate=!1,s.setRenderTarget(M,_,I)};function x(w,T){let A=e.update(y);d.defines.VSM_SAMPLES!==w.blurSamples&&(d.defines.VSM_SAMPLES=w.blurSamples,f.defines.VSM_SAMPLES=w.blurSamples,d.needsUpdate=!0,f.needsUpdate=!0),w.mapPass===null&&(w.mapPass=new ei(i.x,i.y)),d.uniforms.shadow_pass.value=w.map.texture,d.uniforms.resolution.value=w.mapSize,d.uniforms.radius.value=w.radius,s.setRenderTarget(w.mapPass),s.clear(),s.renderBufferDirect(T,null,A,d,y,null),f.uniforms.shadow_pass.value=w.mapPass.texture,f.uniforms.resolution.value=w.mapSize,f.uniforms.radius.value=w.radius,s.setRenderTarget(w.map),s.clear(),s.renderBufferDirect(T,null,A,f,y,null)}function v(w,T,A,M){let _=null,I=A.isPointLight===!0?w.customDistanceMaterial:w.customDepthMaterial;if(I!==void 0)_=I;else if(_=A.isPointLight===!0?c:o,s.localClippingEnabled&&T.clipShadows===!0&&Array.isArray(T.clippingPlanes)&&T.clippingPlanes.length!==0||T.displacementMap&&T.displacementScale!==0||T.alphaMap&&T.alphaTest>0||T.map&&T.alphaTest>0||T.alphaToCoverage===!0){let C=_.uuid,D=T.uuid,N=l[C];N===void 0&&(N={},l[C]=N);let U=N[D];U===void 0&&(U=_.clone(),N[D]=U,T.addEventListener("dispose",S)),_=U}if(_.visible=T.visible,_.wireframe=T.wireframe,M===ri?_.side=T.shadowSide!==null?T.shadowSide:T.side:_.side=T.shadowSide!==null?T.shadowSide:h[T.side],_.alphaMap=T.alphaMap,_.alphaTest=T.alphaToCoverage===!0?.5:T.alphaTest,_.map=T.map,_.clipShadows=T.clipShadows,_.clippingPlanes=T.clippingPlanes,_.clipIntersection=T.clipIntersection,_.displacementMap=T.displacementMap,_.displacementScale=T.displacementScale,_.displacementBias=T.displacementBias,_.wireframeLinewidth=T.wireframeLinewidth,_.linewidth=T.linewidth,A.isPointLight===!0&&_.isMeshDistanceMaterial===!0){let C=s.properties.get(_);C.light=A}return _}function b(w,T,A,M,_){if(w.visible===!1)return;if(w.layers.test(T.layers)&&(w.isMesh||w.isLine||w.isPoints)&&(w.castShadow||w.receiveShadow&&_===ri)&&(!w.frustumCulled||n.intersectsObject(w))){w.modelViewMatrix.multiplyMatrices(A.matrixWorldInverse,w.matrixWorld);let D=e.update(w),N=w.material;if(Array.isArray(N)){let U=D.groups;for(let B=0,J=U.length;B<J;B++){let V=U[B],ne=N[V.materialIndex];if(ne&&ne.visible){let ue=v(w,ne,M,_);w.onBeforeShadow(s,w,T,A,D,ue,V),s.renderBufferDirect(A,null,D,ue,w,V),w.onAfterShadow(s,w,T,A,D,ue,V)}}}else if(N.visible){let U=v(w,N,M,_);w.onBeforeShadow(s,w,T,A,D,U,null),s.renderBufferDirect(A,null,D,U,w,null),w.onAfterShadow(s,w,T,A,D,U,null)}}let C=w.children;for(let D=0,N=C.length;D<N;D++)b(C[D],T,A,M,_)}function S(w){w.target.removeEventListener("dispose",S);for(let A in l){let M=l[A],_=w.target.uuid;_ in M&&(M[_].dispose(),delete M[_])}}}var av={[Go]:Wo,[Yo]:jo,[Xo]:Ko,[ts]:qo,[Wo]:Go,[jo]:Yo,[Ko]:Xo,[qo]:ts};function ov(s,e){function t(){let F=!1,se=new tt,ce=null,xe=new tt(0,0,0,0);return{setMask:function(ie){ce!==ie&&!F&&(s.colorMask(ie,ie,ie,ie),ce=ie)},setLocked:function(ie){F=ie},setClear:function(ie,$,Ce,Xe,wt){wt===!0&&(ie*=Xe,$*=Xe,Ce*=Xe),se.set(ie,$,Ce,Xe),xe.equals(se)===!1&&(s.clearColor(ie,$,Ce,Xe),xe.copy(se))},reset:function(){F=!1,ce=null,xe.set(-1,0,0,0)}}}function n(){let F=!1,se=!1,ce=null,xe=null,ie=null;return{setReversed:function($){if(se!==$){let Ce=e.get("EXT_clip_control");$?Ce.clipControlEXT(Ce.LOWER_LEFT_EXT,Ce.ZERO_TO_ONE_EXT):Ce.clipControlEXT(Ce.LOWER_LEFT_EXT,Ce.NEGATIVE_ONE_TO_ONE_EXT),se=$;let Xe=ie;ie=null,this.setClear(Xe)}},getReversed:function(){return se},setTest:function($){$?te(s.DEPTH_TEST):ve(s.DEPTH_TEST)},setMask:function($){ce!==$&&!F&&(s.depthMask($),ce=$)},setFunc:function($){if(se&&($=av[$]),xe!==$){switch($){case Go:s.depthFunc(s.NEVER);break;case Wo:s.depthFunc(s.ALWAYS);break;case Yo:s.depthFunc(s.LESS);break;case ts:s.depthFunc(s.LEQUAL);break;case Xo:s.depthFunc(s.EQUAL);break;case qo:s.depthFunc(s.GEQUAL);break;case jo:s.depthFunc(s.GREATER);break;case Ko:s.depthFunc(s.NOTEQUAL);break;default:s.depthFunc(s.LEQUAL)}xe=$}},setLocked:function($){F=$},setClear:function($){ie!==$&&(se&&($=1-$),s.clearDepth($),ie=$)},reset:function(){F=!1,ce=null,xe=null,ie=null,se=!1}}}function i(){let F=!1,se=null,ce=null,xe=null,ie=null,$=null,Ce=null,Xe=null,wt=null;return{setTest:function(ut){F||(ut?te(s.STENCIL_TEST):ve(s.STENCIL_TEST))},setMask:function(ut){se!==ut&&!F&&(s.stencilMask(ut),se=ut)},setFunc:function(ut,hi,Jn){(ce!==ut||xe!==hi||ie!==Jn)&&(s.stencilFunc(ut,hi,Jn),ce=ut,xe=hi,ie=Jn)},setOp:function(ut,hi,Jn){($!==ut||Ce!==hi||Xe!==Jn)&&(s.stencilOp(ut,hi,Jn),$=ut,Ce=hi,Xe=Jn)},setLocked:function(ut){F=ut},setClear:function(ut){wt!==ut&&(s.clearStencil(ut),wt=ut)},reset:function(){F=!1,se=null,ce=null,xe=null,ie=null,$=null,Ce=null,Xe=null,wt=null}}}let r=new t,a=new n,o=new i,c=new WeakMap,l=new WeakMap,u={},h={},d=new WeakMap,f=[],g=null,y=!1,m=null,p=null,x=null,v=null,b=null,S=null,w=null,T=new Ue(0,0,0),A=0,M=!1,_=null,I=null,C=null,D=null,N=null,U=s.getParameter(s.MAX_COMBINED_TEXTURE_IMAGE_UNITS),B=!1,J=0,V=s.getParameter(s.VERSION);V.indexOf("WebGL")!==-1?(J=parseFloat(/^WebGL (\d)/.exec(V)[1]),B=J>=1):V.indexOf("OpenGL ES")!==-1&&(J=parseFloat(/^OpenGL ES (\d)/.exec(V)[1]),B=J>=2);let ne=null,ue={},_e=s.getParameter(s.SCISSOR_BOX),ze=s.getParameter(s.VIEWPORT),$e=new tt().fromArray(_e),ht=new tt().fromArray(ze);function Ye(F,se,ce,xe){let ie=new Uint8Array(4),$=s.createTexture();s.bindTexture(F,$),s.texParameteri(F,s.TEXTURE_MIN_FILTER,s.NEAREST),s.texParameteri(F,s.TEXTURE_MAG_FILTER,s.NEAREST);for(let Ce=0;Ce<ce;Ce++)F===s.TEXTURE_3D||F===s.TEXTURE_2D_ARRAY?s.texImage3D(se,0,s.RGBA,1,1,xe,0,s.RGBA,s.UNSIGNED_BYTE,ie):s.texImage2D(se+Ce,0,s.RGBA,1,1,0,s.RGBA,s.UNSIGNED_BYTE,ie);return $}let Q={};Q[s.TEXTURE_2D]=Ye(s.TEXTURE_2D,s.TEXTURE_2D,1),Q[s.TEXTURE_CUBE_MAP]=Ye(s.TEXTURE_CUBE_MAP,s.TEXTURE_CUBE_MAP_POSITIVE_X,6),Q[s.TEXTURE_2D_ARRAY]=Ye(s.TEXTURE_2D_ARRAY,s.TEXTURE_2D_ARRAY,1,1),Q[s.TEXTURE_3D]=Ye(s.TEXTURE_3D,s.TEXTURE_3D,1,1),r.setClear(0,0,0,1),a.setClear(1),o.setClear(0),te(s.DEPTH_TEST),a.setFunc(ts),fe(!1),W(lh),te(s.CULL_FACE),ae(Ti);function te(F){u[F]!==!0&&(s.enable(F),u[F]=!0)}function ve(F){u[F]!==!1&&(s.disable(F),u[F]=!1)}function Fe(F,se){return h[F]!==se?(s.bindFramebuffer(F,se),h[F]=se,F===s.DRAW_FRAMEBUFFER&&(h[s.FRAMEBUFFER]=se),F===s.FRAMEBUFFER&&(h[s.DRAW_FRAMEBUFFER]=se),!0):!1}function Se(F,se){let ce=f,xe=!1;if(F){ce=d.get(se),ce===void 0&&(ce=[],d.set(se,ce));let ie=F.textures;if(ce.length!==ie.length||ce[0]!==s.COLOR_ATTACHMENT0){for(let $=0,Ce=ie.length;$<Ce;$++)ce[$]=s.COLOR_ATTACHMENT0+$;ce.length=ie.length,xe=!0}}else ce[0]!==s.BACK&&(ce[0]=s.BACK,xe=!0);xe&&s.drawBuffers(ce)}function je(F){return g!==F?(s.useProgram(F),g=F,!0):!1}let Z={[Fi]:s.FUNC_ADD,[Kd]:s.FUNC_SUBTRACT,[Zd]:s.FUNC_REVERSE_SUBTRACT};Z[Jd]=s.MIN,Z[$d]=s.MAX;let P={[Qd]:s.ZERO,[ef]:s.ONE,[tf]:s.SRC_COLOR,[Mo]:s.SRC_ALPHA,[cf]:s.SRC_ALPHA_SATURATE,[af]:s.DST_COLOR,[sf]:s.DST_ALPHA,[nf]:s.ONE_MINUS_SRC_COLOR,[So]:s.ONE_MINUS_SRC_ALPHA,[of]:s.ONE_MINUS_DST_COLOR,[rf]:s.ONE_MINUS_DST_ALPHA,[lf]:s.CONSTANT_COLOR,[hf]:s.ONE_MINUS_CONSTANT_COLOR,[uf]:s.CONSTANT_ALPHA,[df]:s.ONE_MINUS_CONSTANT_ALPHA};function ae(F,se,ce,xe,ie,$,Ce,Xe,wt,ut){if(F===Ti){y===!0&&(ve(s.BLEND),y=!1);return}if(y===!1&&(te(s.BLEND),y=!0),F!==jd){if(F!==m||ut!==M){if((p!==Fi||b!==Fi)&&(s.blendEquation(s.FUNC_ADD),p=Fi,b=Fi),ut)switch(F){case es:s.blendFuncSeparate(s.ONE,s.ONE_MINUS_SRC_ALPHA,s.ONE,s.ONE_MINUS_SRC_ALPHA);break;case ds:s.blendFunc(s.ONE,s.ONE);break;case hh:s.blendFuncSeparate(s.ZERO,s.ONE_MINUS_SRC_COLOR,s.ZERO,s.ONE);break;case uh:s.blendFuncSeparate(s.DST_COLOR,s.ONE_MINUS_SRC_ALPHA,s.ZERO,s.ONE);break;default:console.error("THREE.WebGLState: Invalid blending: ",F);break}else switch(F){case es:s.blendFuncSeparate(s.SRC_ALPHA,s.ONE_MINUS_SRC_ALPHA,s.ONE,s.ONE_MINUS_SRC_ALPHA);break;case ds:s.blendFuncSeparate(s.SRC_ALPHA,s.ONE,s.ONE,s.ONE);break;case hh:console.error("THREE.WebGLState: SubtractiveBlending requires material.premultipliedAlpha = true");break;case uh:console.error("THREE.WebGLState: MultiplyBlending requires material.premultipliedAlpha = true");break;default:console.error("THREE.WebGLState: Invalid blending: ",F);break}x=null,v=null,S=null,w=null,T.set(0,0,0),A=0,m=F,M=ut}return}ie=ie||se,$=$||ce,Ce=Ce||xe,(se!==p||ie!==b)&&(s.blendEquationSeparate(Z[se],Z[ie]),p=se,b=ie),(ce!==x||xe!==v||$!==S||Ce!==w)&&(s.blendFuncSeparate(P[ce],P[xe],P[$],P[Ce]),x=ce,v=xe,S=$,w=Ce),(Xe.equals(T)===!1||wt!==A)&&(s.blendColor(Xe.r,Xe.g,Xe.b,wt),T.copy(Xe),A=wt),m=F,M=!1}function me(F,se){F.side===Mt?ve(s.CULL_FACE):te(s.CULL_FACE);let ce=F.side===Dt;se&&(ce=!ce),fe(ce),F.blending===es&&F.transparent===!1?ae(Ti):ae(F.blending,F.blendEquation,F.blendSrc,F.blendDst,F.blendEquationAlpha,F.blendSrcAlpha,F.blendDstAlpha,F.blendColor,F.blendAlpha,F.premultipliedAlpha),a.setFunc(F.depthFunc),a.setTest(F.depthTest),a.setMask(F.depthWrite),r.setMask(F.colorWrite);let xe=F.stencilWrite;o.setTest(xe),xe&&(o.setMask(F.stencilWriteMask),o.setFunc(F.stencilFunc,F.stencilRef,F.stencilFuncMask),o.setOp(F.stencilFail,F.stencilZFail,F.stencilZPass)),j(F.polygonOffset,F.polygonOffsetFactor,F.polygonOffsetUnits),F.alphaToCoverage===!0?te(s.SAMPLE_ALPHA_TO_COVERAGE):ve(s.SAMPLE_ALPHA_TO_COVERAGE)}function fe(F){_!==F&&(F?s.frontFace(s.CW):s.frontFace(s.CCW),_=F)}function W(F){F!==Xd?(te(s.CULL_FACE),F!==I&&(F===lh?s.cullFace(s.BACK):F===qd?s.cullFace(s.FRONT):s.cullFace(s.FRONT_AND_BACK))):ve(s.CULL_FACE),I=F}function de(F){F!==C&&(B&&s.lineWidth(F),C=F)}function j(F,se,ce){F?(te(s.POLYGON_OFFSET_FILL),(D!==se||N!==ce)&&(s.polygonOffset(se,ce),D=se,N=ce)):ve(s.POLYGON_OFFSET_FILL)}function re(F){F?te(s.SCISSOR_TEST):ve(s.SCISSOR_TEST)}function Ie(F){F===void 0&&(F=s.TEXTURE0+U-1),ne!==F&&(s.activeTexture(F),ne=F)}function Te(F,se,ce){ce===void 0&&(ne===null?ce=s.TEXTURE0+U-1:ce=ne);let xe=ue[ce];xe===void 0&&(xe={type:void 0,texture:void 0},ue[ce]=xe),(xe.type!==F||xe.texture!==se)&&(ne!==ce&&(s.activeTexture(ce),ne=ce),s.bindTexture(F,se||Q[F]),xe.type=F,xe.texture=se)}function k(){let F=ue[ne];F!==void 0&&F.type!==void 0&&(s.bindTexture(F.type,null),F.type=void 0,F.texture=void 0)}function E(){try{s.compressedTexImage2D(...arguments)}catch(F){console.error("THREE.WebGLState:",F)}}function O(){try{s.compressedTexImage3D(...arguments)}catch(F){console.error("THREE.WebGLState:",F)}}function q(){try{s.texSubImage2D(...arguments)}catch(F){console.error("THREE.WebGLState:",F)}}function ee(){try{s.texSubImage3D(...arguments)}catch(F){console.error("THREE.WebGLState:",F)}}function K(){try{s.compressedTexSubImage2D(...arguments)}catch(F){console.error("THREE.WebGLState:",F)}}function Me(){try{s.compressedTexSubImage3D(...arguments)}catch(F){console.error("THREE.WebGLState:",F)}}function he(){try{s.texStorage2D(...arguments)}catch(F){console.error("THREE.WebGLState:",F)}}function Ee(){try{s.texStorage3D(...arguments)}catch(F){console.error("THREE.WebGLState:",F)}}function Pe(){try{s.texImage2D(...arguments)}catch(F){console.error("THREE.WebGLState:",F)}}function oe(){try{s.texImage3D(...arguments)}catch(F){console.error("THREE.WebGLState:",F)}}function ge(F){$e.equals(F)===!1&&(s.scissor(F.x,F.y,F.z,F.w),$e.copy(F))}function De(F){ht.equals(F)===!1&&(s.viewport(F.x,F.y,F.z,F.w),ht.copy(F))}function Ae(F,se){let ce=l.get(se);ce===void 0&&(ce=new WeakMap,l.set(se,ce));let xe=ce.get(F);xe===void 0&&(xe=s.getUniformBlockIndex(se,F.name),ce.set(F,xe))}function pe(F,se){let xe=l.get(se).get(F);c.get(se)!==xe&&(s.uniformBlockBinding(se,xe,F.__bindingPointIndex),c.set(se,xe))}function Ve(){s.disable(s.BLEND),s.disable(s.CULL_FACE),s.disable(s.DEPTH_TEST),s.disable(s.POLYGON_OFFSET_FILL),s.disable(s.SCISSOR_TEST),s.disable(s.STENCIL_TEST),s.disable(s.SAMPLE_ALPHA_TO_COVERAGE),s.blendEquation(s.FUNC_ADD),s.blendFunc(s.ONE,s.ZERO),s.blendFuncSeparate(s.ONE,s.ZERO,s.ONE,s.ZERO),s.blendColor(0,0,0,0),s.colorMask(!0,!0,!0,!0),s.clearColor(0,0,0,0),s.depthMask(!0),s.depthFunc(s.LESS),a.setReversed(!1),s.clearDepth(1),s.stencilMask(4294967295),s.stencilFunc(s.ALWAYS,0,4294967295),s.stencilOp(s.KEEP,s.KEEP,s.KEEP),s.clearStencil(0),s.cullFace(s.BACK),s.frontFace(s.CCW),s.polygonOffset(0,0),s.activeTexture(s.TEXTURE0),s.bindFramebuffer(s.FRAMEBUFFER,null),s.bindFramebuffer(s.DRAW_FRAMEBUFFER,null),s.bindFramebuffer(s.READ_FRAMEBUFFER,null),s.useProgram(null),s.lineWidth(1),s.scissor(0,0,s.canvas.width,s.canvas.height),s.viewport(0,0,s.canvas.width,s.canvas.height),u={},ne=null,ue={},h={},d=new WeakMap,f=[],g=null,y=!1,m=null,p=null,x=null,v=null,b=null,S=null,w=null,T=new Ue(0,0,0),A=0,M=!1,_=null,I=null,C=null,D=null,N=null,$e.set(0,0,s.canvas.width,s.canvas.height),ht.set(0,0,s.canvas.width,s.canvas.height),r.reset(),a.reset(),o.reset()}return{buffers:{color:r,depth:a,stencil:o},enable:te,disable:ve,bindFramebuffer:Fe,drawBuffers:Se,useProgram:je,setBlending:ae,setMaterial:me,setFlipSided:fe,setCullFace:W,setLineWidth:de,setPolygonOffset:j,setScissorTest:re,activeTexture:Ie,bindTexture:Te,unbindTexture:k,compressedTexImage2D:E,compressedTexImage3D:O,texImage2D:Pe,texImage3D:oe,updateUBOMapping:Ae,uniformBlockBinding:pe,texStorage2D:he,texStorage3D:Ee,texSubImage2D:q,texSubImage3D:ee,compressedTexSubImage2D:K,compressedTexSubImage3D:Me,scissor:ge,viewport:De,reset:Ve}}function cv(s,e,t,n,i,r,a){let o=e.has("WEBGL_multisampled_render_to_texture")?e.get("WEBGL_multisampled_render_to_texture"):null,c=typeof navigator>"u"?!1:/OculusBrowser/g.test(navigator.userAgent),l=new Ne,u=new WeakMap,h,d=new WeakMap,f=!1;try{f=typeof OffscreenCanvas<"u"&&new OffscreenCanvas(1,1).getContext("2d")!==null}catch{}function g(k,E){return f?new OffscreenCanvas(k,E):Zs("canvas")}function y(k,E,O){let q=1,ee=Te(k);if((ee.width>O||ee.height>O)&&(q=O/Math.max(ee.width,ee.height)),q<1)if(typeof HTMLImageElement<"u"&&k instanceof HTMLImageElement||typeof HTMLCanvasElement<"u"&&k instanceof HTMLCanvasElement||typeof ImageBitmap<"u"&&k instanceof ImageBitmap||typeof VideoFrame<"u"&&k instanceof VideoFrame){let K=Math.floor(q*ee.width),Me=Math.floor(q*ee.height);h===void 0&&(h=g(K,Me));let he=E?g(K,Me):h;return he.width=K,he.height=Me,he.getContext("2d").drawImage(k,0,0,K,Me),console.warn("THREE.WebGLRenderer: Texture has been resized from ("+ee.width+"x"+ee.height+") to ("+K+"x"+Me+")."),he}else return"data"in k&&console.warn("THREE.WebGLRenderer: Image in DataTexture is too big ("+ee.width+"x"+ee.height+")."),k;return k}function m(k){return k.generateMipmaps}function p(k){s.generateMipmap(k)}function x(k){return k.isWebGLCubeRenderTarget?s.TEXTURE_CUBE_MAP:k.isWebGL3DRenderTarget?s.TEXTURE_3D:k.isWebGLArrayRenderTarget||k.isCompressedArrayTexture?s.TEXTURE_2D_ARRAY:s.TEXTURE_2D}function v(k,E,O,q,ee=!1){if(k!==null){if(s[k]!==void 0)return s[k];console.warn("THREE.WebGLRenderer: Attempt to use non-existing WebGL internal format '"+k+"'")}let K=E;if(E===s.RED&&(O===s.FLOAT&&(K=s.R32F),O===s.HALF_FLOAT&&(K=s.R16F),O===s.UNSIGNED_BYTE&&(K=s.R8)),E===s.RED_INTEGER&&(O===s.UNSIGNED_BYTE&&(K=s.R8UI),O===s.UNSIGNED_SHORT&&(K=s.R16UI),O===s.UNSIGNED_INT&&(K=s.R32UI),O===s.BYTE&&(K=s.R8I),O===s.SHORT&&(K=s.R16I),O===s.INT&&(K=s.R32I)),E===s.RG&&(O===s.FLOAT&&(K=s.RG32F),O===s.HALF_FLOAT&&(K=s.RG16F),O===s.UNSIGNED_BYTE&&(K=s.RG8)),E===s.RG_INTEGER&&(O===s.UNSIGNED_BYTE&&(K=s.RG8UI),O===s.UNSIGNED_SHORT&&(K=s.RG16UI),O===s.UNSIGNED_INT&&(K=s.RG32UI),O===s.BYTE&&(K=s.RG8I),O===s.SHORT&&(K=s.RG16I),O===s.INT&&(K=s.RG32I)),E===s.RGB_INTEGER&&(O===s.UNSIGNED_BYTE&&(K=s.RGB8UI),O===s.UNSIGNED_SHORT&&(K=s.RGB16UI),O===s.UNSIGNED_INT&&(K=s.RGB32UI),O===s.BYTE&&(K=s.RGB8I),O===s.SHORT&&(K=s.RGB16I),O===s.INT&&(K=s.RGB32I)),E===s.RGBA_INTEGER&&(O===s.UNSIGNED_BYTE&&(K=s.RGBA8UI),O===s.UNSIGNED_SHORT&&(K=s.RGBA16UI),O===s.UNSIGNED_INT&&(K=s.RGBA32UI),O===s.BYTE&&(K=s.RGBA8I),O===s.SHORT&&(K=s.RGBA16I),O===s.INT&&(K=s.RGBA32I)),E===s.RGB&&(O===s.UNSIGNED_INT_5_9_9_9_REV&&(K=s.RGB9_E5),O===s.UNSIGNED_INT_10F_11F_11F_REV&&(K=s.R11F_G11F_B10F)),E===s.RGBA){let Me=ee?Kr:et.getTransfer(q);O===s.FLOAT&&(K=s.RGBA32F),O===s.HALF_FLOAT&&(K=s.RGBA16F),O===s.UNSIGNED_BYTE&&(K=Me===pt?s.SRGB8_ALPHA8:s.RGBA8),O===s.UNSIGNED_SHORT_4_4_4_4&&(K=s.RGBA4),O===s.UNSIGNED_SHORT_5_5_5_1&&(K=s.RGB5_A1)}return(K===s.R16F||K===s.R32F||K===s.RG16F||K===s.RG32F||K===s.RGBA16F||K===s.RGBA32F)&&e.get("EXT_color_buffer_float"),K}function b(k,E){let O;return k?E===null||E===Oi||E===dr?O=s.DEPTH24_STENCIL8:E===Fn?O=s.DEPTH32F_STENCIL8:E===ur&&(O=s.DEPTH24_STENCIL8,console.warn("DepthTexture: 16 bit depth attachment is not supported with stencil. Using 24-bit attachment.")):E===null||E===Oi||E===dr?O=s.DEPTH_COMPONENT24:E===Fn?O=s.DEPTH_COMPONENT32F:E===ur&&(O=s.DEPTH_COMPONENT16),O}function S(k,E){return m(k)===!0||k.isFramebufferTexture&&k.minFilter!==qt&&k.minFilter!==jt?Math.log2(Math.max(E.width,E.height))+1:k.mipmaps!==void 0&&k.mipmaps.length>0?k.mipmaps.length:k.isCompressedTexture&&Array.isArray(k.image)?E.mipmaps.length:1}function w(k){let E=k.target;E.removeEventListener("dispose",w),A(E),E.isVideoTexture&&u.delete(E)}function T(k){let E=k.target;E.removeEventListener("dispose",T),_(E)}function A(k){let E=n.get(k);if(E.__webglInit===void 0)return;let O=k.source,q=d.get(O);if(q){let ee=q[E.__cacheKey];ee.usedTimes--,ee.usedTimes===0&&M(k),Object.keys(q).length===0&&d.delete(O)}n.remove(k)}function M(k){let E=n.get(k);s.deleteTexture(E.__webglTexture);let O=k.source,q=d.get(O);delete q[E.__cacheKey],a.memory.textures--}function _(k){let E=n.get(k);if(k.depthTexture&&(k.depthTexture.dispose(),n.remove(k.depthTexture)),k.isWebGLCubeRenderTarget)for(let q=0;q<6;q++){if(Array.isArray(E.__webglFramebuffer[q]))for(let ee=0;ee<E.__webglFramebuffer[q].length;ee++)s.deleteFramebuffer(E.__webglFramebuffer[q][ee]);else s.deleteFramebuffer(E.__webglFramebuffer[q]);E.__webglDepthbuffer&&s.deleteRenderbuffer(E.__webglDepthbuffer[q])}else{if(Array.isArray(E.__webglFramebuffer))for(let q=0;q<E.__webglFramebuffer.length;q++)s.deleteFramebuffer(E.__webglFramebuffer[q]);else s.deleteFramebuffer(E.__webglFramebuffer);if(E.__webglDepthbuffer&&s.deleteRenderbuffer(E.__webglDepthbuffer),E.__webglMultisampledFramebuffer&&s.deleteFramebuffer(E.__webglMultisampledFramebuffer),E.__webglColorRenderbuffer)for(let q=0;q<E.__webglColorRenderbuffer.length;q++)E.__webglColorRenderbuffer[q]&&s.deleteRenderbuffer(E.__webglColorRenderbuffer[q]);E.__webglDepthRenderbuffer&&s.deleteRenderbuffer(E.__webglDepthRenderbuffer)}let O=k.textures;for(let q=0,ee=O.length;q<ee;q++){let K=n.get(O[q]);K.__webglTexture&&(s.deleteTexture(K.__webglTexture),a.memory.textures--),n.remove(O[q])}n.remove(k)}let I=0;function C(){I=0}function D(){let k=I;return k>=i.maxTextures&&console.warn("THREE.WebGLTextures: Trying to use "+k+" texture units while this GPU supports only "+i.maxTextures),I+=1,k}function N(k){let E=[];return E.push(k.wrapS),E.push(k.wrapT),E.push(k.wrapR||0),E.push(k.magFilter),E.push(k.minFilter),E.push(k.anisotropy),E.push(k.internalFormat),E.push(k.format),E.push(k.type),E.push(k.generateMipmaps),E.push(k.premultiplyAlpha),E.push(k.flipY),E.push(k.unpackAlignment),E.push(k.colorSpace),E.join()}function U(k,E){let O=n.get(k);if(k.isVideoTexture&&re(k),k.isRenderTargetTexture===!1&&k.isExternalTexture!==!0&&k.version>0&&O.__version!==k.version){let q=k.image;if(q===null)console.warn("THREE.WebGLRenderer: Texture marked for update but no image data found.");else if(q.complete===!1)console.warn("THREE.WebGLRenderer: Texture marked for update but image is incomplete");else{Q(O,k,E);return}}else k.isExternalTexture&&(O.__webglTexture=k.sourceTexture?k.sourceTexture:null);t.bindTexture(s.TEXTURE_2D,O.__webglTexture,s.TEXTURE0+E)}function B(k,E){let O=n.get(k);if(k.isRenderTargetTexture===!1&&k.version>0&&O.__version!==k.version){Q(O,k,E);return}t.bindTexture(s.TEXTURE_2D_ARRAY,O.__webglTexture,s.TEXTURE0+E)}function J(k,E){let O=n.get(k);if(k.isRenderTargetTexture===!1&&k.version>0&&O.__version!==k.version){Q(O,k,E);return}t.bindTexture(s.TEXTURE_3D,O.__webglTexture,s.TEXTURE0+E)}function V(k,E){let O=n.get(k);if(k.version>0&&O.__version!==k.version){te(O,k,E);return}t.bindTexture(s.TEXTURE_CUBE_MAP,O.__webglTexture,s.TEXTURE0+E)}let ne={[Ui]:s.REPEAT,[$n]:s.CLAMP_TO_EDGE,[js]:s.MIRRORED_REPEAT},ue={[qt]:s.NEAREST,[ec]:s.NEAREST_MIPMAP_NEAREST,[ms]:s.NEAREST_MIPMAP_LINEAR,[jt]:s.LINEAR,[hr]:s.LINEAR_MIPMAP_NEAREST,[qn]:s.LINEAR_MIPMAP_LINEAR},_e={[Ef]:s.NEVER,[kf]:s.ALWAYS,[Af]:s.LESS,[_h]:s.LEQUAL,[Rf]:s.EQUAL,[Pf]:s.GEQUAL,[Cf]:s.GREATER,[If]:s.NOTEQUAL};function ze(k,E){if(E.type===Fn&&e.has("OES_texture_float_linear")===!1&&(E.magFilter===jt||E.magFilter===hr||E.magFilter===ms||E.magFilter===qn||E.minFilter===jt||E.minFilter===hr||E.minFilter===ms||E.minFilter===qn)&&console.warn("THREE.WebGLRenderer: Unable to use linear filtering with floating point textures. OES_texture_float_linear not supported on this device."),s.texParameteri(k,s.TEXTURE_WRAP_S,ne[E.wrapS]),s.texParameteri(k,s.TEXTURE_WRAP_T,ne[E.wrapT]),(k===s.TEXTURE_3D||k===s.TEXTURE_2D_ARRAY)&&s.texParameteri(k,s.TEXTURE_WRAP_R,ne[E.wrapR]),s.texParameteri(k,s.TEXTURE_MAG_FILTER,ue[E.magFilter]),s.texParameteri(k,s.TEXTURE_MIN_FILTER,ue[E.minFilter]),E.compareFunction&&(s.texParameteri(k,s.TEXTURE_COMPARE_MODE,s.COMPARE_REF_TO_TEXTURE),s.texParameteri(k,s.TEXTURE_COMPARE_FUNC,_e[E.compareFunction])),e.has("EXT_texture_filter_anisotropic")===!0){if(E.magFilter===qt||E.minFilter!==ms&&E.minFilter!==qn||E.type===Fn&&e.has("OES_texture_float_linear")===!1)return;if(E.anisotropy>1||n.get(E).__currentAnisotropy){let O=e.get("EXT_texture_filter_anisotropic");s.texParameterf(k,O.TEXTURE_MAX_ANISOTROPY_EXT,Math.min(E.anisotropy,i.getMaxAnisotropy())),n.get(E).__currentAnisotropy=E.anisotropy}}}function $e(k,E){let O=!1;k.__webglInit===void 0&&(k.__webglInit=!0,E.addEventListener("dispose",w));let q=E.source,ee=d.get(q);ee===void 0&&(ee={},d.set(q,ee));let K=N(E);if(K!==k.__cacheKey){ee[K]===void 0&&(ee[K]={texture:s.createTexture(),usedTimes:0},a.memory.textures++,O=!0),ee[K].usedTimes++;let Me=ee[k.__cacheKey];Me!==void 0&&(ee[k.__cacheKey].usedTimes--,Me.usedTimes===0&&M(E)),k.__cacheKey=K,k.__webglTexture=ee[K].texture}return O}function ht(k,E,O){return Math.floor(Math.floor(k/O)/E)}function Ye(k,E,O,q){let K=k.updateRanges;if(K.length===0)t.texSubImage2D(s.TEXTURE_2D,0,0,0,E.width,E.height,O,q,E.data);else{K.sort((oe,ge)=>oe.start-ge.start);let Me=0;for(let oe=1;oe<K.length;oe++){let ge=K[Me],De=K[oe],Ae=ge.start+ge.count,pe=ht(De.start,E.width,4),Ve=ht(ge.start,E.width,4);De.start<=Ae+1&&pe===Ve&&ht(De.start+De.count-1,E.width,4)===pe?ge.count=Math.max(ge.count,De.start+De.count-ge.start):(++Me,K[Me]=De)}K.length=Me+1;let he=s.getParameter(s.UNPACK_ROW_LENGTH),Ee=s.getParameter(s.UNPACK_SKIP_PIXELS),Pe=s.getParameter(s.UNPACK_SKIP_ROWS);s.pixelStorei(s.UNPACK_ROW_LENGTH,E.width);for(let oe=0,ge=K.length;oe<ge;oe++){let De=K[oe],Ae=Math.floor(De.start/4),pe=Math.ceil(De.count/4),Ve=Ae%E.width,F=Math.floor(Ae/E.width),se=pe,ce=1;s.pixelStorei(s.UNPACK_SKIP_PIXELS,Ve),s.pixelStorei(s.UNPACK_SKIP_ROWS,F),t.texSubImage2D(s.TEXTURE_2D,0,Ve,F,se,ce,O,q,E.data)}k.clearUpdateRanges(),s.pixelStorei(s.UNPACK_ROW_LENGTH,he),s.pixelStorei(s.UNPACK_SKIP_PIXELS,Ee),s.pixelStorei(s.UNPACK_SKIP_ROWS,Pe)}}function Q(k,E,O){let q=s.TEXTURE_2D;(E.isDataArrayTexture||E.isCompressedArrayTexture)&&(q=s.TEXTURE_2D_ARRAY),E.isData3DTexture&&(q=s.TEXTURE_3D);let ee=$e(k,E),K=E.source;t.bindTexture(q,k.__webglTexture,s.TEXTURE0+O);let Me=n.get(K);if(K.version!==Me.__version||ee===!0){t.activeTexture(s.TEXTURE0+O);let he=et.getPrimaries(et.workingColorSpace),Ee=E.colorSpace===Ai?null:et.getPrimaries(E.colorSpace),Pe=E.colorSpace===Ai||he===Ee?s.NONE:s.BROWSER_DEFAULT_WEBGL;s.pixelStorei(s.UNPACK_FLIP_Y_WEBGL,E.flipY),s.pixelStorei(s.UNPACK_PREMULTIPLY_ALPHA_WEBGL,E.premultiplyAlpha),s.pixelStorei(s.UNPACK_ALIGNMENT,E.unpackAlignment),s.pixelStorei(s.UNPACK_COLORSPACE_CONVERSION_WEBGL,Pe);let oe=y(E.image,!1,i.maxTextureSize);oe=Ie(E,oe);let ge=r.convert(E.format,E.colorSpace),De=r.convert(E.type),Ae=v(E.internalFormat,ge,De,E.colorSpace,E.isVideoTexture);ze(q,E);let pe,Ve=E.mipmaps,F=E.isVideoTexture!==!0,se=Me.__version===void 0||ee===!0,ce=K.dataReady,xe=S(E,oe);if(E.isDepthTexture)Ae=b(E.format===fr,E.type),se&&(F?t.texStorage2D(s.TEXTURE_2D,1,Ae,oe.width,oe.height):t.texImage2D(s.TEXTURE_2D,0,Ae,oe.width,oe.height,0,ge,De,null));else if(E.isDataTexture)if(Ve.length>0){F&&se&&t.texStorage2D(s.TEXTURE_2D,xe,Ae,Ve[0].width,Ve[0].height);for(let ie=0,$=Ve.length;ie<$;ie++)pe=Ve[ie],F?ce&&t.texSubImage2D(s.TEXTURE_2D,ie,0,0,pe.width,pe.height,ge,De,pe.data):t.texImage2D(s.TEXTURE_2D,ie,Ae,pe.width,pe.height,0,ge,De,pe.data);E.generateMipmaps=!1}else F?(se&&t.texStorage2D(s.TEXTURE_2D,xe,Ae,oe.width,oe.height),ce&&Ye(E,oe,ge,De)):t.texImage2D(s.TEXTURE_2D,0,Ae,oe.width,oe.height,0,ge,De,oe.data);else if(E.isCompressedTexture)if(E.isCompressedArrayTexture){F&&se&&t.texStorage3D(s.TEXTURE_2D_ARRAY,xe,Ae,Ve[0].width,Ve[0].height,oe.depth);for(let ie=0,$=Ve.length;ie<$;ie++)if(pe=Ve[ie],E.format!==Tn)if(ge!==null)if(F){if(ce)if(E.layerUpdates.size>0){let Ce=Rh(pe.width,pe.height,E.format,E.type);for(let Xe of E.layerUpdates){let wt=pe.data.subarray(Xe*Ce/pe.data.BYTES_PER_ELEMENT,(Xe+1)*Ce/pe.data.BYTES_PER_ELEMENT);t.compressedTexSubImage3D(s.TEXTURE_2D_ARRAY,ie,0,0,Xe,pe.width,pe.height,1,ge,wt)}E.clearLayerUpdates()}else t.compressedTexSubImage3D(s.TEXTURE_2D_ARRAY,ie,0,0,0,pe.width,pe.height,oe.depth,ge,pe.data)}else t.compressedTexImage3D(s.TEXTURE_2D_ARRAY,ie,Ae,pe.width,pe.height,oe.depth,0,pe.data,0,0);else console.warn("THREE.WebGLRenderer: Attempt to load unsupported compressed texture format in .uploadTexture()");else F?ce&&t.texSubImage3D(s.TEXTURE_2D_ARRAY,ie,0,0,0,pe.width,pe.height,oe.depth,ge,De,pe.data):t.texImage3D(s.TEXTURE_2D_ARRAY,ie,Ae,pe.width,pe.height,oe.depth,0,ge,De,pe.data)}else{F&&se&&t.texStorage2D(s.TEXTURE_2D,xe,Ae,Ve[0].width,Ve[0].height);for(let ie=0,$=Ve.length;ie<$;ie++)pe=Ve[ie],E.format!==Tn?ge!==null?F?ce&&t.compressedTexSubImage2D(s.TEXTURE_2D,ie,0,0,pe.width,pe.height,ge,pe.data):t.compressedTexImage2D(s.TEXTURE_2D,ie,Ae,pe.width,pe.height,0,pe.data):console.warn("THREE.WebGLRenderer: Attempt to load unsupported compressed texture format in .uploadTexture()"):F?ce&&t.texSubImage2D(s.TEXTURE_2D,ie,0,0,pe.width,pe.height,ge,De,pe.data):t.texImage2D(s.TEXTURE_2D,ie,Ae,pe.width,pe.height,0,ge,De,pe.data)}else if(E.isDataArrayTexture)if(F){if(se&&t.texStorage3D(s.TEXTURE_2D_ARRAY,xe,Ae,oe.width,oe.height,oe.depth),ce)if(E.layerUpdates.size>0){let ie=Rh(oe.width,oe.height,E.format,E.type);for(let $ of E.layerUpdates){let Ce=oe.data.subarray($*ie/oe.data.BYTES_PER_ELEMENT,($+1)*ie/oe.data.BYTES_PER_ELEMENT);t.texSubImage3D(s.TEXTURE_2D_ARRAY,0,0,0,$,oe.width,oe.height,1,ge,De,Ce)}E.clearLayerUpdates()}else t.texSubImage3D(s.TEXTURE_2D_ARRAY,0,0,0,0,oe.width,oe.height,oe.depth,ge,De,oe.data)}else t.texImage3D(s.TEXTURE_2D_ARRAY,0,Ae,oe.width,oe.height,oe.depth,0,ge,De,oe.data);else if(E.isData3DTexture)F?(se&&t.texStorage3D(s.TEXTURE_3D,xe,Ae,oe.width,oe.height,oe.depth),ce&&t.texSubImage3D(s.TEXTURE_3D,0,0,0,0,oe.width,oe.height,oe.depth,ge,De,oe.data)):t.texImage3D(s.TEXTURE_3D,0,Ae,oe.width,oe.height,oe.depth,0,ge,De,oe.data);else if(E.isFramebufferTexture){if(se)if(F)t.texStorage2D(s.TEXTURE_2D,xe,Ae,oe.width,oe.height);else{let ie=oe.width,$=oe.height;for(let Ce=0;Ce<xe;Ce++)t.texImage2D(s.TEXTURE_2D,Ce,Ae,ie,$,0,ge,De,null),ie>>=1,$>>=1}}else if(Ve.length>0){if(F&&se){let ie=Te(Ve[0]);t.texStorage2D(s.TEXTURE_2D,xe,Ae,ie.width,ie.height)}for(let ie=0,$=Ve.length;ie<$;ie++)pe=Ve[ie],F?ce&&t.texSubImage2D(s.TEXTURE_2D,ie,0,0,ge,De,pe):t.texImage2D(s.TEXTURE_2D,ie,Ae,ge,De,pe);E.generateMipmaps=!1}else if(F){if(se){let ie=Te(oe);t.texStorage2D(s.TEXTURE_2D,xe,Ae,ie.width,ie.height)}ce&&t.texSubImage2D(s.TEXTURE_2D,0,0,0,ge,De,oe)}else t.texImage2D(s.TEXTURE_2D,0,Ae,ge,De,oe);m(E)&&p(q),Me.__version=K.version,E.onUpdate&&E.onUpdate(E)}k.__version=E.version}function te(k,E,O){if(E.image.length!==6)return;let q=$e(k,E),ee=E.source;t.bindTexture(s.TEXTURE_CUBE_MAP,k.__webglTexture,s.TEXTURE0+O);let K=n.get(ee);if(ee.version!==K.__version||q===!0){t.activeTexture(s.TEXTURE0+O);let Me=et.getPrimaries(et.workingColorSpace),he=E.colorSpace===Ai?null:et.getPrimaries(E.colorSpace),Ee=E.colorSpace===Ai||Me===he?s.NONE:s.BROWSER_DEFAULT_WEBGL;s.pixelStorei(s.UNPACK_FLIP_Y_WEBGL,E.flipY),s.pixelStorei(s.UNPACK_PREMULTIPLY_ALPHA_WEBGL,E.premultiplyAlpha),s.pixelStorei(s.UNPACK_ALIGNMENT,E.unpackAlignment),s.pixelStorei(s.UNPACK_COLORSPACE_CONVERSION_WEBGL,Ee);let Pe=E.isCompressedTexture||E.image[0].isCompressedTexture,oe=E.image[0]&&E.image[0].isDataTexture,ge=[];for(let $=0;$<6;$++)!Pe&&!oe?ge[$]=y(E.image[$],!0,i.maxCubemapSize):ge[$]=oe?E.image[$].image:E.image[$],ge[$]=Ie(E,ge[$]);let De=ge[0],Ae=r.convert(E.format,E.colorSpace),pe=r.convert(E.type),Ve=v(E.internalFormat,Ae,pe,E.colorSpace),F=E.isVideoTexture!==!0,se=K.__version===void 0||q===!0,ce=ee.dataReady,xe=S(E,De);ze(s.TEXTURE_CUBE_MAP,E);let ie;if(Pe){F&&se&&t.texStorage2D(s.TEXTURE_CUBE_MAP,xe,Ve,De.width,De.height);for(let $=0;$<6;$++){ie=ge[$].mipmaps;for(let Ce=0;Ce<ie.length;Ce++){let Xe=ie[Ce];E.format!==Tn?Ae!==null?F?ce&&t.compressedTexSubImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+$,Ce,0,0,Xe.width,Xe.height,Ae,Xe.data):t.compressedTexImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+$,Ce,Ve,Xe.width,Xe.height,0,Xe.data):console.warn("THREE.WebGLRenderer: Attempt to load unsupported compressed texture format in .setTextureCube()"):F?ce&&t.texSubImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+$,Ce,0,0,Xe.width,Xe.height,Ae,pe,Xe.data):t.texImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+$,Ce,Ve,Xe.width,Xe.height,0,Ae,pe,Xe.data)}}}else{if(ie=E.mipmaps,F&&se){ie.length>0&&xe++;let $=Te(ge[0]);t.texStorage2D(s.TEXTURE_CUBE_MAP,xe,Ve,$.width,$.height)}for(let $=0;$<6;$++)if(oe){F?ce&&t.texSubImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+$,0,0,0,ge[$].width,ge[$].height,Ae,pe,ge[$].data):t.texImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+$,0,Ve,ge[$].width,ge[$].height,0,Ae,pe,ge[$].data);for(let Ce=0;Ce<ie.length;Ce++){let wt=ie[Ce].image[$].image;F?ce&&t.texSubImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+$,Ce+1,0,0,wt.width,wt.height,Ae,pe,wt.data):t.texImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+$,Ce+1,Ve,wt.width,wt.height,0,Ae,pe,wt.data)}}else{F?ce&&t.texSubImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+$,0,0,0,Ae,pe,ge[$]):t.texImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+$,0,Ve,Ae,pe,ge[$]);for(let Ce=0;Ce<ie.length;Ce++){let Xe=ie[Ce];F?ce&&t.texSubImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+$,Ce+1,0,0,Ae,pe,Xe.image[$]):t.texImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+$,Ce+1,Ve,Ae,pe,Xe.image[$])}}}m(E)&&p(s.TEXTURE_CUBE_MAP),K.__version=ee.version,E.onUpdate&&E.onUpdate(E)}k.__version=E.version}function ve(k,E,O,q,ee,K){let Me=r.convert(O.format,O.colorSpace),he=r.convert(O.type),Ee=v(O.internalFormat,Me,he,O.colorSpace),Pe=n.get(E),oe=n.get(O);if(oe.__renderTarget=E,!Pe.__hasExternalTextures){let ge=Math.max(1,E.width>>K),De=Math.max(1,E.height>>K);ee===s.TEXTURE_3D||ee===s.TEXTURE_2D_ARRAY?t.texImage3D(ee,K,Ee,ge,De,E.depth,0,Me,he,null):t.texImage2D(ee,K,Ee,ge,De,0,Me,he,null)}t.bindFramebuffer(s.FRAMEBUFFER,k),j(E)?o.framebufferTexture2DMultisampleEXT(s.FRAMEBUFFER,q,ee,oe.__webglTexture,0,de(E)):(ee===s.TEXTURE_2D||ee>=s.TEXTURE_CUBE_MAP_POSITIVE_X&&ee<=s.TEXTURE_CUBE_MAP_NEGATIVE_Z)&&s.framebufferTexture2D(s.FRAMEBUFFER,q,ee,oe.__webglTexture,K),t.bindFramebuffer(s.FRAMEBUFFER,null)}function Fe(k,E,O){if(s.bindRenderbuffer(s.RENDERBUFFER,k),E.depthBuffer){let q=E.depthTexture,ee=q&&q.isDepthTexture?q.type:null,K=b(E.stencilBuffer,ee),Me=E.stencilBuffer?s.DEPTH_STENCIL_ATTACHMENT:s.DEPTH_ATTACHMENT,he=de(E);j(E)?o.renderbufferStorageMultisampleEXT(s.RENDERBUFFER,he,K,E.width,E.height):O?s.renderbufferStorageMultisample(s.RENDERBUFFER,he,K,E.width,E.height):s.renderbufferStorage(s.RENDERBUFFER,K,E.width,E.height),s.framebufferRenderbuffer(s.FRAMEBUFFER,Me,s.RENDERBUFFER,k)}else{let q=E.textures;for(let ee=0;ee<q.length;ee++){let K=q[ee],Me=r.convert(K.format,K.colorSpace),he=r.convert(K.type),Ee=v(K.internalFormat,Me,he,K.colorSpace),Pe=de(E);O&&j(E)===!1?s.renderbufferStorageMultisample(s.RENDERBUFFER,Pe,Ee,E.width,E.height):j(E)?o.renderbufferStorageMultisampleEXT(s.RENDERBUFFER,Pe,Ee,E.width,E.height):s.renderbufferStorage(s.RENDERBUFFER,Ee,E.width,E.height)}}s.bindRenderbuffer(s.RENDERBUFFER,null)}function Se(k,E){if(E&&E.isWebGLCubeRenderTarget)throw new Error("Depth Texture with cube render targets is not supported");if(t.bindFramebuffer(s.FRAMEBUFFER,k),!(E.depthTexture&&E.depthTexture.isDepthTexture))throw new Error("renderTarget.depthTexture must be an instance of THREE.DepthTexture");let q=n.get(E.depthTexture);q.__renderTarget=E,(!q.__webglTexture||E.depthTexture.image.width!==E.width||E.depthTexture.image.height!==E.height)&&(E.depthTexture.image.width=E.width,E.depthTexture.image.height=E.height,E.depthTexture.needsUpdate=!0),U(E.depthTexture,0);let ee=q.__webglTexture,K=de(E);if(E.depthTexture.format===Ks)j(E)?o.framebufferTexture2DMultisampleEXT(s.FRAMEBUFFER,s.DEPTH_ATTACHMENT,s.TEXTURE_2D,ee,0,K):s.framebufferTexture2D(s.FRAMEBUFFER,s.DEPTH_ATTACHMENT,s.TEXTURE_2D,ee,0);else if(E.depthTexture.format===fr)j(E)?o.framebufferTexture2DMultisampleEXT(s.FRAMEBUFFER,s.DEPTH_STENCIL_ATTACHMENT,s.TEXTURE_2D,ee,0,K):s.framebufferTexture2D(s.FRAMEBUFFER,s.DEPTH_STENCIL_ATTACHMENT,s.TEXTURE_2D,ee,0);else throw new Error("Unknown depthTexture format")}function je(k){let E=n.get(k),O=k.isWebGLCubeRenderTarget===!0;if(E.__boundDepthTexture!==k.depthTexture){let q=k.depthTexture;if(E.__depthDisposeCallback&&E.__depthDisposeCallback(),q){let ee=()=>{delete E.__boundDepthTexture,delete E.__depthDisposeCallback,q.removeEventListener("dispose",ee)};q.addEventListener("dispose",ee),E.__depthDisposeCallback=ee}E.__boundDepthTexture=q}if(k.depthTexture&&!E.__autoAllocateDepthBuffer){if(O)throw new Error("target.depthTexture not supported in Cube render targets");let q=k.texture.mipmaps;q&&q.length>0?Se(E.__webglFramebuffer[0],k):Se(E.__webglFramebuffer,k)}else if(O){E.__webglDepthbuffer=[];for(let q=0;q<6;q++)if(t.bindFramebuffer(s.FRAMEBUFFER,E.__webglFramebuffer[q]),E.__webglDepthbuffer[q]===void 0)E.__webglDepthbuffer[q]=s.createRenderbuffer(),Fe(E.__webglDepthbuffer[q],k,!1);else{let ee=k.stencilBuffer?s.DEPTH_STENCIL_ATTACHMENT:s.DEPTH_ATTACHMENT,K=E.__webglDepthbuffer[q];s.bindRenderbuffer(s.RENDERBUFFER,K),s.framebufferRenderbuffer(s.FRAMEBUFFER,ee,s.RENDERBUFFER,K)}}else{let q=k.texture.mipmaps;if(q&&q.length>0?t.bindFramebuffer(s.FRAMEBUFFER,E.__webglFramebuffer[0]):t.bindFramebuffer(s.FRAMEBUFFER,E.__webglFramebuffer),E.__webglDepthbuffer===void 0)E.__webglDepthbuffer=s.createRenderbuffer(),Fe(E.__webglDepthbuffer,k,!1);else{let ee=k.stencilBuffer?s.DEPTH_STENCIL_ATTACHMENT:s.DEPTH_ATTACHMENT,K=E.__webglDepthbuffer;s.bindRenderbuffer(s.RENDERBUFFER,K),s.framebufferRenderbuffer(s.FRAMEBUFFER,ee,s.RENDERBUFFER,K)}}t.bindFramebuffer(s.FRAMEBUFFER,null)}function Z(k,E,O){let q=n.get(k);E!==void 0&&ve(q.__webglFramebuffer,k,k.texture,s.COLOR_ATTACHMENT0,s.TEXTURE_2D,0),O!==void 0&&je(k)}function P(k){let E=k.texture,O=n.get(k),q=n.get(E);k.addEventListener("dispose",T);let ee=k.textures,K=k.isWebGLCubeRenderTarget===!0,Me=ee.length>1;if(Me||(q.__webglTexture===void 0&&(q.__webglTexture=s.createTexture()),q.__version=E.version,a.memory.textures++),K){O.__webglFramebuffer=[];for(let he=0;he<6;he++)if(E.mipmaps&&E.mipmaps.length>0){O.__webglFramebuffer[he]=[];for(let Ee=0;Ee<E.mipmaps.length;Ee++)O.__webglFramebuffer[he][Ee]=s.createFramebuffer()}else O.__webglFramebuffer[he]=s.createFramebuffer()}else{if(E.mipmaps&&E.mipmaps.length>0){O.__webglFramebuffer=[];for(let he=0;he<E.mipmaps.length;he++)O.__webglFramebuffer[he]=s.createFramebuffer()}else O.__webglFramebuffer=s.createFramebuffer();if(Me)for(let he=0,Ee=ee.length;he<Ee;he++){let Pe=n.get(ee[he]);Pe.__webglTexture===void 0&&(Pe.__webglTexture=s.createTexture(),a.memory.textures++)}if(k.samples>0&&j(k)===!1){O.__webglMultisampledFramebuffer=s.createFramebuffer(),O.__webglColorRenderbuffer=[],t.bindFramebuffer(s.FRAMEBUFFER,O.__webglMultisampledFramebuffer);for(let he=0;he<ee.length;he++){let Ee=ee[he];O.__webglColorRenderbuffer[he]=s.createRenderbuffer(),s.bindRenderbuffer(s.RENDERBUFFER,O.__webglColorRenderbuffer[he]);let Pe=r.convert(Ee.format,Ee.colorSpace),oe=r.convert(Ee.type),ge=v(Ee.internalFormat,Pe,oe,Ee.colorSpace,k.isXRRenderTarget===!0),De=de(k);s.renderbufferStorageMultisample(s.RENDERBUFFER,De,ge,k.width,k.height),s.framebufferRenderbuffer(s.FRAMEBUFFER,s.COLOR_ATTACHMENT0+he,s.RENDERBUFFER,O.__webglColorRenderbuffer[he])}s.bindRenderbuffer(s.RENDERBUFFER,null),k.depthBuffer&&(O.__webglDepthRenderbuffer=s.createRenderbuffer(),Fe(O.__webglDepthRenderbuffer,k,!0)),t.bindFramebuffer(s.FRAMEBUFFER,null)}}if(K){t.bindTexture(s.TEXTURE_CUBE_MAP,q.__webglTexture),ze(s.TEXTURE_CUBE_MAP,E);for(let he=0;he<6;he++)if(E.mipmaps&&E.mipmaps.length>0)for(let Ee=0;Ee<E.mipmaps.length;Ee++)ve(O.__webglFramebuffer[he][Ee],k,E,s.COLOR_ATTACHMENT0,s.TEXTURE_CUBE_MAP_POSITIVE_X+he,Ee);else ve(O.__webglFramebuffer[he],k,E,s.COLOR_ATTACHMENT0,s.TEXTURE_CUBE_MAP_POSITIVE_X+he,0);m(E)&&p(s.TEXTURE_CUBE_MAP),t.unbindTexture()}else if(Me){for(let he=0,Ee=ee.length;he<Ee;he++){let Pe=ee[he],oe=n.get(Pe),ge=s.TEXTURE_2D;(k.isWebGL3DRenderTarget||k.isWebGLArrayRenderTarget)&&(ge=k.isWebGL3DRenderTarget?s.TEXTURE_3D:s.TEXTURE_2D_ARRAY),t.bindTexture(ge,oe.__webglTexture),ze(ge,Pe),ve(O.__webglFramebuffer,k,Pe,s.COLOR_ATTACHMENT0+he,ge,0),m(Pe)&&p(ge)}t.unbindTexture()}else{let he=s.TEXTURE_2D;if((k.isWebGL3DRenderTarget||k.isWebGLArrayRenderTarget)&&(he=k.isWebGL3DRenderTarget?s.TEXTURE_3D:s.TEXTURE_2D_ARRAY),t.bindTexture(he,q.__webglTexture),ze(he,E),E.mipmaps&&E.mipmaps.length>0)for(let Ee=0;Ee<E.mipmaps.length;Ee++)ve(O.__webglFramebuffer[Ee],k,E,s.COLOR_ATTACHMENT0,he,Ee);else ve(O.__webglFramebuffer,k,E,s.COLOR_ATTACHMENT0,he,0);m(E)&&p(he),t.unbindTexture()}k.depthBuffer&&je(k)}function ae(k){let E=k.textures;for(let O=0,q=E.length;O<q;O++){let ee=E[O];if(m(ee)){let K=x(k),Me=n.get(ee).__webglTexture;t.bindTexture(K,Me),p(K),t.unbindTexture()}}}let me=[],fe=[];function W(k){if(k.samples>0){if(j(k)===!1){let E=k.textures,O=k.width,q=k.height,ee=s.COLOR_BUFFER_BIT,K=k.stencilBuffer?s.DEPTH_STENCIL_ATTACHMENT:s.DEPTH_ATTACHMENT,Me=n.get(k),he=E.length>1;if(he)for(let Pe=0;Pe<E.length;Pe++)t.bindFramebuffer(s.FRAMEBUFFER,Me.__webglMultisampledFramebuffer),s.framebufferRenderbuffer(s.FRAMEBUFFER,s.COLOR_ATTACHMENT0+Pe,s.RENDERBUFFER,null),t.bindFramebuffer(s.FRAMEBUFFER,Me.__webglFramebuffer),s.framebufferTexture2D(s.DRAW_FRAMEBUFFER,s.COLOR_ATTACHMENT0+Pe,s.TEXTURE_2D,null,0);t.bindFramebuffer(s.READ_FRAMEBUFFER,Me.__webglMultisampledFramebuffer);let Ee=k.texture.mipmaps;Ee&&Ee.length>0?t.bindFramebuffer(s.DRAW_FRAMEBUFFER,Me.__webglFramebuffer[0]):t.bindFramebuffer(s.DRAW_FRAMEBUFFER,Me.__webglFramebuffer);for(let Pe=0;Pe<E.length;Pe++){if(k.resolveDepthBuffer&&(k.depthBuffer&&(ee|=s.DEPTH_BUFFER_BIT),k.stencilBuffer&&k.resolveStencilBuffer&&(ee|=s.STENCIL_BUFFER_BIT)),he){s.framebufferRenderbuffer(s.READ_FRAMEBUFFER,s.COLOR_ATTACHMENT0,s.RENDERBUFFER,Me.__webglColorRenderbuffer[Pe]);let oe=n.get(E[Pe]).__webglTexture;s.framebufferTexture2D(s.DRAW_FRAMEBUFFER,s.COLOR_ATTACHMENT0,s.TEXTURE_2D,oe,0)}s.blitFramebuffer(0,0,O,q,0,0,O,q,ee,s.NEAREST),c===!0&&(me.length=0,fe.length=0,me.push(s.COLOR_ATTACHMENT0+Pe),k.depthBuffer&&k.resolveDepthBuffer===!1&&(me.push(K),fe.push(K),s.invalidateFramebuffer(s.DRAW_FRAMEBUFFER,fe)),s.invalidateFramebuffer(s.READ_FRAMEBUFFER,me))}if(t.bindFramebuffer(s.READ_FRAMEBUFFER,null),t.bindFramebuffer(s.DRAW_FRAMEBUFFER,null),he)for(let Pe=0;Pe<E.length;Pe++){t.bindFramebuffer(s.FRAMEBUFFER,Me.__webglMultisampledFramebuffer),s.framebufferRenderbuffer(s.FRAMEBUFFER,s.COLOR_ATTACHMENT0+Pe,s.RENDERBUFFER,Me.__webglColorRenderbuffer[Pe]);let oe=n.get(E[Pe]).__webglTexture;t.bindFramebuffer(s.FRAMEBUFFER,Me.__webglFramebuffer),s.framebufferTexture2D(s.DRAW_FRAMEBUFFER,s.COLOR_ATTACHMENT0+Pe,s.TEXTURE_2D,oe,0)}t.bindFramebuffer(s.DRAW_FRAMEBUFFER,Me.__webglMultisampledFramebuffer)}else if(k.depthBuffer&&k.resolveDepthBuffer===!1&&c){let E=k.stencilBuffer?s.DEPTH_STENCIL_ATTACHMENT:s.DEPTH_ATTACHMENT;s.invalidateFramebuffer(s.DRAW_FRAMEBUFFER,[E])}}}function de(k){return Math.min(i.maxSamples,k.samples)}function j(k){let E=n.get(k);return k.samples>0&&e.has("WEBGL_multisampled_render_to_texture")===!0&&E.__useRenderToTexture!==!1}function re(k){let E=a.render.frame;u.get(k)!==E&&(u.set(k,E),k.update())}function Ie(k,E){let O=k.colorSpace,q=k.format,ee=k.type;return k.isCompressedTexture===!0||k.isVideoTexture===!0||O!==Kt&&O!==Ai&&(et.getTransfer(O)===pt?(q!==Tn||ee!==jn)&&console.warn("THREE.WebGLTextures: sRGB encoded textures have to use RGBAFormat and UnsignedByteType."):console.error("THREE.WebGLTextures: Unsupported texture color space:",O)),E}function Te(k){return typeof HTMLImageElement<"u"&&k instanceof HTMLImageElement?(l.width=k.naturalWidth||k.width,l.height=k.naturalHeight||k.height):typeof VideoFrame<"u"&&k instanceof VideoFrame?(l.width=k.displayWidth,l.height=k.displayHeight):(l.width=k.width,l.height=k.height),l}this.allocateTextureUnit=D,this.resetTextureUnits=C,this.setTexture2D=U,this.setTexture2DArray=B,this.setTexture3D=J,this.setTextureCube=V,this.rebindTextures=Z,this.setupRenderTarget=P,this.updateRenderTargetMipmap=ae,this.updateMultisampleRenderTarget=W,this.setupDepthRenderbuffer=je,this.setupFrameBufferTexture=ve,this.useMultisampledRTT=j}function lv(s,e){function t(n,i=Ai){let r,a=et.getTransfer(i);if(n===jn)return s.UNSIGNED_BYTE;if(n===nc)return s.UNSIGNED_SHORT_4_4_4_4;if(n===ic)return s.UNSIGNED_SHORT_5_5_5_1;if(n===mh)return s.UNSIGNED_INT_5_9_9_9_REV;if(n===gh)return s.UNSIGNED_INT_10F_11F_11F_REV;if(n===fh)return s.BYTE;if(n===ph)return s.SHORT;if(n===ur)return s.UNSIGNED_SHORT;if(n===tc)return s.INT;if(n===Oi)return s.UNSIGNED_INT;if(n===Fn)return s.FLOAT;if(n===zi)return s.HALF_FLOAT;if(n===bh)return s.ALPHA;if(n===yh)return s.RGB;if(n===Tn)return s.RGBA;if(n===Ks)return s.DEPTH_COMPONENT;if(n===fr)return s.DEPTH_STENCIL;if(n===pr)return s.RED;if(n===sc)return s.RED_INTEGER;if(n===xh)return s.RG;if(n===rc)return s.RG_INTEGER;if(n===ac)return s.RGBA_INTEGER;if(n===Ta||n===Ea||n===Aa||n===Ra)if(a===pt)if(r=e.get("WEBGL_compressed_texture_s3tc_srgb"),r!==null){if(n===Ta)return r.COMPRESSED_SRGB_S3TC_DXT1_EXT;if(n===Ea)return r.COMPRESSED_SRGB_ALPHA_S3TC_DXT1_EXT;if(n===Aa)return r.COMPRESSED_SRGB_ALPHA_S3TC_DXT3_EXT;if(n===Ra)return r.COMPRESSED_SRGB_ALPHA_S3TC_DXT5_EXT}else return null;else if(r=e.get("WEBGL_compressed_texture_s3tc"),r!==null){if(n===Ta)return r.COMPRESSED_RGB_S3TC_DXT1_EXT;if(n===Ea)return r.COMPRESSED_RGBA_S3TC_DXT1_EXT;if(n===Aa)return r.COMPRESSED_RGBA_S3TC_DXT3_EXT;if(n===Ra)return r.COMPRESSED_RGBA_S3TC_DXT5_EXT}else return null;if(n===oc||n===cc||n===lc||n===hc)if(r=e.get("WEBGL_compressed_texture_pvrtc"),r!==null){if(n===oc)return r.COMPRESSED_RGB_PVRTC_4BPPV1_IMG;if(n===cc)return r.COMPRESSED_RGB_PVRTC_2BPPV1_IMG;if(n===lc)return r.COMPRESSED_RGBA_PVRTC_4BPPV1_IMG;if(n===hc)return r.COMPRESSED_RGBA_PVRTC_2BPPV1_IMG}else return null;if(n===uc||n===dc||n===fc)if(r=e.get("WEBGL_compressed_texture_etc"),r!==null){if(n===uc||n===dc)return a===pt?r.COMPRESSED_SRGB8_ETC2:r.COMPRESSED_RGB8_ETC2;if(n===fc)return a===pt?r.COMPRESSED_SRGB8_ALPHA8_ETC2_EAC:r.COMPRESSED_RGBA8_ETC2_EAC}else return null;if(n===pc||n===mc||n===gc||n===bc||n===yc||n===xc||n===vc||n===_c||n===wc||n===Mc||n===Sc||n===Tc||n===Ec||n===Ac)if(r=e.get("WEBGL_compressed_texture_astc"),r!==null){if(n===pc)return a===pt?r.COMPRESSED_SRGB8_ALPHA8_ASTC_4x4_KHR:r.COMPRESSED_RGBA_ASTC_4x4_KHR;if(n===mc)return a===pt?r.COMPRESSED_SRGB8_ALPHA8_ASTC_5x4_KHR:r.COMPRESSED_RGBA_ASTC_5x4_KHR;if(n===gc)return a===pt?r.COMPRESSED_SRGB8_ALPHA8_ASTC_5x5_KHR:r.COMPRESSED_RGBA_ASTC_5x5_KHR;if(n===bc)return a===pt?r.COMPRESSED_SRGB8_ALPHA8_ASTC_6x5_KHR:r.COMPRESSED_RGBA_ASTC_6x5_KHR;if(n===yc)return a===pt?r.COMPRESSED_SRGB8_ALPHA8_ASTC_6x6_KHR:r.COMPRESSED_RGBA_ASTC_6x6_KHR;if(n===xc)return a===pt?r.COMPRESSED_SRGB8_ALPHA8_ASTC_8x5_KHR:r.COMPRESSED_RGBA_ASTC_8x5_KHR;if(n===vc)return a===pt?r.COMPRESSED_SRGB8_ALPHA8_ASTC_8x6_KHR:r.COMPRESSED_RGBA_ASTC_8x6_KHR;if(n===_c)return a===pt?r.COMPRESSED_SRGB8_ALPHA8_ASTC_8x8_KHR:r.COMPRESSED_RGBA_ASTC_8x8_KHR;if(n===wc)return a===pt?r.COMPRESSED_SRGB8_ALPHA8_ASTC_10x5_KHR:r.COMPRESSED_RGBA_ASTC_10x5_KHR;if(n===Mc)return a===pt?r.COMPRESSED_SRGB8_ALPHA8_ASTC_10x6_KHR:r.COMPRESSED_RGBA_ASTC_10x6_KHR;if(n===Sc)return a===pt?r.COMPRESSED_SRGB8_ALPHA8_ASTC_10x8_KHR:r.COMPRESSED_RGBA_ASTC_10x8_KHR;if(n===Tc)return a===pt?r.COMPRESSED_SRGB8_ALPHA8_ASTC_10x10_KHR:r.COMPRESSED_RGBA_ASTC_10x10_KHR;if(n===Ec)return a===pt?r.COMPRESSED_SRGB8_ALPHA8_ASTC_12x10_KHR:r.COMPRESSED_RGBA_ASTC_12x10_KHR;if(n===Ac)return a===pt?r.COMPRESSED_SRGB8_ALPHA8_ASTC_12x12_KHR:r.COMPRESSED_RGBA_ASTC_12x12_KHR}else return null;if(n===Rc||n===Cc||n===Ic)if(r=e.get("EXT_texture_compression_bptc"),r!==null){if(n===Rc)return a===pt?r.COMPRESSED_SRGB_ALPHA_BPTC_UNORM_EXT:r.COMPRESSED_RGBA_BPTC_UNORM_EXT;if(n===Cc)return r.COMPRESSED_RGB_BPTC_SIGNED_FLOAT_EXT;if(n===Ic)return r.COMPRESSED_RGB_BPTC_UNSIGNED_FLOAT_EXT}else return null;if(n===Pc||n===kc||n===Lc||n===Dc)if(r=e.get("EXT_texture_compression_rgtc"),r!==null){if(n===Pc)return r.COMPRESSED_RED_RGTC1_EXT;if(n===kc)return r.COMPRESSED_SIGNED_RED_RGTC1_EXT;if(n===Lc)return r.COMPRESSED_RED_GREEN_RGTC2_EXT;if(n===Dc)return r.COMPRESSED_SIGNED_RED_GREEN_RGTC2_EXT}else return null;return n===dr?s.UNSIGNED_INT_24_8:s[n]!==void 0?s[n]:null}return{convert:t}}var hv=`
void main() {

	gl_Position = vec4( position, 1.0 );

}`,uv=`
uniform sampler2DArray depthColor;
uniform float depthWidth;
uniform float depthHeight;

void main() {

	vec2 coord = vec2( gl_FragCoord.x / depthWidth, gl_FragCoord.y / depthHeight );

	if ( coord.x >= 1.0 ) {

		gl_FragDepth = texture( depthColor, vec3( coord.x - 1.0, coord.y, 1 ) ).r;

	} else {

		gl_FragDepth = texture( depthColor, vec3( coord.x, coord.y, 0 ) ).r;

	}

}`,Hh=class{constructor(){this.texture=null,this.mesh=null,this.depthNear=0,this.depthFar=0}init(e,t){if(this.texture===null){let n=new ua(e.texture);(e.depthNear!==t.depthNear||e.depthFar!==t.depthFar)&&(this.depthNear=e.depthNear,this.depthFar=e.depthFar),this.texture=n}}getMesh(e){if(this.texture!==null&&this.mesh===null){let t=e.cameras[0].viewport,n=new Yt({vertexShader:hv,fragmentShader:uv,uniforms:{depthColor:{value:this.texture},depthWidth:{value:t.z},depthHeight:{value:t.w}}});this.mesh=new at(new Bi(20,20),n)}return this.mesh}reset(){this.texture=null,this.mesh=null}getDepthTexture(){return this.texture}},Vh=class extends xi{constructor(e,t){super();let n=this,i=null,r=1,a=null,o="local-floor",c=1,l=null,u=null,h=null,d=null,f=null,g=null,y=typeof XRWebGLBinding<"u",m=new Hh,p={},x=t.getContextAttributes(),v=null,b=null,S=[],w=[],T=new Ne,A=null,M=new Ut;M.viewport=new tt;let _=new Ut;_.viewport=new tt;let I=[M,_],C=new Ho,D=null,N=null;this.cameraAutoUpdate=!0,this.enabled=!1,this.isPresenting=!1,this.getController=function(Q){let te=S[Q];return te===void 0&&(te=new er,S[Q]=te),te.getTargetRaySpace()},this.getControllerGrip=function(Q){let te=S[Q];return te===void 0&&(te=new er,S[Q]=te),te.getGripSpace()},this.getHand=function(Q){let te=S[Q];return te===void 0&&(te=new er,S[Q]=te),te.getHandSpace()};function U(Q){let te=w.indexOf(Q.inputSource);if(te===-1)return;let ve=S[te];ve!==void 0&&(ve.update(Q.inputSource,Q.frame,l||a),ve.dispatchEvent({type:Q.type,data:Q.inputSource}))}function B(){i.removeEventListener("select",U),i.removeEventListener("selectstart",U),i.removeEventListener("selectend",U),i.removeEventListener("squeeze",U),i.removeEventListener("squeezestart",U),i.removeEventListener("squeezeend",U),i.removeEventListener("end",B),i.removeEventListener("inputsourceschange",J);for(let Q=0;Q<S.length;Q++){let te=w[Q];te!==null&&(w[Q]=null,S[Q].disconnect(te))}D=null,N=null,m.reset();for(let Q in p)delete p[Q];e.setRenderTarget(v),f=null,d=null,h=null,i=null,b=null,Ye.stop(),n.isPresenting=!1,e.setPixelRatio(A),e.setSize(T.width,T.height,!1),n.dispatchEvent({type:"sessionend"})}this.setFramebufferScaleFactor=function(Q){r=Q,n.isPresenting===!0&&console.warn("THREE.WebXRManager: Cannot change framebuffer scale while presenting.")},this.setReferenceSpaceType=function(Q){o=Q,n.isPresenting===!0&&console.warn("THREE.WebXRManager: Cannot change reference space type while presenting.")},this.getReferenceSpace=function(){return l||a},this.setReferenceSpace=function(Q){l=Q},this.getBaseLayer=function(){return d!==null?d:f},this.getBinding=function(){return h===null&&y&&(h=new XRWebGLBinding(i,t)),h},this.getFrame=function(){return g},this.getSession=function(){return i},this.setSession=async function(Q){if(i=Q,i!==null){if(v=e.getRenderTarget(),i.addEventListener("select",U),i.addEventListener("selectstart",U),i.addEventListener("selectend",U),i.addEventListener("squeeze",U),i.addEventListener("squeezestart",U),i.addEventListener("squeezeend",U),i.addEventListener("end",B),i.addEventListener("inputsourceschange",J),x.xrCompatible!==!0&&await t.makeXRCompatible(),A=e.getPixelRatio(),e.getSize(T),y&&"createProjectionLayer"in XRWebGLBinding.prototype){let ve=null,Fe=null,Se=null;x.depth&&(Se=x.stencil?t.DEPTH24_STENCIL8:t.DEPTH_COMPONENT24,ve=x.stencil?fr:Ks,Fe=x.stencil?dr:Oi);let je={colorFormat:t.RGBA8,depthFormat:Se,scaleFactor:r};h=this.getBinding(),d=h.createProjectionLayer(je),i.updateRenderState({layers:[d]}),e.setPixelRatio(1),e.setSize(d.textureWidth,d.textureHeight,!1),b=new ei(d.textureWidth,d.textureHeight,{format:Tn,type:jn,depthTexture:new ha(d.textureWidth,d.textureHeight,Fe,void 0,void 0,void 0,void 0,void 0,void 0,ve),stencilBuffer:x.stencil,colorSpace:e.outputColorSpace,samples:x.antialias?4:0,resolveDepthBuffer:d.ignoreDepthValues===!1,resolveStencilBuffer:d.ignoreDepthValues===!1})}else{let ve={antialias:x.antialias,alpha:!0,depth:x.depth,stencil:x.stencil,framebufferScaleFactor:r};f=new XRWebGLLayer(i,t,ve),i.updateRenderState({baseLayer:f}),e.setPixelRatio(1),e.setSize(f.framebufferWidth,f.framebufferHeight,!1),b=new ei(f.framebufferWidth,f.framebufferHeight,{format:Tn,type:jn,colorSpace:e.outputColorSpace,stencilBuffer:x.stencil,resolveDepthBuffer:f.ignoreDepthValues===!1,resolveStencilBuffer:f.ignoreDepthValues===!1})}b.isXRRenderTarget=!0,this.setFoveation(c),l=null,a=await i.requestReferenceSpace(o),Ye.setContext(i),Ye.start(),n.isPresenting=!0,n.dispatchEvent({type:"sessionstart"})}},this.getEnvironmentBlendMode=function(){if(i!==null)return i.environmentBlendMode},this.getDepthTexture=function(){return m.getDepthTexture()};function J(Q){for(let te=0;te<Q.removed.length;te++){let ve=Q.removed[te],Fe=w.indexOf(ve);Fe>=0&&(w[Fe]=null,S[Fe].disconnect(ve))}for(let te=0;te<Q.added.length;te++){let ve=Q.added[te],Fe=w.indexOf(ve);if(Fe===-1){for(let je=0;je<S.length;je++)if(je>=w.length){w.push(ve),Fe=je;break}else if(w[je]===null){w[je]=ve,Fe=je;break}if(Fe===-1)break}let Se=S[Fe];Se&&Se.connect(ve)}}let V=new L,ne=new L;function ue(Q,te,ve){V.setFromMatrixPosition(te.matrixWorld),ne.setFromMatrixPosition(ve.matrixWorld);let Fe=V.distanceTo(ne),Se=te.projectionMatrix.elements,je=ve.projectionMatrix.elements,Z=Se[14]/(Se[10]-1),P=Se[14]/(Se[10]+1),ae=(Se[9]+1)/Se[5],me=(Se[9]-1)/Se[5],fe=(Se[8]-1)/Se[0],W=(je[8]+1)/je[0],de=Z*fe,j=Z*W,re=Fe/(-fe+W),Ie=re*-fe;if(te.matrixWorld.decompose(Q.position,Q.quaternion,Q.scale),Q.translateX(Ie),Q.translateZ(re),Q.matrixWorld.compose(Q.position,Q.quaternion,Q.scale),Q.matrixWorldInverse.copy(Q.matrixWorld).invert(),Se[10]===-1)Q.projectionMatrix.copy(te.projectionMatrix),Q.projectionMatrixInverse.copy(te.projectionMatrixInverse);else{let Te=Z+re,k=P+re,E=de-Ie,O=j+(Fe-Ie),q=ae*P/k*Te,ee=me*P/k*Te;Q.projectionMatrix.makePerspective(E,O,q,ee,Te,k),Q.projectionMatrixInverse.copy(Q.projectionMatrix).invert()}}function _e(Q,te){te===null?Q.matrixWorld.copy(Q.matrix):Q.matrixWorld.multiplyMatrices(te.matrixWorld,Q.matrix),Q.matrixWorldInverse.copy(Q.matrixWorld).invert()}this.updateCamera=function(Q){if(i===null)return;let te=Q.near,ve=Q.far;m.texture!==null&&(m.depthNear>0&&(te=m.depthNear),m.depthFar>0&&(ve=m.depthFar)),C.near=_.near=M.near=te,C.far=_.far=M.far=ve,(D!==C.near||N!==C.far)&&(i.updateRenderState({depthNear:C.near,depthFar:C.far}),D=C.near,N=C.far),C.layers.mask=Q.layers.mask|6,M.layers.mask=C.layers.mask&3,_.layers.mask=C.layers.mask&5;let Fe=Q.parent,Se=C.cameras;_e(C,Fe);for(let je=0;je<Se.length;je++)_e(Se[je],Fe);Se.length===2?ue(C,M,_):C.projectionMatrix.copy(M.projectionMatrix),ze(Q,C,Fe)};function ze(Q,te,ve){ve===null?Q.matrix.copy(te.matrixWorld):(Q.matrix.copy(ve.matrixWorld),Q.matrix.invert(),Q.matrix.multiply(te.matrixWorld)),Q.matrix.decompose(Q.position,Q.quaternion,Q.scale),Q.updateMatrixWorld(!0),Q.projectionMatrix.copy(te.projectionMatrix),Q.projectionMatrixInverse.copy(te.projectionMatrixInverse),Q.isPerspectiveCamera&&(Q.fov=ss*2*Math.atan(1/Q.projectionMatrix.elements[5]),Q.zoom=1)}this.getCamera=function(){return C},this.getFoveation=function(){if(!(d===null&&f===null))return c},this.setFoveation=function(Q){c=Q,d!==null&&(d.fixedFoveation=Q),f!==null&&f.fixedFoveation!==void 0&&(f.fixedFoveation=Q)},this.hasDepthSensing=function(){return m.texture!==null},this.getDepthSensingMesh=function(){return m.getMesh(C)},this.getCameraTexture=function(Q){return p[Q]};let $e=null;function ht(Q,te){if(u=te.getViewerPose(l||a),g=te,u!==null){let ve=u.views;f!==null&&(e.setRenderTargetFramebuffer(b,f.framebuffer),e.setRenderTarget(b));let Fe=!1;ve.length!==C.cameras.length&&(C.cameras.length=0,Fe=!0);for(let P=0;P<ve.length;P++){let ae=ve[P],me=null;if(f!==null)me=f.getViewport(ae);else{let W=h.getViewSubImage(d,ae);me=W.viewport,P===0&&(e.setRenderTargetTextures(b,W.colorTexture,W.depthStencilTexture),e.setRenderTarget(b))}let fe=I[P];fe===void 0&&(fe=new Ut,fe.layers.enable(P),fe.viewport=new tt,I[P]=fe),fe.matrix.fromArray(ae.transform.matrix),fe.matrix.decompose(fe.position,fe.quaternion,fe.scale),fe.projectionMatrix.fromArray(ae.projectionMatrix),fe.projectionMatrixInverse.copy(fe.projectionMatrix).invert(),fe.viewport.set(me.x,me.y,me.width,me.height),P===0&&(C.matrix.copy(fe.matrix),C.matrix.decompose(C.position,C.quaternion,C.scale)),Fe===!0&&C.cameras.push(fe)}let Se=i.enabledFeatures;if(Se&&Se.includes("depth-sensing")&&i.depthUsage=="gpu-optimized"&&y){h=n.getBinding();let P=h.getDepthInformation(ve[0]);P&&P.isValid&&P.texture&&m.init(P,i.renderState)}if(Se&&Se.includes("camera-access")&&y){e.state.unbindTexture(),h=n.getBinding();for(let P=0;P<ve.length;P++){let ae=ve[P].camera;if(ae){let me=p[ae];me||(me=new ua,p[ae]=me);let fe=h.getCameraImage(ae);me.sourceTexture=fe}}}}for(let ve=0;ve<S.length;ve++){let Fe=w[ve],Se=S[ve];Fe!==null&&Se!==void 0&&Se.update(Fe,te,l||a)}$e&&$e(Q,te),te.detectedPlanes&&n.dispatchEvent({type:"planesdetected",data:te}),g=null}let Ye=new op;Ye.setAnimationLoop(ht),this.setAnimationLoop=function(Q){$e=Q},this.dispose=function(){}}},ys=new Dn,dv=new ke;function fv(s,e){function t(m,p){m.matrixAutoUpdate===!0&&m.updateMatrix(),p.value.copy(m.matrix)}function n(m,p){p.color.getRGB(m.fogColor.value,Th(s)),p.isFog?(m.fogNear.value=p.near,m.fogFar.value=p.far):p.isFogExp2&&(m.fogDensity.value=p.density)}function i(m,p,x,v,b){p.isMeshBasicMaterial||p.isMeshLambertMaterial?r(m,p):p.isMeshToonMaterial?(r(m,p),h(m,p)):p.isMeshPhongMaterial?(r(m,p),u(m,p)):p.isMeshStandardMaterial?(r(m,p),d(m,p),p.isMeshPhysicalMaterial&&f(m,p,b)):p.isMeshMatcapMaterial?(r(m,p),g(m,p)):p.isMeshDepthMaterial?r(m,p):p.isMeshDistanceMaterial?(r(m,p),y(m,p)):p.isMeshNormalMaterial?r(m,p):p.isLineBasicMaterial?(a(m,p),p.isLineDashedMaterial&&o(m,p)):p.isPointsMaterial?c(m,p,x,v):p.isSpriteMaterial?l(m,p):p.isShadowMaterial?(m.color.value.copy(p.color),m.opacity.value=p.opacity):p.isShaderMaterial&&(p.uniformsNeedUpdate=!1)}function r(m,p){m.opacity.value=p.opacity,p.color&&m.diffuse.value.copy(p.color),p.emissive&&m.emissive.value.copy(p.emissive).multiplyScalar(p.emissiveIntensity),p.map&&(m.map.value=p.map,t(p.map,m.mapTransform)),p.alphaMap&&(m.alphaMap.value=p.alphaMap,t(p.alphaMap,m.alphaMapTransform)),p.bumpMap&&(m.bumpMap.value=p.bumpMap,t(p.bumpMap,m.bumpMapTransform),m.bumpScale.value=p.bumpScale,p.side===Dt&&(m.bumpScale.value*=-1)),p.normalMap&&(m.normalMap.value=p.normalMap,t(p.normalMap,m.normalMapTransform),m.normalScale.value.copy(p.normalScale),p.side===Dt&&m.normalScale.value.negate()),p.displacementMap&&(m.displacementMap.value=p.displacementMap,t(p.displacementMap,m.displacementMapTransform),m.displacementScale.value=p.displacementScale,m.displacementBias.value=p.displacementBias),p.emissiveMap&&(m.emissiveMap.value=p.emissiveMap,t(p.emissiveMap,m.emissiveMapTransform)),p.specularMap&&(m.specularMap.value=p.specularMap,t(p.specularMap,m.specularMapTransform)),p.alphaTest>0&&(m.alphaTest.value=p.alphaTest);let x=e.get(p),v=x.envMap,b=x.envMapRotation;v&&(m.envMap.value=v,ys.copy(b),ys.x*=-1,ys.y*=-1,ys.z*=-1,v.isCubeTexture&&v.isRenderTargetTexture===!1&&(ys.y*=-1,ys.z*=-1),m.envMapRotation.value.setFromMatrix4(dv.makeRotationFromEuler(ys)),m.flipEnvMap.value=v.isCubeTexture&&v.isRenderTargetTexture===!1?-1:1,m.reflectivity.value=p.reflectivity,m.ior.value=p.ior,m.refractionRatio.value=p.refractionRatio),p.lightMap&&(m.lightMap.value=p.lightMap,m.lightMapIntensity.value=p.lightMapIntensity,t(p.lightMap,m.lightMapTransform)),p.aoMap&&(m.aoMap.value=p.aoMap,m.aoMapIntensity.value=p.aoMapIntensity,t(p.aoMap,m.aoMapTransform))}function a(m,p){m.diffuse.value.copy(p.color),m.opacity.value=p.opacity,p.map&&(m.map.value=p.map,t(p.map,m.mapTransform))}function o(m,p){m.dashSize.value=p.dashSize,m.totalSize.value=p.dashSize+p.gapSize,m.scale.value=p.scale}function c(m,p,x,v){m.diffuse.value.copy(p.color),m.opacity.value=p.opacity,m.size.value=p.size*x,m.scale.value=v*.5,p.map&&(m.map.value=p.map,t(p.map,m.uvTransform)),p.alphaMap&&(m.alphaMap.value=p.alphaMap,t(p.alphaMap,m.alphaMapTransform)),p.alphaTest>0&&(m.alphaTest.value=p.alphaTest)}function l(m,p){m.diffuse.value.copy(p.color),m.opacity.value=p.opacity,m.rotation.value=p.rotation,p.map&&(m.map.value=p.map,t(p.map,m.mapTransform)),p.alphaMap&&(m.alphaMap.value=p.alphaMap,t(p.alphaMap,m.alphaMapTransform)),p.alphaTest>0&&(m.alphaTest.value=p.alphaTest)}function u(m,p){m.specular.value.copy(p.specular),m.shininess.value=Math.max(p.shininess,1e-4)}function h(m,p){p.gradientMap&&(m.gradientMap.value=p.gradientMap)}function d(m,p){m.metalness.value=p.metalness,p.metalnessMap&&(m.metalnessMap.value=p.metalnessMap,t(p.metalnessMap,m.metalnessMapTransform)),m.roughness.value=p.roughness,p.roughnessMap&&(m.roughnessMap.value=p.roughnessMap,t(p.roughnessMap,m.roughnessMapTransform)),p.envMap&&(m.envMapIntensity.value=p.envMapIntensity)}function f(m,p,x){m.ior.value=p.ior,p.sheen>0&&(m.sheenColor.value.copy(p.sheenColor).multiplyScalar(p.sheen),m.sheenRoughness.value=p.sheenRoughness,p.sheenColorMap&&(m.sheenColorMap.value=p.sheenColorMap,t(p.sheenColorMap,m.sheenColorMapTransform)),p.sheenRoughnessMap&&(m.sheenRoughnessMap.value=p.sheenRoughnessMap,t(p.sheenRoughnessMap,m.sheenRoughnessMapTransform))),p.clearcoat>0&&(m.clearcoat.value=p.clearcoat,m.clearcoatRoughness.value=p.clearcoatRoughness,p.clearcoatMap&&(m.clearcoatMap.value=p.clearcoatMap,t(p.clearcoatMap,m.clearcoatMapTransform)),p.clearcoatRoughnessMap&&(m.clearcoatRoughnessMap.value=p.clearcoatRoughnessMap,t(p.clearcoatRoughnessMap,m.clearcoatRoughnessMapTransform)),p.clearcoatNormalMap&&(m.clearcoatNormalMap.value=p.clearcoatNormalMap,t(p.clearcoatNormalMap,m.clearcoatNormalMapTransform),m.clearcoatNormalScale.value.copy(p.clearcoatNormalScale),p.side===Dt&&m.clearcoatNormalScale.value.negate())),p.dispersion>0&&(m.dispersion.value=p.dispersion),p.iridescence>0&&(m.iridescence.value=p.iridescence,m.iridescenceIOR.value=p.iridescenceIOR,m.iridescenceThicknessMinimum.value=p.iridescenceThicknessRange[0],m.iridescenceThicknessMaximum.value=p.iridescenceThicknessRange[1],p.iridescenceMap&&(m.iridescenceMap.value=p.iridescenceMap,t(p.iridescenceMap,m.iridescenceMapTransform)),p.iridescenceThicknessMap&&(m.iridescenceThicknessMap.value=p.iridescenceThicknessMap,t(p.iridescenceThicknessMap,m.iridescenceThicknessMapTransform))),p.transmission>0&&(m.transmission.value=p.transmission,m.transmissionSamplerMap.value=x.texture,m.transmissionSamplerSize.value.set(x.width,x.height),p.transmissionMap&&(m.transmissionMap.value=p.transmissionMap,t(p.transmissionMap,m.transmissionMapTransform)),m.thickness.value=p.thickness,p.thicknessMap&&(m.thicknessMap.value=p.thicknessMap,t(p.thicknessMap,m.thicknessMapTransform)),m.attenuationDistance.value=p.attenuationDistance,m.attenuationColor.value.copy(p.attenuationColor)),p.anisotropy>0&&(m.anisotropyVector.value.set(p.anisotropy*Math.cos(p.anisotropyRotation),p.anisotropy*Math.sin(p.anisotropyRotation)),p.anisotropyMap&&(m.anisotropyMap.value=p.anisotropyMap,t(p.anisotropyMap,m.anisotropyMapTransform))),m.specularIntensity.value=p.specularIntensity,m.specularColor.value.copy(p.specularColor),p.specularColorMap&&(m.specularColorMap.value=p.specularColorMap,t(p.specularColorMap,m.specularColorMapTransform)),p.specularIntensityMap&&(m.specularIntensityMap.value=p.specularIntensityMap,t(p.specularIntensityMap,m.specularIntensityMapTransform))}function g(m,p){p.matcap&&(m.matcap.value=p.matcap)}function y(m,p){let x=e.get(p).light;m.referencePosition.value.setFromMatrixPosition(x.matrixWorld),m.nearDistance.value=x.shadow.camera.near,m.farDistance.value=x.shadow.camera.far}return{refreshFogUniforms:n,refreshMaterialUniforms:i}}function pv(s,e,t,n){let i={},r={},a=[],o=s.getParameter(s.MAX_UNIFORM_BUFFER_BINDINGS);function c(x,v){let b=v.program;n.uniformBlockBinding(x,b)}function l(x,v){let b=i[x.id];b===void 0&&(g(x),b=u(x),i[x.id]=b,x.addEventListener("dispose",m));let S=v.program;n.updateUBOMapping(x,S);let w=e.render.frame;r[x.id]!==w&&(d(x),r[x.id]=w)}function u(x){let v=h();x.__bindingPointIndex=v;let b=s.createBuffer(),S=x.__size,w=x.usage;return s.bindBuffer(s.UNIFORM_BUFFER,b),s.bufferData(s.UNIFORM_BUFFER,S,w),s.bindBuffer(s.UNIFORM_BUFFER,null),s.bindBufferBase(s.UNIFORM_BUFFER,v,b),b}function h(){for(let x=0;x<o;x++)if(a.indexOf(x)===-1)return a.push(x),x;return console.error("THREE.WebGLRenderer: Maximum number of simultaneously usable uniforms groups reached."),0}function d(x){let v=i[x.id],b=x.uniforms,S=x.__cache;s.bindBuffer(s.UNIFORM_BUFFER,v);for(let w=0,T=b.length;w<T;w++){let A=Array.isArray(b[w])?b[w]:[b[w]];for(let M=0,_=A.length;M<_;M++){let I=A[M];if(f(I,w,M,S)===!0){let C=I.__offset,D=Array.isArray(I.value)?I.value:[I.value],N=0;for(let U=0;U<D.length;U++){let B=D[U],J=y(B);typeof B=="number"||typeof B=="boolean"?(I.__data[0]=B,s.bufferSubData(s.UNIFORM_BUFFER,C+N,I.__data)):B.isMatrix3?(I.__data[0]=B.elements[0],I.__data[1]=B.elements[1],I.__data[2]=B.elements[2],I.__data[3]=0,I.__data[4]=B.elements[3],I.__data[5]=B.elements[4],I.__data[6]=B.elements[5],I.__data[7]=0,I.__data[8]=B.elements[6],I.__data[9]=B.elements[7],I.__data[10]=B.elements[8],I.__data[11]=0):(B.toArray(I.__data,N),N+=J.storage/Float32Array.BYTES_PER_ELEMENT)}s.bufferSubData(s.UNIFORM_BUFFER,C,I.__data)}}}s.bindBuffer(s.UNIFORM_BUFFER,null)}function f(x,v,b,S){let w=x.value,T=v+"_"+b;if(S[T]===void 0)return typeof w=="number"||typeof w=="boolean"?S[T]=w:S[T]=w.clone(),!0;{let A=S[T];if(typeof w=="number"||typeof w=="boolean"){if(A!==w)return S[T]=w,!0}else if(A.equals(w)===!1)return A.copy(w),!0}return!1}function g(x){let v=x.uniforms,b=0,S=16;for(let T=0,A=v.length;T<A;T++){let M=Array.isArray(v[T])?v[T]:[v[T]];for(let _=0,I=M.length;_<I;_++){let C=M[_],D=Array.isArray(C.value)?C.value:[C.value];for(let N=0,U=D.length;N<U;N++){let B=D[N],J=y(B),V=b%S,ne=V%J.boundary,ue=V+ne;b+=ne,ue!==0&&S-ue<J.storage&&(b+=S-ue),C.__data=new Float32Array(J.storage/Float32Array.BYTES_PER_ELEMENT),C.__offset=b,b+=J.storage}}}let w=b%S;return w>0&&(b+=S-w),x.__size=b,x.__cache={},this}function y(x){let v={boundary:0,storage:0};return typeof x=="number"||typeof x=="boolean"?(v.boundary=4,v.storage=4):x.isVector2?(v.boundary=8,v.storage=8):x.isVector3||x.isColor?(v.boundary=16,v.storage=12):x.isVector4?(v.boundary=16,v.storage=16):x.isMatrix3?(v.boundary=48,v.storage=48):x.isMatrix4?(v.boundary=64,v.storage=64):x.isTexture?console.warn("THREE.WebGLRenderer: Texture samplers can not be part of an uniforms group."):console.warn("THREE.WebGLRenderer: Unsupported uniform value type.",x),v}function m(x){let v=x.target;v.removeEventListener("dispose",m);let b=a.indexOf(v.__bindingPointIndex);a.splice(b,1),s.deleteBuffer(i[v.id]),delete i[v.id],delete r[v.id]}function p(){for(let x in i)s.deleteBuffer(i[x]);a=[],i={},r={}}return{bind:c,update:l,dispose:p}}var zc=class{constructor(e={}){let{canvas:t=Lf(),context:n=null,depth:i=!0,stencil:r=!1,alpha:a=!1,antialias:o=!1,premultipliedAlpha:c=!0,preserveDrawingBuffer:l=!1,powerPreference:u="default",failIfMajorPerformanceCaveat:h=!1,reversedDepthBuffer:d=!1}=e;this.isWebGLRenderer=!0;let f;if(n!==null){if(typeof WebGLRenderingContext<"u"&&n instanceof WebGLRenderingContext)throw new Error("THREE.WebGLRenderer: WebGL 1 is not supported since r163.");f=n.getContextAttributes().alpha}else f=a;let g=new Uint32Array(4),y=new Int32Array(4),m=null,p=null,x=[],v=[];this.domElement=t,this.debug={checkShaderErrors:!0,onShaderError:null},this.autoClear=!0,this.autoClearColor=!0,this.autoClearDepth=!0,this.autoClearStencil=!0,this.sortObjects=!0,this.clippingPlanes=[],this.localClippingEnabled=!1,this.toneMapping=Ei,this.toneMappingExposure=1,this.transmissionResolutionScale=1;let b=this,S=!1;this._outputColorSpace=kt;let w=0,T=0,A=null,M=-1,_=null,I=new tt,C=new tt,D=null,N=new Ue(0),U=0,B=t.width,J=t.height,V=1,ne=null,ue=null,_e=new tt(0,0,B,J),ze=new tt(0,0,B,J),$e=!1,ht=new rr,Ye=!1,Q=!1,te=new ke,ve=new L,Fe=new tt,Se={background:null,fog:null,environment:null,overrideMaterial:null,isScene:!0},je=!1;function Z(){return A===null?V:1}let P=n;function ae(R,z){return t.getContext(R,z)}try{let R={alpha:!0,depth:i,stencil:r,antialias:o,premultipliedAlpha:c,preserveDrawingBuffer:l,powerPreference:u,failIfMajorPerformanceCaveat:h};if("setAttribute"in t&&t.setAttribute("data-engine",`three.js r${"180"}`),t.addEventListener("webglcontextlost",ce,!1),t.addEventListener("webglcontextrestored",xe,!1),t.addEventListener("webglcontextcreationerror",ie,!1),P===null){let z="webgl2";if(P=ae(z,R),P===null)throw ae(z)?new Error("Error creating WebGL context with your selected attributes."):new Error("Error creating WebGL context.")}}catch(R){throw console.error("THREE.WebGLRenderer: "+R.message),R}let me,fe,W,de,j,re,Ie,Te,k,E,O,q,ee,K,Me,he,Ee,Pe,oe,ge,De,Ae,pe,Ve;function F(){me=new ky(P),me.init(),Ae=new lv(P,me),fe=new Ty(P,me,e,Ae),W=new ov(P,me),fe.reversedDepthBuffer&&d&&W.buffers.depth.setReversed(!0),de=new Ny(P),j=new jx,re=new cv(P,me,W,j,fe,Ae,de),Ie=new Ay(b),Te=new Py(b),k=new Hg(P),pe=new My(P,k),E=new Ly(P,k,de,pe),O=new Uy(P,E,k,de),oe=new Fy(P,fe,re),he=new Ey(j),q=new qx(b,Ie,Te,me,fe,pe,he),ee=new fv(b,j),K=new Zx,Me=new nv(me),Pe=new wy(b,Ie,Te,W,O,f,c),Ee=new rv(b,O,fe),Ve=new pv(P,de,fe,W),ge=new Sy(P,me,de),De=new Dy(P,me,de),de.programs=q.programs,b.capabilities=fe,b.extensions=me,b.properties=j,b.renderLists=K,b.shadowMap=Ee,b.state=W,b.info=de}F();let se=new Vh(b,P);this.xr=se,this.getContext=function(){return P},this.getContextAttributes=function(){return P.getContextAttributes()},this.forceContextLoss=function(){let R=me.get("WEBGL_lose_context");R&&R.loseContext()},this.forceContextRestore=function(){let R=me.get("WEBGL_lose_context");R&&R.restoreContext()},this.getPixelRatio=function(){return V},this.setPixelRatio=function(R){R!==void 0&&(V=R,this.setSize(B,J,!1))},this.getSize=function(R){return R.set(B,J)},this.setSize=function(R,z,Y=!0){if(se.isPresenting){console.warn("THREE.WebGLRenderer: Can't change size while VR device is presenting.");return}B=R,J=z,t.width=Math.floor(R*V),t.height=Math.floor(z*V),Y===!0&&(t.style.width=R+"px",t.style.height=z+"px"),this.setViewport(0,0,R,z)},this.getDrawingBufferSize=function(R){return R.set(B*V,J*V).floor()},this.setDrawingBufferSize=function(R,z,Y){B=R,J=z,V=Y,t.width=Math.floor(R*Y),t.height=Math.floor(z*Y),this.setViewport(0,0,R,z)},this.getCurrentViewport=function(R){return R.copy(I)},this.getViewport=function(R){return R.copy(_e)},this.setViewport=function(R,z,Y,X){R.isVector4?_e.set(R.x,R.y,R.z,R.w):_e.set(R,z,Y,X),W.viewport(I.copy(_e).multiplyScalar(V).round())},this.getScissor=function(R){return R.copy(ze)},this.setScissor=function(R,z,Y,X){R.isVector4?ze.set(R.x,R.y,R.z,R.w):ze.set(R,z,Y,X),W.scissor(C.copy(ze).multiplyScalar(V).round())},this.getScissorTest=function(){return $e},this.setScissorTest=function(R){W.setScissorTest($e=R)},this.setOpaqueSort=function(R){ne=R},this.setTransparentSort=function(R){ue=R},this.getClearColor=function(R){return R.copy(Pe.getClearColor())},this.setClearColor=function(){Pe.setClearColor(...arguments)},this.getClearAlpha=function(){return Pe.getClearAlpha()},this.setClearAlpha=function(){Pe.setClearAlpha(...arguments)},this.clear=function(R=!0,z=!0,Y=!0){let X=0;if(R){let H=!1;if(A!==null){let le=A.texture.format;H=le===ac||le===rc||le===sc}if(H){let le=A.texture.type,ye=le===jn||le===Oi||le===ur||le===dr||le===nc||le===ic,Re=Pe.getClearColor(),we=Pe.getClearAlpha(),He=Re.r,Ge=Re.g,Be=Re.b;ye?(g[0]=He,g[1]=Ge,g[2]=Be,g[3]=we,P.clearBufferuiv(P.COLOR,0,g)):(y[0]=He,y[1]=Ge,y[2]=Be,y[3]=we,P.clearBufferiv(P.COLOR,0,y))}else X|=P.COLOR_BUFFER_BIT}z&&(X|=P.DEPTH_BUFFER_BIT),Y&&(X|=P.STENCIL_BUFFER_BIT,this.state.buffers.stencil.setMask(4294967295)),P.clear(X)},this.clearColor=function(){this.clear(!0,!1,!1)},this.clearDepth=function(){this.clear(!1,!0,!1)},this.clearStencil=function(){this.clear(!1,!1,!0)},this.dispose=function(){t.removeEventListener("webglcontextlost",ce,!1),t.removeEventListener("webglcontextrestored",xe,!1),t.removeEventListener("webglcontextcreationerror",ie,!1),Pe.dispose(),K.dispose(),Me.dispose(),j.dispose(),Ie.dispose(),Te.dispose(),O.dispose(),pe.dispose(),Ve.dispose(),q.dispose(),se.dispose(),se.removeEventListener("sessionstart",Jn),se.removeEventListener("sessionend",td),qi.stop()};function ce(R){R.preventDefault(),console.log("THREE.WebGLRenderer: Context Lost."),S=!0}function xe(){console.log("THREE.WebGLRenderer: Context Restored."),S=!1;let R=de.autoReset,z=Ee.enabled,Y=Ee.autoUpdate,X=Ee.needsUpdate,H=Ee.type;F(),de.autoReset=R,Ee.enabled=z,Ee.autoUpdate=Y,Ee.needsUpdate=X,Ee.type=H}function ie(R){console.error("THREE.WebGLRenderer: A WebGL context could not be created. Reason: ",R.statusMessage)}function $(R){let z=R.target;z.removeEventListener("dispose",$),Ce(z)}function Ce(R){Xe(R),j.remove(R)}function Xe(R){let z=j.get(R).programs;z!==void 0&&(z.forEach(function(Y){q.releaseProgram(Y)}),R.isShaderMaterial&&q.releaseShaderCache(R))}this.renderBufferDirect=function(R,z,Y,X,H,le){z===null&&(z=Se);let ye=H.isMesh&&H.matrixWorld.determinant()<0,Re=Pm(R,z,Y,X,H);W.setMaterial(X,ye);let we=Y.index,He=1;if(X.wireframe===!0){if(we=E.getWireframeAttribute(Y),we===void 0)return;He=2}let Ge=Y.drawRange,Be=Y.attributes.position,Qe=Ge.start*He,mt=(Ge.start+Ge.count)*He;le!==null&&(Qe=Math.max(Qe,le.start*He),mt=Math.min(mt,(le.start+le.count)*He)),we!==null?(Qe=Math.max(Qe,0),mt=Math.min(mt,we.count)):Be!=null&&(Qe=Math.max(Qe,0),mt=Math.min(mt,Be.count));let It=mt-Qe;if(It<0||It===1/0)return;pe.setup(H,X,Re,Y,we);let St,bt=ge;if(we!==null&&(St=k.get(we),bt=De,bt.setIndex(St)),H.isMesh)X.wireframe===!0?(W.setLineWidth(X.wireframeLinewidth*Z()),bt.setMode(P.LINES)):bt.setMode(P.TRIANGLES);else if(H.isLine){let Oe=X.linewidth;Oe===void 0&&(Oe=1),W.setLineWidth(Oe*Z()),H.isLineSegments?bt.setMode(P.LINES):H.isLineLoop?bt.setMode(P.LINE_LOOP):bt.setMode(P.LINE_STRIP)}else H.isPoints?bt.setMode(P.POINTS):H.isSprite&&bt.setMode(P.TRIANGLES);if(H.isBatchedMesh)if(H._multiDrawInstances!==null)Js("THREE.WebGLRenderer: renderMultiDrawInstances has been deprecated and will be removed in r184. Append to renderMultiDraw arguments and use indirection."),bt.renderMultiDrawInstances(H._multiDrawStarts,H._multiDrawCounts,H._multiDrawCount,H._multiDrawInstances);else if(me.get("WEBGL_multi_draw"))bt.renderMultiDraw(H._multiDrawStarts,H._multiDrawCounts,H._multiDrawCount);else{let Oe=H._multiDrawStarts,At=H._multiDrawCounts,rt=H._multiDrawCount,vn=we?k.get(we).bytesPerElement:1,Is=j.get(X).currentProgram.getUniforms();for(let _n=0;_n<rt;_n++)Is.setValue(P,"_gl_DrawID",_n),bt.render(Oe[_n]/vn,At[_n])}else if(H.isInstancedMesh)bt.renderInstances(Qe,It,H.count);else if(Y.isInstancedBufferGeometry){let Oe=Y._maxInstanceCount!==void 0?Y._maxInstanceCount:1/0,At=Math.min(Y.instanceCount,Oe);bt.renderInstances(Qe,It,At)}else bt.render(Qe,It)};function wt(R,z,Y){R.transparent===!0&&R.side===Mt&&R.forceSinglePass===!1?(R.side=Dt,R.needsUpdate=!0,Ka(R,z,Y),R.side=pn,R.needsUpdate=!0,Ka(R,z,Y),R.side=Mt):Ka(R,z,Y)}this.compile=function(R,z,Y=null){Y===null&&(Y=R),p=Me.get(Y),p.init(z),v.push(p),Y.traverseVisible(function(H){H.isLight&&H.layers.test(z.layers)&&(p.pushLight(H),H.castShadow&&p.pushShadow(H))}),R!==Y&&R.traverseVisible(function(H){H.isLight&&H.layers.test(z.layers)&&(p.pushLight(H),H.castShadow&&p.pushShadow(H))}),p.setupLights();let X=new Set;return R.traverse(function(H){if(!(H.isMesh||H.isPoints||H.isLine||H.isSprite))return;let le=H.material;if(le)if(Array.isArray(le))for(let ye=0;ye<le.length;ye++){let Re=le[ye];wt(Re,Y,H),X.add(Re)}else wt(le,Y,H),X.add(le)}),p=v.pop(),X},this.compileAsync=function(R,z,Y=null){let X=this.compile(R,z,Y);return new Promise(H=>{function le(){if(X.forEach(function(ye){j.get(ye).currentProgram.isReady()&&X.delete(ye)}),X.size===0){H(R);return}setTimeout(le,10)}me.get("KHR_parallel_shader_compile")!==null?le():setTimeout(le,10)})};let ut=null;function hi(R){ut&&ut(R)}function Jn(){qi.stop()}function td(){qi.start()}let qi=new op;qi.setAnimationLoop(hi),typeof self<"u"&&qi.setContext(self),this.setAnimationLoop=function(R){ut=R,se.setAnimationLoop(R),R===null?qi.stop():qi.start()},se.addEventListener("sessionstart",Jn),se.addEventListener("sessionend",td),this.render=function(R,z){if(z!==void 0&&z.isCamera!==!0){console.error("THREE.WebGLRenderer.render: camera is not an instance of THREE.Camera.");return}if(S===!0)return;if(R.matrixWorldAutoUpdate===!0&&R.updateMatrixWorld(),z.parent===null&&z.matrixWorldAutoUpdate===!0&&z.updateMatrixWorld(),se.enabled===!0&&se.isPresenting===!0&&(se.cameraAutoUpdate===!0&&se.updateCamera(z),z=se.getCamera()),R.isScene===!0&&R.onBeforeRender(b,R,z,A),p=Me.get(R,v.length),p.init(z),v.push(p),te.multiplyMatrices(z.projectionMatrix,z.matrixWorldInverse),ht.setFromProjectionMatrix(te,Wn,z.reversedDepth),Q=this.localClippingEnabled,Ye=he.init(this.clippingPlanes,Q),m=K.get(R,x.length),m.init(),x.push(m),se.enabled===!0&&se.isPresenting===!0){let le=b.xr.getDepthSensingMesh();le!==null&&_l(le,z,-1/0,b.sortObjects)}_l(R,z,0,b.sortObjects),m.finish(),b.sortObjects===!0&&m.sort(ne,ue),je=se.enabled===!1||se.isPresenting===!1||se.hasDepthSensing()===!1,je&&Pe.addToRenderList(m,R),this.info.render.frame++,Ye===!0&&he.beginShadows();let Y=p.state.shadowsArray;Ee.render(Y,R,z),Ye===!0&&he.endShadows(),this.info.autoReset===!0&&this.info.reset();let X=m.opaque,H=m.transmissive;if(p.setupLights(),z.isArrayCamera){let le=z.cameras;if(H.length>0)for(let ye=0,Re=le.length;ye<Re;ye++){let we=le[ye];id(X,H,R,we)}je&&Pe.render(R);for(let ye=0,Re=le.length;ye<Re;ye++){let we=le[ye];nd(m,R,we,we.viewport)}}else H.length>0&&id(X,H,R,z),je&&Pe.render(R),nd(m,R,z);A!==null&&T===0&&(re.updateMultisampleRenderTarget(A),re.updateRenderTargetMipmap(A)),R.isScene===!0&&R.onAfterRender(b,R,z),pe.resetDefaultState(),M=-1,_=null,v.pop(),v.length>0?(p=v[v.length-1],Ye===!0&&he.setGlobalState(b.clippingPlanes,p.state.camera)):p=null,x.pop(),x.length>0?m=x[x.length-1]:m=null};function _l(R,z,Y,X){if(R.visible===!1)return;if(R.layers.test(z.layers)){if(R.isGroup)Y=R.renderOrder;else if(R.isLOD)R.autoUpdate===!0&&R.update(z);else if(R.isLight)p.pushLight(R),R.castShadow&&p.pushShadow(R);else if(R.isSprite){if(!R.frustumCulled||ht.intersectsSprite(R)){X&&Fe.setFromMatrixPosition(R.matrixWorld).applyMatrix4(te);let ye=O.update(R),Re=R.material;Re.visible&&m.push(R,ye,Re,Y,Fe.z,null)}}else if((R.isMesh||R.isLine||R.isPoints)&&(!R.frustumCulled||ht.intersectsObject(R))){let ye=O.update(R),Re=R.material;if(X&&(R.boundingSphere!==void 0?(R.boundingSphere===null&&R.computeBoundingSphere(),Fe.copy(R.boundingSphere.center)):(ye.boundingSphere===null&&ye.computeBoundingSphere(),Fe.copy(ye.boundingSphere.center)),Fe.applyMatrix4(R.matrixWorld).applyMatrix4(te)),Array.isArray(Re)){let we=ye.groups;for(let He=0,Ge=we.length;He<Ge;He++){let Be=we[He],Qe=Re[Be.materialIndex];Qe&&Qe.visible&&m.push(R,ye,Qe,Y,Fe.z,Be)}}else Re.visible&&m.push(R,ye,Re,Y,Fe.z,null)}}let le=R.children;for(let ye=0,Re=le.length;ye<Re;ye++)_l(le[ye],z,Y,X)}function nd(R,z,Y,X){let H=R.opaque,le=R.transmissive,ye=R.transparent;p.setupLightsView(Y),Ye===!0&&he.setGlobalState(b.clippingPlanes,Y),X&&W.viewport(I.copy(X)),H.length>0&&ja(H,z,Y),le.length>0&&ja(le,z,Y),ye.length>0&&ja(ye,z,Y),W.buffers.depth.setTest(!0),W.buffers.depth.setMask(!0),W.buffers.color.setMask(!0),W.setPolygonOffset(!1)}function id(R,z,Y,X){if((Y.isScene===!0?Y.overrideMaterial:null)!==null)return;p.state.transmissionRenderTarget[X.id]===void 0&&(p.state.transmissionRenderTarget[X.id]=new ei(1,1,{generateMipmaps:!0,type:me.has("EXT_color_buffer_half_float")||me.has("EXT_color_buffer_float")?zi:jn,minFilter:qn,samples:4,stencilBuffer:r,resolveDepthBuffer:!1,resolveStencilBuffer:!1,colorSpace:et.workingColorSpace}));let le=p.state.transmissionRenderTarget[X.id],ye=X.viewport||I;le.setSize(ye.z*b.transmissionResolutionScale,ye.w*b.transmissionResolutionScale);let Re=b.getRenderTarget(),we=b.getActiveCubeFace(),He=b.getActiveMipmapLevel();b.setRenderTarget(le),b.getClearColor(N),U=b.getClearAlpha(),U<1&&b.setClearColor(16777215,.5),b.clear(),je&&Pe.render(Y);let Ge=b.toneMapping;b.toneMapping=Ei;let Be=X.viewport;if(X.viewport!==void 0&&(X.viewport=void 0),p.setupLightsView(X),Ye===!0&&he.setGlobalState(b.clippingPlanes,X),ja(R,Y,X),re.updateMultisampleRenderTarget(le),re.updateRenderTargetMipmap(le),me.has("WEBGL_multisampled_render_to_texture")===!1){let Qe=!1;for(let mt=0,It=z.length;mt<It;mt++){let St=z[mt],bt=St.object,Oe=St.geometry,At=St.material,rt=St.group;if(At.side===Mt&&bt.layers.test(X.layers)){let vn=At.side;At.side=Dt,At.needsUpdate=!0,sd(bt,Y,X,Oe,At,rt),At.side=vn,At.needsUpdate=!0,Qe=!0}}Qe===!0&&(re.updateMultisampleRenderTarget(le),re.updateRenderTargetMipmap(le))}b.setRenderTarget(Re,we,He),b.setClearColor(N,U),Be!==void 0&&(X.viewport=Be),b.toneMapping=Ge}function ja(R,z,Y){let X=z.isScene===!0?z.overrideMaterial:null;for(let H=0,le=R.length;H<le;H++){let ye=R[H],Re=ye.object,we=ye.geometry,He=ye.group,Ge=ye.material;Ge.allowOverride===!0&&X!==null&&(Ge=X),Re.layers.test(Y.layers)&&sd(Re,z,Y,we,Ge,He)}}function sd(R,z,Y,X,H,le){R.onBeforeRender(b,z,Y,X,H,le),R.modelViewMatrix.multiplyMatrices(Y.matrixWorldInverse,R.matrixWorld),R.normalMatrix.getNormalMatrix(R.modelViewMatrix),H.onBeforeRender(b,z,Y,X,R,le),H.transparent===!0&&H.side===Mt&&H.forceSinglePass===!1?(H.side=Dt,H.needsUpdate=!0,b.renderBufferDirect(Y,z,X,H,R,le),H.side=pn,H.needsUpdate=!0,b.renderBufferDirect(Y,z,X,H,R,le),H.side=Mt):b.renderBufferDirect(Y,z,X,H,R,le),R.onAfterRender(b,z,Y,X,H,le)}function Ka(R,z,Y){z.isScene!==!0&&(z=Se);let X=j.get(R),H=p.state.lights,le=p.state.shadowsArray,ye=H.state.version,Re=q.getParameters(R,H.state,le,z,Y),we=q.getProgramCacheKey(Re),He=X.programs;X.environment=R.isMeshStandardMaterial?z.environment:null,X.fog=z.fog,X.envMap=(R.isMeshStandardMaterial?Te:Ie).get(R.envMap||X.environment),X.envMapRotation=X.environment!==null&&R.envMap===null?z.environmentRotation:R.envMapRotation,He===void 0&&(R.addEventListener("dispose",$),He=new Map,X.programs=He);let Ge=He.get(we);if(Ge!==void 0){if(X.currentProgram===Ge&&X.lightsStateVersion===ye)return ad(R,Re),Ge}else Re.uniforms=q.getUniforms(R),R.onBeforeCompile(Re,b),Ge=q.acquireProgram(Re,we),He.set(we,Ge),X.uniforms=Re.uniforms;let Be=X.uniforms;return(!R.isShaderMaterial&&!R.isRawShaderMaterial||R.clipping===!0)&&(Be.clippingPlanes=he.uniform),ad(R,Re),X.needsLights=Lm(R),X.lightsStateVersion=ye,X.needsLights&&(Be.ambientLightColor.value=H.state.ambient,Be.lightProbe.value=H.state.probe,Be.directionalLights.value=H.state.directional,Be.directionalLightShadows.value=H.state.directionalShadow,Be.spotLights.value=H.state.spot,Be.spotLightShadows.value=H.state.spotShadow,Be.rectAreaLights.value=H.state.rectArea,Be.ltc_1.value=H.state.rectAreaLTC1,Be.ltc_2.value=H.state.rectAreaLTC2,Be.pointLights.value=H.state.point,Be.pointLightShadows.value=H.state.pointShadow,Be.hemisphereLights.value=H.state.hemi,Be.directionalShadowMap.value=H.state.directionalShadowMap,Be.directionalShadowMatrix.value=H.state.directionalShadowMatrix,Be.spotShadowMap.value=H.state.spotShadowMap,Be.spotLightMatrix.value=H.state.spotLightMatrix,Be.spotLightMap.value=H.state.spotLightMap,Be.pointShadowMap.value=H.state.pointShadowMap,Be.pointShadowMatrix.value=H.state.pointShadowMatrix),X.currentProgram=Ge,X.uniformsList=null,Ge}function rd(R){if(R.uniformsList===null){let z=R.currentProgram.getUniforms();R.uniformsList=yr.seqWithValue(z.seq,R.uniforms)}return R.uniformsList}function ad(R,z){let Y=j.get(R);Y.outputColorSpace=z.outputColorSpace,Y.batching=z.batching,Y.batchingColor=z.batchingColor,Y.instancing=z.instancing,Y.instancingColor=z.instancingColor,Y.instancingMorph=z.instancingMorph,Y.skinning=z.skinning,Y.morphTargets=z.morphTargets,Y.morphNormals=z.morphNormals,Y.morphColors=z.morphColors,Y.morphTargetsCount=z.morphTargetsCount,Y.numClippingPlanes=z.numClippingPlanes,Y.numIntersection=z.numClipIntersection,Y.vertexAlphas=z.vertexAlphas,Y.vertexTangents=z.vertexTangents,Y.toneMapping=z.toneMapping}function Pm(R,z,Y,X,H){z.isScene!==!0&&(z=Se),re.resetTextureUnits();let le=z.fog,ye=X.isMeshStandardMaterial?z.environment:null,Re=A===null?b.outputColorSpace:A.isXRRenderTarget===!0?A.texture.colorSpace:Kt,we=(X.isMeshStandardMaterial?Te:Ie).get(X.envMap||ye),He=X.vertexColors===!0&&!!Y.attributes.color&&Y.attributes.color.itemSize===4,Ge=!!Y.attributes.tangent&&(!!X.normalMap||X.anisotropy>0),Be=!!Y.morphAttributes.position,Qe=!!Y.morphAttributes.normal,mt=!!Y.morphAttributes.color,It=Ei;X.toneMapped&&(A===null||A.isXRRenderTarget===!0)&&(It=b.toneMapping);let St=Y.morphAttributes.position||Y.morphAttributes.normal||Y.morphAttributes.color,bt=St!==void 0?St.length:0,Oe=j.get(X),At=p.state.lights;if(Ye===!0&&(Q===!0||R!==_)){let an=R===_&&X.id===M;he.setState(X,R,an)}let rt=!1;X.version===Oe.__version?(Oe.needsLights&&Oe.lightsStateVersion!==At.state.version||Oe.outputColorSpace!==Re||H.isBatchedMesh&&Oe.batching===!1||!H.isBatchedMesh&&Oe.batching===!0||H.isBatchedMesh&&Oe.batchingColor===!0&&H.colorTexture===null||H.isBatchedMesh&&Oe.batchingColor===!1&&H.colorTexture!==null||H.isInstancedMesh&&Oe.instancing===!1||!H.isInstancedMesh&&Oe.instancing===!0||H.isSkinnedMesh&&Oe.skinning===!1||!H.isSkinnedMesh&&Oe.skinning===!0||H.isInstancedMesh&&Oe.instancingColor===!0&&H.instanceColor===null||H.isInstancedMesh&&Oe.instancingColor===!1&&H.instanceColor!==null||H.isInstancedMesh&&Oe.instancingMorph===!0&&H.morphTexture===null||H.isInstancedMesh&&Oe.instancingMorph===!1&&H.morphTexture!==null||Oe.envMap!==we||X.fog===!0&&Oe.fog!==le||Oe.numClippingPlanes!==void 0&&(Oe.numClippingPlanes!==he.numPlanes||Oe.numIntersection!==he.numIntersection)||Oe.vertexAlphas!==He||Oe.vertexTangents!==Ge||Oe.morphTargets!==Be||Oe.morphNormals!==Qe||Oe.morphColors!==mt||Oe.toneMapping!==It||Oe.morphTargetsCount!==bt)&&(rt=!0):(rt=!0,Oe.__version=X.version);let vn=Oe.currentProgram;rt===!0&&(vn=Ka(X,z,H));let Is=!1,_n=!1,Br=!1,Rt=vn.getUniforms(),In=Oe.uniforms;if(W.useProgram(vn.program)&&(Is=!0,_n=!0,Br=!0),X.id!==M&&(M=X.id,_n=!0),Is||_!==R){W.buffers.depth.getReversed()&&R.reversedDepth!==!0&&(R._reversedDepth=!0,R.updateProjectionMatrix()),Rt.setValue(P,"projectionMatrix",R.projectionMatrix),Rt.setValue(P,"viewMatrix",R.matrixWorldInverse);let dn=Rt.map.cameraPosition;dn!==void 0&&dn.setValue(P,ve.setFromMatrixPosition(R.matrixWorld)),fe.logarithmicDepthBuffer&&Rt.setValue(P,"logDepthBufFC",2/(Math.log(R.far+1)/Math.LN2)),(X.isMeshPhongMaterial||X.isMeshToonMaterial||X.isMeshLambertMaterial||X.isMeshBasicMaterial||X.isMeshStandardMaterial||X.isShaderMaterial)&&Rt.setValue(P,"isOrthographic",R.isOrthographicCamera===!0),_!==R&&(_=R,_n=!0,Br=!0)}if(H.isSkinnedMesh){Rt.setOptional(P,H,"bindMatrix"),Rt.setOptional(P,H,"bindMatrixInverse");let an=H.skeleton;an&&(an.boneTexture===null&&an.computeBoneTexture(),Rt.setValue(P,"boneTexture",an.boneTexture,re))}H.isBatchedMesh&&(Rt.setOptional(P,H,"batchingTexture"),Rt.setValue(P,"batchingTexture",H._matricesTexture,re),Rt.setOptional(P,H,"batchingIdTexture"),Rt.setValue(P,"batchingIdTexture",H._indirectTexture,re),Rt.setOptional(P,H,"batchingColorTexture"),H._colorsTexture!==null&&Rt.setValue(P,"batchingColorTexture",H._colorsTexture,re));let Pn=Y.morphAttributes;if((Pn.position!==void 0||Pn.normal!==void 0||Pn.color!==void 0)&&oe.update(H,Y,vn),(_n||Oe.receiveShadow!==H.receiveShadow)&&(Oe.receiveShadow=H.receiveShadow,Rt.setValue(P,"receiveShadow",H.receiveShadow)),X.isMeshGouraudMaterial&&X.envMap!==null&&(In.envMap.value=we,In.flipEnvMap.value=we.isCubeTexture&&we.isRenderTargetTexture===!1?-1:1),X.isMeshStandardMaterial&&X.envMap===null&&z.environment!==null&&(In.envMapIntensity.value=z.environmentIntensity),_n&&(Rt.setValue(P,"toneMappingExposure",b.toneMappingExposure),Oe.needsLights&&km(In,Br),le&&X.fog===!0&&ee.refreshFogUniforms(In,le),ee.refreshMaterialUniforms(In,X,V,J,p.state.transmissionRenderTarget[R.id]),yr.upload(P,rd(Oe),In,re)),X.isShaderMaterial&&X.uniformsNeedUpdate===!0&&(yr.upload(P,rd(Oe),In,re),X.uniformsNeedUpdate=!1),X.isSpriteMaterial&&Rt.setValue(P,"center",H.center),Rt.setValue(P,"modelViewMatrix",H.modelViewMatrix),Rt.setValue(P,"normalMatrix",H.normalMatrix),Rt.setValue(P,"modelMatrix",H.matrixWorld),X.isShaderMaterial||X.isRawShaderMaterial){let an=X.uniformsGroups;for(let dn=0,wl=an.length;dn<wl;dn++){let ji=an[dn];Ve.update(ji,vn),Ve.bind(ji,vn)}}return vn}function km(R,z){R.ambientLightColor.needsUpdate=z,R.lightProbe.needsUpdate=z,R.directionalLights.needsUpdate=z,R.directionalLightShadows.needsUpdate=z,R.pointLights.needsUpdate=z,R.pointLightShadows.needsUpdate=z,R.spotLights.needsUpdate=z,R.spotLightShadows.needsUpdate=z,R.rectAreaLights.needsUpdate=z,R.hemisphereLights.needsUpdate=z}function Lm(R){return R.isMeshLambertMaterial||R.isMeshToonMaterial||R.isMeshPhongMaterial||R.isMeshStandardMaterial||R.isShadowMaterial||R.isShaderMaterial&&R.lights===!0}this.getActiveCubeFace=function(){return w},this.getActiveMipmapLevel=function(){return T},this.getRenderTarget=function(){return A},this.setRenderTargetTextures=function(R,z,Y){let X=j.get(R);X.__autoAllocateDepthBuffer=R.resolveDepthBuffer===!1,X.__autoAllocateDepthBuffer===!1&&(X.__useRenderToTexture=!1),j.get(R.texture).__webglTexture=z,j.get(R.depthTexture).__webglTexture=X.__autoAllocateDepthBuffer?void 0:Y,X.__hasExternalTextures=!0},this.setRenderTargetFramebuffer=function(R,z){let Y=j.get(R);Y.__webglFramebuffer=z,Y.__useDefaultFramebuffer=z===void 0};let Dm=P.createFramebuffer();this.setRenderTarget=function(R,z=0,Y=0){A=R,w=z,T=Y;let X=!0,H=null,le=!1,ye=!1;if(R){let we=j.get(R);if(we.__useDefaultFramebuffer!==void 0)W.bindFramebuffer(P.FRAMEBUFFER,null),X=!1;else if(we.__webglFramebuffer===void 0)re.setupRenderTarget(R);else if(we.__hasExternalTextures)re.rebindTextures(R,j.get(R.texture).__webglTexture,j.get(R.depthTexture).__webglTexture);else if(R.depthBuffer){let Be=R.depthTexture;if(we.__boundDepthTexture!==Be){if(Be!==null&&j.has(Be)&&(R.width!==Be.image.width||R.height!==Be.image.height))throw new Error("WebGLRenderTarget: Attached DepthTexture is initialized to the incorrect size.");re.setupDepthRenderbuffer(R)}}let He=R.texture;(He.isData3DTexture||He.isDataArrayTexture||He.isCompressedArrayTexture)&&(ye=!0);let Ge=j.get(R).__webglFramebuffer;R.isWebGLCubeRenderTarget?(Array.isArray(Ge[z])?H=Ge[z][Y]:H=Ge[z],le=!0):R.samples>0&&re.useMultisampledRTT(R)===!1?H=j.get(R).__webglMultisampledFramebuffer:Array.isArray(Ge)?H=Ge[Y]:H=Ge,I.copy(R.viewport),C.copy(R.scissor),D=R.scissorTest}else I.copy(_e).multiplyScalar(V).floor(),C.copy(ze).multiplyScalar(V).floor(),D=$e;if(Y!==0&&(H=Dm),W.bindFramebuffer(P.FRAMEBUFFER,H)&&X&&W.drawBuffers(R,H),W.viewport(I),W.scissor(C),W.setScissorTest(D),le){let we=j.get(R.texture);P.framebufferTexture2D(P.FRAMEBUFFER,P.COLOR_ATTACHMENT0,P.TEXTURE_CUBE_MAP_POSITIVE_X+z,we.__webglTexture,Y)}else if(ye){let we=z;for(let He=0;He<R.textures.length;He++){let Ge=j.get(R.textures[He]);P.framebufferTextureLayer(P.FRAMEBUFFER,P.COLOR_ATTACHMENT0+He,Ge.__webglTexture,Y,we)}}else if(R!==null&&Y!==0){let we=j.get(R.texture);P.framebufferTexture2D(P.FRAMEBUFFER,P.COLOR_ATTACHMENT0,P.TEXTURE_2D,we.__webglTexture,Y)}M=-1},this.readRenderTargetPixels=function(R,z,Y,X,H,le,ye,Re=0){if(!(R&&R.isWebGLRenderTarget)){console.error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not THREE.WebGLRenderTarget.");return}let we=j.get(R).__webglFramebuffer;if(R.isWebGLCubeRenderTarget&&ye!==void 0&&(we=we[ye]),we){W.bindFramebuffer(P.FRAMEBUFFER,we);try{let He=R.textures[Re],Ge=He.format,Be=He.type;if(!fe.textureFormatReadable(Ge)){console.error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not in RGBA or implementation defined format.");return}if(!fe.textureTypeReadable(Be)){console.error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not in UnsignedByteType or implementation defined type.");return}z>=0&&z<=R.width-X&&Y>=0&&Y<=R.height-H&&(R.textures.length>1&&P.readBuffer(P.COLOR_ATTACHMENT0+Re),P.readPixels(z,Y,X,H,Ae.convert(Ge),Ae.convert(Be),le))}finally{let He=A!==null?j.get(A).__webglFramebuffer:null;W.bindFramebuffer(P.FRAMEBUFFER,He)}}},this.readRenderTargetPixelsAsync=async function(R,z,Y,X,H,le,ye,Re=0){if(!(R&&R.isWebGLRenderTarget))throw new Error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not THREE.WebGLRenderTarget.");let we=j.get(R).__webglFramebuffer;if(R.isWebGLCubeRenderTarget&&ye!==void 0&&(we=we[ye]),we)if(z>=0&&z<=R.width-X&&Y>=0&&Y<=R.height-H){W.bindFramebuffer(P.FRAMEBUFFER,we);let He=R.textures[Re],Ge=He.format,Be=He.type;if(!fe.textureFormatReadable(Ge))throw new Error("THREE.WebGLRenderer.readRenderTargetPixelsAsync: renderTarget is not in RGBA or implementation defined format.");if(!fe.textureTypeReadable(Be))throw new Error("THREE.WebGLRenderer.readRenderTargetPixelsAsync: renderTarget is not in UnsignedByteType or implementation defined type.");let Qe=P.createBuffer();P.bindBuffer(P.PIXEL_PACK_BUFFER,Qe),P.bufferData(P.PIXEL_PACK_BUFFER,le.byteLength,P.STREAM_READ),R.textures.length>1&&P.readBuffer(P.COLOR_ATTACHMENT0+Re),P.readPixels(z,Y,X,H,Ae.convert(Ge),Ae.convert(Be),0);let mt=A!==null?j.get(A).__webglFramebuffer:null;W.bindFramebuffer(P.FRAMEBUFFER,mt);let It=P.fenceSync(P.SYNC_GPU_COMMANDS_COMPLETE,0);return P.flush(),await Df(P,It,4),P.bindBuffer(P.PIXEL_PACK_BUFFER,Qe),P.getBufferSubData(P.PIXEL_PACK_BUFFER,0,le),P.deleteBuffer(Qe),P.deleteSync(It),le}else throw new Error("THREE.WebGLRenderer.readRenderTargetPixelsAsync: requested read bounds are out of range.")},this.copyFramebufferToTexture=function(R,z=null,Y=0){let X=Math.pow(2,-Y),H=Math.floor(R.image.width*X),le=Math.floor(R.image.height*X),ye=z!==null?z.x:0,Re=z!==null?z.y:0;re.setTexture2D(R,0),P.copyTexSubImage2D(P.TEXTURE_2D,Y,0,0,ye,Re,H,le),W.unbindTexture()};let Nm=P.createFramebuffer(),Fm=P.createFramebuffer();this.copyTextureToTexture=function(R,z,Y=null,X=null,H=0,le=null){le===null&&(H!==0?(Js("WebGLRenderer: copyTextureToTexture function signature has changed to support src and dst mipmap levels."),le=H,H=0):le=0);let ye,Re,we,He,Ge,Be,Qe,mt,It,St=R.isCompressedTexture?R.mipmaps[le]:R.image;if(Y!==null)ye=Y.max.x-Y.min.x,Re=Y.max.y-Y.min.y,we=Y.isBox3?Y.max.z-Y.min.z:1,He=Y.min.x,Ge=Y.min.y,Be=Y.isBox3?Y.min.z:0;else{let Pn=Math.pow(2,-H);ye=Math.floor(St.width*Pn),Re=Math.floor(St.height*Pn),R.isDataArrayTexture?we=St.depth:R.isData3DTexture?we=Math.floor(St.depth*Pn):we=1,He=0,Ge=0,Be=0}X!==null?(Qe=X.x,mt=X.y,It=X.z):(Qe=0,mt=0,It=0);let bt=Ae.convert(z.format),Oe=Ae.convert(z.type),At;z.isData3DTexture?(re.setTexture3D(z,0),At=P.TEXTURE_3D):z.isDataArrayTexture||z.isCompressedArrayTexture?(re.setTexture2DArray(z,0),At=P.TEXTURE_2D_ARRAY):(re.setTexture2D(z,0),At=P.TEXTURE_2D),P.pixelStorei(P.UNPACK_FLIP_Y_WEBGL,z.flipY),P.pixelStorei(P.UNPACK_PREMULTIPLY_ALPHA_WEBGL,z.premultiplyAlpha),P.pixelStorei(P.UNPACK_ALIGNMENT,z.unpackAlignment);let rt=P.getParameter(P.UNPACK_ROW_LENGTH),vn=P.getParameter(P.UNPACK_IMAGE_HEIGHT),Is=P.getParameter(P.UNPACK_SKIP_PIXELS),_n=P.getParameter(P.UNPACK_SKIP_ROWS),Br=P.getParameter(P.UNPACK_SKIP_IMAGES);P.pixelStorei(P.UNPACK_ROW_LENGTH,St.width),P.pixelStorei(P.UNPACK_IMAGE_HEIGHT,St.height),P.pixelStorei(P.UNPACK_SKIP_PIXELS,He),P.pixelStorei(P.UNPACK_SKIP_ROWS,Ge),P.pixelStorei(P.UNPACK_SKIP_IMAGES,Be);let Rt=R.isDataArrayTexture||R.isData3DTexture,In=z.isDataArrayTexture||z.isData3DTexture;if(R.isDepthTexture){let Pn=j.get(R),an=j.get(z),dn=j.get(Pn.__renderTarget),wl=j.get(an.__renderTarget);W.bindFramebuffer(P.READ_FRAMEBUFFER,dn.__webglFramebuffer),W.bindFramebuffer(P.DRAW_FRAMEBUFFER,wl.__webglFramebuffer);for(let ji=0;ji<we;ji++)Rt&&(P.framebufferTextureLayer(P.READ_FRAMEBUFFER,P.COLOR_ATTACHMENT0,j.get(R).__webglTexture,H,Be+ji),P.framebufferTextureLayer(P.DRAW_FRAMEBUFFER,P.COLOR_ATTACHMENT0,j.get(z).__webglTexture,le,It+ji)),P.blitFramebuffer(He,Ge,ye,Re,Qe,mt,ye,Re,P.DEPTH_BUFFER_BIT,P.NEAREST);W.bindFramebuffer(P.READ_FRAMEBUFFER,null),W.bindFramebuffer(P.DRAW_FRAMEBUFFER,null)}else if(H!==0||R.isRenderTargetTexture||j.has(R)){let Pn=j.get(R),an=j.get(z);W.bindFramebuffer(P.READ_FRAMEBUFFER,Nm),W.bindFramebuffer(P.DRAW_FRAMEBUFFER,Fm);for(let dn=0;dn<we;dn++)Rt?P.framebufferTextureLayer(P.READ_FRAMEBUFFER,P.COLOR_ATTACHMENT0,Pn.__webglTexture,H,Be+dn):P.framebufferTexture2D(P.READ_FRAMEBUFFER,P.COLOR_ATTACHMENT0,P.TEXTURE_2D,Pn.__webglTexture,H),In?P.framebufferTextureLayer(P.DRAW_FRAMEBUFFER,P.COLOR_ATTACHMENT0,an.__webglTexture,le,It+dn):P.framebufferTexture2D(P.DRAW_FRAMEBUFFER,P.COLOR_ATTACHMENT0,P.TEXTURE_2D,an.__webglTexture,le),H!==0?P.blitFramebuffer(He,Ge,ye,Re,Qe,mt,ye,Re,P.COLOR_BUFFER_BIT,P.NEAREST):In?P.copyTexSubImage3D(At,le,Qe,mt,It+dn,He,Ge,ye,Re):P.copyTexSubImage2D(At,le,Qe,mt,He,Ge,ye,Re);W.bindFramebuffer(P.READ_FRAMEBUFFER,null),W.bindFramebuffer(P.DRAW_FRAMEBUFFER,null)}else In?R.isDataTexture||R.isData3DTexture?P.texSubImage3D(At,le,Qe,mt,It,ye,Re,we,bt,Oe,St.data):z.isCompressedArrayTexture?P.compressedTexSubImage3D(At,le,Qe,mt,It,ye,Re,we,bt,St.data):P.texSubImage3D(At,le,Qe,mt,It,ye,Re,we,bt,Oe,St):R.isDataTexture?P.texSubImage2D(P.TEXTURE_2D,le,Qe,mt,ye,Re,bt,Oe,St.data):R.isCompressedTexture?P.compressedTexSubImage2D(P.TEXTURE_2D,le,Qe,mt,St.width,St.height,bt,St.data):P.texSubImage2D(P.TEXTURE_2D,le,Qe,mt,ye,Re,bt,Oe,St);P.pixelStorei(P.UNPACK_ROW_LENGTH,rt),P.pixelStorei(P.UNPACK_IMAGE_HEIGHT,vn),P.pixelStorei(P.UNPACK_SKIP_PIXELS,Is),P.pixelStorei(P.UNPACK_SKIP_ROWS,_n),P.pixelStorei(P.UNPACK_SKIP_IMAGES,Br),le===0&&z.generateMipmaps&&P.generateMipmap(At),W.unbindTexture()},this.initRenderTarget=function(R){j.get(R).__webglFramebuffer===void 0&&re.setupRenderTarget(R)},this.initTexture=function(R){R.isCubeTexture?re.setTextureCube(R,0):R.isData3DTexture?re.setTexture3D(R,0):R.isDataArrayTexture||R.isCompressedArrayTexture?re.setTexture2DArray(R,0):re.setTexture2D(R,0),W.unbindTexture()},this.resetState=function(){w=0,T=0,A=null,W.reset(),pe.reset()},typeof __THREE_DEVTOOLS__<"u"&&__THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("observe",{detail:this}))}get coordinateSystem(){return Wn}get outputColorSpace(){return this._outputColorSpace}set outputColorSpace(e){this._outputColorSpace=e;let t=this.getContext();t.drawingBufferColorSpace=et._getDrawingBufferColorSpace(e),t.unpackColorSpace=et._getUnpackColorSpace()}};function Wh(s,e){if(e===vh)return console.warn("THREE.BufferGeometryUtils.toTrianglesDrawMode(): Geometry already defined as triangles."),s;if(e===mr||e===Ca){let t=s.getIndex();if(t===null){let a=[],o=s.getAttribute("position");if(o!==void 0){for(let c=0;c<o.count;c++)a.push(c);s.setIndex(a),t=s.getIndex()}else return console.error("THREE.BufferGeometryUtils.toTrianglesDrawMode(): Undefined position attribute. Processing not possible."),s}let n=t.count-2,i=[];if(e===mr)for(let a=1;a<=n;a++)i.push(t.getX(0)),i.push(t.getX(a)),i.push(t.getX(a+1));else for(let a=0;a<n;a++)a%2===0?(i.push(t.getX(a)),i.push(t.getX(a+1)),i.push(t.getX(a+2))):(i.push(t.getX(a+2)),i.push(t.getX(a+1)),i.push(t.getX(a)));i.length/3!==n&&console.error("THREE.BufferGeometryUtils.toTrianglesDrawMode(): Unable to generate correct amount of triangles.");let r=s.clone();return r.setIndex(i),r.clearGroups(),r}else return console.error("THREE.BufferGeometryUtils.toTrianglesDrawMode(): Unknown draw mode:",e),s}var Gc=class extends si{constructor(e){super(e),this.dracoLoader=null,this.ktx2Loader=null,this.meshoptDecoder=null,this.pluginCallbacks=[],this.register(function(t){return new Jh(t)}),this.register(function(t){return new $h(t)}),this.register(function(t){return new ou(t)}),this.register(function(t){return new cu(t)}),this.register(function(t){return new lu(t)}),this.register(function(t){return new eu(t)}),this.register(function(t){return new tu(t)}),this.register(function(t){return new nu(t)}),this.register(function(t){return new iu(t)}),this.register(function(t){return new Zh(t)}),this.register(function(t){return new su(t)}),this.register(function(t){return new Qh(t)}),this.register(function(t){return new au(t)}),this.register(function(t){return new ru(t)}),this.register(function(t){return new jh(t)}),this.register(function(t){return new hu(t)}),this.register(function(t){return new uu(t)})}load(e,t,n,i){let r=this,a;if(this.resourcePath!=="")a=this.resourcePath;else if(this.path!==""){let l=Si.extractUrlBase(e);a=Si.resolveURL(l,this.path)}else a=Si.extractUrlBase(e);this.manager.itemStart(e);let o=function(l){i?i(l):console.error(l),r.manager.itemError(e),r.manager.itemEnd(e)},c=new cr(this.manager);c.setPath(this.path),c.setResponseType("arraybuffer"),c.setRequestHeader(this.requestHeader),c.setWithCredentials(this.withCredentials),c.load(e,function(l){try{r.parse(l,a,function(u){t(u),r.manager.itemEnd(e)},o)}catch(u){o(u)}},n,o)}setDRACOLoader(e){return this.dracoLoader=e,this}setKTX2Loader(e){return this.ktx2Loader=e,this}setMeshoptDecoder(e){return this.meshoptDecoder=e,this}register(e){return this.pluginCallbacks.indexOf(e)===-1&&this.pluginCallbacks.push(e),this}unregister(e){return this.pluginCallbacks.indexOf(e)!==-1&&this.pluginCallbacks.splice(this.pluginCallbacks.indexOf(e),1),this}parse(e,t,n,i){let r,a={},o={},c=new TextDecoder;if(typeof e=="string")r=JSON.parse(e);else if(e instanceof ArrayBuffer)if(c.decode(new Uint8Array(e,0,4))===gp){try{a[Ze.KHR_BINARY_GLTF]=new du(e)}catch(h){i&&i(h);return}r=JSON.parse(a[Ze.KHR_BINARY_GLTF].content)}else r=JSON.parse(c.decode(e));else r=e;if(r.asset===void 0||r.asset.version[0]<2){i&&i(new Error("THREE.GLTFLoader: Unsupported asset. glTF versions >=2.0 are supported."));return}let l=new xu(r,{path:t||this.resourcePath||"",crossOrigin:this.crossOrigin,requestHeader:this.requestHeader,manager:this.manager,ktx2Loader:this.ktx2Loader,meshoptDecoder:this.meshoptDecoder});l.fileLoader.setRequestHeader(this.requestHeader);for(let u=0;u<this.pluginCallbacks.length;u++){let h=this.pluginCallbacks[u](l);h.name||console.error("THREE.GLTFLoader: Invalid plugin found: missing name"),o[h.name]=h,a[h.name]=!0}if(r.extensionsUsed)for(let u=0;u<r.extensionsUsed.length;++u){let h=r.extensionsUsed[u],d=r.extensionsRequired||[];switch(h){case Ze.KHR_MATERIALS_UNLIT:a[h]=new Kh;break;case Ze.KHR_DRACO_MESH_COMPRESSION:a[h]=new fu(r,this.dracoLoader);break;case Ze.KHR_TEXTURE_TRANSFORM:a[h]=new pu;break;case Ze.KHR_MESH_QUANTIZATION:a[h]=new mu;break;default:d.indexOf(h)>=0&&o[h]===void 0&&console.warn('THREE.GLTFLoader: Unknown extension "'+h+'".')}}l.setExtensions(a),l.setPlugins(o),l.parse(n,i)}parseAsync(e,t){let n=this;return new Promise(function(i,r){n.parse(e,t,i,r)})}};function mv(){let s={};return{get:function(e){return s[e]},add:function(e,t){s[e]=t},remove:function(e){delete s[e]},removeAll:function(){s={}}}}var Ze={KHR_BINARY_GLTF:"KHR_binary_glTF",KHR_DRACO_MESH_COMPRESSION:"KHR_draco_mesh_compression",KHR_LIGHTS_PUNCTUAL:"KHR_lights_punctual",KHR_MATERIALS_CLEARCOAT:"KHR_materials_clearcoat",KHR_MATERIALS_DISPERSION:"KHR_materials_dispersion",KHR_MATERIALS_IOR:"KHR_materials_ior",KHR_MATERIALS_SHEEN:"KHR_materials_sheen",KHR_MATERIALS_SPECULAR:"KHR_materials_specular",KHR_MATERIALS_TRANSMISSION:"KHR_materials_transmission",KHR_MATERIALS_IRIDESCENCE:"KHR_materials_iridescence",KHR_MATERIALS_ANISOTROPY:"KHR_materials_anisotropy",KHR_MATERIALS_UNLIT:"KHR_materials_unlit",KHR_MATERIALS_VOLUME:"KHR_materials_volume",KHR_TEXTURE_BASISU:"KHR_texture_basisu",KHR_TEXTURE_TRANSFORM:"KHR_texture_transform",KHR_MESH_QUANTIZATION:"KHR_mesh_quantization",KHR_MATERIALS_EMISSIVE_STRENGTH:"KHR_materials_emissive_strength",EXT_MATERIALS_BUMP:"EXT_materials_bump",EXT_TEXTURE_WEBP:"EXT_texture_webp",EXT_TEXTURE_AVIF:"EXT_texture_avif",EXT_MESHOPT_COMPRESSION:"EXT_meshopt_compression",EXT_MESH_GPU_INSTANCING:"EXT_mesh_gpu_instancing"},jh=class{constructor(e){this.parser=e,this.name=Ze.KHR_LIGHTS_PUNCTUAL,this.cache={refs:{},uses:{}}}_markDefs(){let e=this.parser,t=this.parser.json.nodes||[];for(let n=0,i=t.length;n<i;n++){let r=t[n];r.extensions&&r.extensions[this.name]&&r.extensions[this.name].light!==void 0&&e._addNodeRef(this.cache,r.extensions[this.name].light)}}_loadLight(e){let t=this.parser,n="light:"+e,i=t.cache.get(n);if(i)return i;let r=t.json,c=((r.extensions&&r.extensions[this.name]||{}).lights||[])[e],l,u=new Ue(16777215);c.color!==void 0&&u.setRGB(c.color[0],c.color[1],c.color[2],Kt);let h=c.range!==void 0?c.range:0;switch(c.type){case"directional":l=new us(u),l.target.position.set(0,0,-1),l.add(l.target);break;case"point":l=new Mi(u),l.distance=h;break;case"spot":l=new xa(u),l.distance=h,c.spot=c.spot||{},c.spot.innerConeAngle=c.spot.innerConeAngle!==void 0?c.spot.innerConeAngle:0,c.spot.outerConeAngle=c.spot.outerConeAngle!==void 0?c.spot.outerConeAngle:Math.PI/4,l.angle=c.spot.outerConeAngle,l.penumbra=1-c.spot.innerConeAngle/c.spot.outerConeAngle,l.target.position.set(0,0,-1),l.add(l.target);break;default:throw new Error("THREE.GLTFLoader: Unexpected light type: "+c.type)}return l.position.set(0,0,0),oi(l,c),c.intensity!==void 0&&(l.intensity=c.intensity),l.name=t.createUniqueName(c.name||"light_"+e),i=Promise.resolve(l),t.cache.add(n,i),i}getDependency(e,t){if(e==="light")return this._loadLight(t)}createNodeAttachment(e){let t=this,n=this.parser,r=n.json.nodes[e],o=(r.extensions&&r.extensions[this.name]||{}).light;return o===void 0?null:this._loadLight(o).then(function(c){return n._getNodeRef(t.cache,o,c)})}},Kh=class{constructor(){this.name=Ze.KHR_MATERIALS_UNLIT}getMaterialType(){return nn}extendParams(e,t,n){let i=[];e.color=new Ue(1,1,1),e.opacity=1;let r=t.pbrMetallicRoughness;if(r){if(Array.isArray(r.baseColorFactor)){let a=r.baseColorFactor;e.color.setRGB(a[0],a[1],a[2],Kt),e.opacity=a[3]}r.baseColorTexture!==void 0&&i.push(n.assignTexture(e,"map",r.baseColorTexture,kt))}return Promise.all(i)}},Zh=class{constructor(e){this.parser=e,this.name=Ze.KHR_MATERIALS_EMISSIVE_STRENGTH}extendMaterialParams(e,t){let i=this.parser.json.materials[e];if(!i.extensions||!i.extensions[this.name])return Promise.resolve();let r=i.extensions[this.name].emissiveStrength;return r!==void 0&&(t.emissiveIntensity=r),Promise.resolve()}},Jh=class{constructor(e){this.parser=e,this.name=Ze.KHR_MATERIALS_CLEARCOAT}getMaterialType(e){let n=this.parser.json.materials[e];return!n.extensions||!n.extensions[this.name]?null:mn}extendMaterialParams(e,t){let n=this.parser,i=n.json.materials[e];if(!i.extensions||!i.extensions[this.name])return Promise.resolve();let r=[],a=i.extensions[this.name];if(a.clearcoatFactor!==void 0&&(t.clearcoat=a.clearcoatFactor),a.clearcoatTexture!==void 0&&r.push(n.assignTexture(t,"clearcoatMap",a.clearcoatTexture)),a.clearcoatRoughnessFactor!==void 0&&(t.clearcoatRoughness=a.clearcoatRoughnessFactor),a.clearcoatRoughnessTexture!==void 0&&r.push(n.assignTexture(t,"clearcoatRoughnessMap",a.clearcoatRoughnessTexture)),a.clearcoatNormalTexture!==void 0&&(r.push(n.assignTexture(t,"clearcoatNormalMap",a.clearcoatNormalTexture)),a.clearcoatNormalTexture.scale!==void 0)){let o=a.clearcoatNormalTexture.scale;t.clearcoatNormalScale=new Ne(o,o)}return Promise.all(r)}},$h=class{constructor(e){this.parser=e,this.name=Ze.KHR_MATERIALS_DISPERSION}getMaterialType(e){let n=this.parser.json.materials[e];return!n.extensions||!n.extensions[this.name]?null:mn}extendMaterialParams(e,t){let i=this.parser.json.materials[e];if(!i.extensions||!i.extensions[this.name])return Promise.resolve();let r=i.extensions[this.name];return t.dispersion=r.dispersion!==void 0?r.dispersion:0,Promise.resolve()}},Qh=class{constructor(e){this.parser=e,this.name=Ze.KHR_MATERIALS_IRIDESCENCE}getMaterialType(e){let n=this.parser.json.materials[e];return!n.extensions||!n.extensions[this.name]?null:mn}extendMaterialParams(e,t){let n=this.parser,i=n.json.materials[e];if(!i.extensions||!i.extensions[this.name])return Promise.resolve();let r=[],a=i.extensions[this.name];return a.iridescenceFactor!==void 0&&(t.iridescence=a.iridescenceFactor),a.iridescenceTexture!==void 0&&r.push(n.assignTexture(t,"iridescenceMap",a.iridescenceTexture)),a.iridescenceIor!==void 0&&(t.iridescenceIOR=a.iridescenceIor),t.iridescenceThicknessRange===void 0&&(t.iridescenceThicknessRange=[100,400]),a.iridescenceThicknessMinimum!==void 0&&(t.iridescenceThicknessRange[0]=a.iridescenceThicknessMinimum),a.iridescenceThicknessMaximum!==void 0&&(t.iridescenceThicknessRange[1]=a.iridescenceThicknessMaximum),a.iridescenceThicknessTexture!==void 0&&r.push(n.assignTexture(t,"iridescenceThicknessMap",a.iridescenceThicknessTexture)),Promise.all(r)}},eu=class{constructor(e){this.parser=e,this.name=Ze.KHR_MATERIALS_SHEEN}getMaterialType(e){let n=this.parser.json.materials[e];return!n.extensions||!n.extensions[this.name]?null:mn}extendMaterialParams(e,t){let n=this.parser,i=n.json.materials[e];if(!i.extensions||!i.extensions[this.name])return Promise.resolve();let r=[];t.sheenColor=new Ue(0,0,0),t.sheenRoughness=0,t.sheen=1;let a=i.extensions[this.name];if(a.sheenColorFactor!==void 0){let o=a.sheenColorFactor;t.sheenColor.setRGB(o[0],o[1],o[2],Kt)}return a.sheenRoughnessFactor!==void 0&&(t.sheenRoughness=a.sheenRoughnessFactor),a.sheenColorTexture!==void 0&&r.push(n.assignTexture(t,"sheenColorMap",a.sheenColorTexture,kt)),a.sheenRoughnessTexture!==void 0&&r.push(n.assignTexture(t,"sheenRoughnessMap",a.sheenRoughnessTexture)),Promise.all(r)}},tu=class{constructor(e){this.parser=e,this.name=Ze.KHR_MATERIALS_TRANSMISSION}getMaterialType(e){let n=this.parser.json.materials[e];return!n.extensions||!n.extensions[this.name]?null:mn}extendMaterialParams(e,t){let n=this.parser,i=n.json.materials[e];if(!i.extensions||!i.extensions[this.name])return Promise.resolve();let r=[],a=i.extensions[this.name];return a.transmissionFactor!==void 0&&(t.transmission=a.transmissionFactor),a.transmissionTexture!==void 0&&r.push(n.assignTexture(t,"transmissionMap",a.transmissionTexture)),Promise.all(r)}},nu=class{constructor(e){this.parser=e,this.name=Ze.KHR_MATERIALS_VOLUME}getMaterialType(e){let n=this.parser.json.materials[e];return!n.extensions||!n.extensions[this.name]?null:mn}extendMaterialParams(e,t){let n=this.parser,i=n.json.materials[e];if(!i.extensions||!i.extensions[this.name])return Promise.resolve();let r=[],a=i.extensions[this.name];t.thickness=a.thicknessFactor!==void 0?a.thicknessFactor:0,a.thicknessTexture!==void 0&&r.push(n.assignTexture(t,"thicknessMap",a.thicknessTexture)),t.attenuationDistance=a.attenuationDistance||1/0;let o=a.attenuationColor||[1,1,1];return t.attenuationColor=new Ue().setRGB(o[0],o[1],o[2],Kt),Promise.all(r)}},iu=class{constructor(e){this.parser=e,this.name=Ze.KHR_MATERIALS_IOR}getMaterialType(e){let n=this.parser.json.materials[e];return!n.extensions||!n.extensions[this.name]?null:mn}extendMaterialParams(e,t){let i=this.parser.json.materials[e];if(!i.extensions||!i.extensions[this.name])return Promise.resolve();let r=i.extensions[this.name];return t.ior=r.ior!==void 0?r.ior:1.5,Promise.resolve()}},su=class{constructor(e){this.parser=e,this.name=Ze.KHR_MATERIALS_SPECULAR}getMaterialType(e){let n=this.parser.json.materials[e];return!n.extensions||!n.extensions[this.name]?null:mn}extendMaterialParams(e,t){let n=this.parser,i=n.json.materials[e];if(!i.extensions||!i.extensions[this.name])return Promise.resolve();let r=[],a=i.extensions[this.name];t.specularIntensity=a.specularFactor!==void 0?a.specularFactor:1,a.specularTexture!==void 0&&r.push(n.assignTexture(t,"specularIntensityMap",a.specularTexture));let o=a.specularColorFactor||[1,1,1];return t.specularColor=new Ue().setRGB(o[0],o[1],o[2],Kt),a.specularColorTexture!==void 0&&r.push(n.assignTexture(t,"specularColorMap",a.specularColorTexture,kt)),Promise.all(r)}},ru=class{constructor(e){this.parser=e,this.name=Ze.EXT_MATERIALS_BUMP}getMaterialType(e){let n=this.parser.json.materials[e];return!n.extensions||!n.extensions[this.name]?null:mn}extendMaterialParams(e,t){let n=this.parser,i=n.json.materials[e];if(!i.extensions||!i.extensions[this.name])return Promise.resolve();let r=[],a=i.extensions[this.name];return t.bumpScale=a.bumpFactor!==void 0?a.bumpFactor:1,a.bumpTexture!==void 0&&r.push(n.assignTexture(t,"bumpMap",a.bumpTexture)),Promise.all(r)}},au=class{constructor(e){this.parser=e,this.name=Ze.KHR_MATERIALS_ANISOTROPY}getMaterialType(e){let n=this.parser.json.materials[e];return!n.extensions||!n.extensions[this.name]?null:mn}extendMaterialParams(e,t){let n=this.parser,i=n.json.materials[e];if(!i.extensions||!i.extensions[this.name])return Promise.resolve();let r=[],a=i.extensions[this.name];return a.anisotropyStrength!==void 0&&(t.anisotropy=a.anisotropyStrength),a.anisotropyRotation!==void 0&&(t.anisotropyRotation=a.anisotropyRotation),a.anisotropyTexture!==void 0&&r.push(n.assignTexture(t,"anisotropyMap",a.anisotropyTexture)),Promise.all(r)}},ou=class{constructor(e){this.parser=e,this.name=Ze.KHR_TEXTURE_BASISU}loadTexture(e){let t=this.parser,n=t.json,i=n.textures[e];if(!i.extensions||!i.extensions[this.name])return null;let r=i.extensions[this.name],a=t.options.ktx2Loader;if(!a){if(n.extensionsRequired&&n.extensionsRequired.indexOf(this.name)>=0)throw new Error("THREE.GLTFLoader: setKTX2Loader must be called before loading KTX2 textures");return null}return t.loadTextureImage(e,r.source,a)}},cu=class{constructor(e){this.parser=e,this.name=Ze.EXT_TEXTURE_WEBP}loadTexture(e){let t=this.name,n=this.parser,i=n.json,r=i.textures[e];if(!r.extensions||!r.extensions[t])return null;let a=r.extensions[t],o=i.images[a.source],c=n.textureLoader;if(o.uri){let l=n.options.manager.getHandler(o.uri);l!==null&&(c=l)}return n.loadTextureImage(e,a.source,c)}},lu=class{constructor(e){this.parser=e,this.name=Ze.EXT_TEXTURE_AVIF}loadTexture(e){let t=this.name,n=this.parser,i=n.json,r=i.textures[e];if(!r.extensions||!r.extensions[t])return null;let a=r.extensions[t],o=i.images[a.source],c=n.textureLoader;if(o.uri){let l=n.options.manager.getHandler(o.uri);l!==null&&(c=l)}return n.loadTextureImage(e,a.source,c)}},hu=class{constructor(e){this.name=Ze.EXT_MESHOPT_COMPRESSION,this.parser=e}loadBufferView(e){let t=this.parser.json,n=t.bufferViews[e];if(n.extensions&&n.extensions[this.name]){let i=n.extensions[this.name],r=this.parser.getDependency("buffer",i.buffer),a=this.parser.options.meshoptDecoder;if(!a||!a.supported){if(t.extensionsRequired&&t.extensionsRequired.indexOf(this.name)>=0)throw new Error("THREE.GLTFLoader: setMeshoptDecoder must be called before loading compressed files");return null}return r.then(function(o){let c=i.byteOffset||0,l=i.byteLength||0,u=i.count,h=i.byteStride,d=new Uint8Array(o,c,l);return a.decodeGltfBufferAsync?a.decodeGltfBufferAsync(u,h,d,i.mode,i.filter).then(function(f){return f.buffer}):a.ready.then(function(){let f=new ArrayBuffer(u*h);return a.decodeGltfBuffer(new Uint8Array(f),u,h,d,i.mode,i.filter),f})})}else return null}},uu=class{constructor(e){this.name=Ze.EXT_MESH_GPU_INSTANCING,this.parser=e}createNodeMesh(e){let t=this.parser.json,n=t.nodes[e];if(!n.extensions||!n.extensions[this.name]||n.mesh===void 0)return null;let i=t.meshes[n.mesh];for(let l of i.primitives)if(l.mode!==Un.TRIANGLES&&l.mode!==Un.TRIANGLE_STRIP&&l.mode!==Un.TRIANGLE_FAN&&l.mode!==void 0)return null;let a=n.extensions[this.name].attributes,o=[],c={};for(let l in a)o.push(this.parser.getDependency("accessor",a[l]).then(u=>(c[l]=u,c[l])));return o.length<1?null:(o.push(this.parser.createNodeMesh(e)),Promise.all(o).then(l=>{let u=l.pop(),h=u.isGroup?u.children:[u],d=l[0].count,f=[];for(let g of h){let y=new ke,m=new L,p=new Ln,x=new L(1,1,1),v=new aa(g.geometry,g.material,d);for(let b=0;b<d;b++)c.TRANSLATION&&m.fromBufferAttribute(c.TRANSLATION,b),c.ROTATION&&p.fromBufferAttribute(c.ROTATION,b),c.SCALE&&x.fromBufferAttribute(c.SCALE,b),v.setMatrixAt(b,y.compose(m,p,x));for(let b in c)if(b==="_COLOR_0"){let S=c[b];v.instanceColor=new Nn(S.array,S.itemSize,S.normalized)}else b!=="TRANSLATION"&&b!=="ROTATION"&&b!=="SCALE"&&g.geometry.setAttribute(b,c[b]);Et.prototype.copy.call(v,g),this.parser.assignFinalMaterial(v),f.push(v)}return u.isGroup?(u.clear(),u.add(...f),u):f[0]}))}},gp="glTF",ka=12,dp={JSON:1313821514,BIN:5130562},du=class{constructor(e){this.name=Ze.KHR_BINARY_GLTF,this.content=null,this.body=null;let t=new DataView(e,0,ka),n=new TextDecoder;if(this.header={magic:n.decode(new Uint8Array(e.slice(0,4))),version:t.getUint32(4,!0),length:t.getUint32(8,!0)},this.header.magic!==gp)throw new Error("THREE.GLTFLoader: Unsupported glTF-Binary header.");if(this.header.version<2)throw new Error("THREE.GLTFLoader: Legacy binary file detected.");let i=this.header.length-ka,r=new DataView(e,ka),a=0;for(;a<i;){let o=r.getUint32(a,!0);a+=4;let c=r.getUint32(a,!0);if(a+=4,c===dp.JSON){let l=new Uint8Array(e,ka+a,o);this.content=n.decode(l)}else if(c===dp.BIN){let l=ka+a;this.body=e.slice(l,l+o)}a+=o}if(this.content===null)throw new Error("THREE.GLTFLoader: JSON content not found.")}},fu=class{constructor(e,t){if(!t)throw new Error("THREE.GLTFLoader: No DRACOLoader instance provided.");this.name=Ze.KHR_DRACO_MESH_COMPRESSION,this.json=e,this.dracoLoader=t,this.dracoLoader.preload()}decodePrimitive(e,t){let n=this.json,i=this.dracoLoader,r=e.extensions[this.name].bufferView,a=e.extensions[this.name].attributes,o={},c={},l={};for(let u in a){let h=bu[u]||u.toLowerCase();o[h]=a[u]}for(let u in e.attributes){let h=bu[u]||u.toLowerCase();if(a[u]!==void 0){let d=n.accessors[e.attributes[u]],f=_r[d.componentType];l[h]=f.name,c[h]=d.normalized===!0}}return t.getDependency("bufferView",r).then(function(u){return new Promise(function(h,d){i.decodeDracoFile(u,function(f){for(let g in f.attributes){let y=f.attributes[g],m=c[g];m!==void 0&&(y.normalized=m)}h(f)},o,l,Kt,d)})})}},pu=class{constructor(){this.name=Ze.KHR_TEXTURE_TRANSFORM}extendTexture(e,t){return(t.texCoord===void 0||t.texCoord===e.channel)&&t.offset===void 0&&t.rotation===void 0&&t.scale===void 0||(e=e.clone(),t.texCoord!==void 0&&(e.channel=t.texCoord),t.offset!==void 0&&e.offset.fromArray(t.offset),t.rotation!==void 0&&(e.rotation=t.rotation),t.scale!==void 0&&e.repeat.fromArray(t.scale),e.needsUpdate=!0),e}},mu=class{constructor(){this.name=Ze.KHR_MESH_QUANTIZATION}},Wc=class extends vi{constructor(e,t,n,i){super(e,t,n,i)}copySampleValue_(e){let t=this.resultBuffer,n=this.sampleValues,i=this.valueSize,r=e*i*3+i;for(let a=0;a!==i;a++)t[a]=n[r+a];return t}interpolate_(e,t,n,i){let r=this.resultBuffer,a=this.sampleValues,o=this.valueSize,c=o*2,l=o*3,u=i-t,h=(n-t)/u,d=h*h,f=d*h,g=e*l,y=g-l,m=-2*f+3*d,p=f-d,x=1-m,v=p-d+h;for(let b=0;b!==o;b++){let S=a[y+b+o],w=a[y+b+c]*u,T=a[g+b+o],A=a[g+b]*u;r[b]=x*S+v*w+m*T+p*A}return r}},gv=new Ln,gu=class extends Wc{interpolate_(e,t,n,i){let r=super.interpolate_(e,t,n,i);return gv.fromArray(r).normalize().toArray(r),r}},Un={FLOAT:5126,FLOAT_MAT3:35675,FLOAT_MAT4:35676,FLOAT_VEC2:35664,FLOAT_VEC3:35665,FLOAT_VEC4:35666,LINEAR:9729,REPEAT:10497,SAMPLER_2D:35678,POINTS:0,LINES:1,LINE_LOOP:2,LINE_STRIP:3,TRIANGLES:4,TRIANGLE_STRIP:5,TRIANGLE_FAN:6,UNSIGNED_BYTE:5121,UNSIGNED_SHORT:5123},_r={5120:Int8Array,5121:Uint8Array,5122:Int16Array,5123:Uint16Array,5125:Uint32Array,5126:Float32Array},fp={9728:qt,9729:jt,9984:ec,9985:hr,9986:ms,9987:qn},pp={33071:$n,33648:js,10497:Ui},Yh={SCALAR:1,VEC2:2,VEC3:3,VEC4:4,MAT2:4,MAT3:9,MAT4:16},bu={POSITION:"position",NORMAL:"normal",TANGENT:"tangent",TEXCOORD_0:"uv",TEXCOORD_1:"uv1",TEXCOORD_2:"uv2",TEXCOORD_3:"uv3",COLOR_0:"color",WEIGHTS_0:"skinWeight",JOINTS_0:"skinIndex"},Hi={scale:"scale",translation:"position",rotation:"quaternion",weights:"morphTargetInfluences"},bv={CUBICSPLINE:void 0,LINEAR:is,STEP:ns},Xh={OPAQUE:"OPAQUE",MASK:"MASK",BLEND:"BLEND"};function yv(s){return s.DefaultMaterial===void 0&&(s.DefaultMaterial=new Lt({color:16777215,emissive:0,metalness:1,roughness:1,transparent:!1,depthTest:!0,side:pn})),s.DefaultMaterial}function _s(s,e,t){for(let n in t.extensions)s[n]===void 0&&(e.userData.gltfExtensions=e.userData.gltfExtensions||{},e.userData.gltfExtensions[n]=t.extensions[n])}function oi(s,e){e.extras!==void 0&&(typeof e.extras=="object"?Object.assign(s.userData,e.extras):console.warn("THREE.GLTFLoader: Ignoring primitive type .extras, "+e.extras))}function xv(s,e,t){let n=!1,i=!1,r=!1;for(let l=0,u=e.length;l<u;l++){let h=e[l];if(h.POSITION!==void 0&&(n=!0),h.NORMAL!==void 0&&(i=!0),h.COLOR_0!==void 0&&(r=!0),n&&i&&r)break}if(!n&&!i&&!r)return Promise.resolve(s);let a=[],o=[],c=[];for(let l=0,u=e.length;l<u;l++){let h=e[l];if(n){let d=h.POSITION!==void 0?t.getDependency("accessor",h.POSITION):s.attributes.position;a.push(d)}if(i){let d=h.NORMAL!==void 0?t.getDependency("accessor",h.NORMAL):s.attributes.normal;o.push(d)}if(r){let d=h.COLOR_0!==void 0?t.getDependency("accessor",h.COLOR_0):s.attributes.color;c.push(d)}}return Promise.all([Promise.all(a),Promise.all(o),Promise.all(c)]).then(function(l){let u=l[0],h=l[1],d=l[2];return n&&(s.morphAttributes.position=u),i&&(s.morphAttributes.normal=h),r&&(s.morphAttributes.color=d),s.morphTargetsRelative=!0,s})}function vv(s,e){if(s.updateMorphTargets(),e.weights!==void 0)for(let t=0,n=e.weights.length;t<n;t++)s.morphTargetInfluences[t]=e.weights[t];if(e.extras&&Array.isArray(e.extras.targetNames)){let t=e.extras.targetNames;if(s.morphTargetInfluences.length===t.length){s.morphTargetDictionary={};for(let n=0,i=t.length;n<i;n++)s.morphTargetDictionary[t[n]]=n}else console.warn("THREE.GLTFLoader: Invalid extras.targetNames length. Ignoring names.")}}function _v(s){let e,t=s.extensions&&s.extensions[Ze.KHR_DRACO_MESH_COMPRESSION];if(t?e="draco:"+t.bufferView+":"+t.indices+":"+qh(t.attributes):e=s.indices+":"+qh(s.attributes)+":"+s.mode,s.targets!==void 0)for(let n=0,i=s.targets.length;n<i;n++)e+=":"+qh(s.targets[n]);return e}function qh(s){let e="",t=Object.keys(s).sort();for(let n=0,i=t.length;n<i;n++)e+=t[n]+":"+s[t[n]]+";";return e}function yu(s){switch(s){case Int8Array:return 1/127;case Uint8Array:return 1/255;case Int16Array:return 1/32767;case Uint16Array:return 1/65535;default:throw new Error("THREE.GLTFLoader: Unsupported normalized accessor component type.")}}function wv(s){return s.search(/\.jpe?g($|\?)/i)>0||s.search(/^data\:image\/jpeg/)===0?"image/jpeg":s.search(/\.webp($|\?)/i)>0||s.search(/^data\:image\/webp/)===0?"image/webp":s.search(/\.ktx2($|\?)/i)>0||s.search(/^data\:image\/ktx2/)===0?"image/ktx2":"image/png"}var Mv=new ke,xu=class{constructor(e={},t={}){this.json=e,this.extensions={},this.plugins={},this.options=t,this.cache=new mv,this.associations=new Map,this.primitiveCache={},this.nodeCache={},this.meshCache={refs:{},uses:{}},this.cameraCache={refs:{},uses:{}},this.lightCache={refs:{},uses:{}},this.sourceCache={},this.textureCache={},this.nodeNamesUsed={};let n=!1,i=-1,r=!1,a=-1;if(typeof navigator<"u"){let o=navigator.userAgent;n=/^((?!chrome|android).)*safari/i.test(o)===!0;let c=o.match(/Version\/(\d+)/);i=n&&c?parseInt(c[1],10):-1,r=o.indexOf("Firefox")>-1,a=r?o.match(/Firefox\/([0-9]+)\./)[1]:-1}typeof createImageBitmap>"u"||n&&i<17||r&&a<98?this.textureLoader=new cs(this.options.manager):this.textureLoader=new va(this.options.manager),this.textureLoader.setCrossOrigin(this.options.crossOrigin),this.textureLoader.setRequestHeader(this.options.requestHeader),this.fileLoader=new cr(this.options.manager),this.fileLoader.setResponseType("arraybuffer"),this.options.crossOrigin==="use-credentials"&&this.fileLoader.setWithCredentials(!0)}setExtensions(e){this.extensions=e}setPlugins(e){this.plugins=e}parse(e,t){let n=this,i=this.json,r=this.extensions;this.cache.removeAll(),this.nodeCache={},this._invokeAll(function(a){return a._markDefs&&a._markDefs()}),Promise.all(this._invokeAll(function(a){return a.beforeRoot&&a.beforeRoot()})).then(function(){return Promise.all([n.getDependencies("scene"),n.getDependencies("animation"),n.getDependencies("camera")])}).then(function(a){let o={scene:a[0][i.scene||0],scenes:a[0],animations:a[1],cameras:a[2],asset:i.asset,parser:n,userData:{}};return _s(r,o,i),oi(o,i),Promise.all(n._invokeAll(function(c){return c.afterRoot&&c.afterRoot(o)})).then(function(){for(let c of o.scenes)c.updateMatrixWorld();e(o)})}).catch(t)}_markDefs(){let e=this.json.nodes||[],t=this.json.skins||[],n=this.json.meshes||[];for(let i=0,r=t.length;i<r;i++){let a=t[i].joints;for(let o=0,c=a.length;o<c;o++)e[a[o]].isBone=!0}for(let i=0,r=e.length;i<r;i++){let a=e[i];a.mesh!==void 0&&(this._addNodeRef(this.meshCache,a.mesh),a.skin!==void 0&&(n[a.mesh].isSkinnedMesh=!0)),a.camera!==void 0&&this._addNodeRef(this.cameraCache,a.camera)}}_addNodeRef(e,t){t!==void 0&&(e.refs[t]===void 0&&(e.refs[t]=e.uses[t]=0),e.refs[t]++)}_getNodeRef(e,t,n){if(e.refs[t]<=1)return n;let i=n.clone(),r=(a,o)=>{let c=this.associations.get(a);c!=null&&this.associations.set(o,c);for(let[l,u]of a.children.entries())r(u,o.children[l])};return r(n,i),i.name+="_instance_"+e.uses[t]++,i}_invokeOne(e){let t=Object.values(this.plugins);t.push(this);for(let n=0;n<t.length;n++){let i=e(t[n]);if(i)return i}return null}_invokeAll(e){let t=Object.values(this.plugins);t.unshift(this);let n=[];for(let i=0;i<t.length;i++){let r=e(t[i]);r&&n.push(r)}return n}getDependency(e,t){let n=e+":"+t,i=this.cache.get(n);if(!i){switch(e){case"scene":i=this.loadScene(t);break;case"node":i=this._invokeOne(function(r){return r.loadNode&&r.loadNode(t)});break;case"mesh":i=this._invokeOne(function(r){return r.loadMesh&&r.loadMesh(t)});break;case"accessor":i=this.loadAccessor(t);break;case"bufferView":i=this._invokeOne(function(r){return r.loadBufferView&&r.loadBufferView(t)});break;case"buffer":i=this.loadBuffer(t);break;case"material":i=this._invokeOne(function(r){return r.loadMaterial&&r.loadMaterial(t)});break;case"texture":i=this._invokeOne(function(r){return r.loadTexture&&r.loadTexture(t)});break;case"skin":i=this.loadSkin(t);break;case"animation":i=this._invokeOne(function(r){return r.loadAnimation&&r.loadAnimation(t)});break;case"camera":i=this.loadCamera(t);break;default:if(i=this._invokeOne(function(r){return r!=this&&r.getDependency&&r.getDependency(e,t)}),!i)throw new Error("Unknown type: "+e);break}this.cache.add(n,i)}return i}getDependencies(e){let t=this.cache.get(e);if(!t){let n=this,i=this.json[e+(e==="mesh"?"es":"s")]||[];t=Promise.all(i.map(function(r,a){return n.getDependency(e,a)})),this.cache.add(e,t)}return t}loadBuffer(e){let t=this.json.buffers[e],n=this.fileLoader;if(t.type&&t.type!=="arraybuffer")throw new Error("THREE.GLTFLoader: "+t.type+" buffer type is not supported.");if(t.uri===void 0&&e===0)return Promise.resolve(this.extensions[Ze.KHR_BINARY_GLTF].body);let i=this.options;return new Promise(function(r,a){n.load(Si.resolveURL(t.uri,i.path),r,void 0,function(){a(new Error('THREE.GLTFLoader: Failed to load buffer "'+t.uri+'".'))})})}loadBufferView(e){let t=this.json.bufferViews[e];return this.getDependency("buffer",t.buffer).then(function(n){let i=t.byteLength||0,r=t.byteOffset||0;return n.slice(r,r+i)})}loadAccessor(e){let t=this,n=this.json,i=this.json.accessors[e];if(i.bufferView===void 0&&i.sparse===void 0){let a=Yh[i.type],o=_r[i.componentType],c=i.normalized===!0,l=new o(i.count*a);return Promise.resolve(new xt(l,a,c))}let r=[];return i.bufferView!==void 0?r.push(this.getDependency("bufferView",i.bufferView)):r.push(null),i.sparse!==void 0&&(r.push(this.getDependency("bufferView",i.sparse.indices.bufferView)),r.push(this.getDependency("bufferView",i.sparse.values.bufferView))),Promise.all(r).then(function(a){let o=a[0],c=Yh[i.type],l=_r[i.componentType],u=l.BYTES_PER_ELEMENT,h=u*c,d=i.byteOffset||0,f=i.bufferView!==void 0?n.bufferViews[i.bufferView].byteStride:void 0,g=i.normalized===!0,y,m;if(f&&f!==h){let p=Math.floor(d/f),x="InterleavedBuffer:"+i.bufferView+":"+i.componentType+":"+p+":"+i.count,v=t.cache.get(x);v||(y=new l(o,p*f,i.count*f/u),v=new nr(y,f/u),t.cache.add(x,v)),m=new ir(v,c,d%f/u,g)}else o===null?y=new l(i.count*c):y=new l(o,d,i.count*c),m=new xt(y,c,g);if(i.sparse!==void 0){let p=Yh.SCALAR,x=_r[i.sparse.indices.componentType],v=i.sparse.indices.byteOffset||0,b=i.sparse.values.byteOffset||0,S=new x(a[1],v,i.sparse.count*p),w=new l(a[2],b,i.sparse.count*c);o!==null&&(m=new xt(m.array.slice(),m.itemSize,m.normalized)),m.normalized=!1;for(let T=0,A=S.length;T<A;T++){let M=S[T];if(m.setX(M,w[T*c]),c>=2&&m.setY(M,w[T*c+1]),c>=3&&m.setZ(M,w[T*c+2]),c>=4&&m.setW(M,w[T*c+3]),c>=5)throw new Error("THREE.GLTFLoader: Unsupported itemSize in sparse BufferAttribute.")}m.normalized=g}return m})}loadTexture(e){let t=this.json,n=this.options,r=t.textures[e].source,a=t.images[r],o=this.textureLoader;if(a.uri){let c=n.manager.getHandler(a.uri);c!==null&&(o=c)}return this.loadTextureImage(e,r,o)}loadTextureImage(e,t,n){let i=this,r=this.json,a=r.textures[e],o=r.images[t],c=(o.uri||o.bufferView)+":"+a.sampler;if(this.textureCache[c])return this.textureCache[c];let l=this.loadImageSource(t,n).then(function(u){u.flipY=!1,u.name=a.name||o.name||"",u.name===""&&typeof o.uri=="string"&&o.uri.startsWith("data:image/")===!1&&(u.name=o.uri);let d=(r.samplers||{})[a.sampler]||{};return u.magFilter=fp[d.magFilter]||jt,u.minFilter=fp[d.minFilter]||qn,u.wrapS=pp[d.wrapS]||Ui,u.wrapT=pp[d.wrapT]||Ui,u.generateMipmaps=!u.isCompressedTexture&&u.minFilter!==qt&&u.minFilter!==jt,i.associations.set(u,{textures:e}),u}).catch(function(){return null});return this.textureCache[c]=l,l}loadImageSource(e,t){let n=this,i=this.json,r=this.options;if(this.sourceCache[e]!==void 0)return this.sourceCache[e].then(h=>h.clone());let a=i.images[e],o=self.URL||self.webkitURL,c=a.uri||"",l=!1;if(a.bufferView!==void 0)c=n.getDependency("bufferView",a.bufferView).then(function(h){l=!0;let d=new Blob([h],{type:a.mimeType});return c=o.createObjectURL(d),c});else if(a.uri===void 0)throw new Error("THREE.GLTFLoader: Image "+e+" is missing URI and bufferView");let u=Promise.resolve(c).then(function(h){return new Promise(function(d,f){let g=d;t.isImageBitmapLoader===!0&&(g=function(y){let m=new Wt(y);m.needsUpdate=!0,d(m)}),t.load(Si.resolveURL(h,r.path),g,void 0,f)})}).then(function(h){return l===!0&&o.revokeObjectURL(c),oi(h,a),h.userData.mimeType=a.mimeType||wv(a.uri),h}).catch(function(h){throw console.error("THREE.GLTFLoader: Couldn't load texture",c),h});return this.sourceCache[e]=u,u}assignTexture(e,t,n,i){let r=this;return this.getDependency("texture",n.index).then(function(a){if(!a)return null;if(n.texCoord!==void 0&&n.texCoord>0&&(a=a.clone(),a.channel=n.texCoord),r.extensions[Ze.KHR_TEXTURE_TRANSFORM]){let o=n.extensions!==void 0?n.extensions[Ze.KHR_TEXTURE_TRANSFORM]:void 0;if(o){let c=r.associations.get(a);a=r.extensions[Ze.KHR_TEXTURE_TRANSFORM].extendTexture(a,o),r.associations.set(a,c)}}return i!==void 0&&(a.colorSpace=i),e[t]=a,a})}assignFinalMaterial(e){let t=e.geometry,n=e.material,i=t.attributes.tangent===void 0,r=t.attributes.color!==void 0,a=t.attributes.normal===void 0;if(e.isPoints){let o="PointsMaterial:"+n.uuid,c=this.cache.get(o);c||(c=new or,cn.prototype.copy.call(c,n),c.color.copy(n.color),c.map=n.map,c.sizeAttenuation=!1,this.cache.add(o,c)),n=c}else if(e.isLine){let o="LineBasicMaterial:"+n.uuid,c=this.cache.get(o);c||(c=new ar,cn.prototype.copy.call(c,n),c.color.copy(n.color),c.map=n.map,this.cache.add(o,c)),n=c}if(i||r||a){let o="ClonedMaterial:"+n.uuid+":";i&&(o+="derivative-tangents:"),r&&(o+="vertex-colors:"),a&&(o+="flat-shading:");let c=this.cache.get(o);c||(c=n.clone(),r&&(c.vertexColors=!0),a&&(c.flatShading=!0),i&&(c.normalScale&&(c.normalScale.y*=-1),c.clearcoatNormalScale&&(c.clearcoatNormalScale.y*=-1)),this.cache.add(o,c),this.associations.set(c,this.associations.get(n))),n=c}e.material=n}getMaterialType(){return Lt}loadMaterial(e){let t=this,n=this.json,i=this.extensions,r=n.materials[e],a,o={},c=r.extensions||{},l=[];if(c[Ze.KHR_MATERIALS_UNLIT]){let h=i[Ze.KHR_MATERIALS_UNLIT];a=h.getMaterialType(),l.push(h.extendParams(o,r,t))}else{let h=r.pbrMetallicRoughness||{};if(o.color=new Ue(1,1,1),o.opacity=1,Array.isArray(h.baseColorFactor)){let d=h.baseColorFactor;o.color.setRGB(d[0],d[1],d[2],Kt),o.opacity=d[3]}h.baseColorTexture!==void 0&&l.push(t.assignTexture(o,"map",h.baseColorTexture,kt)),o.metalness=h.metallicFactor!==void 0?h.metallicFactor:1,o.roughness=h.roughnessFactor!==void 0?h.roughnessFactor:1,h.metallicRoughnessTexture!==void 0&&(l.push(t.assignTexture(o,"metalnessMap",h.metallicRoughnessTexture)),l.push(t.assignTexture(o,"roughnessMap",h.metallicRoughnessTexture))),a=this._invokeOne(function(d){return d.getMaterialType&&d.getMaterialType(e)}),l.push(Promise.all(this._invokeAll(function(d){return d.extendMaterialParams&&d.extendMaterialParams(e,o)})))}r.doubleSided===!0&&(o.side=Mt);let u=r.alphaMode||Xh.OPAQUE;if(u===Xh.BLEND?(o.transparent=!0,o.depthWrite=!1):(o.transparent=!1,u===Xh.MASK&&(o.alphaTest=r.alphaCutoff!==void 0?r.alphaCutoff:.5)),r.normalTexture!==void 0&&a!==nn&&(l.push(t.assignTexture(o,"normalMap",r.normalTexture)),o.normalScale=new Ne(1,1),r.normalTexture.scale!==void 0)){let h=r.normalTexture.scale;o.normalScale.set(h,h)}if(r.occlusionTexture!==void 0&&a!==nn&&(l.push(t.assignTexture(o,"aoMap",r.occlusionTexture)),r.occlusionTexture.strength!==void 0&&(o.aoMapIntensity=r.occlusionTexture.strength)),r.emissiveFactor!==void 0&&a!==nn){let h=r.emissiveFactor;o.emissive=new Ue().setRGB(h[0],h[1],h[2],Kt)}return r.emissiveTexture!==void 0&&a!==nn&&l.push(t.assignTexture(o,"emissiveMap",r.emissiveTexture,kt)),Promise.all(l).then(function(){let h=new a(o);return r.name&&(h.name=r.name),oi(h,r),t.associations.set(h,{materials:e}),r.extensions&&_s(i,h,r),h})}createUniqueName(e){let t=yt.sanitizeNodeName(e||"");return t in this.nodeNamesUsed?t+"_"+ ++this.nodeNamesUsed[t]:(this.nodeNamesUsed[t]=0,t)}loadGeometries(e){let t=this,n=this.extensions,i=this.primitiveCache;function r(o){return n[Ze.KHR_DRACO_MESH_COMPRESSION].decodePrimitive(o,t).then(function(c){return mp(c,o,t)})}let a=[];for(let o=0,c=e.length;o<c;o++){let l=e[o],u=_v(l),h=i[u];if(h)a.push(h.promise);else{let d;l.extensions&&l.extensions[Ze.KHR_DRACO_MESH_COMPRESSION]?d=r(l):d=mp(new Bt,l,t),i[u]={primitive:l,promise:d},a.push(d)}}return Promise.all(a)}loadMesh(e){let t=this,n=this.json,i=this.extensions,r=n.meshes[e],a=r.primitives,o=[];for(let c=0,l=a.length;c<l;c++){let u=a[c].material===void 0?yv(this.cache):this.getDependency("material",a[c].material);o.push(u)}return o.push(t.loadGeometries(a)),Promise.all(o).then(function(c){let l=c.slice(0,c.length-1),u=c[c.length-1],h=[];for(let f=0,g=u.length;f<g;f++){let y=u[f],m=a[f],p,x=l[f];if(m.mode===Un.TRIANGLES||m.mode===Un.TRIANGLE_STRIP||m.mode===Un.TRIANGLE_FAN||m.mode===void 0)p=r.isSkinnedMesh===!0?new sa(y,x):new at(y,x),p.isSkinnedMesh===!0&&p.normalizeSkinWeights(),m.mode===Un.TRIANGLE_STRIP?p.geometry=Wh(p.geometry,Ca):m.mode===Un.TRIANGLE_FAN&&(p.geometry=Wh(p.geometry,mr));else if(m.mode===Un.LINES)p=new oa(y,x);else if(m.mode===Un.LINE_STRIP)p=new as(y,x);else if(m.mode===Un.LINE_LOOP)p=new ca(y,x);else if(m.mode===Un.POINTS)p=new la(y,x);else throw new Error("THREE.GLTFLoader: Primitive mode unsupported: "+m.mode);Object.keys(p.geometry.morphAttributes).length>0&&vv(p,r),p.name=t.createUniqueName(r.name||"mesh_"+e),oi(p,r),m.extensions&&_s(i,p,m),t.assignFinalMaterial(p),h.push(p)}for(let f=0,g=h.length;f<g;f++)t.associations.set(h[f],{meshes:e,primitives:f});if(h.length===1)return r.extensions&&_s(i,h[0],r),h[0];let d=new Gt;r.extensions&&_s(i,d,r),t.associations.set(d,{meshes:e});for(let f=0,g=h.length;f<g;f++)d.add(h[f]);return d})}loadCamera(e){let t,n=this.json.cameras[e],i=n[n.type];if(!i){console.warn("THREE.GLTFLoader: Missing camera parameters.");return}return n.type==="perspective"?t=new Ut(Ct.radToDeg(i.yfov),i.aspectRatio||1,i.znear||1,i.zfar||2e6):n.type==="orthographic"&&(t=new hs(-i.xmag,i.xmag,i.ymag,-i.ymag,i.znear,i.zfar)),n.name&&(t.name=this.createUniqueName(n.name)),oi(t,n),Promise.resolve(t)}loadSkin(e){let t=this.json.skins[e],n=[];for(let i=0,r=t.joints.length;i<r;i++)n.push(this._loadNodeShallow(t.joints[i]));return t.inverseBindMatrices!==void 0?n.push(this.getDependency("accessor",t.inverseBindMatrices)):n.push(null),Promise.all(n).then(function(i){let r=i.pop(),a=i,o=[],c=[];for(let l=0,u=a.length;l<u;l++){let h=a[l];if(h){o.push(h);let d=new ke;r!==null&&d.fromArray(r.array,l*16),c.push(d)}else console.warn('THREE.GLTFLoader: Joint "%s" could not be found.',t.joints[l])}return new ra(o,c)})}loadAnimation(e){let t=this.json,n=this,i=t.animations[e],r=i.name?i.name:"animation_"+e,a=[],o=[],c=[],l=[],u=[];for(let h=0,d=i.channels.length;h<d;h++){let f=i.channels[h],g=i.samplers[f.sampler],y=f.target,m=y.node,p=i.parameters!==void 0?i.parameters[g.input]:g.input,x=i.parameters!==void 0?i.parameters[g.output]:g.output;y.node!==void 0&&(a.push(this.getDependency("node",m)),o.push(this.getDependency("accessor",p)),c.push(this.getDependency("accessor",x)),l.push(g),u.push(y))}return Promise.all([Promise.all(a),Promise.all(o),Promise.all(c),Promise.all(l),Promise.all(u)]).then(function(h){let d=h[0],f=h[1],g=h[2],y=h[3],m=h[4],p=[];for(let v=0,b=d.length;v<b;v++){let S=d[v],w=f[v],T=g[v],A=y[v],M=m[v];if(S===void 0)continue;S.updateMatrix&&S.updateMatrix();let _=n._createAnimationTracks(S,w,T,A,M);if(_)for(let I=0;I<_.length;I++)p.push(_[I])}let x=new ga(r,void 0,p);return oi(x,i),x})}createNodeMesh(e){let t=this.json,n=this,i=t.nodes[e];return i.mesh===void 0?null:n.getDependency("mesh",i.mesh).then(function(r){let a=n._getNodeRef(n.meshCache,i.mesh,r);return i.weights!==void 0&&a.traverse(function(o){if(o.isMesh)for(let c=0,l=i.weights.length;c<l;c++)o.morphTargetInfluences[c]=i.weights[c]}),a})}loadNode(e){let t=this.json,n=this,i=t.nodes[e],r=n._loadNodeShallow(e),a=[],o=i.children||[];for(let l=0,u=o.length;l<u;l++)a.push(n.getDependency("node",o[l]));let c=i.skin===void 0?Promise.resolve(null):n.getDependency("skin",i.skin);return Promise.all([r,Promise.all(a),c]).then(function(l){let u=l[0],h=l[1],d=l[2];d!==null&&u.traverse(function(f){f.isSkinnedMesh&&f.bind(d,Mv)});for(let f=0,g=h.length;f<g;f++)u.add(h[f]);return u})}_loadNodeShallow(e){let t=this.json,n=this.extensions,i=this;if(this.nodeCache[e]!==void 0)return this.nodeCache[e];let r=t.nodes[e],a=r.name?i.createUniqueName(r.name):"",o=[],c=i._invokeOne(function(l){return l.createNodeMesh&&l.createNodeMesh(e)});return c&&o.push(c),r.camera!==void 0&&o.push(i.getDependency("camera",r.camera).then(function(l){return i._getNodeRef(i.cameraCache,r.camera,l)})),i._invokeAll(function(l){return l.createNodeAttachment&&l.createNodeAttachment(e)}).forEach(function(l){o.push(l)}),this.nodeCache[e]=Promise.all(o).then(function(l){let u;if(r.isBone===!0?u=new sr:l.length>1?u=new Gt:l.length===1?u=l[0]:u=new Et,u!==l[0])for(let h=0,d=l.length;h<d;h++)u.add(l[h]);if(r.name&&(u.userData.name=r.name,u.name=a),oi(u,r),r.extensions&&_s(n,u,r),r.matrix!==void 0){let h=new ke;h.fromArray(r.matrix),u.applyMatrix4(h)}else r.translation!==void 0&&u.position.fromArray(r.translation),r.rotation!==void 0&&u.quaternion.fromArray(r.rotation),r.scale!==void 0&&u.scale.fromArray(r.scale);if(!i.associations.has(u))i.associations.set(u,{});else if(r.mesh!==void 0&&i.meshCache.refs[r.mesh]>1){let h=i.associations.get(u);i.associations.set(u,{...h})}return i.associations.get(u).nodes=e,u}),this.nodeCache[e]}loadScene(e){let t=this.extensions,n=this.json.scenes[e],i=this,r=new Gt;n.name&&(r.name=i.createUniqueName(n.name)),oi(r,n),n.extensions&&_s(t,r,n);let a=n.nodes||[],o=[];for(let c=0,l=a.length;c<l;c++)o.push(i.getDependency("node",a[c]));return Promise.all(o).then(function(c){for(let u=0,h=c.length;u<h;u++)r.add(c[u]);let l=u=>{let h=new Map;for(let[d,f]of i.associations)(d instanceof cn||d instanceof Wt)&&h.set(d,f);return u.traverse(d=>{let f=i.associations.get(d);f!=null&&h.set(d,f)}),h};return i.associations=l(r),r})}_createAnimationTracks(e,t,n,i,r){let a=[],o=e.name?e.name:e.uuid,c=[];Hi[r.path]===Hi.weights?e.traverse(function(d){d.morphTargetInfluences&&c.push(d.name?d.name:d.uuid)}):c.push(o);let l;switch(Hi[r.path]){case Hi.weights:l=ti;break;case Hi.rotation:l=ni;break;case Hi.translation:case Hi.scale:l=ii;break;default:n.itemSize===1?l=ti:l=ii;break}let u=i.interpolation!==void 0?bv[i.interpolation]:is,h=this._getArrayFromAccessor(n);for(let d=0,f=c.length;d<f;d++){let g=new l(c[d]+"."+Hi[r.path],t.array,h,u);i.interpolation==="CUBICSPLINE"&&this._createCubicSplineTrackInterpolant(g),a.push(g)}return a}_getArrayFromAccessor(e){let t=e.array;if(e.normalized){let n=yu(t.constructor),i=new Float32Array(t.length);for(let r=0,a=t.length;r<a;r++)i[r]=t[r]*n;t=i}return t}_createCubicSplineTrackInterpolant(e){e.createInterpolant=function(n){let i=this instanceof ni?gu:Wc;return new i(this.times,this.values,this.getValueSize()/3,n)},e.createInterpolant.isInterpolantFactoryMethodGLTFCubicSpline=!0}};function Sv(s,e,t){let n=e.attributes,i=new ot;if(n.POSITION!==void 0){let o=t.json.accessors[n.POSITION],c=o.min,l=o.max;if(c!==void 0&&l!==void 0){if(i.set(new L(c[0],c[1],c[2]),new L(l[0],l[1],l[2])),o.normalized){let u=yu(_r[o.componentType]);i.min.multiplyScalar(u),i.max.multiplyScalar(u)}}else{console.warn("THREE.GLTFLoader: Missing min/max properties for accessor POSITION.");return}}else return;let r=e.targets;if(r!==void 0){let o=new L,c=new L;for(let l=0,u=r.length;l<u;l++){let h=r[l];if(h.POSITION!==void 0){let d=t.json.accessors[h.POSITION],f=d.min,g=d.max;if(f!==void 0&&g!==void 0){if(c.setX(Math.max(Math.abs(f[0]),Math.abs(g[0]))),c.setY(Math.max(Math.abs(f[1]),Math.abs(g[1]))),c.setZ(Math.max(Math.abs(f[2]),Math.abs(g[2]))),d.normalized){let y=yu(_r[d.componentType]);c.multiplyScalar(y)}o.max(c)}else console.warn("THREE.GLTFLoader: Missing min/max properties for accessor POSITION.")}}i.expandByVector(o)}s.boundingBox=i;let a=new tn;i.getCenter(a.center),a.radius=i.min.distanceTo(i.max)/2,s.boundingSphere=a}function mp(s,e,t){let n=e.attributes,i=[];function r(a,o){return t.getDependency("accessor",a).then(function(c){s.setAttribute(o,c)})}for(let a in n){let o=bu[a]||a.toLowerCase();o in s.attributes||i.push(r(n[a],o))}if(e.indices!==void 0&&!s.index){let a=t.getDependency("accessor",e.indices).then(function(o){s.setIndex(o)});i.push(a)}return et.workingColorSpace!==Kt&&"COLOR_0"in n&&console.warn(`THREE.GLTFLoader: Converting vertex colors from "srgb-linear" to "${et.workingColorSpace}" not supported.`),oi(s,e),Sv(s,e,t),Promise.all(i).then(function(){return e.targets!==void 0?xv(s,e.targets,t):s})}var bp=(function(){var s="b9H79Tebbbe8Fv9Gbb9Gvuuuuueu9Giuuub9Geueu9Giuuueuikqbeeedddillviebeoweuec:q:Odkr;leDo9TW9T9VV95dbH9F9F939H79T9F9J9H229F9Jt9VV7bb8A9TW79O9V9Wt9F9KW9J9V9KW9wWVtW949c919M9MWVbeY9TW79O9V9Wt9F9KW9J9V9KW69U9KW949c919M9MWVbdE9TW79O9V9Wt9F9KW9J9V9KW69U9KW949tWG91W9U9JWbiL9TW79O9V9Wt9F9KW9J9V9KWS9P2tWV9p9JtblK9TW79O9V9Wt9F9KW9J9V9KWS9P2tWV9r919HtbvL9TW79O9V9Wt9F9KW9J9V9KWS9P2tWVT949Wbol79IV9Rbrq;w8Wqdbk;esezu8Jjjjjbcj;eb9Rgv8Kjjjjbc9:hodnadcefal0mbcuhoaiRbbc:Ge9hmbavaialfgrad9Radz1jjjbhwcj;abad9Uc;WFbGgocjdaocjd6EhDaicefhocbhqdnindndndnaeaq9nmbaDaeaq9RaqaDfae6Egkcsfglcl4cifcd4hxalc9WGgmTmecbhPawcjdfhsaohzinaraz9Rax6mvarazaxfgo9RcK6mvczhlcbhHinalgic9WfgOawcj;cbffhldndndndndnazaOco4fRbbaHcoG4ciGPlbedibkal9cb83ibalcwf9cb83ibxikalaoRblaoRbbgOco4gAaAciSgAE86bbawcj;cbfaifglcGfaoclfaAfgARbbaOcl4ciGgCaCciSgCE86bbalcVfaAaCfgARbbaOcd4ciGgCaCciSgCE86bbalc7faAaCfgARbbaOciGgOaOciSgOE86bbalctfaAaOfgARbbaoRbegOco4gCaCciSgCE86bbalc91faAaCfgARbbaOcl4ciGgCaCciSgCE86bbalc4faAaCfgARbbaOcd4ciGgCaCciSgCE86bbalc93faAaCfgARbbaOciGgOaOciSgOE86bbalc94faAaOfgARbbaoRbdgOco4gCaCciSgCE86bbalc95faAaCfgARbbaOcl4ciGgCaCciSgCE86bbalc96faAaCfgARbbaOcd4ciGgCaCciSgCE86bbalc97faAaCfgARbbaOciGgOaOciSgOE86bbalc98faAaOfgORbbaoRbigoco4gAaAciSgAE86bbalc99faOaAfgORbbaocl4ciGgAaAciSgAE86bbalc9:faOaAfgORbbaocd4ciGgAaAciSgAE86bbalcufaOaAfglRbbaociGgoaociSgoE86bbalaofhoxdkalaoRbwaoRbbgOcl4gAaAcsSgAE86bbawcj;cbfaifglcGfaocwfaAfgARbbaOcsGgOaOcsSgOE86bbalcVfaAaOfgORbbaoRbegAcl4gCaCcsSgCE86bbalc7faOaCfgORbbaAcsGgAaAcsSgAE86bbalctfaOaAfgORbbaoRbdgAcl4gCaCcsSgCE86bbalc91faOaCfgORbbaAcsGgAaAcsSgAE86bbalc4faOaAfgORbbaoRbigAcl4gCaCcsSgCE86bbalc93faOaCfgORbbaAcsGgAaAcsSgAE86bbalc94faOaAfgORbbaoRblgAcl4gCaCcsSgCE86bbalc95faOaCfgORbbaAcsGgAaAcsSgAE86bbalc96faOaAfgORbbaoRbvgAcl4gCaCcsSgCE86bbalc97faOaCfgORbbaAcsGgAaAcsSgAE86bbalc98faOaAfgORbbaoRbogAcl4gCaCcsSgCE86bbalc99faOaCfgORbbaAcsGgAaAcsSgAE86bbalc9:faOaAfgORbbaoRbrgocl4gAaAcsSgAE86bbalcufaOaAfglRbbaocsGgoaocsSgoE86bbalaofhoxekalao8Pbb83bbalcwfaocwf8Pbb83bbaoczfhokdnaiam9pmbaHcdfhHaiczfhlarao9RcL0mekkaiam6mvaoTmvdnakTmbawaPfRbbhHawcj;cbfhlashiakhOinaialRbbgzce4cbazceG9R7aHfgH86bbaiadfhialcefhlaOcufgOmbkkascefhsaohzaPcefgPad9hmbxikkcbc99arao9Radcaadca0ESEhoxlkaoaxad2fhCdnakmbadhlinaoTmlarao9Rax6mlaoaxfhoalcufglmbkaChoxekcbhmawcjdfhAinarao9Rax6miawamfRbbhHawcj;cbfhlaAhiakhOinaialRbbgzce4cbazceG9R7aHfgH86bbaiadfhialcefhlaOcufgOmbkaAcefhAaoaxfhoamcefgmad9hmbkaChokabaqad2fawcjdfakad2z1jjjb8Aawawcjdfakcufad2fadz1jjjb8Aakaqfhqaombkc9:hoxekc9:hokavcj;ebf8Kjjjjbaok;cseHu8Jjjjjbc;ae9Rgv8Kjjjjbc9:hodnaeci9UgrcHfal0mbcuhoaiRbbgwc;WeGc;Ge9hmbawcsGgwce0mbavc;abfcFecjez:jjjjb8AavcUf9cu83ibavc8Wf9cu83ibavcyf9cu83ibavcaf9cu83ibavcKf9cu83ibavczf9cu83ibav9cu83iwav9cu83ibaialfc9WfhDaicefgqarfhidnaeTmbcmcsawceSEhkcbhxcbhmcbhPcbhwcbhlindnaiaD9nmbc9:hoxikdndnaqRbbgoc;Ve0mbavc;abfalaocu7gscl4fcsGcitfgzydlhrazydbhzdnaocsGgHak9pmbavawasfcsGcdtfydbaxaHEhoaHThsdndnadcd9hmbabaPcetfgHaz87ebaHclfao87ebaHcdfar87ebxekabaPcdtfgHazBdbaHcwfaoBdbaHclfarBdbkaxasfhxcdhHavawcdtfaoBdbawasfhwcehsalhOxdkdndnaHcsSmbaHc987aHamffcefhoxekaicefhoai8SbbgHcFeGhsdndnaHcu9mmbaohixekaicvfhiascFbGhscrhHdninao8SbbgOcFbGaHtasVhsaOcu9kmeaocefhoaHcrfgHc8J9hmbxdkkaocefhikasce4cbasceG9R7amfhokdndnadcd9hmbabaPcetfgHaz87ebaHclfao87ebaHcdfar87ebxekabaPcdtfgHazBdbaHcwfaoBdbaHclfarBdbkcdhHavawcdtfaoBdbcehsawcefhwalhOaohmxekdnaocpe0mbaxcefgHavawaDaocsGfRbbgocl49RcsGcdtfydbaocz6gzEhravawao9RcsGcdtfydbaHazfgAaocsGgHEhoaHThCdndnadcd9hmbabaPcetfgHax87ebaHclfao87ebaHcdfar87ebxekabaPcdtfgHaxBdbaHcwfaoBdbaHclfarBdbkcdhsavawcdtfaxBdbavawcefgwcsGcdtfarBdbcihHavc;abfalcitfgOaxBdlaOarBdbavawazfgwcsGcdtfaoBdbalcefcsGhOawaCfhwaxhzaAaCfhxxekaxcbaiRbbgOEgzaoc;:eSgHfhraOcsGhCaOcl4hAdndnaOcs0mbarcefhoxekarhoavawaA9RcsGcdtfydbhrkdndnaCmbaocefhxxekaohxavawaO9RcsGcdtfydbhokdndnaHTmbaicefhHxekaicdfhHai8SbegscFeGhzdnascu9kmbaicofhXazcFbGhzcrhidninaH8SbbgscFbGaitazVhzascu9kmeaHcefhHaicrfgic8J9hmbkaXhHxekaHcefhHkazce4cbazceG9R7amfgmhzkdndnaAcsSmbaHhsxekaHcefhsaH8SbbgicFeGhrdnaicu9kmbaHcvfhXarcFbGhrcrhidninas8SbbgHcFbGaitarVhraHcu9kmeascefhsaicrfgic8J9hmbkaXhsxekascefhskarce4cbarceG9R7amfgmhrkdndnaCcsSmbashixekascefhias8SbbgocFeGhHdnaocu9kmbascvfhXaHcFbGhHcrhodninai8SbbgscFbGaotaHVhHascu9kmeaicefhiaocrfgoc8J9hmbkaXhixekaicefhikaHce4cbaHceG9R7amfgmhokdndnadcd9hmbabaPcetfgHaz87ebaHclfao87ebaHcdfar87ebxekabaPcdtfgHazBdbaHcwfaoBdbaHclfarBdbkcdhsavawcdtfazBdbavawcefgwcsGcdtfarBdbcihHavc;abfalcitfgXazBdlaXarBdbavawaOcz6aAcsSVfgwcsGcdtfaoBdbawaCTaCcsSVfhwalcefcsGhOkaqcefhqavc;abfaOcitfgOarBdlaOaoBdbavc;abfalasfcsGcitfgraoBdlarazBdbawcsGhwalaHfcsGhlaPcifgPae6mbkkcbc99aiaDSEhokavc;aef8Kjjjjbaok:flevu8Jjjjjbcz9Rhvc9:hodnaecvfal0mbcuhoaiRbbc;:eGc;qe9hmbav9cb83iwaicefhraialfc98fhwdnaeTmbdnadcdSmbcbhDindnaraw6mbc9:skarcefhoar8SbbglcFeGhidndnalcu9mmbaohrxekarcvfhraicFbGhicrhldninao8SbbgdcFbGaltaiVhiadcu9kmeaocefhoalcrfglc8J9hmbxdkkaocefhrkabaDcdtfaic8Etc8F91aicd47avcwfaiceGcdtVgoydbfglBdbaoalBdbaDcefgDae9hmbxdkkcbhDindnaraw6mbc9:skarcefhoar8SbbglcFeGhidndnalcu9mmbaohrxekarcvfhraicFbGhicrhldninao8SbbgdcFbGaltaiVhiadcu9kmeaocefhoalcrfglc8J9hmbxdkkaocefhrkabaDcetfaic8Etc8F91aicd47avcwfaiceGcdtVgoydbfgl87ebaoalBdbaDcefgDae9hmbkkcbc99arawSEhokaok:Lvoeue99dud99eud99dndnadcl9hmbaeTmeindndnabcdfgd8Sbb:Yab8Sbbgi:Ygl:l:tabcefgv8Sbbgo:Ygr:l:tgwJbb;:9cawawNJbbbbawawJbbbb9GgDEgq:mgkaqaicb9iEalMgwawNakaqaocb9iEarMgqaqNMM:r:vglNJbbbZJbbb:;aDEMgr:lJbbb9p9DTmbar:Ohixekcjjjj94hikadai86bbdndnaqalNJbbbZJbbb:;aqJbbbb9GEMgq:lJbbb9p9DTmbaq:Ohdxekcjjjj94hdkavad86bbdndnawalNJbbbZJbbb:;awJbbbb9GEMgw:lJbbb9p9DTmbaw:Ohdxekcjjjj94hdkabad86bbabclfhbaecufgembxdkkaeTmbindndnabclfgd8Ueb:Yab8Uebgi:Ygl:l:tabcdfgv8Uebgo:Ygr:l:tgwJb;:FSawawNJbbbbawawJbbbb9GgDEgq:mgkaqaicb9iEalMgwawNakaqaocb9iEarMgqaqNMM:r:vglNJbbbZJbbb:;aDEMgr:lJbbb9p9DTmbar:Ohixekcjjjj94hikadai87ebdndnaqalNJbbbZJbbb:;aqJbbbb9GEMgq:lJbbb9p9DTmbaq:Ohdxekcjjjj94hdkavad87ebdndnawalNJbbbZJbbb:;awJbbbb9GEMgw:lJbbb9p9DTmbaw:Ohdxekcjjjj94hdkabad87ebabcwfhbaecufgembkkk;oiliui99iue99dnaeTmbcbhiabhlindndnJ;Zl81Zalcof8UebgvciV:Y:vgoal8Ueb:YNgrJb;:FSNJbbbZJbbb:;arJbbbb9GEMgw:lJbbb9p9DTmbaw:OhDxekcjjjj94hDkalclf8Uebhqalcdf8UebhkabaiavcefciGfcetfaD87ebdndnaoak:YNgwJb;:FSNJbbbZJbbb:;awJbbbb9GEMgx:lJbbb9p9DTmbax:OhDxekcjjjj94hDkabaiavciGfgkcd7cetfaD87ebdndnaoaq:YNgoJb;:FSNJbbbZJbbb:;aoJbbbb9GEMgx:lJbbb9p9DTmbax:OhDxekcjjjj94hDkabaiavcufciGfcetfaD87ebdndnJbbjZararN:tawawN:taoaoN:tgrJbbbbarJbbbb9GE:rJb;:FSNJbbbZMgr:lJbbb9p9DTmbar:Ohvxekcjjjj94hvkabakcetfav87ebalcwfhlaiclfhiaecufgembkkk9mbdnadcd4ae2gdTmbinababydbgecwtcw91:Yaece91cjjj98Gcjjj;8if::NUdbabclfhbadcufgdmbkkk9teiucbcbydj1jjbgeabcifc98GfgbBdj1jjbdndnabZbcztgd9nmbcuhiabad9RcFFifcz4nbcuSmekaehikaik;LeeeudndnaeabVciGTmbabhixekdndnadcz9pmbabhixekabhiinaiaeydbBdbaiclfaeclfydbBdbaicwfaecwfydbBdbaicxfaecxfydbBdbaeczfheaiczfhiadc9Wfgdcs0mbkkadcl6mbinaiaeydbBdbaeclfheaiclfhiadc98fgdci0mbkkdnadTmbinaiaeRbb86bbaicefhiaecefheadcufgdmbkkabk;aeedudndnabciGTmbabhixekaecFeGc:b:c:ew2hldndnadcz9pmbabhixekabhiinaialBdbaicxfalBdbaicwfalBdbaiclfalBdbaiczfhiadc9Wfgdcs0mbkkadcl6mbinaialBdbaiclfhiadc98fgdci0mbkkdnadTmbinaiae86bbaicefhiadcufgdmbkkabkkkebcjwklzNbb",e="b9H79TebbbeKl9Gbb9Gvuuuuueu9Giuuub9Geueuikqbbebeedddilve9Weeeviebeoweuec:q:6dkr;leDo9TW9T9VV95dbH9F9F939H79T9F9J9H229F9Jt9VV7bb8A9TW79O9V9Wt9F9KW9J9V9KW9wWVtW949c919M9MWVbdY9TW79O9V9Wt9F9KW9J9V9KW69U9KW949c919M9MWVblE9TW79O9V9Wt9F9KW9J9V9KW69U9KW949tWG91W9U9JWbvL9TW79O9V9Wt9F9KW9J9V9KWS9P2tWV9p9JtboK9TW79O9V9Wt9F9KW9J9V9KWS9P2tWV9r919HtbrL9TW79O9V9Wt9F9KW9J9V9KWS9P2tWVT949Wbwl79IV9RbDq:p9sqlbzik9:evu8Jjjjjbcz9Rhbcbheincbhdcbhiinabcwfadfaicjuaead4ceGglE86bbaialfhiadcefgdcw9hmbkaec:q:yjjbfai86bbaecitc:q1jjbfab8Piw83ibaecefgecjd9hmbkk:N8JlHud97euo978Jjjjjbcj;kb9Rgv8Kjjjjbc9:hodnadcefal0mbcuhoaiRbbc:Ge9hmbavaialfgrad9Rad;8qbbcj;abad9UhlaicefhodnaeTmbadTmbalc;WFbGglcjdalcjd6EhwcbhDinawaeaD9RaDawfae6Egqcsfglc9WGgkci2hxakcethmalcl4cifcd4hPabaDad2fhsakc;ab6hzcbhHincbhOaohAdndninaraA9RaP6meavcj;cbfaOak2fhCaAaPfhocbhidnazmbarao9Rc;Gb6mbcbhlinaCalfhidndndndndnaAalco4fRbbgXciGPlbedibkaipxbbbbbbbbbbbbbbbbpklbxikaiaopbblaopbbbgQclp:meaQpmbzeHdOiAlCvXoQrLgQcdp:meaQpmbzeHdOiAlCvXoQrLpxiiiiiiiiiiiiiiiip9ogLpxiiiiiiiiiiiiiiiip8JgQp5b9cjF;8;4;W;G;ab9:9cU1:NgKcitc:q1jjbfpbibaKc:q:yjjbfpbbbgYaYpmbbbbbbbbbbbbbbbbaQp5e9cjF;8;4;W;G;ab9:9cU1:NgKcitc:q1jjbfpbibp9UpmbedilvorzHOACXQLpPaLaQp9spklbaoclfaYpQbfaKc:q:yjjbfRbbfhoxdkaiaopbbwaopbbbgQclp:meaQpmbzeHdOiAlCvXoQrLpxssssssssssssssssp9ogLpxssssssssssssssssp8JgQp5b9cjF;8;4;W;G;ab9:9cU1:NgKcitc:q1jjbfpbibaKc:q:yjjbfpbbbgYaYpmbbbbbbbbbbbbbbbbaQp5e9cjF;8;4;W;G;ab9:9cU1:NgKcitc:q1jjbfpbibp9UpmbedilvorzHOACXQLpPaLaQp9spklbaocwfaYpQbfaKc:q:yjjbfRbbfhoxekaiaopbbbpklbaoczfhokdndndndndnaXcd4ciGPlbedibkaipxbbbbbbbbbbbbbbbbpklzxikaiaopbblaopbbbgQclp:meaQpmbzeHdOiAlCvXoQrLgQcdp:meaQpmbzeHdOiAlCvXoQrLpxiiiiiiiiiiiiiiiip9ogLpxiiiiiiiiiiiiiiiip8JgQp5b9cjF;8;4;W;G;ab9:9cU1:NgKcitc:q1jjbfpbibaKc:q:yjjbfpbbbgYaYpmbbbbbbbbbbbbbbbbaQp5e9cjF;8;4;W;G;ab9:9cU1:NgKcitc:q1jjbfpbibp9UpmbedilvorzHOACXQLpPaLaQp9spklzaoclfaYpQbfaKc:q:yjjbfRbbfhoxdkaiaopbbwaopbbbgQclp:meaQpmbzeHdOiAlCvXoQrLpxssssssssssssssssp9ogLpxssssssssssssssssp8JgQp5b9cjF;8;4;W;G;ab9:9cU1:NgKcitc:q1jjbfpbibaKc:q:yjjbfpbbbgYaYpmbbbbbbbbbbbbbbbbaQp5e9cjF;8;4;W;G;ab9:9cU1:NgKcitc:q1jjbfpbibp9UpmbedilvorzHOACXQLpPaLaQp9spklzaocwfaYpQbfaKc:q:yjjbfRbbfhoxekaiaopbbbpklzaoczfhokdndndndndnaXcl4ciGPlbedibkaipxbbbbbbbbbbbbbbbbpklaxikaiaopbblaopbbbgQclp:meaQpmbzeHdOiAlCvXoQrLgQcdp:meaQpmbzeHdOiAlCvXoQrLpxiiiiiiiiiiiiiiiip9ogLpxiiiiiiiiiiiiiiiip8JgQp5b9cjF;8;4;W;G;ab9:9cU1:NgKcitc:q1jjbfpbibaKc:q:yjjbfpbbbgYaYpmbbbbbbbbbbbbbbbbaQp5e9cjF;8;4;W;G;ab9:9cU1:NgKcitc:q1jjbfpbibp9UpmbedilvorzHOACXQLpPaLaQp9spklaaoclfaYpQbfaKc:q:yjjbfRbbfhoxdkaiaopbbwaopbbbgQclp:meaQpmbzeHdOiAlCvXoQrLpxssssssssssssssssp9ogLpxssssssssssssssssp8JgQp5b9cjF;8;4;W;G;ab9:9cU1:NgKcitc:q1jjbfpbibaKc:q:yjjbfpbbbgYaYpmbbbbbbbbbbbbbbbbaQp5e9cjF;8;4;W;G;ab9:9cU1:NgKcitc:q1jjbfpbibp9UpmbedilvorzHOACXQLpPaLaQp9spklaaocwfaYpQbfaKc:q:yjjbfRbbfhoxekaiaopbbbpklaaoczfhokdndndndndnaXco4Plbedibkaipxbbbbbbbbbbbbbbbbpkl8WxikaiaopbblaopbbbgQclp:meaQpmbzeHdOiAlCvXoQrLgQcdp:meaQpmbzeHdOiAlCvXoQrLpxiiiiiiiiiiiiiiiip9ogLpxiiiiiiiiiiiiiiiip8JgQp5b9cjF;8;4;W;G;ab9:9cU1:NgXcitc:q1jjbfpbibaXc:q:yjjbfpbbbgYaYpmbbbbbbbbbbbbbbbbaQp5e9cjF;8;4;W;G;ab9:9cU1:NgXcitc:q1jjbfpbibp9UpmbedilvorzHOACXQLpPaLaQp9spkl8WaoclfaYpQbfaXc:q:yjjbfRbbfhoxdkaiaopbbwaopbbbgQclp:meaQpmbzeHdOiAlCvXoQrLpxssssssssssssssssp9ogLpxssssssssssssssssp8JgQp5b9cjF;8;4;W;G;ab9:9cU1:NgXcitc:q1jjbfpbibaXc:q:yjjbfpbbbgYaYpmbbbbbbbbbbbbbbbbaQp5e9cjF;8;4;W;G;ab9:9cU1:NgXcitc:q1jjbfpbibp9UpmbedilvorzHOACXQLpPaLaQp9spkl8WaocwfaYpQbfaXc:q:yjjbfRbbfhoxekaiaopbbbpkl8Waoczfhokalc;abfhialcjefak0meaihlarao9Rc;Fb0mbkkdnaiak9pmbaici4hlinarao9RcK6miaCaifhXdndndndndnaAaico4fRbbalcoG4ciGPlbedibkaXpxbbbbbbbbbbbbbbbbpkbbxikaXaopbblaopbbbgQclp:meaQpmbzeHdOiAlCvXoQrLgQcdp:meaQpmbzeHdOiAlCvXoQrLpxiiiiiiiiiiiiiiiip9ogLpxiiiiiiiiiiiiiiiip8JgQp5b9cjF;8;4;W;G;ab9:9cU1:NgKcitc:q1jjbfpbibaKc:q:yjjbfpbbbgYaYpmbbbbbbbbbbbbbbbbaQp5e9cjF;8;4;W;G;ab9:9cU1:NgKcitc:q1jjbfpbibp9UpmbedilvorzHOACXQLpPaLaQp9spkbbaoclfaYpQbfaKc:q:yjjbfRbbfhoxdkaXaopbbwaopbbbgQclp:meaQpmbzeHdOiAlCvXoQrLpxssssssssssssssssp9ogLpxssssssssssssssssp8JgQp5b9cjF;8;4;W;G;ab9:9cU1:NgKcitc:q1jjbfpbibaKc:q:yjjbfpbbbgYaYpmbbbbbbbbbbbbbbbbaQp5e9cjF;8;4;W;G;ab9:9cU1:NgKcitc:q1jjbfpbibp9UpmbedilvorzHOACXQLpPaLaQp9spkbbaocwfaYpQbfaKc:q:yjjbfRbbfhoxekaXaopbbbpkbbaoczfhokalcdfhlaiczfgiak6mbkkaoTmeaohAaOcefgOclSmdxbkkc9:hoxlkdnakTmbavcjdfaHfhiavaHfpbdbhYcbhXinaiavcj;cbfaXfglpblbgLcep9TaLpxeeeeeeeeeeeeeeeegQp9op9Hp9rgLalakfpblbg8Acep9Ta8AaQp9op9Hp9rg8ApmbzeHdOiAlCvXoQrLgEalamfpblbg3cep9Ta3aQp9op9Hp9rg3alaxfpblbg5cep9Ta5aQp9op9Hp9rg5pmbzeHdOiAlCvXoQrLg8EpmbezHdiOAlvCXorQLgQaQpmbedibedibedibediaYp9UgYp9AdbbaiadfglaYaQaQpmlvorlvorlvorlvorp9UgYp9AdbbaladfglaYaQaQpmwDqkwDqkwDqkwDqkp9UgYp9AdbbaladfglaYaQaQpmxmPsxmPsxmPsxmPsp9UgYp9AdbbaladfglaYaEa8EpmwDKYqk8AExm35Ps8E8FgQaQpmbedibedibedibedip9UgYp9AdbbaladfglaYaQaQpmlvorlvorlvorlvorp9UgYp9AdbbaladfglaYaQaQpmwDqkwDqkwDqkwDqkp9UgYp9AdbbaladfglaYaQaQpmxmPsxmPsxmPsxmPsp9UgYp9AdbbaladfglaYaLa8ApmwKDYq8AkEx3m5P8Es8FgLa3a5pmwKDYq8AkEx3m5P8Es8Fg8ApmbezHdiOAlvCXorQLgQaQpmbedibedibedibedip9UgYp9AdbbaladfglaYaQaQpmlvorlvorlvorlvorp9UgYp9AdbbaladfglaYaQaQpmwDqkwDqkwDqkwDqkp9UgYp9AdbbaladfglaYaQaQpmxmPsxmPsxmPsxmPsp9UgYp9AdbbaladfglaYaLa8ApmwDKYqk8AExm35Ps8E8FgQaQpmbedibedibedibedip9UgYp9AdbbaladfglaYaQaQpmlvorlvorlvorlvorp9UgYp9AdbbaladfglaYaQaQpmwDqkwDqkwDqkwDqkp9UgYp9AdbbaladfglaYaQaQpmxmPsxmPsxmPsxmPsp9UgYp9AdbbaladfhiaXczfgXak6mbkkaHclfgHad6mbkasavcjdfaqad2;8qbbavavcjdfaqcufad2fad;8qbbaqaDfgDae6mbkkcbc99arao9Radcaadca0ESEhokavcj;kbf8Kjjjjbaokwbz:bjjjbk::seHu8Jjjjjbc;ae9Rgv8Kjjjjbc9:hodnaeci9UgrcHfal0mbcuhoaiRbbgwc;WeGc;Ge9hmbawcsGgwce0mbavc;abfcFecje;8kbavcUf9cu83ibavc8Wf9cu83ibavcyf9cu83ibavcaf9cu83ibavcKf9cu83ibavczf9cu83ibav9cu83iwav9cu83ibaialfc9WfhDaicefgqarfhidnaeTmbcmcsawceSEhkcbhxcbhmcbhPcbhwcbhlindnaiaD9nmbc9:hoxikdndnaqRbbgoc;Ve0mbavc;abfalaocu7gscl4fcsGcitfgzydlhrazydbhzdnaocsGgHak9pmbavawasfcsGcdtfydbaxaHEhoaHThsdndnadcd9hmbabaPcetfgHaz87ebaHclfao87ebaHcdfar87ebxekabaPcdtfgHazBdbaHcwfaoBdbaHclfarBdbkaxasfhxcdhHavawcdtfaoBdbawasfhwcehsalhOxdkdndnaHcsSmbaHc987aHamffcefhoxekaicefhoai8SbbgHcFeGhsdndnaHcu9mmbaohixekaicvfhiascFbGhscrhHdninao8SbbgOcFbGaHtasVhsaOcu9kmeaocefhoaHcrfgHc8J9hmbxdkkaocefhikasce4cbasceG9R7amfhokdndnadcd9hmbabaPcetfgHaz87ebaHclfao87ebaHcdfar87ebxekabaPcdtfgHazBdbaHcwfaoBdbaHclfarBdbkcdhHavawcdtfaoBdbcehsawcefhwalhOaohmxekdnaocpe0mbaxcefgHavawaDaocsGfRbbgocl49RcsGcdtfydbaocz6gzEhravawao9RcsGcdtfydbaHazfgAaocsGgHEhoaHThCdndnadcd9hmbabaPcetfgHax87ebaHclfao87ebaHcdfar87ebxekabaPcdtfgHaxBdbaHcwfaoBdbaHclfarBdbkcdhsavawcdtfaxBdbavawcefgwcsGcdtfarBdbcihHavc;abfalcitfgOaxBdlaOarBdbavawazfgwcsGcdtfaoBdbalcefcsGhOawaCfhwaxhzaAaCfhxxekaxcbaiRbbgOEgzaoc;:eSgHfhraOcsGhCaOcl4hAdndnaOcs0mbarcefhoxekarhoavawaA9RcsGcdtfydbhrkdndnaCmbaocefhxxekaohxavawaO9RcsGcdtfydbhokdndnaHTmbaicefhHxekaicdfhHai8SbegscFeGhzdnascu9kmbaicofhXazcFbGhzcrhidninaH8SbbgscFbGaitazVhzascu9kmeaHcefhHaicrfgic8J9hmbkaXhHxekaHcefhHkazce4cbazceG9R7amfgmhzkdndnaAcsSmbaHhsxekaHcefhsaH8SbbgicFeGhrdnaicu9kmbaHcvfhXarcFbGhrcrhidninas8SbbgHcFbGaitarVhraHcu9kmeascefhsaicrfgic8J9hmbkaXhsxekascefhskarce4cbarceG9R7amfgmhrkdndnaCcsSmbashixekascefhias8SbbgocFeGhHdnaocu9kmbascvfhXaHcFbGhHcrhodninai8SbbgscFbGaotaHVhHascu9kmeaicefhiaocrfgoc8J9hmbkaXhixekaicefhikaHce4cbaHceG9R7amfgmhokdndnadcd9hmbabaPcetfgHaz87ebaHclfao87ebaHcdfar87ebxekabaPcdtfgHazBdbaHcwfaoBdbaHclfarBdbkcdhsavawcdtfazBdbavawcefgwcsGcdtfarBdbcihHavc;abfalcitfgXazBdlaXarBdbavawaOcz6aAcsSVfgwcsGcdtfaoBdbawaCTaCcsSVfhwalcefcsGhOkaqcefhqavc;abfaOcitfgOarBdlaOaoBdbavc;abfalasfcsGcitfgraoBdlarazBdbawcsGhwalaHfcsGhlaPcifgPae6mbkkcbc99aiaDSEhokavc;aef8Kjjjjbaok:flevu8Jjjjjbcz9Rhvc9:hodnaecvfal0mbcuhoaiRbbc;:eGc;qe9hmbav9cb83iwaicefhraialfc98fhwdnaeTmbdnadcdSmbcbhDindnaraw6mbc9:skarcefhoar8SbbglcFeGhidndnalcu9mmbaohrxekarcvfhraicFbGhicrhldninao8SbbgdcFbGaltaiVhiadcu9kmeaocefhoalcrfglc8J9hmbxdkkaocefhrkabaDcdtfaic8Etc8F91aicd47avcwfaiceGcdtVgoydbfglBdbaoalBdbaDcefgDae9hmbxdkkcbhDindnaraw6mbc9:skarcefhoar8SbbglcFeGhidndnalcu9mmbaohrxekarcvfhraicFbGhicrhldninao8SbbgdcFbGaltaiVhiadcu9kmeaocefhoalcrfglc8J9hmbxdkkaocefhrkabaDcetfaic8Etc8F91aicd47avcwfaiceGcdtVgoydbfgl87ebaoalBdbaDcefgDae9hmbkkcbc99arawSEhokaok:wPliuo97eue978Jjjjjbca9Rhiaec98Ghldndnadcl9hmbdnalTmbcbhvabhdinadadpbbbgocKp:RecKp:Sep;6egraocwp:RecKp:Sep;6earp;Geaoczp:RecKp:Sep;6egwp;Gep;Kep;LegDpxbbbbbbbbbbbbbbbbp:2egqarpxbbbjbbbjbbbjbbbjgkp9op9rp;Kegrpxbb;:9cbb;:9cbb;:9cbb;:9cararp;MeaDaDp;Meawaqawakp9op9rp;Kegrarp;Mep;Kep;Kep;Jep;Negwp;Mepxbbn0bbn0bbn0bbn0gqp;KepxFbbbFbbbFbbbFbbbp9oaopxbbbFbbbFbbbFbbbFp9op9qarawp;Meaqp;Kecwp:RepxbFbbbFbbbFbbbFbbp9op9qaDawp;Meaqp;Keczp:RepxbbFbbbFbbbFbbbFbp9op9qpkbbadczfhdavclfgval6mbkkalaeSmeaipxbbbbbbbbbbbbbbbbgqpklbaiabalcdtfgdaeciGglcdtgv;8qbbdnalTmbaiaipblbgocKp:RecKp:Sep;6egraocwp:RecKp:Sep;6earp;Geaoczp:RecKp:Sep;6egwp;Gep;Kep;LegDaqp:2egqarpxbbbjbbbjbbbjbbbjgkp9op9rp;Kegrpxbb;:9cbb;:9cbb;:9cbb;:9cararp;MeaDaDp;Meawaqawakp9op9rp;Kegrarp;Mep;Kep;Kep;Jep;Negwp;Mepxbbn0bbn0bbn0bbn0gqp;KepxFbbbFbbbFbbbFbbbp9oaopxbbbFbbbFbbbFbbbFp9op9qarawp;Meaqp;Kecwp:RepxbFbbbFbbbFbbbFbbp9op9qaDawp;Meaqp;Keczp:RepxbbFbbbFbbbFbbbFbp9op9qpklbkadaiav;8qbbskdnalTmbcbhvabhdinadczfgxaxpbbbgopxbbbbbbFFbbbbbbFFgkp9oadpbbbgDaopmbediwDqkzHOAKY8AEgwczp:Reczp:Sep;6egraDaopmlvorxmPsCXQL358E8FpxFubbFubbFubbFubbp9op;6eawczp:Sep;6egwp;Gearp;Gep;Kep;Legopxbbbbbbbbbbbbbbbbp:2egqarpxbbbjbbbjbbbjbbbjgmp9op9rp;Kegrpxb;:FSb;:FSb;:FSb;:FSararp;Meaoaop;Meawaqawamp9op9rp;Kegrarp;Mep;Kep;Kep;Jep;Negwp;Mepxbbn0bbn0bbn0bbn0gqp;KepxFFbbFFbbFFbbFFbbp9oaoawp;Meaqp;Keczp:Rep9qgoarawp;Meaqp;KepxFFbbFFbbFFbbFFbbp9ogrpmwDKYqk8AExm35Ps8E8Fp9qpkbbadaDakp9oaoarpmbezHdiOAlvCXorQLp9qpkbbadcafhdavclfgval6mbkkalaeSmbaiaeciGgvcitgdfcbcaad9R;8kbaiabalcitfglad;8qbbdnavTmbaiaipblzgopxbbbbbbFFbbbbbbFFgkp9oaipblbgDaopmbediwDqkzHOAKY8AEgwczp:Reczp:Sep;6egraDaopmlvorxmPsCXQL358E8FpxFubbFubbFubbFubbp9op;6eawczp:Sep;6egwp;Gearp;Gep;Kep;Legopxbbbbbbbbbbbbbbbbp:2egqarpxbbbjbbbjbbbjbbbjgmp9op9rp;Kegrpxb;:FSb;:FSb;:FSb;:FSararp;Meaoaop;Meawaqawamp9op9rp;Kegrarp;Mep;Kep;Kep;Jep;Negwp;Mepxbbn0bbn0bbn0bbn0gqp;KepxFFbbFFbbFFbbFFbbp9oaoawp;Meaqp;Keczp:Rep9qgoarawp;Meaqp;KepxFFbbFFbbFFbbFFbbp9ogrpmwDKYqk8AExm35Ps8E8Fp9qpklzaiaDakp9oaoarpmbezHdiOAlvCXorQLp9qpklbkalaiad;8qbbkk;4wllue97euv978Jjjjjbc8W9Rhidnaec98GglTmbcbhvabhoinaiaopbbbgraoczfgwpbbbgDpmlvorxmPsCXQL358E8Fgqczp:Segkclp:RepklbaopxbbjZbbjZbbjZbbjZpx;Zl81Z;Zl81Z;Zl81Z;Zl81Zakpxibbbibbbibbbibbbp9qp;6ep;NegkaraDpmbediwDqkzHOAKY8AEgrczp:Reczp:Sep;6ep;MegDaDp;Meakarczp:Sep;6ep;Megxaxp;Meakaqczp:Reczp:Sep;6ep;Megqaqp;Mep;Kep;Kep;Lepxbbbbbbbbbbbbbbbbp:4ep;Jepxb;:FSb;:FSb;:FSb;:FSgkp;Mepxbbn0bbn0bbn0bbn0grp;KepxFFbbFFbbFFbbFFbbgmp9oaxakp;Mearp;Keczp:Rep9qgxaDakp;Mearp;Keamp9oaqakp;Mearp;Keczp:Rep9qgkpmbezHdiOAlvCXorQLgrp5baipblbpEb:T:j83ibaocwfarp5eaipblbpEe:T:j83ibawaxakpmwDKYqk8AExm35Ps8E8Fgkp5baipblbpEd:T:j83ibaocKfakp5eaipblbpEi:T:j83ibaocafhoavclfgval6mbkkdnalaeSmbaiaeciGgvcitgofcbcaao9R;8kbaiabalcitfgwao;8qbbdnavTmbaiaipblbgraipblzgDpmlvorxmPsCXQL358E8Fgqczp:Segkclp:RepklaaipxbbjZbbjZbbjZbbjZpx;Zl81Z;Zl81Z;Zl81Z;Zl81Zakpxibbbibbbibbbibbbp9qp;6ep;NegkaraDpmbediwDqkzHOAKY8AEgrczp:Reczp:Sep;6ep;MegDaDp;Meakarczp:Sep;6ep;Megxaxp;Meakaqczp:Reczp:Sep;6ep;Megqaqp;Mep;Kep;Kep;Lepxbbbbbbbbbbbbbbbbp:4ep;Jepxb;:FSb;:FSb;:FSb;:FSgkp;Mepxbbn0bbn0bbn0bbn0grp;KepxFFbbFFbbFFbbFFbbgmp9oaxakp;Mearp;Keczp:Rep9qgxaDakp;Mearp;Keamp9oaqakp;Mearp;Keczp:Rep9qgkpmbezHdiOAlvCXorQLgrp5baipblapEb:T:j83ibaiarp5eaipblapEe:T:j83iwaiaxakpmwDKYqk8AExm35Ps8E8Fgkp5baipblapEd:T:j83izaiakp5eaipblapEi:T:j83iKkawaiao;8qbbkk:Pddiue978Jjjjjbc;ab9Rhidnadcd4ae2glc98GgvTmbcbheabhdinadadpbbbgocwp:Recwp:Sep;6eaocep:SepxbbjFbbjFbbjFbbjFp9opxbbjZbbjZbbjZbbjZp:Uep;Mepkbbadczfhdaeclfgeav6mbkkdnavalSmbaialciGgecdtgdVcbc;abad9R;8kbaiabavcdtfgvad;8qbbdnaeTmbaiaipblbgocwp:Recwp:Sep;6eaocep:SepxbbjFbbjFbbjFbbjFp9opxbbjZbbjZbbjZbbjZp:Uep;Mepklbkavaiad;8qbbkk9teiucbcbydj1jjbgeabcifc98GfgbBdj1jjbdndnabZbcztgd9nmbcuhiabad9RcFFifcz4nbcuSmekaehikaikkkebcjwklz:Dbb",t=new Uint8Array([0,97,115,109,1,0,0,0,1,4,1,96,0,0,3,3,2,0,0,5,3,1,0,1,12,1,0,10,22,2,12,0,65,0,65,0,65,0,252,10,0,0,11,7,0,65,0,253,15,26,11]),n=new Uint8Array([32,0,65,2,1,106,34,33,3,128,11,4,13,64,6,253,10,7,15,116,127,5,8,12,40,16,19,54,20,9,27,255,113,17,42,67,24,23,146,148,18,14,22,45,70,69,56,114,101,21,25,63,75,136,108,28,118,29,73,115]);if(typeof WebAssembly!="object")return{supported:!1};var i=WebAssembly.validate(t)?o(e):o(s),r,a=WebAssembly.instantiate(i,{}).then(function(p){r=p.instance,r.exports.__wasm_call_ctors()});function o(p){for(var x=new Uint8Array(p.length),v=0;v<p.length;++v){var b=p.charCodeAt(v);x[v]=b>96?b-97:b>64?b-39:b+4}for(var S=0,v=0;v<p.length;++v)x[S++]=x[v]<60?n[x[v]]:(x[v]-60)*64+x[++v];return x.buffer.slice(0,S)}function c(p,x,v,b,S,w,T){var A=p.exports.sbrk,M=b+3&-4,_=A(M*S),I=A(w.length),C=new Uint8Array(p.exports.memory.buffer);C.set(w,I);var D=x(_,b,S,I,w.length);if(D==0&&T&&T(_,M,S),v.set(C.subarray(_,_+b*S)),A(_-A(0)),D!=0)throw new Error("Malformed buffer data: "+D)}var l={NONE:"",OCTAHEDRAL:"meshopt_decodeFilterOct",QUATERNION:"meshopt_decodeFilterQuat",EXPONENTIAL:"meshopt_decodeFilterExp"},u={ATTRIBUTES:"meshopt_decodeVertexBuffer",TRIANGLES:"meshopt_decodeIndexBuffer",INDICES:"meshopt_decodeIndexSequence"},h=[],d=0;function f(p){var x={object:new Worker(p),pending:0,requests:{}};return x.object.onmessage=function(v){var b=v.data;x.pending-=b.count,x.requests[b.id][b.action](b.value),delete x.requests[b.id]},x}function g(p){for(var x="self.ready = WebAssembly.instantiate(new Uint8Array(["+new Uint8Array(i)+"]), {}).then(function(result) { result.instance.exports.__wasm_call_ctors(); return result.instance; });self.onmessage = "+m.name+";"+c.toString()+m.toString(),v=new Blob([x],{type:"text/javascript"}),b=URL.createObjectURL(v),S=h.length;S<p;++S)h[S]=f(b);for(var S=p;S<h.length;++S)h[S].object.postMessage({});h.length=p,URL.revokeObjectURL(b)}function y(p,x,v,b,S){for(var w=h[0],T=1;T<h.length;++T)h[T].pending<w.pending&&(w=h[T]);return new Promise(function(A,M){var _=new Uint8Array(v),I=++d;w.pending+=p,w.requests[I]={resolve:A,reject:M},w.object.postMessage({id:I,count:p,size:x,source:_,mode:b,filter:S},[_.buffer])})}function m(p){var x=p.data;if(!x.id)return self.close();self.ready.then(function(v){try{var b=new Uint8Array(x.count*x.size);c(v,v.exports[x.mode],b,x.count,x.size,x.source,v.exports[x.filter]),self.postMessage({id:x.id,count:x.count,action:"resolve",value:b},[b.buffer])}catch(S){self.postMessage({id:x.id,count:x.count,action:"reject",value:S})}})}return{ready:a,supported:!0,useWorkers:function(p){g(p)},decodeVertexBuffer:function(p,x,v,b,S){c(r,r.exports.meshopt_decodeVertexBuffer,p,x,v,b,r.exports[l[S]])},decodeIndexBuffer:function(p,x,v,b){c(r,r.exports.meshopt_decodeIndexBuffer,p,x,v,b)},decodeIndexSequence:function(p,x,v,b){c(r,r.exports.meshopt_decodeIndexSequence,p,x,v,b)},decodeGltfBuffer:function(p,x,v,b,S,w){c(r,r.exports[u[S]],p,x,v,b,r.exports[l[w]])},decodeGltfBufferAsync:function(p,x,v,b,S){return h.length>0?y(p,x,v,u[b],l[S]):a.then(function(){var w=new Uint8Array(p*x);return c(r,r.exports[u[b]],w,p,x,v,r.exports[l[S]]),w})}}})();var wr=class s extends at{constructor(){let e=s.SkyShader,t=new Yt({name:e.name,uniforms:Fc.clone(e.uniforms),vertexShader:e.vertexShader,fragmentShader:e.fragmentShader,side:Dt,depthWrite:!1});super(new Xn(1,1,1),t),this.isSky=!0}};wr.SkyShader={name:"SkyShader",uniforms:{turbidity:{value:2},rayleigh:{value:1},mieCoefficient:{value:.005},mieDirectionalG:{value:.8},sunPosition:{value:new L},up:{value:new L(0,1,0)}},vertexShader:`
		uniform vec3 sunPosition;
		uniform float rayleigh;
		uniform float turbidity;
		uniform float mieCoefficient;
		uniform vec3 up;

		varying vec3 vWorldPosition;
		varying vec3 vSunDirection;
		varying float vSunfade;
		varying vec3 vBetaR;
		varying vec3 vBetaM;
		varying float vSunE;

		// constants for atmospheric scattering
		const float e = 2.71828182845904523536028747135266249775724709369995957;
		const float pi = 3.141592653589793238462643383279502884197169;

		// wavelength of used primaries, according to preetham
		const vec3 lambda = vec3( 680E-9, 550E-9, 450E-9 );
		// this pre-calculation replaces older TotalRayleigh(vec3 lambda) function:
		// (8.0 * pow(pi, 3.0) * pow(pow(n, 2.0) - 1.0, 2.0) * (6.0 + 3.0 * pn)) / (3.0 * N * pow(lambda, vec3(4.0)) * (6.0 - 7.0 * pn))
		const vec3 totalRayleigh = vec3( 5.804542996261093E-6, 1.3562911419845635E-5, 3.0265902468824876E-5 );

		// mie stuff
		// K coefficient for the primaries
		const float v = 4.0;
		const vec3 K = vec3( 0.686, 0.678, 0.666 );
		// MieConst = pi * pow( ( 2.0 * pi ) / lambda, vec3( v - 2.0 ) ) * K
		const vec3 MieConst = vec3( 1.8399918514433978E14, 2.7798023919660528E14, 4.0790479543861094E14 );

		// earth shadow hack
		// cutoffAngle = pi / 1.95;
		const float cutoffAngle = 1.6110731556870734;
		const float steepness = 1.5;
		const float EE = 1000.0;

		float sunIntensity( float zenithAngleCos ) {
			zenithAngleCos = clamp( zenithAngleCos, -1.0, 1.0 );
			return EE * max( 0.0, 1.0 - pow( e, -( ( cutoffAngle - acos( zenithAngleCos ) ) / steepness ) ) );
		}

		vec3 totalMie( float T ) {
			float c = ( 0.2 * T ) * 10E-18;
			return 0.434 * c * MieConst;
		}

		void main() {

			vec4 worldPosition = modelMatrix * vec4( position, 1.0 );
			vWorldPosition = worldPosition.xyz;

			gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );
			gl_Position.z = gl_Position.w; // set z to camera.far

			vSunDirection = normalize( sunPosition );

			vSunE = sunIntensity( dot( vSunDirection, up ) );

			vSunfade = 1.0 - clamp( 1.0 - exp( ( sunPosition.y / 450000.0 ) ), 0.0, 1.0 );

			float rayleighCoefficient = rayleigh - ( 1.0 * ( 1.0 - vSunfade ) );

			// extinction (absorption + out scattering)
			// rayleigh coefficients
			vBetaR = totalRayleigh * rayleighCoefficient;

			// mie coefficients
			vBetaM = totalMie( turbidity ) * mieCoefficient;

		}`,fragmentShader:`
		varying vec3 vWorldPosition;
		varying vec3 vSunDirection;
		varying float vSunfade;
		varying vec3 vBetaR;
		varying vec3 vBetaM;
		varying float vSunE;

		uniform float mieDirectionalG;
		uniform vec3 up;

		// constants for atmospheric scattering
		const float pi = 3.141592653589793238462643383279502884197169;

		const float n = 1.0003; // refractive index of air
		const float N = 2.545E25; // number of molecules per unit volume for air at 288.15K and 1013mb (sea level -45 celsius)

		// optical length at zenith for molecules
		const float rayleighZenithLength = 8.4E3;
		const float mieZenithLength = 1.25E3;
		// 66 arc seconds -> degrees, and the cosine of that
		const float sunAngularDiameterCos = 0.999956676946448443553574619906976478926848692873900859324;

		// 3.0 / ( 16.0 * pi )
		const float THREE_OVER_SIXTEENPI = 0.05968310365946075;
		// 1.0 / ( 4.0 * pi )
		const float ONE_OVER_FOURPI = 0.07957747154594767;

		float rayleighPhase( float cosTheta ) {
			return THREE_OVER_SIXTEENPI * ( 1.0 + pow( cosTheta, 2.0 ) );
		}

		float hgPhase( float cosTheta, float g ) {
			float g2 = pow( g, 2.0 );
			float inverse = 1.0 / pow( 1.0 - 2.0 * g * cosTheta + g2, 1.5 );
			return ONE_OVER_FOURPI * ( ( 1.0 - g2 ) * inverse );
		}

		void main() {

			vec3 direction = normalize( vWorldPosition - cameraPosition );

			// optical length
			// cutoff angle at 90 to avoid singularity in next formula.
			float zenithAngle = acos( max( 0.0, dot( up, direction ) ) );
			float inverse = 1.0 / ( cos( zenithAngle ) + 0.15 * pow( 93.885 - ( ( zenithAngle * 180.0 ) / pi ), -1.253 ) );
			float sR = rayleighZenithLength * inverse;
			float sM = mieZenithLength * inverse;

			// combined extinction factor
			vec3 Fex = exp( -( vBetaR * sR + vBetaM * sM ) );

			// in scattering
			float cosTheta = dot( direction, vSunDirection );

			float rPhase = rayleighPhase( cosTheta * 0.5 + 0.5 );
			vec3 betaRTheta = vBetaR * rPhase;

			float mPhase = hgPhase( cosTheta, mieDirectionalG );
			vec3 betaMTheta = vBetaM * mPhase;

			vec3 Lin = pow( vSunE * ( ( betaRTheta + betaMTheta ) / ( vBetaR + vBetaM ) ) * ( 1.0 - Fex ), vec3( 1.5 ) );
			Lin *= mix( vec3( 1.0 ), pow( vSunE * ( ( betaRTheta + betaMTheta ) / ( vBetaR + vBetaM ) ) * Fex, vec3( 1.0 / 2.0 ) ), clamp( pow( 1.0 - dot( up, vSunDirection ), 5.0 ), 0.0, 1.0 ) );

			// nightsky
			float theta = acos( direction.y ); // elevation --> y-axis, [-pi/2, pi/2]
			float phi = atan( direction.z, direction.x ); // azimuth --> x-axis [-pi/2, pi/2]
			vec2 uv = vec2( phi, theta ) / vec2( 2.0 * pi, pi ) + vec2( 0.5, 0.0 );
			vec3 L0 = vec3( 0.1 ) * Fex;

			// composition + solar disc
			float sundisk = smoothstep( sunAngularDiameterCos, sunAngularDiameterCos + 0.00002, cosTheta );
			L0 += ( vSunE * 19000.0 * Fex ) * sundisk;

			vec3 texColor = ( Lin + L0 ) * 0.04 + vec3( 0.0, 0.0003, 0.00075 );

			vec3 retColor = pow( texColor, vec3( 1.0 / ( 1.2 + ( 1.2 * vSunfade ) ) ) );

			gl_FragColor = vec4( retColor, 1.0 );

			#include <tonemapping_fragment>
			#include <colorspace_fragment>

		}`};var Mr=Math.pow(2,-24),La=Symbol("SKIP_GENERATION"),Yc={strategy:0,maxDepth:40,targetLeafSize:10,useSharedArrayBuffer:!1,setBoundingBox:!0,onProgress:null,indirect:!1,verbose:!0,range:null,[La]:!1};function vt(s,e,t){return t.min.x=e[s],t.min.y=e[s+1],t.min.z=e[s+2],t.max.x=e[s+3],t.max.y=e[s+4],t.max.z=e[s+5],t}function Da(s){let e=-1,t=-1/0;for(let n=0;n<3;n++){let i=s[n+3]-s[n];i>t&&(t=i,e=n)}return e}function vu(s,e,t){for(let n=0;n<3;n++){let i=e[s+2*n],r=e[s+2*n+1],a=i-r,o=i+r;a<t[n]&&(t[n]=a),o>t[n+3]&&(t[n+3]=o)}}function Xc(s){let e=s[3]-s[0],t=s[4]-s[1],n=s[5]-s[2];return 2*(e*t+t*n+n*e)}function it(s,e){return e[s+15]===65535}function dt(s,e){return e[s+6]}function gt(s,e){return e[s+14]}function ct(s){return s+8}function lt(s,e){let t=e[s+6];return s+t*8}function Sr(s,e){return e[s+7]}function qc(s,e,t,n,i){let r=1/0,a=1/0,o=1/0,c=-1/0,l=-1/0,u=-1/0,h=1/0,d=1/0,f=1/0,g=-1/0,y=-1/0,m=-1/0,p=s.offset||0;for(let x=(e-p)*6,v=(e+t-p)*6;x<v;x+=6){let b=s[x+0],S=s[x+1],w=b-S,T=b+S;w<r&&(r=w),T>c&&(c=T),b<h&&(h=b),b>g&&(g=b);let A=s[x+2],M=s[x+3],_=A-M,I=A+M;_<a&&(a=_),I>l&&(l=I),A<d&&(d=A),A>y&&(y=A);let C=s[x+4],D=s[x+5],N=C-D,U=C+D;N<o&&(o=N),U>u&&(u=U),C<f&&(f=C),C>m&&(m=C)}n[0]=r,n[1]=a,n[2]=o,n[3]=c,n[4]=l,n[5]=u,i[0]=h,i[1]=d,i[2]=f,i[3]=g,i[4]=y,i[5]=m}var li=8,wu=8,_u=new Int32Array(li),ci=new Float32Array(li*6),Tr=new Float32Array(li*6),Kn=new Float32Array(6),jc=new Float32Array(6),Vi=new Int32Array(wu),xp=new Float32Array(wu*6);function Av(s,e,t,n){for(let i=0;i<3;i++){let r=e[s+2*i],a=e[s+2*i+1],o=r-a,c=r+a;o<t[n+i]&&(t[n+i]=o),c>t[n+i+3]&&(t[n+i+3]=c)}}function vp(s,e){let t=s[e+3]-s[e],n=s[e+4]-s[e+1],i=s[e+5]-s[e+2];return 2*(t*n+n*i+i*t)}function _p(s,e,t,n,i,r){let a=-1,o=0;if(r===0)a=Da(e),a!==-1&&(o=(e[a]+e[a+3])/2);else if(r===1)a=Da(s),a!==-1&&(o=Rv(t,n,i,a));else if(r===2){let c=Xc(s),l=1.25*i,u=t.offset||0,h=(n-u)*6,d=(n+i-u)*6;for(let f=0;f<3;f++){let g=e[f],p=(e[f+3]-g)/li;if(i<wu){for(let x=0;x<i;x++){let v=h+x*6,b=t[v+2*f],S=x;for(;S>0&&t[Vi[S-1]+2*f]>b;)Vi[S]=Vi[S-1],S--;Vi[S]=v}for(let x=0;x<3;x++)Kn[x]=1/0,Kn[x+3]=-1/0,jc[x]=1/0,jc[x+3]=-1/0;for(let x=i-1;x>=0;x--)vu(Vi[x],t,jc),xp.set(jc,x*6);for(let x=0;x<i-1;x++){vu(Vi[x],t,Kn);let v=t[Vi[x+1]+2*f];if(t[Vi[x]+2*f]===v)continue;let b=x+1,S=i-b,w=Xc(Kn)/c,T=vp(xp,b*6)/c,A=1+1.25*(w*b+T*S);A<l&&(a=f,l=A,o=v)}}else{for(let b=0;b<li;b++){_u[b]=0;for(let S=0;S<3;S++)ci[b*6+S]=1/0,ci[b*6+S+3]=-1/0}for(let b=h;b<d;b+=6){let T=~~((t[b+2*f]-g)/p);T>=li&&(T=li-1),_u[T]++,Av(b,t,ci,T*6)}let x=(li-1)*6;for(let b=0;b<6;b++)Tr[x+b]=ci[x+b];for(let b=li-2;b>=0;b--){let S=b*6,w=S+6;for(let T=0;T<3;T++)Tr[S+T]=Math.min(ci[S+T],Tr[w+T]),Tr[S+T+3]=Math.max(ci[S+T+3],Tr[w+T+3])}let v=0;for(let b=0;b<li-1;b++){let S=b*6,w=_u[b];if(w!==0)for(let I=0;I<3;I++)v===0?(Kn[I]=ci[S+I],Kn[I+3]=ci[S+I+3]):(Kn[I]=Math.min(Kn[I],ci[S+I]),Kn[I+3]=Math.max(Kn[I+3],ci[S+I+3]));v+=w;let T=0,A=0;v!==0&&(T=Xc(Kn)/c);let M=i-v;M!==0&&(A=vp(Tr,S+6)/c);let _=1+1.25*(T*v+A*M);_<l&&(a=f,l=_,o=g+p+b*p)}}}}else console.warn(`BVH: Invalid build strategy value ${r} used.`);return{axis:a,pos:o}}function Rv(s,e,t,n){let i=0,r=s.offset;for(let a=e,o=e+t;a<o;a++)i+=s[(a-r)*6+n*2];return i/t}function wp(s,e,t,n,i,r){let a=n,o=n+i-1,c=r.pos,l=r.axis*2,u=t.offset||0;for(;;){for(;a<=o&&t[(a-u)*6+l]<c;)a++;for(;a<=o&&t[(o-u)*6+l]>=c;)o--;if(a<o){for(let h=0;h<e;h++){let d=s[a*e+h];s[a*e+h]=s[o*e+h],s[o*e+h]=d}for(let h=0;h<6;h++){let d=a-u,f=o-u,g=t[d*6+h];t[d*6+h]=t[f*6+h],t[f*6+h]=g}a++,o--}else return a}}var Cv=Math.pow(2,32),Er=new Float32Array(6),Kc=new Float32Array(6);function Iv(s,e,t,n,i,r){let{maxDepth:a,verbose:o,targetLeafSize:c,_strictLeafSize:l=1/0,strategy:u,onProgress:h,useSharedArrayBuffer:d=!1}=i,f=s.primitiveBuffer,g=s.primitiveBufferStride,y=d?SharedArrayBuffer:ArrayBuffer,m=new y(32*Math.max(1,2*Math.ceil(n)-1)),p=new Float32Array(m),x=new Uint32Array(m),v=new Uint16Array(m),b=0,S=!1;return qc(e,t,n,Er,Kc),A(t,n,0),m.slice(0,b*32);function w(M){h&&h((M-r.offset)/r.count)}function T(M,_,I){let C=M*2;x[M+6]=_,v[C+14]=I,v[C+15]=65535,w(_+I)}function A(M,_,I){let C=b++,D=C*8;p.set(Er,D),!S&&I>=a&&(S=!0,o&&console.warn(`BVH: Max depth of ${a} reached when generating BVH. Consider increasing maxDepth.`));let N=_>l;if(_<=c&&!N||I>=a){T(D,M,_);return}let U=_p(Er,Kc,e,M,_,u),B=U.axis===-1?-1:wp(f,g,e,M,_,U);if(U.axis===-1||B===M||B===M+_){if(!N){T(D,M,_);return}U.axis=Math.max(0,Da(Er)),B=M+Math.max(1,Math.floor(_/2))}x[D+7]=U.axis;let J=B-M;qc(e,M,J,Er,Kc),A(M,J,I+1);let V=b-C;if(V>Cv)throw new Error("MeshBVH: Cannot store relative child node offset greater than 32 bits.");x[D+6]=V;let ne=_-J;qc(e,B,ne,Er,Kc),A(B,ne,I+1)}}function Mp(s,e){let t=s.getRootRanges(e.range),n=t[0],i=t[t.length-1],r={offset:n.offset,count:i.offset+i.count-n.offset},a=new Float32Array(6*r.count);a.offset=r.offset,s.computePrimitiveBounds(r.offset,r.count,a),s._roots=t.map(o=>Iv(s,a,o.offset,o.count,e,r))}var Gi=class{constructor(e){this._getNewPrimitive=e,this._primitives=[]}getPrimitive(){let e=this._primitives;return e.length===0?this._getNewPrimitive():e.pop()}releasePrimitive(e){this._primitives.push(e)}};var Mu=class{constructor(){this.float32Array=null,this.uint16Array=null,this.uint32Array=null;let e=[],t=null;this.setBuffer=n=>{t&&e.push(t),t=n,this.float32Array=new Float32Array(n),this.uint16Array=new Uint16Array(n),this.uint32Array=new Uint32Array(n)},this.clearBuffer=()=>{t=null,this.float32Array=null,this.uint16Array=null,this.uint32Array=null,e.length!==0&&this.setBuffer(e.pop())}}},Je=new Mu;var Wi,Rr,Ar=[],Zc=new Gi(()=>new ot);function Sp(s,e,t,n,i,r){Wi=Zc.getPrimitive(),Rr=Zc.getPrimitive(),Ar.push(Wi,Rr),Je.setBuffer(s._roots[e]);let a=Su(0,s.geometry,t,n,i,r);Je.clearBuffer(),Zc.releasePrimitive(Wi),Zc.releasePrimitive(Rr),Ar.pop(),Ar.pop();let o=Ar.length;return o>0&&(Rr=Ar[o-1],Wi=Ar[o-2]),a}function Su(s,e,t,n,i=null,r=0,a=0){let{float32Array:o,uint16Array:c,uint32Array:l}=Je,u=s*2;if(it(u,c)){let d=dt(s,l),f=gt(u,c);return vt(s,o,Wi),n(d,f,!1,a,r+s/8,Wi)}else{let _=function(C){let{uint16Array:D,uint32Array:N}=Je,U=C*2;for(;!it(U,D);)C=ct(C),U=C*2;return dt(C,N)},I=function(C){let{uint16Array:D,uint32Array:N}=Je,U=C*2;for(;!it(U,D);)C=lt(C,N),U=C*2;return dt(C,N)+gt(U,D)},d=ct(s),f=lt(s,l),g=d,y=f,m,p,x,v;if(i&&(x=Wi,v=Rr,vt(g,o,x),vt(y,o,v),m=i(x),p=i(v),p<m)){g=f,y=d;let C=m;m=p,p=C,x=v}x||(x=Wi,vt(g,o,x));let b=it(g*2,c),S=t(x,b,m,a+1,r+g/8),w;if(S===2){let C=_(g),N=I(g)-C;w=n(C,N,!0,a+1,r+g/8,x)}else w=S&&Su(g,e,t,n,i,r,a+1);if(w)return!0;v=Rr,vt(y,o,v);let T=it(y*2,c),A=t(v,T,p,a+1,r+y/8),M;if(A===2){let C=_(y),N=I(y)-C;M=n(C,N,!0,a+1,r+y/8,v)}else M=A&&Su(y,e,t,n,i,r,a+1);return!!M}}var Na=new Je.constructor,Jc=new Je.constructor,Yi=new Gi(()=>new ot),Cr=new ot,Ir=new ot,Eu=new ot,Au=new ot,Ru=!1;function Tp(s,e,t,n){if(Ru)throw new Error("MeshBVH: Recursive calls to bvhcast not supported.");Ru=!0;let i=s._roots,r=e._roots,a,o=0,c=0,l=new ke().copy(t).invert();for(let u=0,h=i.length;u<h;u++){Na.setBuffer(i[u]),c=0;let d=Yi.getPrimitive();vt(0,Na.float32Array,d),d.applyMatrix4(l);for(let f=0,g=r.length;f<g&&(Jc.setBuffer(r[f]),a=Zn(0,0,t,l,n,o,c,0,0,d),Jc.clearBuffer(),c+=r[f].byteLength/32,!a);f++);if(Yi.releasePrimitive(d),Na.clearBuffer(),o+=i[u].byteLength/32,a)break}return Ru=!1,a}function Zn(s,e,t,n,i,r=0,a=0,o=0,c=0,l=null,u=!1){let h,d;u?(h=Jc,d=Na):(h=Na,d=Jc);let f=h.float32Array,g=h.uint32Array,y=h.uint16Array,m=d.float32Array,p=d.uint32Array,x=d.uint16Array,v=s*2,b=e*2,S=it(v,y),w=it(b,x),T=!1;if(w&&S)u?T=i(dt(e,p),gt(e*2,x),dt(s,g),gt(s*2,y),c,a+e/8,o,r+s/8):T=i(dt(s,g),gt(s*2,y),dt(e,p),gt(e*2,x),o,r+s/8,c,a+e/8);else if(w){let A=Yi.getPrimitive();vt(e,m,A),A.applyMatrix4(t);let M=ct(s),_=lt(s,g);vt(M,f,Cr),vt(_,f,Ir);let I=A.intersectsBox(Cr),C=A.intersectsBox(Ir);T=I&&Zn(e,M,n,t,i,a,r,c,o+1,A,!u)||C&&Zn(e,_,n,t,i,a,r,c,o+1,A,!u),Yi.releasePrimitive(A)}else{let A=ct(e),M=lt(e,p);vt(A,m,Eu),vt(M,m,Au);let _=l.intersectsBox(Eu),I=l.intersectsBox(Au);if(_&&I)T=Zn(s,A,t,n,i,r,a,o,c+1,l,u)||Zn(s,M,t,n,i,r,a,o,c+1,l,u);else if(_)if(S)T=Zn(s,A,t,n,i,r,a,o,c+1,l,u);else{let C=Yi.getPrimitive();C.copy(Eu).applyMatrix4(t);let D=ct(s),N=lt(s,g);vt(D,f,Cr),vt(N,f,Ir);let U=C.intersectsBox(Cr),B=C.intersectsBox(Ir);T=U&&Zn(A,D,n,t,i,a,r,c,o+1,C,!u)||B&&Zn(A,N,n,t,i,a,r,c,o+1,C,!u),Yi.releasePrimitive(C)}else if(I)if(S)T=Zn(s,M,t,n,i,r,a,o,c+1,l,u);else{let C=Yi.getPrimitive();C.copy(Au).applyMatrix4(t);let D=ct(s),N=lt(s,g);vt(D,f,Cr),vt(N,f,Ir);let U=C.intersectsBox(Cr),B=C.intersectsBox(Ir);T=U&&Zn(M,D,n,t,i,a,r,c,o+1,C,!u)||B&&Zn(M,N,n,t,i,a,r,c,o+1,C,!u),Yi.releasePrimitive(C)}}return T}var $c=new class{constructor(){let s=null,e=null,t=null,n=!1;this.root=null,this.buffer=null,this.uint32Array=null,this.uint16Array=null,this.setBVH=(r,a)=>{if(n)throw new Error("BVHTraversalHelper: cannot call setBVH during an active traversal.");this.root=a,this.buffer=s=r._roots[a],this.uint16Array=t=new Uint16Array(s),this.uint32Array=e=new Uint32Array(s)},this.reset=()=>{this.root=null,this.buffer=s=null,this.uint16Array=t=null,this.uint32Array=e=null},this.getRangeStart=r=>{let a=r*2;for(;!it(a,t);)r=ct(r),a=r*2;return dt(r,e)},this.getRangeEnd=r=>{let a=r*2;for(;!it(a,t);)r=lt(r,e),a=r*2;return dt(r,e)+gt(a,t)};let i=(r,a,o)=>{let c=a*2,l=it(c,t);if(!r(o,l,a)&&!l){let h=ct(a),d=lt(a,e);i(r,h,o+1),i(r,d,o+1)}};this.traverseBuffer=r=>{if(n)throw new Error("BVHTraversalHelper: cannot start a traversal during an active traversal.");n=!0;try{i(r,0,0)}finally{n=!1}},this.traverse=r=>{this.traverseBuffer((a,o,c)=>{if(o){let l=c*2,u=e[c+6],h=t[l+14];return r(a,o,new Float32Array(s,c*4,6),u,h)}else{let l=Sr(c,e);return r(a,o,new Float32Array(s,c*4,6),l)}})}}};var Ep=new ot,Pr=new Float32Array(6),Qc=class{constructor(){this._roots=null,this.primitiveBuffer=null,this.primitiveBufferStride=null}init(e){e={...Yc,...e},"maxLeafSize"in e&&(console.warn('BVH: "maxLeafSize" option has been deprecated. Use "targetLeafSize", instead.'),e={...e,targetLeafSize:e.maxLeafSize}),Mp(this,e)}getRootRanges(){throw new Error("BVH: getRootRanges() not implemented")}writePrimitiveBounds(){throw new Error("BVH: writePrimitiveBounds() not implemented")}writePrimitiveRangeBounds(e,t,n,i){let r=1/0,a=1/0,o=1/0,c=-1/0,l=-1/0,u=-1/0;for(let h=e,d=e+t;h<d;h++){this.writePrimitiveBounds(h,Pr,0);let[f,g,y,m,p,x]=Pr;f<r&&(r=f),m>c&&(c=m),g<a&&(a=g),p>l&&(l=p),y<o&&(o=y),x>u&&(u=x)}return n[i+0]=r,n[i+1]=a,n[i+2]=o,n[i+3]=c,n[i+4]=l,n[i+5]=u,n}computePrimitiveBounds(e,t,n){let i=n.offset||0;for(let r=e,a=e+t;r<a;r++){this.writePrimitiveBounds(r,Pr,0);let[o,c,l,u,h,d]=Pr,f=(o+u)/2,g=(c+h)/2,y=(l+d)/2,m=(u-o)/2,p=(h-c)/2,x=(d-l)/2,v=(r-i)*6;n[v+0]=f,n[v+1]=m+(Math.abs(f)+m)*Mr,n[v+2]=g,n[v+3]=p+(Math.abs(g)+p)*Mr,n[v+4]=y,n[v+5]=x+(Math.abs(y)+x)*Mr}return n}shiftPrimitiveOffsets(e){let t=this._indirectBuffer;if(t)for(let n=0,i=t.length;n<i;n++)t[n]+=e;else{let n=this._roots;for(let i=0;i<n.length;i++){let r=n[i],a=new Uint32Array(r),o=new Uint16Array(r),c=r.byteLength/32;for(let l=0;l<c;l++){let u=8*l,h=2*u;it(h,o)&&(a[u+6]+=e)}}}}traverse(e,t=0){$c.setBVH(this,t),$c.traverse(e),$c.reset()}refit(){let e=this._roots;for(let t=0,n=e.length;t<n;t++){let i=e[t],r=new Uint32Array(i),a=new Uint16Array(i),o=new Float32Array(i),c=i.byteLength/32;for(let l=c-1;l>=0;l--){let u=l*8,h=u*2;if(it(h,a)){let f=dt(u,r),g=gt(h,a);this.writePrimitiveRangeBounds(f,g,Pr,0),o.set(Pr,u)}else{let f=ct(u),g=lt(u,r);for(let y=0;y<3;y++){let m=o[f+y],p=o[f+y+3],x=o[g+y],v=o[g+y+3];o[u+y]=m<x?m:x,o[u+y+3]=p>v?p:v}}}}}getBoundingBox(e){return e.makeEmpty(),this._roots.forEach(n=>{vt(0,new Float32Array(n),Ep),e.union(Ep)}),e}shapecast(e){let{boundsTraverseOrder:t,intersectsBounds:n,intersectsRange:i,intersectsPrimitive:r,scratchPrimitive:a,iterate:o}=e;if(i&&r){let h=i;i=(d,f,g,y,m)=>h(d,f,g,y,m)?!0:o(d,f,this,r,g,y,a)}else i||(r?i=(h,d,f,g)=>o(h,d,this,r,f,g,a):i=(h,d,f)=>f);let c=!1,l=0,u=this._roots;for(let h=0,d=u.length;h<d;h++){let f=u[h];if(c=Sp(this,h,n,i,t,l),c)break;l+=f.byteLength/32}return c}bvhcast(e,t,n){let{intersectsRanges:i}=n;return Tp(this,e,t,i)}};function Ap(){return typeof SharedArrayBuffer<"u"}function Cu(s){return s.index?s.index.count:s.attributes.position.count}function Xi(s){return Cu(s)/3}function kv(s,e=ArrayBuffer){return s>65535?new Uint32Array(new e(4*s)):new Uint16Array(new e(2*s))}function Rp(s,e){if(!s.index){let t=s.attributes.position.count,n=e.useSharedArrayBuffer?SharedArrayBuffer:ArrayBuffer,i=kv(t,n);s.setIndex(new xt(i,1));for(let r=0;r<t;r++)i[r]=r}}function Lv(s,e,t){let n=Cu(s)/t,i=e||s.drawRange,r=i.start/t,a=(i.start+i.count)/t,o=Math.max(0,r),c=Math.min(n,a)-o;return{offset:Math.floor(o),count:Math.floor(c)}}function Dv(s,e){return s.groups.map(t=>({offset:t.start/e,count:t.count/e}))}function Iu(s,e,t){let n=Lv(s,e,t),i=Dv(s,t);if(!i.length)return[n];let r=[],a=n.offset,o=n.offset+n.count,c=Cu(s)/t,l=[];for(let d of i){let{offset:f,count:g}=d,y=f,m=isFinite(g)?g:c-f,p=f+m;y<o&&p>a&&(l.push({pos:Math.max(a,y),isStart:!0}),l.push({pos:Math.min(o,p),isStart:!1}))}l.sort((d,f)=>d.pos!==f.pos?d.pos-f.pos:d.type==="end"?-1:1);let u=0,h=null;for(let d of l){let f=d.pos;u!==0&&f!==h&&r.push({offset:h,count:f-h}),u+=d.isStart?1:-1,h=f}return r}function Nv(s,e){let t=s[s.length-1],n=t.offset+t.count>2**16,i=s.reduce((l,u)=>l+u.count,0),r=n?4:2,a=e?new SharedArrayBuffer(i*r):new ArrayBuffer(i*r),o=n?new Uint32Array(a):new Uint16Array(a),c=0;for(let l=0;l<s.length;l++){let{offset:u,count:h}=s[l];for(let d=0;d<h;d++)o[c+d]=u+d;c+=h}return o}var el=class extends Qc{get indirect(){return!!this._indirectBuffer}get primitiveStride(){return null}get primitiveBufferStride(){return this.indirect?1:this.primitiveStride}set primitiveBufferStride(e){}get primitiveBuffer(){return this.indirect?this._indirectBuffer:this.geometry.index.array}set primitiveBuffer(e){}constructor(e,t={}){if(e.isBufferGeometry){if(e.index&&e.index.isInterleavedBufferAttribute)throw new Error("BVH: InterleavedBufferAttribute is not supported for the index attribute.")}else throw new Error("BVH: Only BufferGeometries are supported.");if(t.useSharedArrayBuffer&&!Ap())throw new Error("BVH: SharedArrayBuffer is not available.");super(),this.geometry=e,this.resolvePrimitiveIndex=t.indirect?n=>this._indirectBuffer[n]:n=>n,this.primitiveBuffer=null,this.primitiveBufferStride=null,this._indirectBuffer=null,t={...Yc,...t},t[La]||this.init(t)}init(e){let{geometry:t,primitiveStride:n}=this;if(e.indirect){let i=Iu(t,e.range,n),r=Nv(i,e.useSharedArrayBuffer);this._indirectBuffer=r}else Rp(t,e);super.init(e),!t.boundingBox&&e.setBoundingBox&&(t.boundingBox=this.getBoundingBox(new ot))}getRootRanges(e){return this.indirect?[{offset:0,count:this._indirectBuffer.length}]:Iu(this.geometry,e,this.primitiveStride)}raycastObject3D(){throw new Error("BVH: raycastObject3D() not implemented")}};var An=class{constructor(){this.min=1/0,this.max=-1/0}setFromPointsField(e,t){let n=1/0,i=-1/0;for(let r=0,a=e.length;r<a;r++){let c=e[r][t];n=c<n?c:n,i=c>i?c:i}this.min=n,this.max=i}setFromPoints(e,t){let n=1/0,i=-1/0;for(let r=0,a=t.length;r<a;r++){let o=t[r],c=e.dot(o);n=c<n?c:n,i=c>i?c:i}this.min=n,this.max=i}isSeparated(e){return this.min>e.max||e.min>this.max}};An.prototype.setFromBox=(function(){let s=new L;return function(t,n){let i=n.min,r=n.max,a=1/0,o=-1/0;for(let c=0;c<=1;c++)for(let l=0;l<=1;l++)for(let u=0;u<=1;u++){s.x=i.x*c+r.x*(1-c),s.y=i.y*l+r.y*(1-l),s.z=i.z*u+r.z*(1-u);let h=t.dot(s);a=Math.min(h,a),o=Math.max(h,o)}this.min=a,this.max=o}})();var Fv=(function(){let s=new L,e=new L,t=new L;return function(i,r,a){let o=i.start,c=s,l=r.start,u=e;t.subVectors(o,l),s.subVectors(i.end,i.start),e.subVectors(r.end,r.start);let h=t.dot(u),d=u.dot(c),f=u.dot(u),g=t.dot(c),m=c.dot(c)*f-d*d,p,x;m!==0?p=(h*d-g*f)/m:p=0,x=(h+p*d)/f,a.x=p,a.y=x}})(),Fa=(function(){let s=new Ne,e=new L,t=new L;return function(i,r,a,o){Fv(i,r,s);let c=s.x,l=s.y;if(c>=0&&c<=1&&l>=0&&l<=1){i.at(c,a),r.at(l,o);return}else if(c>=0&&c<=1){l<0?r.at(0,o):r.at(1,o),i.closestPointToPoint(o,!0,a);return}else if(l>=0&&l<=1){c<0?i.at(0,a):i.at(1,a),r.closestPointToPoint(a,!0,o);return}else{let u;c<0?u=i.start:u=i.end;let h;l<0?h=r.start:h=r.end;let d=e,f=t;if(i.closestPointToPoint(h,!0,e),r.closestPointToPoint(u,!0,t),d.distanceToSquared(h)<=f.distanceToSquared(u)){a.copy(d),o.copy(h);return}else{a.copy(u),o.copy(f);return}}}})(),Cp=(function(){let s=new L,e=new L,t=new fn,n=new Zt;return function(r,a){let{radius:o,center:c}=r,{a:l,b:u,c:h}=a;if(n.start=l,n.end=u,n.closestPointToPoint(c,!0,s).distanceTo(c)<=o||(n.start=l,n.end=h,n.closestPointToPoint(c,!0,s).distanceTo(c)<=o)||(n.start=u,n.end=h,n.closestPointToPoint(c,!0,s).distanceTo(c)<=o))return!0;let y=a.getPlane(t);if(Math.abs(y.distanceToPoint(c))<=o){let p=y.projectPoint(c,e);if(a.containsPoint(p))return!0}return!1}})();var Uv=["x","y","z"],Ri=1e-15,Ip=Ri*Ri;function Bn(s){return Math.abs(s)<Ri}var Jt=class extends en{constructor(...e){super(...e),this.isExtendedTriangle=!0,this.satAxes=new Array(4).fill().map(()=>new L),this.satBounds=new Array(4).fill().map(()=>new An),this.points=[this.a,this.b,this.c],this.plane=new fn,this.isDegenerateIntoSegment=!1,this.isDegenerateIntoPoint=!1,this.degenerateSegment=new Zt,this.needsUpdate=!0}intersectsSphere(e){return Cp(e,this)}update(){let e=this.a,t=this.b,n=this.c,i=this.points,r=this.satAxes,a=this.satBounds,o=r[0],c=a[0];this.getNormal(o),c.setFromPoints(o,i);let l=r[1],u=a[1];l.subVectors(e,t),u.setFromPoints(l,i);let h=r[2],d=a[2];h.subVectors(t,n),d.setFromPoints(h,i);let f=r[3],g=a[3];f.subVectors(n,e),g.setFromPoints(f,i);let y=l.length(),m=h.length(),p=f.length();this.isDegenerateIntoPoint=!1,this.isDegenerateIntoSegment=!1,y<Ri?m<Ri||p<Ri?this.isDegenerateIntoPoint=!0:(this.isDegenerateIntoSegment=!0,this.degenerateSegment.start.copy(e),this.degenerateSegment.end.copy(n)):m<Ri?p<Ri?this.isDegenerateIntoPoint=!0:(this.isDegenerateIntoSegment=!0,this.degenerateSegment.start.copy(t),this.degenerateSegment.end.copy(e)):p<Ri&&(this.isDegenerateIntoSegment=!0,this.degenerateSegment.start.copy(n),this.degenerateSegment.end.copy(t)),this.plane.setFromNormalAndCoplanarPoint(o,e),this.needsUpdate=!1}};Jt.prototype.closestPointToSegment=(function(){let s=new L,e=new L,t=new Zt;return function(i,r=null,a=null){this.needsUpdate&&this.update();let{start:o,end:c}=i,l=this.points,u,h=1/0,d=this.plane.distanceToPoint(o),f=this.plane.distanceToPoint(c);if(d*f<0&&this.plane.intersectLine(i,s)!==null&&this.containsPoint(s))return r&&r.copy(s),a&&a.copy(s),0;for(let g=0;g<3;g++){let y=(g+1)%3;t.start.copy(l[g]),t.end.copy(l[y]),Fa(t,i,s,e),u=s.distanceToSquared(e),u<h&&(h=u,r&&r.copy(s),a&&a.copy(e))}return this.closestPointToPoint(o,s),u=o.distanceToSquared(s),u<h&&(h=u,r&&r.copy(s),a&&a.copy(o)),this.closestPointToPoint(c,s),u=c.distanceToSquared(s),u<h&&(h=u,r&&r.copy(s),a&&a.copy(c)),Math.sqrt(h)}})();Jt.prototype.intersectsTriangle=(function(){let s=new Jt,e=new An,t=new An,n=new L,i=new L,r=new L,a=new L,o=new Zt,c=new Zt,l=new L,u=new Ne,h=new Ne;function d(v,b,S,w){let T=n;!v.isDegenerateIntoPoint&&!v.isDegenerateIntoSegment?T.copy(v.plane.normal):T.copy(b.plane.normal);let A=v.satBounds,M=v.satAxes;for(let C=1;C<4;C++){let D=A[C],N=M[C];if(e.setFromPoints(N,b.points),D.isSeparated(e)||(a.copy(T).cross(N),e.setFromPoints(a,v.points),t.setFromPoints(a,b.points),e.isSeparated(t)))return!1}let _=b.satBounds,I=b.satAxes;for(let C=1;C<4;C++){let D=_[C],N=I[C];if(e.setFromPoints(N,v.points),D.isSeparated(e)||(a.crossVectors(T,N),e.setFromPoints(a,v.points),t.setFromPoints(a,b.points),e.isSeparated(t)))return!1}return S&&(w||console.warn("ExtendedTriangle.intersectsTriangle: Triangles are coplanar which does not support an output edge. Setting edge to 0, 0, 0."),S.start.set(0,0,0),S.end.set(0,0,0)),!0}function f(v,b,S,w,T,A,M,_,I,C,D){let N=M/(M-_);C.x=w+(T-w)*N,D.start.subVectors(b,v).multiplyScalar(N).add(v),N=M/(M-I),C.y=w+(A-w)*N,D.end.subVectors(S,v).multiplyScalar(N).add(v)}function g(v,b,S,w,T,A,M,_,I,C,D){if(T>0)f(v.c,v.a,v.b,w,b,S,I,M,_,C,D);else if(A>0)f(v.b,v.a,v.c,S,b,w,_,M,I,C,D);else if(_*I>0||M!=0)f(v.a,v.b,v.c,b,S,w,M,_,I,C,D);else if(_!=0)f(v.b,v.a,v.c,S,b,w,_,M,I,C,D);else if(I!=0)f(v.c,v.a,v.b,w,b,S,I,M,_,C,D);else return!0;return!1}function y(v,b,S,w){let T=b.degenerateSegment,A=v.plane.distanceToPoint(T.start),M=v.plane.distanceToPoint(T.end);return Bn(A)?Bn(M)?d(v,b,S,w):(S&&(S.start.copy(T.start),S.end.copy(T.start)),v.containsPoint(T.start)):Bn(M)?(S&&(S.start.copy(T.end),S.end.copy(T.end)),v.containsPoint(T.end)):v.plane.intersectLine(T,n)!=null?(S&&(S.start.copy(n),S.end.copy(n)),v.containsPoint(n)):!1}function m(v,b,S){let w=b.a;return Bn(v.plane.distanceToPoint(w))&&v.containsPoint(w)?(S&&(S.start.copy(w),S.end.copy(w)),!0):!1}function p(v,b,S){let w=v.degenerateSegment,T=b.a;return w.closestPointToPoint(T,!0,n),T.distanceToSquared(n)<Ip?(S&&(S.start.copy(T),S.end.copy(T)),!0):!1}function x(v,b,S,w){if(v.isDegenerateIntoSegment)if(b.isDegenerateIntoSegment){let T=v.degenerateSegment,A=b.degenerateSegment,M=i,_=r;T.delta(M),A.delta(_);let I=n.subVectors(A.start,T.start),C=M.x*_.y-M.y*_.x;if(Bn(C))return!1;let D=(I.x*_.y-I.y*_.x)/C,N=-(M.x*I.y-M.y*I.x)/C;if(D<0||D>1||N<0||N>1)return!1;let U=T.start.z+M.z*D,B=A.start.z+_.z*N;return Bn(U-B)?(S&&(S.start.copy(T.start).addScaledVector(M,D),S.end.copy(T.start).addScaledVector(M,D)),!0):!1}else return b.isDegenerateIntoPoint?p(v,b,S):y(b,v,S,w);else{if(v.isDegenerateIntoPoint)return b.isDegenerateIntoPoint?b.a.distanceToSquared(v.a)<Ip?(S&&(S.start.copy(v.a),S.end.copy(v.a)),!0):!1:b.isDegenerateIntoSegment?p(b,v,S):m(b,v,S);if(b.isDegenerateIntoPoint)return m(v,b,S);if(b.isDegenerateIntoSegment)return y(v,b,S,w)}}return function(b,S=null,w=!1){this.needsUpdate&&this.update(),b.isExtendedTriangle?b.needsUpdate&&b.update():(s.copy(b),s.update(),b=s);let T=x(this,b,S,w);if(T!==void 0)return T;let A=this.plane,M=b.plane,_=M.distanceToPoint(this.a),I=M.distanceToPoint(this.b),C=M.distanceToPoint(this.c);Bn(_)&&(_=0),Bn(I)&&(I=0),Bn(C)&&(C=0);let D=_*I,N=_*C;if(D>0&&N>0)return!1;let U=A.distanceToPoint(b.a),B=A.distanceToPoint(b.b),J=A.distanceToPoint(b.c);Bn(U)&&(U=0),Bn(B)&&(B=0),Bn(J)&&(J=0);let V=U*B,ne=U*J;if(V>0&&ne>0)return!1;i.copy(A.normal),r.copy(M.normal);let ue=i.cross(r),_e=0,ze=Math.abs(ue.x),$e=Math.abs(ue.y);$e>ze&&(ze=$e,_e=1),Math.abs(ue.z)>ze&&(_e=2);let Ye=Uv[_e],Q=this.a[Ye],te=this.b[Ye],ve=this.c[Ye],Fe=b.a[Ye],Se=b.b[Ye],je=b.c[Ye];if(g(this,Q,te,ve,D,N,_,I,C,u,o))return d(this,b,S,w);if(g(b,Fe,Se,je,V,ne,U,B,J,h,c))return d(this,b,S,w);if(u.y<u.x){let Z=u.y;u.y=u.x,u.x=Z,l.copy(o.start),o.start.copy(o.end),o.end.copy(l)}if(h.y<h.x){let Z=h.y;h.y=h.x,h.x=Z,l.copy(c.start),c.start.copy(c.end),c.end.copy(l)}return u.y<h.x||h.y<u.x?!1:(S&&(h.x>u.x?S.start.copy(c.start):S.start.copy(o.start),h.y<u.y?S.end.copy(c.end):S.end.copy(o.end)),!0)}})();Jt.prototype.distanceToPoint=(function(){let s=new L;return function(t){return this.closestPointToPoint(t,s),t.distanceTo(s)}})();Jt.prototype.distanceToTriangle=(function(){let s=new L,e=new L,t=["a","b","c"],n=new Zt,i=new Zt;return function(a,o=null,c=null){let l=o||c?n:null;if(this.intersectsTriangle(a,l,!0))return(o||c)&&(o&&l.getCenter(o),c&&l.getCenter(c)),0;let u=1/0;for(let h=0;h<3;h++){let d,f=t[h],g=a[f];this.closestPointToPoint(g,s),d=g.distanceToSquared(s),d<u&&(u=d,o&&o.copy(s),c&&c.copy(g));let y=this[f];a.closestPointToPoint(y,s),d=y.distanceToSquared(s),d<u&&(u=d,o&&o.copy(y),c&&c.copy(s))}for(let h=0;h<3;h++){let d=t[h],f=t[(h+1)%3];n.set(this[d],this[f]);for(let g=0;g<3;g++){let y=t[g],m=t[(g+1)%3];i.set(a[y],a[m]),Fa(n,i,s,e);let p=s.distanceToSquared(e);p<u&&(u=p,o&&o.copy(s),c&&c.copy(e))}}return Math.sqrt(u)}})();var Pt=class{constructor(e,t,n){this.isOrientedBox=!0,this.min=new L,this.max=new L,this.matrix=new ke,this.invMatrix=new ke,this.points=new Array(8).fill().map(()=>new L),this.satAxes=new Array(3).fill().map(()=>new L),this.satBounds=new Array(3).fill().map(()=>new An),this.alignedSatBounds=new Array(3).fill().map(()=>new An),this.needsUpdate=!1,e&&this.min.copy(e),t&&this.max.copy(t),n&&this.matrix.copy(n)}set(e,t,n){this.min.copy(e),this.max.copy(t),this.matrix.copy(n),this.needsUpdate=!0}copy(e){this.min.copy(e.min),this.max.copy(e.max),this.matrix.copy(e.matrix),this.needsUpdate=!0}};Pt.prototype.update=(function(){return function(){let e=this.matrix,t=this.min,n=this.max,i=this.points;for(let l=0;l<=1;l++)for(let u=0;u<=1;u++)for(let h=0;h<=1;h++){let d=1*l|2*u|4*h,f=i[d];f.x=l?n.x:t.x,f.y=u?n.y:t.y,f.z=h?n.z:t.z,f.applyMatrix4(e)}let r=this.satBounds,a=this.satAxes,o=i[0];for(let l=0;l<3;l++){let u=a[l],h=r[l],d=1<<l,f=i[d];u.subVectors(o,f),h.setFromPoints(u,i)}let c=this.alignedSatBounds;c[0].setFromPointsField(i,"x"),c[1].setFromPointsField(i,"y"),c[2].setFromPointsField(i,"z"),this.invMatrix.copy(this.matrix).invert(),this.needsUpdate=!1}})();Pt.prototype.intersectsBox=(function(){let s=new An;return function(t){this.needsUpdate&&this.update();let n=t.min,i=t.max,r=this.satBounds,a=this.satAxes,o=this.alignedSatBounds;if(s.min=n.x,s.max=i.x,o[0].isSeparated(s)||(s.min=n.y,s.max=i.y,o[1].isSeparated(s))||(s.min=n.z,s.max=i.z,o[2].isSeparated(s)))return!1;for(let c=0;c<3;c++){let l=a[c],u=r[c];if(s.setFromBox(l,t),u.isSeparated(s))return!1}return!0}})();Pt.prototype.intersectsTriangle=(function(){let s=new Jt,e=new Array(3),t=new An,n=new An,i=new L;return function(a){this.needsUpdate&&this.update(),a.isExtendedTriangle?a.needsUpdate&&a.update():(s.copy(a),s.update(),a=s);let o=this.satBounds,c=this.satAxes;e[0]=a.a,e[1]=a.b,e[2]=a.c;for(let d=0;d<3;d++){let f=o[d],g=c[d];if(t.setFromPoints(g,e),f.isSeparated(t))return!1}let l=a.satBounds,u=a.satAxes,h=this.points;for(let d=0;d<3;d++){let f=l[d],g=u[d];if(t.setFromPoints(g,h),f.isSeparated(t))return!1}for(let d=0;d<3;d++){let f=c[d];for(let g=0;g<4;g++){let y=u[g];if(i.crossVectors(f,y),t.setFromPoints(i,e),n.setFromPoints(i,h),t.isSeparated(n))return!1}}return!0}})();Pt.prototype.closestPointToPoint=(function(){return function(e,t){return this.needsUpdate&&this.update(),t.copy(e).applyMatrix4(this.invMatrix).clamp(this.min,this.max).applyMatrix4(this.matrix),t}})();Pt.prototype.distanceToPoint=(function(){let s=new L;return function(t){return this.closestPointToPoint(t,s),t.distanceTo(s)}})();Pt.prototype.distanceToBox=(function(){let s=["x","y","z"],e=new Array(12).fill().map(()=>new Zt),t=new Array(12).fill().map(()=>new Zt),n=new L,i=new L;return function(a,o=0,c=null,l=null){if(this.needsUpdate&&this.update(),this.intersectsBox(a))return(c||l)&&(a.getCenter(i),this.closestPointToPoint(i,n),a.closestPointToPoint(n,i),c&&c.copy(n),l&&l.copy(i)),0;let u=o*o,h=a.min,d=a.max,f=this.points,g=1/0;for(let m=0;m<8;m++){let p=f[m];i.copy(p).clamp(h,d);let x=p.distanceToSquared(i);if(x<g&&(g=x,c&&c.copy(p),l&&l.copy(i),x<u))return Math.sqrt(x)}let y=0;for(let m=0;m<3;m++)for(let p=0;p<=1;p++)for(let x=0;x<=1;x++){let v=(m+1)%3,b=(m+2)%3,S=p<<v|x<<b,w=1<<m|p<<v|x<<b,T=f[S],A=f[w];e[y].set(T,A);let _=s[m],I=s[v],C=s[b],D=t[y],N=D.start,U=D.end;N[_]=h[_],N[I]=p?h[I]:d[I],N[C]=x?h[C]:d[C],U[_]=d[_],U[I]=p?h[I]:d[I],U[C]=x?h[C]:d[C],y++}for(let m=0;m<=1;m++)for(let p=0;p<=1;p++)for(let x=0;x<=1;x++){i.x=m?d.x:h.x,i.y=p?d.y:h.y,i.z=x?d.z:h.z,this.closestPointToPoint(i,n);let v=i.distanceToSquared(n);if(v<g&&(g=v,c&&c.copy(n),l&&l.copy(i),v<u))return Math.sqrt(v)}for(let m=0;m<12;m++){let p=e[m];for(let x=0;x<12;x++){let v=t[x];Fa(p,v,n,i);let b=n.distanceToSquared(i);if(b<g&&(g=b,c&&c.copy(n),l&&l.copy(i),b<u))return Math.sqrt(b)}}return Math.sqrt(g)}})();var Pu=class extends Gi{constructor(){super(()=>new Jt)}},ln=new Pu;var Ua=new L,ku=new L;function Pp(s,e,t={},n=0,i=1/0){let r=n*n,a=i*i,o=1/0,c=null;if(s.shapecast({boundsTraverseOrder:u=>(Ua.copy(e).clamp(u.min,u.max),Ua.distanceToSquared(e)),intersectsBounds:(u,h,d)=>d<o&&d<a,intersectsTriangle:(u,h)=>{u.closestPointToPoint(e,Ua);let d=e.distanceToSquared(Ua);return d<o&&(ku.copy(Ua),o=d,c=h),d<r}}),o===1/0)return null;let l=Math.sqrt(o);return t.point?t.point.copy(ku):t.point=ku.clone(),t.distance=l,t.faceIndex=c,t}var tl=parseInt("180")>=169,Bv=parseInt("180")<=161,ws=new L,Ms=new L,Ss=new L,nl=new Ne,il=new Ne,sl=new Ne,kp=new L,Lp=new L,Dp=new L,Ba=new L;function Ov(s,e,t,n,i,r,a,o){let c;if(r===Dt?c=s.intersectTriangle(n,t,e,!0,i):c=s.intersectTriangle(e,t,n,r!==Mt,i),c===null)return null;let l=s.origin.distanceTo(i);return l<a||l>o?null:{distance:l,point:i.clone()}}function Np(s,e,t,n,i,r,a,o,c,l,u){ws.fromBufferAttribute(e,r),Ms.fromBufferAttribute(e,a),Ss.fromBufferAttribute(e,o);let h=Ov(s,ws,Ms,Ss,Ba,c,l,u);if(h){if(n){nl.fromBufferAttribute(n,r),il.fromBufferAttribute(n,a),sl.fromBufferAttribute(n,o),h.uv=new Ne;let f=en.getInterpolation(Ba,ws,Ms,Ss,nl,il,sl,h.uv);tl||(h.uv=f)}if(i){nl.fromBufferAttribute(i,r),il.fromBufferAttribute(i,a),sl.fromBufferAttribute(i,o),h.uv1=new Ne;let f=en.getInterpolation(Ba,ws,Ms,Ss,nl,il,sl,h.uv1);tl||(h.uv1=f),Bv&&(h.uv2=h.uv1)}if(t){kp.fromBufferAttribute(t,r),Lp.fromBufferAttribute(t,a),Dp.fromBufferAttribute(t,o),h.normal=new L;let f=en.getInterpolation(Ba,ws,Ms,Ss,kp,Lp,Dp,h.normal);h.normal.dot(s.direction)>0&&h.normal.multiplyScalar(-1),tl||(h.normal=f)}let d={a:r,b:a,c:o,normal:new L,materialIndex:0};if(en.getNormal(ws,Ms,Ss,d.normal),h.face=d,h.faceIndex=r,tl){let f=new L;en.getBarycoord(Ba,ws,Ms,Ss,f),h.barycoord=f}}return h}function Fp(s){return s&&s.isMaterial?s.side:s}function kr(s,e,t,n,i,r,a){let o=n*3,c=o+0,l=o+1,u=o+2,{index:h,groups:d}=s;s.index&&(c=h.getX(c),l=h.getX(l),u=h.getX(u));let{position:f,normal:g,uv:y,uv1:m}=s.attributes;if(Array.isArray(e)){let p=n*3;for(let x=0,v=d.length;x<v;x++){let{start:b,count:S,materialIndex:w}=d[x];if(p>=b&&p<b+S){let T=Fp(e[w]),A=Np(t,f,g,y,m,c,l,u,T,r,a);if(A)if(A.faceIndex=n,A.face.materialIndex=w,i)i.push(A);else return A}}}else{let p=Fp(e),x=Np(t,f,g,y,m,c,l,u,p,r,a);if(x)if(x.faceIndex=n,x.face.materialIndex=0,i)i.push(x);else return x}return null}function _t(s,e,t,n){let i=s.a,r=s.b,a=s.c,o=e,c=e+1,l=e+2;t&&(o=t.getX(o),c=t.getX(c),l=t.getX(l)),i.x=n.getX(o),i.y=n.getY(o),i.z=n.getZ(o),r.x=n.getX(c),r.y=n.getY(c),r.z=n.getZ(c),a.x=n.getX(l),a.y=n.getY(l),a.z=n.getZ(l)}function Up(s,e,t,n,i,r,a,o){let{geometry:c,_indirectBuffer:l}=s;for(let u=n,h=n+i;u<h;u++)kr(c,e,t,u,r,a,o)}function Bp(s,e,t,n,i,r,a){let{geometry:o,_indirectBuffer:c}=s,l=1/0,u=null;for(let h=n,d=n+i;h<d;h++){let f;f=kr(o,e,t,h,null,r,a),f&&f.distance<l&&(u=f,l=f.distance)}return u}function Op(s,e,t,n,i,r,a){let{geometry:o}=t,{index:c}=o,l=o.attributes.position;for(let u=s,h=e+s;u<h;u++){let d;if(d=u,_t(a,d*3,c,l),a.needsUpdate=!0,n(a,d,i,r))return!0}return!1}function zp(s,e=null){e&&Array.isArray(e)&&(e=new Set(e));let t=s.geometry,n=t.index?t.index.array:null,i=t.attributes.position,r,a,o,c,l=0,u=s._roots;for(let d=0,f=u.length;d<f;d++)r=u[d],a=new Uint32Array(r),o=new Uint16Array(r),c=new Float32Array(r),h(0,l),l+=r.byteLength;function h(d,f,g=!1){let y=d*2;if(it(y,o)){let m=dt(d,a),p=gt(y,o),x=1/0,v=1/0,b=1/0,S=-1/0,w=-1/0,T=-1/0;for(let A=3*m,M=3*(m+p);A<M;A++){let _=n[A],I=i.getX(_),C=i.getY(_),D=i.getZ(_);I<x&&(x=I),I>S&&(S=I),C<v&&(v=C),C>w&&(w=C),D<b&&(b=D),D>T&&(T=D)}return c[d+0]!==x||c[d+1]!==v||c[d+2]!==b||c[d+3]!==S||c[d+4]!==w||c[d+5]!==T?(c[d+0]=x,c[d+1]=v,c[d+2]=b,c[d+3]=S,c[d+4]=w,c[d+5]=T,!0):!1}else{let m=ct(d),p=lt(d,a),x=g,v=!1,b=!1;if(e){if(!x){let _=m/8+f/32,I=p/8+f/32;v=e.has(_),b=e.has(I),x=!v&&!b}}else v=!0,b=!0;let S=x||v,w=x||b,T=!1;S&&(T=h(m,f,x));let A=!1;w&&(A=h(p,f,x));let M=T||A;if(M)for(let _=0;_<3;_++){let I=m+_,C=p+_,D=c[I],N=c[I+3],U=c[C],B=c[C+3];c[d+_]=D<U?D:U,c[d+_+3]=N>B?N:B}return M}}}function rn(s,e,t,n,i){let r,a,o,c,l,u,h=1/t.direction.x,d=1/t.direction.y,f=1/t.direction.z,g=t.origin.x,y=t.origin.y,m=t.origin.z,p=e[s],x=e[s+3],v=e[s+1],b=e[s+3+1],S=e[s+2],w=e[s+3+2];return h>=0?(r=(p-g)*h,a=(x-g)*h):(r=(x-g)*h,a=(p-g)*h),d>=0?(o=(v-y)*d,c=(b-y)*d):(o=(b-y)*d,c=(v-y)*d),r>c||o>a||((o>r||isNaN(r))&&(r=o),(c<a||isNaN(a))&&(a=c),f>=0?(l=(S-m)*f,u=(w-m)*f):(l=(w-m)*f,u=(S-m)*f),r>u||l>a)?!1:((l>r||r!==r)&&(r=l),(u<a||a!==a)&&(a=u),r<=i&&a>=n)}function Hp(s,e,t,n,i,r,a,o){let{geometry:c,_indirectBuffer:l}=s;for(let u=n,h=n+i;u<h;u++){let d=l?l[u]:u;kr(c,e,t,d,r,a,o)}}function Vp(s,e,t,n,i,r,a){let{geometry:o,_indirectBuffer:c}=s,l=1/0,u=null;for(let h=n,d=n+i;h<d;h++){let f;f=kr(o,e,t,c?c[h]:h,null,r,a),f&&f.distance<l&&(u=f,l=f.distance)}return u}function Gp(s,e,t,n,i,r,a){let{geometry:o}=t,{index:c}=o,l=o.attributes.position;for(let u=s,h=e+s;u<h;u++){let d;if(d=t.resolveTriangleIndex(u),_t(a,d*3,c,l),a.needsUpdate=!0,n(a,d,i,r))return!0}return!1}function Wp(s,e,t,n,i,r,a){Je.setBuffer(s._roots[e]),rn(0,Je.float32Array,n,r,a)&&Lu(0,s,t,n,i,r,a),Je.clearBuffer()}function Lu(s,e,t,n,i,r,a){let{float32Array:o,uint16Array:c,uint32Array:l}=Je,u=s*2;if(it(u,c)){let d=dt(s,l),f=gt(u,c);Up(e,t,n,d,f,i,r,a)}else{let d=ct(s);rn(d,o,n,r,a)&&Lu(d,e,t,n,i,r,a);let f=lt(s,l);rn(f,o,n,r,a)&&Lu(f,e,t,n,i,r,a)}}var zv=["x","y","z"];function Yp(s,e,t,n,i,r){Je.setBuffer(s._roots[e]);let a=null;return rn(0,Je.float32Array,n,i,r)&&(a=Du(0,s,t,n,i,r)),Je.clearBuffer(),a}function Du(s,e,t,n,i,r){let{float32Array:a,uint16Array:o,uint32Array:c}=Je,l=s*2;if(it(l,o)){let h=dt(s,c),d=gt(l,o);return Bp(e,t,n,h,d,i,r)}else{let h=Sr(s,c),d=zv[h],g=n.direction[d]>=0,y,m;g?(y=ct(s),m=lt(s,c)):(y=lt(s,c),m=ct(s));let x=rn(y,a,n,i,r)?Du(y,e,t,n,i,r):null;if(x){let S=x.point[d];if(g?S<=a[m+h]:S>=a[m+h+3])return x}let b=rn(m,a,n,i,r)?Du(m,e,t,n,i,r):null;return x&&b?x.distance<=b.distance?x:b:x||b||null}}var rl=new ot,Lr=new Jt,Dr=new Jt,Oa=new ke,Xp=new Pt,al=new Pt;function qp(s,e,t,n){Je.setBuffer(s._roots[e]);let i=Nu(0,s,t,n);return Je.clearBuffer(),i}function Nu(s,e,t,n,i=null){let{float32Array:r,uint16Array:a,uint32Array:o}=Je,c=s*2;if(i===null&&(t.boundingBox||t.computeBoundingBox(),Xp.set(t.boundingBox.min,t.boundingBox.max,n),i=Xp),it(c,a)){let u=e.geometry,h=u.index,d=u.attributes.position,f=t.index,g=t.attributes.position,y=dt(s,o),m=gt(c,a);if(Oa.copy(n).invert(),t.boundsTree)return vt(s,r,al),al.matrix.copy(Oa),al.needsUpdate=!0,t.boundsTree.shapecast({intersectsBounds:x=>al.intersectsBox(x),intersectsTriangle:x=>{x.a.applyMatrix4(n),x.b.applyMatrix4(n),x.c.applyMatrix4(n),x.needsUpdate=!0;for(let v=y*3,b=(m+y)*3;v<b;v+=3)if(_t(Dr,v,h,d),Dr.needsUpdate=!0,x.intersectsTriangle(Dr))return!0;return!1}});{let p=Xi(t);for(let x=y*3,v=(m+y)*3;x<v;x+=3){_t(Lr,x,h,d),Lr.a.applyMatrix4(Oa),Lr.b.applyMatrix4(Oa),Lr.c.applyMatrix4(Oa),Lr.needsUpdate=!0;for(let b=0,S=p*3;b<S;b+=3)if(_t(Dr,b,f,g),Dr.needsUpdate=!0,Lr.intersectsTriangle(Dr))return!0}}}else{let u=ct(s),h=lt(s,o);return vt(u,r,rl),!!(i.intersectsBox(rl)&&Nu(u,e,t,n,i)||(vt(h,r,rl),i.intersectsBox(rl)&&Nu(h,e,t,n,i)))}}var ol=new ke,Fu=new Pt,za=new Pt,Hv=new L,Vv=new L,Gv=new L,Wv=new L;function jp(s,e,t,n={},i={},r=0,a=1/0){e.boundingBox||e.computeBoundingBox(),Fu.set(e.boundingBox.min,e.boundingBox.max,t),Fu.needsUpdate=!0;let o=s.geometry,c=o.attributes.position,l=o.index,u=e.attributes.position,h=e.index,d=ln.getPrimitive(),f=ln.getPrimitive(),g=Hv,y=Vv,m=null,p=null;i&&(m=Gv,p=Wv);let x=1/0,v=null,b=null;return ol.copy(t).invert(),za.matrix.copy(ol),s.shapecast({boundsTraverseOrder:S=>Fu.distanceToBox(S),intersectsBounds:(S,w,T)=>T<x&&T<a?(w&&(za.min.copy(S.min),za.max.copy(S.max),za.needsUpdate=!0),!0):!1,intersectsRange:(S,w)=>{if(e.boundsTree)return e.boundsTree.shapecast({boundsTraverseOrder:A=>za.distanceToBox(A),intersectsBounds:(A,M,_)=>_<x&&_<a,intersectsRange:(A,M)=>{for(let _=A,I=A+M;_<I;_++){_t(f,3*_,h,u),f.a.applyMatrix4(t),f.b.applyMatrix4(t),f.c.applyMatrix4(t),f.needsUpdate=!0;for(let C=S,D=S+w;C<D;C++){_t(d,3*C,l,c),d.needsUpdate=!0;let N=d.distanceToTriangle(f,g,m);if(N<x&&(y.copy(g),p&&p.copy(m),x=N,v=C,b=_),N<r)return!0}}}});{let T=Xi(e);for(let A=0,M=T;A<M;A++){_t(f,3*A,h,u),f.a.applyMatrix4(t),f.b.applyMatrix4(t),f.c.applyMatrix4(t),f.needsUpdate=!0;for(let _=S,I=S+w;_<I;_++){_t(d,3*_,l,c),d.needsUpdate=!0;let C=d.distanceToTriangle(f,g,m);if(C<x&&(y.copy(g),p&&p.copy(m),x=C,v=_,b=A),C<r)return!0}}}}}),ln.releasePrimitive(d),ln.releasePrimitive(f),x===1/0?null:(n.point?n.point.copy(y):n.point=y.clone(),n.distance=x,n.faceIndex=v,i&&(i.point?i.point.copy(p):i.point=p.clone(),i.point.applyMatrix4(ol),y.applyMatrix4(ol),i.distance=y.sub(i.point).length(),i.faceIndex=b),n)}function Kp(s,e=null){e&&Array.isArray(e)&&(e=new Set(e));let t=s.geometry,n=t.index?t.index.array:null,i=t.attributes.position,r,a,o,c,l=0,u=s._roots;for(let d=0,f=u.length;d<f;d++)r=u[d],a=new Uint32Array(r),o=new Uint16Array(r),c=new Float32Array(r),h(0,l),l+=r.byteLength;function h(d,f,g=!1){let y=d*2;if(it(y,o)){let m=dt(d,a),p=gt(y,o),x=1/0,v=1/0,b=1/0,S=-1/0,w=-1/0,T=-1/0;for(let A=m,M=m+p;A<M;A++){let _=3*s.resolveTriangleIndex(A);for(let I=0;I<3;I++){let C=_+I;C=n?n[C]:C;let D=i.getX(C),N=i.getY(C),U=i.getZ(C);D<x&&(x=D),D>S&&(S=D),N<v&&(v=N),N>w&&(w=N),U<b&&(b=U),U>T&&(T=U)}}return c[d+0]!==x||c[d+1]!==v||c[d+2]!==b||c[d+3]!==S||c[d+4]!==w||c[d+5]!==T?(c[d+0]=x,c[d+1]=v,c[d+2]=b,c[d+3]=S,c[d+4]=w,c[d+5]=T,!0):!1}else{let m=ct(d),p=lt(d,a),x=g,v=!1,b=!1;if(e){if(!x){let _=m/8+f/32,I=p/8+f/32;v=e.has(_),b=e.has(I),x=!v&&!b}}else v=!0,b=!0;let S=x||v,w=x||b,T=!1;S&&(T=h(m,f,x));let A=!1;w&&(A=h(p,f,x));let M=T||A;if(M)for(let _=0;_<3;_++){let I=m+_,C=p+_,D=c[I],N=c[I+3],U=c[C],B=c[C+3];c[d+_]=D<U?D:U,c[d+_+3]=N>B?N:B}return M}}}function Zp(s,e,t,n,i,r,a){Je.setBuffer(s._roots[e]),rn(0,Je.float32Array,n,r,a)&&Uu(0,s,t,n,i,r,a),Je.clearBuffer()}function Uu(s,e,t,n,i,r,a){let{float32Array:o,uint16Array:c,uint32Array:l}=Je,u=s*2;if(it(u,c)){let d=dt(s,l),f=gt(u,c);Hp(e,t,n,d,f,i,r,a)}else{let d=ct(s);rn(d,o,n,r,a)&&Uu(d,e,t,n,i,r,a);let f=lt(s,l);rn(f,o,n,r,a)&&Uu(f,e,t,n,i,r,a)}}var Yv=["x","y","z"];function Jp(s,e,t,n,i,r){Je.setBuffer(s._roots[e]);let a=null;return rn(0,Je.float32Array,n,i,r)&&(a=Bu(0,s,t,n,i,r)),Je.clearBuffer(),a}function Bu(s,e,t,n,i,r){let{float32Array:a,uint16Array:o,uint32Array:c}=Je,l=s*2;if(it(l,o)){let h=dt(s,c),d=gt(l,o);return Vp(e,t,n,h,d,i,r)}else{let h=Sr(s,c),d=Yv[h],g=n.direction[d]>=0,y,m;g?(y=ct(s),m=lt(s,c)):(y=lt(s,c),m=ct(s));let x=rn(y,a,n,i,r)?Bu(y,e,t,n,i,r):null;if(x){let S=x.point[d];if(g?S<=a[m+h]:S>=a[m+h+3])return x}let b=rn(m,a,n,i,r)?Bu(m,e,t,n,i,r):null;return x&&b?x.distance<=b.distance?x:b:x||b||null}}var cl=new ot,Nr=new Jt,Fr=new Jt,Ha=new ke,$p=new Pt,ll=new Pt;function Qp(s,e,t,n){Je.setBuffer(s._roots[e]);let i=Ou(0,s,t,n);return Je.clearBuffer(),i}function Ou(s,e,t,n,i=null){let{float32Array:r,uint16Array:a,uint32Array:o}=Je,c=s*2;if(i===null&&(t.boundingBox||t.computeBoundingBox(),$p.set(t.boundingBox.min,t.boundingBox.max,n),i=$p),it(c,a)){let u=e.geometry,h=u.index,d=u.attributes.position,f=t.index,g=t.attributes.position,y=dt(s,o),m=gt(c,a);if(Ha.copy(n).invert(),t.boundsTree)return vt(s,r,ll),ll.matrix.copy(Ha),ll.needsUpdate=!0,t.boundsTree.shapecast({intersectsBounds:x=>ll.intersectsBox(x),intersectsTriangle:x=>{x.a.applyMatrix4(n),x.b.applyMatrix4(n),x.c.applyMatrix4(n),x.needsUpdate=!0;for(let v=y,b=m+y;v<b;v++)if(_t(Fr,3*e.resolveTriangleIndex(v),h,d),Fr.needsUpdate=!0,x.intersectsTriangle(Fr))return!0;return!1}});{let p=Xi(t);for(let x=y,v=m+y;x<v;x++){let b=e.resolveTriangleIndex(x);_t(Nr,3*b,h,d),Nr.a.applyMatrix4(Ha),Nr.b.applyMatrix4(Ha),Nr.c.applyMatrix4(Ha),Nr.needsUpdate=!0;for(let S=0,w=p*3;S<w;S+=3)if(_t(Fr,S,f,g),Fr.needsUpdate=!0,Nr.intersectsTriangle(Fr))return!0}}}else{let u=ct(s),h=lt(s,o);return vt(u,r,cl),!!(i.intersectsBox(cl)&&Ou(u,e,t,n,i)||(vt(h,r,cl),i.intersectsBox(cl)&&Ou(h,e,t,n,i)))}}var hl=new ke,zu=new Pt,Va=new Pt,Xv=new L,qv=new L,jv=new L,Kv=new L;function em(s,e,t,n={},i={},r=0,a=1/0){e.boundingBox||e.computeBoundingBox(),zu.set(e.boundingBox.min,e.boundingBox.max,t),zu.needsUpdate=!0;let o=s.geometry,c=o.attributes.position,l=o.index,u=e.attributes.position,h=e.index,d=ln.getPrimitive(),f=ln.getPrimitive(),g=Xv,y=qv,m=null,p=null;i&&(m=jv,p=Kv);let x=1/0,v=null,b=null;return hl.copy(t).invert(),Va.matrix.copy(hl),s.shapecast({boundsTraverseOrder:S=>zu.distanceToBox(S),intersectsBounds:(S,w,T)=>T<x&&T<a?(w&&(Va.min.copy(S.min),Va.max.copy(S.max),Va.needsUpdate=!0),!0):!1,intersectsRange:(S,w)=>{if(e.boundsTree){let T=e.boundsTree;return T.shapecast({boundsTraverseOrder:A=>Va.distanceToBox(A),intersectsBounds:(A,M,_)=>_<x&&_<a,intersectsRange:(A,M)=>{for(let _=A,I=A+M;_<I;_++){let C=T.resolveTriangleIndex(_);_t(f,3*C,h,u),f.a.applyMatrix4(t),f.b.applyMatrix4(t),f.c.applyMatrix4(t),f.needsUpdate=!0;for(let D=S,N=S+w;D<N;D++){let U=s.resolveTriangleIndex(D);_t(d,3*U,l,c),d.needsUpdate=!0;let B=d.distanceToTriangle(f,g,m);if(B<x&&(y.copy(g),p&&p.copy(m),x=B,v=D,b=_),B<r)return!0}}}})}else{let T=Xi(e);for(let A=0,M=T;A<M;A++){_t(f,3*A,h,u),f.a.applyMatrix4(t),f.b.applyMatrix4(t),f.c.applyMatrix4(t),f.needsUpdate=!0;for(let _=S,I=S+w;_<I;_++){let C=s.resolveTriangleIndex(_);_t(d,3*C,l,c),d.needsUpdate=!0;let D=d.distanceToTriangle(f,g,m);if(D<x&&(y.copy(g),p&&p.copy(m),x=D,v=_,b=A),D<r)return!0}}}}}),ln.releasePrimitive(d),ln.releasePrimitive(f),x===1/0?null:(n.point?n.point.copy(y):n.point=y.clone(),n.distance=x,n.faceIndex=v,i&&(i.point?i.point.copy(p):i.point=p.clone(),i.point.applyMatrix4(hl),y.applyMatrix4(hl),i.distance=y.sub(i.point).length(),i.faceIndex=b),n)}function Hu(s,e,t){return s===null?null:(s.point.applyMatrix4(e.matrixWorld),s.distance=s.point.distanceTo(t.ray.origin),s.object=e,s)}var ul=new Pt,dl=new Sn,tm=new L,nm=new ke,im=new L,Vu=["getX","getY","getZ"],fl=class s extends el{static serialize(e,t={}){t={cloneBuffers:!0,...t};let n=e.geometry,i=e._roots,r=e._indirectBuffer,a=n.getIndex(),o={version:1,roots:null,index:null,indirectBuffer:null};return t.cloneBuffers?(o.roots=i.map(c=>c.slice()),o.index=a?a.array.slice():null,o.indirectBuffer=r?r.slice():null):(o.roots=i,o.index=a?a.array:null,o.indirectBuffer=r),o}static deserialize(e,t,n={}){n={setIndex:!0,indirect:!!e.indirectBuffer,...n};let{index:i,roots:r,indirectBuffer:a}=e;e.version||(console.warn("MeshBVH.deserialize: Serialization format has been changed and will be fixed up. It is recommended to regenerate any stored serialized data."),c(r));let o=new s(t,{...n,[La]:!0});if(o._roots=r,o._indirectBuffer=a||null,n.setIndex){let l=t.getIndex();if(l===null){let u=new xt(e.index,1,!1);t.setIndex(u)}else l.array!==i&&(l.array.set(i),l.needsUpdate=!0)}return o;function c(l){for(let u=0;u<l.length;u++){let h=l[u],d=new Uint32Array(h),f=new Uint16Array(h);for(let g=0,y=h.byteLength/32;g<y;g++){let m=8*g,p=2*m;it(p,f)||(d[m+6]=d[m+6]/8-g)}}}}get primitiveStride(){return 3}get resolveTriangleIndex(){return this.resolvePrimitiveIndex}constructor(e,t={}){t.maxLeafTris&&(console.warn('MeshBVH: "maxLeafTris" option has been deprecated. Use "targetLeafSize", instead.'),t={...t,targetLeafSize:t.maxLeafTris}),super(e,t)}shiftTriangleOffsets(e){return super.shiftPrimitiveOffsets(e)}writePrimitiveBounds(e,t,n){let i=this.geometry,r=this._indirectBuffer,a=i.attributes.position,o=i.index?i.index.array:null,l=(r?r[e]:e)*3,u=l+0,h=l+1,d=l+2;o&&(u=o[u],h=o[h],d=o[d]);for(let f=0;f<3;f++){let g=a[Vu[f]](u),y=a[Vu[f]](h),m=a[Vu[f]](d),p=g;y<p&&(p=y),m<p&&(p=m);let x=g;y>x&&(x=y),m>x&&(x=m),t[n+f]=p,t[n+f+3]=x}return t}computePrimitiveBounds(e,t,n){let i=this.geometry,r=this._indirectBuffer,a=i.attributes.position,o=i.index?i.index.array:null,c=a.normalized;if(e<0||t+e-n.offset>n.length/6)throw new Error("MeshBVH: compute triangle bounds range is invalid.");let l=a.array,u=a.offset||0,h=3;a.isInterleavedBufferAttribute&&(h=a.data.stride);let d=["getX","getY","getZ"],f=n.offset;for(let g=e,y=e+t;g<y;g++){let p=(r?r[g]:g)*3,x=(g-f)*6,v=p+0,b=p+1,S=p+2;o&&(v=o[v],b=o[b],S=o[S]),c||(v=v*h+u,b=b*h+u,S=S*h+u);for(let w=0;w<3;w++){let T,A,M;c?(T=a[d[w]](v),A=a[d[w]](b),M=a[d[w]](S)):(T=l[v+w],A=l[b+w],M=l[S+w]);let _=T;A<_&&(_=A),M<_&&(_=M);let I=T;A>I&&(I=A),M>I&&(I=M);let C=(I-_)/2,D=w*2;n[x+D+0]=_+C,n[x+D+1]=C+(Math.abs(_)+C)*Mr}}return n}raycastObject3D(e,t,n=[]){let{material:i}=e;if(i===void 0)return;nm.copy(e.matrixWorld).invert(),dl.copy(t.ray).applyMatrix4(nm),im.setFromMatrixScale(e.matrixWorld),tm.copy(dl.direction).multiply(im);let r=tm.length(),a=t.near/r,o=t.far/r;if(t.firstHitOnly===!0){let c=this.raycastFirst(dl,i,a,o);c=Hu(c,e,t),c&&n.push(c)}else{let c=this.raycast(dl,i,a,o);for(let l=0,u=c.length;l<u;l++){let h=Hu(c[l],e,t);h&&n.push(h)}}return n}refit(e=null){return(this.indirect?Kp:zp)(this,e)}raycast(e,t=pn,n=0,i=1/0){let r=this._roots,a=[],o=this.indirect?Zp:Wp;for(let c=0,l=r.length;c<l;c++)o(this,c,t,e,a,n,i);return a}raycastFirst(e,t=pn,n=0,i=1/0){let r=this._roots,a=null,o=this.indirect?Jp:Yp;for(let c=0,l=r.length;c<l;c++){let u=o(this,c,t,e,n,i);u!=null&&(a==null||u.distance<a.distance)&&(a=u)}return a}intersectsGeometry(e,t){let n=!1,i=this._roots,r=this.indirect?Qp:qp;for(let a=0,o=i.length;a<o&&(n=r(this,a,e,t),!n);a++);return n}shapecast(e){let t=ln.getPrimitive(),n=super.shapecast({...e,intersectsPrimitive:e.intersectsTriangle,scratchPrimitive:t,iterate:this.indirect?Gp:Op});return ln.releasePrimitive(t),n}bvhcast(e,t,n){let{intersectsRanges:i,intersectsTriangles:r}=n,a=ln.getPrimitive(),o=this.geometry.index,c=this.geometry.attributes.position,l=this.indirect?g=>{let y=this.resolveTriangleIndex(g);_t(a,y*3,o,c)}:g=>{_t(a,g*3,o,c)},u=ln.getPrimitive(),h=e.geometry.index,d=e.geometry.attributes.position,f=e.indirect?g=>{let y=e.resolveTriangleIndex(g);_t(u,y*3,h,d)}:g=>{_t(u,g*3,h,d)};if(r){if(!(e instanceof s))throw new Error('MeshBVH: "intersectsTriangles" callback can only be used with another MeshBVH.');let g=(y,m,p,x,v,b,S,w)=>{for(let T=p,A=p+x;T<A;T++){f(T),u.a.applyMatrix4(t),u.b.applyMatrix4(t),u.c.applyMatrix4(t),u.needsUpdate=!0;for(let M=y,_=y+m;M<_;M++)if(l(M),a.needsUpdate=!0,r(a,u,M,T,v,b,S,w))return!0}return!1};if(i){let y=i;i=function(m,p,x,v,b,S,w,T){return y(m,p,x,v,b,S,w,T)?!0:g(m,p,x,v,b,S,w,T)}}else i=g}return super.bvhcast(e,t,{intersectsRanges:i})}intersectsBox(e,t){return ul.set(e.min,e.max,t),ul.needsUpdate=!0,this.shapecast({intersectsBounds:n=>ul.intersectsBox(n),intersectsTriangle:n=>ul.intersectsTriangle(n)})}intersectsSphere(e){return this.shapecast({intersectsBounds:t=>e.intersectsBox(t),intersectsTriangle:t=>t.intersectsSphere(e)})}closestPointToGeometry(e,t,n={},i={},r=0,a=1/0){return(this.indirect?em:jp)(this,e,t,n,i,r,a)}closestPointToPoint(e,t={},n=0,i=1/0){return Pp(this,e,t,n,i)}};var Zv=100,sm=80,Jv=`
varying vec3 vWPos;
varying vec3 vWNrm;
`,$v=`
varying vec3 vWPos;
varying vec3 vWNrm;
uniform sampler2D uRoof;
uniform float uSkyTaps;
uniform float uDetail;

float hash11(float p){ p = fract(p * .1031); p *= p + 33.33; p *= p + p; return fract(p); }
float hash21(vec2 p){ vec3 p3 = fract(vec3(p.xyx) * .1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
float hash31(vec3 p){ p = fract(p * .1031); p += dot(p, p.zyx + 31.32); return fract((p.x + p.y) * p.z); }
float vnoise(vec3 p){
  vec3 i = floor(p), f = fract(p);
  f = f * f * (3. - 2. * f);
  return mix(mix(mix(hash31(i), hash31(i + vec3(1,0,0)), f.x),
                 mix(hash31(i + vec3(0,1,0)), hash31(i + vec3(1,1,0)), f.x), f.y),
             mix(mix(hash31(i + vec3(0,0,1)), hash31(i + vec3(1,0,1)), f.x),
                 mix(hash31(i + vec3(0,1,1)), hash31(i + vec3(1,1,1)), f.x), f.y), f.z);
}
float fbm(vec3 p){
  float a = .5, s = 0.;
  for (int i = 0; i < 4; i++){ s += a * vnoise(p); p = p * 2.03 + 17.1; a *= .5; }
  return s;
}

float roofHeight(vec2 xz){
  vec2 uv = xz / ${(Zv*2).toFixed(1)} + .5;
  if (uv.x < 0. || uv.x > 1. || uv.y < 0. || uv.y > 1.) return -100.;
  return texture2D(uRoof, uv).r;
}
// How much open sky this point sees, 0..1, from a top-down height map of the building.
float skyTap(vec2 xz, float y){ return smoothstep(-.9, .5, y - roofHeight(xz)); }
float skyVisibility(vec3 p, vec3 n){
  vec2 base = p.xz + n.xz * 1.1;
  float y = p.y + .45;
  float s = skyTap(base, y);
  s += skyTap(base + vec2( 1.7,  .6), y);
  s += skyTap(base + vec2(-1.1, 1.5), y);
  s += skyTap(base + vec2( -.7,-1.8), y);
  s += skyTap(base + vec2( 1.3,-1.2), y);
  if (uSkyTaps > 5.5) {
    s += skyTap(base + vec2( 3.4,  .2), y);
    s += skyTap(base + vec2(-3.1,  .9), y);
    s += skyTap(base + vec2(  .4, 3.3), y);
    s += skyTap(base + vec2( -.6,-3.4), y);
    return s / 9.;
  }
  return s / 5.;
}

// 1 inside the Heikhal and the Kodesh HaKodashim, whose walls were overlaid with gold.
float inHouse(vec3 p){
  return step(-67.3, p.x) * step(p.x, -35.9) * step(abs(p.z), 5.06) * step(9.2, p.y) * step(p.y, 29.5);
}
float sdSeg(vec2 p, vec2 a, vec2 b){
  vec2 pa = p - a, ba = b - a;
  return length(pa - ba * clamp(dot(pa, ba) / dot(ba, ba), 0., 1.));
}
// Height of a palm tree in low relief (Yechezkel 41:18), 0..1, in a panel 2.5 m wide.
float palmRelief(vec2 p){
  if (abs(p.x) > 1.05 || p.y < .5 || p.y > 4.5) return 0.;
  float d = sdSeg(p, vec2(0., .6), vec2(0., 3.05)) - mix(.085, .055, clamp((p.y - .6) / 2.4, 0., 1.));
  // scales on the trunk
  float h = smoothstep(.02, -.02, d) * (.75 + .25 * sin(p.y * 34. + abs(p.x) * 30.));
  vec2 c = vec2(0., 3.05);
  for (int i = 0; i < 9; i++){
    float a = (float(i) - 4.) * .37;
    float L = 1.12 - .05 * abs(float(i) - 4.);
    vec2 dir = vec2(sin(a), cos(a));
    vec2 p1 = c + dir * L * .45;
    vec2 p2 = c + dir * L * .8 + vec2(0., -.10 - .16 * abs(sin(a)));
    vec2 p3 = c + dir * L + vec2(sign(a) * .05, -.34 - .36 * abs(sin(a)));
    float fd = min(min(sdSeg(p, c, p1), sdSeg(p, p1, p2)), sdSeg(p, p2, p3));
    float along = clamp(distance(p, c) / L, 0., 1.);
    // a leaf-shaped blade: widest a third of the way out, feathered along its edge
    float w = .035 + .085 * sin(3.14159 * pow(along, .7)) * (.82 + .18 * sin(along * 46.));
    h = max(h, smoothstep(w, w - .04, fd));
  }
  // cluster of dates under the crown
  h = max(h, smoothstep(.13, .08, length((p - vec2(0., 2.86)) * vec2(1., 1.5))) * .8);
  return h;
}

// Returns block id in xy and distance to the nearest joint (metres) in z.
vec3 ashlar(vec2 uv, float courseH, float blockL){
  float row = floor(uv.y / courseH);
  float len = blockL * (.75 + .6 * hash11(row * 7.13 + 3.7));
  float x = uv.x + len * hash11(row * 3.31 + 1.9);
  float col = floor(x / len);
  float fx = (x / len - col) * len;
  float fy = uv.y - row * courseH;
  float d = min(min(fx, len - fx), min(fy, courseH - fy));
  return vec3(col, row, d);
}

vec3 bumpNormal(vec3 N, vec3 viewPos, float h, float strength){
  vec3 dpdx = dFdx(viewPos), dpdy = dFdy(viewPos);
  float dhdx = dFdx(h), dhdy = dFdy(h);
  vec3 r1 = cross(dpdy, N), r2 = cross(N, dpdx);
  float det = dot(dpdx, r1);
  vec3 grad = sign(det) * (dhdx * r1 + dhdy * r2);
  return normalize(abs(det) * N - strength * grad);
}
`;function On(s,{fragPars:e="",color:t="",rough:n="",normal:i="",sky:r=!0,uniforms:a}){return s.onBeforeCompile=o=>{Object.assign(o.uniforms,a),o.vertexShader=o.vertexShader.replace("#include <common>",`#include <common>
${Jv}`).replace("#include <beginnormal_vertex>",`#include <beginnormal_vertex>
 vWNrm = normalize(mat3(modelMatrix) * objectNormal);`).replace("#include <project_vertex>",`#include <project_vertex>
 vWPos = (modelMatrix * vec4(transformed, 1.)).xyz;`);let c=o.fragmentShader.replace("#include <common>",`#include <common>
${$v}
${e}`).replace("#include <color_fragment>",`#include <color_fragment>
 float mkBump = 0.; float mkBumpK = 0.; float mkRough = 0.; float mkMetal = 0.;
 vec3 wN = normalize(vWNrm);
 float camDist = length(vViewPosition);
${t}`).replace("#include <roughnessmap_fragment>",`#include <roughnessmap_fragment>
 roughnessFactor = clamp(roughnessFactor + mkRough, .04, 1.);
${n}`).replace("#include <metalnessmap_fragment>",`#include <metalnessmap_fragment>
 metalnessFactor = mix(metalnessFactor, 1., mkMetal);`).replace("#include <normal_fragment_maps>",`#include <normal_fragment_maps>
 if (mkBumpK > 0.) normal = bumpNormal(normal, -vViewPosition, mkBump, mkBumpK);
${i}`);r&&(c=c.replace("#include <aomap_fragment>",`#include <aomap_fragment>
        float mkSky = skyVisibility(vWPos, wN);
        float mkAmb = mix(.10, 1., mkSky * mkSky);
        reflectedLight.indirectDiffuse *= mkAmb;
        reflectedLight.indirectSpecular *= mix(vec3(.34, .24, .12), vec3(1.), mkSky);`)),o.fragmentShader=c},s.customProgramCacheKey=()=>t.length+":"+e.length+":"+n.length,s}function rm(s,e){let t={uRoof:{value:s},uSkyTaps:{value:e==="low"?5:9},uDetail:{value:e==="low"?.6:1},uTime:{value:0}},n=On(new Lt({vertexColors:!0,roughness:.86,metalness:0}),{uniforms:t,color:`
      {
        vec3 base = diffuseColor.rgb;
        // steer the flat source tints toward warm Jerusalem limestone
        float lum = dot(base, vec3(.3, .5, .2));
        vec3 lime = vec3(.80, .64, .43) * (.5 + .8 * lum);
        base = mix(base, lime, .7);
        float up = wN.y;
        vec3 ash;
        float tone;
        vec2 uv;
        if (abs(up) < .6) {
          uv = abs(wN.x) > abs(wN.z) ? vec2(vWPos.z, vWPos.y) : vec2(vWPos.x, vWPos.y);
          ash = ashlar(uv, .75, 1.7);
          tone = hash21(ash.xy + floor(uv.x * .013) * 7.);
        } else {
          uv = vWPos.xz;
          ash = ashlar(uv.yx, 1.0, 1.5);
          tone = hash21(ash.xy + 91.);
        }
        // metres covered by one pixel: joints and block tones melt away before they can shimmer
        float px = max(length(fwidth(uv)), 1e-4);
        float fade = 1. - smoothstep(.05, .32, px);
        float joint = (1. - smoothstep(.008, .008 + px * 1.6, ash.z)) * clamp(.05 / (px * 1.6 + .012), 0., 1.) * (1. - smoothstep(.3, .8, px));
        tone = mix(.5, tone, 1. - smoothstep(.08, .35, px));
        float aa = px;
        float margin = smoothstep(.05, .05 + aa * 2., ash.z);   // 0 on the drafted margin, 1 on the boss
        float grain = fbm(vWPos * 5.5);
        float coarse = fbm(vWPos * .32 + 4.);
        float fine = vnoise(vWPos * 42.);
        // block-to-block variation: brightness and a slight swing between cream and honey
        vec3 warm = base * vec3(1.03, .98, .90);
        vec3 cool = base * vec3(.98, .99, 1.02);
        vec3 c = mix(cool, warm, tone) * (.93 + .14 * mix(.5, hash11(tone * 91.7), 1. - smoothstep(.08, .35, px)));
        c *= .94 + .12 * fbm(vWPos * 1.1 + tone * 20.);
        c *= mix(1., .8 + .4 * grain, .55 * fade + .15);
        c *= .9 + .2 * coarse;
        c *= mix(1.045, 1., margin * fade);
        // rain streaks and dust settle low on walls
        float streak = fbm(vec3(vWPos.x * 1.6 + vWPos.z * 1.6, vWPos.y * .12, 3.));
        c *= 1. - .16 * smoothstep(.5, .8, streak) * (1. - abs(up));
        c = mix(c, c * vec3(.42, .38, .33), joint * .85);
        c *= .97 + .06 * fine * fade;
        diffuseColor.rgb = c;
        mkBump = (margin * (.35 + .65 * grain) - joint * 1.4) * .012 + fine * .0012;
        mkBumpK = fade * uDetail;
        mkRough = (grain - .5) * .16 + joint * .08;
        bool nearWall = abs(vWPos.z) > 4.9 || vWPos.x < -66.8 || vWPos.x > -36.2 || (vWPos.x < -56.9 && vWPos.x > -57.2) || vWPos.y > 28.;
        if (inHouse(vWPos) > .5 && nearWall) {
          if (up < -.5) {
            // cedar ceiling in coffers
            vec2 q = fract(vWPos.xz / 2.5) - .5;
            float rib = smoothstep(.36, .42, max(abs(q.x), abs(q.y)));
            float g2 = fbm(vec3(vWPos.x * 8., vWPos.z * .8, 2.));
            diffuseColor.rgb = mix(vec3(.20, .095, .045), vec3(.34, .17, .08), g2) * mix(.62, 1., rib);
            mkBump = rib * .03; mkBumpK = fade; mkRough = -.2;
          } else {
            // gilded panels, a palm between frame and frame
            float along = abs(wN.x) > abs(wN.z) ? vWPos.z + 5. : vWPos.x + 67.;
            float pu = along / 2.5;
            float col = floor(pu);
            vec2 pp = vec2((pu - col - .5) * 2.5, mod(vWPos.y - 9.25, 5.));
            float tier = floor((vWPos.y - 9.25) / 5.);
            float edge = min(min(pp.x + 1.25, 1.25 - pp.x), min(pp.y, 5. - pp.y));
            float frame = smoothstep(.10, .14, edge) - .5 * smoothstep(.20, .24, edge);
            float palm = (mod(col, 2.) < .5 && tier < 2.5) ? palmRelief(pp) : 0.;
            float hammer = vnoise(vWPos * 30.) * .6 + vnoise(vWPos * 70.) * .4;
            float pat = fbm(vWPos * 1.7);
            diffuseColor.rgb = vec3(1., .77, .34) * (.96 + .05 * pat) * (1. - .22 * (1. - smoothstep(.0, .03, edge)));
            diffuseColor.rgb *= 1. + .10 * palm;
            mkMetal = 1.;
            mkBump = frame * .012 + palm * .02 + hammer * .0012;
            mkBumpK = 1. - smoothstep(.02, .12, px);
            mkRough = -.46 + (pat - .5) * .06 - palm * .05;
          }
        }
      }`}),i=On(new Lt({vertexColors:!0,roughness:.74,metalness:0}),{uniforms:t,color:`
      {
        vec3 base = diffuseColor.rgb;
        float lum = dot(base, vec3(.3, .5, .2));
        base = mix(base, vec3(.80, .68, .49) * (.5 + .8 * lum), .7);
        vec2 uv = abs(wN.y) > .5 ? vWPos.xz : (abs(wN.x) > abs(wN.z) ? vec2(vWPos.z, vWPos.y * 2.) : vec2(vWPos.x, vWPos.y * 2.));
        vec3 ash = ashlar(uv, 1.0, 1.5);
        float px = max(length(fwidth(uv)), 1e-4);
        float fade = 1. - smoothstep(.05, .32, px);
        float tone = mix(.5, hash21(ash.xy + 5.), 1. - smoothstep(.12, .5, px));
        float joint = (1. - smoothstep(.006, .006 + px * 1.6, ash.z)) * clamp(.04 / (px * 1.6 + .01), 0., 1.) * (1. - smoothstep(.3, .8, px));
        float grain = fbm(vWPos * 4.);
        float veins = fbm(vec3(vWPos.xz * .7, tone * 8.));
        float coarse = fbm(vWPos * .12 + 9.);
        vec3 c = base * (.9 + .2 * tone) * mix(vec3(1.03, 1., .95), vec3(.98, 1., 1.03), hash11(tone * 37.));
        c *= .9 + .2 * grain * fade;
        c *= .93 + .14 * coarse;
        c *= 1. - .1 * smoothstep(.55, .7, veins) * fade;
        c = mix(c, c * vec3(.5, .46, .40), joint * .6);
        diffuseColor.rgb = c;
        mkBump = -joint * .012 + grain * .002;
        mkBumpK = fade * uDetail;
        mkRough = (veins - .5) * .25 - .08 * tone;
        if (inHouse(vWPos + vec3(0., .1, 0.)) > .5) {
          diffuseColor.rgb = mix(c, vec3(.86, .64, .30) * (.8 + .3 * veins), .78);
          mkMetal = .3;
          mkRough = -.50 + (veins - .5) * .12;
          mkBump *= .4;
        }
      }`}),a=On(new Lt({roughness:.3,metalness:1,envMapIntensity:1.25}),{uniforms:t,color:`
      {
        float hammer = vnoise(vWPos * 26.) * .6 + vnoise(vWPos * 61.) * .4;
        float patina = fbm(vWPos * 1.3);
        diffuseColor.rgb = vec3(1.0, .76, .33) * (.92 + .14 * patina);
        float fade = 1. - smoothstep(8., 40., camDist);
        mkBump = hammer * .0016;
        mkBumpK = fade * uDetail;
        mkRough = (patina - .5) * .22;
      }`}),o=On(new Lt({roughness:.2,metalness:1,envMapIntensity:1.5}),{uniforms:t,color:`
      {
        float patina = fbm(vWPos * 9.);
        diffuseColor.rgb = vec3(1.0, .78, .36) * (.94 + .1 * patina);
        mkRough = (patina - .5) * .14;
      }`}),c=On(new Lt({roughness:.3,metalness:1,envMapIntensity:1.2}),{uniforms:t,color:`
      {
        float patina = fbm(vWPos * 6.);
        diffuseColor.rgb = mix(vec3(.93, .52, .33), vec3(.72, .36, .22), patina);
        mkRough = (patina - .45) * .3;
      }`}),l=On(new Lt({roughness:.62,metalness:0}),{uniforms:t,color:`
      {
        // cedar boards: grain runs along the longer horizontal axis, vertical on leaves
        vec3 q = abs(wN.y) > .5 ? vWPos.xzy : (abs(wN.x) > abs(wN.z) ? vWPos.zyx : vWPos.xyz);
        float board = floor(q.x / .32);
        float rings = fbm(vec3(q.x * 9., q.y * .55, board * 3.1));
        float line = sin((q.y * .6 + rings * 2.2) * 34.) * .5 + .5;
        vec3 c = mix(vec3(.36, .17, .085), vec3(.56, .30, .15), rings);
        c *= .82 + .22 * line;
        c *= .88 + .24 * hash11(board * 1.7);
        float gap = smoothstep(.0, .012, abs(fract(q.x / .32) - .5) * .32 - .147);
        c *= 1. - .5 * gap;
        diffuseColor.rgb = c;
        mkBump = line * .0012 - gap * .004;
        mkBumpK = (1. - smoothstep(6., 30., camDist)) * uDetail;
      }`}),u=On(new Lt({roughness:.6,metalness:0,side:Mt}),{uniforms:t,sky:!1,color:`
      {
        float u = abs(wN.x) > abs(wN.z) ? vWPos.z : vWPos.x;
        float v = vWPos.y;
        if (abs(wN.y) < .5) {
          vec2 g = vec2(u, v) / .21;
          vec2 cell = abs(fract(vec2(g.x + g.y, g.x - g.y) * .5) - .5);
          float bar = min(cell.x, cell.y);
          float post = abs(fract(u / 2.5) - .5) * 2.5;
          bool rail = v < .07 || v > .76 || post < .06;
          if (!rail && bar > .1) discard;
        }
        float rings = fbm(vec3(u * 3., v * 14., vWPos.x + vWPos.z));
        diffuseColor.rgb = mix(vec3(.30, .14, .07), vec3(.50, .27, .13), rings);
      }`}),h=On(new Lt({vertexColors:!0,roughness:.92,metalness:0}),{uniforms:t,color:`
      { diffuseColor.rgb = diffuseColor.rgb * 1.6 + .012 * fbm(vWPos * 7.); }`}),d=new Lt({color:7999504,roughness:.7}),f=On(new Lt({roughness:.82,metalness:0}),{uniforms:t,color:`
      {
        float bake = fbm(vWPos * 22.);
        diffuseColor.rgb = mix(vec3(.80, .58, .30), vec3(.55, .33, .14), bake * .8 + max(wN.y, 0.) * .15);
      }`}),g=On(new Lt({roughness:.92,metalness:0,side:Mt}),{uniforms:t,color:`
      {
        vec2 uv = vec2(vWPos.z, vWPos.y - 9.28);
        vec3 techeles = vec3(.022, .060, .26);
        vec3 argaman = vec3(.15, .022, .17);
        vec3 shani = vec3(.30, .018, .03);
        // a blue field, bordered in purple and crimson
        float border = min(min(uv.x + 1.75, 1.75 - uv.x), min(uv.y, 3.06 - uv.y));
        vec3 c = techeles;
        c = mix(argaman, c, smoothstep(.34, .38, border));
        c = mix(shani, c, smoothstep(.14, .18, border));
        // fine lozenge of gold thread over the field, twisted linen at the crossings
        vec2 g = uv * 4.;
        vec2 cell = abs(fract(vec2(g.x + g.y, g.x - g.y) * .5) - .5);
        float px = max(length(fwidth(uv)), 1e-4);
        float show = 1. - smoothstep(.01, .05, px);
        float lattice = (1. - smoothstep(.012, .012 + px * 4., min(cell.x, cell.y))) * smoothstep(.36, .42, border);
        float knot = (1. - smoothstep(.03, .05, length(cell))) * smoothstep(.36, .42, border);
        c = mix(c, vec3(.72, .52, .17), lattice * (.25 + .5 * show));
        c = mix(c, vec3(.80, .76, .64), knot * show);
        float edgeLine = (1. - smoothstep(.0, .012, abs(border - .36))) + (1. - smoothstep(.0, .012, abs(border - .16)));
        c = mix(c, vec3(.74, .54, .18), clamp(edgeLine, 0., 1.) * .8);
        float weave = sin(uv.x * 1100.) * sin(uv.y * 1100.);
        c *= 1. + .10 * weave * (1. - smoothstep(.0008, .004, px));
        diffuseColor.rgb = c;
      }`}),y=On(new Lt({color:3104614,roughness:.06,metalness:.1,transparent:!0,opacity:.82,envMapIntensity:1.6}),{uniforms:t,fragPars:"uniform float uTime;",color:`
      {
        float w = vnoise(vec3(vWPos.xz * 9., uTime * .8)) + vnoise(vec3(vWPos.xz * 21. + 3., uTime * 1.3)) * .5;
        mkBump = w * .004;
        mkBumpK = 1.;
      }`}),m=On(new Lt({color:16777215,roughness:.9,metalness:0}),{uniforms:t,sky:!1,color:`
      {
        float r = length(vWPos.xz);
        vec3 ash = ashlar(vWPos.xz, 1.5, 2.2);
        float px = max(length(fwidth(vWPos.xz)), 1e-4);
        float fade = 1. - smoothstep(.06, .4, px);
        float tone = mix(.5, hash21(ash.xy + 13.), 1. - smoothstep(.15, .7, px));
        float joint = (1. - smoothstep(.006, .006 + px * 1.6, ash.z)) * clamp(.024 / (px * 1.6 + .006), 0., 1.) * (1. - smoothstep(.25, .8, px));
        float grain = fbm(vWPos * 3.);
        float coarse = fbm(vec3(vWPos.xz * .02, 2.));
        vec3 slab = vec3(.78, .63, .43) * (.88 + .22 * tone) * (.9 + .2 * grain * fade);
        slab = mix(slab, slab * .5, joint * .8);
        vec3 earth = mix(vec3(.50, .42, .30), vec3(.62, .55, .40), coarse) * (.9 + .2 * fbm(vWPos * .6));
        float paved = 1. - smoothstep(730., 760., max(abs(vWPos.x - 419.), abs(vWPos.z - 418.5)) + (coarse - .5) * 30.);
        vec3 c = mix(earth, slab, paved) * (.86 + .28 * coarse);
        diffuseColor.rgb = c;
        mkBump = -joint * .012 * paved + grain * .003;
        mkBumpK = fade * uDetail;
      }`});return{byClass:{stone:n,paving:i,gold:a,vgold:o,copper:c,wood:l,dark:h,red:d,bread:f,cloth:g,water:y,soreg:u},ground:m,uniforms:t}}var om=`
float h21(vec2 p){ vec3 p3 = fract(vec3(p.xyx) * .1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
float n2(vec2 p){ vec2 i = floor(p), f = fract(p); f = f*f*(3.-2.*f);
  return mix(mix(h21(i), h21(i+vec2(1,0)), f.x), mix(h21(i+vec2(0,1)), h21(i+vec2(1,1)), f.x), f.y); }
float fbm2(vec2 p){ float a=.5, s=0.; for(int i=0;i<4;i++){ s+=a*n2(p); p=p*2.02+11.3; a*=.5; } return s; }
`,Qv=`
attribute vec4 aSeed;      // xyz = base position, w = phase
attribute vec2 aSize;      // width, height
uniform float uTime;
varying vec2 vUv;
varying float vPhase;
void main(){
  vUv = uv;
  vPhase = aSeed.w;
  vec3 c = aSeed.xyz;
  vec3 toCam = cameraPosition - c; toCam.y = 0.;
  vec3 right = normalize(cross(vec3(0,1,0), normalize(toCam + vec3(1e-4))));
  float sway = sin(uTime * 2.3 + aSeed.w * 6.28) * .06 * uv.y * aSize.x;
  vec3 p = c + right * ((uv.x - .5) * aSize.x + sway) + vec3(0, uv.y * aSize.y, 0);
  gl_Position = projectionMatrix * viewMatrix * vec4(p, 1.);
}`,e_=`
uniform float uTime;
uniform float uGain;
varying vec2 vUv;
varying float vPhase;
${om}
void main(){
  vec2 uv = vUv;
  float t = uTime * 1.5 + vPhase * 17.;
  float n = fbm2(vec2(uv.x * 3.2 + vPhase * 9., uv.y * 2.6 - t));
  float n2_ = fbm2(vec2(uv.x * 7. - vPhase * 4., uv.y * 5. - t * 1.7));
  float x = abs(uv.x - .5 + (n - .5) * .22 * uv.y) * 2.;
  float body = 1. - smoothstep(0., 1., x * (1. + uv.y * 1.6) + uv.y * .9 - .15);
  float f = body * (.72 + .7 * n) - (1. - n2_) * .32 * uv.y;
  f *= smoothstep(0., .08, uv.y);
  float a = smoothstep(.12, .62, f);
  vec3 col = mix(vec3(.9, .13, .02), vec3(1., .5, .07), smoothstep(.15, .5, f));
  col = mix(col, vec3(1., .86, .45), smoothstep(.45, .85, f));
  col = mix(col, vec3(1., .97, .85), smoothstep(.8, 1.1, f));
  gl_FragColor = vec4(col * a * uGain, a);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}`,t_=`
attribute vec4 aSeed;      // x,z jitter, phase, size jitter
uniform float uTime;
uniform vec3 uBase;
uniform vec4 uShape;       // rise speed, lifetime, start radius, end radius
uniform vec2 uDrift;
varying vec2 vUv;
varying float vAge;
varying float vSeed;
void main(){
  vUv = uv;
  float age = fract(uTime / uShape.y + aSeed.z);
  vAge = age;
  vSeed = aSeed.z;
  float h = age * uShape.y * uShape.x;
  float size = mix(uShape.z, uShape.w, pow(age, .8)) * (.75 + .5 * aSeed.w);
  float spread = age * age * uShape.w * .35;
  vec3 c = uBase + vec3(aSeed.x * (uShape.z * .7 + spread), h, aSeed.y * (uShape.z * .7 + spread));
  c.xz += uDrift * h * age;
  c.x += sin(h * .21 + aSeed.z * 30.) * .12 * size;
  vec3 camRight = vec3(viewMatrix[0][0], viewMatrix[1][0], viewMatrix[2][0]);
  vec3 camUp = vec3(viewMatrix[0][1], viewMatrix[1][1], viewMatrix[2][1]);
  float rot = aSeed.z * 40. + uTime * .08 * (aSeed.w - .5);
  vec2 q = (uv - .5) * size;
  q = vec2(q.x * cos(rot) - q.y * sin(rot), q.x * sin(rot) + q.y * cos(rot));
  vec3 p = c + camRight * q.x + camUp * q.y;
  gl_Position = projectionMatrix * viewMatrix * vec4(p, 1.);
}`,n_=`
uniform vec3 uLit;
uniform vec3 uShade;
uniform float uOpacity;
varying vec2 vUv;
varying float vAge;
varying float vSeed;
${om}
void main(){
  vec2 d = vUv - .5;
  float r = length(d) * 2.;
  float n = fbm2(vUv * 3. + vSeed * 50.);
  float a = smoothstep(1., .25, r + (n - .5) * .7);
  a *= smoothstep(0., .08, vAge) * (1. - smoothstep(.55, 1., vAge));
  vec3 col = mix(uShade, uLit, clamp(.55 + d.y * .9 + (n - .5) * .5, 0., 1.));
  gl_FragColor = vec4(col, a * uOpacity);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}`;function Gu(s,e){let t=new Bi(1,1).translate(.5,.5,0),n=new lr;n.index=t.index,n.setAttribute("position",t.attributes.position),n.setAttribute("uv",t.attributes.uv);let i=new Float32Array(s.length*4),r=new Float32Array(s.length*2);s.forEach((c,l)=>{i.set([c.x,c.y,c.z,c.phase],l*4),r.set([c.w,c.h],l*2)}),n.setAttribute("aSeed",new Nn(i,4)),n.setAttribute("aSize",new Nn(r,2)),n.instanceCount=s.length;let a=new Yt({vertexShader:Qv,fragmentShader:e_,uniforms:{uTime:{value:0},uGain:{value:e}},transparent:!0,depthWrite:!1,blending:ds,side:Mt}),o=new at(n,a);return o.frustumCulled=!1,o.renderOrder=5,o}function am(s,e,t,n){let i=new Bi(1,1).translate(.5,.5,0),r=new lr;r.index=i.index,r.setAttribute("position",i.attributes.position),r.setAttribute("uv",i.attributes.uv);let a=new Float32Array(s*4),o=12345,c=()=>(o=o*16807%2147483647)/2147483647;for(let h=0;h<s;h++)a.set([c()*2-1,c()*2-1,(h+c()*.6)/s,c()],h*4);r.setAttribute("aSeed",new Nn(a,4)),r.instanceCount=s;let l=new Yt({vertexShader:t_,fragmentShader:n_,uniforms:{uTime:{value:0},uBase:{value:e},uShape:{value:t},uDrift:{value:new Ne(0,0)},uLit:{value:new Ue(.8,.78,.75)},uShade:{value:new Ue(.3,.3,.32)},uOpacity:{value:n}},transparent:!0,depthWrite:!1}),u=new at(r,l);return u.frustumCulled=!1,u.renderOrder=4,u}function cm(s,e,t){let n=new Gt;s.add(n);let i=10.9,r=[],a=7,o=()=>(a=a*16807%2147483647)/2147483647;for(let T=0;T<11;T++){let A=T<4;r.push({x:(o()-.5)*2.9,y:i-.05,z:(o()-.5)*2.1,w:A?1.9+o()*.7:1+o()*.6,h:A?2.6+o()*1.1:1.3+o()*.8,phase:o()})}let c=Gu(r,2.4);n.add(c);let l=am(t==="low"?36:64,new L(0,i+1.6,0),new tt(3.2,30,2.2,15),.34);n.add(l);let u=new Mi(16747068,0,55,1.6);u.position.set(0,i+1.4,0),n.add(u);let h=e.lamps.map(([T,A,M],_)=>({x:T,y:A+.004,z:M,w:.05,h:.11,phase:_*.137+.2})),d=Gu(h,3.2);n.add(d);let f=e.lamps[3],g=new Mi(16761466,0,34,1.5);g.position.set(f[0]+.25,f[1]+.25,f[2]),n.add(g);let y=new Mi(16767392,0,60,1.2);y.position.set(-40,25,0),n.add(y);let m=e.boxes.goldenAltar,p=new L((m.min[0]+m.max[0])/2,m.max[1]-.03,(m.min[2]+m.max[2])/2),x=am(t==="low"?14:26,p,new tt(.34,11,.07,.62),.13);x.material.uniforms.uLit.value.setRGB(.62,.55,.45),x.material.uniforms.uShade.value.setRGB(.3,.26,.2),n.add(x);let v=Gu([{x:p.x,y:p.y-.02,z:p.z,w:.16,h:.09,phase:.4}],1.4);n.add(v);let b=[c,d,v,l,x].map(T=>T.material);function S(T,A){for(let _ of b)_.uniforms.uTime.value=A;let M=.82+.18*Math.sin(A*11.3)*Math.sin(A*7.1+1.3)+.06*Math.sin(A*23.7);u.intensity=u.userData.base*M,g.intensity=g.userData.base*(.95+.05*Math.sin(A*9.1+.4))}function w(T,A){let M=Ct.clamp(A.elevation/20,.15,1);l.material.uniforms.uLit.value.setRGB(.86*M+.1,.82*M+.06,.78*M+.04),l.material.uniforms.uShade.value.setRGB(.3*M+.03,.3*M+.03,.33*M+.03),u.userData.base=14+150*(1-M),g.userData.base=13,y.intensity=11}return{update:S,setSun:w,group:n}}var Ci={names:[["Splayed high window stone reveal","outer"],["Outer E pillar collar","gates"],["Side-cell ceiling","cells"],["Hearth stone surround","kitchens"],["Knife-store wing","ulam"],["Outer chamber side wall","galleries"],["Outer chamber door lintel","galleries"],["Cooking vessel","kitchens"],["Cell communicating doorway","mixed"],["Knife-store niches","mixed"],["Copper fitting","vessel"],["Facade pilaster base and capital","ulam"],["Side-cell floor","cells"],["Facade pilaster shaft","ulam"],["Inner E connecting doorway lintel","gates"],["Outer N cell front lower","gates"],["Priestly facade shoulder","priest"],["Priestly room floor","priest"],["Gate leaf panel cross rail","gates"],["Carved palm trunk","ulam"],["Gallery pier","galleries"],["High window sill and lintel","outer"],["Facade recessed field rail","mixed"],["Priestly doorway lintel","priest"],["Inner S gate leaf panel","gates"],["Outer E cell rear wall","gates"],["Outer chamber roof","galleries"],["Outer E stair","gates"],["Golden roof anti-bird point","heichal"],["Altar yesod south return","altar"],["Derived union of House and Ulam foundations","mixed"],["Outer N cell front upper","gates"],["Ulam pillar collar","ulam"],["Inner S cell rear wall","gates"],["Pier base","galleries"],["Cooking back wall","kitchens"],["Outer S mount approach terrace","gates"],["Outer chamber door shoulder","galleries"],["Inner S continuous cell doorway floor","gates"],["Inner lateral gate lintel","gates"],["Facade gold dentil","mixed"],["Inner E connecting doorway back","gates"],["Gate leaf upright border","gates"],["Hearth firebox opening","kitchens"],["Inner N gate leaf panel","gates"],["Priestly inner lintel","priest"],["Inner N pillar","gates"],["Stone table leg","inner"],["Priestly ceiling","priest"],["Knife-store niches","ulam"],["Turned pedestal","vessel"],["Carved palm frond","ulam"],["Outer N cell rear wall","gates"],["Outer N connecting doorway lintel","gates"],["Inner S cell floor","gates"],["Priestly partition","priest"],["Outer N gate leaf panel","gates"],["Pier capital","galleries"],["Court string course and cornice","outer"],["Outer S pillar collar","gates"],["Cooking side wall","kitchens"],["Outer chamber back","galleries"],["Cell communicating lintel","mixed"],["Outer E gate leaf panel","gates"],["Carved palm frond","gates"],["Inner E cell supporting plinth","gates"],["Hollow basin with inner wall","vessel"],["Outer N pillar collar","gates"],["House rear foundation wall six","cells"],["Cell communicating doorway","cells"],["Outer N continuous cell doorway floor","gates"],["Side-cell outer wall","cells"],["Inner S cell roof","gates"],["Outer N cell floor","gates"],["Cooking hearth","kitchens"],["Priestly internal shoulder","priest"],["Inner S pillar collar","gates"],["Outer S cell front upper","gates"],["Outer E connecting doorway front","gates"],["Outer N open gate leaf","gates"],["Outer chamber floor","galleries"],["Stone slaughter table","inner"],["Inner N connecting doorway front","gates"],["Inner side wall","inner"],["Outer N cell roof","gates"],["High narrow window","heichal"],["Facade recessed field rail","ulam"],["Altar yesod east return","altar"],["Outer E cell floor","gates"],["Outer N vestibule wall","gates"],["Outer S connecting doorway back","gates"],["Inner E cell front lower","gates"],["Inner N connecting doorway back","gates"],["Outer N mount approach terrace","gates"],["Inner N pillar collar","gates"],["Inner N cell roof","gates"],["Outer S cell supporting plinth","gates"],["Outer S open gate leaf","gates"],["Sanctuary ceiling","heichal"],["Window edge","heichal"],["Inner E stair","gates"],["Inner E cell window cheek","gates"],["East strip wall footing","inner"],["Altar wood","altar"],["Inner E gate leaf panel","gates"],["Spout","vessel"],["Inner E continuous cell doorway floor","gates"],["Song chamber","inner"],["Rear cell corner passage","cells"],["Ulam stair","ulam"],["Inner S vestibule floor","gates"],["Inner N cell front lower","gates"],["Inner S cell front upper","gates"],["Outer N connecting doorway back","gates"],["Priestly service chamber","inner"],["Inner N cell rear wall","gates"],["Cell communicating lintel","cells"],["Outer S stair","gates"],["Outer E vestibule wall","gates"],["Inner S stair","gates"],["Facade gold dentil","ulam"],["Outer S cell floor","gates"],["Song chamber side","mixed"],["Outer S cell front lower","gates"],["Outer S cell window cheek","gates"],["Outer N pillar","gates"],["Facade pilaster base and capital","mixed"],["Continuous cell threshold floor","cells"],["Inner S connecting doorway back","gates"],["Outer N cell window cheek","gates"],["Five-amah service passage","cells"],["Inner E vestibule floor","gates"],["Inner E cell roof","gates"],["Outer S vestibule floor","gates"],["Outer E connecting doorway lintel","gates"],["Inner N cell window cheek","gates"],["Outer S gate leaf panel","gates"],["Outer S cell rear wall","gates"],["Outer N connecting doorway front","gates"],["Carved palm trunk","gates"],["Outer E cell roof","gates"],["Inner S cell window cheek","gates"],["Ulam nested stone door frame","ulam"],["Inner E cell floor","gates"],["Inner E connecting doorway front","gates"],["Inner N stair","gates"],["Inner S pillar-side access landing","gates"],["Continuous cell threshold floor","mixed"],["Open Heichal door","heichal"],["Song chamber back","inner"],["Five-amah service passage","mixed"],["Outer E cell window cheek","gates"],["Outer S connecting doorway lintel","gates"],["Western cell roof","cells"],["Cooking entrance shoulder","kitchens"],["Inner N cell front upper","gates"],["Ezras Kohanim floor","inner"],["Inner E open gate leaf","gates"],["Inner S connecting doorway front","gates"],["Layered Ulam roof cornice","ulam"],["Priestly service chamber entry","inner"],["Inner S cell supporting plinth","gates"],["Outer S pillar","gates"],["Inner eastern gate wall jamb","inner"],["Inner N connecting doorway lintel","gates"],["Raised priest court foundation","inner"],["Outer E cell supporting plinth","gates"],["Outer E cell front upper","gates"],["Outer S end cell wall","gates"],["Ulam lintel moulding","ulam"],["Outer service passage wall","mixed"],["Inner court clear floor","inner"],["Inner N cell floor","gates"],["Outer S cell roof","gates"],["Duchan rise","inner"],["Western cell floor","cells"],["Keren","altar"],["Inner E end cell wall","gates"],["Outer court floor","outer"],["Outer N end cell wall","gates"],["Outer E connecting doorway back","gates"],["Outer S connecting doorway front","gates"],["Inner N vestibule wall","gates"],["Kodesh clear floor","kodesh"],["Outer S vestibule entablature","gates"],["Altar yesod north","altar"],["Outer E end cell wall","gates"],["Outer N cell access landing","gates"],["Inner S connecting doorway lintel","gates"],["Inner N continuous cell doorway floor","gates"],["Inner E cell front upper","gates"],["Chut hasikra east west","altar"],["Ulam clear floor","ulam"],["Southern kevesh \u2014 ascend north","altar"],["Western outer court foundation","outer"],["Inner N end cell wall","gates"],["Outer E vestibule floor","gates"],["Inner N pillar-side access landing","gates"],["Outer N stair","gates"],["Chut hasikra north south","altar"],["Altar yesod west","altar"],["Sanctuary roof stone moulding","heichal"],["Outer E open gate leaf","gates"],["Inner S vestibule wall","gates"],["Inner S open gate leaf","gates"],["Outer S cell access landing","gates"],["Outer N threshold","gates"],["Outer S vestibule wall","gates"],["Inner E cell rear wall","gates"],["Inner E pillar collar","gates"],["Outer N cell supporting plinth","gates"],["Outer E cell front lower","gates"],["Kodesh partition lintel","kodesh"],["Outer E continuous cell doorway floor","gates"],["Priestly service chamber back","inner"],["Facade cornice","mixed"],["Inner S cell front lower","gates"],["Inner court supporting platform","inner"],["Altar foundation core","altar"],["Inner N threshold","gates"],["Facade pilaster shaft","mixed"],["Inner S end cell wall","gates"],["Inner N cell supporting plinth","gates"],["Facade cornice","ulam"],["Derived union of source raised gallery slabs","mixed"],["Inner S vestibule entablature","gates"],["Inner eastern gate wall lintel","inner"],["Woodpile area","altar"],["Priestly chamber precinct","priest"],["Inner N open gate leaf","gates"],["Outer S threshold","gates"],["Inner N vestibule entablature","gates"],["Inner E pillar-side access landing","gates"],["Outer E vestibule entablature","gates"],["Inner E vestibule entablature","gates"],["Derived union of source House walls and roofs","mixed"],["Kodesh partition shoulder","kodesh"],["Inner S pillar","gates"],["Priestly service chamber side","inner"],["Side-cell outer wall","mixed"],["Outer E cell access landing","gates"],["Altar middle tier","altar"],["Water recessed below rolled rim","vessel"],["Outer E pillar","gates"],["Priestly service chamber roof","inner"],["Inner E pillar","gates"],["Song chamber entry","mixed"],["Inner E vestibule wall","gates"],["Derived union of source western paving and transition","mixed"],["Outer S continuous cell doorway floor","gates"],["Knife-store wing","mixed"],["Outer N vestibule floor","gates"],["House rear upper wall five","cells"],["Inner S threshold","gates"],["Song chamber roof","inner"],["Outer court supporting platform","outer"],["Altar upper tier","altar"],["Outer lateral gate lintel","gates"],["Inner N vestibule floor","gates"],["Ulam entrance pillar","ulam"],["Outer N vestibule entablature","gates"],["Outer E threshold","gates"],["Inner E threshold","gates"],["Heichal clear floor","heichal"],["Derived union of source outer envelope walls","mixed"],["Outer service passage wall","cells"],["Menorah","heichal"],["Stone of three steps before the Menorah","heichal"],["Shulchan","heichal"],["Lechem HaPanim","heichal"],["Golden altar","heichal"],["Paroches","kodesh"],["Paroches hem and fixings","kodesh"],["Cheil","mount"],["Wall of the cheil","mount"],["Soreg","mount"]],index:[0,1,2,3,4,5,6,5,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,3,23,12,24,25,26,27,28,29,26,28,5,30,31,7,3,32,33,10,26,34,18,28,35,36,18,37,21,38,6,34,39,3,40,41,37,42,28,43,21,44,45,18,46,47,0,28,48,49,50,0,7,26,51,52,0,53,54,37,55,56,16,57,43,58,54,59,60,47,58,2,51,61,62,12,10,20,43,63,36,64,16,14,21,57,58,20,28,1,65,7,55,66,56,5,67,64,47,57,23,68,63,69,70,71,72,48,73,74,26,74,18,75,18,76,20,77,78,28,18,0,69,43,79,80,81,58,82,83,13,58,84,2,10,37,48,8,57,85,86,87,88,45,6,89,26,58,57,90,17,42,3,91,43,42,76,63,92,93,73,18,94,0,10,76,37,0,95,10,2,61,69,96,40,49,17,56,97,28,27,64,16,51,74,63,57,54,69,34,98,2,17,0,7,49,48,17,10,10,44,2,75,99,18,3,100,18,101,64,102,75,37,5,0,103,104,46,105,48,37,7,106,35,107,37,28,18,108,61,109,28,48,16,51,11,110,111,55,75,21,112,0,22,65,10,7,10,3,32,64,111,37,16,56,58,113,85,57,28,37,16,75,64,74,114,115,0,91,44,18,104,116,23,117,118,37,61,119,28,64,21,84,64,120,58,20,21,43,75,0,64,6,120,23,94,121,122,3,69,123,124,37,43,92,125,37,69,69,61,18,2,126,3,85,3,20,69,74,99,75,99,21,104,127,128,16,64,16,34,129,124,21,113,130,131,132,40,64,133,63,61,0,134,121,44,12,21,20,31,18,28,47,135,127,69,103,136,42,18,105,55,18,64,28,5,64,137,6,2,138,120,78,64,22,80,74,47,56,94,63,43,12,0,139,20,16,7,5,58,64,69,93,18,43,64,61,140,137,21,21,53,80,141,2,12,6,85,5,75,75,142,143,5,10,0,11,116,67,144,20,37,37,116,99,145,43,64,136,40,58,1,7,2,56,27,74,109,75,146,67,18,58,0,16,28,147,136,74,148,149,3,21,10,125,150,32,151,3,16,128,69,146,21,152,83,103,145,13,153,154,17,81,80,64,69,155,135,47,43,18,116,154,18,55,35,74,33,64,20,0,139,85,156,58,137,49,57,57,42,34,45,76,155,18,48,2,11,157,80,158,3,16,3,154,27,129,43,90,74,116,63,16,159,160,18,48,74,21,0,85,18,26,34,75,33,63,25,58,161,69,117,57,43,80,42,80,48,57,124,5,77,57,2,61,105,116,61,16,18,60,17,16,18,2,57,56,12,37,126,5,75,36,69,16,75,105,26,69,95,37,64,34,162,18,12,105,58,21,61,42,126,23,0,58,163,69,60,45,69,34,80,43,64,72,86,43,69,56,12,28,78,16,164,28,165,12,117,166,34,35,58,10,167,140,0,136,116,47,2,82,27,113,61,16,3,64,124,5,5,57,43,12,27,168,64,139,34,99,120,81,23,101,3,28,7,26,155,18,18,169,9,145,14,55,21,42,21,73,28,154,5,116,90,18,20,37,170,64,12,3,5,99,171,28,45,44,28,76,58,25,47,141,172,21,48,103,47,76,74,23,141,28,10,12,172,36,37,26,82,21,64,7,137,173,43,20,64,34,44,53,58,61,75,174,34,55,64,47,37,23,0,24,139,175,18,124,128,75,75,20,12,176,17,177,124,23,10,99,56,42,5,99,64,18,138,117,21,139,56,18,18,58,11,6,28,69,116,47,84,99,178,28,18,179,74,28,180,3,55,9,100,134,142,6,56,18,181,58,182,74,61,99,64,51,183,9,49,23,184,37,64,145,2,18,20,5,167,16,20,111,34,45,69,26,99,6,45,7,75,145,3,80,174,158,0,126,58,61,18,139,58,7,69,5,185,18,69,21,48,105,43,5,32,34,75,64,18,57,3,129,3,64,12,47,135,104,0,186,28,43,18,18,160,26,7,21,69,72,8,5,187,121,43,174,103,61,43,16,69,0,0,188,189,34,19,12,0,190,0,47,37,105,58,115,190,132,63,191,36,55,18,18,16,64,192,28,57,10,37,55,147,24,28,100,92,129,119,193,188,28,55,60,144,0,37,3,61,108,117,74,191,37,67,28,94,43,99,16,142,80,123,75,119,194,100,126,0,47,75,167,54,37,18,7,57,21,154,21,7,7,23,112,64,18,5,101,18,0,45,47,141,195,28,148,196,0,151,18,18,0,23,197,80,64,91,23,44,116,198,5,88,47,109,10,64,181,64,63,95,85,12,56,199,21,37,137,200,32,5,48,169,117,47,59,26,18,17,116,12,136,180,144,59,116,59,3,42,201,85,37,26,34,21,22,69,37,18,124,20,16,143,84,5,21,7,75,0,140,43,10,86,55,20,93,169,10,21,43,21,2,26,99,55,0,135,80,55,136,21,73,58,55,18,64,55,69,126,64,59,12,69,45,48,60,55,154,18,58,57,120,17,141,104,28,18,6,36,58,21,136,7,74,64,190,75,24,129,83,43,64,128,75,69,123,43,124,27,69,80,202,74,201,99,120,142,16,85,64,203,129,23,3,69,10,21,24,94,64,37,64,61,21,58,5,48,117,64,80,204,43,42,17,64,77,69,69,16,18,205,20,0,112,119,206,49,21,63,47,20,99,64,16,90,16,207,124,16,208,61,61,69,75,47,139,209,21,116,88,121,28,16,41,189,17,57,3,47,58,34,99,64,7,18,101,69,48,44,210,58,58,18,57,116,37,0,61,16,82,99,5,56,43,5,20,7,44,43,211,6,176,2,211,55,28,58,174,208,14,28,126,24,85,21,136,210,102,212,3,20,28,104,48,119,18,18,126,103,10,75,213,58,28,0,34,74,75,28,154,51,143,100,5,116,141,37,18,0,214,42,28,26,104,188,211,0,86,69,209,116,69,9,7,21,5,17,20,101,3,15,109,28,27,64,57,215,86,0,5,216,120,85,75,167,155,69,5,12,21,120,5,69,56,145,28,51,201,23,64,37,139,58,52,3,77,74,64,2,190,172,0,26,85,64,12,94,7,57,28,48,44,99,118,18,155,45,56,99,5,3,111,37,26,21,37,42,113,67,40,213,78,74,16,27,37,34,9,21,28,0,18,58,17,74,3,75,126,74,74,18,51,80,99,18,136,49,80,69,43,18,135,37,144,7,43,56,181,18,69,24,75,23,96,0,28,11,209,16,22,173,45,78,112,6,21,27,47,5,6,132,169,64,124,58,18,74,217,59,28,55,58,151,23,10,69,43,42,135,0,37,5,45,43,104,218,93,26,16,63,128,61,94,134,0,219,18,220,175,2,18,92,47,18,52,61,216,109,6,145,74,10,17,3,17,31,116,209,116,45,20,55,85,95,42,5,24,18,53,104,221,152,16,121,164,48,0,89,18,80,47,57,104,116,18,124,48,115,116,88,195,141,48,222,34,75,0,58,34,75,158,27,74,21,2,49,18,105,37,0,55,145,28,23,116,21,223,2,37,158,21,18,3,224,10,3,18,74,225,58,104,74,116,44,23,44,56,6,226,18,84,21,58,75,109,17,61,18,227,18,116,44,228,64,155,138,229,28,2,26,176,51,5,204,61,86,16,230,37,91,76,0,104,209,12,231,55,43,2,45,44,18,5,28,42,18,69,45,208,58,232,74,93,42,6,40,7,198,135,208,6,34,60,21,47,7,5,37,44,136,188,21,93,233,5,36,63,41,33,143,234,159,99,74,48,47,64,8,21,220,100,80,64,48,152,92,69,38,24,76,6,140,61,5,119,75,10,58,235,203,75,93,64,2,73,75,88,5,80,109,37,43,6,64,162,99,43,69,36,17,64,45,7,123,28,173,148,18,105,18,135,236,211,28,6,58,12,6,18,134,0,177,45,62,43,75,135,3,74,28,21,28,34,74,132,21,26,18,51,58,69,237,238,61,138,238,80,7,239,0,16,74,43,11,47,64,106,64,129,41,64,21,240,28,241,57,137,18,138,24,139,24,242,42,43,69,45,116,56,136,103,1,199,61,63,26,5,18,74,75,94,7,21,92,129,43,43,18,28,7,243,180,28,0,136,58,104,16,86,99,10,11,120,99,244,169,81,80,5,75,154,7,0,55,69,211,37,74,101,18,25,28,48,5,18,245,57,6,0,84,5,16,136,108,221,64,76,23,58,132,61,20,18,18,43,75,246,28,108,201,6,18,0,247,18,17,47,67,48,63,17,28,75,81,31,34,8,136,34,158,159,58,37,57,104,1,16,21,208,20,109,151,5,21,22,74,23,95,16,129,23,23,16,248,75,6,37,83,168,47,207,74,23,78,115,16,249,3,14,64,28,172,136,58,74,101,136,27,15,228,21,22,37,64,129,5,176,16,101,69,64,24,24,16,10,3,69,80,236,75,115,58,74,21,70,21,211,250,17,25,0,229,18,61,24,21,104,129,9,26,57,188,34,64,51,9,120,69,167,151,64,101,180,201,58,67,57,75,69,31,5,80,18,143,134,17,190,25,5,14,17,120,7,1,42,58,113,20,123,21,64,0,45,90,181,45,116,64,45,104,16,64,64,135,58,97,16,24,99,251,5,7,58,69,105,57,75,0,80,37,152,11,58,23,28,28,198,136,0,42,75,209,55,153,43,48,64,75,17,74,18,7,252,58,99,0,18,16,80,67,10,253,81,75,108,48,153,134,151,28,151,21,0,108,58,104,254,7,58,5,37,28,99,10,18,101,37,255,181,69,80,116,18,39,18,36,28,3,112,26,139,28,58,7,91,43,74,126,2,5,69,18,51,5,47,37,77,141,55,64,67,74,18,142,167,75,80,116,23,151,1,58,24,72,11,63,7,55,44,5,7,105,164,28,109,6,16,64,64,139,63,23,3,100,100,64,80,247,10,57,86,26,0,85,161,59,56,45,85,246,5,21,21,15,0,64,10,116,101,21,47,136,18,33,99,37,0,1,126,3,18,105,18,16,18,31,245,69,129,112,0,173,142,85,43,63,44,109,0,54,52,55,111,76,136,116,17,18,256,15,198,257,32,3,169,58,55,1,21,2,243,126,180,164,82,20,202,8,81,7,216,79,6,152,21,43,15,64,6,64,109,116,90,49,5,75,249,12,7,16,69,64,63,58,208,74,64,17,61,7,37,74,258,180,58,26,7,75,95,21,11,182,69,75,44,3,26,186,152,45,127,28,104,128,232,164,119,151,17,7,159,220,47,16,138,75,36,16,151,43,24,64,69,58,18,104,42,69,201,259,64,18,64,58,48,209,55,63,74,93,67,157,54,2,6,52,32,147,5,18,3,62,10,24,6,82,101,198,18,37,21,144,151,17,260,58,109,121,21,122,56,64,16,20,99,173,55,23,64,59,80,32,209,64,37,53,20,45,81,55,7,10,17,10,113,88,141,0,28,216,18,136,116,75,3,58,135,7,75,51,72,140,34,93,24,261,48,24,69,42,64,59,51,143,75,34,123,45,119,64,74,216,7,55,17,12,0,166,7,1,75,16,175,58,91,16,11,18,0,116,188,44,209,34,45,216,10,124,116,262,41,60,7,26,20,5,141,74,21,173,93,75,164,58,64,64,197,99,16,23,33,69,75,144,40,10,3,263,42,45,37,77,75,10,172,26,198,264,58,3,111,47,3,59,198,48,53,2,181,132,34,58,10,99,9,22,28,18,0,21,69,6,58,190,72,172,0,99,12,141,0,55,265,16,40,69,159,16,94,37,73,12,151,12,10,52,75,18,3,179,139,64,18,51,45,45,115,3,55,64,64,18,2,23,42,237,257,148,141,69,16,140,37,60,41,158,74,48,18,69,51,58,18,104,55,222,64,58,80,44,94,2,69,259,120,18,37,43,37,45,163,12,10,5,28,26,12,209,21,55,135,266,267,268,269,270,271,272,273,273,273,273,274,274,274,274,275,275,275,275],boxes:{menorah:{min:[-53.668,9.25,2.642],max:[-52.932,10.75,3.658]},menorahStep:{min:[-52.841,9.25,2.7],max:[-51.941,9.75,3.6]},shulchan:{min:[-53.522,9.25,-3.889],max:[-52.478,11.75,-3.111]},goldenAltar:{min:[-47.024,9.25,-.271],max:[-45.976,10.083,.271]},paroches:{min:[-55.934,9.28,-1.8],max:[-55.765,12.34,1.8]}},lamps:[[-53.3,10.75,2.7033],[-53.3,10.75,2.8385],[-53.3,10.75,2.9854],[-53.3018,10.75,3.15],[-53.3,10.75,3.3146],[-53.3,10.75,3.4615],[-53.3,10.75,3.5967]],fine:[2633,2635,2636,2637,2638,2639],precinct:{faces:{xWest:-33100,xEast:116900,yNorth:-33150,ySouth:116850},gates:[{id:"E",side:"E",along:0,name:"East gate",rule:"on the Temple east-west axis (Yechezkel 42:15 measures through the east gate)"},{id:"N",side:"N",along:0,name:"North gate (Tadi analogue)",rule:"on the Temple north-south axis (fig. 5'3 shows gate 5 beside the Sanctuary)"},{id:"W",side:"W",along:0,name:"West gate (Kiponus analogue)",rule:"ASSUMPTION: on the Temple east-west axis; the book gives no position"},{id:"S1",side:"S",along:16900,name:"South gate 1 (Chuldah analogue)",rule:"ASSUMPTION: at one third of the south wall (fig. 5'3 spaces the two gates along the side)"},{id:"S2",side:"S",along:66900,name:"South gate 2 (Chuldah analogue)",rule:"ASSUMPTION: at two thirds of the south wall"}],block:{pierWidth:10,openingWidth:10,openingHeight:50,totalHeight:60,depth:6},thicknessCm:300,heightCm:300,cmPerAmah:50}};var Ur={morning:{label:"Morning",elevation:24,azimuth:108,exposure:.62,turbidity:3.2,rayleigh:1.3},midday:{label:"Midday",elevation:62,azimuth:168,exposure:.52,turbidity:2.4,rayleigh:.9},afternoon:{label:"Late afternoon",elevation:20,azimuth:248,exposure:.64,turbidity:4.5,rayleigh:1.6},dusk:{label:"Dusk",elevation:6,azimuth:262,exposure:.95,turbidity:6,rayleigh:2.6}},s_=s=>new Promise((e,t)=>new cs().load(s,e,void 0,t));async function lm(s,e,t){let n=new tr,i=(await s_("assets/roof.png")).image,r=document.createElement("canvas");r.width=i.width,r.height=i.height;let a=r.getContext("2d",{willReadFrequently:!0});a.drawImage(i,0,0);let o=a.getImageData(0,0,r.width,r.height).data,c=new Uint16Array(r.width*r.height);for(let W=0;W<c.length;W++)c[W]=$r.toHalfFloat((o[W*4]*256+o[W*4+1])/65535*sm);let l=new rs(c,r.width,r.height,pr,zi);l.magFilter=l.minFilter=jt,l.needsUpdate=!0,t(.08);let u=rm(l,e),h=new Gc().setMeshoptDecoder(bp),d=await new Promise((W,de)=>h.load("assets/mikdash.glb",W,j=>{j.total&&t(.08+.72*(j.loaded/j.total))},de));t(.82);let f=new Gt,g=[];d.scene.traverse(W=>{if(!W.isMesh)return;let de=W.name,j=new at(W.geometry,u.byClass[de]||u.byClass.stone);j.name=de,j.castShadow=de!=="water"&&de!=="soreg",j.receiveShadow=!0,j.matrixAutoUpdate=!1,W.updateWorldMatrix(!0,!1),j.matrix.copy(W.matrixWorld),j.matrixWorld.copy(W.matrixWorld),de==="water"&&(j.renderOrder=2),f.add(j),g.push(j)}),n.add(f);let y=[],m=[],p=new L,x=new Set(Ci.fine);for(let W of g){if(W.name==="water")continue;let de=W.geometry,j=de.attributes.position,re=de.attributes._oid,Ie=de.index,Te=Ie?Ie.count:j.count;for(let k=0;k<Te;k+=3){let E=Ie?Ie.getX(k):k,O=re?re.getX(E):0;if(!x.has(O)){for(let q=0;q<3;q++){let ee=Ie?Ie.getX(k+q):k+q;p.fromBufferAttribute(j,ee).applyMatrix4(W.matrixWorld),y.push(p.x,p.y,p.z)}m.push(O)}}}let v={menorah:"Menorah",shulchan:"Shulchan",goldenAltar:"Golden altar",paroches:"Paroches"},b=W=>Ci.index.findIndex(de=>Ci.names[de][0]===W);for(let[W,de]of Object.entries(Ci.boxes)){if(!v[W])continue;let j=new L(...de.min),re=new L(...de.max);W==="paroches"&&(j.x-=.25,re.x+=.25,j.z-=.3,re.z+=.3,re.y+=.4);let Ie=new Xn(re.x-j.x,re.y-j.y,re.z-j.z).toNonIndexed();Ie.translate((re.x+j.x)/2,(re.y+j.y)/2,(re.z+j.z)/2);let Te=b(v[W]),k=Ie.attributes.position;for(let E=0;E<k.count;E++)y.push(k.getX(E),k.getY(E),k.getZ(E));for(let E=0;E<k.count/3;E++)m.push(Te)}t(.9);let S=(()=>{let j=[],re=[];for(let Te=0;Te<=56;Te++){let k=Te===0?0:12*Math.pow(500,(Te-1)/55);for(let E=0;E<96;E++){let O=E/96*Math.PI*2;j.push(Math.cos(O)*k,0,Math.sin(O)*k)}}for(let Te=0;Te<56;Te++)for(let k=0;k<96;k++){let E=Te*96+k,O=Te*96+(k+1)%96,q=E+96,ee=O+96;Te>0&&re.push(E,O,q),re.push(O,ee,q)}let Ie=new Bt;return Ie.setAttribute("position",new Tt(j,3)),Ie.setAttribute("normal",new Tt(new Float32Array(j.length).map((Te,k)=>k%3===1?1:0),3)),Ie.setIndex(re),Ie})(),w=new at(S,u.ground);w.position.y=-.02,w.receiveShadow=!0,n.add(w);let T=u.byClass.stone.clone();T.onBeforeCompile=u.byClass.stone.onBeforeCompile,T.customProgramCacheKey=u.byClass.stone.customProgramCacheKey,T.vertexColors=!1,T.color.set(11573874);{let W=Ci.precinct,de=W.faces,j=.01,re=W.cmPerAmah*j,Ie=W.thicknessCm*j,Te=W.heightCm*j,k=(W.block.openingWidth/2+W.block.pierWidth)*re,E=W.block.openingWidth/2*re,O=W.block.totalHeight*re,q=W.block.openingHeight*re,ee=de.xWest*j,K=de.xEast*j,Me=de.yNorth*j,he=de.ySouth*j,Ee=[],Pe={W:{fixed:ee+Ie/2,from:Me,to:he,alongZ:!0},E:{fixed:K-Ie/2,from:Me,to:he,alongZ:!0},N:{fixed:Me+Ie/2,from:ee,to:K,alongZ:!1},S:{fixed:he-Ie/2,from:ee,to:K,alongZ:!1}};for(let[ge,De]of Object.entries(Pe)){let Ae=W.gates.filter(F=>F.side===ge).map(F=>F.along*j).sort((F,se)=>F-se),pe=(F,se,ce,xe)=>{if(se-F<.01)return;let ie=(F+se)/2,$=se-F;Ee.push(De.alongZ?[De.fixed,(ce+xe)/2,ie,Ie,xe-ce,$]:[ie,(ce+xe)/2,De.fixed,$,xe-ce,Ie])},Ve=De.from;for(let F of Ae)pe(Ve,F-k,0,Te),pe(F-k,F-E,0,O),pe(F+E,F+k,0,O),pe(F-E,F+E,q,O),Ve=F+k;pe(Ve,De.to,0,Te)}let oe=new Gt;for(let[ge,De,Ae,pe,Ve,F]of Ee){let se=new Xn(pe,Ve,F),ce=new at(se,T);ce.position.set(ge,De,Ae),ce.castShadow=!0,ce.receiveShadow=!0,ce.updateMatrixWorld(),oe.add(ce);let ie=se.toNonIndexed().applyMatrix4(ce.matrixWorld).attributes.position;for(let $=0;$<ie.count;$++)y.push(ie.getX($),ie.getY($),ie.getZ($));for(let $=0;$<ie.count/3;$++)m.push(-2)}n.add(oe)}let A=3e3;y.push(-A,0,-A,-A,0,A,A,0,A,-A,0,-A,A,0,A,A,0,-A),m.push(-1,-1);let M=new Bt;M.setAttribute("position",new xt(new Float32Array(y),3));let _=new fl(M,{indirect:!0});M.boundsTree=_;let I=new at(M,new nn);{let W=new os(4200,4200,1,160,6,!0),de=W.attributes.position,j=new Float32Array(de.count*3),re=Te=>Math.sin(Te*3.1)*.5+Math.sin(Te*7.7+1.3)*.28+Math.sin(Te*17.3+4.1)*.14+Math.sin(Te*41+2)*.06;for(let Te=0;Te<de.count;Te++){let k=de.getX(Te),E=de.getZ(Te),O=Math.atan2(E,k),q=de.getY(Te)+.5,ee=170+150*re(O),K=4200-(1-q)*1500;de.setXYZ(Te,Math.cos(O)*K,q*q*ee-6,Math.sin(O)*K);let Me=.5+.2*q;j.set([.62*Me,.6*Me,.5*Me],Te*3)}W.setAttribute("color",new xt(j,3)),W.computeVertexNormals();let Ie=new at(W,new pa({vertexColors:!0,side:Dt}));n.add(Ie)}let C=new wr;C.scale.setScalar(2e4),C.material.uniforms.mieCoefficient.value=.004,C.material.uniforms.mieDirectionalG.value=.82,n.add(C);let D=new us(16777215,3);D.castShadow=!0;let N=e==="high"?4096:e==="medium"?2048:1024;D.shadow.mapSize.set(N,N);let U=e==="low"?55:80;Object.assign(D.shadow.camera,{left:-U,right:U,top:U,bottom:-U,near:10,far:520});let B=2*U/N;D.shadow.normalBias=B*1.6,n.add(D,D.target);let J=new ba(16773856,13150328,.5);n.add(J),n.fog=new ia(14212576,28e-5);let V=new xr(s),ne=new tr,ue=new wr;ue.scale.setScalar(1e3),ne.add(ue);let _e=new at(new da(900,24).rotateX(-Math.PI/2),new nn({color:9075292}));_e.position.y=-2,ne.add(_e);let ze=null,$e=new L,ht="morning";function Ye(W){let de=Ur[W]||Ur.morning;ht=Ur[W]?W:"morning";let j=Ct.degToRad(90-de.elevation),re=Ct.degToRad(de.azimuth);$e.set(Math.sin(j)*Math.sin(re),Math.cos(j),-Math.sin(j)*Math.cos(re));for(let Te of[C,ue]){let k=Te.material.uniforms;k.sunPosition.value.copy($e),k.turbidity.value=de.turbidity,k.rayleigh.value=de.rayleigh}let Ie=Ct.clamp(1-de.elevation/45,0,1);D.color.setRGB(1,1-.28*Ie,1-.55*Ie),D.intensity=3.4*Ct.clamp(de.elevation/9,.12,1),D.shadow.bias=-Math.min(.004,B/Math.tan(Ct.degToRad(de.elevation))/510*1.5),J.intensity=.5+.2*(1-Ie),J.color.setRGB(1,.95-.03*Ie,.9-.1*Ie),n.fog.color.setRGB(.84+.1*Ie,.86-.08*Ie,.88-.22*Ie),Se=de.exposure,s.toneMappingExposure=Se*(1+1.5*Fe),ze&&ze.dispose(),ze=V.fromScene(ne,0,1,2e3),n.environment=ze.texture,n.environmentIntensity=.22,Q.setSun($e,de)}let Q=cm(n,Ci,e),te=2*U/N,ve=new Sn(new L,new L(0,1,0)),Fe=0,Se=.6;function je(W,de,j){u.uniforms.uTime.value=de,ve.origin.copy(j);let re=_.raycastFirst(ve,Mt,0,70)?1:0;Fe+=(re-Fe)*Math.min(1,W*1.6),s.toneMappingExposure=Se*(1+1.5*Fe);let Ie=Math.round(j.x/te)*te,Te=Math.round(j.z/te)*te;D.target.position.set(Ie,0,Te),D.position.copy(D.target.position).addScaledVector($e,260),D.target.updateMatrixWorld(),Q.update(W,de,j)}let Z=new Sn,P=new L(0,-1,0);function ae(W,de,j){Z.origin.set(W,de,j),Z.direction.copy(P);let re=_.raycastFirst(Z,Mt);return re?re.point.y:null}function me(W,de){let j=p.subVectors(de,W),re=j.length();return re<1e-4?!0:(Z.origin.copy(W),Z.direction.copy(j).divideScalar(re),!_.raycastFirst(Z,Mt,0,re))}function fe(W,de=250){let j=_.raycastFirst(W,Mt,0,de);if(!j)return null;let re=m[j.faceIndex];if(re===-2)return{name:"Wall of the Mount",part:"mount",point:j.point,distance:j.distance};if(re==null||re<0)return{name:"Paving of the Mount",part:"mount",point:j.point,distance:j.distance};let[Ie,Te]=Ci.names[Ci.index[re]];return{name:Ie,part:Te,point:j.point,distance:j.distance}}return Ye("morning"),t(1),{scene:n,collider:I,bvh:_,mats:u,effects:Q,setTime:Ye,update:je,groundBelow:ae,segmentClear:me,identify:fe,get timeKey(){return ht},triangles:y.length/9}}var pl=1.62,Wu=1.78,r_=.3,Yu=.62,a_=24,hm=3.4,um=8.2,o_=13,dm=34,ml=[-700,1500];function fm(s,e){let t=new L(96,0,0),n=new L,i=Math.PI/2,r=0,a=0,o=!0,c="walk",l=0,u=!1,h=0,d=e.bvh,f=new Zt,g=new ot,y=new L,m=new L,p=new L,x=new L,v=new L,b=new tn;function S(C,D,N,U){f.start.set(t.x,t.y+C+N,t.z),f.end.set(t.x,t.y+D-N,t.z);let B=f.start.x,J=f.start.y,V=f.start.z;return g.makeEmpty(),g.expandByPoint(f.start),g.expandByPoint(f.end),g.min.addScalar(-N),g.max.addScalar(N),d.shapecast({intersectsBounds:ne=>ne.intersectsBox(g),intersectsTriangle:ne=>{let ue=ne.closestPointToSegment(f,y,m);if(ue<N&&ue>1e-7){let _e=N-ue;p.subVectors(m,y).multiplyScalar(_e/ue),f.start.add(p),f.end.add(p)}}}),U.set(f.start.x-B,f.start.y-J,f.start.z-V)}let w=new L;function T(C,D){let N=o?16:4;if(n.x+=(D.x-n.x)*Math.min(1,N*C),n.z+=(D.z-n.z)*Math.min(1,N*C),t.x+=n.x*C,t.z+=n.z*C,S(Yu,Wu,r_,w),t.x+=w.x,t.z+=w.z,w.lengthSq()>1e-10){let B=p.set(w.x,0,w.z);if(B.lengthSq()>1e-10){B.normalize();let J=n.x*B.x+n.z*B.z;J<0&&(n.x-=B.x*J,n.z-=B.z*J)}}let U=e.groundBelow(t.x,t.y+Yu+.05,t.z);U!==null&&a<=.01&&U>=t.y-(o?Yu:.02)?(U>t.y+.001?h=Math.min(.6,h+(U-t.y)):o&&U<t.y-.001&&(h=Math.max(-.6,h-(t.y-U))),t.y=U,a=0,o=!0):(o=!1,a-=a_*C,t.y+=a*C,a>0&&(S(Wu-.5,Wu+.1,.2,w),w.y<-1e-4&&(t.y+=w.y,a=0)),U!==null&&t.y<=U&&(t.y=U,a=0,o=!0),t.y<-50&&(t.y=0,a=0))}function A(C,D){n.x+=(D.x-n.x)*Math.min(1,5*C),n.y+=(D.y-n.y)*Math.min(1,5*C),n.z+=(D.z-n.z)*Math.min(1,5*C),t.addScaledVector(n,C),b.center.set(t.x,t.y+pl,t.z),b.radius=.45;let N=p.copy(b.center),U=N.x,B=N.y,J=N.z;d.shapecast({intersectsBounds:V=>V.intersectsSphere(b),intersectsTriangle:V=>{V.closestPointToPoint(b.center,y);let ne=y.distanceTo(b.center);ne<b.radius&&ne>1e-7&&(m.subVectors(b.center,y).multiplyScalar((b.radius-ne)/ne),b.center.add(m))}}),t.x+=b.center.x-U,t.y+=b.center.y-B,t.z+=b.center.z-J,t.y=Ct.clamp(t.y,-pl+.5,260)}function M(C,D){i+=D.lookX,r=Ct.clamp(r+D.lookY,-1.45,1.45),x.set(-Math.sin(i),0,-Math.cos(i)),v.set(Math.cos(i),0,-Math.sin(i));let N=new L;if(c==="walk"){let J=D.run?um:hm;N.addScaledVector(x,D.moveZ*J).addScaledVector(v,D.moveX*J),D.jump&&o&&(a=6.2,o=!1);let V=Math.max(1,Math.ceil(um*C/.2));for(let ne=0;ne<V;ne++)T(C/V,N)}else{let J=D.run?dm:o_,V=Math.cos(r);N.set(x.x*V,Math.sin(r),x.z*V).multiplyScalar(D.moveZ*J),N.addScaledVector(v,D.moveX*J),N.y+=((D.up?1:0)-(D.down?1:0))*J*.7;let ne=Math.max(1,Math.ceil(dm*C/.3));for(let ue=0;ue<ne;ue++)A(C/ne,N)}t.x=Ct.clamp(t.x,ml[0],ml[1]),t.z=Ct.clamp(t.z,ml[0],ml[1]);let U=Math.hypot(n.x,n.z);h*=Math.exp(-C*11);let B=pl-h;return c==="walk"&&o&&!u&&(l+=C*U*1.9,B+=Math.sin(l*2)*.022*Math.min(1,U/hm)),s.position.set(t.x,t.y+B,t.z),s.rotation.set(r,i,0,"YXZ"),U}function _(C,D,N){t.copy(C),n.set(0,0,0),a=0,h=0,o=c==="walk",D!==void 0&&(i=D),N!==void 0&&(r=N)}function I(C){C!==c&&(c=C,n.set(0,0,0),a=0,C==="fly"&&(t.y+=.6,o=!1))}return{update:M,setPose:_,setMode:I,get mode(){return c},get position(){return t},get yaw(){return i},get pitch(){return r},get onGround(){return o},set reduceMotion(C){u=C},EYE:pl}}function Xu(s,e){let t=e.x-s.x,n=e.y-s.y,i=e.z-s.z;return{yaw:Math.atan2(-t,-i),pitch:Math.atan2(n,Math.hypot(t,i))}}function pm(s,e,t){let n={moveX:0,moveZ:0,lookX:0,lookY:0,run:!1,up:!1,down:!1,jump:!1,touch:!1},i=new Set,r={sensitivity:1,invertY:!1,...t},a=!0,o={tap:[],action:[],firstInput:[]},c=(w,...T)=>o[w].forEach(A=>A(...T)),l=!1,u=()=>{l||(l=!0,c("firstInput"))},h={KeyF:"fly",KeyM:"map",KeyT:"tour",KeyH:"help",Slash:"help",BracketRight:"next",BracketLeft:"prev",KeyN:"next",KeyP:"prev",Escape:"escape",KeyG:"go"},d=w=>/INPUT|TEXTAREA|SELECT/.test(w.target.tagName)||w.target.isContentEditable;window.addEventListener("keydown",w=>{if(!(d(w)||w.metaKey||w.ctrlKey||w.altKey)){if(w.code==="Escape"){c("action","escape");return}a&&((w.code==="Space"||w.code==="Enter")&&w.target.closest&&w.target.closest('button, a, [role="button"]')||(i.add(w.code),h[w.code]&&!w.repeat&&c("action",h[w.code]),w.code==="Space"&&!w.repeat&&(n.jump=!0),/^(Arrow|Space)/.test(w.code)&&w.preventDefault(),u()))}}),window.addEventListener("keyup",w=>i.delete(w.code)),window.addEventListener("blur",()=>{i.clear(),m()}),document.addEventListener("visibilitychange",()=>{document.hidden&&(i.clear(),m())});let f=new Map,g=null,y=56;function m(){g=null,n.stickX=0,n.stickY=0,e.classList.remove("on")}n.stickX=0,n.stickY=0,s.addEventListener("pointerdown",w=>{if(!a||w.pointerType==="mouse"&&w.button!==0)return;s.setPointerCapture?.(w.pointerId);let T={x0:w.clientX,y0:w.clientY,x:w.clientX,y:w.clientY,t0:performance.now(),moved:0,kind:"look",type:w.pointerType};w.pointerType==="touch"&&(n.touch=!0,w.clientX<window.innerWidth*.45&&w.clientY>window.innerHeight*.3&&g===null&&(T.kind="stick",g=w.pointerId,e.style.left=`${w.clientX}px`,e.style.top=`${w.clientY}px`,e.style.setProperty("--kx","0px"),e.style.setProperty("--ky","0px"),e.classList.add("on"))),f.set(w.pointerId,T),u()}),s.addEventListener("pointermove",w=>{if(document.pointerLockElement===s){n.lookX-=w.movementX*.0022*r.sensitivity,n.lookY-=w.movementY*.0022*r.sensitivity*(r.invertY?-1:1);return}let T=f.get(w.pointerId);if(!T)return;let A=w.clientX-T.x,M=w.clientY-T.y;if(T.x=w.clientX,T.y=w.clientY,T.moved+=Math.abs(A)+Math.abs(M),T.kind==="stick"){let _=T.x-T.x0,I=T.y-T.y0,C=Math.hypot(_,I);C>y&&(_*=y/C,I*=y/C),e.style.setProperty("--kx",`${_}px`),e.style.setProperty("--ky",`${I}px`),n.stickX=_/y,n.stickY=-I/y}else{let _=(T.type==="touch"?.0052:.0036)*r.sensitivity;n.lookX-=A*_,n.lookY-=M*_*(r.invertY?-1:1)}});let p=w=>{let T=f.get(w.pointerId);T&&(f.delete(w.pointerId),T.kind==="stick"?m():w.type==="pointerup"&&T.moved<8&&performance.now()-T.t0<350&&c("tap",w.clientX,w.clientY))};s.addEventListener("pointerup",p),s.addEventListener("pointercancel",p),s.addEventListener("lostpointercapture",p),s.addEventListener("contextmenu",w=>w.preventDefault()),s.addEventListener("dblclick",()=>{a&&!n.touch&&s.requestPointerLock&&s.requestPointerLock()});function x(w){let T=0,A=0;(i.has("KeyW")||i.has("ArrowUp"))&&(A+=1),(i.has("KeyS")||i.has("ArrowDown"))&&(A-=1),i.has("KeyD")&&(T+=1),i.has("KeyA")&&(T-=1);let M=(i.has("ArrowLeft")?1:0)-(i.has("ArrowRight")?1:0);n.lookX+=M*1.9*w;let _=i.has("ShiftLeft")||i.has("ShiftRight"),I=i.has("Space")||i.has("KeyE"),C=i.has("KeyQ")||i.has("KeyC");T+=n.stickX,A+=n.stickY,Math.hypot(n.stickX,n.stickY)>.96&&(_=!0);let D=navigator.getGamepads?navigator.getGamepads():[];for(let B of D){if(!B||!B.connected)continue;let J=V=>Math.abs(V)<.16?0:V;T+=J(B.axes[0]||0),A-=J(B.axes[1]||0),n.lookX-=J(B.axes[2]||0)*2.4*w*r.sensitivity,n.lookY-=J(B.axes[3]||0)*1.8*w*r.sensitivity*(r.invertY?-1:1),(B.buttons[7]?.pressed||B.buttons[10]?.pressed)&&(_=!0),B.buttons[0]?.pressed&&(I=!0),B.buttons[1]?.pressed&&(C=!0);break}v&&(I=!0),b&&(C=!0);let N=Math.hypot(T,A);N>1&&(T/=N,A/=N);let U={moveX:a?T:0,moveZ:a?A:0,run:_,up:a&&I,down:a&&C,lookX:n.lookX,lookY:n.lookY,jump:a&&n.jump};return n.lookX=0,n.lookY=0,n.jump=!1,U}let v=!1,b=!1;function S(w,T){let A=_=>{_.preventDefault(),T(!0),u()},M=()=>T(!1);w.addEventListener("pointerdown",A),w.addEventListener("pointerup",M),w.addEventListener("pointercancel",M),w.addEventListener("pointerleave",M)}return{read:x,settings:r,on:(w,T)=>o[w].push(T),setEnabled(w){a=w,w||(i.clear(),m(),f.clear())},bindAscend:w=>S(w,T=>{v=T}),bindDescend:w=>S(w,T=>{b=T}),get isTouch(){return n.touch}}}var Le=s=>document.getElementById(s);function G(s,e,...t){let n=document.createElement(s);if(e)for(let[i,r]of Object.entries(e))r==null||r===!1||(i==="class"?n.className=r:i==="text"?n.textContent=r:i.startsWith("on")?n.addEventListener(i.slice(2),r):n.setAttribute(i,r===!0?"":r));for(let i of t.flat())i==null||i===!1||n.append(i.nodeType?i:document.createTextNode(String(i)));return n}var c_={ulam:"Ulam",heichal:"Heikhal",kodesh:"Kodesh HaKodashim",altar:"The altar",gates:"Gates",outer:"Outer court",inner:"Inner court",cells:"Side cells of the House",galleries:"Galleries",kitchens:"Cooking courts",priest:"Chambers of the kohanim",vessel:"Kiyor",mixed:"The House",mount:"The Mount"},l_=s=>Number.isInteger(s)?String(s):String(+s.toFixed(2)),h_=s=>{let e=s/100;return e>=100?`${Math.round(e)} m`:e>=10?`${+e.toFixed(1)} m`:e>=1?`${+e.toFixed(2)} m`:`${+s.toFixed(1)} cm`};function mm({tour:s,codex:e,actions:t,settings:n,times:i}){let r=s.stops,a=new Map(e.entries.map(Z=>[Z.id,Z])),o=Le("sheet"),c=Le("sheet-body"),l=Le("scrim"),u=0,h=new Set,d=null,f=null,g=null,y=0;function m(Z,P){let ae=Math.round(Z*100);Le("loadbar").firstElementChild.style.width=`${ae}%`,Le("loadbar").setAttribute("aria-valuenow",ae),P&&(Le("loadnote").textContent=P)}function p(){Le("welcome").classList.remove("loading"),Le("loadbar").hidden=!0,Le("loadnote").hidden=!0,Le("w-actions").hidden=!1,Le("w-tour").focus({preventScroll:!0})}function x(Z){Le("loadbar").hidden=!0,Le("loadnote").textContent=Z,Le("loadnote").style.color="#f0b9a0"}Le("w-tour").addEventListener("click",()=>t.start("tour")),Le("w-free").addEventListener("click",()=>t.start("free"));function v(Z){Le("welcome").classList.add("gone"),Le("hud").hidden=!1,Le("tourcard").classList.toggle("min",!Z),Le("view").focus({preventScroll:!0})}function b(Z,P,ae,{wide:me=!1,back:fe=null}={}){d||(g=document.activeElement),clearInterval(y),d=Z,f=fe,Le("sheet-title").textContent=P,Le("sheet-back").hidden=!fe,o.classList.toggle("wide",me),c.replaceChildren(...[ae].flat()),c.scrollTop=0,o.hidden=!1,l.hidden=!1,t.panel(!0),Le("sheet-close").focus({preventScroll:!0})}function S(){return d?(clearInterval(y),d=null,o.hidden=!0,l.hidden=!0,t.panel(!1),(g&&g.isConnected?g:Le("view")).focus({preventScroll:!0}),!0):!1}Le("sheet-close").addEventListener("click",S),Le("sheet-back").addEventListener("click",()=>f&&f()),l.addEventListener("click",S),o.addEventListener("keydown",Z=>{if(Z.key!=="Tab")return;let P=[...o.querySelectorAll('button, a[href], input, [tabindex]:not([tabindex="-1"])')].filter(fe=>!fe.hidden&&fe.offsetParent!==null);if(!P.length)return;let ae=P[0],me=P[P.length-1];Z.shiftKey&&document.activeElement===ae?(Z.preventDefault(),me.focus()):!Z.shiftKey&&document.activeElement===me&&(Z.preventDefault(),ae.focus())});let w=Z=>G("span",{class:`badge ${Z}`,title:s.confidenceLabels[Z]||""},Z==="certain"?"Sources agree":Z==="disputed"?"Disputed":"Project\u2019s choice");function T(Z,P){u=Z,P&&(h=P);let ae=r[Z];Le("t-count").textContent=`Stop ${Z+1} of ${r.length}`,Le("t-name").textContent=ae.name,Le("t-he").textContent=ae.he||"",Le("t-sub").textContent=ae.subtitle||"",Le("t-prev").disabled=Z===0,Le("t-next").disabled=Z===r.length-1}function A(Z){Le("t-go").textContent=Z?"You are here":"Take me there",Le("t-go").disabled=Z,Le("t-go").style.opacity=Z?.6:1}Le("t-prev").addEventListener("click",()=>t.selectStop(u-1,!0)),Le("t-next").addEventListener("click",()=>t.selectStop(u+1,!0)),Le("t-go").addEventListener("click",()=>t.goStop(u)),Le("t-read").addEventListener("click",()=>_(u));function M(Z){return G("table",{class:"measures"},G("tbody",null,Z.map(P=>G("tr",null,G("td",null,P.label,P.source?G("small",null,P.source):null),G("td",{class:"num"},P.amot!=null?G("span",{class:"amot"},`${l_(P.amot)} amot`):P.value||"",P.cm!=null?G("small",null,h_(P.cm)):null)))))}function _(Z,P){let ae=r[Z],me=ae.codex.map(W=>a.get(W)).filter(Boolean),fe=[ae.he?G("p",{class:"stop-he",lang:"he",dir:"rtl"},ae.he):null,G("p",{class:"stop-sub"},ae.subtitle," ",w(ae.confidence)),G("h3",null,"What happens here"),G("p",{class:"big"},ae.what),ae.measurements.length?[G("h3",null,"Measurements"),M(ae.measurements)]:null,G("h3",null,"How it was built"),G("p",null,ae.explanation),me.length?[G("h3",null,"Read further"),G("ul",{class:"rows"},me.map(W=>G("li",null,G("button",{class:"row",onclick:()=>D(W.id,()=>_(Z,P))},G("span",{class:"t"},G("b",null,W.name)),G("span",{class:"chev"},"\u203A")))))]:null,G("h3",null,"Sources"),G("ul",{class:"sources"},ae.sources.map(W=>G("li",null,W))),G("div",{class:"stack"},G("button",{class:"btn primary small",onclick:()=>{S(),t.goStop(Z)}},"Take me there"),Z<r.length-1?G("button",{class:"btn small",onclick:()=>{t.selectStop(Z+1,!1),_(Z+1,P)}},"Next stop \u203A"):null)];b("stop",`${Z+1}. ${ae.name}`,fe,{back:P==="list"?I:null})}function I(){let Z=[G("p",null,s.description),G("ul",{class:"rows"},r.map((P,ae)=>G("li",null,G("button",{class:`row${ae===u?" current":""}${h.has(ae)?" seen":""}`,onclick:()=>{t.selectStop(ae,!1),_(ae,"list")}},G("span",{class:"n"},h.has(ae)?"\u2713":ae+1),G("span",{class:"t"},G("b",null,P.name),G("span",null,P.subtitle)),P.he?G("span",{class:"h",lang:"he",dir:"rtl"},P.he):null)))),G("h3",null,"Good to know"),s.limitations.slice(1).map(P=>G("p",null,P))];b("stops",s.name,Z)}function C(){let Z=G("div"),P=me=>{let fe=me.trim().toLowerCase(),W=[];for(let de of e.categories){let j=e.entries.filter(re=>re.category===de.id&&(!fe||re.name.toLowerCase().includes(fe)||re.summary.toLowerCase().includes(fe)||re.he&&re.he.includes(me.trim())));j.length&&(W.push(G("h3",null,de.name.en)),W.push(G("ul",{class:"rows"},j.map(re=>G("li",null,G("button",{class:"row",onclick:()=>D(re.id,C)},G("span",{class:"t"},G("b",null,re.name)),re.he?G("span",{class:"h",lang:"he",dir:"rtl"},re.he):null,G("span",{class:"chev"},"\u203A")))))))}W.length||W.push(G("p",null,"Nothing matches that search.")),Z.replaceChildren(...W)},ae=G("input",{class:"search",type:"search",placeholder:"Search the notes\u2026","aria-label":"Search the notes",oninput:me=>P(me.target.value)});P(""),b("codex","Sources and notes",[G("p",null,`${e.entries.length} notes on what the sources say, where they disagree, and what this model chose.`),ae,Z])}function D(Z,P){let ae=a.get(Z);ae&&b("codex-entry",ae.name,[ae.he?G("p",{class:"stop-he",lang:"he",dir:"rtl"},ae.he):null,G("p",{class:"stop-sub"},w(ae.confidence)),G("p",{class:"big"},ae.summary),ae.measurements.length?[G("h3",null,"Measurements"),M(ae.measurements)]:null,ae.dispute.length?[G("h3",null,"Who holds what"),G("table",{class:"measures"},G("tbody",null,ae.dispute.map(me=>G("tr",null,G("td",null,me.who),G("td",{class:"num",style:"white-space:normal;max-width:60%"},me.holds)))))]:null,ae.sources.length?[G("h3",null,"Sources"),G("ul",{class:"sources"},ae.sources.map(me=>G("li",null,me)))]:null],{back:P})}let N=100,U=(Z,P)=>({left:`${(Z+N)/(2*N)*100}%`,top:`${(P+N)/(2*N)*100}%`});function B(){let Z=G("div",{class:"you"}),P=G("div",{class:"plan-wrap"},G("img",{src:"assets/plan.png",alt:"Plan of the Beis HaMikdash seen from above, north at the top",draggable:"false"}),G("span",{class:"plan-north"},"N \u2191")),ae=[];r.forEach((fe,W)=>{let[de,,j]=fe.stand,re=`pin${h.has(W)?" seen":""}${W===u?" current":""}`,Ie=()=>{S(),t.selectStop(W,!1),t.goStop(W)};if(Math.abs(de)>N-3||Math.abs(j)>N-3){ae.push(G("button",{class:"btn small",onclick:Ie},`${W+1}. ${fe.name}`));return}let Te=G("button",{class:re,"aria-label":`Stop ${W+1}: ${fe.name}`,title:fe.name,onclick:Ie},W+1);Object.assign(Te.style,U(de,j)),P.append(Te)}),P.append(Z);let me=()=>{let fe=t.playerPose(),W=Math.max(-N+2,Math.min(N-2,fe.x)),de=Math.max(-N+2,Math.min(N-2,fe.z));Object.assign(Z.style,U(W,de)),Z.style.transform=`rotate(${-fe.yaw}rad)`};me(),b("map","Plan of the Mikdash",[G("p",null,"Tap a numbered stop to go there. The red arrow is you."),P,ae.length?[G("h3",null,"Stops outside the walls"),G("div",{class:"plan-edge"},ae)]:null],{wide:!0}),y=setInterval(me,250)}function J(Z,P,ae){let me=G("div",{class:"seg",role:"group"}),fe=W=>me.replaceChildren(...Z.map(([de,j])=>G("button",{"aria-pressed":String(de===W),onclick:()=>{fe(de),ae(de)}},j)));return fe(P),me}function V(){let Z=n.get();b("settings","Settings",[G("div",{class:"field"},G("span",{class:"label"},"Time of day"),J(Object.entries(i).map(([P,ae])=>[P,ae.label]),Z.time,P=>n.set("time",P))),G("div",{class:"field"},G("span",{class:"label"},"Picture quality"),J([["auto","Auto"],["low","Low"],["medium","Medium"],["high","High"]],Z.quality,P=>n.set("quality",P)),G("p",{class:"note"},"Auto picks for this device and lowers the resolution if the picture stutters. Changing this reloads the page.")),G("div",{class:"field"},G("label",{for:"set-sens"},"Look speed"),G("input",{id:"set-sens",type:"range",min:"0.4",max:"2.2",step:"0.1",value:String(Z.sensitivity),oninput:P=>n.set("sensitivity",+P.target.value)})),G("div",{class:"field"},G("label",{class:"check"},G("input",{type:"checkbox",checked:Z.invertY,onchange:P=>n.set("invertY",P.target.checked)}),"Invert up and down"),G("label",{class:"check"},G("input",{type:"checkbox",checked:Z.reduceMotion,onchange:P=>n.set("reduceMotion",P.target.checked)}),"Reduce motion (no head bob, no gliding between stops)"),G("label",{class:"check"},G("input",{type:"checkbox",checked:Z.showTour,onchange:P=>n.set("showTour",P.target.checked)}),"Show the tour card")),G("div",{class:"stack"},G("button",{class:"btn small",onclick:()=>{S(),t.restart()}},"Return to the east gate"),G("button",{class:"btn small",onclick:()=>{S(),t.share()}},"Copy a link to this spot"))])}function ne(){let Z=(...P)=>P.map(ae=>G("kbd",null,ae));b("help","How to move",[G("h3",null,"On a phone or tablet"),G("table",{class:"keys"},G("tbody",null,G("tr",null,G("td",null,"Walk"),G("td",null,"Press the left side of the screen and slide your thumb. Push all the way to hurry.")),G("tr",null,G("td",null,"Look"),G("td",null,"Drag anywhere else.")),G("tr",null,G("td",null,"Name it"),G("td",null,"Tap any part of the building to see what it is.")))),G("h3",null,"With a keyboard and mouse"),G("table",{class:"keys"},G("tbody",null,G("tr",null,G("td",null,Z("W","A","S","D")),G("td",null,"Walk. Arrow keys also work.")),G("tr",null,G("td",null,"Drag"),G("td",null,"Look around. Double-click to capture the mouse, Esc to release it.")),G("tr",null,G("td",null,Z("Shift")),G("td",null,"Hurry")),G("tr",null,G("td",null,Z("Space")),G("td",null,"Jump, or rise when flying")),G("tr",null,G("td",null,Z("F")),G("td",null,"Fly as a dove, and land again")),G("tr",null,G("td",null,Z("Q","E")),G("td",null,"Descend and rise when flying")),G("tr",null,G("td",null,Z("[","]")),G("td",null,"Previous and next tour stop")),G("tr",null,G("td",null,Z("G")),G("td",null,"Go to the selected stop")),G("tr",null,G("td",null,Z("M")," ",Z("T")),G("td",null,"Plan, and the list of stops")))),G("h3",null,"About this model"),G("p",null,"The building is the measured reconstruction from this project: ",G("b",null,"2,633 parts")," placed from Yechezkel 40\u201348 with Rashi, Mishnah Middos, Rambam and the sefer Lishchno Tidreshu. One amah is drawn as 50 cm."),G("p",null,"Nothing here is a ruling. Where the sources disagree the notes say who holds what, and where nobody says, the notes say the project chose. The paroches is closed, and the model does not show what is behind it."),G("p",null,"This is the light version that runs in a browser. The full Windows walkthrough has the city, people and sound.")])}let ue=0;function _e(Z,P=2600){let ae=Le("toast");ae.textContent=Z,ae.classList.add("on"),clearTimeout(ue),ue=setTimeout(()=>ae.classList.remove("on"),P)}let ze=0;function $e(Z,P=9e3){let ae=Le("hint");ae.replaceChildren(...Z.map(me=>Array.isArray(me)?G("kbd",null,me[0]):me)),ae.hidden=!1,clearTimeout(ze),ze=setTimeout(()=>{ae.hidden=!0},P)}function ht(){clearTimeout(ze),Le("hint").hidden=!0}let Ye=0;function Q(Z,P,ae,me){let fe=Le("tag");fe.replaceChildren(G("small",null,c_[me]||me),ae),fe.style.left=`${Math.max(90,Math.min(window.innerWidth-90,Z))}px`,fe.style.top=`${Math.max(70,P)}px`,fe.hidden=!0,fe.offsetWidth,fe.hidden=!1,clearTimeout(Ye),Ye=setTimeout(()=>{fe.hidden=!0},3200)}let te="";function ve(Z,P){Z!==te&&(te=Z,Le("place-en").textContent=Z,Le("place-he").textContent=P||"")}function Fe(Z){Le("compass-dial").style.transform=`rotate(${Z}rad)`}function Se(Z,P){Le("b-fly").setAttribute("aria-pressed",String(Z)),Le("fly-keys").hidden=!(Z&&P)}function je(Z){Le("tourcard").classList.toggle("min",!Z)}return Le("b-map").addEventListener("click",()=>d==="map"?S():B()),Le("b-stops").addEventListener("click",()=>d==="stops"?S():I()),Le("b-codex").addEventListener("click",C),Le("b-settings").addEventListener("click",V),Le("b-help").addEventListener("click",ne),Le("b-fly").addEventListener("click",()=>t.toggleFly()),{setProgress:m,ready:p,fail:x,enter:v,setStop:T,setArrived:A,openStop:_,openStops:I,openMap:B,openCodex:C,openSettings:V,openHelp:ne,closeSheet:S,toast:_e,hint:$e,hideHint:ht,tag:Q,setPlace:ve,setCompass:Fe,setFly:Se,setTourVisible:je,get panelOpen(){return!!d},toggle(Z){return d===Z?S():(Z==="map"?B():Z==="stops"?I():Z==="help"&&ne(),!0)},upButton:Le("b-up"),downButton:Le("b-down")}}var qu={name:"The pilgrim's way",description:"Eighteen stops along the path a pilgrim actually walked: in from the east across the Mount, through the outer gate into the great court, up through the Court of Israel to the altar, up the twelve steps into the House, and west through the Heikhal to the paroches with the Kodesh HaKodashim beyond it.",limitations:["The walkability of the straight line between two stops has NOT been verified by a native route trace. The approach waypoints below route the path through the recorded gate and door openings, but no commandlet has walked it.","The tour enters the Ezras Kohanim and the House. An Israelite entered the priestly court only for his own necessary sacrificial task (Keilim 1:8-9), and no non-kohen entered the Heikhal at all. The stop text says so where it applies; the tour still goes, because this is a model of a building and not a re-enactment of a person.","On an ordinary weekday the inner east gate is shut (Yechezkel 46:1) and entry to the inner court was through the lower chambers, which this model does not have. The tour walks up the inner east gate anyway. Stop east-inner-gate says so."],confidenceLabels:{certain:"The sources agree, or one source is decisive and no cited authority disputes it.",disputed:"The sources disagree. The entry names who holds what.",authored:"Nobody said this. The project chose it because a model has to put something somewhere."},stops:[{key:"mount-and-house",name:"The Mount, and the House on it",he:"\u05D4\u05E8 \u05D4\u05D1\u05D9\u05EA",subtitle:"First sight, from the east",stand:[120,0,0],look:[-40,30,0],approach:[],confidence:"certain",what:"Nothing yet. This is where a pilgrim coming up from the east first saw the whole thing at once: the walled precinct, the great court inside it, and the House standing above both with its roof a hundred amot up.",explanation:"The size of this precinct is the largest open question in the whole reconstruction. Yechezkel measures it in reeds - five hundred by five hundred - and a reed is six amot, which gives 3000 amot a side, about a kilometre and a half. The Har HaBayit of the Second Temple was 500 amot square. That is a difference of thirty-six times in area, and the model is built the large way. See the codex entry 'The size of the precinct', which sets out both readings and the author's own third suggestion.",measurements:[{label:"Precinct, each side",amot:3e3,cm:15e4,source:"Yechezkel 42:15-20 with Rashi; 500 reeds, a reed being six amot (Yechezkel 40:5)",confidence:"disputed"},{label:"The House, length, width and height",amot:100,cm:5e3,source:"Yechezkel 41:13 with Rashi; Middos 3:8, 4:7",confidence:"certain"},{label:"Precinct wall, thickness and height",amot:6,cm:300,source:"Yechezkel 40:5 with Rashi citing Middos 2:4; Mishkenei Elyon 196",confidence:"certain"}],sources:["Yechezkel 42:15-20","Yechezkel 40:5","Rashi on Yechezkel 40:5 (citing Middos 2:4)","Mishnah Middot 2:1","Mishkenei Elyon 184, 189, 196","Lishchno Tidreshu pp. 112-113, 359-364"],codex:["precinct-size","precinct-wall-and-gates","the-house-overall","the-amah"]},{key:"immersion",name:"Immersion before the ascent",he:"\u05D8\u05D1\u05D9\u05DC\u05D4",subtitle:"An authored stop: no mikveh is modelled",stand:[110,0,9],look:[100,3,3],approach:[],confidence:"authored",what:"A pilgrim did not walk onto the Mount as he was. He immersed first. This spot is the project's own choice: no mikveh has been built in this model, and the sources read for it give no location for one in the Third Temple. The stop is here so the step is not silently skipped.",explanation:"Three separate things get muddled here and the sources keep them apart. Corpse impurity is not cured by a bath at all - it needs the purification water and the third and seventh days (Bamidbar 19:11-12, 19). Exclusion is graded by zone: the Mount, the cheil, the Women's Court and the Israelite Court each exclude different people (Rambam, Biat HaMikdash 3:3-7, 14). And immersion before service is its own idea, required even of someone already pure (Yoma 3:3). Sanctifying hands and feet (Biat HaMikdash 5:1-2) is a further and separate requirement that no bath replaces.",measurements:[],sources:["Bamidbar 19:11-12, 19","Rambam, Biat HaMikdash 3:3-7, 14","Rambam, Biat HaMikdash 5:1-2","Mishnah Yoma 3:3","Mishnah Yoma 3:4"],codex:["immersion-and-purity","three-camps"]},{key:"soreg-and-cheil",name:"The soreg and the cheil",he:"\u05E1\u05D5\u05E8\u05D2 \u05D5\u05D7\u05D9\u05DC",subtitle:"The first boundary, and who it stops",stand:[100,0,0],look:[80,6,0],approach:[],confidence:"certain",what:"A low wooden lattice, ten tefachim high, then a strip of open ground, then a wall. This is the line a non-Jew and anyone bearing corpse impurity did not cross. The lattice is waist-high and easy to step over, which is the point: it is a notice, not a barrier.",explanation:"Whether the cheil is a wall or only the open strip is a real dispute. The Rambam, the Meiri and Mishkenei Elyon read it as a ten-amah wall with ten amot of open ground inside it, and that is what is built here. The Bartenura and the Tosafos Yom Tov read the soreg itself as the cheil's wall. The one-amah thickness given to the wall in this model is the author's, offered for study.",measurements:[{label:"Soreg height",cm:83.33333333333334,source:"Mishnah Middot 2:3; built in the model at 83.333 cm",confidence:"certain"},{label:"Cheil wall height",amot:10,cm:500,source:"Rambam, Beis HaBechirah 5:3, 6:1; Meiri on Middos 2:3",confidence:"disputed"},{label:"Cheil open strip",amot:10,cm:500,source:"Mishnah Middot 2:3; Mishkenei Elyon 191-192",confidence:"certain"}],sources:["Mishnah Middot 2:3","Rambam, Beis HaBechirah 5:3, 6:1","Meiri on Middot 2:3 / Yoma 16b","Mishkenei Elyon 191-192, 196","Bartenura and Tosafos Yom Tov on Middot 2:3 (the other reading)","Lishchno Tidreshu pp. 121-126"],codex:["soreg","cheil","three-camps"]},{key:"east-outer-gate",name:"The east gate of the outer court",he:"\u05E9\u05E2\u05E8 \u05D4\u05DE\u05D6\u05E8\u05D7 \u05D4\u05D7\u05D9\u05E6\u05D5\u05DF",subtitle:"Twelve steps, then fifty amot of doorway",stand:[79.5,3,0],look:[60,9,0],approach:[[89,1.5,0]],confidence:"certain",what:"Twelve steps up, each half an amah, and then a gate passage six amot deep with an opening ten amot wide and fifty amot high. Six cells line the passage, three on each side. This was the gate of entry for the whole year except the three festivals, when the crowd entered by the north and left by the south.",explanation:"The north and south outer gates are the same gate with seven steps instead of twelve, because the ground is higher on those sides. The tall narrow windows in the cells are splayed the wrong way round on purpose - narrow inside, widening outward - and carry no glass. How many of them there are is nobody's statement; the count in this model is the author's.",measurements:[{label:"Gate opening, width by height",amot:10,cm:500,source:"Yechezkel 40:6-16 with Rashi; height 50 amot per Mishkenei Elyon 170",confidence:"certain"},{label:"Steps, east side",cm:25,source:"Middos 2:3; Rambam, Beis HaBechirah 6:1",confidence:"certain"},{label:"Gate cells, interior",amot:6,cm:300,source:"Yechezkel 40:7 with Rashi; walls 5 amot",confidence:"certain"},{label:"Gate block, total width",amot:25,cm:1250,source:"Rashi on Yechezkel 40:13 - 5 + 2.5 + 10 + 2.5 + 5",confidence:"certain"}],sources:["Yechezkel 40:6-16","Rashi on Yechezkel 40:13, 40:16","Yechezkel 40:19-27","Yechezkel 46:1, 46:9","Rambam, Beis HaBechirah 7:2","Mishkenei Elyon 166-197","Lishchno Tidreshu pp. 121-147"],codex:["outer-gates","gate-cells","splayed-windows","gate-calendar"]},{key:"outer-court",name:"The outer court",he:"\u05D4\u05E2\u05D6\u05E8\u05D4 \u05D4\u05D7\u05D9\u05E6\u05D5\u05E0\u05D4",subtitle:"Where the people stood",stand:[49.74,3,0],look:[0,11,0],approach:[],confidence:"certain",what:"The great court. Six gates open into it - east, north and south on the outer wall and the same three on the inner - and it is a hundred amot from any gate to the gate facing it. This is where the crowd was, and where the pilgrim spent most of his time.",explanation:"A pilgrim entered on his right and circled the court, leaving by his left; a mourner or someone under a ban went round the other way, so that everyone he met knew and could ask (Middos 2:2). There is no west gate anywhere in this plan, in the outer wall or the inner. This exact spot, X 4974, is the one point in the outer court where a downward floor trace in this map is recorded as having landed cleanly.",measurements:[{label:"Gate to facing gate",amot:100,cm:5e3,source:"Yechezkel 40:19, 23, 27 with Rashi",confidence:"certain"},{label:"Court wall thickness",amot:6,cm:300,source:"Yechezkel 40:5 with Rashi",confidence:"certain"}],sources:["Yechezkel 40:19, 23, 27","Mishnah Middot 2:2","Bartenura on Middot 2:2","Lishchno Tidreshu pp. 118, 144-147"],codex:["outer-court","circulation","gallery-chambers","corner-courts"]},{key:"north-gate-and-inner-wall",name:"The north gate and the wall of the inner court",he:"\u05E9\u05E2\u05E8 \u05D4\u05E7\u05E8\u05D1\u05DF",subtitle:"Three inner gates, and no more",stand:[0,3,-45],look:[0,9,-27],approach:[[34,3,-34]],confidence:"certain",what:"The inner court has three gates only - north, east and south - against the seven or thirteen of the Second Temple. Kodshei kodashim are slaughtered on the north side, and this gate carries the tables for it. Eight slaughter tables belong here: four inside its vestibule, four in the passage between the cells.",explanation:"The inner gates are the outer gates turned around: eight steps instead of twelve, and the vestibule projecting outward into the great court with the cells behind it. Two of the three gates get names in this reading - the north is the gate of the offering, the south the water gate, because the water of Yechezkel 47:1-2 flows out from the Kodesh HaKodashim through it. Those names are the author's mapping, not the navi's. And the slaughter tables in this model are not where the book puts them: they sit clustered inside the court rather than at this gate. That is a known and recorded gap.",measurements:[{label:"Inner gate steps",cm:25,source:"Yechezkel 40:31 with Rashi; Middos 2:3",confidence:"certain"},{label:"Marble tables in the rinsing chamber",amot:1.5,cm:75,source:"Yechezkel 40:42-43 with Rashi; four tables, 1.5 x 1.5 x 1 amot",confidence:"certain"},{label:"Recesses in the inner court wall",amot:25,cm:1250,source:"Rashi on Yechezkel 40:30, 41:15-16; six of them, 25 x 5 amot",confidence:"disputed"}],sources:["Yechezkel 40:28-43","Rashi on Yechezkel 40:30, 40:31, 40:38-43","Yechezkel 47:1-2","Mishnah Middot 1:4, 2:6","Mishkenei Elyon 177-178, 188, 193, 199","Lishchno Tidreshu pp. 148-164, 340"],codex:["inner-gates","inner-court-recesses","slaughter-tables","gate-names","song-and-clothing-chambers"]},{key:"east-inner-gate",name:"The east gate of the inner court",he:"\u05E9\u05E2\u05E8 \u05D4\u05DE\u05D6\u05E8\u05D7 \u05D4\u05E4\u05E0\u05D9\u05DE\u05D9",subtitle:"Shut, on a day like this one",stand:[35,4,0],look:[26,8,0],approach:[[36,3,-34]],confidence:"certain",what:"Eight steps up from the outer court, over the eleven amot of the gate's cells, into the inner court. On an ordinary weekday this gate is shut: it opens on Shabbos and on Rosh Chodesh and no other day, and the way in on a weekday was through the lower chambers, which have a door into the Court of Israel.",explanation:"This model has no lower chambers, so the tour walks up the closed gate. Saying that plainly is better than pretending. The lower chambers themselves - two blocks of 100 by 50 amot at the north-east and south-east, three storeys each - are recorded in Yechezkel 42:9-12 with their size but not their purpose; what goes in them in the book is the author filling an empty room.",measurements:[{label:"Steps",cm:25,source:"Yechezkel 40:31 with Rashi",confidence:"certain"},{label:"Gate vestibule interior",amot:13,cm:650,source:"Yechezkel 40:29-31; 13 north-south by 8 east-west, 50 high",confidence:"certain"}],sources:["Yechezkel 46:1","Yechezkel 40:28-31","Yechezkel 42:9-12","Rashi on Yechezkel 42:12","Rambam, Beis HaBechirah 7:2","Mishkenei Elyon 187, 197","Lishchno Tidreshu pp. 137, 300-313"],codex:["gate-calendar","lower-chambers","inner-gates"]},{key:"ezras-yisroel",name:"The Court of Israel",he:"\u05E2\u05D6\u05E8\u05EA \u05D9\u05E9\u05E8\u05D0\u05DC",subtitle:"Seventeen amot, and as close as an Israelite comes",stand:[23,5,0],look:[0,11,0],approach:[],confidence:"certain",what:"A strip seventeen amot deep across the whole east end of the inner court, two and a half amot lower than the priests' court in front of it. From here an Israelite watched the service. He went further west only when his own offering required him to, and no further than that.",explanation:"The hundred amot of the inner court divide east to west as seventeen for Israel, seventeen for the kohanim, thirty-two for the altar and thirty-four from the altar to the Ulam. In the Second Temple the last figure was twenty-two. Because the altar's place is fixed and cannot move, the extra twelve amot push the House itself thirteen amot further west than it stood before - twelve here and one more from the thicker partition of the Kodesh HaKodashim. There is no Women's Court anywhere in this plan. The sources read for this project do not describe one for the Third Temple, and none is modelled; women in the outer court's thirty gallery chambers is the author's suggestion, not a source.",measurements:[{label:"Court of Israel, east to west",amot:17,cm:850,source:"Yechezkel 40:47 with Rashi; Mishkenei Elyon 182, 198, 204",confidence:"certain"},{label:"Below the priests' court",amot:2.5,cm:125,source:"Middos 2:6",confidence:"certain"},{label:"Inner court, each side",amot:100,cm:5e3,source:"Yechezkel 40:47",confidence:"certain"}],sources:["Yechezkel 40:47","Mishnah Middot 2:6","Rambam, Beis HaBechirah 2:1, 2:3","Mishnah Middot 4:7, 5:1","Keilim 1:8-9","Mishkenei Elyon 182, 198, 204","Lishchno Tidreshu pp. 170-172"],codex:["court-of-israel","no-ezras-nashim","house-moved-west","gallery-chambers"]},{key:"duchan",name:"The duchan",he:"\u05D3\u05D5\u05DB\u05DF",subtitle:"Where the Levites stood and sang",stand:[14.5,6.25,0],look:[25,8,0],approach:[],confidence:"certain",what:"The step between the two courts. A rise of one amah with a three-stepped platform on it, half an amah each, so the priests' court stands two and a half amot above the Court of Israel. The Levites stood on it facing east and sang at the wine libation of the daily offering, morning and evening.",explanation:"The book's earlier review recorded this as a gap - the duchan rising only 1.25 amot where it should rise 2.5. The receipt for the map as it now stands shows four rises from Z 500 to Z 625, which is 125 cm, which is 2.5 amot. Either the gap was closed or the earlier reading was of a different build; the numbers in the current architecture manifest are the ones quoted above.",measurements:[{label:"Total rise, Israel to kohanim",amot:2.5,cm:125,source:"Middos 2:6 in the name of R' Eliezer b. Yaakov",confidence:"certain"},{label:"Rise as built in this model",amot:2.5,cm:125,source:"Receipt: four rises X 1575..1675, tops Z 550, 575, 600, 625, from floor Z 500",confidence:"certain"}],sources:["Mishnah Middot 2:6","Rashi on Yechezkel 42:12","Divrei HaYamim II 5:12","Rambam, Beis HaBechirah 6:3-5","Mishkenei Elyon 184, 198","Lishchno Tidreshu pp. 171, 313, 342"],codex:["duchan","levites-song","song-and-clothing-chambers"]},{key:"outer-altar",name:"The altar",he:"\u05D4\u05DE\u05D6\u05D1\u05D7",subtitle:"Thirty-two amot square, and it cannot be moved",stand:[11.5,6.25,12.5],look:[0,11,0],approach:[],confidence:"certain",what:"The altar stands in the exact centre of the inner court, thirty-two amot square, with a ramp climbing to it from the south. Everything else in the plan is measured from it, because its place is the one thing that is fixed: the altar's site is settled forever, and when the House is rebuilt it is the House that moves.",explanation:"Be careful with the altar's own dimensions. The book volume this project reads covers Yechezkel chapters 40 to 42 only, and it defers the altar's height, its yesod, its sovev and its horns to a note on chapter 43 in a second part that is not in the export. So the 32 amot square and the 34 amot to the Ulam are sourced; the tiers, the ramp's width and slope, and the horn heights in this model are the build's own, recorded in the architecture manifest and not in a text. What the sources do say is that the Torah's altar measures are not indispensable - it may be made larger, never smaller than Moshe's (Zevachim 62a).",measurements:[{label:"Altar, each side",amot:32,cm:1600,source:"Yechezkel 40:47 with Rashi; Mishkenei Elyon 182, 198",confidence:"certain"},{label:"Altar to the Ulam",amot:34,cm:1700,source:"Mishkenei Elyon 182, 198, 204; 22 amot in the Second Temple",confidence:"certain"},{label:"Ramp width, as built",amot:16,cm:800,source:"Receipt: SM_0166 southern kevesh, X +/-400, Y 710.08..2300, Z 625..1066.67",confidence:"authored"},{label:"Burning surface, height above the priests' court, as built",amot:8.83,cm:441.67,source:"Receipt: upper tier top Z 1066.67 above court floor Z 625",confidence:"authored"}],sources:["Yechezkel 40:47","Rashi on Yechezkel 40:47","Zevachim 62a","Rambam, Beis HaBechirah 2:1-3","Mishkenei Elyon 182, 198, 204","Lishchno Tidreshu pp. 170-173"],codex:["outer-altar","kevesh","altar-furniture","house-moved-west"]},{key:"kiyor",name:"The kiyor",he:"\u05DB\u05D9\u05D5\u05E8",subtitle:"Between the Ulam and the altar",stand:[-17,6.25,12.5],look:[-19.5,7.2,15],approach:[],confidence:"certain",what:"A kohen sanctified his hands and his feet here before he served, and again whenever he had left the court. The laver stands between the porch and the altar, on its base, with a pit and a pulley to lower it into water overnight so it would not be disqualified by standing.",explanation:"The kiyor is one of the things Yechezkel never mentions and everyone agrees is there anyway. The same is true of the menorah, the golden altar, the Aron and the keruvim. Rashi, the Radak, the Tosafos Yom Tov and Mishkenei Elyon all take the Torah's furniture as continuing unless the navi says otherwise - and that principle is what licenses this whole reconstruction to contain anything at all. Its size and its twelve spouts are the build's, not a text's: no dimension for the kiyor was found in the research read for this project.",measurements:[{label:"Basin, as built",cm:208,source:"Receipt: basin X -2054..-1846, Y 1396..1604, Z 690..750; pedestal Z 625..696; twelve spouts",confidence:"authored"}],sources:["Shemos 30:17-21","Mishnah Middot 3:6","Rambam, Biat HaMikdash 5:1-2","Rashi, Radak, Tosafos Yom Tov as summarised in Mishkenei Elyon 177","Lishchno Tidreshu pp. 160, 173"],codex:["kiyor","unmentioned-vessels","immersion-and-purity"]},{key:"twelve-steps",name:"The twelve steps to the House",he:"\u05E9\u05EA\u05D9\u05DD \u05E2\u05E9\u05E8\u05D4 \u05DE\u05E2\u05DC\u05D5\u05EA",subtitle:"Six amot of rise, twenty-one of run",stand:[-13,6.25,0],look:[-24.5,17,0],approach:[],confidence:"certain",what:"Twelve steps, half an amah each, lifting the floor of the House six amot above the court. They are not a plain flight: the Mishnah lays them out as two steps, a landing of three amot, twice more the same, then two steps and a landing of four - twenty-one amot from foot to threshold.",explanation:"The two pillars flanking the entrance stand sixty amot high with palm capitals, in the place Yachin and Boaz held in the First Temple - though those were thirty-six amot and four thick, so these are not the same pillars redone. How much of the sixty is capital is the author's guess: he suggests ten.",measurements:[{label:"Rise",amot:6,cm:300,source:"Yechezkel 40:49 with Rashi; Middos 3:6",confidence:"certain"},{label:"Run",amot:21,cm:1050,source:"Middos 3:6",confidence:"certain"},{label:"Eilim at the entrance",amot:60,cm:3e3,source:"Yechezkel 40:49 with Rashi; two pillars 2 x 2 amot, 60 high, with palm capitals",confidence:"certain"}],sources:["Yechezkel 40:48-49","Rashi on Yechezkel 40:49","Mishnah Middot 3:6","Rambam, Beis HaBechirah 6:4","Melachim I 7:16","Mishkenei Elyon 166, 172, 197","Lishchno Tidreshu pp. 174-179"],codex:["twelve-steps","eilim-and-palms","ulam"]},{key:"ulam",name:"The Ulam",he:"\u05D0\u05D5\u05DC\u05DD",subtitle:"A doorway fourteen amot wide and fifty high",stand:[-30,9.25,0],look:[-34.5,17,0],approach:[[-19,7.75,0],[-24.4,9.25,0]],confidence:"certain",what:"The porch of the House: twenty amot across, eleven deep, with walls five amot thick. Its entrance has no doors in Yechezkel's account. The jambs step three amot in from each side, so the opening is fourteen amot wide - not the twenty of the Second Temple - and fifty amot high.",explanation:"Two chambers flank the porch, fifteen amot north-south by ten east-west, for the knives. The layered stone lintel over the entrance in this model is Second Temple styling: the five stepped olive-wood beams of Middos 3:7 belong to that building and are not described for this one. Only palm reliefs go on these jambs - no keruvim; the keruvim begin inside.",measurements:[{label:"Interior, north-south by east-west",amot:20,cm:1e3,source:"Yechezkel 40:48 with Rashi; 20 x 11 amot, walls 5",confidence:"certain"},{label:"Entrance opening, width",amot:14,cm:700,source:"Yechezkel 40:48 with Rashi; explicit in Rashi's reading",confidence:"certain"},{label:"Entrance opening, height",amot:50,cm:2500,source:"Mishkenei Elyon 170, 202",confidence:"certain"}],sources:["Yechezkel 40:48-49","Rashi on Yechezkel 40:48","Yechezkel 41:26 with Rashi","Mishnah Middot 3:7, 4:7","Mishkenei Elyon 166, 170, 176, 202","Lishchno Tidreshu pp. 174-179, 264-270"],codex:["ulam","beis-hachalifos","miltaros-historical","reliefs"]},{key:"heikhal",name:"The Heikhal",he:"\u05D4\u05D9\u05DB\u05DC",subtitle:"Forty amot by twenty, and fifty to the lintel",stand:[-39,9.25,0],look:[-56,17,0],approach:[[-34.5,9.25,0]],confidence:"certain",what:"The Sanctuary itself, forty amot long and twenty wide, walls six amot thick on all four sides. The doorway behind you is ten amot wide and fifty high with two pairs of folding leaves, the outer pair set an amah into the wall's thickness. No Israelite came in here; a kohen came in only for service and for nothing else.",explanation:"Every wall in here, the jambs, the doors, the ceiling - and in this Temple, unlike the last, the wall behind the doors too - is lined floor to ceiling with thin cedar boards, carved and beaten over with gold. Gold cannot be laid on stone, which is why the cedar is there at all. The carving alternates a keruv and a palm the whole way round. Each keruv shows two faces only, not a body: a young lion's face on its right turned to the palm on that side, a man's face on its left turned to the palm on that side. That carving has not been modelled here; the walls carry gold and no relief. It is the largest recorded gap in the build.",measurements:[{label:"Heikhal, length by width",amot:40,cm:2e3,source:"Yechezkel 41:2 with Rashi",confidence:"certain"},{label:"Walls",amot:6,cm:300,source:"Yechezkel 41:5 with Rashi; Mishkenei Elyon 164",confidence:"certain"},{label:"Door opening, width",amot:10,cm:500,source:"Yechezkel 41:2, 41:21",confidence:"certain"},{label:"Door opening, height",amot:50,cm:2500,source:"Mishkenei Elyon 169-170; twenty amot in the Second Temple",confidence:"certain"}],sources:["Yechezkel 41:1-2, 41:16-20, 41:21, 41:23-24","Rashi on Yechezkel 41:18-19","Melachim I 6:32","Mishnah Middot 4:1-2","Rambam, Beis HaBechirah 4:7","Mishkenei Elyon 164, 168-171, 190, 203","Lishchno Tidreshu pp. 182-183, 222-239, 259-267"],codex:["heikhal","heikhal-doors","reliefs","gold-over-cedar","atikim","windows","who-may-enter"]},{key:"menorah",name:"The Menorah",he:"\u05DE\u05E0\u05D5\u05E8\u05D4",subtitle:"On the south side, eighteen tefachim high",stand:[-49.5,9.25,3.15],look:[-53.3,10.75,3.15],approach:[],confidence:"disputed",what:"The menorah stands on the south side of the Sanctuary, two and a half amot from the south wall and five from the wall of the Kodesh HaKodashim, beaten from a single talent of gold. In front of it is a stone with three steps, because the lamps are eighteen tefachim up and a kohen has to reach them. Twice a day he cleaned them, refilled each with half a log of oil, and kindled.",explanation:"Which way it faces is disputed and this build has picked a side. The Rambam has the six branches running north and south; Rashi has them east and west, and the book draws that as an alternative. The model follows the Rambam - and it does so because the imported asset was built that way, which is a consistency decision and not a ruling. The six outer lamps face the middle one (Beis HaBechirah 3:8, from Bamidbar 8:2) and the middle one faces the Kodesh HaKodashim. One more thing must be said out loud: the ORDER in which the seven lamps are tended - which five first and which two after - is stated nowhere. Rambam, Temidin uMusafin 3:17 says five, then two, and does not name them. The order shown in this build runs north to south and is an authored placeholder chosen because it reads cleanly on screen. It is not the order of the service.",measurements:[{label:"Height",cm:150,source:"Rambam, Beis HaBechirah 3:8-12; Lishchno Tidreshu p. 241; built at 150.0 cm",confidence:"certain"},{label:"Width across the outer lamp rims, as built",cm:101.52477,source:"Receipt: SourceAssets/vessels-review/MenorahV4/geometry-manifest.json",confidence:"authored"},{label:"Oil per lamp",cm:0,source:"Rambam, Temidin uMusafin 3:11",confidence:"certain"},{label:"Position",cm:0,source:"World [-5330, 315.176, 925], lamps at Z 1075; step stone X -5284.1..-5194.1, top Z 975",confidence:"certain"}],sources:["Shemos 25:31-40, 26:35 with Rashi","Rambam, Beis HaBechirah 3:8, 3:10-12","Rambam, Temidin uMusafin 3:11, 3:12, 3:13, 3:17","Bamidbar 8:2","Bartenura on Tamid 3:9","Menachos 98b","Mishkenei Elyon 167, 173","Lishchno Tidreshu pp. 241, 252-254"],codex:["menorah","menorah-orientation","lamp-service","lamp-order-authored","unmentioned-vessels"]},{key:"shulchan",name:"The Shulchan",he:"\u05E9\u05D5\u05DC\u05D7\u05DF",subtitle:"Opposite the menorah, on the north",stand:[-49.5,9.25,-3.5],look:[-53,10.75,-3.5],approach:[],confidence:"certain",what:"The table of the showbread, facing the menorah across the Sanctuary: two and a half amot from the north wall, five from the wall of the Kodesh HaKodashim. Twelve loaves lie on it in two stacks of six, held apart by twenty-eight half-tube golden rods carried on four uprights, with two bowls of frankincense between the stacks. There is bread on it always.",explanation:"Three amot is the striking number: the Torah's table is a cubit and a half, and Yechezkel's is three. The book takes the three at face value; it also records an alternative reading, that the three amot are measured including the bread stacked on it. Both are in the sources and the model builds the first.",measurements:[{label:"Length, east to west",amot:2,cm:100,source:"Yechezkel 41:22 with Rashi; Shemos 25:23",confidence:"certain"},{label:"Width",amot:1,cm:50,source:"Shemos 25:23",confidence:"certain"},{label:"Height",amot:3,cm:150,source:"Yechezkel 41:22; the Third Temple figure, against the Torah's 1.5 amot",confidence:"disputed"},{label:"Uprights, height above the floor",amot:5,cm:250,source:"Menachos 94-99; Rambam, Beis HaBechirah 3:12-16",confidence:"certain"}],sources:["Yechezkel 41:22 with Rashi and Targum","Shemos 25:23, 26:35 with Rashi","Yoma 33b","Menachos 94-99","Rambam, Beis HaBechirah 3:12-16","Rambam, Temidin uMusafin 5","Mishkenei Elyon 167, 203","Lishchno Tidreshu pp. 241-251"],codex:["shulchan","lechem-hapanim","unmentioned-vessels"]},{key:"golden-altar",name:"The golden altar",he:"\u05DE\u05D6\u05D1\u05D7 \u05D4\u05D6\u05D4\u05D1",subtitle:"The incense, twice a day",stand:[-44,9.25,0],look:[-46.5,10.1,0],approach:[],confidence:"certain",what:"The small golden altar stands on the centre line of the Sanctuary, opposite the Aron, between the menorah and the table and a little east of them. Incense is offered on it morning and afternoon. While it burns, everyone withdraws - out of the Sanctuary and out of the space between the porch and the outer altar - until the kohen who offered it comes out.",explanation:"This is the one object in the whole model measured at a different amah. The Talmud in Eruvin 4a reads the golden altar's cubit as a five-tefach cubit rather than the six-tefach cubit used everywhere else, so its 1 x 1 x 2 amot come out at 41.7 by 41.7 by 83.3 centimetres, not 50 by 50 by 100. Where the incense is offered relative to the lamps is not settled: Abaye's order of service puts it after the second group of lamps, while the Rambam's own note sets the re-entry after the limbs of the daily offering were brought up. This build follows Abaye and marks the position as unsettled.",measurements:[{label:"Square, each side",amot:1,cm:41.666666666666664,source:"Shemos 30:1-10; measured at the five-tefach amah of Eruvin 4a, per Lishchno Tidreshu p. 255",confidence:"certain"},{label:"Height",amot:2,cm:83.33333333333333,source:"Shemos 30:2; same five-tefach amah",confidence:"certain"}],sources:["Shemos 30:1-10","Eruvin 4a on Yechezkel 43:13","Rambam, Beis HaBechirah 3:17","Rambam, Temidin uMusafin 3:1, 3:3, 3:9","Mishnah Yoma 3:5","Mishnah Tamid 6:3","Yoma 33a (Abaye's seder ha-ma'arachah; not independently verified in this pass)","Mishkenei Elyon 167, 193","Lishchno Tidreshu pp. 241, 255-258"],codex:["golden-altar","ketores","maaleh-ashan","the-amah"]},{key:"paroches",name:"The paroches, and what is behind it",he:"\u05E4\u05E8\u05D5\u05DB\u05EA \u05D5\u05E7\u05D3\u05E9 \u05D4\u05E7\u05D3\u05E9\u05D9\u05DD",subtitle:"Seven amot by six, and no further",stand:[-53.5,9.25,0],look:[-56,10.75,0],approach:[[-50,9.25,0]],confidence:"certain",what:"The end of the tour, and the end of where anyone goes. A partition two amot thick with an opening seven amot wide and six high, two doors standing permanently open, and a curtain across the opening exactly the size of the gateway - no less and no more. Behind it a room twenty amot square. The Kohen Gadol enters it once a year and nobody else ever.",explanation:"The paroches is not in the navi. It comes from Mishkenei Elyon, and the model draws it. Behind it stand the Aron with its poles pressing out against the curtain like two breasts (Yoma 54a), the kaporet with two keruvim beaten from it facing each other and downward, and beside the Aron Aharon's staff, the jar of manna and the flask of anointing oil - all of which were missing from the Second Temple. Where the Even HaShtiya sits is not settled: the Rambam puts it in the west of the chamber, the Tosafos Yom Tov and the Tanchuma in the middle, and the author reconciles them by spreading the stone twelve amot square from the centre and marks that as study only. The keruvim are described in the book as having six wings each; the research records that as the book's own statement with no source given, and it is reported here as such.",measurements:[{label:"Partition wall",amot:2,cm:100,source:"Yechezkel 41:3; one amah in the First Temple, no wall at all in the Second",confidence:"certain"},{label:"Opening, width by height",amot:7,cm:350,source:"Yechezkel 41:3; 7 wide by 6 high",confidence:"certain"},{label:"Kodesh HaKodashim, each side",amot:20,cm:1e3,source:"Yechezkel 41:4",confidence:"certain"},{label:"Paroches",amot:7,cm:350,source:"Mishkenei Elyon 159-160, 166 - exactly the measure of the gateway",confidence:"disputed"}],sources:["Yechezkel 41:3-4, 41:23","Rashi on Yechezkel 41:3","Yoma 53b, 54a","Vayikra 16:2","Rambam, Beis HaBechirah 4:1","Rambam, Biat HaMikdash 2:1","Tosafos Yom Tov on Yoma 5:2","Tanchuma Kedoshim 10","Shemos 25:10-22","Mishkenei Elyon 150, 159-167","Lishchno Tidreshu pp. 184-192, 259-263, 306"],codex:["paroches","kodesh-hakodashim","aron","keruvim-on-the-kaporet","even-hashtiya","who-may-enter"]}]};var gm={categories:[{id:"precinct",name:{en:"The Mount and its boundaries",he:""}},{id:"courts",name:{en:"The courts and their gates",he:""}},{id:"altar",name:{en:"The altar and its furniture",he:""}},{id:"house",name:{en:"The House",he:""}},{id:"vessels",name:{en:"The vessels",he:""}},{id:"service",name:{en:"The service",he:""}},{id:"people",name:{en:"People, access and purity",he:""}},{id:"method",name:{en:"How this reconstruction was made",he:""}}],entries:[{id:"the-amah",category:"method",name:"The amah, and how long it is",he:"\u05D0\u05DE\u05D4",confidence:"disputed",summary:"Everything here is measured in amot, and the physical length of an amah is not settled. This model is baked at a round 50 cm per amah, which is a modelling decision and not a ruling. The common opinions run from about 48 cm to about 58 cm, so the same 3000-amah square is 1440 m a side under one and 1740 m under another - without a single vertex moving. One object is measured differently on purpose: the golden altar uses the five-tefach amah of Eruvin 4a, 41.67 cm.",measurements:[{label:"Project world scale",value:"50.0 cm per amah, tefach 8.3333 cm",source:"EnclosureMath.h ProjectCmPerAmah; SourceAssets/vessels-review/*/geometry-manifest.json"},{label:"R' Avraham Chaim Naeh",value:"48.0 cm",source:"Shiurei Torah - amah of six tefachim of 8 cm"},{label:"R' Moshe Feinstein",value:"54.0 cm",source:"Igros Moshe OC I:136 - a 21 3/8 inch amah"},{label:"Chazon Ish",value:"57.6 cm, 58.0 stringent",source:"Kuntres HaShiurim"},{label:"Golden altar only",value:"41.6667 cm",source:"Eruvin 4a on Yechezkel 43:13"}],dispute:[{who:"R' Avraham Chaim Naeh",holds:"48 cm"},{who:"R' Moshe Feinstein",holds:"54 cm"},{who:"Chazon Ish",holds:"57.6 cm, 58 for de'oraisa"}],sources:["Yechezkel 40:5 - a reed of six amot, an amah and a tefach","Eruvin 4a on Yechezkel 43:13","Shiurei Torah","Igros Moshe OC I:136","Chazon Ish, Kuntres HaShiurim"]},{id:"precinct-size",category:"precinct",name:"The size of the precinct: 3000 amot or 500?",he:"",confidence:"disputed",summary:`This is the single largest open question in the reconstruction, and it changes the scale of everything.

The reading this model is built on: Yechezkel 42:15-20 measures the sacred precinct with a reed, five hundred by five hundred. A reed is six amot (Yechezkel 40:5, 'a reed of six amot, an amah and a tefach'). Five hundred reeds is therefore 3000 amot a side - about a kilometre and a half at any of the common amot - and Rashi reads it that way. The book adopts it as certain, notes the Kalir piyut on the figure, and points out that this makes the future Mount thirty-six times the area of the Second Temple's.

The other reading: Mishnah Middot 2:1 gives the Har HaBayit of the Second Temple as 500 amot square. Read Yechezkel's five hundred as amot rather than reeds and the future precinct is the same size as the old one. The research assembled for this project does not find the book arguing that case for the Third Temple - it uses the 500 amot as the Second Temple comparison figure that the thirty-six-times ratio is computed against, and takes Middot 2:1 for the shape and proportions rather than the magnitude. Anyone who holds the 500-amah reading is entitled to it; this entry is stating what the source pile in this project actually contains, not settling it.

A third position, and it is the author's own: an inner soreg ring of 500 amot square inside the 3000, with the cheil inside that. The research marks this explicitly as 'the author's forced reading', starred for study, and it is the only place the 500-amah figure survives into the Third Temple in his account.

What is actually built: the enclosure in this map is the 3000-amah square, 150,000 cm a side, with its wall faces at X -33100 to 116900 and Y -33150 to 116850. The Future Mount platform underneath it is only about 377 m square, so the ring is far larger than the terrain it stands on. That mismatch is a recorded gap, not a claim.`,measurements:[{label:"Yechezkel reading, each side",value:"500 reeds = 3000 amot = 150,000 cm at 50 cm/amah",source:"Yechezkel 42:15-20 with Rashi; Yechezkel 40:5"},{label:"Middot's Har HaBayit",value:"500 amot = 25,000 cm",source:"Mishnah Middot 2:1 (Second Temple)"},{label:"Ratio",value:"36 times the area",source:"Lishchno Tidreshu p. 359; the Kalir piyut on the figure"},{label:"As built",value:"150,000 cm a side, centre [41900, 41850], wall 300 cm thick and 300 cm high",source:"SourceAssets/FutureMountV1/EnclosureV1/enclosure-design.json"}],dispute:[{who:"Yechezkel 42:15-20 as read by Rashi, adopted by the book and built here",holds:"500 reeds, so 3000 amot a side"},{who:"Mishnah Middot 2:1",holds:"the Har HaBayit is 500 amot square - in the research pile this is the Second Temple figure, and whether it governs the future precinct is exactly what is at issue"},{who:"The author of Lishchno Tidreshu, starred for study only",holds:"an additional inner soreg ring of 500 amot square within the 3000, the cheil inside it - his own 'forced reading'"}],sources:["Yechezkel 42:15-20 with Rashi","Yechezkel 40:5","Yechezkel 40:2 with Rashi","Mishnah Middot 2:1","Mishkenei Elyon 184, 188, 189, 191-192, 196","Lishchno Tidreshu pp. 112-113, 359-364 (Hebrew confirmed on the page images)"]},{id:"sanctuary-not-centred",category:"precinct",name:"The House does not stand in the middle",he:"",confidence:"certain",summary:"The Sanctuary sits toward the north-west of the precinct, not at its centre. Open ground is largest to the south, then east, then north, and least to the west, and the city lies on the slope to the south. That asymmetry is why the enclosure in this model is centred at [41900, 41850] rather than on the Temple, and why the clearances come out as 500 amot west, 501 north, 2176 east and 2175 south.",measurements:[{label:"Clearance west / north / east / south",value:"500 / 501 / 2176 / 2175 amot",source:"SourceAssets/FutureMountV1/EnclosureV1/enclosure-design.json"}],dispute:[],sources:["Mishkenei Elyon 184, 189, 196","Yechezkel 45:1-5, 48:10-21","Lishchno Tidreshu pp. 112-113, 116, fig. 2'2"]},{id:"terumah",category:"precinct",name:"The terumah, the portion around the precinct",he:"\u05EA\u05E8\u05D5\u05DE\u05D4",confidence:"disputed",summary:"Yechezkel 45:1 and 48:8-20 describe a consecrated portion of land 25,000 on a side around the precinct. Whether those 25,000 are amot or reeds is itself disputed, which is a six-fold difference. This model draws the ring in amot and labels it rather than deciding.",measurements:[{label:"Terumah side",value:"25,000 - unit disputed",source:"Yechezkel 45:1, 48:8-20"}],dispute:[{who:"Read as amot",holds:"25,000 amot"},{who:"Read as reeds",holds:"150,000 amot"}],sources:["Yechezkel 45:1, 48:8-20"]},{id:"precinct-wall-and-gates",category:"precinct",name:"The wall of the Mount and its five gates",he:"\u05D7\u05D5\u05DE\u05EA \u05D4\u05E8 \u05D4\u05D1\u05D9\u05EA",confidence:"certain",summary:"A wall six amot thick and six amot high runs round all four sides of the precinct, dividing what is holy from what is not. Five gates pierce it: two on the south, one each on the east, north and west. Each opening is ten amot wide and fifty high, with doors. The extra ten amot of wall carried above the opening - making sixty in all - is the author's, marked for study.",measurements:[{label:"Wall",value:"6 x 6 amot = 300 x 300 cm",source:"Yechezkel 40:5 with Rashi citing Middos 2:4"},{label:"Gate opening",value:"10 amot wide x 50 high = 500 x 2500 cm",source:"Mishkenei Elyon 170, 172, 196"},{label:"Total gate height",value:"60 amot",source:"authored - the book's starred suggestion"},{label:"As built",value:"five gates at E [116750, 0], N [0, -33000], W [-32950, 0], S1 [16900, 116700], S2 [66900, 116700]",source:"SourceAssets/FutureMountV1/EnclosureV1/enclosure-design.json"}],dispute:[],sources:["Yechezkel 40:5 with Rashi","Mishnah Middot 1:3, 2:4","Mishkenei Elyon 170, 172, 196","Sanhedrin 100a / Bava Basra 75a","Lishchno Tidreshu pp. 115-117"]},{id:"soreg",category:"precinct",name:"The soreg",he:"\u05E1\u05D5\u05E8\u05D2",confidence:"certain",summary:"A wooden lattice ten tefachim high running round the court, well inside the precinct wall. It is low enough to step over, which is the point: it marks a line rather than blocking one. It is built here at 83.33 cm, at a radius of about 10,250 cm from the Temple centre.",measurements:[{label:"Height",value:"10 tefachim = 83.333 cm",source:"Mishnah Middot 2:3; built at 83.3333 cm"}],dispute:[],sources:["Mishnah Middot 2:3","Mishkenei Elyon 191-192","Lishchno Tidreshu pp. 121-126"]},{id:"cheil",category:"precinct",name:"The cheil",he:"\u05D7\u05D9\u05DC",confidence:"disputed",summary:"Inside the soreg comes the cheil, and what the cheil is depends on whom you follow. The Rambam, the Meiri and Mishkenei Elyon read it as a wall ten amot high with ten amot of open ground inside it, and that is what is built here. The Bartenura and the Tosafos Yom Tov read the soreg itself as the cheil's wall, leaving only the open strip. The one-amah thickness given to the wall in this model is the book author's own, offered for study.",measurements:[{label:"Wall height",value:"10 amot = 500 cm",source:"Rambam, Beis HaBechirah 5:3, 6:1"},{label:"Open strip",value:"10 amot = 500 cm",source:"Mishnah Middot 2:3"},{label:"Wall thickness",value:"1 amah - authored",source:"Lishchno Tidreshu, starred for study"},{label:"As built",value:"cheil wall outer face 9750 cm, height 500 cm; cheil slab 9200..9700 cm",source:"SourceAssets/FutureMountV1/EnclosureV1/enclosure-design.json"}],dispute:[{who:"Rambam, Meiri, Mishkenei Elyon - built here",holds:"the cheil is a ten-amah wall plus ten amot of open ground"},{who:"Bartenura, Tosafos Yom Tov",holds:"the soreg is the cheil's wall; the cheil is the strip"}],sources:["Mishnah Middot 2:3","Rambam, Beis HaBechirah 5:3, 6:1","Meiri on Middot 2:3 / Yoma 16b","Bartenura and Tosafos Yom Tov on Middot 2:3","Mishkenei Elyon 191-196","Lishchno Tidreshu pp. 121-126"]},{id:"height-terraces",category:"precinct",name:"How the whole complex steps upward",he:"",confidence:"disputed",summary:"Nothing here is level. The mountain slopes down on all four sides; the outer court gate floors sit below the inner court; the Court of Israel sits two and a half amot below the priests' court; the House stands six amot above that; and the Even HaShtiya rises three fingerbreadths above the House's floor. The step counts are firm - twelve steps at the east outer gate, seven at the north and south, eight at every inner gate, twelve to the Ulam. The slopes and the exact western levels are the author's.",measurements:[{label:"As built, walkable tops",value:"mount platform 0; outer court 300; Court of Israel 500; priests' court 625; House 925; altar burning surface 1066.67",source:"SourceAssets/architecture-manifest.json"},{label:"Outer gate floors",value:"east 6.5 amot below the inner court, north and south 4",source:"Rashi on Yechezkel 42:9; Middos 2:3"}],dispute:[{who:"Step counts",holds:"certain - Middos 2:3, 2:6"},{who:"Slopes and western levels",holds:"the book author's, starred"}],sources:["Rashi on Yechezkel 42:9","Mishnah Middot 2:3, 2:6","Yoma 16b","Mishkenei Elyon 192-193, 196, 198","Lishchno Tidreshu pp. 300-305"]},{id:"outer-court",category:"courts",name:"The outer court",he:"\u05D4\u05E2\u05D6\u05E8\u05D4 \u05D4\u05D7\u05D9\u05E6\u05D5\u05E0\u05D4",confidence:"certain",summary:"The great court the people stood in. Its wall is six amot thick; three gates open into it from the Mount - east, north and south - and three more lead from it into the inner court. There is no west gate anywhere in this plan. It is a hundred amot from any gate to the gate facing it across the court.",measurements:[{label:"Gate to facing gate",value:"100 amot = 5000 cm",source:"Yechezkel 40:19, 23, 27 with Rashi"},{label:"As built",value:"floor +/-7800 cm, top Z 300; supporting platform +/-8100 cm",source:"SourceAssets/architecture-manifest.json SM_0129"}],dispute:[],sources:["Yechezkel 40:17-27","Rashi on Yechezkel 40:19","Mishkenei Elyon 171, 182","Lishchno Tidreshu pp. 141-147"]},{id:"outer-gates",category:"courts",name:"The outer gates",he:"\u05E9\u05E2\u05E8\u05D9 \u05D4\u05E2\u05D6\u05E8\u05D4 \u05D4\u05D7\u05D9\u05E6\u05D5\u05E0\u05D4",confidence:"certain",summary:"Each outer gate is a block twenty-five amot wide: five of wall, two and a half, the ten-amah opening, two and a half, five. Six cells line its passage, three a side. In front of it a vestibule projects ten amot into the court, its interior thirteen by eight and fifty high, flanked by two round pillars two amot square and sixty high with palm capitals. Twelve steps climb to the east gate, seven to the north and south, because the ground is higher there.",measurements:[{label:"Gate block width",value:"25 amot = 5 + 2.5 + 10 + 2.5 + 5",source:"Rashi on Yechezkel 40:13"},{label:"Opening",value:"10 amot wide x 50 high",source:"Yechezkel 40:6-16 with Rashi; height from Mishkenei Elyon 170"},{label:"Vestibule interior",value:"13 x 8 amot, 50 high",source:"Yechezkel 40:8-9 with Rashi"},{label:"Eilim",value:"2 x 2 amot, 60 high",source:"Yechezkel 40:14 with Rashi; the palm being 10 of the 60 is authored"},{label:"As built",value:"Outer E threshold X 7800..8100 Z 300; Outer E stair X 8600..9200 Z 0..300; Outer N/S thresholds at Y -/+7800..8100 Z 425",source:"SourceAssets/architecture-manifest.json"}],dispute:[],sources:["Yechezkel 40:6-16, 40:19-27","Rashi on Yechezkel 40:13, 40:14","Mishkenei Elyon 166-197","Lishchno Tidreshu pp. 121-147"]},{id:"gate-cells",category:"courts",name:"The cells in the gate passage",he:"\u05EA\u05D0\u05D9\u05DD",confidence:"certain",summary:"Six chambers, three on each side of the passage, each six amot square inside with five-amah walls, projecting eleven amot outward on the Mount side. They are chain-linked one to the next and can be entered only from the passage itself. The five-amah cell walls rising to fifty and a ceiling spanning the passage - so that the vestibule, the passage and the gate are covered continuously - is the book author's proposal.",measurements:[{label:"Cell interior",value:"6 x 6 amot, walls 5, projection 11",source:"Yechezkel 40:7-13 with Rashi"}],dispute:[],sources:["Yechezkel 40:7-13","Rashi on Yechezkel 40:13","Metzudas Dovid","Mishkenei Elyon 197, 199","Lishchno Tidreshu pp. 127-134, 153"]},{id:"splayed-windows",category:"house",name:"The windows that widen outward",he:"\u05D7\u05DC\u05D5\u05E0\u05D5\u05EA \u05E9\u05E7\u05D5\u05E4\u05D9\u05DD \u05D0\u05D8\u05D5\u05DE\u05D9\u05DD",confidence:"disputed",summary:"The windows are built the wrong way round on purpose: narrow on the inside and widening as they go out, the opposite of a window meant to gather light. They carry no glass and are never closed. Where they are and how many is another matter - the counts in this model are the book author's, and Rashi's gloss about them being sealed from within is treated in the book as a corrupt reading.",measurements:[{label:"Counts",value:"authored throughout - 12 per gate, 12 per court-wall side, 4 each in the Heikhal's north, south and east walls, 12 in the Kodesh HaKodashim",source:"the book author, starred"}],dispute:[{who:"Rashi on Yechezkel 40:16, Mishkenei Elyon 169",holds:"shape and outward splay are settled; open, never glazed"},{who:"The book author",holds:"the counts and placement, offered for study"}],sources:["Yechezkel 40:16 with Rashi","Mishkenei Elyon 169","Rabbeinu Bachya, Beha'aloscha 8","Lishchno Tidreshu pp. 138-140, 224-226"]},{id:"gallery-chambers",category:"courts",name:"The thirty chambers on the gallery",he:"\u05E9\u05DC\u05E9\u05D9\u05DD \u05DC\u05E9\u05DB\u05D5\u05EA",confidence:"disputed",summary:"Thirty chambers stand on a gallery whose floor is fifty amot up - the same height as the gate openings. Ten on the east, ten on the south, ten on the north, five to each side of every gate, and none at all on the west. That much is Rashi and Mishkenei Elyon. Their size, their height and the suggestion that they are where women stood are the book author's.",measurements:[{label:"Count and gallery floor",value:"30 chambers, floor at 50 amot",source:"Rashi on Yechezkel 40:17-18; Mishkenei Elyon 185, 197"},{label:"Chamber size",value:"10 x 5 amot, 10 high, 5-amah slab - authored",source:"the book author"}],dispute:[{who:"Rashi, Radak, Mishkenei Elyon",holds:"thirty chambers with the gallery floor at fifty amot"},{who:"The book author",holds:"their dimensions, and that women may have used them"}],sources:["Yechezkel 40:17-18 with Rashi","Radak","Mishnah Middot 2:5","Mishkenei Elyon 185, 197","Lishchno Tidreshu pp. 141-143, 339"]},{id:"corner-courts",category:"courts",name:"The four corner courts",he:"",confidence:"certain",summary:"Four unroofed courts, forty by thirty amot, one in each corner of the outer court, where the lesser holy offerings were cooked. No piers and no gallery run over them.",measurements:[{label:"Each court",value:"40 x 30 amot",source:"Yechezkel 46:21-22; Rashi on 40:18"}],dispute:[],sources:["Yechezkel 40:18, 46:21-22 with Rashi","Mishkenei Elyon 185, 197","Lishchno Tidreshu pp. 143, 276-278"]},{id:"circulation",category:"people",name:"Which way a pilgrim walked",he:"",confidence:"certain",summary:"Everyone entering the Mount turned right and circled, leaving by the left. A mourner, or someone under a ban, went the other way round, so that whoever met him coming the wrong way knew and could ask what had happened to him.",measurements:[],dispute:[],sources:["Mishnah Middot 2:2","Bartenura on Middot 2:2","Lishchno Tidreshu p. 118"]},{id:"gate-calendar",category:"people",name:"Which gate is open when",he:"",confidence:"certain",summary:"The outer east gate is the gate of entry all year round, except at the three festivals, when the crowd enters by the north and leaves by the south, or the reverse. The inner east gate is different: it opens on Shabbos and on Rosh Chodesh and on no other day. On an ordinary weekday the way into the inner court was through the lower chambers, which have a door into the Court of Israel. This model has no lower chambers, so the tour walks up a gate that would be shut.",measurements:[],dispute:[],sources:["Yechezkel 46:1, 46:9","Rambam, Beis HaBechirah 7:2, 7:16","Keilim 1:8","Rashi on Yechezkel 42:12","Lishchno Tidreshu pp. 137, 313, 341"]},{id:"inner-gates",category:"courts",name:"The inner gates",he:"\u05E9\u05E2\u05E8\u05D9 \u05D4\u05E2\u05D6\u05E8\u05D4 \u05D4\u05E4\u05E0\u05D9\u05DE\u05D9\u05EA",confidence:"certain",summary:"The inner gates are the outer gates turned back to front. Eight steps instead of twelve or seven, and the vestibule projecting outward into the great court with the cells behind it, so a person climbing goes vestibule, then steps over the eleven amot of cells, then gate. There are three of them and no more.",measurements:[{label:"Steps",value:"8, half an amah each = 4 amot",source:"Yechezkel 40:31 with Rashi; Middos 2:3"},{label:"As built",value:"Inner E threshold X 2500..2800 Z 500; Inner N Y -2800..-2500; Inner S Y 2500..2800; both at Z 625",source:"SourceAssets/architecture-manifest.json"}],dispute:[],sources:["Yechezkel 40:28-37 with Rashi","Mishnah Middot 2:3","Mishkenei Elyon 193","Lishchno Tidreshu pp. 148-152"]},{id:"gate-names",category:"courts",name:"The names of the three inner gates",he:"",confidence:"authored",summary:"That there are three inner gates and not the seven or thirteen of the Second Temple is settled. What they are called is not. The book maps the north to the gate of the offering, because kodshei kodashim are slaughtered on the north side, and the south to the water gate, because the water of Yechezkel 47:1-2 flows out from the Kodesh HaKodashim through the southern inner gate; he floats a gate of the firstborn as well. The research records this mapping explicitly as the author's, not the navi's.",measurements:[],dispute:[],sources:["Mishnah Middot 1:4, 2:6","Yechezkel 47:1-2","Lishchno Tidreshu p. 340"]},{id:"inner-court-recesses",category:"courts",name:"The six recesses in the inner court wall",he:"\u05D0\u05D5\u05DC\u05DE\u05D9\u05DD",confidence:"disputed",summary:"Recesses twenty-five amot by five are set into the thickness of the inner court wall, one on each side of each inner gate, leaving half an amah of wall on each face. That they are twenty-five by five is Rashi. That there are six of them is the author's reasoning from there being three gates, and their twenty-five-amah height is his too. They are not in this model at all - a recorded gap.",measurements:[{label:"Each recess",value:"25 x 5 amot",source:"Rashi on Yechezkel 40:30, 41:15-16"}],dispute:[{who:"Rashi, Mishkenei Elyon 188",holds:"the 25 x 5 in-wall recess is certain"},{who:"The book author",holds:"there are six, and they rise 25 amot"}],sources:["Yechezkel 40:29-30, 41:15-16 with Rashi","Tosafos on Yechezkel 42:3","Mishkenei Elyon 188","Lishchno Tidreshu pp. 150-151, 220-224"]},{id:"slaughter-tables",category:"courts",name:"The slaughter tables and the rinsing chamber",he:"",confidence:"certain",summary:"Eight tables belong at the north inner gate: four inside its vestibule, two east and two west, and four in the cell passage at the gate's own floor level. The vestibule, although it stands in the outer court, carries inner-court sanctity. At the gate's west shoulder is a closed chamber with four stone tables an amah and a half square and an amah high, and eight low cedar posts carrying iron hooks a tefach long in three rows. In this build the eight tables are not at the gate at all: they sit clustered inside the court at X -1188 to -663, Y -2088 to -1812. That is a recorded gap, not a reading.",measurements:[{label:"Marble tables",value:"1.5 x 1.5 x 1 amot = 75 x 75 x 50 cm, four of them",source:"Yechezkel 40:42-43 with Rashi"},{label:"Hooks",value:"1 tefach, on eight posts in three rows",source:"Yechezkel 40:43; Middos 3:5; Tamid 3:5, 4:2"},{label:"As built",value:"8 tables at X -1187.5..-662.5, Y -2087.5..-1812.5, Z 665..675",source:"SourceAssets/architecture-manifest.json"}],dispute:[],sources:["Yechezkel 40:38-43 with Rashi","Zevachim 47a-48a","Pesachim 65a","Mishnah Tamid 3:5, 4:2","Mishnah Middot 3:5","Rambam, Maaseh HaKorbanos 5:2-3","Mishkenei Elyon 177-178, 199, 202","Lishchno Tidreshu pp. 154-164"]},{id:"song-and-clothing-chambers",category:"courts",name:"The song chamber and the clothing chamber",he:"",confidence:"certain",summary:"At the east shoulder of the north inner gate stands the Levites' chamber for the instruments - one chamber from outside, divided in two within, its doors facing south. At the north shoulder of the east inner gate stands the chamber where the kohanim put on their white linen. Both positions are Rashi and Mishkenei Elyon. In this build the chamber labelled 'Song chamber' is in the south-west of the court instead, and the clothing chamber is absent. Recorded gap.",measurements:[{label:"As built",value:"Song chamber at X -2200..-1700, Y 1900..2400, Z 605..625 - the wrong corner",source:"SourceAssets/architecture-manifest.json SM_0041"}],dispute:[],sources:["Yechezkel 40:44-46 with Rashi","Mishkenei Elyon 178-179, 199","Rambam, Klei HaMikdash 8:8-9 (the 96 garment niches, a Second Temple detail the author reuses)","Lishchno Tidreshu pp. 165-169"]},{id:"court-of-israel",category:"courts",name:"The Court of Israel and the priests' court",he:"\u05E2\u05D6\u05E8\u05EA \u05D9\u05E9\u05E8\u05D0\u05DC \u05D5\u05E2\u05D6\u05E8\u05EA \u05DB\u05D4\u05E0\u05D9\u05DD",confidence:"certain",summary:"The inner court is a hundred amot square and divides east to west as seventeen amot for Israel, seventeen for the kohanim, thirty-two for the altar and thirty-four from the altar to the porch. The Court of Israel is two and a half amot lower than the priests' court. North to south the reckoning is four amot from the wall to the ramp, sixty-two for ramp and altar together, and thirty-four to the north wall.",measurements:[{label:"Inner court",value:"100 x 100 amot",source:"Yechezkel 40:47"},{label:"East-west split",value:"17 + 17 + 32 + 34",source:"Mishkenei Elyon 182, 198, 204"},{label:"As built",value:"Court of Israel floor X 1675..2500, Z 500; priests' court X -2500..1575, Z 625",source:"SourceAssets/architecture-manifest.json SM_0130, SM_0071"}],dispute:[],sources:["Yechezkel 40:47 with Rashi","Mishnah Middot 2:6","Mishkenei Elyon 182, 198, 204","Lishchno Tidreshu pp. 170-172"]},{id:"no-ezras-nashim",category:"courts",name:"There is no Women's Court here",he:"",confidence:"authored",summary:"Every plan of the Second Temple has an Ezras Nashim east of the Israelite Court. This plan does not, and neither does this model: the research assembled for this project contains no Third Temple row describing one, and the word appears nowhere in the build's receipts. The nearest thing in the book is a suggestion that women may have used the thirty gallery chambers of the outer court, and the research marks that as the author's, after the Second Temple's balcony. Saying 'we found nothing' is a result. It is not the same as saying there was none.",measurements:[],dispute:[],sources:["Lishchno Tidreshu p. 339 (women in the gallery chambers - marked author)","Mishnah Middot 2:5, 3:5, 5:3 (the Second Temple arrangement)","Rambam, Biat HaMikdash 3:3-7 (zone-graded exclusion, a halachic register)"]},{id:"house-moved-west",category:"house",name:"Why the House stands thirteen amot further west",he:"",confidence:"certain",summary:"The altar's site is fixed and cannot move. So when the distance from altar to porch grows from the Second Temple's twenty-two amot to thirty-four, and the partition of the Kodesh HaKodashim grows from one amah to two, the whole House shifts west by thirteen amot. The Zohar's answer to the obvious worry - that the Aron would then no longer sit on the Even HaShtiya - is that the stone fills the whole chamber.",measurements:[{label:"Shift",value:"12 amot from the altar-to-Ulam distance, 1 from the partition = 13",source:"Mishkenei Elyon 182, 198, 204; Middos 4:7, 5:1"}],dispute:[],sources:["Rambam, Beis HaBechirah 2:1, 2:3","Mishnah Middot 4:7, 5:1","Zohar","Mishkenei Elyon 182, 198, 204","Lishchno Tidreshu p. 172 (marked as comparison)"]},{id:"duchan",category:"courts",name:"The duchan",he:"\u05D3\u05D5\u05DB\u05DF",confidence:"certain",summary:"The step between the Court of Israel and the priests' court: a rise of one amah with a three-stepped platform on it, half an amah each, two and a half amot in all. The Levites stood on it facing east. This is R' Eliezer b. Yaakov's arrangement in Middot 2:6, adopted here.",measurements:[{label:"Total rise",value:"2.5 amot = 125 cm",source:"Mishnah Middot 2:6"},{label:"As built",value:"four rises X 1575..1675, tops Z 550, 575, 600, 625 from floor Z 500 - 125 cm",source:"SourceAssets/architecture-manifest.json SM_1669..SM_1672"}],dispute:[],sources:["Mishnah Middot 2:6","Rashi on Yechezkel 42:12","Rambam, Beis HaBechirah 6:3-5","Rosh on Middot 2:6","Mishkenei Elyon 184, 198","Lishchno Tidreshu pp. 171, 313, 342"]},{id:"levites-song",category:"service",name:"The Levites' song",he:"",confidence:"certain",summary:"The Levites sang at the wine libation of the daily offering, morning and afternoon, standing on the duchan and facing east. Their instruments were kept in the chamber at the east shoulder of the north inner gate.",measurements:[],dispute:[],sources:["Divrei HaYamim II 5:12","Mishnah Middot 2:6","Yechezkel 40:44-45 with Rashi","Rambam, Beis HaBechirah 6:3-5","Mishkenei Elyon 178-179, 198"]},{id:"outer-altar",category:"altar",name:"The altar",he:"\u05DE\u05D6\u05D1\u05D7 \u05D4\u05D7\u05D9\u05E6\u05D5\u05DF",confidence:"disputed",summary:`Thirty-two amot square, in the exact centre of the inner court, thirty-four amot from the porch. That much is Yechezkel 40:47 as Rashi and Mishkenei Elyon read it, and everything else in the plan is measured from it because its site is fixed forever.

What this project does NOT have from the sources is the altar's own build-up. The volume of the book read here covers Yechezkel 40 to 42 and defers the altar's height, yesod, sovev and horns to a note on chapter 43 in a second part that is not in the export. So the tiers, the ramp's width and slope and the horn heights in this model come from the architecture manifest and not from a text, and they are labelled authored here for that reason. The Gemara's rule is that the Torah's altar measures are not indispensable - it may be made larger, never smaller than Moshe's.`,measurements:[{label:"Each side",value:"32 amot = 1600 cm",source:"Yechezkel 40:47 with Rashi; Mishkenei Elyon 182, 198"},{label:"Altar to the porch",value:"34 amot (22 in the Second Temple)",source:"Mishkenei Elyon 182, 198, 204"},{label:"As built - yesod",value:"X,Y +/-800 cm, Z 625..716.67",source:"SourceAssets/architecture-manifest.json SM_0155..SM_0158"},{label:"As built - middle tier",value:"+/-750 cm, Z 716.67..916.67",source:"SourceAssets/architecture-manifest.json SM_0159"},{label:"As built - burning surface",value:"+/-708.33 cm, top Z 1066.67",source:"SourceAssets/architecture-manifest.json SM_0160"},{label:"As built - horns",value:"four, Z 1066.67..1108.33",source:"SourceAssets/architecture-manifest.json SM_0162..SM_0165"}],dispute:[{who:"Yechezkel 40:47 with Rashi and Mishkenei Elyon",holds:"32 amot square, central, 34 from the porch - settled"},{who:"Not in the sources read",holds:"height, yesod, sovev, horns and ramp - deferred by the book to chapter 43, part 2, which is not in this export"}],sources:["Yechezkel 40:47 with Rashi","Zevachim 62a","Ohr HaChaim on Shemos 25:9","Chasam Sofer YD 236","Rambam, Beis HaBechirah 2:1-3","Mishkenei Elyon 182, 198, 204","Lishchno Tidreshu pp. 170-173"]},{id:"kevesh",category:"altar",name:"The ramp",he:"\u05DB\u05D1\u05E9",confidence:"authored",summary:"The altar is climbed by a ramp from the south, not by steps. The only figure the research gives is indirect: north to south, the ramp and the altar together account for sixty-two amot, with four amot from the court wall to the ramp's foot and thirty-four from the altar to the north wall. Its width, its length and its gradient in this model are the build's own, and no source in this project fixes them.",measurements:[{label:"Ramp and altar together",value:"62 amot north-south",source:"Mishkenei Elyon 182, 198"},{label:"As built",value:"X +/-400 cm (16 amot wide), Y 710.08..2300, Z 625..1066.67",source:"SourceAssets/architecture-manifest.json SM_0166"}],dispute:[],sources:["Yechezkel 40:47 as read in Mishkenei Elyon 182, 198","Lishchno Tidreshu p. 170"]},{id:"altar-furniture",category:"altar",name:"The ash place, the shis and the two tables",he:"",confidence:"disputed",summary:"Around the altar stand: the place of the ashes, east of it, ten amot north of the ramp's foot and three tefachim east; the shis, the drain at the south-west corner; two tables west of the ramp, one for the ninety-three service vessels and one for the fats; a fire pan; and cups for the wine and water libations. The items themselves are from the Torah and are not in question. Their positions come from Middot, which describes the Second Temple, and are adopted here for want of anything else. None of them are in this model.",measurements:[{label:"Ash place",value:"10 amot north of the ramp's foot, 3 tefachim east",source:"Middos, as read in Lishchno Tidreshu p. 173"}],dispute:[{who:"Torah",holds:"the items exist"},{who:"Middos - a Second Temple description",holds:"where they stand; adopted for want of a Third Temple source"}],sources:["Mishnah Middot 3:1-3","Mishnah Tamid","Lishchno Tidreshu p. 173"]},{id:"kiyor",category:"altar",name:"The kiyor",he:"\u05DB\u05D9\u05D5\u05E8",confidence:"disputed",summary:"The laver stands with its base between the porch and the altar. A kohen sanctified his hands and his feet from it before serving, and again after leaving the court; the requirement is its own, and no immersion replaces it. A pit and a pulley lower it into water overnight so it is not disqualified by standing. Its size and its number of spouts are not in any source read for this project: the basin in this build is 208 cm across with twelve spouts, and those are the build's numbers.",measurements:[{label:"Position",value:"between the Ulam and the altar",source:"Middos 3:6; Lishchno Tidreshu p. 173"},{label:"As built",value:"basin X -2054..-1846, Y 1396..1604, Z 690..750; pedestal Z 625..696; 12 spouts",source:"SourceAssets/architecture-manifest.json SM_0072, SM_0073, SM_0078..SM_0122"}],dispute:[{who:"Middos 3:6, Rambam",holds:"position and function"},{who:"Not in the sources read",holds:"dimensions and spout count - authored here"}],sources:["Shemos 30:17-21","Mishnah Middot 3:6","Rambam, Biat HaMikdash 5:1-2","Mishkenei Elyon 177","Lishchno Tidreshu p. 173"]},{id:"unmentioned-vessels",category:"method",name:"What licenses a vessel Yechezkel never mentions",he:"",confidence:"certain",summary:"Yechezkel names one piece of furniture in the House - the table of 41:22 - and no others. The menorah, the golden altar, the Aron and its keruvim, the kiyor and its base are all absent from his account. Rashi, the Radak, the Tosafos Yom Tov and Mishkenei Elyon take the Torah's furniture as continuing unless the navi cancels it, and the book records that as certain. That principle is what allows this reconstruction to contain anything at all beyond the walls; it is worth knowing it is a principle and not a verse.",measurements:[],dispute:[],sources:["Rashi, Radak and Tosafos Yom Tov as gathered in Mishkenei Elyon 177","Lishchno Tidreshu p. 160"]},{id:"twelve-steps",category:"house",name:"The twelve steps to the porch",he:"",confidence:"certain",summary:"Twelve steps of half an amah lift the House six amot above the priests' court. They are laid out as two steps, a landing of three amot, twice more the same, then two steps and a landing of four - twenty-one amot from foot to threshold.",measurements:[{label:"Rise / run",value:"6 amot / 21 amot",source:"Yechezkel 40:49 with Rashi; Middos 3:6"},{label:"As built",value:"foot [-1350, 0, 625] to [-2375, 0, 925]",source:"SourceAssets/runtime-review/route-waypoints.json - Ulam stair diagnostics"}],dispute:[],sources:["Yechezkel 40:49 with Rashi","Mishnah Middot 3:6","Rambam, Beis HaBechirah 6:4","Lishchno Tidreshu pp. 174-179"]},{id:"eilim-and-palms",category:"house",name:"The two pillars at the entrance",he:"\u05D0\u05D9\u05DC\u05D9\u05DD",confidence:"disputed",summary:"Two pillars, two amot square and sixty high with palm capitals, stand at the porch entrance in the place Yachin and Boaz held in the First Temple - though those were thirty-six amot high and four thick, so these are not the same pillars remade. How much of the sixty is capital is the author's guess: he suggests ten.",measurements:[{label:"Pillar",value:"2 x 2 amot, 60 high",source:"Yechezkel 40:49 with Rashi"},{label:"Palm capital",value:"10 of the 60 - authored",source:"the book author, starred"},{label:"Yachin and Boaz, for contrast",value:"36 amot high, 4 thick",source:"Melachim I 7:16"}],dispute:[{who:"Rashi on Yechezkel 40:49, Mishkenei Elyon 166, 172",holds:"2 x 2 x 60 with a palm capital is certain"},{who:"The book author",holds:"ten of the sixty amot are capital"}],sources:["Yechezkel 40:49 with Rashi","Melachim I 7:16","Mishkenei Elyon 166, 172, 197","Lishchno Tidreshu p. 176"]},{id:"ulam",category:"house",name:"The Ulam",he:"\u05D0\u05D5\u05DC\u05DD",confidence:"certain",summary:"The porch of the House: twenty amot north to south, eleven east to west, walls five amot thick, its facade a hundred amot long. The jambs step three amot in from each side, so the opening is fourteen amot wide - not the twenty of the Second Temple - and fifty amot high. Only palm reliefs go on its jambs; the keruvim begin inside.",measurements:[{label:"Interior",value:"20 x 11 amot, walls 5",source:"Yechezkel 40:48 with Rashi"},{label:"Opening",value:"14 amot wide, 50 high",source:"Yechezkel 40:48 with Rashi; height Mishkenei Elyon 170"},{label:"As built",value:"floor X -3300..-2750, top Z 925; clear opening 700 cm at Y +/-350",source:"SourceAssets/architecture-manifest.json SM_0145, SM_0167, SM_0172"}],dispute:[],sources:["Yechezkel 40:48-49 with Rashi","Yechezkel 41:26 with Rashi","Mishkenei Elyon 170, 202","Lishchno Tidreshu pp. 174-179, 268-270"]},{id:"beis-hachalifos",category:"house",name:"The chambers of the knives",he:"\u05D1\u05D9\u05EA \u05D4\u05D7\u05DC\u05D9\u05E4\u05D5\u05EA",confidence:"certain",summary:"Two chambers flank the porch, fifteen amot north to south by ten east to west, where the slaughtering knives were stored. Their five-amah east walls are part of the hundred-amah facade. The one-amah west wall and the small side doors are the author's.",measurements:[{label:"Each chamber",value:"15 x 10 amot",source:"Yechezkel 40:48, 41:12 with Rashi; Middos 4:7"},{label:"As built",value:"knife store wing X -2950..-2750, Y 500..2500, with nine niches",source:"SourceAssets/architecture-manifest.json SM_0022..SM_0031"}],dispute:[],sources:["Yechezkel 40:48, 41:12 with Rashi","Mishnah Middot 4:7","Zevachim 55b","Mishkenei Elyon 176, 202","Lishchno Tidreshu p. 174"]},{id:"miltaros-historical",category:"method",name:"The stepped lintel over the porch is Second Temple",he:"",confidence:"certain",summary:"Five stepped olive-wood beams above the porch entrance, each projecting an amah further at each side, are Middot 3:7 describing the Second Temple. They are not described for this House, and the book says so. The layered stone lintel and cornice in this model are that Second Temple styling carried over by mistake - a recorded gap, not a reading.",measurements:[],dispute:[],sources:["Mishnah Middot 3:7","Lishchno Tidreshu p. 265, marked historical","Rashi on Yechezkel 41:25"]},{id:"heikhal",category:"house",name:"The Heikhal",he:"\u05D4\u05D9\u05DB\u05DC",confidence:"certain",summary:"Forty amot long, twenty wide, with walls six amot thick on all four sides. Its doorway is ten amot wide and fifty high - twenty in the Second Temple - with a square frame: threshold, straight lintel, two jambs, and nothing round or five-sided about it.",measurements:[{label:"Interior",value:"40 x 20 amot = 2000 x 1000 cm",source:"Yechezkel 41:2 with Rashi"},{label:"Walls",value:"6 amot",source:"Yechezkel 41:5; Mishkenei Elyon 164"},{label:"Door opening",value:"10 x 50 amot",source:"Yechezkel 41:2, 41:21; height Mishkenei Elyon 169-170"},{label:"As built",value:"floor X -5600..-3600, Y +/-500, top Z 925; ceiling Z 2925..3025",source:"SourceAssets/architecture-manifest.json SM_0146"}],dispute:[],sources:["Yechezkel 41:1-2, 41:21","Rashi on Yechezkel 41:2","Mishkenei Elyon 164, 169-170, 203","Lishchno Tidreshu pp. 182-183, 240"]},{id:"heikhal-doors",category:"house",name:"The doors of the Heikhal",he:"",confidence:"disputed",summary:"Two pairs of leaves, each leaf five amot wide and fifty high. The outer pair sits an amah in from the jamb and folds back onto the five amot of wall thickness, the extra amah being the door's own thickness; the inner pair stands at the Sanctuary face and folds onto the five-amah shoulders inside. That is the Tanna Kamma's arrangement, followed by the Rambam and the Ramchal, and it is the one the book builds. Rashi also carries R' Yehudah's version of the folding. The western pair was opened first each morning, then the eastern, and they were locked each evening by way of the small northern door. In this model the doors are four flat slabs protruding into the Sanctuary - a recorded gap.",measurements:[{label:"Each leaf",value:"5 amot wide, 50 high",source:"Yechezkel 41:24 with Rashi; Middos 4:1"},{label:"As built",value:"SM_1948..SM_1951, X -3670..-3220, Y +/-250.5..261.5, Z 925..3425",source:"SourceAssets/architecture-manifest.json"}],dispute:[{who:"Tanna Kamma, Rambam Beis HaBechirah 4:7, Ramchal - built here",holds:"two pairs, outer folding into the wall thickness"},{who:"R' Yehudah, cited by Rashi",holds:"a different folding arrangement"}],sources:["Yechezkel 41:23-24 with Rashi","Mishnah Middot 4:1-2","Mishnah Tamid 3:7","Rambam, Beis HaBechirah 4:7","Mishkenei Elyon 170","Lishchno Tidreshu pp. 259-263"]},{id:"gold-over-cedar",category:"house",name:"Why there is cedar under the gold",he:"",confidence:"certain",summary:"Gold cannot be laid directly on stone. So the walls, jambs, doors and ceiling of the Sanctuary and the Kodesh HaKodashim are panelled floor to ceiling in thin cedar boards, carved, and the gold is beaten into the carving so the forms stay visible, fixed with gold nails. Only the window openings are left bare. In this Temple, unlike the last, the wall behind the doors is lined too. No wood is left exposed anywhere in the House or the courts. That the floor is also carved boards under gold is the author's.",measurements:[],dispute:[],sources:["Yechezkel 41:16-17 with Rashi and Targum","Melachim I 6:32 with Rashi, Radak and Malbim","Rambam, Beis HaBechirah 1:9","Tikkunei Zohar 21","Mishkenei Elyon 168","Lishchno Tidreshu pp. 222-234"]},{id:"reliefs",category:"house",name:"The keruvim and palms on the walls",he:"\u05DB\u05E8\u05D5\u05D1\u05D9\u05DD \u05D5\u05EA\u05DE\u05D5\u05E8\u05D9\u05DD",confidence:"disputed",summary:"Every wall of the Sanctuary and the Kodesh HaKodashim carries an alternating carving: keruv, palm, keruv, palm, floor to ceiling, on the jambs and the doors and above the entrance. Each keruv shows two faces and only faces - not a body: a young lion's face on the keruv's right, turned to the palm on that side, and a man's face on its left, turned to the palm on that side. The two faces and the alternation are in the navi and Rashi. Which face goes on which side is Mishkenei Elyon, who reads the lion as the right and so as chesed. The six wings the book gives them are his own speculation. None of this has been modelled: the walls in this build carry gold and a palm-only study panel, and the keruvim have never been made. It is the largest recorded gap in the reconstruction.",measurements:[],dispute:[{who:"Yechezkel 41:18-19 with Rashi",holds:"two faces, lion and man, palms between - certain"},{who:"Mishkenei Elyon 168, 190",holds:"the lion is on the right, and the right is chesed"},{who:"The book author",holds:"six wings each - speculation"}],sources:["Yechezkel 41:18-20 with Rashi, Targum, Radak, Metzudas Dovid and Malbim","Chagigah 13b","Sukkah 5b","Mishkenei Elyon 168, 190-191, 203","Lishchno Tidreshu pp. 235-239"]},{id:"atikim",category:"house",name:"The atikim",he:"\u05E2\u05EA\u05D9\u05E7\u05D9\u05DD",confidence:"disputed",summary:"Square reinforcing pillars set into the north and south walls of the Sanctuary and the Kodesh HaKodashim, projecting both inside and out and rising about two-thirds of the wall's height before tapering. That they exist is settled; that there are three to a side is Mishkenei Elyon as the author reads him. On the upper priestly chambers the Tosafos and the Metzudas Dovid read the atikim the other way round, as being below rather than above. None are in this model.",measurements:[{label:"Count",value:"3 per side, north and south, inside and out - Mishkenei Elyon as read by the author",source:"Mishkenei Elyon 169"}],dispute:[{who:"Mishkenei Elyon 169, Tosafos on Yechezkel 42:3",holds:"buttresses above, three a side"},{who:"Tosafos and Metzudas Dovid on the chambers",holds:"the atikim are below, not above"}],sources:["Yechezkel 42:3-6 with Rashi and Tosafos","Metzudas Dovid","Mishkenei Elyon 169, 186-187","Lishchno Tidreshu pp. 223-226, 291"]},{id:"windows",category:"house",name:"The windows of the House",he:"",confidence:"authored",summary:"The navi does not say how many windows the House has or where they are. Every count in this model - twelve in the Kodesh HaKodashim, four each in the Sanctuary's north, south and east walls - is the book author's proposal. What is not authored is that they are always open and carry no glass. There is also a suggestion of a small opening in the west wall six to eight amot up, as the Second Temple had, and that too is the author's.",measurements:[],dispute:[],sources:["Mishkenei Elyon 169","Rashi on Yechezkel 40:16","Zevachim 55b; Gittin 54b with Rashi; Middos 4:5 (the west opening)","Lishchno Tidreshu pp. 63, 224-226"]},{id:"bracing-beams",category:"house",name:"The beams that come through the facade",he:"",confidence:"disputed",summary:"Thick cedar beams run from the Sanctuary wall across to the porch wall and protrude eastward through the front of the House, covered in gold. That they protrude is Rashi and the Radak. That there are ten of them, six amot by two, running up to sixty amot, is the author's. They are not in this model.",measurements:[{label:"Beams",value:"10 beams of 6 x 2 amot up to 60 amot high - authored",source:"the book author, starred"}],dispute:[{who:"Rashi and Radak on Yechezkel 41:25",holds:"the beams protrude east through the facade, gold-covered"},{who:"The book author",holds:"their number and size"}],sources:["Yechezkel 41:25 with Rashi, Radak and Metzudas Dovid","Mishnah Middot 3:8","Rambam, Beis HaBechirah 1:9","Mishkenei Elyon 171, 202","Lishchno Tidreshu pp. 264-267"]},{id:"the-house-overall",category:"house",name:"The House, a hundred amot every way",he:"",confidence:"disputed",summary:"The House measures a hundred amot long, a hundred wide and a hundred high. The length adds up exactly: porch wall 5, porch 11, Sanctuary wall 6, Sanctuary 40, partition 2, Kodesh HaKodashim 20, west wall 6, west chamber 4, chamber foundation 6. The width is the porch's twenty with forty-three of wall on each flank and the two knife chambers. The height of a hundred is certain; the layers the author breaks it into - eighty-five of interior, six of otem, five of ceiling, three of parapet, one of spikes - are his. For contrast the First Temple was a hundred and twenty and the Second a hundred, and the book's reading of why is kabbalistic rather than architectural.",measurements:[{label:"Length",value:"5 + 11 + 6 + 40 + 2 + 20 + 6 + 4 + 6 = 100 amot",source:"Yechezkel 41:13 with Rashi; Middos 3:8, 4:7"},{label:"Height",value:"100 amot",source:"Rashi on Yechezkel 41:8 citing Middos 4:6"},{label:"As built",value:"roof top Z 6130 including the anti-bird points",source:"SourceAssets/architecture-manifest.json"}],dispute:[{who:"Yechezkel 41:13 with Rashi, Middos 4:6-4:7",holds:"100 by 100 by 100 - certain"},{who:"The book author",holds:"the internal breakdown of the hundred amot of height"}],sources:["Yechezkel 41:13-14 with Rashi","Mishnah Middot 3:8, 4:6, 4:7","Chasam Sofer YD 234","Chaggai 2:9","Mishkenei Elyon 150, 170-171","Lishchno Tidreshu pp. 63, 113, 191, 201-219"]},{id:"side-chambers",category:"house",name:"The thirty-three side chambers",he:"\u05E6\u05DC\u05E2\u05D5\u05EA",confidence:"disputed",summary:"Thirty-three chambers in three storeys wrap the House: fifteen north, fifteen south, three west. Their widths grow with height - four, then five, then six amot - because the House wall steps back from six to five to four to three, and the cedar beams rest on the ledges rather than being socketed into the holy wall. Chambers are eleven amot long with five-amah walls; the west ones are twenty-two. The storey heights are the author's.",measurements:[{label:"Chamber widths by storey",value:"4 / 5 / 6 amot",source:"Yechezkel 41:6-7 with Rashi; Middos 4:4"},{label:"Storey height",value:"6 amot plus 5 of ceiling = 11, so 33 in all - authored",source:"the book author, starred"}],dispute:[{who:"Yechezkel 41:5-7 with Rashi, Middos 4:4, Mishkenei Elyon 180-181",holds:"33 chambers, stepped widths, cedar on ledges - certain"},{who:"The book author",holds:"the storey heights"}],sources:["Yechezkel 41:5-7 with Rashi","Melachim I 6:6, 6:10","Mishnah Middot 4:4","Bava Basra 61a","Mishkenei Elyon 180-181, 203","Lishchno Tidreshu pp. 193-200"]},{id:"mesibah-and-water-house",category:"house",name:"The winding stair and the water passage",he:"\u05DE\u05E1\u05D9\u05D1\u05D4 \u05D5\u05D1\u05D9\u05EA \u05D4\u05D5\u05E8\u05D3\u05EA \u05D4\u05DE\u05D9\u05DD",confidence:"disputed",summary:"The seventy-amah block behind the House divides as thirty-two of chamber, four of ledge, five of wall, then five amot of winding stair on the north and five of the water passage on the south, each with a five-amah wall. The winding stair climbs to the chamber roofs and to the roof of the House itself. Mishkenei Elyon's five-and-five split is what is built; Middot gives three and five. The only way into the side chambers is through the corner passages, reached by the small doors in the porch - the northern one always open, the southern one always shut.",measurements:[{label:"West block",value:"70 amot = 32 + 4 + 5 + 5 + 5 either side",source:"Yechezkel 41:9-12 with Rashi; Mishkenei Elyon 181, 204"}],dispute:[{who:"Mishkenei Elyon 181, 204 - built here",holds:"5 and 5"},{who:"Mishnah Middot 4:7",holds:"3 and 5"}],sources:["Yechezkel 41:9-12 with Rashi","Yechezkel 44:1-2","Mishnah Middot 4:5, 4:7","Mishkenei Elyon 181, 204","Lishchno Tidreshu pp. 205-214"]},{id:"menorah",category:"vessels",name:"The Menorah",he:"\u05DE\u05E0\u05D5\u05E8\u05D4",confidence:"certain",summary:"Beaten from a single talent of gold, eighteen tefachim high, standing on the south side of the Sanctuary two and a half amot from the south wall and five from the wall of the Kodesh HaKodashim. Twenty-two cups, eleven knobs and nine flowers ornament it - forty-two in all - and seven lamps burn on it, one of which burns even on Shabbos. Before it stands a stone with three steps for the kohen to reach the lamps.",measurements:[{label:"Height",value:"18 tefachim = 150 cm at this project's amah",source:"Rambam, Beis HaBechirah 3:8-12; Lishchno Tidreshu p. 241"},{label:"Ornaments",value:"22 cups, 11 knobs, 9 flowers",source:"Rambam, Beis HaBechirah 3:1-10"},{label:"Oil per lamp",value:"half a log",source:"Rambam, Temidin uMusafin 3:11"},{label:"As built",value:"at [-5330, 315.176, 925], lamps at Z 1075, width across the outer lamp rims 101.52 cm; step stone X -5284.1..-5194.1, top Z 975",source:"SourceAssets/vessels-review/MenorahV4/native-import-20260908T030534818522Z.json"}],dispute:[],sources:["Shemos 25:31-40, 26:35 with Rashi","Rambam, Beis HaBechirah 3:1-12","Rambam, Temidin uMusafin 3:11","Menachos 98b","Mishkenei Elyon 167, 173","Lishchno Tidreshu pp. 241, 252-254 (Hebrew confirmed on the p. 241 image)"]},{id:"menorah-orientation",category:"vessels",name:"Which way the menorah faces",he:"",confidence:"disputed",summary:"The Rambam has the six branches running north and south; Rashi has them east and west, and the book draws Rashi's arrangement as an alternative in its diagram 22:23a. This model follows the Rambam - and the reason it does is that the imported asset was built that way. That is a consistency decision with the placement spec, not an independent ruling on the question. The six outer lamps face the middle one, and on the Rambam's orientation the middle one faces the Kodesh HaKodashim.",measurements:[],dispute:[{who:"Rambam - depicted here",holds:"branches north-south"},{who:"Rashi",holds:"branches east-west; drawn in the book as diagram 22:23a"}],sources:["Rambam, Beis HaBechirah 3:8 - the six lamps all faced the central lamp, from Bamidbar 8:2","Rambam, Temidin uMusafin 3:13","Bamidbar 8:2","Menachos 98b","Lishchno Tidreshu p. 241 and diagram 22:23a"]},{id:"menorah-height-conflict",category:"vessels",name:"How tall is eighteen tefachim?",he:"",confidence:"disputed",summary:"Eighteen tefachim is a fixed number and an unfixed length. At this project's amah it is 150 cm, and that is what is built. At the Temple Institute's own conversion it is about 1.80 m; at the two tefach values recorded on Wikimikdash, 8 cm and 9.67 cm, it is 144 cm or 174 cm. The Temple Institute's own pages give its physical menorah's mass as 45 kg in one place and 43 kg in another; the audit for this project decided to preserve that discrepancy rather than pick one, and to record the object's true measured height, width and base footprint as unknown.",measurements:[{label:"At 50 cm/amah - built here",value:"150 cm",source:"SourceAssets/vessels-review/MenorahV4/geometry-manifest.json"},{label:"Temple Institute schematic",value:"about 180 cm",source:"Temple Institute illustrated tour, per the project audit"},{label:"At tefach 8 cm / 9.67 cm",value:"144 cm / 174.06 cm",source:"Wikimikdash tefach values, per the project audit"}],dispute:[{who:"This build",holds:"150 cm, following the project amah"},{who:"The Temple Institute's own presentation",holds:"about 180 cm"},{who:"The two Wikimikdash tefach conversions",holds:"144 cm or 174 cm"}],sources:["Rambam, Beis HaBechirah 3:10 (18 tefachim)","Temple Institute reference audit","Wikimikdash article on the tefach"]},{id:"lamp-service",category:"service",name:"The lamp service",he:"\u05D4\u05D8\u05D1\u05EA \u05D4\u05E0\u05E8\u05D5\u05EA",confidence:"disputed",summary:`Every lamp that had gone out had its wick and leftover oil taken away and the lamp cleaned; a new wick and a fresh half-log of oil went in, and it was kindled. The Rambam says that kindling is what the word hatavah means - and the Moznaim note on that passage records that other authorities take hatavah as the cleaning alone. This build depicts the Rambam.

The kohen came in carrying a golden vessel, put the spent wicks and oil into it, kindled five lamps, left the vessel on the second of the three steps and went out; then came back, kindled the remaining two, took the vessel, prostrated himself and left.

Who does it: ordinarily an ordinary kohen, chosen by the lottery of Temidin uMusafin chapter 4. The Kohen Gadol may perform any service he wishes on any day without entering the lottery, and Mishnah Yoma 1:2 names the lamps among the services he performs during his seven days of sequestering - so depicting him doing it is legitimate.`,measurements:[{label:"Oil",value:"half a log per lamp",source:"Rambam, Temidin uMusafin 3:11"}],dispute:[{who:"Rambam, Temidin uMusafin 3:12 - depicted here",holds:"hatavah means the kindling"},{who:"Other authorities, per the Moznaim note there",holds:"hatavah refers only to the cleaning of the lamps"}],sources:["Rambam, Temidin uMusafin 3:11, 3:12, 3:17","Rambam, Beis HaBechirah 3:11 (the stone of three steps)","Rambam, Biat HaMikdash 2:1","Rambam, Klei HaMikdash 5:12","Mishnah Yoma 1:2 (Yoma 14a)","Bartenura on Tamid 3:9"]},{id:"lamp-order-authored",category:"service",name:"The order of the seven lamps is authored",he:"",confidence:"authored",summary:"This one has to be said plainly, because the depiction is convincing and the source is not there. The Rambam says five lamps, then two. He does not say WHICH five and which two, and no passage read for this project does. The sequence in this build walks the seven from north to south, lamps one to five and then six and seven, and that ordering is an authored placeholder chosen because it reads cleanly on screen. It must not be presented to anyone as the order of the service. The agent who built it wrote: 'It is a single edit to change - the two group sizes are already fields.'",measurements:[],dispute:[],sources:["Rambam, Temidin uMusafin 3:17 - five, then two, unnamed"]},{id:"citation-corrections",category:"method",name:"Two citations this project got wrong and fixed",he:"",confidence:"certain",summary:`Both corrections were found and recorded by the agent that built the Kohen Gadol's service, and they are carried here so they are not quietly re-broken.

First: the ruling that the Kohen Gadol may perform any service he wishes without entering the lottery is Rambam, Klei HaMikdash 5:12, not 5:11. 5:11 is a different halachah - it describes him entering the Sanctuary to prostrate, supported by three attendants, one holding the jewels of the choshen so it does not shift from the ephod. That halachah is independently useful: it is direct evidence that he walks into the Sanctuary in the golden garments.

Second: that the lamps face the centre is Rambam, Beis HaBechirah 3:8, not 3:12. Beis HaBechirah 3:12 is the Shulchan. Temidin uMusafin 3:12 is the definition of hatavah - both 3:12s are real and each is cited for what it actually says.`,measurements:[],dispute:[],sources:["Rambam, Klei HaMikdash 5:11 and 5:12","Rambam, Beis HaBechirah 3:8 and 3:12","Rambam, Temidin uMusafin 3:12"]},{id:"service-pacing-authored",category:"service",name:"Every timing in the service is invented",he:"",confidence:"authored",summary:"Fourteen seconds a lamp, eight in the porch, four at the doorway, six on the stone, five for the vessel, twenty waiting outside, thirty at the golden altar, ninety centimetres a second walking, ninety seconds between one sequence and the next. Nothing in any source fixes any of them. They are pacing choices, and the whole loop runs 290.5 seconds because those numbers were picked, not because the service took that long.",measurements:[{label:"Loop length",value:"290.5 s ordinary day, 346.7 s in the Yom Kippur variant",source:"SourceAssets/runtime-review/kohen-service/sources.md - SVC-D-PACING"}],dispute:[],sources:[]},{id:"shulchan",category:"vessels",name:"The Shulchan",he:"\u05E9\u05D5\u05DC\u05D7\u05DF",confidence:"disputed",summary:`Wood overlaid with gold, two amot long east to west - its length running along the length of the House - one wide, and three high. It stands on the north side of the Sanctuary, opposite the menorah, two and a half amot from the north wall and five from the wall of the Kodesh HaKodashim. Bread is on it always.

Three amot is the number to notice. The Torah's table is a cubit and a half; Yechezkel's is three. The book takes the three at face value and this model builds it that way, and the book also records the alternative reading that the three amot are measured with the bread stacked on it.`,measurements:[{label:"Length x width x height",value:"2 x 1 x 3 amot = 100 x 50 x 150 cm",source:"Yechezkel 41:22 with Rashi and Targum; Shemos 25:23"},{label:"Torah's table, for contrast",value:"1.5 amot high",source:"Shemos 25:23"},{label:"As built",value:"at [-5300, -350, 925], misgeret 8.3333 cm, upright plates 41.667 cm wide reaching Z 250 above the floor",source:"SourceAssets/vessels-review/KeilimTIV1/native-import-20260908T031336905985Z.json"}],dispute:[{who:"The book's main line, built here",holds:"three amot is the table's own height"},{who:"The alternative the book records at p. 246",holds:"the three amot include the bread"}],sources:["Yechezkel 41:22 with Rashi and Targum","Shemos 25:23, 26:35 with Rashi","Yoma 33b","Menachos 98b-99a","Baraisa d'Meleches HaMishkan","Rambam, Beis HaBechirah 3:12","Mishkenei Elyon 167, 203","Lishchno Tidreshu pp. 241-251"]},{id:"lechem-hapanim",category:"vessels",name:"The showbread",he:"\u05DC\u05D7\u05DD \u05D4\u05E4\u05E0\u05D9\u05DD",confidence:"certain",summary:"Twelve folded loaves in two stacks of six, each a tefach thick and folded to six tefachim by five. Twenty-eight golden half-tubes hold them apart, three under each loaf and two on the top one of each stack, carried on four golden uprights that rise five amot from the floor. Two golden bowls of frankincense stand between the stacks. Before Shabbos the new loaves wait in the porch on a marble table on the north side, and the old ones go to a golden table on the south.",measurements:[{label:"Loaf",value:"1 tefach thick, folded to 6 x 5 tefachim",source:"Menachos 94-99"},{label:"Rods and uprights",value:"28 rods, 4 uprights 5 tefachim wide reaching 5 amot",source:"Rambam, Beis HaBechirah 3:12-16"},{label:"As built",value:"12 loaves, 28 rods, 2 bowls; uprights to Z 250 above the floor",source:"SourceAssets/vessels-review/KeilimTIV1/geometry-manifest.json"}],dispute:[],sources:["Menachos 94-99","Rambam, Beis HaBechirah 3:12-16","Rambam, Temidin uMusafin 5","Rashi on Shemos 25:29","Lishchno Tidreshu p. 250"]},{id:"golden-altar",category:"vessels",name:"The golden altar",he:"\u05DE\u05D6\u05D1\u05D7 \u05D4\u05D6\u05D4\u05D1",confidence:"certain",summary:`Acacia overlaid with gold, one amah square and two amot high, with four horns. It stands on the centre line of the Sanctuary opposite the Aron, between the menorah and the table and drawn a little east of them; all three vessels are in the western half of the forty-amah Sanctuary. Incense is offered on it morning and afternoon.

It is the one object in this model built at a different amah. Eruvin 4a reads its cubit as a five-tefach cubit, so its 1 x 1 x 2 amot come out at 41.7 by 41.7 by 83.3 cm rather than 50 by 50 by 100.`,measurements:[{label:"Square and height",value:"1 x 1 x 2 amot at the 5-tefach amah = 41.67 x 41.67 x 83.33 cm",source:"Shemos 30:1-2; Eruvin 4a on Yechezkel 43:13"},{label:"As built",value:"at [-4650, 0, 925]; roof plane 79.167; horns 4.1667 square; ring axis Z +70.833; poles 100 cm",source:"SourceAssets/vessels-review/IncenseAltarV2/geometry-manifest.json"}],dispute:[],sources:["Shemos 30:1-10","Eruvin 4a on Yechezkel 43:13","Rashi on Shemos 26:35","Yoma 33b","Menachos 98b","Rambam, Beis HaBechirah 3:17","Mishkenei Elyon 167, 193","Lishchno Tidreshu pp. 241, 255-258"]},{id:"ketores",category:"service",name:"The incense",he:"\u05E7\u05D8\u05D5\u05E8\u05EA",confidence:"disputed",summary:`Incense is offered on the golden altar morning and afternoon. The morning offering falls between the blood service of the daily offering and the bringing up of its limbs; the afternoon one between the limbs and the libations - these are relative positions in the service, not clock times. While the incense burns everyone withdraws from the Sanctuary and from the space between the porch and the outer altar, until the kohen who offered it comes out.

Where in the lamp sequence it falls is not settled. Abaye's order of service puts it after the second group of lamps; the Rambam's own note at Temidin uMusafin 3:17 sets the re-entry after the limbs were brought up. This build follows Abaye, and the passage in Yoma 33a was not independently verified in the pass that recorded it. Treat the relative position as unsettled.

Nothing about the incense is modelled: no particles, no emitter, no smoke.`,measurements:[],dispute:[{who:"Abaye, Yoma 33a - followed here, and not independently verified in the pass that recorded it",holds:"five lamps, the blood of the daily offering, two lamps, then the incense"},{who:"Rambam's note at Temidin uMusafin 3:17",holds:"the re-entry comes after the limbs were brought up"}],sources:["Shemos 30:7-8","Rambam, Temidin uMusafin 3:1, 3:3, 3:9","Mishnah Yoma 3:5","Mishnah Tamid 6:3","Yoma 33a","Vayikra 16:12-13","Rambam, Avodat Yom HaKippurim 4:1, 4:2"]},{id:"maaleh-ashan",category:"service",name:"The smoke, and what nobody knows about it",he:"\u05DE\u05E2\u05DC\u05D4 \u05E2\u05E9\u05DF",confidence:"authored",summary:`Yoma 53a describes the smoke rising like a staff to the ceiling and then spreading down the walls until the chamber is full, and distinguishes putting the incense on the fire inside from carrying a cloud in ready-made. Yoma 38a records the Avtinas family's column against the Alexandrians' dispersing smoke, and a descendant who could recognise the herb and would not name it.

What none of that establishes is a plant. The research for this project states flatly that no secure botanical identification of maaleh ashan has been made, and that no modern species, chemical mechanism or recovered sample may be labelled as the authentic ingredient. Colour, opacity, rise speed, thickness, particle size, smell and how long it lingers are all artistic choices.`,measurements:[],dispute:[],sources:["Yoma 53a:4-5, 11, 15-16","Yoma 38a:10, 14"]},{id:"incense-compounding-authored",category:"service",name:"Where the incense is compounded",he:"",confidence:"authored",summary:"The incense must be compounded within the holy precinct. Where exactly is not stated, and the book places it in the west recess of the southern wall vestibule, on the second and third floors. That is his suggestion, starred, and not a source.",measurements:[],dispute:[],sources:["Kerisos 6a","Rambam, Klei HaMikdash 2:6","Yerushalmi Yoma 1:5","Lishchno Tidreshu p. 327 - the author's suggestion"]},{id:"paroches",category:"house",name:"The paroches",he:"\u05E4\u05E8\u05D5\u05DB\u05EA",confidence:"disputed",summary:`Under the reconstruction chosen from Mishkenei Elyon and the supplied book, a curtain covers the Kodesh HaKodashim doorway, seven amot wide by six high. Yechezkel describes the partition and opening but does not explicitly specify this curtain. The earlier four textile materials are blue wool, purple wool, scarlet wool and linen; their names do not establish an exact RGB palette or a unique pattern.

The replacement textile is still being designed, drawing on the book illustration and the user-selected architectural motif. Its blue ground, border, colors, figure anatomy and motif arrangement are artistic choices, not a recovered historical textile or a definitive prophetic design. A separate optional blood-mask concept is an authored service-state interpretation; it has not been adopted into this scene. Historical sprinkling toward the curtain did not require contact; no source establishes these exact marks.

The selected 48 cm amah gives a 336 x 288 cm doorway. The working scene still uses the legacy 50 cm architecture until the coordinated conversion is complete. Existing cloth includes an authored edge overlap that still needs dimensional review. The service code defines an ordinary-day boundary at the legacy X -5600, but its service actor has not yet been integrated into this working map.`,measurements:[{label:"Paroches",value:"7 x 6 amot: selected 48 cm = 336 x 288 cm; legacy 50 cm opening = 350 x 300 cm",source:"Mishkenei Elyon 159-160, 166"},{label:"As built",value:"at [-5585, 0, 928]; the boundary line is X -5600",source:"SourceAssets/sanctuary-detail/DoorsParochesV1/native-import-20260907T184828Z.json"}],dispute:[{who:"Yechezkel 41:3",holds:"the partition, the 7 x 6 opening and the doors - certain"},{who:"Mishkenei Elyon 159-160, 166",holds:"there is also a curtain, exactly the size of the gateway - not in the navi"},{who:"The book author",holds:"the doors open inward - starred"}],sources:["Yechezkel 41:3, 41:21, 41:23 with Rashi","Yoma 54a","Shemos 26:31-33","Menachos 98a-b","Rambam, Beis HaBechirah 4:2","Yoma 51b","Mishnah Middot 4:7","Mishkenei Elyon 159-166, 203","Lishchno Tidreshu pp. 184-186, 261","Tosefta Shekalim 3:11 (Mechon Mamre numbering)","Yoma 57a","Lishchno Tidreshu illustration 19b, printed p.133 (reference export page238); illustrated interpretation"]},{id:"kodesh-hakodashim",category:"house",name:"The Kodesh HaKodashim",he:"\u05E7\u05D3\u05E9 \u05D4\u05E7\u05D3\u05E9\u05D9\u05DD",confidence:"certain",summary:"Twenty amot square, behind a partition two amot thick - an amah in the First Temple, no wall at all in the Second. Its entrance is seven amot wide and six high in a square four-post frame, with two doors of three and a half by six amot, cedar carved with keruvim and palms and overlaid with gold, standing permanently open. There is no upper storey above it.",measurements:[{label:"Chamber",value:"20 x 20 amot = 1000 x 1000 cm",source:"Yechezkel 41:4"},{label:"Partition",value:"2 amot = 100 cm",source:"Yechezkel 41:3"},{label:"Entrance",value:"7 amot wide x 6 high = 350 x 300 cm",source:"Yechezkel 41:3"},{label:"As built",value:"floor X -6700..-5700, Y +/-500, top Z 925; partition X -5700..-5600; lintel Z 1225..2925",source:"SourceAssets/architecture-manifest.json SM_0142..SM_0147"}],dispute:[],sources:["Yechezkel 41:3-4, 41:23 with Rashi","Rambam, Beis HaBechirah 4:1","Yoma 53b","Mishnah Middot 4:1-2","Mishnah Tamid 3:7","Mishkenei Elyon 150, 167, 170","Lishchno Tidreshu pp. 184-192, 259"]},{id:"aron",category:"vessels",name:"The Aron",he:"\u05D0\u05E8\u05D5\u05DF",confidence:"disputed",summary:`A wooden box two and a half amot by one and a half by one and a half, with an inner gold box a tefach smaller and an outer a tefach larger, a gold crown around it, four rings at the top corners and gold-covered poles permanently in them. Inside it the Luchos, the broken Luchos and a Sefer Torah. On it the kaporet, a gold slab a tefach thick - and that thickness is a rabbinic derivation, not a measurement in the verse. Beside it Aharon's staff, the jar of manna and the flask of anointing oil.

All of that was missing from the Second Temple, along with the fire, the Shechinah and the Urim v'Tumim. Where the Aron stands is disputed: the Rambam puts it on a stone in the western part of the chamber, the Tosafos Yom Tov and the Tanchuma in the middle. And Yirmiyahu 3:16-17, with Rashi, speaks of an era when it is not spoken of again - a passage that must be acknowledged, and which should not be flattened either into a prohibition on depicting it or out of existence.

In this build there is an Aron study at [-6200, 0, 925] in sixteen parts. The project's own audit found no finished Aron mesh in the architecture manifests and recorded the Kodesh floor package as a source-derived chamber envelope, not an established Aron location.`,measurements:[{label:"Box",value:"2.5 x 1.5 x 1.5 amot = 125 x 75 x 75 cm",source:"Shemos 25:10-22"},{label:"Kaporet",value:"1 tefach thick - a rabbinic derivation, not stated in the verse",source:"Sukkah 5a"},{label:"As built",value:"study at [-6200, 0, 925], 16 parts sharing one origin; kaporet 125 x 75 x 8.3333; poles 250 cm",source:"SourceAssets/vessels-review/aron-study-v1-spec.json"}],dispute:[{who:"Rambam, Beis HaBechirah 4:1",holds:"on a stone in the western part of the chamber"},{who:"Tosafos Yom Tov on Yoma 5:2; Tanchuma Kedoshim 10",holds:"in the centre"}],sources:["Shemos 25:10-22 with Rashi","Bava Basra 14a-b","Sukkah 5a-5b","Yoma 21b, 53b","Rambam, Beis HaBechirah 4:1","Yirmiyahu 3:16-17 with Rashi","Mishkenei Elyon 150, 167","Lishchno Tidreshu pp. 187-192"]},{id:"keruvim-on-the-kaporet",category:"vessels",name:"The keruvim on the kaporet",he:"\u05DB\u05E8\u05D5\u05D1\u05D9\u05DD",confidence:"disputed",summary:`Two figures beaten out of the same slab as the cover, wings spread above it, faces toward each other and inclined down toward the cover, with the faces of children. Their bodies are ten tefachim high - about 83 cm at this project's amah, and the derivation of the ten tefachim is in Sukkah 5b, which in the same discussion sets out the five-tefach and six-tefach cubit systems and warns against mixing their arithmetic.

The book adds that each has six wings. The research for this project records that as the book's own statement with no source given, and it is reported here on that footing and no other.

Do not confuse three different sets of keruvim: the two on the cover, Shlomo's ten-amah figures in Melachim I 6:23-28, and the carved figures on Yechezkel's walls. The ten amot belong to Shlomo's and to nothing else.`,measurements:[{label:"Body height",value:"10 tefachim = about 83.33 cm at this project's amah",source:"Sukkah 5b"},{label:"Six wings",value:"the book's statement, no source given",source:"Lishchno Tidreshu p. 190, as recorded in the project research"}],dispute:[{who:"Shemos 25:18-20 and Sukkah 5b",holds:"two figures, faces to each other and down, ten tefachim - certain"},{who:"The book",holds:"six wings each - no source given"}],sources:["Shemos 25:18-22","Sukkah 5a-5b","Bava Basra 99a","Melachim I 6:23-28 (Shlomo's, a different thing)","Lishchno Tidreshu p. 190"]},{id:"keruvim-anatomy",category:"vessels",name:"What a keruv looks like",he:"",confidence:"disputed",summary:"Two reconstructions are named in the project's modelling brief: birdlike bodies with youthful faces, attributed to the Rashbam, and a human-like head and shoulders on a birdlike lower body with wings, attributed to R' Avraham ben HaRambam, who leaves the legs unspecified. The brief is explicit that both attributions come through a Temple Institute Hebrew article and were not read in the originals for this project. The face is not less than a tefach.",measurements:[{label:"Face",value:"not less than a tefach",source:"Sukkah 5b"}],dispute:[{who:"Rashbam, as reported second-hand",holds:"birdlike bodies with youthful faces"},{who:"R' Avraham ben HaRambam, as reported second-hand",holds:"human head and shoulders, birdlike lower body and wings; legs unspecified"}],sources:["Sukkah 5b","Rashbam and R' Avraham ben HaRambam, reported via a Temple Institute Hebrew article and NOT read in the original for this project"]},{id:"even-hashtiya",category:"house",name:"The Even HaShtiya",he:"\u05D0\u05D1\u05DF \u05D4\u05E9\u05EA\u05D9\u05D4",confidence:"disputed",summary:"A stone standing three fingerbreadths - about six centimetres - above the floor of the chamber. Where it is is genuinely unresolved. The Rambam puts it in the west of the Kodesh HaKodashim; the Tosafos Yom Tov and the Tanchuma put it in the centre, the Tanchuma describing it as visible 'before the Aron', which reads as protruding eastward; Mishkenei Elyon says it is 'in the place of' the chamber. The book reconciles them by letting the stone spread about twelve amot square from the centre, and marks that reconciliation as study only. It is not in this model.",measurements:[{label:"Height above the floor",value:"3 fingerbreadths, about 6 cm",source:"Rambam, Beis HaBechirah 4:1"}],dispute:[{who:"Rambam, Beis HaBechirah 4:1",holds:"in the west of the chamber"},{who:"Tosafos Yom Tov on Yoma 5:2; Tanchuma Kedoshim 10",holds:"in the centre, visible before the Aron"},{who:"Mishkenei Elyon 150, 167",holds:"in the place of the chamber"},{who:"The book author, study only",holds:"a slab about 12 x 12 amot spreading from the centre, reconciling them"}],sources:["Rambam, Beis HaBechirah 4:1","Yoma 53b","Tosafos Yom Tov on Yoma 5:2","Tanchuma Kedoshim 10","Zohar Noach 70a-b","Mishkenei Elyon 150, 167","Lishchno Tidreshu pp. 187-189, 306"]},{id:"who-may-enter",category:"people",name:"Who goes how far in",he:"",confidence:"certain",summary:`An ordinary kohen may enter the Sanctuary every day, for service. The Kohen Gadol enters the Kodesh HaKodashim once a year, on Yom Kippur, and nobody else ever does. All kohanim are warned not to be in the Sanctuary or the chamber beyond it when they are not in the middle of a service; this model's depicted service has no idle wandering for that reason.

One caution: the Rambam extends the verse's 'within the curtain' to the whole House, and the Kessef Mishneh questions that reading. Where the tour walks past those lines it says so.`,measurements:[],dispute:[{who:"Rambam, Biat HaMikdash 2:2",holds:"'within the curtain' extends to the whole House"},{who:"Kessef Mishneh",holds:"questions that extension"}],sources:["Vayikra 16:2","Rambam, Biat HaMikdash 2:1, 2:2","Rambam, Klei HaMikdash 5:11, 5:12","Mishnah Yoma 1:2 (Yoma 14a)","Keilim 1:8-9"]},{id:"three-camps",category:"people",name:"The three camps",he:"\u05E9\u05DC\u05E9 \u05DE\u05D7\u05E0\u05D5\u05EA",confidence:"certain",summary:"The camp of Israel is the whole city up to the Mount, including where the kohanim and Levites live around it. The camp of the Levites runs from the Mount's gate to the vestibules of the three inner gates - the outer court, the eleven amot behind the House, the lower chambers. The camp of the Shechinah begins at those vestibules and goes inward. A non-Jew and anyone bearing corpse impurity stop at the cheil; someone who has immersed but whose day has not ended stops at the outer court.",measurements:[],dispute:[],sources:["Rambam, Beis HaBechirah 7:11-22","Keilim 1:6-9","Chagigah 26a","Lishchno Tidreshu p. 356"]},{id:"immersion-and-purity",category:"people",name:"Immersion, and three things it is not",he:"",confidence:"certain",summary:`Three separate ideas get run together and the sources keep them apart.

Corpse impurity is not cured by a bath at all: it needs the purification water and the third and seventh days and then immersion and the ending of the day. A bath is not a universal reset.

Exclusion is graded by zone. The Rambam distinguishes what bars a person from the Mount, from the cheil, from the Women's Court and from the Israelite Court, and corpse impurity, someone who has immersed but whose day has not ended, and someone still owing an offering are not interchangeable.

Immersion before service is its own requirement, described in Yoma for someone already pure. It must never be implemented as clearing an existing state of corpse impurity. Sanctifying hands and feet at the laver is a further and separate prerequisite that no immersion replaces.

No mikveh has been built in this model and the research gives no Third Temple location for one; where the book places mikvaot in the lower chambers, that placement is his own.`,measurements:[],dispute:[],sources:["Bamidbar 19:11-12, 19","Rambam, Biat HaMikdash 3:3-7, 3:14","Rambam, Biat HaMikdash 5:1-2","Mishnah Yoma 3:3, 3:4","Lishchno Tidreshu p. 324 (the mikvaot placements - the author's)"]},{id:"garments",category:"people",name:"The priestly garments",he:"\u05D1\u05D2\u05D3\u05D9 \u05DB\u05D4\u05D5\u05E0\u05D4",confidence:"disputed",summary:`An ordinary kohen wears four garments: tunic, breeches, head covering and sash. The Kohen Gadol wears eight, and his Yom Kippur linen set - tunic, breeches, turban and sash - is a service-specific outfit for part of that day, not a replacement for everything he wears through it.

Several points are open and must not be quietly decided. Whether the Kohen Gadol's sash is the same as an ordinary kohen's is disputed between the Rambam and others. The pomegranates on the hem of the robe are drawn both open-mouthed and closed. The Temple Institute holds two reconstructions of the ephod, one after the Rambam and one after Rashi, and they differ in how it sits. The modern identification of several of the breastplate stones is not settled. Even whether the words on the head plate run on one line or two is disputed.

There is no Kohen Gadol garment asset in this project at all. The figure in the service sequence wears a pilgrim material and says so.`,measurements:[],dispute:[{who:"Rambam and others",holds:"differ on whether the Kohen Gadol's sash is the ordinary kohen's"},{who:"Reconstructions of the ephod",holds:"differ after the Rambam and after Rashi"},{who:"The pomegranates and the head plate",holds:"open or closed mouths; one line of engraving or two"}],sources:["Rambam, Klei HaMikdash ch. 9","Rambam, Klei HaMikdash 8:1-3, 8:11","Yechezkel 44:17-19 (needs a documented reconciliation with the wool question)","Shemos 28"]},{id:"eating-kodshei-kodashim",category:"people",name:"Where the kohanim ate",he:"",confidence:"disputed",summary:"The most holy offerings are eaten in the upper chambers, which carry inner-court sanctity, and eaten in the four service garments. The garments are then left there and ordinary clothes put on before going out to the people. Nobody sits in the court except the kings of the house of David. That they ate standing at high tables, and that the Kohen Gadol alone sits to eat in the southern chamber, is the author's, and he himself records it as doubtful. The Metzudas Dovid includes all four chamber blocks rather than only the upper ones.",measurements:[],dispute:[{who:"Yechezkel 42:13 with Rashi, Mishkenei Elyon",holds:"the upper chambers"},{who:"Metzudas Dovid",holds:"all four blocks"},{who:"The book author",holds:"standing, at high tables - recorded by him as a doubt"}],sources:["Yechezkel 42:13-14, 44:3 with Rashi","Chagigah 2:7","Yoma 68b-69b","Zevachim 15b-16a, 23b, 56a","Rambam, Klei HaMikdash 10:4-5; Biat HaMikdash 5:16-17; Beis HaBechirah 6:8","Mishkenei Elyon 182, 186-187, 198","Lishchno Tidreshu pp. 345-358"]},{id:"upper-chambers",category:"courts",name:"The upper priestly chambers",he:"\u05DC\u05E9\u05DB\u05D5\u05EA \u05D4\u05E2\u05DC\u05D9\u05D5\u05E0\u05D5\u05EA",confidence:"disputed",summary:"Two blocks a hundred amot by fifty at the north-west and south-west, three storeys, standing twenty amot clear of the House's side building, their floors at the level of the inner court, doors on the north and into the twenty-amah strip. Fifty amot of open court lie north of them and their east wall is a fifty-amah fence. The layout is certain; every height and storey number in the book is his own example. In this model the block is 98 by 46 at Z 405 - below the court level - about 24 amot high and without the pillars. A recorded gap.",measurements:[{label:"Each block",value:"100 x 50 amot, 3 storeys",source:"Yechezkel 42:1-2 with Rashi"},{label:"As built",value:"98 x 46 amot at Z 405, about 24 high, no atikim",source:"SourceAssets/research/book-scene-requirements-20260907.md section 7"}],dispute:[{who:"Yechezkel 42:1-8 with Rashi, Mishkenei Elyon 186-187, 198",holds:"the layout"},{who:"The book author",holds:"50 amot high, storeys about 10, pillars about 7 thick - 'for example'"}],sources:["Yechezkel 42:1-8 with Rashi","Menachos 96a","Mishkenei Elyon 186-187, 198","Lishchno Tidreshu pp. 272-299"]},{id:"lower-chambers",category:"courts",name:"The lower chambers",he:"\u05DC\u05E9\u05DB\u05D5\u05EA \u05D4\u05EA\u05D7\u05EA\u05D5\u05E0\u05D5\u05EA",confidence:"disputed",summary:"Two blocks a hundred amot by fifty at the north-east and south-east, three storeys, at the level of the outer court, running east from the ends of the gate cells and leaving eleven amot to the east wall, with doors north and south and doors into the Court of Israel. That is the size and position. What they are FOR is not stated anywhere, and the book fills them - Sanhedrin, the lots, the fire chamber, mikvaot, the Kohen Gadol's chamber, the seals, the wood, the metzoraim, the nazirites, the oil and wine, seating for the pilgrims - and marks the filling as his own throughout. None of these blocks are in this model.",measurements:[{label:"Each block",value:"100 x 50 amot, 3 storeys, 11 amot clear of the east wall",source:"Yechezkel 42:9-12 with Rashi; the 11 amot from Tzuras HaBayis as adopted"},{label:"Height",value:"45 amot - the author's, for illustration only",source:"the book author"}],dispute:[{who:"Yechezkel 42:9-12 with Rashi, Mishkenei Elyon 187, 197",holds:"existence, size and position - certain"},{who:"The book author",holds:"everything they are used for"}],sources:["Yechezkel 42:9-12 with Rashi","Tzuras HaBayis","Metzudas Dovid","Mishkenei Elyon 184-187, 197","Lishchno Tidreshu pp. 300-337"]},{id:"lishkas-hagazis",category:"courts",name:"Where the Sanhedrin sits",he:"\u05DC\u05E9\u05DB\u05EA \u05D4\u05D2\u05D6\u05D9\u05EA",confidence:"authored",summary:"This is authored, and it should be labelled that way wherever it appears. The book puts the Great Sanhedrin of seventy-one on the third floor of the northern lower chambers at the east end, with a door out to the unconsecrated side, and the lots half in the holy area with a door into the inner court; the two courts of twenty-three at the Mount's east gate by the cheil and on the second floor of the southern lower chambers. The judges sit in a semicircle. The sources cited are about the institution, not about this building's plan.",measurements:[],dispute:[],sources:["Sanhedrin 86b","Yoma 25a","Rambam, Sanhedrin 1:3","Mishnah Middot 5:4","Lishchno Tidreshu p. 316 - the author's suggestion"]},{id:"priestly-kitchen",category:"courts",name:"The priestly kitchen and the one-amah way in",he:"",confidence:"certain",summary:"The twenty-amah strip is inner court, and its western end on the north side is the kitchen where the sin offerings, guilt offerings and meal offerings were cooked. It is entered from the outer court by a sloping opening one amah wide at the end of the court wall, leading into a passage five amot by ten. The book also proposes a second opening from the inner court, and that one is his.",measurements:[{label:"Entry",value:"a 1-amah sloped opening into a 5 x 10 amot passage",source:"Yechezkel 42:4 with Rashi per R' Shemayah; Mishkenei Elyon 198"}],dispute:[],sources:["Yechezkel 42:3-4, 46:19-20 with Rashi","Menachos 96a","Sukkah 7b","Rambam, Maaseh HaKorbanos 11:21-22","Mishkenei Elyon 187, 198","Lishchno Tidreshu pp. 276-290"]},{id:"water-from-the-house",category:"precinct",name:"The water that comes out from under the threshold",he:"",confidence:"certain",summary:"Yechezkel 47:1-2 has water coming out from under the threshold of the House eastward and passing out by the southern gate. The book takes the southern inner gate as its way out, and that is the source point this scene would use. It is not modelled.",measurements:[],dispute:[],sources:["Yechezkel 47:1-2","Lishchno Tidreshu p. 340"]},{id:"method-and-limits",category:"method",name:"How to read this codex",he:"",confidence:"authored",summary:`Three things are worth knowing before trusting any entry here.

First, the labels mean what they say. 'Certain' means the sources read for this project agree; it does not mean the matter is beyond argument, only that no cited authority in this pile disputes it. 'Disputed' names the disagreement. 'Authored' means the project made it up, and every 'authored' label in this file is a place where the model is more confident-looking than the evidence.

Second, a source about the Mishkan or the first two Temples is evidence for the institution, not automatic proof of a detail of the future House. The book itself works in three layers and only its Ketz HaYamin layer is a claim about this building.

Third, 'unknown' is a result. It is not the same as 'permitted', and it is not an invitation to fill the gap. Things this project looked for and did not find are recorded as not found - the altar's own dimensions, the kiyor's size, any Women's Court, the order of the seven lamps, the identity of the smoke-raising herb, and a rabbinic approval of any of it.`,measurements:[],dispute:[],sources:[]}]};var xl=new URLSearchParams(location.search),wm=document.getElementById("view"),f_=document.getElementById("fade"),yn=qu.stops,Mm="mikdash-walk-v1",p_={time:"morning",quality:"auto",sensitivity:1,invertY:!1,showTour:!0,reduceMotion:window.matchMedia("(prefers-reduced-motion: reduce)").matches},Xa={};try{Xa=JSON.parse(localStorage.getItem(Mm)||"{}")||{}}catch{Xa={}}var hn={...p_,...Xa.prefs},As=new Set(Array.isArray(Xa.seen)?Xa.seen.filter(s=>s>=0&&s<yn.length):[]);function Zu(){try{localStorage.setItem(Mm,JSON.stringify({prefs:hn,seen:[...As]}))}catch{}}var Ju=window.matchMedia("(pointer: coarse)").matches;function m_(){let s=xl.get("q")||hn.quality;if(s==="low"||s==="medium"||s==="high")return s;let e=navigator.deviceMemory||4,t=navigator.hardwareConcurrency||4;return Ju?e<=3||t<=4?"low":"medium":t>=8&&e>=8?"high":"medium"}var qa=m_(),Cn;try{Cn=new zc({canvas:wm,antialias:qa!=="low",powerPreference:"high-performance",stencil:!1})}catch(s){document.getElementById("loadbar").hidden=!0;let e=document.getElementById("loadnote");throw e.textContent="This browser could not start 3D graphics (WebGL). Try a current Chrome, Safari, Edge or Firefox.",e.style.color="#f0b9a0",s}var g_={low:1,medium:1.5,high:2}[qa],Sm=Math.min(window.devicePixelRatio||1,g_),Ts=1;Cn.setPixelRatio(Sm);Cn.outputColorSpace=kt;Cn.toneMapping=Jo;Cn.shadowMap.enabled=!0;Cn.shadowMap.type=qa==="low"?Ma:Vo;var bn=new Ut(70,1,.1,14e3);function $u(){let s=window.innerWidth,e=window.innerHeight;Cn.setSize(s,e,!1),bn.aspect=s/e,bn.fov=s<e?82:68,bn.updateProjectionMatrix()}window.addEventListener("resize",$u);window.addEventListener("orientationchange",()=>setTimeout($u,200));$u();var Ot={mount:["The Mount","\u05D4\u05E8 \u05D4\u05D1\u05D9\u05EA"],outerGateE:["East gate, outer court","\u05E9\u05E2\u05E8 \u05D4\u05DE\u05D6\u05E8\u05D7 \u05D4\u05D7\u05D9\u05E6\u05D5\u05DF"],outerGateN:["North gate, outer court","\u05E9\u05E2\u05E8 \u05D4\u05E6\u05E4\u05D5\u05DF \u05D4\u05D7\u05D9\u05E6\u05D5\u05DF"],outerGateS:["South gate, outer court","\u05E9\u05E2\u05E8 \u05D4\u05D3\u05E8\u05D5\u05DD \u05D4\u05D7\u05D9\u05E6\u05D5\u05DF"],outer:["The outer court","\u05D4\u05E2\u05D6\u05E8\u05D4 \u05D4\u05D7\u05D9\u05E6\u05D5\u05E0\u05D4"],innerGateE:["East gate, inner court","\u05E9\u05E2\u05E8 \u05D4\u05DE\u05D6\u05E8\u05D7 \u05D4\u05E4\u05E0\u05D9\u05DE\u05D9"],innerGateN:["North gate, inner court","\u05E9\u05E2\u05E8 \u05D4\u05E6\u05E4\u05D5\u05DF \u05D4\u05E4\u05E0\u05D9\u05DE\u05D9"],innerGateS:["South gate, inner court","\u05E9\u05E2\u05E8 \u05D4\u05D3\u05E8\u05D5\u05DD \u05D4\u05E4\u05E0\u05D9\u05DE\u05D9"],yisroel:["The Court of Israel","\u05E2\u05D6\u05E8\u05EA \u05D9\u05E9\u05E8\u05D0\u05DC"],kohanim:["The Court of the Kohanim","\u05E2\u05D6\u05E8\u05EA \u05DB\u05D4\u05E0\u05D9\u05DD"],altar:["At the altar","\u05D4\u05DE\u05D6\u05D1\u05D7"],steps:["The twelve steps","\u05E9\u05EA\u05D9\u05DD \u05E2\u05E9\u05E8\u05D4 \u05DE\u05E2\u05DC\u05D5\u05EA"],ulam:["The Ulam","\u05D0\u05D5\u05DC\u05DD"],heikhal:["The Heikhal","\u05D4\u05D9\u05DB\u05DC"],kodesh:["Kodesh HaKodashim","\u05E7\u05D3\u05E9 \u05D4\u05E7\u05D3\u05E9\u05D9\u05DD"],house:["Beside the House","\u05D4\u05D1\u05D9\u05EA"],above:["Above the Mikdash",""]};function Tm(s,e){let{x:t,y:n,z:i}=s,r=Math.abs(t),a=Math.abs(i);if(e&&n>38)return Ot.above;if(r>81.5||a>81.5)return t>78&&t<93&&a<13?Ot.outerGateE:i<-78&&i>-96&&r<13?Ot.outerGateN:i>78&&i<96&&r<13?Ot.outerGateS:Ot.mount;if(t>55&&a<13)return Ot.outerGateE;if(i<-55&&r<13)return Ot.outerGateN;if(i>55&&r<13)return Ot.outerGateS;if(a<=5.2&&n>8.5){if(t>=-67.5&&t<-56.5)return Ot.kodesh;if(t>=-56.5&&t<-36)return Ot.heikhal}return t>=-36&&t<-25&&a<12.5&&n>8.5?Ot.ulam:t>=-25&&t<-14&&a<8?Ot.steps:r<=25&&a<=25?r<9.5&&a<9.5||r<4.5&&i>0&&i<23.5?Ot.altar:t>11.5?Ot.yisroel:Ot.kohanim:t>25&&t<51&&a<13?Ot.innerGateE:i<-25&&i>-51&&r<13?Ot.innerGateN:i>25&&i<51&&r<13?Ot.innerGateS:t<-25&&t>-76&&a<26?Ot.house:Ot.outer}var un,st,Xt,nt,Cs=!1,Rn=null,xn=0,Ya=-1,Qu=!1,Em=s=>s===0?8:4,b_={get:()=>({...hn,quality:hn.quality}),set(s,e){hn[s]=e,Zu(),s==="time"?un.setTime(e):s==="quality"?setTimeout(()=>location.reload(),150):s==="sensitivity"||s==="invertY"?Xt.settings[s]=e:s==="reduceMotion"?st.reduceMotion=e:s==="showTour"&&nt.setTourVisible(e)}},bl=s=>new Promise(e=>{f_.classList.toggle("on",s),setTimeout(e,hn.reduceMotion?20:400)});function Am(s){let e=yn[s],t=un.groundBelow(e.stand[0],e.stand[1]+2.5,e.stand[2]),n=new L(e.stand[0],t??e.stand[1],e.stand[2]),i=n.clone();i.y+=st.EYE;let r=Xu(i,new L(...e.look));return{feet:n,yaw:r.yaw,pitch:Ct.clamp(r.pitch,-.6,.75)}}function Es(s,e){if(!(s<0||s>=yn.length)){xn=s,nt.setStop(s,As),Cm(),ed(),e&&!hn.showTour&&nt.toast(`Stop ${s+1}: ${yn[s].name}`);try{history.replaceState(null,"",`#stop=${yn[s].key}`)}catch{}}}function ed(){let s=yn[xn],t=Math.hypot(st.position.x-s.stand[0],st.position.z-s.stand[2])<Em(xn)+1.5&&Math.abs(st.position.y-s.stand[1])<4;nt.setArrived(t&&!Rn),Rs.visible=Cs&&!t}async function gl(s){if(Rn||s<0||s>=yn.length)return;xn!==s&&Es(s,!1),nt.hideHint();let e=Am(s);st.mode==="fly"&&(st.setMode("walk"),nt.setFly(!1,Xt.isTouch));let n=[st.position.clone()];if(Ya===s-1)for(let o of yn[s].approach)n.push(new L(...o));n.push(e.feet);let i=!hn.reduceMotion&&st.onGround,r=0,a=new L(0,1.15,0);for(let o=0;o+1<n.length&&i;o++)r+=n[o].distanceTo(n[o+1]),un.segmentClear(n[o].clone().add(a),n[o+1].clone().add(a))||(i=!1);if(i&&r>.5&&r<160){let o=Ct.clamp(r/4.5,5,20);Rn={pts:n,length:r,t:0,duration:r/o+.6,target:e,yaw0:st.yaw,pitch0:st.pitch,index:s},Xt.setEnabled(!1),nt.setArrived(!1);return}Rn={fading:!0},Xt.setEnabled(!1),await bl(!0),st.setPose(e.feet,e.yaw,e.pitch),Rn=null,Xt.setEnabled(!Qu),vl(s),await bl(!1)}function vl(s){Ya=s,As.has(s)||(As.add(s),Zu()),nt.setStop(xn,As),ed()}var ju=s=>s*s*(3-2*s),bm=(s,e,t)=>s+(((e-s+Math.PI)%(2*Math.PI)+2*Math.PI)%(2*Math.PI)-Math.PI)*t;function y_(s){let e=Rn;if(!e||e.fading)return;e.t=Math.min(1,e.t+s/e.duration);let n=ju(e.t)*e.length,i=new L().copy(e.pts[e.pts.length-1]),r=e.target.yaw;for(let h=0;h+1<e.pts.length;h++){let d=e.pts[h].distanceTo(e.pts[h+1]);if(n<=d||h===e.pts.length-2){i.lerpVectors(e.pts[h],e.pts[h+1],d>0?Math.min(1,n/d):1),r=Xu(e.pts[h],e.pts[h+1]).yaw;break}n-=d}let a=un.groundBelow(i.x,i.y+1.6,i.z);a!==null&&Math.abs(a-i.y)<2.2&&(i.y=a);let o=ju(Ct.clamp((e.t-.55)/.45,0,1)),c=ju(Ct.clamp(e.t/.25,0,1)),l=bm(bm(e.yaw0,r,c),e.target.yaw,o),u=Ct.lerp(Ct.lerp(e.pitch0,0,c),e.target.pitch,o);st.setPose(i,l,u),e.t>=1&&(Rn=null,Xt.setEnabled(!Qu),vl(e.index))}var Rs=new Gt,Rm=[];function x_(){let s=new at(new fa(.62,.8,48).rotateX(-Math.PI/2),new nn({color:16767370,transparent:!0,opacity:.9,depthWrite:!1,toneMapped:!1}));s.position.y=.04;let e=new Yt({transparent:!0,depthWrite:!1,depthTest:!1,side:Mt,blending:ds,uniforms:{uTime:{value:0}},vertexShader:"varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.); }",fragmentShader:"uniform float uTime; varying vec2 vUv; void main(){ float a = pow(1. - vUv.y, 1.6) * (.16 + .05 * sin(uTime * 2.2)); gl_FragColor = vec4(vec3(1., .82, .45) * a, a); }"}),t=new at(new os(.34,.34,26,20,1,!0).translate(0,13,0),e);t.renderOrder=8,Rs.add(s,t),Rm=[s,e],Rs.visible=!1,un.scene.add(Rs)}function Cm(){let s=yn[xn],e=un.groundBelow(s.stand[0],s.stand[1]+2.5,s.stand[2]);Rs.position.set(s.stand[0],e??s.stand[1],s.stand[2])}function v_(){let s=/stop=([\w-]+)/.exec(location.hash);if(s){let t=yn.findIndex(n=>n.key===s[1]);if(t>=0)return{stop:t}}let e=/p=(-?[\d.]+),(-?[\d.]+),(-?[\d.]+),(-?[\d.]+),(-?[\d.]+)/.exec(location.hash);return e?{pose:e.slice(1).map(Number)}:{}}async function Im(s){if(Cs)return;await bl(!0),Cs=!0;let e=v_(),t=e.stop??0;xn=t;let n=Am(t);e.pose?st.setPose(new L(e.pose[0],e.pose[1],e.pose[2]),e.pose[3],e.pose[4]):st.setPose(n.feet,n.yaw,n.pitch);let i=s==="tour";hn.showTour!==i&&(hn.showTour=i,Zu()),nt.enter(i),nt.setStop(xn,As),Cm(),e.pose||vl(t),await bl(!1),Ju?nt.hint(["Slide your left thumb to walk. Drag anywhere else to look."],12e3):nt.hint([["W"],["A"],["S"],["D"]," to walk \xB7 drag to look \xB7 ",["F"]," to fly \xB7 ",["H"]," for help"],12e3)}function __(){let s=st.position,e=`${location.origin}${location.pathname}#p=${s.x.toFixed(1)},${s.y.toFixed(1)},${s.z.toFixed(1)},${st.yaw.toFixed(2)},${st.pitch.toFixed(2)}`,t=()=>nt.toast("Link copied");navigator.clipboard?.writeText?navigator.clipboard.writeText(e).then(t,()=>nt.toast(e,6e3)):nt.toast(e,6e3)}function ym(){if(Rn)return;let s=st.mode!=="fly";st.setMode(s?"fly":"walk"),nt.setFly(s,Xt.isTouch||Ju),nt.toast(s?"Flying as a dove. Look where you want to go.":"Walking")}async function w_(){nt=mm({tour:qu,codex:gm,times:Ur,settings:b_,actions:{start:Im,selectStop:Es,goStop:gl,toggleFly:ym,share:__,panel(s){Qu=s,Xt?.setEnabled(!s&&!Rn)},playerPose:()=>({x:st.position.x,z:st.position.z,yaw:st.yaw}),restart(){Es(0,!1),gl(0)}}});try{un=await lm(Cn,qa,s=>nt.setProgress(s*.96))}catch(s){console.error(s),nt.fail("The model could not be loaded. Check the connection and reload the page.");return}Ur[hn.time]&&un.setTime(xl.get("time")||hn.time),st=fm(bn,un),st.reduceMotion=hn.reduceMotion,Xt=pm(wm,document.getElementById("stick"),{sensitivity:hn.sensitivity,invertY:hn.invertY}),Xt.bindAscend(nt.upButton),Xt.bindDescend(nt.downButton),Xt.setEnabled(!1),x_(),Xt.on("firstInput",()=>setTimeout(()=>nt.hideHint(),2500)),Xt.on("tap",(s,e)=>{if(!Cs||Rn)return;let t=new Ne(s/window.innerWidth*2-1,-(e/window.innerHeight)*2+1),n=new wa;n.setFromCamera(t,bn);let i=un.identify(n.ray);i&&nt.tag(s,e,i.name,i.part)}),Xt.on("action",s=>{if(s==="escape"){!nt.closeSheet()&&document.pointerLockElement&&document.exitPointerLock();return}!Cs||nt.panelOpen||(s==="fly"?ym():s==="map"?nt.toggle("map"):s==="tour"?nt.toggle("stops"):s==="help"?nt.toggle("help"):s==="next"?Es(xn+1,!0):s==="prev"?Es(xn-1,!0):s==="go"&&gl(xn))}),bn.position.set(150,46,60),bn.lookAt(-20,16,0),Cn.compile(un.scene,bn),nt.setProgress(1),Wa?yl(0):requestAnimationFrame(yl),setTimeout(()=>{nt.ready(),Xt.setEnabled(!0),window.__mk.ready=!0},60)}var xm=new _a,Ga=16,vm=0,Ku=0,M_=xl.has("fixed"),Wa=xl.has("manual"),_m=0;function yl(s){Wa||requestAnimationFrame(yl);let e=Wa?s||0:Math.min(xm.getDelta(),.05);Wa&&(_m+=e);let t=Wa?_m:xm.elapsedTime;if(Cs){let n=Xt.read(e);if(Rn&&(y_(e),n.moveX=n.moveZ=n.lookX=n.lookY=0,n.jump=!1),st.update(e,n),un.update(e,t,bn.position),Ku-=e,Ku<=0){Ku=.2;let[i,r]=Tm(st.position,st.mode==="fly");if(nt.setPlace(i,r),!Rn){let a=-1;for(let o=0;o<yn.length;o++){let c=yn[o],l=Em(o)+(Ya===o?2.2:0);Math.hypot(st.position.x-c.stand[0],st.position.z-c.stand[2])<l&&Math.abs(st.position.y-c.stand[1])<3&&(a<0||o===xn)&&(a=o)}a>=0&&a!==Ya?(a!==xn&&Es(a,!1),vl(a),nt.toast(`Stop ${a+1}: ${yn[a].name}`)):a<0&&(Ya=-1),ed()}}if(nt.setCompass(st.yaw),Rs.visible){Rm[1].uniforms.uTime.value=t;let i=1+.12*Math.sin(t*2.6);Rs.children[0].scale.set(i,1,i)}}else{let n=-.42+Math.sin(t*.05)*.5;bn.position.set(-10+Math.cos(n)*175,44+Math.sin(t*.07)*6,Math.sin(n)*175),bn.lookAt(-18,17,0),un.update(e,t,bn.position)}if(Cn.render(un.scene,bn),Ga+=(e*1e3-Ga)*.05,!M_&&t-vm>1.5){vm=t;let n=Ts;Ga>36?n=Math.max(.55,Ts-.12):Ga<19&&Ts<1&&(n=Math.min(1,Ts+.06)),n!==Ts&&(Ts=n,Cn.setPixelRatio(Sm*Ts),Cn.setSize(window.innerWidth,window.innerHeight,!1))}}window.__mk={ready:!1,get world(){return un},get player(){return st},get started(){return Cs},get traveling(){return!!Rn},get quality(){return qa},get emaMs(){return Ga},stops:yn,start:Im,goStop:gl,selectStop:Es,placeAt:Tm,camera:bn,renderer:Cn,step(s=1/30,e=1){for(let t=0;t<e;t++)yl(s)},get input(){return Xt},get ui(){return nt},get seen(){return[...As]},get current(){return xn}};w_();
