
const areas={Nagpur:["Dharampeth","Manish Nagar","Sitabuldi","Hingna","Sadar","Pratap Nagar","Nandanvan","Wardha Road","Besa","MIHAN"],Pune:["Hinjewadi","Kothrud","Wakad","Viman Nagar","Baner"],Mumbai:["Andheri","Bandra","Powai","Borivali","Dadar"]};
document.addEventListener("DOMContentLoaded",()=>{
 const city=document.getElementById("citySelect"),area=document.getElementById("areaSelect");
 function fill(){if(!city||!area)return;const old=area.dataset.selected||area.value;area.innerHTML='<option value="">All areas</option>';(areas[city.value]||[]).forEach(x=>{let o=document.createElement("option");o.value=x;o.textContent=x;if(x===old)o.selected=true;area.appendChild(o);});}
 if(city&&area){fill();city.addEventListener("change",()=>{area.dataset.selected="";fill();});}
 const form=document.getElementById("propertyForm"),modal=document.getElementById("confirmModal");let confirmed=false;
 if(form&&modal){form.addEventListener("submit",e=>{if(!confirmed){e.preventDefault();modal.classList.add("show");}});document.getElementById("backBtn").onclick=()=>modal.classList.remove("show");document.getElementById("confirmBtn").onclick=()=>{confirmed=true;form.requestSubmit();};}
});
