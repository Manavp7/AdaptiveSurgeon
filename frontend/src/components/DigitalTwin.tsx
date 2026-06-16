import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import type { TwinStructure } from "../types";

function webglAvailable(): boolean {
  try {
    const c = document.createElement("canvas");
    return !!(
      window.WebGLRenderingContext &&
      (c.getContext("webgl") || c.getContext("experimental-webgl"))
    );
  } catch {
    return false;
  }
}

export interface PlanOverlay {
  trajectory: number[][];
  safe: boolean;
}

export default function DigitalTwin({
  structures,
  plan,
}: {
  structures: TwinStructure[];
  plan?: PlanOverlay | null;
}) {
  const mountRef = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!webglAvailable()) {
      setFailed(true);
      return;
    }
    const mount = mountRef.current;
    if (!mount) return;

    const width = mount.clientWidth;
    const height = mount.clientHeight;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x05070f);

    const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 100);
    camera.position.set(2.2, 1.4, 3.2);

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true });
    } catch {
      setFailed(true);
      return;
    }
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

    // --- surgical plan overlay (trajectory + markers + animated probe) ---
    let probe: THREE.Mesh | null = null;
    let pathPts: THREE.Vector3[] = [];
    if (plan && plan.trajectory.length > 1) {
      pathPts = plan.trajectory.map((p) => new THREE.Vector3(p[0], p[1], p[2]));
      const lineColor = plan.safe ? 0x21d4a8 : 0xe0455e;
      const lineGeom = new THREE.BufferGeometry().setFromPoints(pathPts);
      const line = new THREE.Line(lineGeom, new THREE.LineBasicMaterial({ color: lineColor, linewidth: 2 }));
      scene.add(line);
      // entry (blue) + target (yellow) markers
      const entry = pathPts[0];
      const target = pathPts[pathPts.length - 1];
      const mk = (pos: THREE.Vector3, color: number) => {
        const m = new THREE.Mesh(new THREE.SphereGeometry(0.07, 16, 12), new THREE.MeshBasicMaterial({ color }));
        m.position.copy(pos);
        scene.add(m);
      };
      mk(entry, 0x4f8cff);
      mk(target, 0xe0a800);
      probe = new THREE.Mesh(
        new THREE.SphereGeometry(0.06, 16, 12),
        new THREE.MeshStandardMaterial({ color: lineColor, emissive: new THREE.Color(lineColor).multiplyScalar(0.4) })
      );
      scene.add(probe);
    }

    let raf = 0;
    const clock = new THREE.Clock();
    const animate = () => {
      controls.update();
      if (probe && pathPts.length > 1) {
        const t = (clock.getElapsedTime() * 0.25) % 1;
        const f = t * (pathPts.length - 1);
        const i = Math.floor(f);
        const frac = f - i;
        const a = pathPts[i];
        const b = pathPts[Math.min(i + 1, pathPts.length - 1)];
        probe.position.lerpVectors(a, b, frac);
      }
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
  }, [structures, plan]);

  if (failed) {
    return (
      <div className="twin-canvas" style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: 16 }}>
        <div>
          <div className="muted small" style={{ marginBottom: 8 }}>
            3D rendering unavailable (no WebGL). Anatomy structures:
          </div>
          {structures.map((s) => (
            <div key={s.name} className="small" style={{ marginBottom: 3 }}>
              <span className="dot" style={{ background: s.color }} />
              {s.name.replace(/_/g, " ")} — <span className={`sev-${s.criticality === "critical" ? "critical" : s.criticality === "caution" ? "medium" : "low"}`}>{s.criticality}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }
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
