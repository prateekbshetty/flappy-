import base64
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Flappy Face", page_icon="🐤", layout="centered")

ASSETS = Path(__file__).parent / "assets"


def b64(name: str) -> str:
    return "data:image/png;base64," + base64.b64encode((ASSETS / name).read_bytes()).decode()


GAME_HTML = """
<style>
  html,body{margin:0;background:transparent;display:flex;justify-content:center;font-family:'Courier New',monospace}
  #wrap{position:relative;width:480px;max-width:100%}
  canvas{width:100%;height:auto;border:4px solid #2b1010;border-radius:10px;display:block;
         image-rendering:pixelated;touch-action:manipulation;outline:none;background:#3db9f2}
</style>
<div id="wrap"><canvas id="c" width="480" height="640" tabindex="0"></canvas></div>
<script>
const W=480,H=640,GROUND_H=70,GROUND_Y=H-GROUND_H;
const cv=document.getElementById('c'),ctx=cv.getContext('2d');
ctx.imageSmoothingEnabled=false;

function load(src){return new Promise(r=>{const i=new Image();i.onload=()=>r(i);i.src=src;});}
Promise.all([load("__BIRD__"),load("__SCENERY__"),load("__GROUND__")]).then(([bird,scenery,ground])=>start(bird,scenery,ground));

function start(bird,scenery,ground){
  const SC_H=230, SC_W=Math.round(scenery.width*SC_H/scenery.height);
  const GR_W=Math.round(ground.width*GROUND_H/ground.height);
  const BW=66, BH=Math.round(BW*bird.height/bird.width);
  const BX=125, R=21;
  const PIPE_W=72, GAP=165, SPACING=230, SPEED=2.6, GRAV=0.42, FLAP=-7.4, MAXV=10.5;

  let state='ready', bx=BX, by=H/2-40, vy=0, pipes=[], score=0, t=0, offBg=0, offGr=0, shake=0;
  let best=0; try{best=+localStorage.getItem('flappyFaceBest')||0}catch(e){}
  const clouds=[{x:40,y:70,s:4},{x:300,y:140,s:5},{x:520,y:50,s:3}];

  // ---- sound
  let ac=null;
  function beep(f,d,type='square',v=0.05){
    try{ac=ac||new (window.AudioContext||window.webkitAudioContext)();
      const o=ac.createOscillator(),g=ac.createGain();o.type=type;o.frequency.value=f;g.gain.value=v;
      o.connect(g);g.connect(ac.destination);o.start();g.gain.exponentialRampToValueAtTime(0.0001,ac.currentTime+d);o.stop(ac.currentTime+d);}catch(e){}
  }

  function reset(){by=H/2-40;vy=0;pipes=[];score=0;t=0;state='ready';}
  function addPipe(x){
    const min=110,max=GROUND_Y-GAP-110;
    pipes.push({x:x,top:min+Math.random()*(max-min),passed:false});
  }
  function flap(){
    if(state==='ready'){state='play';pipes=[];addPipe(W+60);addPipe(W+60+SPACING);}
    if(state==='play'){vy=FLAP;beep(620,0.08);}
    else if(state==='dead' && t>40){reset();}
  }
  function die(){
    if(state!=='play')return;
    state='dead';t=0;shake=10;beep(140,0.35,'sawtooth',0.07);
    if(score>best){best=score;try{localStorage.setItem('flappyFaceBest',best)}catch(e){}}
  }

  window.addEventListener('keydown',e=>{
    if(['Space','ArrowUp','KeyW'].includes(e.code)){e.preventDefault();if(!e.repeat)flap();}
  });
  cv.addEventListener('pointerdown',e=>{e.preventDefault();cv.focus();flap();});

  // ---- update
  function update(k){
    t+=k;
    if(state!=='dead'){offBg=(offBg+SPEED*0.35*k)%(SC_W/2*1);offGr=(offGr+SPEED*k)%(GR_W/2);}
    clouds.forEach(c=>{c.x-=0.25*k;if(c.x<-120)c.x=W+40;});
    if(state==='ready'){by=H/2-40+Math.sin(t*0.08)*9;vy=0;return;}
    vy=Math.min(vy+GRAV*k,MAXV);by+=vy*k;
    if(state==='play'){
      pipes.forEach(p=>{p.x-=SPEED*k;
        if(!p.passed&&p.x+PIPE_W<bx){p.passed=true;score++;beep(900,0.1,'square',0.04);}});
      if(pipes.length&&pipes[0].x<-PIPE_W-10)pipes.shift();
      const last=pipes[pipes.length-1];
      if(last.x<W-SPACING+60)addPipe(last.x+SPACING);
      if(by+R>=GROUND_Y){by=GROUND_Y-R;die();}
      if(by-R<-40){by=-40+R;vy=0;}
      for(const p of pipes){
        const inX=bx+R>p.x+4&&bx-R<p.x+PIPE_W-4;
        if(inX&&(by-R<p.top||by+R>p.top+GAP)){die();break;}
        // cap overhang
        const capX=bx+R>p.x-4&&bx-R<p.x+PIPE_W+4;
        if(capX&&(by-R<p.top&&by+R>p.top-28||by+R>p.top+GAP&&by-R<p.top+GAP+28)){die();break;}
      }
    } else { // dead: fall
      if(by+R>=GROUND_Y){by=GROUND_Y-R;vy=0;}
    }
    if(shake>0)shake-=k*0.8;
  }

  // ---- drawing
  function cloud(x,y,s){
    ctx.fillStyle='#f7f7ef';
    const rows=[[2,4],[1,7],[0,9],[0,9],[1,8]];
    rows.forEach((r,i)=>ctx.fillRect(x+r[0]*s*2,y+i*s*2,r[1]*s*2,s*2));
    ctx.fillStyle='#bfe3f7';ctx.fillRect(x+2,y+rows.length*s*2-s*2+s,rows[4][1]*s*2,s);
  }
  function pipe(x,y,h,cap){ // cap: 'bottom' (cap at lower end) or 'top' (cap at upper end)
    const o='#2b1010';
    function body(bx,by,bw,bh){
      ctx.fillStyle=o;ctx.fillRect(bx-3,by,bw+6,bh);
      const g=ctx.createLinearGradient(bx,0,bx+bw,0);
      g.addColorStop(0,'#c8ff4a');g.addColorStop(0.18,'#a6ee2a');g.addColorStop(0.55,'#74e01c');g.addColorStop(1,'#2e9c18');
      ctx.fillStyle=g;ctx.fillRect(bx,by,bw,bh);
    }
    const CH=28,ex=6;
    if(cap==='bottom'){
      body(x+4,y,PIPE_W-8,h-CH+2);
      ctx.fillStyle=o;ctx.fillRect(x-ex-3,y+h-CH,PIPE_W+ex*2+6,CH+3);
      const g=ctx.createLinearGradient(x-ex,0,x+PIPE_W+ex,0);
      g.addColorStop(0,'#c8ff4a');g.addColorStop(0.2,'#a6ee2a');g.addColorStop(0.55,'#74e01c');g.addColorStop(1,'#2e9c18');
      ctx.fillStyle=g;ctx.fillRect(x-ex,y+h-CH+3,PIPE_W+ex*2,CH-3);
    }else{
      body(x+4,y+CH-2,PIPE_W-8,h-CH+2);
      ctx.fillStyle=o;ctx.fillRect(x-ex-3,y-3,PIPE_W+ex*2+6,CH+3);
      const g=ctx.createLinearGradient(x-ex,0,x+PIPE_W+ex,0);
      g.addColorStop(0,'#c8ff4a');g.addColorStop(0.2,'#a6ee2a');g.addColorStop(0.55,'#74e01c');g.addColorStop(1,'#2e9c18');
      ctx.fillStyle=g;ctx.fillRect(x-ex,y,PIPE_W+ex*2,CH-3);
    }
  }
  function tileX(img,w,h,y,off){
    let x=-off;while(x<W){ctx.drawImage(img,x,y,w,h);x+=w;}
  }
  function text(s,x,y,size,align='center'){
    ctx.font='bold '+size+'px "Courier New",monospace';ctx.textAlign=align;
    ctx.lineWidth=Math.max(4,size/6);ctx.strokeStyle='#2b1010';ctx.strokeText(s,x,y);
    ctx.fillStyle='#fff';ctx.fillText(s,x,y);
  }
  function draw(){
    ctx.save();
    if(shake>0)ctx.translate((Math.random()-.5)*shake,(Math.random()-.5)*shake);
    // sky
    const g=ctx.createLinearGradient(0,0,0,GROUND_Y);
    g.addColorStop(0,'#3db9f2');g.addColorStop(1,'#58ccf6');
    ctx.fillStyle=g;ctx.fillRect(-10,-10,W+20,H+20);
    clouds.forEach(c=>cloud(c.x,c.y,c.s));
    // scenery from reference image (seamless mirrored tile)
    tileX(scenery,SC_W,SC_H,GROUND_Y-SC_H,offBg);
    // pipes
    pipes.forEach(p=>{
      pipe(p.x,-4,p.top+4,'bottom');
      pipe(p.x,p.top+GAP,GROUND_Y-(p.top+GAP),'top');
    });
    // ground
    tileX(ground,GR_W,GROUND_H,GROUND_Y,offGr);
    // bird
    ctx.save();ctx.translate(bx,by);
    const ang=state==='ready'?0:Math.max(-0.45,Math.min(1.3,vy*0.07));
    ctx.rotate(ang);ctx.imageSmoothingEnabled=true;
    ctx.drawImage(bird,-BW*0.52,-BH*0.5,BW,BH);
    ctx.restore();
    ctx.restore();
    // HUD
    if(state==='play')text(score,W/2,90,56);
    if(state==='ready'){
      text('FLAPPY FACE',W/2,150,46);
      text('Tap / Click / Space',W/2,GROUND_Y-120,22);
      text('to flap',W/2,GROUND_Y-92,22);
      if(best)text('Best: '+best,W/2,GROUND_Y-50,22);
    }
    if(state==='dead'){
      ctx.fillStyle='rgba(0,0,0,0.25)';ctx.fillRect(0,0,W,H);
      text('GAME OVER',W/2,210,50);
      ctx.fillStyle='#f6e7a8';ctx.strokeStyle='#2b1010';ctx.lineWidth=4;
      ctx.fillRect(W/2-120,250,240,130);ctx.strokeRect(W/2-120,250,240,130);
      ctx.fillStyle='#2b1010';ctx.font='bold 22px "Courier New"';ctx.textAlign='center';
      ctx.fillText('SCORE  '+score,W/2,305);ctx.fillText('BEST   '+best,W/2,350);
      if(t>40)text('Tap to restart',W/2,440,26);
    }
  }

  let last=performance.now();
  function loop(now){
    const k=Math.min((now-last)/16.667,2.5);last=now;
    update(k);draw();requestAnimationFrame(loop);
  }
  requestAnimationFrame(loop);
  cv.focus();
}
</script>
"""

html = (
    GAME_HTML.replace("__BIRD__", b64("bird.png"))
    .replace("__SCENERY__", b64("scenery.png"))
    .replace("__GROUND__", b64("ground.png"))
)

st.markdown("<h2 style='text-align:center'>🐤 Flappy Face</h2>", unsafe_allow_html=True)
components.html(html, height=680)
st.caption("Click the game once to focus it, then tap / click / press Space or ↑ to flap.")
