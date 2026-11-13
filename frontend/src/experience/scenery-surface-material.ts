import { MeshStandardMaterial } from "three";

/** Continuous world-scale UVs and mixed albedo rather than a uniform flat tint. */
export function surfaceMaterial(
  color: string,
  kind: "ground" | "bark" | "chalk",
  vertexColors = false,
) {
  const material = new MeshStandardMaterial({
    color,
    vertexColors,
    roughness: kind === "chalk" ? 0.92 : 0.95,
  });
  material.userData.surface = kind;
  material.userData.coastalHaze = { value: 0 };
  material.onBeforeCompile = (shader) => {
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", "#include <common>\nvarying vec3 vSurface;")
      .replace(
        "#include <begin_vertex>",
        "#include <begin_vertex>\nvSurface=(modelMatrix*vec4(position,1.)).xyz;",
      );
    shader.fragmentShader = shader.fragmentShader.replace(
      "#include <common>",
      `#include <common>
      varying vec3 vSurface;
      float surfaceHash(vec3 p){return fract(sin(dot(p,vec3(127.1,311.7,74.7)))*43758.5453);}
      float surfaceNoise(vec3 p){vec3 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);return mix(mix(mix(surfaceHash(i),surfaceHash(i+vec3(1,0,0)),f.x),mix(surfaceHash(i+vec3(0,1,0)),surfaceHash(i+vec3(1,1,0)),f.x),f.y),mix(mix(surfaceHash(i+vec3(0,0,1)),surfaceHash(i+vec3(1,0,1)),f.x),mix(surfaceHash(i+vec3(0,1,1)),surfaceHash(i+1.),f.x),f.y),f.z);}
    `,
    );
    if (kind === "ground") {
      shader.uniforms.coastalHaze = material.userData.coastalHaze;
      shader.fragmentShader = shader.fragmentShader.replace(
        "varying vec3 vSurface;",
        "varying vec3 vSurface; uniform float coastalHaze;",
      );
      shader.fragmentShader = shader.fragmentShader.replace(
        "#include <fog_fragment>",
        `#include <fog_fragment>
      #ifdef USE_FOG
        gl_FragColor.rgb=mix(gl_FragColor.rgb,fogColor,coastalHaze*smoothstep(120.,180.,length(cameraPosition-vSurface)));
      #endif`,
      );
      shader.uniforms.grassMap = {
        value: material.userData.grassMap || material.map,
      };
      shader.fragmentShader = shader.fragmentShader.replace(
        "varying vec3 vSurface;",
        "varying vec3 vSurface;\nuniform sampler2D grassMap;",
      );
      shader.fragmentShader = shader.fragmentShader.replace(
        "#include <map_fragment>",
        `
      #ifdef USE_MAP
        vec2 uv=vMapUv;float variation=surfaceNoise(vSurface*.045);
        vec3 earth=mix(texture2D(map,uv).rgb,texture2D(map,mat2(.8,-.6,.6,.8)*uv*.37+vec2(.31,.71)).rgb,.28);
        vec3 grass=mix(texture2D(grassMap,uv*.24).rgb,texture2D(grassMap,uv*.68+vec2(.2,.8)).rgb,.22);
        grass*=vec3(.62,.79,.48);grass+=vec3(.026,.038,.014);
        float forest=clamp(smoothstep(-150.,-60.,vSurface.z)+1.-smoothstep(-850.,-795.,vSurface.z),0.,1.);
        float path=1.-smoothstep(2.8,6.5,abs(vSurface.x-1.5)+variation*1.8);
        vec3 soil=mix(earth*.65,earth*.94,path);
        diffuseColor.rgb=mix(grass*(.8+variation*.38),soil,forest);
        diffuseColor.rgb*=mix(.7,1.,smoothstep(-1.5,.5,vSurface.y));
      #endif`,
      );
    } else if (kind === "chalk") {
      shader.uniforms.grassMap = {
        value: material.userData.grassMap || material.map,
      };
      shader.fragmentShader = shader.fragmentShader.replace(
        "varying vec3 vSurface;",
        "varying vec3 vSurface; varying vec3 vRockNormal; uniform sampler2D grassMap;",
      );
      shader.vertexShader = shader.vertexShader
        .replace(
          "varying vec3 vSurface;",
          "varying vec3 vSurface; varying vec3 vRockNormal;",
        )
        .replace(
          "vSurface=(modelMatrix*vec4(position,1.)).xyz;",
          "vSurface=(modelMatrix*vec4(position,1.)).xyz; vRockNormal=normalize(mat3(modelMatrix)*normal);",
        );
      shader.fragmentShader = shader.fragmentShader.replace(
        "#include <map_fragment>",
        `
      #include <map_fragment>
      float n=surfaceNoise(vSurface*.8), large=surfaceNoise(vSurface*.12);
      float stratum=surfaceNoise(vec3(vSurface.x*.09,vSurface.y*1.7,vSurface.z*.09));
      float fissure=smoothstep(.67,.84,stratum)*(.15+.35*large);
      float grit=dot(diffuseColor.rgb,vec3(.2126,.7152,.0722));
      diffuseColor.rgb=vec3(.83,.84,.79)*(.78+.27*grit+.08*n)-vec3(fissure*.35);
      float wet=1.-smoothstep(.2,3.8,vSurface.y);
      diffuseColor.rgb*=1.-wet*.48;
      float turf=smoothstep(.55,.85,normalize(vRockNormal).y)*smoothstep(28.,39.,vSurface.y);
      vec3 turfColor=texture2D(grassMap,vSurface.xz*.035).rgb*vec3(.6,.78,.45);
      diffuseColor.rgb=mix(diffuseColor.rgb,turfColor,turf);
      `,
      );
    }
  };
  material.customProgramCacheKey = () =>
    `scenery-${kind}-${Boolean(material.userData.grassMap)}`;
  return material;
}
