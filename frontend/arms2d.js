import { relaxedArmDirections } from './rest-pose.js';
// Project anatomical arm joints into the character, retaining depth for layering.
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
export function projectArm(pose,side){
 const shoulder=side==='left'?[243,313]:[157,313];
 const entry=pose?.armPoints?.[side],points=entry?.points;
 if(points?.length===3 && points.every(p=>p?.length===3 && p.every(Number.isFinite))){
  const scale=90/Math.max(.15,entry.shoulderSpan||.4),[origin,elbow,wrist]=points;
  const project=p=>[clamp(shoulder[0]+(p[0]-origin[0])*scale,35,365),clamp(shoulder[1]-(p[1]-origin[1])*scale,105,450)];
  // +Z points toward the camera after MediaPipe → avatar conversion.
  return {shoulder,elbow:project(elbow),wrist:project(wrist),depth:(wrist[2]-origin[2])/Math.max(.15,entry.shoulderSpan||.4),tracked:true};
 }
 const upper=pose?.armDirections?.[side+'UpperArm'],lower=pose?.armDirections?.[side+'LowerArm'];
 const unit=d=>{if(!d?.every(Number.isFinite))return null;const len=Math.hypot(...d);return len>1e-5?d.map(v=>v/len):null;};
 const rest=relaxedArmDirections(side);
 const u=unit(upper)||rest.upper,l=unit(lower)||(upper?u:rest.lower);
 const elbow=[shoulder[0]+u[0]*44,shoulder[1]-u[1]*44],wrist=[elbow[0]+l[0]*38,elbow[1]-l[1]*38];
 return {shoulder,elbow,wrist,depth:(u[2]*44+l[2]*38)/90,tracked:!!upper};
}
