import test from 'node:test';
import assert from 'node:assert/strict';
import {idlePoses,idleArmDirections,idleBodyPose} from '../frontend/idle-poses.js';
test('only natural and animated sway remain',()=>{
 assert.deepEqual(idlePoses.map(p=>p[0]),['natural','sway']);
 assert.notDeepEqual(idleArmDirections('sway',0),idleArmDirections('sway',1));
 assert.deepEqual(idleArmDirections('natural',0),idleArmDirections('natural',1));
 assert.equal(idleBodyPose().roll,0);assert.equal(idleBodyPose().lowering,0);
});
