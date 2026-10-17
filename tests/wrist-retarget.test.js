import test from 'node:test';
import assert from 'node:assert/strict';
import {Object3D,Vector3,Quaternion,Euler} from 'three';
import {retargetPalm,naturalWristRotation} from '../frontend/wrist-retarget.js';
for(const legacy of [false,true])for(const side of [1,-1])test(`large palm flips stay bounded with a rotated forearm, VRM${legacy?0:1} side${side}`,()=>{
 const root=new Object3D(),forearm=new Object3D(),hand=new Object3D(),index=new Object3D(),little=new Object3D();root.rotation.y=legacy?Math.PI:0;root.add(forearm);forearm.rotation.set(.2,-.4,.9);forearm.add(hand);hand.add(index,little);index.position.set(side*.08,0,.025);little.position.set(side*.07,0,-.025);
 const restDirection=index.position.clone().add(little.position).normalize(),restNormal=new Vector3().crossVectors(index.position,little.position).normalize();
 for(const angle of [-2.8,-1.6,0,1.6,2.8]){
  const desired=new Quaternion().setFromEuler(new Euler(angle,.3,-.2));
  const palm={direction:restDirection.clone().applyQuaternion(desired).toArray(),normal:restNormal.clone().applyQuaternion(desired).toArray()};
  const previous=hand.quaternion.clone();
  assert.ok(retargetPalm(hand,index,little,palm,previous,1,1/60));
  assert.ok(hand.quaternion.angleTo(previous)<=8/60+1e-8);
  for(let frame=0;frame<180;frame++)retargetPalm(hand,index,little,palm,hand.quaternion.clone(),.2,1/60);
  assert.ok(hand.quaternion.toArray().every(Number.isFinite));
  assert.ok(hand.quaternion.lengthSq()>.999);
 }
});
test('degenerate palm signals do not change the wrist',()=>{const h=new Object3D(),a=new Object3D(),b=new Object3D();assert.equal(retargetPalm(h,a,b,{direction:[0,0,0],normal:[0,0,0]},h.quaternion.clone(),1),false);});

test('normal wrist motion is full scale and extreme motion stays bounded',()=>{
 const axis=new Vector3(1,0,0);
 const small=naturalWristRotation(new Quaternion().setFromAxisAngle(axis,.5),axis);
 assert.ok(Math.abs(small.angleTo(new Quaternion())-.5)<1e-8);
 for(const angle of [-Math.PI,Math.PI])assert.ok(naturalWristRotation(new Quaternion().setFromAxisAngle(axis,angle),axis).angleTo(new Quaternion())<=Math.PI*7/36+1e-8);
 assert.ok(naturalWristRotation(new Quaternion().setFromAxisAngle(new Vector3(0,0,1),2),axis).angleTo(new Quaternion())<=Math.PI*7/18+1e-8);
});

test('ordinary pronation and wrist flexion are not attenuated',()=>{
 const axis=new Vector3(1,0,0);
 for(const [turnAxis,angle] of [[axis,.5],[new Vector3(0,0,1),1.0]]){
  const target=new Quaternion().setFromAxisAngle(turnAxis,angle);
  assert.ok(naturalWristRotation(target,axis).angleTo(target)<1e-7);
 }
});

test('one-frame palm reversals are ignored but a confirmed large turn follows',()=>{
 const parent=new Object3D(),hand=new Object3D(),index=new Object3D(),little=new Object3D();parent.add(hand);hand.add(index,little);index.position.set(.08,0,.02);little.position.set(.08,0,-.02);
 const neutral={direction:[1,0,0],normal:[0,1,0]},turned={direction:[1,0,0],normal:new Vector3(0,1,0).applyAxisAngle(new Vector3(1,0,0),2.5).toArray()};
 const tick=p=>retargetPalm(hand,index,little,p,hand.quaternion.clone(),1,1/60);
 tick(neutral);tick(turned);assert.ok(hand.quaternion.angleTo(new Quaternion())<1e-8);
 tick(neutral);assert.ok(hand.quaternion.angleTo(new Quaternion())<1e-8);
 for(let i=0;i<12;i++)tick(turned);assert.ok(hand.quaternion.angleTo(new Quaternion())>.4);
});

for(const legacy of [false,true])for(const sign of [-1,1])test(`forearm shares pronation without moving wrist position, VRM${legacy?0:1} side${sign}`,()=>{
 const root=new Object3D(),forearm=new Object3D(),hand=new Object3D(),index=new Object3D(),little=new Object3D();root.rotation.y=legacy?Math.PI:0;root.add(forearm);forearm.add(hand);hand.position.set(sign*.25,0,0);hand.add(index,little);index.position.set(sign*.08,0,.025);little.position.set(sign*.08,0,-.025);root.updateMatrixWorld(true);
 const axis=new Vector3(sign,0,0),original=hand.getWorldPosition(new Vector3());
 const desired=root.getWorldQuaternion(new Quaternion()).multiply(new Quaternion().setFromAxisAngle(axis,Math.PI/2));
 const palm={direction:index.position.clone().add(little.position).normalize().applyQuaternion(desired).toArray(),normal:new Vector3().crossVectors(index.position,little.position).normalize().applyQuaternion(desired).toArray()};
 for(let i=0;i<180;i++)retargetPalm(hand,index,little,palm,hand.quaternion.clone(),.3,1/60,forearm);
 assert.ok(hand.getWorldPosition(new Vector3()).distanceTo(original)<1e-8);
 assert.ok(forearm.quaternion.angleTo(new Quaternion())>1);
 assert.ok(hand.quaternion.angleTo(new Quaternion())<.4);
 assert.ok(hand.getWorldQuaternion(new Quaternion()).angleTo(desired)<1e-5);
});

test('sideways wrist bending is limited separately from normal flexion',()=>{
 const axis=new Vector3(1,0,0),normal=new Vector3(0,1,0);
 const side=naturalWristRotation(new Quaternion().setFromAxisAngle(normal,1.3),axis,normal);
 assert.ok(side.angleTo(new Quaternion())<=Math.PI*5/36+1e-8);
 const flex=new Quaternion().setFromAxisAngle(new Vector3(0,0,1),1);
 assert.ok(naturalWristRotation(flex,axis,normal).angleTo(flex)<1e-7);
});

test('palm wraparound never accumulates turns and returns to neutral',()=>{
 const forearm=new Object3D(),root=new Object3D(),hand=new Object3D(),index=new Object3D(),little=new Object3D();root.add(forearm);forearm.add(hand);hand.position.set(.25,0,0);hand.add(index,little);index.position.set(.08,0,.02);little.position.set(.08,0,-.02);
 for(const angle of [0,1.5,2.8,-2.8,-1.5,0]){
  const palm={direction:[1,0,0],normal:new Vector3(0,1,0).applyAxisAngle(new Vector3(1,0,0),angle).toArray()};
  for(let i=0;i<180;i++){retargetPalm(hand,index,little,palm,hand.quaternion.clone(),.3,1/60,forearm);assert.ok(forearm.quaternion.angleTo(new Quaternion())<=Math.PI*17/36+1e-8);}
 }
 assert.ok(forearm.quaternion.angleTo(new Quaternion())<1e-5);assert.ok(hand.quaternion.angleTo(new Quaternion())<1e-5);
});
