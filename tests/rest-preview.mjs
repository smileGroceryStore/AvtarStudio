import {chromium} from '@playwright/test';
const browser=await chromium.launch({channel:'msedge',headless:true});
const page=await browser.newPage({viewport:{width:500,height:650}});
await page.request.post('http://127.0.0.1:8080/api/control',{data:{action:'settings',settings:{avatarMode:'3d'}}});
await page.goto('http://127.0.0.1:8080/widget');
await page.waitForFunction(()=>document.documentElement.dataset.avatarReady==='true');
await page.waitForTimeout(1400);
await page.screenshot({path:'test-results/relaxed-3d.png'});
await browser.close();
