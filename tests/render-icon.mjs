import { chromium } from '@playwright/test';
import fs from 'node:fs/promises';
const svg=await fs.readFile('frontend/app-icon.svg','utf8');
const browser=await chromium.launch({channel:'msedge',headless:true});
const page=await browser.newPage({viewport:{width:512,height:512},deviceScaleFactor:1});
await page.setContent('<html><body style="margin:0;background:transparent">'+svg.replace('viewBox=', 'width="512" height="512" viewBox=')+'</body></html>');
await page.screenshot({path:'desktop-assets/app.png',omitBackground:true});
await fs.copyFile('frontend/app-icon.svg','desktop-assets/app.svg');
await browser.close();
