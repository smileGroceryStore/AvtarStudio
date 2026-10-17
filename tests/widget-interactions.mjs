import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
const browser=await chromium.launch({channel:'msedge',headless:true});
const page=await browser.newPage({viewport:{width:420,height:620},deviceScaleFactor:1.5}),errors=[];
page.on('pageerror',e=>errors.push(e.message));
await page.addInitScript(()=>{window.widgetMoves=[];window.pywebview={api:{widget_position:async()=>({x:80,y:140}),move_widget:async(x,y)=>{window.widgetMoves.push([x,y]);},save_widget_position:async()=>{window.widgetSaved=true;},show_widget_menu:async()=>{window.contextOpened=true;}}};});
async function drag(x,y,dx,dy){await page.mouse.move(x,y);await page.mouse.down();await page.waitForTimeout(100);await page.mouse.move(x+dx,y+dy,{steps:8});await page.mouse.up();await page.waitForTimeout(250);}
for(const mode of ['3d','2d'])for(const mirror of [false,true]){
 await page.request.post('http://127.0.0.1:8098/api/control',{data:{action:'settings',settings:{avatarMode:mode,mirror}}});
 await page.goto('http://127.0.0.1:8098/widget');await page.waitForFunction(()=>document.documentElement.dataset.avatarReady==='true');await page.waitForTimeout(700);
 assert.equal(await page.locator('#widgetGrip,#widgetTools,#outputError,.pywebview-drag-region').count(),0);
 assert.equal(await page.locator('body').innerText(),'');
 await drag(5,5,60,50);assert.equal(await page.evaluate(()=>window.widgetMoves.length),0,`${mode} mirror=${mirror}: blank corner must not drag`);
 await drag(30,310,60,50);assert.equal(await page.evaluate(()=>window.widgetMoves.length),0,`${mode} mirror=${mirror}: blank side must not drag`);
 await drag(210,310,160,60);assert.deepEqual(await page.evaluate(()=>window.widgetMoves.at(-1)),[240,200],`${mode} mirror=${mirror}: character must drag even beyond silhouette`);
 assert.equal(await page.evaluate(()=>window.widgetSaved),true);
 await page.mouse.click(200,250,{button:'right'});await page.waitForFunction(()=>window.contextOpened===true);
}
assert.deepEqual(errors,[]);await browser.close();console.log('3D / 2D, mirrored, high DPI: blank ignored, silhouette drags, pointer capture, native menu PASS');
