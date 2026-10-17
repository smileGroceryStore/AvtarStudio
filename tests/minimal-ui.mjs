import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
const browser=await chromium.launch({channel:'msedge',headless:true});const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
for(const [w,h] of [[1440,1000],[1072,900],[768,1000],[375,812]]){
 await page.setViewportSize({width:w,height:h});await page.goto('http://127.0.0.1:8098/');await page.waitForFunction(()=>document.documentElement.dataset.avatarReady==='true');
 assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
 assert.equal(await page.locator('.stage-grid').isVisible(),false);
 await page.screenshot({path:`test-results/minimal-${w}.png`});
}
await page.emulateMedia({reducedMotion:'reduce'});await page.goto('http://127.0.0.1:8098/widget');await page.waitForFunction(()=>document.documentElement.dataset.avatarReady==='true');
assert.equal(await page.locator('body').innerText(),'');assert.equal(await page.evaluate(()=>getComputedStyle(document.body).backgroundColor),'rgba(0, 0, 0, 0)');
assert.deepEqual(errors,[]);await browser.close();console.log('Minimal UI: 4 viewport sizes, no overflow, pure transparent widget, no JS errors PASS');
