import {Vector3} from 'three';
import {VRMSpringBoneManager,VRMSpringBoneJoint} from '@pixiv/three-vrm';

// Models with authored springs keep their own configuration. For unconfigured
// models, only long, unbranched chains attached to the raw head qualify.
export function addMissingHairPhysics(vrm){
 if(vrm.springBoneManager?.joints.size)return 0;
 const head=vrm.humanoid?.getRawBoneNode('head');
 if(!head)return 0;
 vrm.scene.updateMatrixWorld(true);
 const humanoid=new Set(Object.values(vrm.humanoid.rawHumanBones).map(b=>b?.node));
 const chains=[];
 for(const root of head.children){
  const chain=[root];let node=root;
  while(node.children.length===1&&chain.length<24){node=node.children[0];chain.push(node);}
  if(chain.length<5||chain.some(b=>humanoid.has(b)||b.isMesh))continue;
  const start=root.getWorldPosition(new Vector3()),end=node.getWorldPosition(new Vector3());
  if(start.y-end.y<.35)continue;
  chains.push(chain);
 }
 if(!chains.length)return 0;
 const manager=vrm.springBoneManager||new VRMSpringBoneManager();let count=0;
 for(const chain of chains){
  // Keep the scalp attachment fixed; simulate the length below it.
  for(let i=1;i<chain.length-1;i++){
   manager.addJoint(new VRMSpringBoneJoint(chain[i],chain[i+1],{
    stiffness:2.2,dragForce:.42,gravityPower:.025,
    gravityDir:new Vector3(0,-1,0),hitRadius:.015,
   }));count++;
  }
 }
 manager.setInitState();manager.reset();vrm.springBoneManager=manager;
 return count;
}
