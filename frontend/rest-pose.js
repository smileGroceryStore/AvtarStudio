// Nearly vertical arms, with a small outward clearance from the torso.
export function relaxedArmDirections(side){
 const sign=side==='left'?1:-1;
 const unit=v=>{const n=Math.hypot(...v);return v.map(x=>x/n);};
 return {upper:unit([sign*.12,-1,.015]),lower:unit([sign*.10,-1,.025])};
}
