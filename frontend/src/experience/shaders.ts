export const skyVertex = `varying vec3 vDirection; void main(){vDirection=position;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`;
export const skyFragment = `varying vec3 vDirection;uniform float night;uniform float coast;uniform vec3 sunDirection;
float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
float noise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);return mix(mix(hash(i),hash(i+vec2(1,0)),f.x),mix(hash(i+vec2(0,1)),hash(i+1.),f.x),f.y);}
void main(){vec3 d=normalize(vDirection);float h=max(d.y,0.);vec3 color=mix(mix(vec3(.77,.83,.74),vec3(.82,.87,.88),coast),vec3(.22,.44,.53),pow(h,.6));
vec2 uv=d.xz/(h+.24)*2.8;float clouds=smoothstep(.48,.78,noise(uv)*.65+noise(uv*2.1)*.35)*smoothstep(0.,.2,d.y);
color=mix(color,vec3(.95,.94,.85),clouds*.8);float sun=max(dot(d,normalize(sunDirection)),0.);color+=vec3(.9,.7,.4)*(.12*pow(sun,14.)+.4*pow(sun,450.));
vec3 nocturnal=mix(vec3(.08,.16,.18),vec3(.012,.04,.065),pow(h,.5));
vec2 starsUV=vec2(atan(d.z,d.x),asin(d.y))*vec2(180.,220.);vec2 cell=floor(starsUV);float stars=step(.993,hash(cell))*(1.-smoothstep(.05,.19,length(fract(starsUV)-.5)))*smoothstep(.05,.3,d.y);
nocturnal+=vec3(.7,.82,.83)*stars*.65;float moon=pow(max(dot(d,normalize(vec3(-.45,.6,-.65))),0.),2200.);nocturnal+=vec3(.72,.8,.79)*moon;
gl_FragColor=vec4(mix(color,nocturnal,night),1.);
#include <tonemapping_fragment>
#include <colorspace_fragment>
}`;
export const waterVertex = `varying vec3 vWorld;void main(){vec4 w=modelMatrix*vec4(position,1.);vWorld=w.xyz;gl_Position=projectionMatrix*viewMatrix*w;}`;
export const waterFragment = `
varying vec3 vWorld;uniform float phase;uniform float night;uniform float coast;uniform vec3 sunDirection;
uniform sampler2D reflectionMap;uniform mat4 reflectionMatrix;uniform float reflectionEnabled;
uniform vec3 fogColor;uniform float fogDensity;
float h(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
float n(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);return mix(mix(h(i),h(i+vec2(1,0)),f.x),mix(h(i+vec2(0,1)),h(i+1.),f.x),f.y);}
void main(){
 vec2 p=vWorld.xz;float t=phase;
 float a=dot(p,vec2(.29,.16))+t*.75,b=dot(p,vec2(-.17,.38))-t*.51,c=dot(p,vec2(.92,.72))+t*.93;
 float wind=n(p*.22+vec2(t*.03,-t*.02))*2.-1.;a+=wind*2.;b+=wind;
 float attenuation=1.-smoothstep(.12,1.6,length(fwidth(p)));
 vec3 normal=normalize(vec3(-cos(a)*.095+cos(b)*.065+cos(c)*.045*attenuation,1.,-cos(a)*.07-cos(b)*.09+cos(c)*.04*attenuation));
 vec3 V=normalize(cameraPosition-vWorld),L=normalize(sunDirection),R=reflect(-V,normal);
 float fresnel=.035+.965*pow(1.-max(dot(V,normal),0.),5.);
 vec3 sky=mix(vec3(.66,.76,.77),vec3(.27,.49,.64),pow(max(R.y,0.),.55));
 sky+=vec3(1.,.77,.43)*pow(max(dot(R,L),0.),340.)*.75;
 if(reflectionEnabled>.5){vec4 projected=reflectionMatrix*vec4(vWorld,1.);vec2 uv=projected.xy/projected.w;uv=clamp(uv+normal.xz*.03,vec2(.004),vec2(.996));vec2 r=vec2(.0016);vec3 reflected=(texture2D(reflectionMap,uv+r).rgb+texture2D(reflectionMap,uv-r).rgb+texture2D(reflectionMap,uv+vec2(r.x,-r.y)).rgb+texture2D(reflectionMap,uv+vec2(-r.x,r.y)).rgb)*.25;sky=mix(sky,reflected,.82);}
 vec3 deep=mix(vec3(.025,.115,.084),vec3(.028,.125,.155),coast);
 vec3 color=mix(deep,sky,clamp(fresnel*.88+.2,.0,.92));
 vec3 halfVector=normalize(L+V);float glint=pow(max(dot(normal,halfVector),0.),160.)*(.7+.3*n(p*3.));
 color+=vec3(1.,.86,.61)*glint*2.1*(1.-night);
 float center=8.*sin((p.y+210.)*.025)+6.*cos((p.y+210.)*.012);
 float width=8.+14.*smoothstep(0.,1.,(-p.y-245.)/45.)+4.*smoothstep(0.,1.,(-p.y-385.)/35.);
 float riverShore=width-abs(p.x-center);
 float coastShore=abs(length(p-vec2(23.,-753.))-7.);
 float shore=mix(riverShore,coastShore,coast);
 float foam=(1.-smoothstep(.0,.9,shore))*(.16+.2*n(p*2.+t*.035));
 color=mix(color,vec3(.72,.79,.7),foam*.45);
 color=mix(color,color*.22+vec3(.008,.02,.025),night);
 if(!gl_FrontFacing)color=mix(deep,color,.35);
 float distanceToCamera=length(cameraPosition-vWorld);float fog=1.-exp(-fogDensity*fogDensity*distanceToCamera*distanceToCamera);
 gl_FragColor=vec4(color,gl_FrontFacing?mix(.92,1.,coast):.68);
 #include <tonemapping_fragment>
 #include <colorspace_fragment>
 gl_FragColor.rgb=mix(gl_FragColor.rgb,linearToOutputTexel(vec4(fogColor,1.)).rgb,clamp(fog,0.,1.));
}`;
export const screenVertex = `varying vec2 vUv;void main(){vUv=uv;gl_Position=vec4(position.xy,0.,1.);}`;
/** A single world render is refracted; never blends two scene photographs. */
export const refractionFragment = `varying vec2 vUv;uniform sampler2D sceneColor;uniform float immersion;uniform float phase;
// The visible waterline comes from the actual y=0 mesh, never a second screen wipe.
void main(){vec2 uv=vUv;
vec2 shift=vec2(sin(uv.y*55.+phase*.8),cos(uv.x*42.-phase*.6))*.004*immersion;
vec3 color=texture2D(sceneColor,clamp(uv+shift,vec2(.002),vec2(.998))).rgb;
float rays=pow(.5+.5*sin(uv.x*28.+uv.y*5.+phase*.025),20.)*smoothstep(.1,1.,uv.y)*.035;
vec3 underwater=mix(color*vec3(.62,.9,.86),vec3(.035,.16,.14),smoothstep(.35,1.,uv.y)*.65)+vec3(rays*.6,rays,rays*.85);
color=mix(color,underwater,immersion);gl_FragColor=vec4(color,1.);
#include <tonemapping_fragment>
#include <colorspace_fragment>
}`;
export const fogVertex = `varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`;
export const fogFragment = `varying vec2 vUv;uniform float strength;void main(){float edge=sin(vUv.x*3.14159)*sin(vUv.y*3.14159);float billow=.7+.3*sin(vUv.x*18.)*sin(vUv.y*9.);gl_FragColor=vec4(.72,.81,.72,edge*billow*.09*strength);}`;
