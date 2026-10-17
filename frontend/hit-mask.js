export function encodeAlphaMask(pixels,width,height,{flipY=false,mirror=false}={}){
 const rows=[];
 for(let y=0;y<height;y++){
  let row='';const sy=flipY?height-1-y:y;
  for(let x=0;x<width;x++){const sx=mirror?width-1-x:x;row+=pixels[(sy*width+sx)*4+3]>=24?'1':'0';}
  rows.push(row);
 }
 return {width,height,pixels:rows.join('')};
}

// Native polling still runs when the WebView no longer receives mouse events.
// Send a small rendered mask, rather than doing a Python/JS round trip per move.
export function installHitMask(getMask,getApi){
 let stopped=false,last='';
 async function update(){
  if(stopped)return;
  try{
   const api=getApi();
   if(api?.set_widget_hit_mask){
    const mask=await getMask();
    if(mask){const signature=mask.width+':'+mask.height+':'+mask.pixels;if(signature!==last&&await api.set_widget_hit_mask(mask.width,mask.height,mask.pixels))last=signature;}
   }
  }catch(error){console.error('Widget hit mask failed',error);}
  if(!stopped)setTimeout(update,80);
 }
 update();window.addEventListener('pagehide',()=>{stopped=true;},{once:true});
}
