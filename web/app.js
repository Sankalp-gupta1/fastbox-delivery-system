const COLORS=["#69e3ff","#c7ff6b","#a78bfa","#ffb66d","#ff75b9","#6e8cff","#ff7a7a","#66ffc2"];
const $=s=>document.querySelector(s);
let lastResult=null;

function checkId(v,label){if(typeof v!=="string"||!v.trim())throw new Error(label+" must be a non-empty string.")}
function checkLoc(v,label){if(!Array.isArray(v)||v.length!==2||v.some(x=>typeof x!=="number"||!Number.isFinite(x)))throw new Error(label+" must contain two finite numbers: [x, y].")}
function readLocations(items,label){
  const out={};
  if(Array.isArray(items)){
    for(const item of items){if(!item||typeof item!=="object")throw new Error("Each entry in "+label+" must be an object.");checkId(item.id,"ID in "+label);if(out[item.id])throw new Error("Duplicate ID in "+label+": "+item.id);checkLoc(item.location,"Location of "+item.id);out[item.id]=[...item.location]}
  }else if(items&&typeof items==="object"){
    for(const [id,loc] of Object.entries(items)){checkId(id,"ID in "+label);if(out[id])throw new Error("Duplicate ID in "+label+": "+id);checkLoc(loc,"Location of "+id);out[id]=[...loc]}
  }else throw new Error(label+" must be a dictionary or a list.");
  return out;
}
function prepare(data){
  if(!data||typeof data!=="object"||Array.isArray(data))throw new Error("The input JSON must be an object.");
  ["warehouses","agents","packages"].forEach(k=>{if(!(k in data))throw new Error("Missing required field: "+k)});
  const warehouses=readLocations(data.warehouses,"warehouses"),agents=readLocations(data.agents,"agents");
  if("best_agent" in agents)throw new Error("Agent ID 'best_agent' is reserved for the report.");
  if(!Array.isArray(data.packages))throw new Error("packages must be a list.");
  if(data.packages.length&&!Object.keys(agents).length)throw new Error("At least one agent is needed to deliver packages.");
  const seen=new Set(),packages=data.packages.map(p=>{
    if(!p||typeof p!=="object")throw new Error("Each package must be an object.");
    checkId(p.id,"Package ID");if(seen.has(p.id))throw new Error("Duplicate package ID: "+p.id);seen.add(p.id);
    const wid=p.warehouse_id??p.warehouse;checkId(wid,"Warehouse ID for "+p.id);
    if("warehouse_id" in p&&"warehouse" in p&&p.warehouse_id!==p.warehouse)throw new Error("Conflicting warehouse fields for "+p.id+".");
    if(!(wid in warehouses))throw new Error("Unknown warehouse for "+p.id+": "+wid);
    checkLoc(p.destination,"Destination of "+p.id);
    return {id:p.id,warehouse_id:wid,destination:[...p.destination]};
  });
  return {warehouses,agents,packages};
}
function distance(a,b){return Math.hypot(a[0]-b[0],a[1]-b[1])}
function simulate(data){
  const {warehouses,agents,packages}=prepare(data),assignments={};
  for(const p of packages){
    const wh=warehouses[p.warehouse_id];
    assignments[p.id]=Object.keys(agents).sort().reduce((best,id)=>{
      if(best===null)return id;const d=distance(agents[id],wh),bd=distance(agents[best],wh);return d<bd?id:d===bd&&id<best?id:best;
    },null);
  }
  const positions=Object.fromEntries(Object.entries(agents).map(([k,v])=>[k,[...v]]));
  const totals=Object.fromEntries(Object.keys(agents).map(id=>[id,{packages_delivered:0,total_distance:0}]));
  const log=[];
  for(const p of packages){
    const aid=assignments[p.id],start=[...positions[aid]],wh=warehouses[p.warehouse_id],dest=p.destination;
    const pickup=distance(start,wh),delivery=distance(wh,dest),trip=pickup+delivery;
    totals[aid].packages_delivered++;totals[aid].total_distance+=trip;positions[aid]=[...dest];
    log.push({package_id:p.id,agent_id:aid,warehouse_id:p.warehouse_id,start,warehouse:[...wh],destination:[...dest],pickup_distance:+pickup.toFixed(2),delivery_distance:+delivery.toFixed(2),trip_distance:+trip.toFixed(2)});
  }
  const report={},scores=[];
  for(const [id,s] of Object.entries(totals)){
    const avg=s.packages_delivered?s.total_distance/s.packages_delivered:null;
    report[id]={packages_delivered:s.packages_delivered,total_distance:+s.total_distance.toFixed(2),efficiency:avg===null?null:+avg.toFixed(2)};
    if(avg!==null)scores.push({id,avg,count:s.packages_delivered});
  }
  scores.sort((a,b)=>a.avg-b.avg||b.count-a.count||a.id.localeCompare(b.id));
  report.best_agent=scores.length?scores[0].id:null;
  return {report,log,warehouses,agents};
}
function fmt(n){return n===null||n===undefined?"—":Number(n).toFixed(2)}
function render(result){
  lastResult=result;
  const {report,log,warehouses,agents}=result,best=report.best_agent;
  const ids=Object.keys(agents);
  $("#bestAgent").textContent=best||"None";$("#packageCount").textContent=log.length;$("#agentCount").textContent=ids.length;
  $("#totalDistance").textContent=fmt(ids.reduce((s,id)=>s+report[id].total_distance,0));
  $("#agentBody").innerHTML=ids.sort().map(id=>'<tr><td><strong>'+id+'</strong></td><td>'+report[id].packages_delivered+'</td><td>'+fmt(report[id].total_distance)+'</td><td>'+fmt(report[id].efficiency)+'</td><td class="'+(id===best?"winner":"")+'">'+(id===best?"Best agent":"—")+'</td></tr>').join("");
  $("#deliveryLog").innerHTML=log.length?log.map((d,i)=>'<div class="log-item"><strong>'+d.package_id+'</strong><p>'+d.agent_id+' · '+d.start.join(", ")+' → '+d.warehouse_id+' '+d.warehouse.join(", ")+' → '+d.destination.join(", ")+'</p><span class="log-distance">'+fmt(d.trip_distance)+'</span></div>').join(""):'<div class="empty">No packages to deliver.</div>';
  $("#downloadBtn").disabled=false;renderMap(result);
}
function renderMap(result){
  const svg=$("#routeMap"),points=[];
  Object.values(result.warehouses).forEach(p=>points.push(p));Object.values(result.agents).forEach(p=>points.push(p));result.log.forEach(d=>points.push(d.destination));
  if(!points.length){svg.innerHTML="";return}
  let minX=Math.min(...points.map(p=>p[0])),maxX=Math.max(...points.map(p=>p[0])),minY=Math.min(...points.map(p=>p[1])),maxY=Math.max(...points.map(p=>p[1]));
  if(minX===maxX){minX--;maxX++}if(minY===maxY){minY--;maxY++}
  const W=760,H=470,pad=42,x=v=>pad+(v-minX)/(maxX-minX)*(W-pad*2),y=v=>H-pad-(v-minY)/(maxY-minY)*(H-pad*2);
  let out="";for(let i=0;i<=8;i++){const xx=pad+i*(W-pad*2)/8,yy=pad+i*(H-pad*2)/8;out+='<line class="grid-line" x1="'+xx+'" y1="'+pad+'" x2="'+xx+'" y2="'+(H-pad)+'"/><line class="grid-line" x1="'+pad+'" y1="'+yy+'" x2="'+(W-pad)+'" y2="'+yy+'"/>'}
  const agentIndex=Object.fromEntries(Object.keys(result.agents).sort().map((id,i)=>[id,i]));
  result.log.forEach(d=>{const c=COLORS[agentIndex[d.agent_id]%COLORS.length];out+='<polyline class="route" stroke="'+c+'" points="'+x(d.start[0])+','+y(d.start[1])+' '+x(d.warehouse[0])+','+y(d.warehouse[1])+' '+x(d.destination[0])+','+y(d.destination[1])+'"/>'});
  Object.entries(result.agents).forEach(([id,p])=>{const c=COLORS[agentIndex[id]%COLORS.length];out+='<circle class="route-point" cx="'+x(p[0])+'" cy="'+y(p[1])+'" r="7" fill="'+c+'"/><text class="label" x="'+(x(p[0])+10)+'" y="'+(y(p[1])+3)+'">'+id+'</text>'});
  Object.entries(result.warehouses).forEach(([id,p])=>{out+='<rect x="'+(x(p[0])-6)+'" y="'+(y(p[1])-6)+'" width="12" height="12" rx="2" fill="#f1f4f6"/><text class="label" x="'+(x(p[0])+10)+'" y="'+(y(p[1])+3)+'">'+id+'</text>'});
  result.log.forEach(d=>{out+='<circle class="route-point" cx="'+x(d.destination[0])+'" cy="'+y(d.destination[1])+'" r="4" fill="#ffb66d"/><text class="sub-label" x="'+(x(d.destination[0])+7)+'" y="'+(y(d.destination[1])-6)+'">'+d.package_id+'</text>'});
  svg.innerHTML=out;
}
function run(){
  $("#error").classList.add("hidden");$("#status").textContent="Running…";
  try{const data=JSON.parse($("#jsonInput").value);const r=simulate(data);render(r);$("#status").textContent="Simulation complete"}
  catch(e){$("#error").textContent=e.message;$("#error").classList.remove("hidden");$("#status").textContent="Input error"}
}
$("#sampleBtn").addEventListener("click",()=>fetch("base_case.json").then(r=>r.text()).then(t=>{$("#jsonInput").value=t;run()}));
$("#fileInput").addEventListener("change",e=>{const f=e.target.files[0];if(!f)return;const reader=new FileReader();reader.onload=()=>{$("#jsonInput").value=reader.result;run()};reader.readAsText(f)});
$("#runBtn").addEventListener("click",run);
$("#downloadBtn").addEventListener("click",()=>{if(!lastResult)return;const blob=new Blob([JSON.stringify(lastResult.report,null,2)+"\n"],{type:"application/json"}),url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download="report.json";a.click();URL.revokeObjectURL(url)});
$("#sampleBtn").click();