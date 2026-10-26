# -*- coding: utf-8 -*-
# 사용법: index.html 과 같은 폴더에서  python patch_relay.py
# 결과:   index.patched.html (전체 파일) 이 생성됩니다. 원본은 index.html.bak 으로 백업됩니다.
import sys, shutil

SRC = sys.argv[1] if len(sys.argv) > 1 else "index.html"
OUT = sys.argv[2] if len(sys.argv) > 2 else "index.patched.html"

NEW_SCRIPT = r'''<script>
(function(){
  var ctx=window.__drip;
  if(!ctx)return;
  var pe=ctx.pe, G=ctx.G;
  function sb(){return ctx.v}
  var btn=document.getElementById("goRelayStories"), back=document.getElementById("relayBack"),
      form=document.getElementById("relayComposer"), input=document.getElementById("relayContent"),
      count=document.getElementById("relayCharCount"), status=document.getElementById("relayStatus"),
      list=document.getElementById("relayStoryList"), submit=document.getElementById("relaySubmit");
  if(!pe.relayStories||!btn||!form)return;
  function msg(t,ok){status.textContent=t||"";status.style.color=ok?"#08734c":"#b4233a";}
  function esc(t){return String(t==null?"":t).replace(/[&<>"']/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]})}
  function dateText(t){var d=new Date(t);return isNaN(d.getTime())?"":d.toLocaleString("ko-KR",{year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit"})}
  input.addEventListener("input",function(){count.textContent=Array.from(input.value).length+" / 100자"});
  async function load(){
    var v=sb();
    list.innerHTML='<p class="sub">이야기를 불러오는 중…</p>';
    if(!v){list.innerHTML='<div class="community-post"><p style="margin:0;color:#b4233a;font-weight:700">Supabase 연결이 없습니다.</p></div>';return}
    try{
      var res=await v.from("relay_stories").select("id,content,author_nickname,created_at").order("created_at",{ascending:true}).limit(300);
      if(res.error)throw res.error;
      var rows=res.data||[];
      if(!rows.length){list.innerHTML='<div class="community-post"><p style="margin:0;color:var(--muted)">아직 이야기가 없어요. 첫 문장을 남겨 주세요!</p></div>';return}
      list.innerHTML=rows.map(function(r,n){
        return '<article class="community-post" style="margin:10px 0;padding:14px 16px">'
          +'<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">'
          +'<span style="display:grid;place-items:center;width:27px;height:27px;flex:none;border-radius:8px;background:#eef4ff;color:#3558a5;font-size:12px;font-weight:800">'+(n+1)+'</span>'
          +'<strong style="font-size:13px">✍️ '+esc(r.author_nickname||"익명 회원")+'</strong>'
          +'<span style="margin-left:auto;color:var(--muted);font-size:11px">🕒 '+esc(dateText(r.created_at))+'</span></div>'
          +'<div style="white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.7">'+esc(r.content)+'</div></article>'
      }).join("");
    }catch(e){
      list.innerHTML='<div class="community-post"><p style="margin:0;color:#b4233a;font-weight:700">릴레이 소설을 불러오지 못했어요. Supabase에 relay_stories 테이블 SQL을 실행했는지 확인해 주세요.</p><p style="font-size:12px;color:var(--muted);overflow-wrap:anywhere">'+esc(e.message||e)+'</p></div>'
    }
  }
  btn.addEventListener("click",function(){G("relayStories");load()});
  back.addEventListener("click",function(){G("main")});
  document.getElementById("relayRefresh").addEventListener("click",load);
  form.addEventListener("submit",async function(e){
    e.preventDefault();
    var v=sb(), content=input.value.trim();
    if(!v){msg("Supabase 연결이 없습니다.");return}
    if(!content){msg("이야기를 입력해 주세요.");return}
    if(Array.from(content).length>100){msg("100자 이내로 작성해 주세요.");return}
    submit.disabled=true;msg("저장 중…",true);
    try{
      var ur=await v.auth.getUser(), user=ur.data&&ur.data.user;
      if(ur.error||!user)throw new Error("로그인이 필요합니다. 다시 로그인해 주세요.");
      var nickname=(user.user_metadata&&user.user_metadata.nickname)||"회원";
      var saved=await v.from("relay_stories").insert({content:content,author_id:user.id,author_nickname:nickname});
      if(saved.error)throw saved.error;
      input.value="";count.textContent="0 / 100자";msg("이야기를 이어 썼어요!",true);await load();
    }catch(err){msg("저장하지 못했어요: "+(err.message||err))}
    finally{submit.disabled=false}
  });
})();
</script>'''

def die(m):
    print("[실패] " + m); sys.exit(1)

with open(SRC, "r", encoding="utf-8") as f:
    html = f.read()

if "window.__drip=" in html:
    die("이미 패치된 파일입니다.")

# 1) 릴레이 섹션을 <main> 밖으로 이동
s = html.find('<section id="relayStoriesView"')
if s < 0: die('relayStoriesView 섹션을 찾지 못했습니다.')
e = html.find('</section>', s)
if e < 0: die('relayStoriesView 닫는 태그를 찾지 못했습니다.')
e += len('</section>')
block = html[s:e]
html = html[:s] + html[e:]
m = html.find('</main>')
if m < 0: die('</main>을 찾지 못했습니다.')
m += len('</main>')
html = html[:m] + "\n" + block + html[m:]

# 2) pe 에 릴레이 화면 등록
a = 'suggest:i("suggestView")}'
if html.count(a) != 1: die('pe 정의(suggest:i("suggestView")})를 정확히 1곳에서 찾지 못했습니다. (%d곳)' % html.count(a))
html = html.replace(a, 'suggest:i("suggestView"),relayStories:i("relayStoriesView")}')

# 3) 메인 스크립트 끝에서 v / pe / G 공개
b = 'n()})()})();'
if html.count(b) != 1: die('메인 스크립트 끝부분을 정확히 1곳에서 찾지 못했습니다. (%d곳)' % html.count(b))
html = html.replace(b, 'n()})(),window.__drip={get v(){return v},pe:pe,G:G}})();')

# 4) 마지막 릴레이 스크립트 교체
k = html.find('pe.relayStories=document.getElementById("relayStoriesView")')
if k < 0: die('기존 릴레이 스크립트를 찾지 못했습니다.')
ss = html.rfind('<script>', 0, k)
se = html.find('</script>', k)
if ss < 0 or se < 0: die('릴레이 스크립트 경계를 찾지 못했습니다.')
se += len('</script>')
html = html[:ss] + NEW_SCRIPT + html[se:]

shutil.copyfile(SRC, SRC + ".bak")
with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)
print("[완료] %s 생성 (원본 백업: %s.bak)" % (OUT, SRC))
