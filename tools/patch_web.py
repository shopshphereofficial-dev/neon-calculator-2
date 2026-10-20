#!/usr/bin/env python3
"""Apply Android-hardening patches to www/index.html, preserving the original neon UI.

Every replacement is asserted so a silent no-op can never ship.
"""
import io, os, sys

SRC = "/scratch/work/neon/Neon_Calculator_2_Source/index.html"
DST = "/scratch/work/proj/www/index.html"

html = io.open(SRC, encoding="utf-8").read()


def sub(old, new, count=1):
    global html
    n = html.count(old)
    assert n == count, f"expected {count} match(es), found {n} for: {old[:70]!r}"
    html = html.replace(old, new)


# --- 1. Native-feel body: no rubber-band scroll, no tap flash -----------------
sub(
    "*{box-sizing:border-box}body{margin:0;min-height:100vh;",
    "*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}body{margin:0;min-height:100vh;"
    "overscroll-behavior:none;-webkit-tap-highlight-color:transparent;"
    "-webkit-touch-callout:none;",
)

# --- 2. Edge-to-edge safe areas (status bar / gesture nav / display cutouts) --
sub(
    ".app{max-width:520px;margin:auto;padding:22px 15px 26px}",
    ".app{max-width:520px;margin:auto;padding:calc(22px + env(safe-area-inset-top)) "
    "calc(15px + env(safe-area-inset-right)) calc(26px + env(safe-area-inset-bottom)) "
    "calc(15px + env(safe-area-inset-left))}",
)
sub(
    "@media(max-width:370px){.app{padding:16px 10px}",
    "@media(max-width:370px){.app{padding:calc(16px + env(safe-area-inset-top)) "
    "calc(10px + env(safe-area-inset-right)) calc(16px + env(safe-area-inset-bottom)) "
    "calc(10px + env(safe-area-inset-left))}",
)

# --- 3. Keys behave like native buttons, not like selectable text -------------
sub(
    "box-shadow:0 3px 0 #080a13;touch-action:manipulation;-webkit-tap-highlight-color:transparent}",
    "box-shadow:0 3px 0 #080a13;touch-action:manipulation;-webkit-tap-highlight-color:transparent;"
    "user-select:none;-webkit-user-select:none;touch-action:manipulation}",
)

# --- 3b. BUGFIX: `ln(` was rewritten to `Math.log(` and the later `log(` rule
# then corrupted it into `Math.Math.log10(`. Apply `log(` first (safe: `Math.log10(`
# contains no `log(` substring), then `ln(`.
sub(
    ".replace(/ln\\(/g,'Math.log(').replace(/log\\(/g,'Math.log10(')",
    ".replace(/log\\(/g,'Math.log10(').replace(/ln\\(/g,'Math.log(')",
)

# --- 4. State: sound preference + history survive app restarts (offline only) --
sub(
    "let expr='', result='0', evaluated=false, sound=true, scientific=false, history=[];",
    "let expr='', result='0', evaluated=false, scientific=false, history=[];\n"
    "/* Local-only persistence: WebView localStorage. No network, no analytics. */\n"
    "const store={get(k,d){try{const v=localStorage.getItem('neoncalc.'+k);return v===null?d:JSON.parse(v)}catch(e){return d}},"
    "set(k,v){try{localStorage.setItem('neoncalc.'+k,JSON.stringify(v))}catch(e){}}};\n"
    "let sound=store.get('sound',true);",
)

# --- 5. Persist on change -----------------------------------------------------
sub(
    "history=history.slice(0,50);expr=result;evaluated=true;renderHistory()}",
    "history=history.slice(0,50);store.set('history',history);expr=result;evaluated=true;renderHistory()}",
)
sub(
    "$('soundBtn').onclick=()=>{sound=!sound;$('soundBtn').textContent=sound?'\u266b Sound on':'\u266b Sound off';if(sound)tone('\u266a')};",
    "$('soundBtn').onclick=()=>{sound=!sound;store.set('sound',sound);"
    "$('soundBtn').textContent=sound?'\u266b Sound on':'\u266b Sound off';if(sound)tone('\u266a')};",
)
sub(
    "c.onclick=()=>{history=[];renderHistory()}",
    "c.onclick=()=>{history=[];store.set('history',history);renderHistory()}",
)

# --- 6. Boot: restore history + sound label, unlock audio on first touch ------
sub(
    "['amount','fromUnit','toUnit'].forEach(id=>$(id).addEventListener('input',convert));"
    "$('swap').onclick=()=>{let a=$('fromUnit').value;"
    "$('fromUnit').value=$('toUnit').value;$('toUnit').value=a;convert();tone('swap')};fillUnits();",
    "['amount','fromUnit','toUnit'].forEach(id=>$(id).addEventListener('input',convert));"
    "$('swap').onclick=()=>{let a=$('fromUnit').value;"
    "$('fromUnit').value=$('toUnit').value;$('toUnit').value=a;convert();tone('swap')};fillUnits();\n"
    "/* --- native shell boot --- */\n"
    "history=Array.isArray(store.get('history',[]))?store.get('history',[]).slice(0,50):[];\n"
    "renderHistory();\n"
    "$('soundBtn').textContent=sound?'\u266b Sound on':'\u266b Sound off';\n"
    "/* Android WebView needs a real user gesture before audio may play. */\n"
    "function unlockAudio(){try{const C=window.AudioContext||window.webkitAudioContext;"
    "if(C&&!window.audioCtx)window.audioCtx=new C();if(window.audioCtx&&window.audioCtx.state==='suspended')"
    "window.audioCtx.resume()}catch(e){}}\n"
    "['pointerdown','touchstart','keydown'].forEach(ev=>document.addEventListener(ev,unlockAudio,"
    "{once:true,passive:true}));\n"
    "document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')unlockAudio()});\n"
    "/* Block navigation away from the bundled app (offline, no external links). */\n"
    "window.addEventListener('dragover',e=>e.preventDefault());",
)

# --- 7. Viewport: cover the cutout, allow zoom-free native feel ---------------
sub(
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
    '<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, '
    'user-scalable=no, viewport-fit=cover">',
)
sub(
    '<meta name="theme-color" content="#090b17">',
    '<meta name="theme-color" content="#090b17">\n'
    '<meta name="color-scheme" content="dark">\n'
    '<meta name="mobile-web-app-capable" content="yes">',
)

io.open(DST, "w", encoding="utf-8").write(html)
print("patched", DST, len(html), "bytes")
