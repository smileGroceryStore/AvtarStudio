import test from 'node:test';
import assert from 'node:assert/strict';
import {clothingClearance} from '../frontend/clothing-clearance.js';
test('hanging arms get symmetric clearance without changing length',()=>{
 const l=clothingClearance([.12,-1,.015],'left'),r=clothingClearance([-.12,-1,.015],'right');
 assert.ok(l[0]>.19&&r[0]<-.19);assert.ok(Math.abs(l[0]+r[0])<1e-9);assert.ok(Math.abs(Math.hypot(...l)-1)<1e-9);
});
test('raised arms, forward reaches, outward arms and disabled setting stay intact',()=>{
 for(const v of [[.8,.2,.1],[.1,-.6,.8],[.5,-.8,0]])assert.deepEqual(clothingClearance(v,'left'),v);
 const v=[0,-1,0];assert.deepEqual(clothingClearance(v,'left',false),v);
});
test('clearance fades continuously into ordinary tracking',()=>{
 for(let y=-.95;y<-.45;y+=.002){const a=clothingClearance([.1,y,.2],'left'),b=clothingClearance([.1,y+.001,.2],'left');assert.ok(Math.hypot(...a.map((v,i)=>v-b[i]))<.01);}
});
