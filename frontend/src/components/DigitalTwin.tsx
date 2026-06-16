import { useEffect, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import type { TwinStructure } from "../types";

export default function DigitalTwin({ structures }: { structures: TwinStructure[] }) {
  const mountRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    const width = mount.clientWidth;
    const height = mount.clientHeight;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x05070f);

    const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 100);
    camera.position.set(2.2, 1.4, 3.2);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    mount.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.8;

    scene.add(new THREE.AmbientLight(0xffffff, 0.6));
    const dir = new THREE.DirectionalLight(0xffffff, 0.9);
    dir.position.set(3, 5, 4);
    scene.add(dir);
    const dir2 = new THREE.DirectionalLight(0x88aaff, 0.4);
    dir2.position.set(-3, -2, -3);
    scene.add(dir2);

    const group = new THREE.Group();
    for (const s of structures) {
      const mesh = buildMesh(s);
      if (mesh) group.add(mesh);
    }
    scene.add(group);

    // ground grid for spatial reference
    const grid = new THREE.GridHelper(6, 12, 0x243152, 0x1a2440);
    grid.position.y = -1.6;
    scene.add(grid);

    let raf = 0;
    const animate = () => {
      controls.update();
      renderer.render(scene, camera);
      raf = requestAnimationFrame(animate);
    };
    animate();

    const onResize = () => {
      const w = mount.clientWidth;
      const h = mount.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener("resize", onResize);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
      controls.dispose();
      renderer.dispose();
      mount.removeChild(renderer.domElement);
    };
  }, [structures]);

  return <div ref={mountRef} className="twin-canvas" />;
}

function buildMesh(s: TwinStructure): THREE.Mesh | null {
  const g = s.geometry as Record<string, unknown>;
  const color = new THREE.Color(s.color || "#888");
  const material = new THREE.MeshStandardMaterial({
    color,
    transparent: true,
    opacity: s.criticality === "critical" ? 0.95 : 0.7,
    roughness: 0.5,
    metalness: 0.1,
    emissive: s.criticality === "critical" ? color.clone().multiplyScalar(0.25) : new THREE.Color(0x000000),
  });

  if (g.type === "ellipsoid") {
    const c = g.center as number[];
    const r = g.radii as number[];
    const geom = new THREE.SphereGeometry(1, 32, 24);
    const mesh = new THREE.Mesh(geom, material);
    mesh.scale.set(r[0], r[1], r[2]);
    mesh.position.set(c[0], c[1], c[2]);
    return mesh;
  }
  if (g.type === "cylinder") {
    const from = new THREE.Vector3(...(g.from as number[]));
    const to = new THREE.Vector3(...(g.to as number[]));
    const radius = g.radius as number;
    const dirv = new THREE.Vector3().subVectors(to, from);
    const len = dirv.length();
    const geom = new THREE.CylinderGeometry(radius, radius, len, 16);
    const mesh = new THREE.Mesh(geom, material);
    mesh.position.copy(from).add(to).multiplyScalar(0.5);
    mesh.quaternion.setFromUnitVectors(
      new THREE.Vector3(0, 1, 0),
      dirv.clone().normalize()
    );
    return mesh;
  }
  return null;
}
