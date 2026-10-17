import test from 'node:test';
import assert from 'node:assert/strict';
import { dampFactor, scaleExpressions, rigQuaternionComponents, routeBlink } from '../frontend/rig.js';
import { Quaternion, Vector3 } from 'three';
test('expression amplification remains within valid blendshape range',()=>{
  assert.deepEqual(scaleExpressions({aa:.8, blinkLeft:.2, happy:-.1},2),{aa:1,blinkLeft:.2,happy:0});
});
test('VRM 0 and VRM 1 arm rotations produce the same world direction',()=>{
  const target=new Vector3(.3,-.8,.4).normalize();
  const canonical=new Quaternion().setFromUnitVectors(new Vector3(1,0,0),target);
  const legacy=new Quaternion().fromArray(rigQuaternionComponents(canonical.toArray(),true));
  const vrm0=new Vector3(-1,0,0).applyQuaternion(legacy).applyAxisAngle(new Vector3(0,1,0),Math.PI);
  const vrm1=new Vector3(1,0,0).applyQuaternion(canonical);
  assert.ok(vrm0.distanceTo(vrm1)<1e-10);
  assert.ok(vrm0.y<0);
});
test('smoothing has consistent convergence across rendering frame rates',()=>{
  const at30=1-Math.pow(1-dampFactor(.7,1/30),30);
  const at60=1-Math.pow(1-dampFactor(.7,1/60),60);
  assert.ok(Math.abs(at30-at60)<1e-10);
  assert.equal(dampFactor(0,1/60),1);
  assert.ok(dampFactor(.9,1/60)<dampFactor(.5,1/60));
});

test('blink falls back to common morph when unilateral definitions have no binds',()=>{
 const manager={getExpression:name=>({binds:name==='blink'?[{}]:[]})};
 const result=routeBlink({blink:1,blinkLeft:1,blinkRight:1},manager);
 assert.equal(result.blink,1);assert.equal(result.blinkLeft,0);
});
test('valid unilateral blink channels do not stack with common morph',()=>{
 const manager={getExpression:()=>({binds:[{}]})};
 const result=routeBlink({blink:1,blinkLeft:1,blinkRight:.2},manager);
 assert.deepEqual(result,{blink:0,blinkLeft:1,blinkRight:.2});
 assert.equal(scaleExpressions({blinkLeft:1},.2).blinkLeft,1);
});

test('blink routing drives actual VRM morph bindings to full closure',async()=>{
 const {VRMExpression,VRMExpressionManager,VRMExpressionMorphTargetBind}=await import('@pixiv/three-vrm');
 const manager=new VRMExpressionManager(),mesh={morphTargetInfluences:[0]};
 const common=new VRMExpression('blink');common.addBind(new VRMExpressionMorphTargetBind({primitives:[mesh],index:0,weight:1}));
 manager.registerExpression(common);manager.registerExpression(new VRMExpression('blinkLeft'));manager.registerExpression(new VRMExpression('blinkRight'));
 const result=routeBlink(scaleExpressions({blinkLeft:1,blinkRight:1},.2),manager);
 for(const [name,weight] of Object.entries(result))manager.setValue(name,weight);
 manager.update();assert.equal(mesh.morphTargetInfluences[0],1);
});
