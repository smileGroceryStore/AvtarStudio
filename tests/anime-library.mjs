import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
import {models} from '../frontend/model-library.js';
const browser=await chromium.launch({channel:'msedge',headless:true});
const page=await browser.newPage({viewport:{width:500,height:650}}),errors=[];
page.on('pageerror',e=>errors.push(e.message));
const base='http://127.0.0.1:8098';
const personal=await(await page.request.get(base+'/api/library')).json();assert.equal(personal.length,2);
for(const model of personal){
 await page.goto(base);await page.waitForFunction(()=>document.querySelector('#modelLibrary').options.length===12);
 await page.selectOption('#modelLibrary',model.id);
 const applied=page.waitForResponse(r=>r.url().endsWith(model.file?'/api/avatar':'/api/control')&&r.request().method()==='POST');
 const modeApplied=model.file?page.waitForResponse(r=>r.url().endsWith('/api/control')&&r.request().method()==='POST'):null;
 await page.click('#useLibraryModel');const response=await applied;assert.equal(response.status(),200);
 if(modeApplied)await modeApplied;
 const state=await(await page.request.get(base+'/api/state')).json();
 if(model.file){assert.equal(state.avatarName,model.name+'.vrm');assert.equal(state.settings.avatarMode,'3d');}
 else {assert.equal(state.settings.avatarMode,'2d');assert.equal(state.settings.petColor,model.color);}
 await page.goto(base+'/widget');await page.waitForFunction(()=>document.documentElement.dataset.avatarReady==='true');await page.waitForTimeout(850);
 assert.equal(await page.locator('body').innerText(),'');
 if(model.id==='personal-miku-v4x')assert.equal(Number(await page.locator('#c').getAttribute('data-added-hair-joints')),14);
 if(model.color){assert.equal(await page.locator('.avatar-2d').isVisible(),true);if(model.id!=='cat')assert.ok(await page.locator('#pet-accessory-front > *').count()>0);}
 await page.screenshot({path:`test-results/library-${model.id}.png`,omitBackground:true});
 console.log(model.name+': loaded');
}
assert.deepEqual(errors,[]);await browser.close();console.log('2 personal anime/game models, UI switching, pure widget, no JS errors: PASS');
