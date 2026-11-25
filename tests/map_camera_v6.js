/* Node test of the actual browser asset with a controlled MapLibre/Plotly adapter.
   Full map rendering is verified separately by the optional live browser test. */
const assert=require('node:assert/strict'), fs=require('node:fs'), vm=require('node:vm'), path=require('node:path');
const queue=[], events={};let copies=true,calls=[],layouts=[],map={getRenderWorldCopies:()=>copies,setRenderWorldCopies:v=>{copies=v;calls.push(v)},loaded:()=>true};
const gd={_fullLayout:{uirevision:'reset-0',map:{_subplot:{map}}},on:(e,f)=>events[e]=f,closest:()=>({clientWidth:1200,clientHeight:300})};
const window={addEventListener:(e,f)=>events[e]=f,Plotly:{relayout:(g,edits)=>{assert.equal(g,gd);layouts.push(edits);return Promise.resolve()}}};
const document={readyState:'complete',body:{},querySelector:()=>gd};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../assets/zzzzzzzzzz_single_world.js'),'utf8'),{window,document,WeakSet,WeakMap,Promise,Math,MutationObserver:class{constructor(f){events.mutation=f}observe(){}},requestAnimationFrame:f=>queue.push(f)});
function flush(){while(queue.length)queue.shift()()}
flush();assert.equal(copies,false);assert.equal(calls.length,1);assert.equal(layouts.length,1);assert.ok(layouts[0]['map.zoom']<1);
// Data-only updates and a user pan must not force the map back to the overview.
events.plotly_afterplot();events.mutation();flush();assert.equal(layouts.length,1);
// Reset view re-fits; new MapLibre instance disables wrap again.
gd._fullLayout.uirevision='reset-1';events.plotly_afterplot();flush();assert.equal(layouts.length,2);
copies=true;map={...map};gd._fullLayout.map._subplot.map=map;events.plotly_afterplot();flush();assert.equal(copies,false);assert.equal(layouts.length,3);
console.log('[PASS] Single-world guard, initial fit, reset fit and preservation across data updates (mock adapter)');
