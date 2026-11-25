/* Observe actual graph containers, including drawers opening after startup. */
(function(){'use strict';
 var seen=new WeakSet(), pending=false, sizes=new WeakMap();
 function resize(){pending=false;document.querySelectorAll('.graph-slot, .drawer-graph, .overlap-compact').forEach(function(el){
   var node=el.querySelector('.js-plotly-plot');var w=el.clientWidth,h=el.clientHeight;
   if(!node||w<30||h<30||!window.Plotly||!window.Plotly.Plots)return;
   var previous=sizes.get(node);if(previous&&previous[0]===w&&previous[1]===h)return;
   sizes.set(node,[w,h]);try{window.Plotly.Plots.resize(node);}catch(e){sizes.delete(node);}
 });}
 function schedule(){if(!pending){pending=true;requestAnimationFrame(resize);}}
 var ro=window.ResizeObserver?new ResizeObserver(schedule):null;
 function connect(){document.querySelectorAll('.graph-slot, .drawer-graph, .overlap-compact').forEach(function(el){if(ro&&!seen.has(el)){seen.add(el);ro.observe(el);}});schedule();}
 function init(){connect();new MutationObserver(function(records){if(records.some(function(r){return r.type==='childList'||(r.target.classList&&r.target.classList.contains('context-drawer'));}))connect();}).observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['style']});}
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
 window.addEventListener('resize',schedule,{passive:true});
 document.addEventListener('toggle',schedule,true);
}());
