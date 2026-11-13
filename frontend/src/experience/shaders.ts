export const skyVertex = `varying vec3 vDirection; void main(){vDirection=position;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`;
export const skyFragment = `varying vec3 vDirection;uniform float night;uniform float coast;
float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
float noise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);return mix(mix(hash(i),hash(i+vec2(1,0)),f.x),mix(hash(i+vec2(0,1)),hash(i+1.),f.x),f.y);}
void main(){vec3 d=normalize(vDirection);float h=max(d.y,0.);vec3 color=mix(mix(vec3(.77,.83,.74),vec3(.82,.87,.88),coast),vec3(.22,.44,.53),pow(h,.6));
vec2 uv=d.xz/(h+.24)*2.8;float clouds=smoothstep(.48,.78,noise(uv)*.65+noise(uv*2.1)*.35)*smoothstep(0.,.2,d.y);
color=mix(color,vec3(.95,.94,.85),clouds*.8);float sun=max(dot(d,normalize(vec3(-.4,.65,-.7))),0.);color+=vec3(.9,.7,.4)*(.12*pow(sun,14.)+.4*pow(sun,450.));
vec3 nocturnal=mix(vec3(.08,.16,.18),vec3(.012,.04,.065),pow(h,.5));
vec2 starsUV=vec2(atan(d.z,d.x),asin(d.y))*vec2(180.,220.);vec2 cell=floor(starsUV);float stars=step(.993,hash(cell))*(1.-smoothstep(.05,.19,length(fract(starsUV)-.5)))*smoothstep(.05,.3,d.y);
nocturnal+=vec3(.7,.82,.83)*stars*.65;float moon=pow(max(dot(d,normalize(vec3(-.45,.6,-.65))),0.),2200.);nocturnal+=vec3(.72,.8,.79)*moon;
gl_FragColor=vec4(mix(color,nocturnal,night),1.);
#include <tonemapping_fragment>
#include <colorspace_fragment>
}`;
export const waterVertex = `varying vec3 vWorld;void main(){vec4 w=modelMatrix*vec4(position,1.);vWorld=w.xyz;gl_Position=projectionMatrix*viewMatrix*w;}`;
export const waterFragment = `varying vec3 vWorld;uniform float phase;uniform float night;uniform float coast;
void main(){float wave=sin(vWorld.x*.28+vWorld.z*.16+phase)*.6+sin(vWorld.z*.4-vWorld.x*.08-phase*.4)*.4;
float fine=max(0.,sin(vWorld.x*1.7+vWorld.z*2.2+sin(vWorld.z*.21)+phase))*(1.-smoothstep(.15,1.,length(fwidth(vWorld.xz))));
vec3 color=mix(vec3(.12,.28,.24),vec3(.48,.63,.57),wave*.12+.35);color=mix(color,vec3(.19,.33,.36)+wave*.035,coast*.8);color+=vec3(.3,.34,.30)*pow(fine,12.)*.16;
color=mix(color,color*.22,night);gl_FragColor=vec4(color,.68);
#include <tonemapping_fragment>
#include <colorspace_fragment>
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
