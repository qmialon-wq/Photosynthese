import { MeshStandardMaterial } from "three";

/** Object-space detail, fixed to geometry; no textures, frame clock or extra draw pass. */
export function surfaceMaterial(
  color: string,
  kind: "ground" | "bark",
  vertexColors = false,
) {
  const material = new MeshStandardMaterial({
    color,
    vertexColors,
    roughness: 1,
  });
  material.onBeforeCompile = (shader) => {
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", "#include <common>\nvarying vec3 vSurface;")
      .replace(
        "#include <begin_vertex>",
        "#include <begin_vertex>\nvSurface=position;",
      );
    const pattern =
      kind === "bark"
        ? "float ribs=pow(.5+.5*sin(atan(vSurface.z,vSurface.x)*31.+sin(vSurface.y*160.)*.32),3.);float grain=sin(vSurface.y*320.+vSurface.x*90.)*.035;diffuseColor.rgb*=.72+ribs*.27+grain;"
        : "float patches=sin(vSurface.x*.31+sin(vSurface.z*.19)*1.8)*sin(vSurface.z*.27+sin(vSurface.x*.13));float detail=sin(vSurface.x*11.7)*sin(vSurface.z*10.3)*(1.-smoothstep(.2,2.,length(fwidth(vSurface))));diffuseColor.rgb*=.83+patches*.12+detail*.045;";
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>", "#include <common>\nvarying vec3 vSurface;")
      .replace(
        "#include <color_fragment>",
        `#include <color_fragment>\n${pattern}`,
      );
  };
  material.customProgramCacheKey = () => `symbiose-surface-${kind}`;
  return material;
}
