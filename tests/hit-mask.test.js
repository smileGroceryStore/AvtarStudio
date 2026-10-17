import test from 'node:test';
import assert from 'node:assert/strict';
import {encodeAlphaMask} from '../frontend/hit-mask.js';
test('alpha masks preserve holes, alpha cutoff, origin and mirror direction',()=>{
 const rgba=new Uint8Array(2*2*4);[0,23,24,255].forEach((a,i)=>rgba[i*4+3]=a);
 assert.equal(encodeAlphaMask(rgba,2,2).pixels,'0011');
 assert.equal(encodeAlphaMask(rgba,2,2,{flipY:true}).pixels,'1100');
 rgba[7]=255;
 assert.equal(encodeAlphaMask(rgba,2,2,{mirror:true}).pixels,'1011');
});
