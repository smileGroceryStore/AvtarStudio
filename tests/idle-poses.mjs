import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
const browser=await chromium.launch({channel:'msedge',headless:true}),base='http://127.0.0.1:8098';
const page=await browser.newPage({viewport:{width:500,height:650}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.goto(base);await page.waitForSelector('#idlePose');
const applied=page.waitForResponse(r=>r.url().endsWith('/api/avatar')&&r.request().method()==='POST');
await page.selectOption('#modelLibrary','personal-miku-v4x');await page.click('#useLibraryModel');assert.equal((await applied).status(),200);
for(const mode of ['3d','2d']){
 await page.request.post(base+'/api/control',{data:{action:'settings',settings:{avatarMode:mode}}});
 for(const pose of ['natural','sway']){
  await page.goto(base);await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('已就绪'));
  const saved=page.waitForResponse(r=>r.url().endsWith('/api/control')&&r.request().method()==='POST');await page.selectOption('#idlePose',pose);assert.equal((await saved).status(),200);
  const state=await(await page.request.get(base+'/api/state')).json();assert.equal(state.settings.idlePose,pose);assert.equal(state.running,false);
  await page.goto(base+'/widget');await page.waitForFunction(()=>document.documentElement.dataset.avatarReady==='true');await page.waitForTimeout(950);
  assert.equal(await page.locator('body').innerText(),'');await page.screenshot({path:`test-results/pose-${mode}-${pose}.png`,omitBackground:true});
 }
}
await page.goto(base);await page.reload();await page.waitForTimeout(300);assert.equal(await page.locator('#idlePose').inputValue(),'sway');
assert.deepEqual(errors,[]);await browser.close();console.log('2 poses x 2D/3D: settings persisted, rendered, pure widget, no JS errors: PASS');
