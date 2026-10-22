const M=require('./model.js');
const base={mix:{HDPE:40,LDPE:20,PP:30,PS:10},mass:50,Vr:0.3,mSteel:150,UA:30,Tamb:298,Tsp:723,Pmax:40000,Pset:1.2e5,reflux:true,Tref:603,Tc:298,n2:0.005,cat:'none',catLoad:0,recirc:true};
function run(name,o){const c={...base,...o};const s=M.makeState(c);let maxP=0;let tHot=0;
 while(s.t<6*3600 && !s.done){M.step(s,c,0.2);maxP=Math.max(maxP,s.P);}
 const r=M.summary(s);const pc=x=>(100*x/c.mass).toFixed(1);
 console.log(name.padEnd(22),'t',(s.t/60).toFixed(0)+'min','T',(s.T-273).toFixed(0),'Pmax',(maxP/1e5).toFixed(2),'G',pc(r.G),'D',pc(r.D),'W',pc(r.W),'gas',pc(r.gas),'char',pc(r.char),'in',pc(r.inside),'clos',(r.closure*100).toExponential(1),'kWh/kg',(s.Eext/3.6e6/c.mass).toFixed(2),'gasKWh',(s.Egas/3.6e6).toFixed(1));}
run('default',{});
run('sin reflujo',{reflux:false,Pset:1.05e5});
run('HDPE 450 sin reflujo',{mix:{HDPE:1},reflux:false,Pset:1.05e5});
run('HDPE 450 reflujo 350',{mix:{HDPE:1},Tref:623});
run('PP ZSM5 10% 470',{mix:{PP:1},Tsp:743,cat:'ZSM5',catLoad:0.1,Tref:513,Pset:2.5e5});
run('PS 420',{mix:{PS:1},Tsp:693});
run('mix 500 P3',{Tsp:773,Pset:3e5,Pmax:60000});
run('mix 420',{Tsp:693});
run('closed Pset 5.5',{Pset:5.5e5});
