import * as T from "three";

/** An openly illustrative reconstruction of Porte d'Aval and its distinct needle. */
export function createCoast() {
  const group = new T.Group();
  group.name = "etretat-evocation";
  const chalk = new T.MeshStandardMaterial({ color: "#dedbc7", roughness: 1 });
  chalk.onBeforeCompile = (shader) => {
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", "#include <common>\nvarying vec3 vStone;")
      .replace(
        "#include <begin_vertex>",
        "#include <begin_vertex>\nvStone=position;",
      );
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>", "#include <common>\nvarying vec3 vStone;")
      .replace(
        "#include <color_fragment>",
        "#include <color_fragment>\nfloat strata=pow(.5+.5*sin(vStone.y*4.8+sin(vStone.x*.4)*.7),18.); diffuseColor.rgb*=.84+.1*sin(vStone.y*1.5)-.17*strata;",
      );
  };
  const shape = new T.Shape();
  shape.moveTo(-45, 0);
  shape.lineTo(-47, 36);
  shape.lineTo(-44, 44);
  shape.lineTo(-33, 46);
  shape.lineTo(-22, 44.8);
  shape.lineTo(-14, 43);
  shape.lineTo(-5, 37);
  shape.lineTo(1.5, 27);
  shape.lineTo(8, 0);
  shape.lineTo(0, 0);
  shape.lineTo(-1, 12);
  shape.bezierCurveTo(-2, 32, -24, 35, -28, 12);
  shape.lineTo(-29, 0);
  shape.closePath();
  const arch = new T.Mesh(
    new T.ExtrudeGeometry(shape, {
      depth: 13,
      steps: 1,
      bevelEnabled: true,
      bevelThickness: 0.7,
      bevelSize: 0.8,
      bevelSegments: 2,
      curveSegments: 20,
    }),
    chalk,
  );
  arch.position.set(0, -0.8, -753);
  arch.name = "porte-d-aval";
  group.add(arch);
  const headlandGeometry = new T.BoxGeometry(110, 43, 95, 12, 10, 10);
  const hp = headlandGeometry.attributes.position;
  for (let i = 0; i < hp.count; i++) {
    const x = hp.getX(i),
      y = hp.getY(i),
      z = hp.getZ(i);
    hp.setXYZ(
      i,
      x + Math.sin(z * 0.13 + y * 0.05) * 1.6,
      y +
        Math.max(0, y / 21.5) * (Math.sin(x * 0.09) + Math.sin(z * 0.11)) * 1.5,
      z + Math.sin(x * 0.15 + y * 0.08) * 0.8,
    );
  }
  headlandGeometry.computeVertexNormals();
  const headland = new T.Mesh(headlandGeometry, chalk);
  headland.position.set(-100, 20.7, -787);
  group.add(headland);
  const grass = new T.Mesh(
    new T.BoxGeometry(111, 0.8, 97),
    new T.MeshStandardMaterial({ color: "#687b43", roughness: 1 }),
  );
  grass.position.set(-100, 42.5, -787);
  group.add(grass);
  const top = new T.Shape();
  top.moveTo(-45, 13);
  top.lineTo(-45, 0);
  top.lineTo(-20, 0);
  top.lineTo(-5, 0);
  top.lineTo(-5, 13);
  top.closePath();
  const cap = new T.Mesh(
    new T.ShapeGeometry(top),
    new T.MeshStandardMaterial({
      color: "#637b42",
      side: T.DoubleSide,
      roughness: 1,
    }),
  );
  cap.rotation.x = -Math.PI / 2;
  cap.position.set(0, 43, -740);
  group.add(cap);
  const needle = new T.Mesh(
    new T.LatheGeometry(
      [
        new T.Vector2(6.8, -20),
        new T.Vector2(7, -16),
        new T.Vector2(6, -5),
        new T.Vector2(4.7, 5),
        new T.Vector2(3.8, 11),
        new T.Vector2(2.3, 17),
        new T.Vector2(0.5, 21),
        new T.Vector2(0.1, 21.5),
      ],
      15,
    ),
    chalk,
  );
  needle.position.set(23, 19.7, -753);
  needle.rotation.z = 0.025;
  needle.name = "aiguille";
  const p = needle.geometry.attributes.position;
  for (let i = 0; i < p.count; i++) {
    const y = p.getY(i),
      x = p.getX(i),
      z = p.getZ(i);
    p.setXYZ(
      i,
      x * (1 + 0.08 * Math.sin(y * 2.1)),
      y,
      z * (1 + 0.08 * Math.cos(y * 1.9)),
    );
  }
  needle.geometry.computeVertexNormals();
  group.add(needle);
  return { group, arch, needle };
}
