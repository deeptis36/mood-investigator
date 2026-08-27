const $=id=>document.getElementById(id),wait=ms=>new Promise(r=>setTimeout(r,ms));
const emoji={anger:"😡",disgust:"🤢",fear:"😨",joy:"😀",neutral:"😐",sadness:"😔",surprise:"😲"};
const names={anger:"Anger",disgust:"Disgust",fear:"Fear",joy:"Joy",neutral:"Neutral",sadness:"Sadness",surprise:"Surprise"};
$("investigate").onclick=async()=>{
 const text=$("text").value.trim(),err=$("inputError");
 if(!text){err.textContent="Tell me something first.";err.classList.remove("hidden");return}
 err.classList.add("hidden");$("investigate").disabled=true;$("inputScreen").classList.add("hidden");$("thinkingScreen").classList.remove("hidden");
 try{
  for(const s of ["Understanding what happened…","Looking beyond the literal words…","Connecting the situation to emotional signals…","Comparing possible feelings…"]){$("thinkingText").textContent=s;await wait(500)}
  const r=await fetch("/analyze",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({text})}),d=await r.json();
  if(!r.ok)throw Error(d.detail||"Analysis failed");
  $("thinkingText").textContent="Investigation complete.";await wait(450);
  $("thinkingScreen").classList.add("hidden");$("resultScreen").classList.remove("hidden");
  $("emoji").textContent=d.emoji||"💭";$("emotion").textContent=d.primary_emotion||"Mixed emotions";
  $("confidence").textContent=Math.round((d.confidence||0)*100)+"%";
  $("tags").innerHTML=(d.secondary_emotions||[]).map(x=>`<span class="tag">${x}</span>`).join("");
  $("situation").textContent=d.situation||"The situation could not be summarized.";
  $("observation").textContent=d.observation||"Your sentence contains emotional signals.";
  $("emotions").innerHTML=(d.emotions||[]).slice(0,4).map(e=>`<div class="emotion"><label><span>${emoji[e.label]||"•"} ${names[e.label]||e.label}</span><b>${Math.round(e.score*100)}%</b></label><div class="bar"><i data-score="${e.score*100}"></i></div></div>`).join("");
  setTimeout(()=>document.querySelectorAll(".bar i").forEach(x=>x.style.width=x.dataset.score+"%"),80);
 }catch(e){$("thinkingScreen").classList.add("hidden");$("inputScreen").classList.remove("hidden");err.textContent=e.message||"The investigator could not complete the analysis. Check that the Python server is running.";err.classList.remove("hidden");$("investigate").disabled=false}
};
$("text").addEventListener("keydown",e=>{if((e.ctrlKey||e.metaKey)&&e.key==="Enter")$("investigate").click()});