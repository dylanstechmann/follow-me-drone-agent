// Procedural, z-up scenario viewport. three.js is imported lazily from the site's
// existing import map; the SVG fallback has no library or WebGL dependency.

const asNumber = (value) => Number.isFinite(Number(value)) ? Number(value) : 0;
const SVG_NS = "http://www.w3.org/2000/svg";

function cssColor(element, name, fallback) {
  return getComputedStyle(element).getPropertyValue(name).trim() || fallback;
}

export async function createScene3D(container, options = {}) {
  const THREE = await import("three");
  const { OrbitControls } = await import("three/addons/controls/OrbitControls.js");
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.domElement.setAttribute("aria-hidden", "true");
  container.replaceChildren(renderer.domElement);

  const scene = new THREE.Scene();
  const external = new THREE.PerspectiveCamera(45, 1, 0.025, 500);
  const onboard = new THREE.PerspectiveCamera(60, 1, 0.02, 250);
  external.up.set(0, 0, 1);
  onboard.up.set(0, 0, 1);
  const controls = new OrbitControls(external, renderer.domElement);
  controls.enableDamping = false;
  controls.minDistance = 1.2;
  controls.maxDistance = 180;
  controls.maxPolarAngle = Math.PI * 0.495;

  const hemisphere = new THREE.HemisphereLight(0xf4f8ff, 0x344038, 1.6);
  hemisphere.position.set(0, 0, 20);
  scene.add(hemisphere);
  const sun = new THREE.DirectionalLight(0xffffff, 2.3);
  sun.position.set(-10, -12, 22);
  scene.add(sun);
  const fill = new THREE.DirectionalLight(0xb8d8ff, 0.65);
  fill.position.set(12, 8, 10);
  scene.add(fill);

  const mats = {
    drone: new THREE.MeshStandardMaterial({ color: 0x26343b, roughness: 0.48, metalness: 0.55 }),
    arm: new THREE.MeshStandardMaterial({ color: 0x60727b, roughness: 0.5, metalness: 0.65 }),
    rotor: new THREE.MeshStandardMaterial({ color: 0x11181b, roughness: 0.35 }),
    accent: new THREE.MeshStandardMaterial({ color: 0x2a78d6, roughness: 0.45 }),
    tentacle: new THREE.MeshStandardMaterial({ color: 0xfab219, roughness: 0.38, metalness: 0.35 }),
    gripper: new THREE.MeshStandardMaterial({ color: 0xec835a, roughness: 0.5, metalness: 0.25 }),
    white: new THREE.MeshStandardMaterial({ color: 0xf0f0e8, roughness: 0.72 }),
    dark: new THREE.MeshStandardMaterial({ color: 0x182125, roughness: 0.65 }),
    red: new THREE.MeshStandardMaterial({ color: 0xc94e3d, roughness: 0.55 }),
    blue: new THREE.MeshStandardMaterial({ color: 0x286fa8, roughness: 0.5 }),
    board: new THREE.MeshStandardMaterial({ color: 0x2a78d6, roughness: 0.6 }),
    rubber: new THREE.MeshStandardMaterial({ color: 0x151515, roughness: 0.9 }),
    generic: new THREE.MeshStandardMaterial({ color: 0xeb6834, roughness: 0.7 }),
    pad: new THREE.MeshStandardMaterial({ color: 0x1baf7a, roughness: 0.85, transparent: true, opacity: 0.78 }),
    ground: new THREE.MeshStandardMaterial({ color: 0xa9b5a4, roughness: 1 }),
    floor: new THREE.MeshStandardMaterial({ color: 0xb5a990, roughness: 0.95 }),
    wall: new THREE.MeshStandardMaterial({ color: 0xd7d2c4, roughness: 1 }),
    rug: new THREE.MeshStandardMaterial({ color: 0x5d7e81, roughness: 1 }),
    water: new THREE.MeshStandardMaterial({ color: 0x3b9fc4, transparent: true, opacity: 0.43, roughness: 0.25, depthWrite: false, side: THREE.DoubleSide }),
    marker: new THREE.MeshBasicMaterial({ color: 0xfab219, transparent: true, opacity: 0.8, side: THREE.DoubleSide }),
    skin: new THREE.MeshStandardMaterial({ color: 0xb87954, roughness: 0.9 }),
    shirt: new THREE.MeshStandardMaterial({ color: 0xec835a, roughness: 0.9 }),
  };
  const vec = (p) => new THREE.Vector3(asNumber(p?.x), asNumber(p?.y), asNumber(p?.z));
  const mesh = (geometry, material, parent, position) => {
    const item = new THREE.Mesh(geometry, material);
    if (position) item.position.set(...position);
    parent.add(item);
    return item;
  };
  const box = (parent, material, size, position = [0, 0, 0]) => mesh(new THREE.BoxGeometry(...size), material, parent, position);
  const cylinder = (parent, material, radius, height, position = [0, 0, 0], segments = 20) => {
    const item = mesh(new THREE.CylinderGeometry(radius, radius, height, segments), material, parent, position);
    item.rotation.x = Math.PI / 2; // three cylinders are y-axis; the scenario is z-up
    return item;
  };
  const label = (parent, text, position = [0, 0, 1], width = 2.3) => {
    const canvas = document.createElement("canvas");
    canvas.width = 512;
    canvas.height = 96;
    const context = canvas.getContext("2d");
    context.fillStyle = "rgba(12, 20, 23, 0.88)";
    context.fillRect(0, 0, 512, 96);
    context.strokeStyle = "#74b8ef";
    context.lineWidth = 4;
    context.strokeRect(2, 2, 508, 92);
    context.fillStyle = "#f4f6f2";
    context.font = "600 30px ui-monospace, monospace";
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.fillText(text, 256, 49, 480);
    const texture = new THREE.CanvasTexture(canvas);
    if (THREE.SRGBColorSpace) texture.colorSpace = THREE.SRGBColorSpace;
    const material = new THREE.SpriteMaterial({ map: texture, transparent: true, depthTest: false });
    const sprite = new THREE.Sprite(material);
    sprite.position.set(...position);
    sprite.scale.set(width, width * 96 / 512, 1);
    sprite.renderOrder = 20;
    parent.add(sprite);
    return sprite;
  };
  const clearGenerated = (group) => {
    group.traverse((item) => {
      item.geometry?.dispose();
      if (item.isSprite) {
        item.material.map?.dispose();
        item.material.dispose();
      } else if (item.material && !Object.values(mats).includes(item.material)) {
        item.material.dispose();
      }
    });
    group.clear();
  };
  const between = (item, a, b) => {
    const start = vec(a);
    const end = vec(b);
    const direction = end.clone().sub(start);
    const length = Math.max(direction.length(), 0.0001);
    item.position.copy(start.add(end).multiplyScalar(0.5));
    item.scale.set(1, length, 1);
    item.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction.normalize());
  };

  const environment = new THREE.Group();
  const targetHolder = new THREE.Group();
  scene.add(environment, targetHolder);

  // A recognizable but deliberately schematic multirotor, not a hardware model.
  const drone = new THREE.Group();
  box(drone, mats.drone, [0.68, 0.44, 0.18]);
  box(drone, mats.accent, [0.18, 0.46, 0.1], [0.18, 0, 0.08]);
  const rotorPoints = [[-0.53, -0.4], [-0.53, 0.4], [0.53, -0.4], [0.53, 0.4]];
  for (const [x, y] of rotorPoints) {
    const arm = mesh(new THREE.CylinderGeometry(0.035, 0.035, 1, 10), mats.arm, drone);
    between(arm, { x: 0, y: 0, z: 0 }, { x, y, z: 0 });
    cylinder(drone, mats.arm, 0.085, 0.1, [x, y, 0.025]);
    cylinder(drone, mats.rotor, 0.28, 0.012, [x, y, 0.095], 32);
    box(drone, mats.white, [0.48, 0.025, 0.012], [x, y, 0.105]);
  }
  const cameraPod = mesh(new THREE.SphereGeometry(0.085, 16, 12), mats.dark, drone, [0.27, 0, -0.13]);
  cameraPod.scale.set(1, 0.8, 0.8);
  scene.add(drone);

  const tentacle = mesh(new THREE.CylinderGeometry(0.025, 0.025, 1, 12), mats.tentacle, scene);
  const gripper = new THREE.Group();
  box(gripper, mats.gripper, [0.18, 0.06, 0.045]);
  box(gripper, mats.gripper, [0.025, 0.035, 0.14], [-0.075, 0, -0.065]);
  box(gripper, mats.gripper, [0.025, 0.035, 0.14], [0.075, 0, -0.065]);
  scene.add(gripper);

  const rider = new THREE.Group();
  // Synthetic rider and board: geometric figures only, no person imagery.
  box(rider, mats.board, [0.57, 0.15, 0.025], [0, 0, 0.075]);
  for (const x of [-0.19, 0.19]) for (const y of [-0.095, 0.095]) {
    const wheel = cylinder(rider, mats.rubber, 0.035, 0.025, [x, y, 0.035], 12);
    wheel.rotation.set(Math.PI / 2, 0, 0);
  }
  const torso = cylinder(rider, mats.shirt, 0.18, 0.58, [0, 0, 1.05], 16);
  torso.scale.x = 0.8;
  mesh(new THREE.SphereGeometry(0.13, 18, 12), mats.skin, rider, [0, 0, 1.48]);
  for (const y of [-0.09, 0.09]) {
    const leg = mesh(new THREE.CylinderGeometry(0.055, 0.05, 1, 10), mats.dark, rider);
    between(leg, { x: 0, y, z: 0.14 }, { x: 0.03, y, z: 0.77 });
  }
  label(rider, "SYNTHETIC · CONSENTING", [0, 0, 1.95], 2.8);
  scene.add(rider);

  let trace = null;
  let lastFrame = null;
  let targetGroup = null;
  let cameraMode = "external";
  let autoTrack = true;
  let raf = 0;
  let disposed = false;
  let resizeObserver = null;
  let themeObserver = null;
  const media = window.matchMedia("(prefers-color-scheme: dark)");

  const draw = () => {
    raf = 0;
    if (disposed) return;
    renderer.render(scene, cameraMode === "onboard" ? onboard : external);
  };
  const requestDraw = () => {
    if (!raf && !disposed) raf = requestAnimationFrame(draw);
  };
  controls.addEventListener("change", requestDraw);
  controls.addEventListener("start", () => { autoTrack = false; });

  const recolor = () => {
    const background = cssColor(container, "--scene-bg", "#e8eeeb");
    scene.background = new THREE.Color(background);
    mats.ground.color.set(background).offsetHSL(0, -0.03, -0.035);
    requestDraw();
  };
  const resize = () => {
    const width = Math.max(280, container.clientWidth || 800);
    const height = Math.max(300, container.clientHeight || 480);
    renderer.setSize(width, height, false);
    for (const camera of [external, onboard]) {
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    }
    requestDraw();
  };

  const buildEnvironment = (config) => {
    clearGenerated(environment);
    const follow = config.mode === "follow";
    const span = follow ? 100 : 24;
    const centre = follow ? 34 : 0;
    const ground = mesh(new THREE.PlaneGeometry(span, follow ? 30 : 24), config.setting === "indoor" ? mats.floor : mats.ground, environment, [centre, 0, config.surface === "water" ? -1.15 : -0.025]);
    ground.receiveShadow = true;
    const grid = new THREE.GridHelper(span, Math.min(100, span), 0x74847c, 0x9aa79f);
    grid.rotation.x = Math.PI / 2;
    grid.position.set(centre, 0, config.surface === "water" ? -1.13 : 0.002);
    grid.material.transparent = true;
    grid.material.opacity = 0.35;
    environment.add(grid);
    if (config.surface === "water") {
      mesh(new THREE.PlaneGeometry(span, follow ? 30 : 24), mats.water, environment, [centre, 0, 0]);
      label(environment, "SHALLOW WATER · ZERO DRAG", [5, 7, 0.08], 4.1);
    }
    if (config.setting === "indoor") {
      box(environment, mats.wall, [18, 0.14, 4], [0, 8, 2]);
      box(environment, mats.wall, [0.14, 18, 4], [-8.5, 0, 2]);
      box(environment, mats.dark, [18, 0.04, 0.12], [0, 7.9, 0.06]);
      box(environment, mats.dark, [0.04, 18, 0.12], [-8.4, 0, 0.06]);
      mesh(new THREE.PlaneGeometry(5, 3), mats.rug, environment, [1.5, 1.5, 0.006]);
      label(environment, "SYNTHETIC LIVING ROOM", [0, 7.75, 2.6], 3.6);
    }
    const pad = config.drop_zone;
    cylinder(environment, mats.pad, config.drop_zone_radius_m || 1, 0.035, [pad.x, pad.y, pad.z + 0.0175], 48);
    label(environment, "SAFE DROP PAD", [pad.x, pad.y, pad.z + 0.45], 1.8);
  };

  const buildTarget = (config) => {
    clearGenerated(targetHolder);
    targetGroup = new THREE.Group();
    targetHolder.add(targetGroup);
    const spec = trace.frames[0].target;
    const d = spec.dimensions_m;
    if (spec.kind === "soccer_ball") {
      mesh(new THREE.SphereGeometry(d.x / 2, 28, 20), mats.white, targetGroup);
      const seams = mesh(new THREE.SphereGeometry(d.x / 2 * 1.006, 12, 8), new THREE.MeshBasicMaterial({ color: 0x253036, wireframe: true, transparent: true, opacity: 0.55 }), targetGroup);
      seams.rotation.z = 0.25;
    } else if (spec.kind === "soda_can") {
      cylinder(targetGroup, mats.red, d.x / 2, d.z, [0, 0, 0], 28);
      cylinder(targetGroup, mats.white, d.x / 2 * 1.01, 0.006, [0, 0, d.z / 2], 28);
    } else if (spec.kind === "pennyboard") {
      box(targetGroup, mats.board, [d.x, d.y, 0.025], [0, 0, d.z / 2 - 0.0125]);
      for (const x of [-d.x * 0.32, d.x * 0.32]) for (const y of [-d.y * 0.6, d.y * 0.6]) {
        cylinder(targetGroup, mats.rubber, 0.035, 0.025, [x, y, 0.035], 12);
      }
    } else {
      box(targetGroup, mats.generic, [d.x, d.y, d.z]);
      const edges = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(d.x * 1.005, d.y * 1.005, d.z * 1.005)), new THREE.LineBasicMaterial({ color: 0x30241c }));
      targetGroup.add(edges);
    }
    const small = Math.max(d.x, d.y) < 0.25;
    if (small) {
      const ring = mesh(new THREE.RingGeometry(0.17, 0.205, 40), mats.marker, targetGroup, [0, 0, -d.z / 2 + 0.008]);
      ring.renderOrder = 5;
    }
    label(targetGroup, `${spec.kind.replaceAll("_", " ").toUpperCase()} · ILLUSTRATIVE`, [0, 0, d.z / 2 + 0.32], small ? 2.5 : 2.1);
  };

  const updateExternal = (frame) => {
    if (!autoTrack || !frame.viewer_orbit_camera) return;
    external.position.copy(vec(frame.viewer_orbit_camera.position));
    controls.target.copy(vec(frame.viewer_orbit_camera.look_at));
    external.up.set(0, 0, 1);
    controls.update();
  };
  const updateOnboard = (frame) => {
    const pose = frame.onboard_camera_pose;
    onboard.position.copy(vec(pose.position));
    onboard.up.copy(vec(pose.up || { x: 0, y: 0, z: 1 }));
    onboard.fov = asNumber(pose.vertical_fov_deg) || 60;
    onboard.lookAt(vec(pose.look_at));
    onboard.updateProjectionMatrix();
  };

  const setTrace = (nextTrace) => {
    trace = nextTrace;
    buildEnvironment(trace.config);
    buildTarget(trace.config);
    const follow = trace.config.mode === "follow";
    rider.visible = follow;
    targetHolder.visible = !follow;
    autoTrack = true;
    lastFrame = trace.frames[0];
    update(lastFrame);
    reset();
  };

  const update = (frame) => {
    if (!frame) return;
    lastFrame = frame;
    drone.position.copy(vec(frame.drone_flight.position));
    drone.rotation.z = asNumber(frame.drone_flight.yaw_deg) * Math.PI / 180;
    const dronePosition = frame.drone_flight.position;
    const tip = frame.tentacle.tip_position;
    tentacle.visible = frame.tentacle.extension_m > 0.001;
    if (tentacle.visible) between(tentacle, dronePosition, tip);
    gripper.position.copy(vec(tip));
    gripper.visible = trace?.config.mode !== "follow";
    if (targetGroup) targetGroup.position.copy(vec(frame.target.position));
    if (frame.follow) {
      rider.position.copy(vec(frame.follow.rider_position));
      rider.rotation.z = Math.atan2(asNumber(frame.follow.rider_velocity.y), asNumber(frame.follow.rider_velocity.x));
    }
    updateExternal(frame);
    updateOnboard(frame);
    controls.enabled = cameraMode === "external";
    requestDraw();
  };

  const setCamera = (mode) => {
    cameraMode = mode === "onboard" ? "onboard" : "external";
    controls.enabled = cameraMode === "external";
    if (lastFrame) update(lastFrame);
    requestDraw();
  };
  const reset = () => {
    autoTrack = true;
    if (lastFrame) {
      updateExternal(lastFrame);
      if (!lastFrame.viewer_orbit_camera) {
        const target = vec(lastFrame.target.position);
        controls.target.copy(target);
        external.position.copy(target.clone().add(new THREE.Vector3(-7, -9, 6)));
      }
      controls.update();
    }
    requestDraw();
  };
  const nudge = (action) => {
    const offset = external.position.clone().sub(controls.target);
    const distance = Math.max(1, offset.length());
    if (action === "left" || action === "right") {
      offset.applyAxisAngle(new THREE.Vector3(0, 0, 1), action === "left" ? 0.16 : -0.16);
    } else if (action === "up" || action === "down") {
      const horizontal = new THREE.Vector3(offset.x, offset.y, 0);
      const axis = horizontal.cross(new THREE.Vector3(0, 0, 1)).normalize();
      if (axis.lengthSq() > 0) offset.applyAxisAngle(axis, action === "up" ? 0.12 : -0.12);
      if (offset.z < 0.3) offset.z = 0.3;
    } else if (action === "in" || action === "out") {
      offset.multiplyScalar(action === "in" ? 0.84 : 1.19);
    }
    const clamped = Math.max(controls.minDistance, Math.min(controls.maxDistance, offset.length()));
    offset.setLength(clamped || distance);
    autoTrack = false;
    external.position.copy(controls.target).add(offset);
    controls.update();
    requestDraw();
  };
  const contextLost = (event) => {
    event.preventDefault();
    options.onFailure?.("The WebGL context was lost. Switched to the top-down fallback.");
  };
  renderer.domElement.addEventListener("webglcontextlost", contextLost);

  if (window.ResizeObserver) {
    resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(container);
  } else window.addEventListener("resize", resize);
  themeObserver = new MutationObserver(recolor);
  themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  media.addEventListener("change", recolor);
  recolor();
  resize();

  return {
    kind: "webgl",
    setTrace, update, setCamera, reset, nudge,
    dispose() {
      if (disposed) return;
      disposed = true;
      if (raf) cancelAnimationFrame(raf);
      resizeObserver?.disconnect();
      if (!resizeObserver) window.removeEventListener("resize", resize);
      themeObserver?.disconnect();
      media.removeEventListener("change", recolor);
      renderer.domElement.removeEventListener("webglcontextlost", contextLost);
      controls.dispose();
      const geometries = new Set();
      const materials = new Set(Object.values(mats));
      const textures = new Set();
      scene.traverse((item) => {
        if (item.geometry) geometries.add(item.geometry);
        if (item.material) {
          for (const material of Array.isArray(item.material) ? item.material : [item.material]) {
            materials.add(material);
            if (material.map) textures.add(material.map);
          }
        }
      });
      geometries.forEach((item) => item.dispose());
      materials.forEach((item) => item.dispose());
      textures.forEach((item) => item.dispose());
      renderer.dispose();
      renderer.domElement.remove();
    },
  };
}

