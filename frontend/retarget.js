import { Vector3, Quaternion } from 'three';
const rest = new Vector3(), target = new Vector3(), parent = new Quaternion(), solved = new Quaternion();
// Aim the actual model segment in WORLD space, removing its current parent's
// rotation. The lower arm therefore follows the already-smoothed upper arm.
export function retargetDirection(bone, child, direction, previous, alpha) {
  if (!bone || !child || !direction || direction.length !== 3 || !direction.every(Number.isFinite)) return false;
  rest.copy(child.position);
  target.fromArray(direction);
  if (rest.lengthSq()<1e-8 || target.lengthSq()<1e-8) return false;
  bone.parent.updateWorldMatrix(true,false);
  bone.parent.getWorldQuaternion(parent).invert();
  target.normalize().applyQuaternion(parent);
  solved.setFromUnitVectors(rest.normalize(),target);
  bone.quaternion.copy(previous).slerp(solved,alpha);
  bone.updateWorldMatrix(false,true);
  return true;
}
