import test from 'node:test';
import assert from 'node:assert/strict';
import { Object3D, Vector3, Quaternion } from 'three';
import { retargetDirection } from '../frontend/retarget.js';

function rig(legacy){
  const root=new Object3D(),torso=new Object3D(),upper=new Object3D(),lower=new Object3D(),hand=new Object3D();
  root.rotation.y=legacy?Math.PI:0;torso.rotation.set(.2,.45,-.16);root.add(torso);torso.add(upper);upper.add(lower);lower.add(hand);
  lower.position.set(legacy?-.3:.3,0,0);hand.position.set(legacy?-.25:.25,0,0);root.updateMatrixWorld(true);
  return {root,upper,lower,hand};
}
function direction(a,b){return b.getWorldPosition(new Vector3()).sub(a.getWorldPosition(new Vector3())).normalize();}
for(const legacy of [false,true])test(`world-space arm retarget compensates torso rotation (VRM ${legacy?'0':'1'})`,()=>{
  const r=rig(legacy),a=new Vector3(.4,-.7,.3).normalize(),b=new Vector3(.6,-.1,.5).normalize();
  assert.ok(retargetDirection(r.upper,r.lower,a.toArray(),new Quaternion(),1));
  assert.ok(retargetDirection(r.lower,r.hand,b.toArray(),new Quaternion(),1));
  assert.ok(direction(r.upper,r.lower).distanceTo(a)<1e-8);
  assert.ok(direction(r.lower,r.hand).distanceTo(b)<1e-8);
});
test('lower arm follows the actual smoothed upper-arm parent',()=>{
  const r=rig(false),b=new Vector3(.7,.2,.4).normalize();
  retargetDirection(r.upper,r.lower,[.3,-.8,.2],new Quaternion(),.25);
  retargetDirection(r.lower,r.hand,b.toArray(),new Quaternion(),1);
  assert.ok(direction(r.lower,r.hand).distanceTo(b)<1e-8);
});

import {relaxedArmDirections} from '../frontend/rest-pose.js';
for(const legacy of [false,true])test(`idle arms hang down with torso clearance (VRM ${legacy?'0':'1'})`,()=>{
 const r=rig(legacy),rest=relaxedArmDirections('left');
 retargetDirection(r.upper,r.lower,rest.upper,new Quaternion(),1);
 retargetDirection(r.lower,r.hand,rest.lower,new Quaternion(),1);
 const upper=direction(r.upper,r.lower),lower=direction(r.lower,r.hand);
 assert.ok(upper.angleTo(lower)<.05);
 assert.ok(upper.y<-.95&&lower.y<-.85);
 assert.ok(lower.x>0&&upper.x>0);
});

import {neutralHeadPitch} from '../frontend/rig.js';
test('level head rejects small pitch noise and corrects camera-to-avatar pitch direction',()=>{
 assert.equal(neutralHeadPitch(.04),0);
 assert.equal(neutralHeadPitch(-.04),0);
 assert.ok(neutralHeadPitch(.3)<0&&neutralHeadPitch(.3)>-.3);
 assert.ok(neutralHeadPitch(-.3)>0);
});
