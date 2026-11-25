/* Plotly Scattermap uses MapLibre. Suppress its default repeating worlds.
   Preserve the normal Plotly map selection, zoom and hover interactions.
   Fit once on creation/reset; never refit on data-only changes. */
(function(){
 'use strict';
 const bound=new WeakSet(), state=new WeakMap(), awaiting=new WeakSet();
 let scheduled=false;
 const merc=lat=>Math.log(Math.tan(Math.PI/4+lat*Math.PI/360))/(2*Math.PI);
 function overview(w,h){
   const south=merc(-59),north=merc(79);
   const scale=Math.min(Math.max(1,w-20),Math.max(1,h-20)/(north-south));
   const zoom=Math.max(-2,Math.min(2,Math.log2(scale/512)));
   const lat=(2*Math.atan(Math.exp((north+south)*Math.PI))-Math.PI/2)*180/Math.PI;
   return {zoom:zoom,center:{lon:0,lat:lat}};
 }
 function sync(){
   scheduled=false;
   const gd=document.querySelector('#plant-map .js-plotly-plot');
   if(!gd)return;
   if(!bound.has(gd)&&typeof gd.on==='function'){
     gd.on('plotly_afterplot',schedule);
     bound.add(gd);
   }
   const full=gd._fullLayout, layout=full&&full.map;
   const map=layout&&layout._subplot&&layout._subplot.map;
   if(!map||typeof map.setRenderWorldCopies!=='function')return;
   if(typeof map.getRenderWorldCopies!=='function'||map.getRenderWorldCopies())map.setRenderWorldCopies(false);
   if(typeof map.loaded==='function'&&!map.loaded()){
     if(!awaiting.has(map)&&typeof map.once==='function'){
       awaiting.add(map); map.once('idle',()=>{awaiting.delete(map);schedule();});
     }
     return;
   }
   const rev=String(full.uirevision||'initial');
   const previous=state.get(gd);
   if(previous&&previous.map===map&&previous.rev===rev)return;
   const slot=gd.closest('.graph-slot');
   if(!slot||slot.clientWidth<50||slot.clientHeight<50||!window.Plotly||!window.Plotly.relayout)return;
   state.set(gd,{map:map,rev:rev});
   const camera=overview(slot.clientWidth,slot.clientHeight);
   // Updating Plotly's own camera preserves the fitted view on subsequent callbacks.
   try {
     Promise.resolve(window.Plotly.relayout(gd,{'map.center':camera.center,'map.zoom':camera.zoom})).catch(()=>state.delete(gd));
   } catch(error) {state.delete(gd);}

 }
 function schedule(){if(!scheduled){scheduled=true;requestAnimationFrame(sync);}}
 function init(){
   schedule();
   new MutationObserver(schedule).observe(document.body,{childList:true,subtree:true});
   window.addEventListener('resize',schedule,{passive:true});
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
}());
