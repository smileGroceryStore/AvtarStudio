import test from 'node:test';
import assert from 'node:assert/strict';
import {projectArm} from '../frontend/arms2d.js';
for(const side of ['left','right'])test(`${side}: bent elbow and forward wrist stay in front`,()=>{
 const pose={armPoints:{[side]:{points:[[0,0,0],[.05,-.25,.02],[-.15,-.08,.24]],shoulderSpan:.4}}};
 const a=projectArm(pose,side);
 assert.ok(a.depth>0);assert.ok(a.wrist[1]<a.elbow[1]);assert.ok(a.wrist[0]<a.shoulder[0]);
 const back=projectArm({armPoints:{[side]:{...pose.armPoints[side],points:[[0,0,0],[.05,-.25,-.1],[-.15,-.08,-.24]]}}},side);
 assert.ok(back.depth<0);
});
test('anatomical left appears on viewer right and only CSS handles mirroring',()=>{
 assert.ok(projectArm(null,'left').shoulder[0]>200);
 assert.ok(projectArm(null,'right').shoulder[0]<200);
});
test('fallback uses forearm direction, not just shoulder rotation',()=>{
 const a=projectArm({armDirections:{leftUpperArm:[0,-1,0],leftLowerArm:[-.8,.3,.5]}},'left');
 assert.ok(a.wrist[1]<a.elbow[1]);assert.ok(a.depth>0);
});
