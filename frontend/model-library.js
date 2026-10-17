export const models=[
 {id:'a',name:'3D · 清新学院 · A',file:'AvatarSample_A.vrm'},
 {id:'b',name:'3D · 星饰少女 · B',file:'AvatarSample_B.vrm'},
 {id:'c',name:'3D · 黑发少年 · C',file:'AvatarSample_C.vrm'},
 {id:'sample',name:'3D · 银发休闲',file:'sample.vrm'},
 {id:'darkness',name:'3D · 暗色街头 · Darkness Shibu',file:'Darkness_Shibu.vrm'},
 {id:'fumiriya',name:'3D · 金发衬衫 · Fumiriya',file:'Sakurada_Fumiriya.vrm'},
 {id:'unitychan',name:'3D · Unity Chan · 科幻运动',file:'UnityChan.vrm'},
 {id:'cat',name:'2D · 薄荷猫耳',color:'mint'},
 {id:'bunny',name:'2D · 樱花兔耳',color:'rose'},
 {id:'cyber',name:'2D · 冰蓝机甲',color:'blue'},
];
export async function installModelLibrary({command,update,notify,getState}){
 const select=document.getElementById('modelLibrary');
 const available=[...models];
 const add=model=>{const option=document.createElement('option');option.value=model.id;option.textContent=model.name;select.append(option);};
 available.forEach(add);
 try{const response=await fetch('/api/library');if(response.ok){for(const model of await response.json()){available.push(model);add(model);}}}catch(error){console.warn('个人角色库读取失败',error);}
 document.getElementById('modelLibraryLabel').textContent='角色库 · '+available.length+' 款';
 const button=document.getElementById('useLibraryModel');
 button.onclick=async()=>{
  const model=available.find(x=>x.id===select.value);if(!model)return;
  if(getState()?.running){notify('请先停止捕捉，再切换角色。',true);return;}
  button.disabled=true;
  try{
   if(model.file){
    notify('正在加载 '+model.name+'…');
    const asset=await fetch(model.assetUrl||'/assets/models/'+model.file);if(!asset.ok)throw new Error('模型文件读取失败');
    const response=await fetch('/api/avatar',{method:'POST',headers:{'Content-Type':'application/octet-stream','X-Avatar-Name':encodeURIComponent(model.name+'.vrm')},body:await asset.blob()});
    if(!response.ok)throw new Error(await response.text());
    update(await response.json());update(await command('settings',{settings:{avatarMode:'3d'}}));
   }else update(await command('settings',{settings:{avatarMode:'2d',petColor:model.color}}));
   notify('已切换：'+model.name+(model.notice?' · '+model.notice:''));
  }catch(error){notify(error.message,true);}finally{button.disabled=false;}
 };
}
