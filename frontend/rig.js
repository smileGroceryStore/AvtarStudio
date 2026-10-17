export function dampFactor(smoothing, dt) {
  return 1 - Math.pow(Math.min(.95, Math.max(0, smoothing)), Math.min(dt, .1) * 60);
}
export function scaleExpressions(expressions, gain) {
  return Object.fromEntries(Object.entries(expressions).map(([k,v]) => [k, Math.min(1, Math.max(0, v * (k.startsWith('blink')?1:gain)))]));
}
// VRM 0's normalized skeleton faces -Z. After rotating its scene to +Z,
// conjugate canonical local rotations by that half-turn (VRM 1 needs none).
export function rigQuaternionComponents(q, legacy) {
  return legacy ? [-q[0], q[1], -q[2], q[3]] : [...q];
}

export function routeBlink(expressions,manager){
  const bound=name=>!!manager.getExpression(name)?.binds?.length;
  const both=bound('blinkLeft')&&bound('blinkRight');
  const l=expressions.blinkLeft??expressions.blink??0,r=expressions.blinkRight??expressions.blink??0;
  if(both)return {...expressions,blink:0,blinkLeft:l,blinkRight:r};
  if(bound('blink'))return {...expressions,blink:Math.max(l,r),blinkLeft:0,blinkRight:0};
  return {...expressions,blink:0,blinkLeft:l,blinkRight:r};
}

// Ignore small calibration/camera noise around straight ahead, continuously.
export function neutralHeadPitch(pitch){
 const deadzone=3*Math.PI/180;
 return Math.abs(pitch)<=deadzone?0:-Math.sign(pitch)*(Math.abs(pitch)-deadzone)*.8;
}
