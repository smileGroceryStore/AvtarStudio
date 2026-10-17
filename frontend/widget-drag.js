// Pointer capture keeps drag events flowing even outside the character/window.
export function attachWidgetDrag(regions, getApi, hitTest=()=>true) {
 let drag=null,pending=null,sending=false,finishing=false;
 async function flush(){
  if(sending)return;sending=true;
  try{while(pending){const next=pending;pending=null;await getApi().move_widget(next.x,next.y);}}
  catch(e){console.error('Widget move failed',e);}
  finally{sending=false;if(finishing){finishing=false;await getApi()?.save_widget_position();}}
 }
 for(const region of regions){
  region.addEventListener('mousedown',e=>e.stopPropagation());
  region.addEventListener('pointerdown',async e=>{
   if(e.button!==0||!getApi()?.move_widget||!hitTest(e.clientX,e.clientY))return;
   e.preventDefault();e.stopPropagation();
   const start={id:e.pointerId,screenX:e.screenX,screenY:e.screenY,x:null,y:null,lastX:e.screenX,lastY:e.screenY};drag=start;
   region.setPointerCapture(e.pointerId);
   const pos=await getApi().widget_position();
   if(drag!==start)return;
   start.x=pos.x;start.y=pos.y;
   pending={x:pos.x+start.lastX-start.screenX,y:pos.y+start.lastY-start.screenY};flush();
  });
  region.addEventListener('pointermove',e=>{
   if(!drag||e.pointerId!==drag.id)return;
   drag.lastX=e.screenX;drag.lastY=e.screenY;
   if(drag.x===null)return;
   pending={x:drag.x+e.screenX-drag.screenX,y:drag.y+e.screenY-drag.screenY};flush();
  });
  const end=e=>{if(!drag||e.pointerId!==drag.id)return;drag=null;finishing=true;flush();};
  region.addEventListener('pointerup',end);region.addEventListener('pointercancel',end);region.addEventListener('lostpointercapture',end);
 }
}
