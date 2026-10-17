import {relaxedArmDirections} from './rest-pose.js';
export const idlePoses=[['natural','自然下垂'],['sway','轻松摇摆']];
export function idleArmDirections(preset,time=0){
 const result={};
 for(const side of ['left','right']){
  const sign=side==='left'?1:-1,rest=relaxedArmDirections(side);
  let upper=rest.upper,lower=rest.lower;
  if(preset==='sway'){upper=[sign*.15,-1,.03+.07*Math.sin(time*1.4)];lower=[sign*.10,-1,.08+.10*Math.sin(time*1.4-.5)];}
  result[side+'UpperArm']=upper;result[side+'LowerArm']=lower;
 }
 return result;
}
export function idleBodyPose(){
 return {legs:Object.fromEntries(['leftUpperLeg','rightUpperLeg','leftLowerLeg','rightLowerLeg','leftFoot','rightFoot'].map(n=>[n,[0,0,0]])),lowering:0,roll:0};
}
