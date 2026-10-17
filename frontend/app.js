import { installModelLibrary } from './model-library.js';
import './style.css';
import './minimal.css';
import './workspace.css';
import {installLayout,labelButton} from './ui-layout.js';
import { initAvatar } from './avatar.js';
import { initAvatar2D } from './avatar2d.js';
import { attachWidgetDrag } from './widget-drag.js';

const widget = location.pathname === '/widget';
const output = location.pathname === '/output' || widget;
const desktop = new URLSearchParams(location.search).get('desktop') === '1';
const $ = id => document.getElementById(id);
if(!output)installLayout();
if(desktop){document.documentElement.classList.add('desktop-mode');document.querySelector('.version').textContent='桌面版';document.querySelector('.local-tag').textContent='本机运行 · 支持桌面挂件';}
if (output) {
  document.documentElement.classList.add('output-mode');
  document.body.append($('viewport'));
  if(!widget){const error=document.createElement('div');error.id='outputError';error.hidden=true;document.body.append(error);}
}
if(widget){
  document.documentElement.classList.add('widget-mode');
  attachWidgetDrag([$('viewport')],()=>window.pywebview?.api,(x,y)=>activeMode==='2d'?avatar2d.hitTest(x,y):avatar3d.hitTest(x,y));
  document.addEventListener('contextmenu',event=>{
    event.preventDefault();
    const api=window.pywebview?.api;
    if(api?.show_widget_menu)api.show_widget_menu().catch(error=>console.error(error));
  });
}
const labels = {ready:'已就绪 · 点击开始捕捉',starting:'正在启动摄像头与追踪模型…',stopping:'正在释放摄像头…',tracking:'正在跟随你的动作',calibrating:'校准中 · 请正对镜头，保持自然表情', 'no-face':'未检测到脸部 · 请调整取景',error:'捕捉未启动'};
let state = null, ready = false, ws, toastTimer, saveTimer, modelVersion = null;
const avatar3d = initAvatar({output, widget, onLoad:(name)=> {ready=true;document.documentElement.dataset.avatarReady='true';if(!output) $('modelStatus').textContent=state?.settings?.avatarMode==='2d'?'已加载 · 2D 动态伙伴':name;}, onError:message=>notify(message,true)});

const avatar2d=initAvatar2D({viewport:$('viewport'),output,widget});
let activeMode='3d';
const avatar={load:url=>avatar3d.load(url),setState(next){
  if(next.testBlink)next={...next,rig:{...next.rig,expressions:{...next.rig?.expressions,blink:1,blinkLeft:1,blinkRight:1}}};
  activeMode=next.settings?.avatarMode || '3d';
  $('c').hidden=activeMode==='2d';
  avatar2d.setState(next,activeMode==='2d');
  avatar3d.setState(next);
  if(activeMode==='2d') {ready=true;document.documentElement.dataset.avatarReady='true';}
}};

