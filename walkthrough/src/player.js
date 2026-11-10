// First-person movement. Walking follows the floor by a ray cast straight down and is
// kept out of walls by a capsule; "dove" mode flies freely but still cannot pass stone.
import * as THREE from 'three';

const EYE = 1.62;
const HEIGHT = 1.78;
const RADIUS = 0.3;
const STEP = 0.62;         // tallest riser a visitor climbs without jumping
const GRAVITY = 24;
const WALK = 3.4;
const RUN = 8.2;
const FLY = 13;
const FLY_FAST = 34;
const LIMIT = [-1430, 1800]; // metres on each axis: the Old City to the west, the valley and slope to the east

export function createPlayer(camera, world) {
  const pos = new THREE.Vector3(96, 0, 0); // feet
  const vel = new THREE.Vector3();
  let yaw = Math.PI / 2;     // facing west, toward the House
  let pitch = 0;
  let vy = 0;
  let onGround = true;
  let mode = 'walk';
  let bob = 0;
  let reduceMotion = false;
  let stepSmooth = 0;        // visual smoothing of stair steps

  const bvh = world.bvh;
  const seg = new THREE.Line3();
  const box = new THREE.Box3();
  const triPoint = new THREE.Vector3();
  const capPoint = new THREE.Vector3();
  const tmp = new THREE.Vector3();
  const fwd = new THREE.Vector3();
  const right = new THREE.Vector3();
  const sphere = new THREE.Sphere();

  // Push a vertical capsule (bottom..top above the feet) out of the collider. Returns the push.
  function resolveCapsule(bottom, top, radius, out) {
    seg.start.set(pos.x, pos.y + bottom + radius, pos.z);
    seg.end.set(pos.x, pos.y + top - radius, pos.z);
    const sx = seg.start.x, sy = seg.start.y, sz = seg.start.z;
    box.makeEmpty();
    box.expandByPoint(seg.start);
    box.expandByPoint(seg.end);
    box.min.addScalar(-radius);
    box.max.addScalar(radius);
    bvh.shapecast({
      intersectsBounds: (b) => b.intersectsBox(box),
      intersectsTriangle: (tri) => {
        const d = tri.closestPointToSegment(seg, triPoint, capPoint);
        if (d < radius && d > 1e-7) {
          const depth = radius - d;
          tmp.subVectors(capPoint, triPoint).multiplyScalar(depth / d);
          seg.start.add(tmp);
          seg.end.add(tmp);
        }
      },
    });
    return out.set(seg.start.x - sx, seg.start.y - sy, seg.start.z - sz);
  }

  const push = new THREE.Vector3();
  function walkStep(dt, wish) {
    // horizontal motion
    const accel = onGround ? 16 : 4;
    vel.x += (wish.x - vel.x) * Math.min(1, accel * dt);
    vel.z += (wish.z - vel.z) * Math.min(1, accel * dt);
    const px0 = pos.x, pz0 = pos.z;
    pos.x += vel.x * dt;
    pos.z += vel.z * dt;
    // Off the platform the ground is a height map: a rise taller than a step is a wall.
    if (!world.onDeck(pos.x, pos.z) && world.topAt(pos.x, pos.z) > pos.y + STEP) {
      pos.x = px0; pos.z = pz0; vel.x = 0; vel.z = 0;
    }
    resolveCapsule(STEP, HEIGHT, RADIUS, push);
    pos.x += push.x;
    pos.z += push.z;
    if (push.lengthSq() > 1e-10) {
      // lose the part of the velocity that ran into the wall
      const n = tmp.set(push.x, 0, push.z);
      if (n.lengthSq() > 1e-10) {
        n.normalize();
        const into = vel.x * n.x + vel.z * n.z;
        if (into < 0) { vel.x -= n.x * into; vel.z -= n.z * into; }
      }
    }

    // vertical: floor under the feet
    let ground = world.groundBelow(pos.x, pos.y + STEP + 0.05, pos.z);
    if (!world.onDeck(pos.x, pos.z)) {
      const t = world.topAt(pos.x, pos.z);
      if (t <= pos.y + STEP + 0.05 && (ground === null || t > ground)) ground = t;
      else if (t > pos.y + STEP + 0.05) { pos.y = t; vy = 0; ground = t; } // set down inside something: stand on it
    }
    if (ground !== null && vy <= 0.01 && ground >= pos.y - (onGround ? STEP : 0.02)) {
      if (ground > pos.y + 1e-3) stepSmooth = Math.min(0.6, stepSmooth + (ground - pos.y));
      else if (onGround && ground < pos.y - 1e-3) stepSmooth = Math.max(-0.6, stepSmooth - (pos.y - ground));
      pos.y = ground;
      vy = 0;
      onGround = true;
    } else {
      onGround = false;
      vy -= GRAVITY * dt;
      pos.y += vy * dt;
      if (vy > 0) {
        // head against a ceiling
        resolveCapsule(HEIGHT - 0.5, HEIGHT + 0.1, 0.2, push);
        if (push.y < -1e-4) { pos.y += push.y; vy = 0; }
      }
      if (ground !== null && pos.y <= ground) { pos.y = ground; vy = 0; onGround = true; }
      if (pos.y < -260) { pos.y = world.topAt(pos.x, pos.z); vy = 0; }
    }
  }

  function flyStep(dt, wish) {
    vel.x += (wish.x - vel.x) * Math.min(1, 5 * dt);
    vel.y += (wish.y - vel.y) * Math.min(1, 5 * dt);
    vel.z += (wish.z - vel.z) * Math.min(1, 5 * dt);
    pos.addScaledVector(vel, dt);
    sphere.center.set(pos.x, pos.y + EYE, pos.z);
    sphere.radius = 0.45;
    const c0 = tmp.copy(sphere.center);
    const sx = c0.x, sy = c0.y, sz = c0.z;
    bvh.shapecast({
      intersectsBounds: (b) => b.intersectsSphere(sphere),
      intersectsTriangle: (tri) => {
        tri.closestPointToPoint(sphere.center, triPoint);
        const d = triPoint.distanceTo(sphere.center);
        if (d < sphere.radius && d > 1e-7) {
          capPoint.subVectors(sphere.center, triPoint).multiplyScalar((sphere.radius - d) / d);
          sphere.center.add(capPoint);
        }
      },
    });
    pos.x += sphere.center.x - sx;
    pos.y += sphere.center.y - sy;
    pos.z += sphere.center.z - sz;
    // never below the ground or inside a house
    pos.y = THREE.MathUtils.clamp(pos.y, world.topAt(pos.x, pos.z) + 0.7 - EYE, 320);
  }

  function update(dt, input) {
    yaw += input.lookX;
    pitch = THREE.MathUtils.clamp(pitch + input.lookY, -1.45, 1.45);
    fwd.set(-Math.sin(yaw), 0, -Math.cos(yaw));
    right.set(Math.cos(yaw), 0, -Math.sin(yaw));

    const wish = new THREE.Vector3();
    if (mode === 'walk') {
      const sp = input.run ? RUN : WALK;
      wish.addScaledVector(fwd, input.moveZ * sp).addScaledVector(right, input.moveX * sp);
      if (input.jump && onGround) { vy = 6.2; onGround = false; }
      // substep so a fast frame can never tunnel through a wall
      const n = Math.max(1, Math.ceil((RUN * dt) / 0.2));
      for (let i = 0; i < n; i++) walkStep(dt / n, wish);
    } else {
      const sp = input.run ? FLY_FAST : FLY;
      const cp = Math.cos(pitch);
      wish.set(fwd.x * cp, Math.sin(pitch), fwd.z * cp).multiplyScalar(input.moveZ * sp);
      wish.addScaledVector(right, input.moveX * sp);
      wish.y += ((input.up ? 1 : 0) - (input.down ? 1 : 0)) * sp * 0.7;
      const n = Math.max(1, Math.ceil((FLY_FAST * dt) / 0.3));
      for (let i = 0; i < n; i++) flyStep(dt / n, wish);
    }
    pos.x = THREE.MathUtils.clamp(pos.x, LIMIT[0], LIMIT[1]);
    pos.z = THREE.MathUtils.clamp(pos.z, LIMIT[0], LIMIT[1]);

    // camera
    const speed = Math.hypot(vel.x, vel.z);
    stepSmooth *= Math.exp(-dt * 11);
    let eye = EYE - stepSmooth;
    if (mode === 'walk' && onGround && !reduceMotion) {
      bob += dt * speed * 1.9;
      eye += Math.sin(bob * 2) * 0.022 * Math.min(1, speed / WALK);
    }
    camera.position.set(pos.x, pos.y + eye, pos.z);
    camera.rotation.set(pitch, yaw, 0, 'YXZ');
    return speed;
  }

  function setPose(p, yawTo, pitchTo) {
    pos.copy(p);
    vel.set(0, 0, 0);
    vy = 0;
    stepSmooth = 0;
    onGround = mode === 'walk';
    if (yawTo !== undefined) yaw = yawTo;
    if (pitchTo !== undefined) pitch = pitchTo;
  }

  function setMode(m) {
    if (m === mode) return;
    mode = m;
    vel.set(0, 0, 0);
    vy = 0;
    if (m === 'fly') { pos.y += 0.6; onGround = false; }
  }

  return {
    update, setPose, setMode,
    get mode() { return mode; },
    get position() { return pos; },
    get yaw() { return yaw; },
    get pitch() { return pitch; },
    get onGround() { return onGround; },
    set reduceMotion(v) { reduceMotion = v; },
    EYE,
  };
}

/** Yaw and pitch that look from `from` toward `to`. */
export function lookAngles(from, to) {
  const dx = to.x - from.x, dy = to.y - from.y, dz = to.z - from.z;
  return { yaw: Math.atan2(-dx, -dz), pitch: Math.atan2(dy, Math.hypot(dx, dz)) };
}
