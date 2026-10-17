import test from 'node:test';
import assert from 'node:assert/strict';
import {Object3D,Vector3} from 'three';
import {addMissingHairPhysics} from '../frontend/hair-physics.js';
function model(){const scene=new Object3D(),head=new Object3D();scene.add(head);const root=new Object3D();root.position.set(.12,.15,0);head.add(root);let parent=root;const bones=[];for(let i=0;i<8;i++){const b=new Object3D();b.position.set(0,-.15,0);parent.add(b);bones.push(b);parent=b;}return {scene,head,bones,humanoid:{getRawBoneNode:()=>head,rawHumanBones:{head:{node:head}}}};}
test('unconfigured long hair reacts to head turns and stays finite',()=>{const vrm=model();assert.equal(addMissingHairPhysics(vrm),7);const m=vrm.springBoneManager;for(let i=0;i<120;i++)m.update(1/60);const rest=vrm.bones[1].quaternion.clone();vrm.head.rotation.x=.4;vrm.scene.updateMatrixWorld(true);m.update(1/60);assert.ok(vrm.bones[1].quaternion.angleTo(rest)>.001);for(let i=0;i<300;i++)m.update(1/60);for(const b of vrm.bones)assert.ok(b.getWorldPosition(new Vector3()).toArray().every(Number.isFinite));assert.equal(addMissingHairPhysics(vrm),0);assert.equal(m.joints.size,7);});
test('short accessories are not treated as long hair',()=>{const vrm=model();vrm.bones[1].remove(vrm.bones[2]);assert.equal(addMissingHairPhysics(vrm),0);});