function notify(message, error=false){
  if(widget){if(error)console.error(message);return;}
  if(output){const el=$('outputError');el.textContent=message;el.hidden=!error;return;}
  $('toast').textContent=message; $('toast').classList.toggle('error',error); $('toast').hidden=false;
  clearTimeout(toastTimer); toastTimer=setTimeout(()=>$('toast').hidden=true,error?10000:3500);
}
async function command(action, extra={}){
  const response=await fetch('/api/control',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action,...extra})});
  if(!response.ok)throw new Error(await response.text());
  return response.json();
}
function update(next){
  state=next; avatar.setState(next);
  if(modelVersion!==next.avatarVersion && next.hasAvatar){modelVersion=next.avatarVersion;avatar.load(`/api/avatar?v=${modelVersion}`);}

  if(output)return;
  $('avatarName').textContent=next.avatarName;
  $('empty').hidden=next.hasAvatar || activeMode==='2d';
  if(activeMode==='2d') $('modelStatus').textContent='已加载 · 2D 动态伙伴';
  $('status').textContent=next.error || labels[next.status] || next.status;
  $('statusDot').style.background=next.status==='tracking'?'#22c55e':next.error?'#f97316':'#22d3ee';
  $('fps').textContent=`${next.fps.toFixed(1)} FPS`;
  $('hudFps').replaceChildren(document.createTextNode(next.fps.toFixed(1)),Object.assign(document.createElement('small'),{textContent:' FPS'}));
  $('hudLatency').replaceChildren(document.createTextNode(next.running?Number(next.inferenceMs??0).toFixed(0):'—'),Object.assign(document.createElement('small'),{textContent:' MS'}));
  $('fpsMeter').style.width=Math.min(100,next.fps/30*100)+'%';
  $('latencyMeter').style.width=(next.running?Math.min(100,(next.inferenceMs??0)/100*100):0)+'%';
  const stages=next.stageMs||{},camera=next.camera||{};
  $('fps').title=`并行推理 ${next.inferenceMs??0} ms；面部 ${stages.face??0} ms / 身体 ${stages.pose??0} ms / 手部 ${stages.hands??0} ms`;
  $('trackingInfo').textContent=next.running?`相机 ${camera.width||'—'}×${camera.height||'—'} · ${camera.fps||'—'} FPS；并行处理 ${Number(next.inferenceMs||0).toFixed(0)} ms；采集后 ${Number(next.processingAgeMs||0).toFixed(0)} ms`:'开启捕捉后显示相机帧率与处理耗时';

  labelButton($('capture'),next.running?'停止捕捉':'开始捕捉',next.running?'stop':'play');
  $('capture').classList.toggle('active',next.running);
  $('calibrate').disabled=!next.running;
  const eye=next.rig.eyeSignal||{};
  $('blinkStatus').textContent=next.testBlink?'模型闭眼测试中':next.running?`闭眼信号：左 ${Math.round((eye.closedLeft||0)*100)}% · 右 ${Math.round((eye.closedRight||0)*100)}%`:'闭眼测试无需开启摄像头';
  $('cameraIndex').disabled=next.running;
  $('cameraIndex').value=String(next.cameraIndex);
  $('avatarFile').disabled=next.running;
  $('importAvatar').disabled=next.running;
  $('faceTag').textContent=`面部 · ${next.status==='tracking'?'已跟随':next.status==='calibrating'?'校准中':'待机'}`;
  $('bodyTag').textContent=`上半身 · ${next.rig.pose?.leftUpperArm || next.rig.pose?.rightUpperArm?'已跟随':'待机'}`;
  $('handTag').textContent=`手腕/手指 · ${next.settings.hands===false?'已关闭':next.rig.hands?.left || next.rig.hands?.right?'已跟随':next.running?'等待双手进入画面':'待机'}`;
  for(const [key,value] of Object.entries(next.settings)){
    const el=$(key);if(!el || pendingSettings.has(key) || inFlightSettings.has(key))continue;
    if(el.type==='checkbox')el.checked=value;else el.value=value;
    showValue(key,value);
  }
  for(const button of document.querySelectorAll('[data-preset]')){const active=button.dataset.preset===(next.settings.hands&&next.settings.body?'full':next.settings.body?'body':!next.settings.hands?'chat':'');button.setAttribute('aria-pressed',String(active));}
  const stage=$('stage');
  stage.classList.toggle('green',next.settings.background==='green');
  stage.classList.toggle('transparent',next.settings.background==='transparent');
  stage.classList.toggle('mirrored',next.settings.mirror);
  cameraPreview();
}
function showValue(key,value){const el=$(key+'Value');if(el)el.textContent=key==='smoothing'?`${Math.round(value*100)}%`:key==='height'?Number(value).toFixed(2):`${Number(value).toFixed(2)}×`;}
function cameraPreview(){
  const visible=$('showCamera').checked && state?.running;
  $('cam').hidden=!visible; $('cameraPlaceholder').hidden=visible;
  if(visible && !$('cam').hasAttribute('src'))$('cam').src='/camera?t='+Date.now();
  if(!visible)$('cam').removeAttribute('src');
}
const pendingSettings=new Map();
const inFlightSettings=new Set();
let saving=false;
async function saveSettings(){
  if(saving)return;
  saving=true;
  try{while(pendingSettings.size){const batch=Object.fromEntries(pendingSettings);pendingSettings.clear();for(const key of Object.keys(batch))inFlightSettings.add(key);await command('settings',{settings:batch});inFlightSettings.clear();}}
  catch(e){notify('设置保存失败：'+e.message,true);}
  finally{saving=false;inFlightSettings.clear();}
}
function connect(){
  ws=new WebSocket(`${location.protocol==='https:'?'wss':'ws'}://${location.host}/ws`);
  ws.onopen=()=>{if(!output)$('connection').textContent='本地服务已连接';else notify('',false);};
  ws.onmessage=e=>{try{update(JSON.parse(e.data));}catch(err){console.error(err);}};
  ws.onclose=()=>{avatar.setState({rig:{},settings:state?.settings||{}});if(!output){$('connection').textContent='连接中断 · 重连中';$('status').textContent='本地服务未连接';}else notify('本地服务连接已中断，正在重连…',true);setTimeout(connect,1500);};
}
if(!output){
  const attachNative=()=>{if(!window.pywebview?.api)return;for(const [id,action] of [['desktopPet','open_widget'],['desktopHideConsole','collapse_console'],['desktopBackground','run_background']]){const button=$(id);button.disabled=false;button.onclick=async()=>{try{await window.pywebview.api[action]();}catch(e){notify('桌面挂件打开失败：'+e.message,true);}};}};
  window.addEventListener('pywebviewready',attachNative);attachNative();
  for(const button of document.querySelectorAll('[data-preset]'))button.onclick=async()=>{try{const settings=button.dataset.preset==='chat'?{body:false,hands:false,smoothing:.4}:button.dataset.preset==='body'?{body:true,hands:false,smoothing:.55}:{body:true,hands:true,smoothing:.55};await command('settings',{settings});notify('已切换到'+button.textContent.trim()+'模式');}catch(e){notify(e.message,true);}};
  installModelLibrary({command,update,notify,getState:()=>state});
  $('importAvatar').onclick=()=>$('avatarFile').click();
  $('naturalMotion').onclick=async()=>{try{await command('settings',{settings:{body:true,hands:true,smoothing:.4,sensitivity:1,expression:1.2}});notify('已应用自然跟随参数：平滑 40%，上半身与手腕/手指追踪已开启。');}catch(e){notify(e.message,true);}};
  $('capture').onclick=async()=>{const button=$('capture');button.disabled=true;try{if(!ready && !state?.running)throw new Error('请等待角色加载完成');update(await command(state?.running?'stop':'start',{cameraIndex:Number($('cameraIndex').value)}));}catch(e){notify(e.message,true);}finally{button.disabled=false;}};
  $('testBlink').onclick=async()=>{try{await command('test-blink');notify('正在测试模型闭眼。若角色能闭眼，说明模型通道可用。');}catch(e){notify(e.message,true);}};
  $('calibrate').onclick=async()=>{try{await command('calibrate');notify('请保持自然表情，正对摄像头约 1 秒。');}catch(e){notify(e.message,true);}};
  $('avatarFile').onchange=async e=>{const file=e.target.files[0];if(!file)return;if(file.size>100*1024*1024){notify('文件超过 100 MB',true);return;}try{notify('正在导入角色…');const response=await fetch('/api/avatar',{method:'POST',headers:{'Content-Type':'application/octet-stream','X-Avatar-Name':encodeURIComponent(file.name)},body:file});if(!response.ok)throw new Error(await response.text());update(await response.json());notify('角色已保存，下次启动仍可使用。');}catch(error){notify(error.message,true);}finally{e.target.value='';}};
  for(const key of ['blinkSensitivity','sensitivity','expression','smoothing','zoom','height','background','mirror','body','hands','idlePose','avatarMode','petColor','clothingClearance']){
    $(key).addEventListener('input',()=>{const el=$(key), value=el.type==='checkbox'?el.checked:el.type==='range'?Number(el.value):el.value;showValue(key,value);pendingSettings.set(key,value);if(state){state.settings[key]=value;avatar.setState(state);}clearTimeout(saveTimer);saveTimer=setTimeout(saveSettings,180);});
  }
  $('reset').onclick=()=>{for(const [key,value] of Object.entries({blinkSensitivity:1,sensitivity:1,expression:1.3,smoothing:.55,zoom:1,height:0,background:'studio',mirror:false,body:true,hands:true,clothingClearance:true}))pendingSettings.set(key,value);saveSettings();notify('已恢复默认参数');};
  $('copy').onclick=async()=>{try{await navigator.clipboard.writeText(location.origin+'/output');notify('OBS 地址已复制。浏览器来源设为 1280 × 720。');}catch{notify('OBS 地址：'+location.origin+'/output');}};
  $('showCamera').onchange=cameraPreview;
}
fetch('/api/state').then(r=>{if(!r.ok)throw new Error('本地服务不可用');return r.json();}).then(update).catch(e=>notify(e.message,true));
connect();
