// Gentle clearance near a hanging upper arm, not a global joint-angle clamp.
// Raised arms and deliberate forward reaches keep their captured directions.
export function clothingClearance(direction,side,enabled=true){
 if(!enabled||!Array.isArray(direction)||direction.length!==3||!direction.every(Number.isFinite))return direction;
 const length=Math.hypot(...direction);if(length<1e-8)return direction;
 const [x,y,z]=direction.map(v=>v/length),sign=side==='left'?1:-1;
 const smooth=v=>{const t=Math.max(0,Math.min(1,v));return t*t*(3-2*t);};
 const weight=smooth((-y-.5)/.35)*(1-smooth((Math.abs(z)-.18)/.25));
 const outward=sign*x;
 if(outward>=.21||weight===0)return direction;
 const next=[x+sign*(.21-outward)*weight,y,z],n=Math.hypot(...next);
 return next.map(v=>v/n);
}
