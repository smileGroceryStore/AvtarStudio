import {idleArmDirections} from './idle-poses.js';
import { projectArm } from './arms2d.js';
// Original layered SVG character. No external artwork or runtime required.
export function initAvatar2D({viewport,output,widget}) {
 const host=document.createElement('div');host.className='avatar-2d';host.hidden=true;
 host.innerHTML=`<svg viewBox="0 0 400 560" role="img" aria-label="2D 猫耳伙伴"><defs><linearGradient id="hair" x2=".2" y2="1"><stop stop-color="#384c61"/><stop offset="1" stop-color="#192b41"/></linearGradient></defs>
 <g id="pet-root" stroke="#233347" stroke-width="5" stroke-linejoin="round" stroke-linecap="round">
 <g id="pet-arms-back"></g>
 <g id="pet-body"><path id="pet-legs" d="M151 405l-5 66q18 15 37 0l10-60M210 411l7 60q20 15 38 0l-5-66" fill="#405369"/><path id="pet-shoes" d="M145 465q-24 13-17 30h58v-29M216 466v29h58q7-17-20-30" fill="#f4f7fb"/>
 <path d="M161 293q39-18 78 0l19 118q-58 24-116 0z" fill="var(--pet-accent)"/><path d="M165 294l35 37 35-37M178 324v29m44-29v29" fill="none" stroke="#f5fffd"/><path d="M171 365h58l-5 27h-48z" fill="#ffffff" fill-opacity=".26" stroke-width="3"/><path d="M190 289v17q10 10 20 0v-17" fill="#ffe3d4"/></g>
 <g id="pet-arms-front"></g>
 <g id="pet-head"><g id="pet-accessory-back"></g><path id="pet-hair-back" d="M104 196Q76 123 111 63l56 47q42-13 76 0l47-49q31 65 8 135l-9 83q-86 41-178 0z" fill="url(#hair)"/>
 <path id="pet-ears-inner" d="M110 84l37 31-42 23zM282 84l-32 32 40 20z" fill="var(--pet-accent)" stroke-width="3"/>
 <path d="M107 179q0-70 93-70t93 70l-9 55q-8 62-84 65t-85-65z" fill="#ffe8db"/>
 <path d="M102 192q-3-90 91-88q104-8 105 95l-39-30-5 24-45-49-18 43-19-26-24 39-10-26-31 32z" fill="url(#hair)"/>
 <path d="M116 200l-7 63 28-21M285 199l8 64-28-21" fill="url(#hair)"/>
 <g id="pet-eye-left"><ellipse cx="158" cy="224" rx="16" ry="22" fill="#31aeb0"/><ellipse cx="160" cy="225" rx="8" ry="16" fill="#223448" stroke="none"/><circle cx="153" cy="216" r="5" fill="white" stroke="none"/></g>
 <g id="pet-eye-right"><ellipse cx="242" cy="224" rx="16" ry="22" fill="#31aeb0"/><ellipse cx="240" cy="225" rx="8" ry="16" fill="#223448" stroke="none"/><circle cx="237" cy="216" r="5" fill="white" stroke="none"/></g>
 <path id="pet-lid-left" d="M143 224q15 10 30 0" fill="none" opacity="0"/><path id="pet-lid-right" d="M227 224q15 10 30 0" fill="none" opacity="0"/>
 <path d="M140 205q15-9 31 0m58 0q15-9 31 0" fill="none" stroke-width="4"/><ellipse cx="135" cy="251" rx="17" ry="7" fill="#f1a5a0" stroke="none" opacity=".65"/><ellipse cx="265" cy="251" rx="17" ry="7" fill="#f1a5a0" stroke="none" opacity=".65"/>
 <ellipse id="pet-mouth" cx="200" cy="266" rx="10" ry="3" fill="#a64e63" stroke-width="3"/><path d="M200 240l-3 5h5" fill="none" stroke="#d4a18e" stroke-width="2"/>
 <g id="pet-accessory-front"></g><path d="M114 170l20 9m-18-19 20 9" stroke="var(--pet-accent)" stroke-width="6"/></g></g></svg>`;
 viewport.append(host);
 const baseHair=host.querySelector('#pet-hair-back').getAttribute('d');
 const baseInner=host.querySelector('#pet-ears-inner').getAttribute('d');
 let lastStyle='';
 function styleCharacter(style){
  if(style===lastStyle)return;lastStyle=style;
  const hair=host.querySelector('#pet-hair-back'),inner=host.querySelector('#pet-ears-inner');
  const back=host.querySelector('#pet-accessory-back'),front=host.querySelector('#pet-accessory-front');
  hair.setAttribute('d',baseHair);inner.setAttribute('d',baseInner);back.innerHTML='';front.innerHTML='';
  const stops=host.querySelectorAll('#hair stop');
  const colors=style==='rose'?['#97627e','#53354f']:style==='blue'?['#c3e5f7','#527893']:['#384c61','#192b41'];
  stops.forEach((stop,i)=>stop.setAttribute('stop-color',colors[i]));
  if(style==='rose'){
   hair.setAttribute('d','M104 196Q87 114 135 104Q200 78 265 104Q310 116 298 196l-9 83q-86 41-178 0z');
   inner.setAttribute('d','M139 107Q83 -12 122 12Q160 34 169 100M231 100Q241 27 278 13Q309 -5 265 107');
   inner.setAttribute('stroke-width','8');
   front.innerHTML='<path d="M262 175l-25-14v30zM262 175l25-14v30z" fill="#efadca"/><circle cx="262" cy="175" r="6" fill="#fff0f7"/>';
  }else if(style==='blue'){
   hair.setAttribute('d','M104 196Q78 100 139 95Q200 65 263 96Q315 115 298 196l-9 83q-86 41-178 0z');
   inner.setAttribute('d','M103 160l-23-40v85l21 14M297 160l23-40v85l-21 14');
   back.innerHTML='<path d="M101 199v-52q0-75 99-75t99 75v52" fill="none" stroke="#97c7f0" stroke-width="14"/>';
   front.innerHTML='<rect x="89" y="185" width="23" height="57" rx="9" fill="#97c7f0"/><rect x="288" y="185" width="23" height="57" rx="9" fill="#97c7f0"/><path d="M301 240q-3 31-51 31" fill="none" stroke="#97c7f0"/><circle cx="247" cy="271" r="7" fill="#d1faff"/>';
  }
  if(style!=='rose')inner.setAttribute('stroke-width','3');
 }
 const armState={};
 for(const side of ['left','right']){
  const group=document.createElementNS('http://www.w3.org/2000/svg','g');group.id='pet-arm-'+side;
  group.innerHTML='<path class="arm-outline" fill="none" stroke-width="33"/><path class="arm-sleeve" fill="none" stroke="var(--pet-accent)" stroke-width="24"/><path class="forearm-outline" fill="none" stroke-width="28"/><path class="forearm" fill="none" stroke="#ffe3d4" stroke-width="20"/><ellipse class="arm-hand" rx="14" ry="16" fill="#ffe3d4"/>';
  host.querySelector('#pet-arms-front').append(group);
  armState[side]={group,points:null,depth:0,front:true};
 }
 const el=id=>host.querySelector('#pet-'+id),clamp=(n,a,b)=>Math.max(a,Math.min(b,n));
 let state={},active=false,values={x:0,y:0,z:0,blinkL:0,blinkR:0,mouth:0,left:0,right:0},last=performance.now();
 function frame(now){requestAnimationFrame(frame);const dt=Math.min(.1,(now-last)/1000);last=now;if(!active)return;
  const s=state.settings||{},r=state.rig||{},e=r.expressions||{},head=r.head||[0,0,0],strength=s.expression??1.3;
  const idleBlink=now%4800>4650?1:0;
  const target={x:clamp(head[0]*(s.sensitivity??1),-.5,.5),y:clamp(head[1],-.4,.4),z:clamp(head[2],-.4,.4),blinkL:clamp((e.blinkLeft??e.blink??idleBlink),0,.95),blinkR:clamp((e.blinkRight??e.blink??idleBlink),0,.95),mouth:clamp((e.aa??0)*strength,0,1),left:0,right:0};

  const a=1-Math.exp(-dt*(5+20*(1-(s.smoothing??.55))));for(const k of Object.keys(values)){const speed=k.startsWith('blink')?1-Math.exp(-dt*40):a;values[k]+=(target[k]-values[k])*speed;}
  el('head').setAttribute('transform',`translate(${values.x*28} ${values.y*18}) rotate(${values.z*35} 200 290)`);
  for(const [side,cx,key] of [['left',158,'blinkL'],['right',242,'blinkR']]){
   el('eye-'+side).setAttribute('transform',`translate(${cx} 224) scale(1 ${Math.max(.05,1-values[key])}) translate(${-cx} -224)`);
   el('eye-'+side).setAttribute('opacity',values[key]>.8?'0':'1');
   el('lid-'+side).setAttribute('opacity',values[key]>.8?'1':'0');
  }
  el('mouth').setAttribute('ry',String(3+values.mouth*13));
  for(const side of ['left','right']){
   const pose=state.running?(s.body===false?null:r.pose):{armDirections:idleArmDirections(s.idlePose,now/1000)};
   const projected=projectArm(pose,side),arm=armState[side];
   const targetPoints=[...projected.shoulder,...projected.elbow,...projected.wrist];
   if(!arm.points)arm.points=targetPoints.slice();
   const armAlpha=projected.tracked?a:1-Math.exp(-dt*8);
   arm.points=arm.points.map((v,i)=>v+(targetPoints[i]-v)*armAlpha);arm.depth+=(projected.depth-arm.depth)*armAlpha;
   // Hysteresis stops noisy depth from flickering the arm through the torso.
   const front=!projected.tracked || (arm.front?arm.depth>-.10:arm.depth>-.03);
   if(front!==arm.front){el(front?'arms-front':'arms-back').append(arm.group);arm.front=front;}
   arm.group.dataset.layer=front?'front':'back';
   const [sx,sy,ex,ey,wx,wy]=arm.points;
   for(const cls of ['arm-outline','arm-sleeve'])arm.group.querySelector('.'+cls).setAttribute('d',`M${sx} ${sy} L${ex} ${ey}`);
   for(const cls of ['forearm-outline','forearm'])arm.group.querySelector('.'+cls).setAttribute('d',`M${ex} ${ey} L${wx} ${wy}`);
   const hand=arm.group.querySelector('.arm-hand');hand.setAttribute('cx',wx);hand.setAttribute('cy',wy);
   arm.group.setAttribute('transform',`translate(${values.x*7} ${Math.sin(now/650)*1.5})`);
  }
  el('body').setAttribute('transform',`translate(${values.x*7} ${Math.sin(now/650)*1.5})`);
  el('root').setAttribute('transform',`translate(200 280) scale(${widget?1:s.zoom??1}) translate(-200 ${-280+(widget?0:(s.height??0)*100)})`);
 }
 requestAnimationFrame(frame);
 function hitTest(x,y){
  if(!active||host.hidden)return false;
  for(const shape of host.querySelectorAll('path,ellipse,circle,rect,polygon,line,polyline')){
   const matrix=shape.getScreenCTM();if(!matrix)continue;
   let visible=true;
   for(let node=shape;node&&node!==host;node=node.parentElement){const s=getComputedStyle(node);if(s.display==='none'||s.visibility==='hidden'||Number(s.opacity)===0){visible=false;break;}}
   if(!visible)continue;
   const p=new DOMPoint(x,y).matrixTransform(matrix.inverse()),style=getComputedStyle(shape);
   if(style.fill!=='none'&&Number(style.fillOpacity)>0&&shape.isPointInFill(p))return true;
   if(style.stroke!=='none'&&Number(style.strokeOpacity)>0&&shape.isPointInStroke(p))return true;
  }
  return false;
 }
 return {hitTest,setState(next,visible){state=next;styleCharacter(next.settings?.petColor||'mint');active=visible;host.hidden=!visible;host.style.setProperty('--pet-accent',({mint:'#79d8c1',rose:'#efadca',blue:'#97c7f0'})[next.settings?.petColor]||'#79d8c1');if(output)viewport.classList.toggle('mirrored',!!next.settings?.mirror);}};
}
