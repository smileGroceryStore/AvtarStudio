const paths={camera:'M4 7h10v10H4z M14 10l6-3v10l-6-3',person:'M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0 M4 21v-2a8 8 0 0 1 16 0v2',sliders:'M5 3v8m0 4v6M12 3v3m0 4v11M19 3v11m0 4v3 M2 11h6M9 6h6M16 14h6',frame:'M4 9V4h5m6 0h5v5m0 6v5h-5m-6 0H4v-5',external:'M14 3h7v7m0-7L10 14 M10 3H3v18h18v-7',upload:'M12 16V3m-5 5 5-5 5 5M4 15v6h16v-6',play:'m8 4 12 8-12 8z',stop:'M5 5h14v14H5z',reset:'M3 11a9 9 0 1 1 2 7 M3 4v7h7',eye:'M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12 M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0',copy:'M9 9h12v12H9z M15 9V3H3v12h6',pet:'M4 10V4l6 3h4l6-3v9a8 8 0 0 1-16 0z M8 12h.01M16 12h.01 M10 16h4',hide:'M3 4h18v14H3z M8 22h8m-4-4v4'};
export function icon(name){return `<svg class="ui-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${paths[name]||paths.frame}"/></svg>`;}
export function labelButton(button,text,name){button.innerHTML=icon(name)+`<span>${text}</span>`;}
export function installLayout(){
 const left=document.querySelector('.controls'),right=document.querySelector('.adjustments');
 function tabs(panel,items){
  const nav=document.createElement('div');nav.className='panel-tabs';nav.setAttribute('role','tablist');nav.setAttribute('aria-label',panel===left?'角色和捕捉设置':'参数设置');
  const body=document.createElement('div');body.className='panel-body';
  items.forEach(([label,name,section],i)=>{
   const id=`${panel===left?'left':'right'}-${i}`,button=document.createElement('button');button.type='button';button.id=id+'-tab';button.setAttribute('role','tab');button.setAttribute('aria-controls',id);button.innerHTML=icon(name)+label;
   section.id=id;section.setAttribute('role','tabpanel');section.setAttribute('aria-labelledby',button.id);section.tabIndex=0;
   function select(){items.forEach((item,j)=>{const b=nav.children[j];b.setAttribute('aria-selected',String(j===i));b.tabIndex=j===i?0:-1;item[2].hidden=j!==i;});}
   button.onclick=select;button.onkeydown=e=>{let j=i;if(e.key==='ArrowRight')j=(i+1)%items.length;else if(e.key==='ArrowLeft')j=(i+items.length-1)%items.length;else if(e.key==='Home')j=0;else if(e.key==='End')j=items.length-1;else return;e.preventDefault();nav.children[j].click();nav.children[j].focus();};
   nav.append(button);body.append(section);
  });
  panel.querySelector('.panel-heading').after(nav);nav.after(body);nav.children[0].click();
 }
 const ls=[...left.querySelectorAll(':scope > section')],rs=[...right.querySelectorAll(':scope > section')];
 left.querySelector('h1').textContent='工作区';left.querySelector('.panel-heading p').textContent='选择形象，开始与分身互动';
 right.querySelector('.panel-heading h2').textContent='设置';right.querySelector('.panel-heading p').textContent='调整会自动保存';
 tabs(left,[['捕捉','camera',ls[0]],['角色','person',ls[1]]]);
 tabs(right,[['动作','sliders',rs[0]],['画面','frame',rs[1]],['输出','external',rs[3]]]);
 const tools=document.createElement('details');tools.className='tool-details';tools.innerHTML='<summary>校准与测试</summary>';
 const capture=ls[0];['calibrate','testBlink','blinkStatus','naturalMotion'].forEach(id=>tools.append(document.getElementById(id)));capture.append(tools);
 const advanced=document.createElement('details');advanced.className='tool-details';advanced.innerHTML='<summary>导入与模型说明</summary>';
 for(const node of [...ls[1].children])if(node.matches('.hint,.game-model-sources,#importAvatar,#avatarFile'))advanced.append(node);
 ls[1].append(advanced);
 rs[2].classList.add('desktop-dock');
 rs[2].querySelector('.hint').textContent='拖动角色移动，右键管理。关闭设置后可继续在托盘运行。';
 const entries={capture:['开始捕捉','play'],calibrate:['重新校准','reset'],testBlink:['测试闭眼','eye'],naturalMotion:['恢复自然跟随','reset'],useLibraryModel:['使用此角色','person'],importAvatar:['导入我的皮套','upload'],reset:['恢复默认参数','reset'],desktopPet:['挂到桌面','pet'],desktopHideConsole:['仅显示挂件','frame'],desktopBackground:['后台运行','hide'],copy:['复制 OBS 地址','copy']};
 for(const [id,[text,name]] of Object.entries(entries))labelButton(document.getElementById(id),text,name);
 const out=document.querySelector('.output-section a');labelButton(out,'打开纯净输出','external');
 document.querySelectorAll('.inline-code').forEach(el=>el.remove());
 document.querySelector('label[for="hands"]').textContent='跟随手腕与手指';
 const clearance=document.createElement('div');clearance.className='switch-row';clearance.innerHTML='<label for="clothingClearance">衣物避让 <small>手臂与躯干留出空间</small></label><input id="clothingClearance" type="checkbox" checked>';rs[0].append(clearance);
}
