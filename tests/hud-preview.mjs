import {chromium} from '@playwright/test';
const browser=await chromium.launch({channel:'msedge',headless:true});
const page=await browser.newPage({viewport:{width:1440,height:1060},deviceScaleFactor:1});
await page.goto('http://127.0.0.1:8080/?desktop=1');
await page.locator('#modelStatus').filter({hasText:'已加载'}).waitFor({timeout:30000});
await page.screenshot({path:'test-results/hud-final-preview.png',fullPage:true});
console.log(await page.locator('#avatarName').textContent(),await page.locator('.version').textContent());
await browser.close();
