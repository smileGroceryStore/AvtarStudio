import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
const browser=await chromium.launch({channel:'msedge',headless:true});const page=await browser.newPage({viewport:{width:500,height:650}}),errors=[];
page.on('pageerror',e=>errors.push(e.message));
await page.addInitScript(()=>{const Native=window.WebSocket;window.testSockets=[];window.WebSocket=class extends Native{constructor(...a){super(...a);window.testSockets.push(this);}}});
await page.request.post('http://127.0.0.1:8098/api/control',{data:{action:'settings',settings:{avatarMode:'3d',mirror:false}}});
await page.goto('http://127.0.0.1:8098/widget');await page.waitForFunction(()=>document.documentElement.dataset.avatarReady==='true');
await page.evaluate(async()=>{const socket=window.testSockets[0],handler=socket.onmessage;socket.onmessage=e=>{if(!e.isTrusted)handler(e);};window.wristState=await(await fetch('/api/state')).json();wristState.running=true;wristState.rig={head:[0,0,0],hands:{left:{palm:{direction:[0,1,0],normal:[0,0,1]},fingers:{}}},pose:{armDirections:{leftUpperArm:[.8,-.2,.1],leftLowerArm:[0,1,.2]}}};window.wristTimer=setInterval(()=>socket.dispatchEvent(new MessageEvent('message',{data:JSON.stringify(wristState)})),20);});
for(const z of [1,-1]){await page.evaluate(z=>wristState.rig.hands.left.palm.normal=[0,0,z],z);await page.waitForTimeout(1000);await page.screenshot({path:`test-results/wrist-palm-${z}.png`,omitBackground:true});}
assert.deepEqual(errors,[]);await browser.close();console.log('Rendered palm front/back with raised forearm, no JS errors: PASS');
