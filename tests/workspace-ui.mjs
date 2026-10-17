import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
const browser=await chromium.launch({channel:'msedge',headless:true}),page=await browser.newPage(),errors=[];
page.on('pageerror',e=>errors.push(e.message));
for(const [w,h] of [[1440,1000],[1072,900],[768,1000],[375,812]]){
 await page.setViewportSize({width:w,height:h});await page.goto('http://127.0.0.1:8098/');await page.waitForFunction(()=>document.documentElement.dataset.avatarReady==='true');
 assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
 if(w>900){const a=await page.locator('.adjustments').boundingBox(),b=await page.locator('.stage-column').boundingBox();assert.ok(a.x>b.x+b.width-1);}
 for(const tab of await page.getByRole('tab').all()){
  await tab.click();assert.equal(await tab.getAttribute('aria-selected'),'true');
  const id=await tab.getAttribute('aria-controls');assert.equal(await page.locator('#'+id).isVisible(),true);
 }
 await page.getByRole('tab',{name:'捕捉',exact:true}).click();await page.getByRole('tab',{name:'动作',exact:true}).click();
 await page.mouse.move(0,0);await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:`test-results/workspace-${w}.png`});
}
await page.getByRole('tab',{name:'动作',exact:true}).focus();await page.keyboard.press('ArrowRight');assert.equal(await page.getByRole('tab',{name:'画面',exact:true}).getAttribute('aria-selected'),'true');
await page.getByRole('tab',{name:'动作',exact:true}).click();await page.locator('#clothingClearance').uncheck();await page.waitForTimeout(700);await page.reload();await page.waitForFunction(()=>document.documentElement.dataset.avatarReady==='true');assert.equal(await page.locator('#clothingClearance').isChecked(),false);
await page.locator('#clothingClearance').check();
await page.emulateMedia({reducedMotion:'reduce'});await page.goto('http://127.0.0.1:8098/widget');await page.waitForFunction(()=>document.documentElement.dataset.avatarReady==='true');assert.equal(await page.locator('body').innerText(),'');assert.equal(await page.evaluate(()=>getComputedStyle(document.body).backgroundColor),'rgba(0, 0, 0, 0)');
assert.deepEqual(errors,[]);await browser.close();console.log('Workspace: responsive layout, tabs, keyboard, saved clearance, transparent widget PASS');
