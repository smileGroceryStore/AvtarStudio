import {Vector3,Matrix4,Quaternion} from 'three';
function frame(direction,normal){
 const x=new Vector3().fromArray(direction),z=new Vector3().fromArray(normal);
 if(![...direction,...normal].every(Number.isFinite)||x.lengthSq()<1e-8||z.lengthSq()<1e-8)return null;
 x.normalize();z.addScaledVector(x,-z.dot(x));if(z.lengthSq()<1e-8)return null;z.normalize();
 const y=new Vector3().crossVectors(z,x).normalize();return new Quaternion().setFromRotationMatrix(new Matrix4().makeBasis(x,y,z));
}
// Preserve normal motion at full scale; only extreme joint angles are capped.
const trackingHistory=new WeakMap();
export function naturalWristRotation(rotation,axis,palmNormal=null){
 const q=rotation.clone().normalize();if(q.w<0)q.set(-q.x,-q.y,-q.z,-q.w);
 const along=q.x*axis.x+q.y*axis.y+q.z*axis.z;
 const twist=new Quaternion(axis.x*along,axis.y*along,axis.z*along,q.w);
 if(twist.lengthSq()<1e-8)twist.identity();else twist.normalize();
 const swing=q.clone().multiply(twist.clone().invert()).normalize();
 const twistAngle=2*Math.atan2(along,q.w);
 const safeTwist=new Quaternion().setFromAxisAngle(axis,Math.max(-Math.PI*7/36,Math.min(Math.PI*7/36,twistAngle)));
 const angle=swing.angleTo(new Quaternion());
 let safeSwing=new Quaternion().slerp(swing,angle>1e-8?Math.min(1,(Math.PI*7/18)/angle):0);
 if(palmNormal&&angle>1e-8){
  const normal=palmNormal.clone().addScaledVector(axis,-palmNormal.dot(axis)).normalize();
  const flexAxis=new Vector3().crossVectors(axis,normal).normalize();
  const scale=Math.sin(angle/2);
  if(Math.abs(scale)>1e-6&&normal.lengthSq()>.5){
   const rotationVector=new Vector3(swing.x,swing.y,swing.z).multiplyScalar(angle/scale);
   const flex=Math.max(-Math.PI*7/18,Math.min(Math.PI*7/18,rotationVector.dot(flexAxis)));
   const sideways=Math.max(-Math.PI*5/36,Math.min(Math.PI*5/36,rotationVector.dot(normal)));
   const bounded=flexAxis.multiplyScalar(flex).addScaledVector(normal,sideways);
   const length=bounded.length();safeSwing=length>1e-8?new Quaternion().setFromAxisAngle(bounded.divideScalar(length),length):new Quaternion();
  }
 }
 return safeSwing.multiply(safeTwist).normalize();
}
export function resetPalm(hand){trackingHistory.delete(hand);}
export function retargetPalm(hand,index,little,palm,previous,alpha,dt=1/60,forearm=null){
 if(!hand||!index||!little||!palm?.direction||!palm?.normal||palm.direction.length!==3||palm.normal.length!==3)return false;
 const a=index.position,b=little.position;
 const rest=frame(a.clone().add(b).toArray(),new Vector3().crossVectors(a,b).toArray());
 const target=frame(palm.direction,palm.normal);if(!rest||!target)return false;
 // Compare detector changes in WORLD space, not a moving forearm's local frame.
 const desired=target.multiply(rest.invert());
 let history=trackingHistory.get(hand);
 if(!history){history={accepted:desired.clone(),candidate:null,age:0,twist:0,fullAngle:0};trackingHistory.set(hand,history);}
 if(history.accepted.angleTo(desired)>2){
  if(history.candidate&&history.candidate.angleTo(desired)<.45)history.age+=dt;
  else{history.candidate=desired.clone();history.age=dt;}
  if(history.age>=.05){history.accepted.copy(desired);history.candidate=null;history.age=0;}
 }else{history.accepted.copy(desired);history.candidate=null;history.age=0;}
 if(forearm&&hand.parent===forearm&&hand.position.lengthSq()>1e-8){
  const axis=hand.position.clone().normalize();
  // Replace axial roll while preserving the solved elbow-to-wrist direction.
  const aim=axis.clone().applyQuaternion(forearm.quaternion);
  const base=new Quaternion().setFromUnitVectors(axis,aim);
  forearm.parent.updateWorldMatrix(true,false);
  const baseWorld=forearm.parent.getWorldQuaternion(new Quaternion()).multiply(base);
  const delta=baseWorld.invert().multiply(history.accepted);
  let angle=2*Math.atan2(delta.x*axis.x+delta.y*axis.y+delta.z*axis.z,delta.w);
  // Never accumulate multiple turns from noisy palm-normal reversals.
  if(angle>Math.PI)angle-=2*Math.PI;
  if(angle<-Math.PI)angle+=2*Math.PI;
  if(Math.abs(angle)>2.6&&Math.abs(history.twist)>.1&&angle*history.twist<0)angle=Math.sign(history.twist)*Math.abs(angle);
  const targetTwist=Math.max(-Math.PI*17/36,Math.min(Math.PI*17/36,angle*.8));
  const change=(targetTwist-history.twist)*(1-Math.exp(-Math.max(0,dt)*18));
  history.twist+=Math.max(-dt*5,Math.min(dt*5,change));
  forearm.quaternion.copy(base).multiply(new Quaternion().setFromAxisAngle(axis,history.twist));
  forearm.updateWorldMatrix(false,true);
 }
 hand.parent.updateWorldMatrix(true,false);
 const parent=hand.parent.getWorldQuaternion(new Quaternion());
 const solved=parent.invert().multiply(history.accepted);
 const safe=naturalWristRotation(solved,a.clone().add(b).normalize(),new Vector3().crossVectors(a,b).normalize());
 const filtered=previous.clone().slerp(safe,alpha);
 hand.quaternion.copy(previous).rotateTowards(filtered,Math.max(0,Math.min(.1,dt))*8);
 hand.updateWorldMatrix(false,true);return true;
}
