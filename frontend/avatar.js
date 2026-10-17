import {retargetPalm,resetPalm} from './wrist-retarget.js';
import {idleArmDirections,idleBodyPose} from './idle-poses.js';
import {addMissingHairPhysics} from './hair-physics.js';
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { VRMLoaderPlugin, VRMUtils } from "@pixiv/three-vrm";
import { dampFactor, scaleExpressions, rigQuaternionComponents, routeBlink, neutralHeadPitch } from "./rig.js";
import { retargetDirection } from './retarget.js';
import { relaxedArmDirections } from './rest-pose.js';
import { clothingClearance } from './clothing-clearance.js';
import {encodeAlphaMask} from './hit-mask.js';

export function initAvatar({output, widget=false, onLoad, onError}) {
let studioState = {settings:{},rig:{}};
let loadGeneration = 0;
let previousExpressions = {};
let baseSceneQuaternion=new THREE.Quaternion(),baseHipPosition=null,thighLength=.4;
let idleRoll=0;
const idleRotation=new THREE.Quaternion();

// ---------------------------------------------------------------------------
// Renderer / Scene / Camera
// ---------------------------------------------------------------------------
const canvas = document.getElementById("c");
const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setClearColor(0x000000, 0);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(32, window.innerWidth / window.innerHeight, 0.1, 100);
camera.position.set(0, 1.45, -1.8);
camera.lookAt(0, 1.32, 0);

// Lights — simple 3-point setup
scene.add(new THREE.HemisphereLight(0xffffff, 0x444444, 1.0));
const key = new THREE.DirectionalLight(0xffffff, 0.9);
key.position.set(1, 2, -1.5);
scene.add(key);
const fill = new THREE.DirectionalLight(0xffffff, 0.3);
fill.position.set(-1, 1, -1);
scene.add(fill);

// ---------------------------------------------------------------------------
// VRM model
// ---------------------------------------------------------------------------
let vrm = null;
let currentVrmUrl = null;
let _framingApplied = false;
let _sitCam = null;  // {dist, targetY, fov, tilt} — stored sitting framing
let _standCam = null;  // full-body framing

function _poseArms(directions, alpha, previousBones) {
  vrm.scene.updateMatrixWorld(true);
  for(const side of ['left','right']){
    const rest=relaxedArmDirections(side);
    for(const [segment,childName,key] of [['UpperArm','LowerArm','upper'],['LowerArm','Hand','lower']]){
      const name=side+segment,bone=_getBone(name),child=_getBone(side+childName);
      if(!bone||!child)continue;
      const previous=previousBones?.get(bone)||bone.quaternion.clone();
      const captured=directions?.[name]||rest[key];
      const target=segment==='UpperArm'?clothingClearance(captured,side,studioState.settings.clothingClearance!==false):captured;
      if(!retargetDirection(bone,child,target,previous,alpha)){
        retargetDirection(bone,child,rest[key],previous,alpha);
      }
    }
  }
}

function _applyPose(vrmModel, pose) {
  const h = vrmModel.humanoid;
  if (!h) return;

  // Standing amount: 0 = sitting, 1 = standing
  const standing = pose?.standing ?? 0;
  const sit = 1.0 - standing;

  // Base posture — no forced lean (kept straight)
  const hips = _getBone("hips");
  if (hips) hips.rotation.set(0, 0, 0);
  const spine = _getBone("spine");
  if (spine) spine.rotation.set(0, 0, 0);

  if (pose) {
    // Spine: forward lean + twist + lateral bend
    // Keep the torso neutral; a forced standing lean also tilts the head.
    const sp = pose.spine;
    const lean = (sp ? sp[0] : (pose.torso ?? 0));
    const twist = sp ? sp[1] : 0;
    const lateral = sp ? sp[2] : 0;
    const upperChest = _getBone("upperChest");
    if (upperChest) upperChest.rotation.set(lean * 0.5, twist * 0.5, lateral * 0.5);
    const chest = _getBone("chest");
    if (chest) chest.rotation.set(lean * 0.3, twist * 0.3, lateral * 0.3);
    if (spine) spine.rotation.set(lean * 0.2, twist * 0.2, lateral * 0.2);
  } else {
    const upperChest = _getBone("upperChest");
    if (upperChest) upperChest.rotation.set(0, 0, 0);
    const chest = _getBone("chest");
    if (chest) chest.rotation.set(0, 0, 0);
  }
}

async function loadVRM(url) {
  const generation = ++loadGeneration;
  const loader = new GLTFLoader();
  loader.register(parser => new VRMLoaderPlugin(parser));
  try {
    const gltf = await loader.loadAsync(url);
    const next = gltf.userData.vrm;
    if (!next) throw new Error('文件不是受支持的 VRM 模型');
    if (generation !== loadGeneration) { VRMUtils.deepDispose(next.scene); return; }
    if (vrm) { scene.remove(vrm.scene); VRMUtils.deepDispose(vrm.scene); }
    vrm = next;
    VRMUtils.rotateVRM0(vrm);
    scene.add(vrm.scene);
    baseSceneQuaternion.copy(vrm.scene.quaternion);idleRoll=0;
    for (const k of Object.keys(_BONE_CACHE)) delete _BONE_CACHE[k];
    savedBones.clear();
    previousExpressions = {};
    window._lastTwist = {};
    vrm.update(0);
    baseHipPosition=_getBone("hips")?.position.clone();
    thighLength=_getBone("leftLowerLeg")?.position.length()||.4;
    vrm.scene.updateMatrixWorld(true);
    const box = new THREE.Box3().setFromObject(vrm.scene);
    const size = box.getSize(new THREE.Vector3());
    const center = box.getCenter(new THREE.Vector3());
    vrm.scene.position.x -= center.x;
    vrm.scene.position.z -= center.z;
    framing = { targetY: box.min.y + size.y * .72, dist: Math.max(size.y * 1.4, 1.6),
                centerY:center.y, fullHeight:size.y, fullWidth:size.x };
    _applyPose(vrm, null);
    _poseArms(null,1);
    vrm.update(0);
    const addedHairJoints=addMissingHairPhysics(vrm);
    canvas.dataset.hairJoints=String(vrm.springBoneManager?.joints.size||0);
    canvas.dataset.addedHairJoints=String(addedHairJoints);
    onLoad('已加载 · ' + (vrm.meta?.metaVersion === '1' ? 'VRM 1.0' : 'VRM 0.x'));
  } catch (error) { console.error(error); onError('角色加载失败：' + error.message); }
}
let framing = {targetY:1.2,dist:2.4};

// ---------------------------------------------------------------------------
// Apply rig state to VRM each frame
// ---------------------------------------------------------------------------
function applyRig(rig) {
  if (!vrm || !rig) return;
  let expr = scaleExpressions(rig.expressions || {}, studioState.settings.expression ?? 1.3);
  const em = vrm.expressionManager;
  if (em) {
    expr=routeBlink(expr,em);
    const alpha = dampFactor(studioState.settings.smoothing ?? .55, frameDt);
    for (const item of em.expressions) {
      const name = item.expressionName;
      // Prefer separate eyelid controls over stacking blink + blinkLeft/Right.
      const target = expr[name] ?? 0;
      const expressionAlpha=name.startsWith('blink')?Math.max(alpha,1-Math.exp(-frameDt*40)):alpha;
      const value = (previousExpressions[name] ?? 0) + (target - (previousExpressions[name] ?? 0)) * expressionAlpha;
      em.setValue(name, value);
      previousExpressions[name] = value;
    }
    em.update();
  }

  // Head bone rotation (radians: yaw, pitch, roll, YXZ order)
  if (rig.head) {
    const head = vrm.humanoid?.getNormalizedBoneNode("head");
    if (head) {
      const [yaw, pitch, roll] = rig.head;
      head.rotation.order = "YXZ";
      const gain = studioState.settings.sensitivity ?? 1;
      head.rotation.set(neutralHeadPitch(pitch) * gain, yaw * gain, roll * gain);
    }
  }

  // Eye gaze
  if (rig.gaze && vrm.lookAt) {
    const [yaw, pitch] = rig.gaze;
    vrm.lookAt.applier.applyYawPitch(THREE.MathUtils.radToDeg(yaw), THREE.MathUtils.radToDeg(pitch));
  }

  // Hand finger curls (pass standing for palm offset blend)
  _applyHands(rig.hands, rig.pose?.standing ?? 0);
}

// ---------------------------------------------------------------------------
// Hand tracking: wrist orientation + per-joint finger angles
// ---------------------------------------------------------------------------
const _FINGER_NAMES = ["thumb", "index", "middle", "ring", "little"];
const _HAND_BONES = {
  left: {
    thumb:  ["leftThumbMetacarpal", "leftThumbProximal", "leftThumbDistal"],
    index:  ["leftIndexProximal", "leftIndexIntermediate", "leftIndexDistal"],
    middle: ["leftMiddleProximal", "leftMiddleIntermediate", "leftMiddleDistal"],
    ring:   ["leftRingProximal", "leftRingIntermediate", "leftRingDistal"],
    little: ["leftLittleProximal", "leftLittleIntermediate", "leftLittleDistal"],
  },
  right: {
    thumb:  ["rightThumbMetacarpal", "rightThumbProximal", "rightThumbDistal"],
    index:  ["rightIndexProximal", "rightIndexIntermediate", "rightIndexDistal"],
    middle: ["rightMiddleProximal", "rightMiddleIntermediate", "rightMiddleDistal"],
    ring:   ["rightRingProximal", "rightRingIntermediate", "rightRingDistal"],
    little: ["rightLittleProximal", "rightLittleIntermediate", "rightLittleDistal"],
  },
};
const _BONE_CACHE = {};

function _getBone(name) {
  if (!vrm?.humanoid) return null;
  if (!(name in _BONE_CACHE)) {
    _BONE_CACHE[name] = vrm.humanoid.getNormalizedBoneNode(name);
  }
  return _BONE_CACHE[name];
}

function _applyHands(hands, standing = 0) {
  for (const side of ["left", "right"]) {
    const hand = hands?.[side];
    const sign = side === "left" ? -1 : 1;

    // Keep the idle wrist neutral; tracking adds a limited palm twist.
    const handBone = _getBone(side === "left" ? "leftHand" : "rightHand");
    if (handBone) {
      const twistKey = side + "_twist";
      let twist = hand?.twist;
      if (twist == null) {
        twist = 0;
      } else {
        (window._lastTwist ??= {})[twistKey] = twist;
      }
      const final = hand ? Math.max(-.61, Math.min(.61, -twist)) : 0;
      handBone.rotation.set(final, 0, 0);
    }

    // Per-joint finger angles (raw radians from MediaPipe landmarks)
    // Use detected joint data at any distance; missing joints return to rest.
    const restCurls = {index:[.20,.28,.15],middle:[.26,.35,.19],ring:[.32,.42,.23],little:[.38,.48,.27],thumb:[.10,.16,.10]};
    for (const fingerName of _FINGER_NAMES) {
      const bones = _HAND_BONES[side][fingerName];
      const angles = hand?.fingers?.[fingerName] ?? [];
      for (let j = 0; j < bones.length; j++) {
        const bone = _getBone(bones[j]);
        if (!bone) continue;
        const tracked = Number.isFinite(angles[j]);
        const flex = tracked ? Math.max(0,Math.min(1.5,angles[j])) : restCurls[fingerName][j];
        const angle = sign * flex;
        if (fingerName === "thumb") {
          // Subtract rest baseline so open thumb = straight, only curl past threshold
          const baseline = [0.35, 0.25, 0.15][j] ?? 0.2;
          const curl = tracked ? Math.min(1.1,Math.max(0, flex - baseline) * 1.5) : restCurls.thumb[j];
          bone.rotation.set(0, -sign * curl, 0);
        } else {
          bone.rotation.set(0, 0, angle);
        }
      }
    }
  }
}

// ---------------------------------------------------------------------------
// Animation loop
// ---------------------------------------------------------------------------
const clock = new THREE.Clock();
let frameDt = 1 / 60;
const savedBones = new Map();
const targetQuaternion = new THREE.Quaternion();
const armNames = new Set(['leftUpperArm','rightUpperArm','leftLowerArm','rightLowerArm']);
const controlledNames = new Set(['leftUpperLeg','rightUpperLeg','leftLowerLeg','rightLowerLeg','leftFoot','rightFoot','hips','spine','chest','upperChest','head',
  'leftUpperArm','rightUpperArm','leftLowerArm','rightLowerArm','leftHand','rightHand',
  ...Object.values(_HAND_BONES).flatMap(hand => Object.values(hand).flat())]);
function resize() {
  const bounds = canvas.parentElement.getBoundingClientRect();
  const width = Math.max(1, bounds.width), height = Math.max(1, bounds.height);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  renderer.setSize(width, height, false);
}
new ResizeObserver(resize).observe(canvas.parentElement);
function animate() {
  requestAnimationFrame(animate);
  frameDt = Math.min(clock.getDelta(), .1);
  const settings = studioState.settings || {};
  const rig = studioState.rig || {};
  if(settings.avatarMode==='2d') return;
  if (output) canvas.parentElement.classList.toggle('mirrored', !!settings.mirror);
  if (vrm) {
    for (const [name, bone] of Object.entries(vrm.humanoid.normalizedHumanBones)) {
      if (bone?.node && controlledNames.has(name)) {
        if (!savedBones.has(bone.node)) savedBones.set(bone.node, new THREE.Quaternion());
        savedBones.get(bone.node).copy(bone.node.quaternion);
      }
    }
    const preset=studioState.running?'natural':settings.idlePose||'natural';
    const bodyPose=idleBodyPose(preset);
    const poseAlpha=1-Math.exp(-frameDt*6);
    idleRoll+=(bodyPose.roll-idleRoll)*poseAlpha;
    idleRotation.setFromAxisAngle(new THREE.Vector3(0,0,1),idleRoll);
    vrm.scene.quaternion.copy(idleRotation).multiply(baseSceneQuaternion);
    const hips=_getBone('hips');
    if(hips&&baseHipPosition)hips.position.lerp(baseHipPosition.clone().add(new THREE.Vector3(0,-bodyPose.lowering*thighLength,0)),poseAlpha);
    _applyPose(vrm, settings.body === false || !studioState.running ? null : rig.pose);
    for(const [name,angles] of Object.entries(bodyPose.legs))_getBone(name)?.rotation.set(...angles);
    canvas.dataset.idlePose=preset;
    const neutral = {head:[0,0,0], gaze:[0,0], expressions:{},hands:null};
    applyRig({...neutral, ...rig, head:rig.head || [0,0,0], gaze:rig.gaze || [0,0], hands: settings.hands === false ? null : rig.hands});
    const alpha = dampFactor(settings.smoothing ?? .55, frameDt);
    const directions = studioState.running ? (settings.body === false ? null : rig.pose?.armDirections) : idleArmDirections(settings.idlePose,performance.now()/1000);
    for (const [bone, previous] of savedBones) {
      if ([...armNames].some(name=>_getBone(name)===bone)) continue;
      if(settings.hands!==false&&['left','right'].some(side=>rig.hands?.[side]?.palm&&_getBone(side+'Hand')===bone))continue;
      targetQuaternion.copy(bone.quaternion);
      targetQuaternion.fromArray(rigQuaternionComponents(targetQuaternion.toArray(), vrm.meta?.metaVersion === '0'));
      bone.quaternion.copy(previous).slerp(targetQuaternion, alpha);
    }
    // Use the same world-space solver for tracking, idle and missing arms.
    // Returning to rest is slower than following a live movement.
    const restAlpha=dampFactor(Math.max(settings.smoothing??.55,.84),frameDt);
    const armAlpha=dampFactor(Math.min(settings.smoothing??.55,.8),frameDt);
    for(const side of ['left','right']){
      const rest=relaxedArmDirections(side);
      vrm.scene.updateMatrixWorld(true);
      for(const [segment,childName,key] of [['UpperArm','LowerArm','upper'],['LowerArm','Hand','lower']]){
        const name=side+segment,bone=_getBone(name),child=_getBone(side+childName);
        if(!bone||!child)continue;
        const previous=savedBones.get(bone)||bone.quaternion.clone();
        const canonical=directions?.[name];
        const live=canonical?new THREE.Vector3().fromArray(canonical).applyQuaternion(idleRotation).toArray():null;
        if(!retargetDirection(bone,child,live||rest[key],previous,live?armAlpha:restAlpha)){
          retargetDirection(bone,child,rest[key],previous,restAlpha);
        }
      }
    }
    // Solve wrists after the actual smoothed forearm, in world space. A fast
    // quaternion filter avoids scalar angle wrapping and double smoothing.
    if(settings.hands!==false){
      for(const side of ['left','right']){
        const hand=_getBone(side+'Hand'),palm=rig.hands?.[side]?.palm;
        if(hand&&palm)retargetPalm(hand,_getBone(side+'IndexProximal'),_getBone(side+'LittleProximal'),palm,savedBones.get(hand)||hand.quaternion.clone(),1-Math.exp(-frameDt*18),frameDt,_getBone(side+'LowerArm'));
        else if(hand)resetPalm(hand);
      }
    }
    if(widget){
      const center=new THREE.Vector3(0,framing.centerY-bodyPose.lowering*thighLength*.55,0).applyQuaternion(idleRotation);
      const c=Math.abs(Math.cos(idleRoll)),s=Math.abs(Math.sin(idleRoll));
      const h=framing.fullHeight,w=framing.fullWidth;
      const fitHeight=h*c+w*s,fitWidth=w*c+h*s;
      const tan=Math.tan(THREE.MathUtils.degToRad(16));
      const distance=Math.max(fitHeight*1.15/(2*tan),fitWidth*1.12/(2*tan*camera.aspect));
      camera.position.set(center.x,center.y,distance);
      camera.lookAt(center.x,center.y,0);
    }else{
      camera.position.set(0, framing.targetY + (settings.height ?? 0), framing.dist / (settings.zoom ?? 1));
      camera.lookAt(0, framing.targetY + (settings.height ?? 0), 0);
    }
    camera.fov = 32;
    camera.updateProjectionMatrix();
    vrm.update(frameDt);
  }
  renderer.render(scene, camera);
}
resize();
animate();
const hitPixel=new Uint8Array(4);
let hitTarget=null,hitPixels=null;
function hitMask(){
 if(!vrm||canvas.hidden)return null;
 const box=canvas.getBoundingClientRect(),w=Math.max(1,Math.min(192,Math.ceil(box.width/3))),h=Math.max(1,Math.min(288,Math.ceil(box.height/3)));
 if(!hitTarget||hitTarget.width!==w||hitTarget.height!==h){hitTarget?.dispose();hitTarget=new THREE.WebGLRenderTarget(w,h);hitPixels=new Uint8Array(w*h*4);}
 const previous=renderer.getRenderTarget();
 try{renderer.setRenderTarget(hitTarget);renderer.render(scene,camera);renderer.readRenderTargetPixels(hitTarget,0,0,w,h,hitPixels);}
 finally{renderer.setRenderTarget(previous);}
 return encodeAlphaMask(hitPixels,w,h,{flipY:true,mirror:canvas.parentElement.classList.contains('mirrored')});
}
function hitTest(clientX,clientY){
  if(!vrm||canvas.hidden)return false;
  const box=canvas.getBoundingClientRect();
  let x=(clientX-box.left)/box.width,y=(clientY-box.top)/box.height;
  if(x<0||x>=1||y<0||y>=1)return false;
  if(canvas.parentElement.classList.contains('mirrored'))x=1-x;
  // Read the rendered alpha, including skinning, hair and material cutouts.
  // Render and read synchronously; the default WebGL buffer is discarded later.
  renderer.render(scene,camera);
  const gl=renderer.getContext();
  if(gl.isContextLost())return false;
  gl.readPixels(Math.min(canvas.width-1,Math.floor(x*canvas.width)),Math.min(canvas.height-1,Math.floor((1-y)*canvas.height)),1,1,gl.RGBA,gl.UNSIGNED_BYTE,hitPixel);
  return hitPixel[3]>=24;
}
return {load:loadVRM,hitTest,hitMask, setState(next){studioState=next;}};
}