// Accessible, non-WebGL view. It is deliberately a schematic top-down display, not a
// pretend onboard perspective. All mission controls and the event table remain usable.
export function createTopDownScene(container) {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", "0 0 800 480");
  svg.setAttribute("aria-hidden", "true");
  container.replaceChildren(svg);
  const node = (tag, attrs = {}, parent = svg, text) => {
    const item = document.createElementNS(SVG_NS, tag);
    for (const [key, value] of Object.entries(attrs)) item.setAttribute(key, value);
    if (text !== undefined) item.textContent = text;
    parent.appendChild(item);
    return item;
  };
  node("rect", { width: 800, height: 480, fill: "var(--scene-bg)" });
  const grid = node("g", { stroke: "var(--scene-grid)", "stroke-width": 1, "stroke-opacity": 0.45 });
  for (let x = 0; x <= 800; x += 40) node("line", { x1: x, y1: 0, x2: x, y2: 480 }, grid);
  for (let y = 0; y <= 480; y += 40) node("line", { x1: 0, y1: y, x2: 800, y2: y }, grid);
  const world = node("g");
  const drop = node("circle", { fill: "var(--good)", "fill-opacity": 0.2, stroke: "var(--good)", "stroke-width": 2 }, world);
  const dropText = node("text", { "text-anchor": "middle" }, world, "safe drop pad");
  const waterText = node("text", { x: 18, y: 28 }, svg, "");
  const link = node("line", { stroke: "var(--warning)", "stroke-width": 3 }, world);
  const marker = node("circle", { fill: "none", stroke: "var(--warning)", "stroke-width": 2, "stroke-dasharray": "4 3" }, world);
  const target = node("rect", { width: 14, height: 14, x: -7, y: -7, rx: 3, fill: "var(--serious)", stroke: "var(--surface)", "stroke-width": 2 }, world);
  const targetText = node("text", { x: 12, y: 5, class: "halo", "stroke-width": 4 }, world, "target");
  const rider = node("circle", { r: 8, fill: "var(--s-phone)", stroke: "var(--surface)", "stroke-width": 2 }, world);
  const riderText = node("text", { x: 12, y: -10, class: "halo", "stroke-width": 4 }, world, "synthetic consenting rider");
  const drone = node("path", { d: "M0,-12 L9,9 L0,5 L-9,9 Z", fill: "var(--ink)", stroke: "var(--surface)", "stroke-width": 2 }, world);
  const droneText = node("text", { x: 13, y: 5, class: "halo", "stroke-width": 4 }, world, "drone");
  const modeText = node("text", { x: 782, y: 28, "text-anchor": "end" }, svg, "TOP-DOWN FALLBACK · Z-UP METRES");
  const note = document.createElement("p");
  note.className = "scene-fallback-message";
  note.textContent = "Non-WebGL top-down fallback. Onboard mode does not reproduce perspective here; use the textual framing readout.";
  container.appendChild(note);
  let trace = null;
  let project = (p) => ({ x: 400, y: 240 });
  let cameraMode = "external";
  let lastFrame = null;

  const setTrace = (next) => {
    trace = next;
    const points = [next.config.drop_zone];
    for (const frame of next.frames) {
      points.push(frame.drone_flight.position, frame.target.position);
      if (frame.follow) points.push(frame.follow.rider_position);
    }
    let minX = Math.min(...points.map((p) => p.x));
    let maxX = Math.max(...points.map((p) => p.x));
    let minY = Math.min(...points.map((p) => p.y));
    let maxY = Math.max(...points.map((p) => p.y));
    const pad = 2;
    minX -= pad; maxX += pad; minY -= pad; maxY += pad;
    const spanX = Math.max(8, maxX - minX);
    const spanY = Math.max(8, maxY - minY);
    const scale = Math.min(740 / spanX, 400 / spanY);
    const midX = (minX + maxX) / 2;
    const midY = (minY + maxY) / 2;
    project = (p) => ({ x: 400 + (p.x - midX) * scale, y: 245 - (p.y - midY) * scale });
    const dz = project(next.config.drop_zone);
    drop.setAttribute("cx", dz.x); drop.setAttribute("cy", dz.y);
    drop.setAttribute("r", Math.max(10, next.config.drop_zone_radius_m * scale));
    dropText.setAttribute("x", dz.x); dropText.setAttribute("y", dz.y + Math.max(18, next.config.drop_zone_radius_m * scale + 14));
    waterText.textContent = `${next.config.setting.toUpperCase()} · ${next.config.surface.toUpperCase()} · SCHEMATIC`;
    update(next.frames[0]);
  };
  const place = (item, p) => item.setAttribute("transform", `translate(${project(p).x} ${project(p).y})`);
  const update = (frame) => {
    if (!frame || !trace) return;
    lastFrame = frame;
    const d = project(frame.drone_flight.position);
    const t = project(frame.target.position);
    const tip = project(frame.tentacle.tip_position);
    place(drone, frame.drone_flight.position);
    place(target, frame.target.position);
    droneText.setAttribute("x", d.x + 13); droneText.setAttribute("y", d.y + 5);
    targetText.setAttribute("x", t.x + 12); targetText.setAttribute("y", t.y + 5);
    targetText.textContent = frame.target.kind.replaceAll("_", " ");
    for (const [key, value] of Object.entries({ x1: d.x, y1: d.y, x2: tip.x, y2: tip.y })) link.setAttribute(key, value);
    link.setAttribute("visibility", frame.tentacle.extension_m > 0.001 ? "visible" : "hidden");
    marker.setAttribute("cx", t.x); marker.setAttribute("cy", t.y);
    marker.setAttribute("r", Math.max(frame.target.dimensions_m.x, frame.target.dimensions_m.y) < 0.25 ? 18 : 12);
    const follow = Boolean(frame.follow);
    rider.setAttribute("visibility", follow ? "visible" : "hidden");
    riderText.setAttribute("visibility", follow ? "visible" : "hidden");
    target.setAttribute("visibility", follow ? "hidden" : "visible");
    targetText.setAttribute("visibility", follow ? "hidden" : "visible");
    marker.setAttribute("visibility", follow ? "hidden" : "visible");
    if (follow) {
      const r = project(frame.follow.rider_position);
      rider.setAttribute("cx", r.x); rider.setAttribute("cy", r.y);
      riderText.setAttribute("x", r.x + 12); riderText.setAttribute("y", r.y - 10);
    }
    modeText.textContent = cameraMode === "onboard" ? "ONBOARD SELECTED · TOP-DOWN FALLBACK" : "EXTERNAL · TOP-DOWN FALLBACK · Z-UP METRES";
  };
  return {
    kind: "svg",
    setTrace, update,
    setCamera(mode) { cameraMode = mode === "onboard" ? "onboard" : "external"; if (lastFrame) update(lastFrame); },
    reset() { if (lastFrame) update(lastFrame); },
    nudge() {},
    dispose() { container.replaceChildren(); },
  };
}
