let scanned = []; // [{code, name, unit, stock, qty}]
let scanning = false;
let videoStream = null;
let scanCanvas = null;
let scanFrameCount = 0;
let scanEngineReady = false;

function renderList(){
  const dir = $('#f-direction').value;
  $('#tbl tbody').innerHTML = scanned.map((it,i)=>{
    const after = dir==='in' ? it.stock + it.qty : it.stock - it.qty;
    const warn = dir==='out' && it.stock < it.qty;
    return `<tr>
      <td>${it.code}</td><td>${it.name}</td>
      <td>${it.stock} ${it.unit||''}</td>
      <td><input type="number" step="0.01" value="${it.qty}" style="width:70px" oninput="updateQty(${i},this.value)"></td>
      <td style="color:${warn?'#c33':'#155724'};font-weight:bold">${warn?'不足':(after.toFixed(2)+' '+ (it.unit||''))}</td>
      <td><button class="btn small danger" onclick="scanned.splice(${i},1);renderList()">删</button></td>
    </tr>`;
  }).join('') || '<tr><td colspan="6">还没有扫码添加商品</td></tr>';
  $('#count').textContent = scanned.length;
}
function updateQty(i,v){ scanned[i].qty = +v||0; 
function showToast(msg, type){
  const t = document.createElement("div");
  t.textContent = msg;
  t.style.cssText = "position:fixed;top:20px;left:50%;transform:translateX(-50%);padding:12px 24px;border-radius:8px;color:#fff;font-size:16px;font-weight:bold;z-index:9999;animation:fadeInOut 2.5s ease;white-space:nowrap;pointer-events:none;";
  t.style.background = type==="success" ? "#1e6b3a" : "#e76f51";
  document.body.appendChild(t);
  setTimeout(()=>{ t.style.opacity="0"; t.style.transition="opacity 0.5s"; }, 2000);
  setTimeout(()=>{ t.remove(); }, 2500);
}
renderList(); }
function clearList(){ scanned = []; 
function showToast(msg, type){
  const t = document.createElement("div");
  t.textContent = msg;
  t.style.cssText = "position:fixed;top:20px;left:50%;transform:translateX(-50%);padding:12px 24px;border-radius:8px;color:#fff;font-size:16px;font-weight:bold;z-index:9999;animation:fadeInOut 2.5s ease;white-space:nowrap;pointer-events:none;";
  t.style.background = type==="success" ? "#1e6b3a" : "#e76f51";
  document.body.appendChild(t);
  setTimeout(()=>{ t.style.opacity="0"; t.style.transition="opacity 0.5s"; }, 2000);
  setTimeout(()=>{ t.remove(); }, 2500);
}
renderList(); }
function manualAdd(){ $('#m-code').value=''; $('#m-qty').value=1; $('#manual').showModal(); }
async function addManual(e){
  e.preventDefault();
  const code = $('#m-code').value.trim();
  const qty = +$('#m-qty').value;
  await addByCode(code, qty);
  $('#manual').close();
}
async function addByCode(code, qty){
  if(!code) { alert('编码不能为空'); return; }
  qty = qty || 1;
  const status = $('#scan-status');
  status.style.display = 'block';
  status.textContent = `正在查找商品：${code}…`;
  const d = await api('/api/products/by-code/'+encodeURIComponent(code));
  if(!d){
    // api() 已经弹了错误提示，这里更新状态栏
    status.textContent = `未找到编码 ${code} 对应的商品，请检查编码是否正确`;
    status.style.background = '#fff3cd';
    status.style.color = '#856404';
    return;
  }
  const p = d.data;
  const exist = scanned.find(s=>s.code===code);
  if(exist){ exist.qty += qty; }
  else { scanned.push({code, name:p.name, unit:p.unit, stock:p.stock, qty}); }
  status.textContent = `✅ 已添加：${p.name}（${code}）`;
  status.style.background = '#e8f5e9';
  status.style.color = '#1e6b3a';
  
function showToast(msg, type){
  const t = document.createElement("div");
  t.textContent = msg;
  t.style.cssText = "position:fixed;top:20px;left:50%;transform:translateX(-50%);padding:12px 24px;border-radius:8px;color:#fff;font-size:16px;font-weight:bold;z-index:9999;animation:fadeInOut 2.5s ease;white-space:nowrap;pointer-events:none;";
  t.style.background = type==="success" ? "#1e6b3a" : "#e76f51";
  document.body.appendChild(t);
  setTimeout(()=>{ t.style.opacity="0"; t.style.transition="opacity 0.5s"; }, 2000);
  setTimeout(()=>{ t.remove(); }, 2500);
}
renderList();
}

// 检测运行环境
function detectEnv(){
  const ua = navigator.userAgent.toLowerCase();
  const isWeixin = ua.indexOf('micromessenger') > -1;
  const isIOS = /iphone|ipad|ipod/.test(ua);
  const isAndroid = /android/.test(ua);
  const isHuawei = /huawei|hon|honor/.test(ua) || /hbpc/.test(ua);
  return { isWeixin, isIOS, isAndroid, isHuawei };
}

// ---------- 摄像头扫码（jsQR 全平台兼容）----------
async function startScan(){
  const env = detectEnv();
  const area = $('#scan-area');
  const video = $('#video');

  // 微信内置浏览器 iOS：getUserMedia 受限
  if(env.isWeixin && !env.isAndroid){
    showWeixinGuide();
    return;
  }

  area.style.display = 'block';
  $('#scan-status').style.display = 'block';
  $('#scan-status').textContent = '正在启动摄像头…';

  // 检查 getUserMedia 是否存在
  if(!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia){
    $('#scan-status').textContent = '当前浏览器不支持摄像头扫码';
    area.style.display = 'none';
    let tip = '当前浏览器不支持自动扫码识别，可点「手动输入编码」，或拍下二维码后人工识别编码再录入';
    if(env.isWeixin){
      tip = '微信内置浏览器无法调用摄像头，请点右上角「···」→ 用浏览器打开本页面后再扫码，或直接用「手动输入编码」';
    }
    alert(tip);
    return;
  }

  // 检查扫码引擎是否可用
  const hasBarcodeDetector = typeof window.BarcodeDetector !== 'undefined';
  const hasJsQR = typeof window.jsQR === 'function';
  if(!hasBarcodeDetector && !hasJsQR){
    area.style.display = 'none';
    $('#scan-status').textContent = '扫码引擎加载失败';
    alert('扫码识别引擎未能加载，请检查网络后刷新页面重试。\n\n也可以点「手动输入编码」直接录入商品编码。');
    return;
  }
  scanEngineReady = true;

  // 请求后置摄像头
  try{
    const constraints = { video: { facingMode: { ideal: 'environment' } } };
    videoStream = await navigator.mediaDevices.getUserMedia(constraints);
    video.srcObject = videoStream;
    // iOS 需要属性设置才能播放
    video.setAttribute('playsinline', true);
    video.setAttribute('muted', true);
    video.setAttribute('autoplay', true);
    await video.play();
    $('#scan-status').textContent = '摄像头已就绪，将商品二维码/条码对准画面';
  }catch(err){
    area.style.display = 'none';
    $('#scan-status').style.display = 'none';
    let tip = '无法打开摄像头：' + err.message;
    if(env.isWeixin){
      tip += '\n\n微信内打开请点右上角「···」→ 用浏览器打开本页面后再扫码，或直接用「手动输入编码」';
    } else if(env.isIOS){
      tip += '\n\n请用 Safari 打开本页面，并允许摄像头权限';
    }
    tip += '\n\n也可以点「手动输入编码」直接录入';
    alert(tip);
    return;
  }

  // 准备 canvas 用于抓帧
  scanCanvas = document.createElement('canvas');
  scanning = true;
  scanFrameCount = 0;

  // 等 video 有画面再开始识别
  const beginDetect = ()=>{
    if(!scanning) return;
    if(video.readyState >= 2 && video.videoWidth > 0){
      detectLoop();
    } else {
      setTimeout(beginDetect, 200);
    }
  };
  beginDetect();
}

async function detectLoop(){
  if(!scanning) return;
  const video = $('#video');
  if(video.readyState >= 2 && video.videoWidth > 0){
    scanFrameCount++;
    const w = video.videoWidth, h = video.videoHeight;
    scanCanvas.width = w;
    scanCanvas.height = h;
    const ctx = scanCanvas.getContext('2d', { willReadFrequently: true });
    ctx.drawImage(video, 0, 0, w, h);
    let foundCode = null;
    try{
      const imgData = ctx.getImageData(0, 0, w, h);
      // 优先用原生 BarcodeDetector（安卓 Chrome/华为浏览器支持好，速度快）
      if(window.BarcodeDetector){
        try{
          const detector = window._bd = window._bd || new BarcodeDetector({formats:['qr_code','code_128','code_39','ean_13','ean_8','upc_a','upc_e','itf','codabar']});
          const codes = await detector.detect(video);
          if(codes && codes.length){
            foundCode = codes[0].rawValue;
          }
        }catch(e){ /* 回退到 jsQR */ }
      }
      // jsQR 兜底（iOS Safari、所有浏览器全兼容二维码）
      if(!foundCode && window.jsQR){
        const qr = jsQR(imgData.data, w, h, { inversionAttempts:'attemptBoth' });
        if(qr){
          foundCode = qr.data;
        }
      }
    }catch(e){ /* ignore frame errors */ }
    if(foundCode){
      handleCode(foundCode);
      return;
    }
    // 每 150 帧（约 5 秒）提示一次
    if(scanFrameCount % 150 === 0){
      const status = $('#scan-status');
      status.textContent = '摄像头运行中… 请将二维码/条码对准画面中央';
      status.style.background = '#e3f2fd';
      status.style.color = '#1565c0';
    }
  }
  if(scanning) requestAnimationFrame(detectLoop);
}

async function handleCode(text){
  if(!text) { if(scanning) requestAnimationFrame(detectLoop); return; }
  // 商品编码可能是 url 末尾或纯编码
  let code = text;
  if(text.includes('/p/')) code = text.split('/p/').pop();
  // 去掉可能的换行和空白
  code = code.trim();
  const status = $('#scan-status');
  status.style.display = 'block';
  status.textContent = `已识别：${code}，正在查找商品…`;
  status.style.background = '#e3f2fd';
  status.style.color = '#1565c0';
  await addByCode(code, 1);
  if(navigator.vibrate) navigator.vibrate(100);
  // 停顿 1.2 秒避免重复扫
  setTimeout(()=>{ if(scanning) requestAnimationFrame(detectLoop); }, 1200);
}

function stopScan(){
  scanning = false;
  $('#scan-area').style.display = 'none';
  const status = $('#scan-status');
  status.style.display = 'none';
  status.style.background = '#e8f5e9';
  status.style.color = '#1e6b3a';
  if(videoStream){ videoStream.getTracks().forEach(t=>t.stop()); videoStream=null; }
}

// 微信内置浏览器引导
function showWeixinGuide(){
  const html = `<div style="text-align:left;line-height:1.8">
    <p style="font-weight:bold;color:#1e6b3a;margin-bottom:8px">微信内扫码方式</p>
    <p>微信内置浏览器无法直接调用摄像头连续扫码，请选一种方式：</p>
    <p><b>方式一（推荐）：用微信扫一扫识别二维码</b><br>
    1. 点微信右上角「+」→「扫一扫」<br>
    2. 扫商品二维码 → 系统自动跳转到扫码入库页面<br>
    3. 确认商品和数量后点「提交」即可入库/出库</p>
    <p><b>方式二：跳出微信用浏览器扫码</b><br>
    1. 点右上角「···」→「在浏览器打开」（iOS Safari / 华为浏览器）<br>
    2. 在浏览器里点「📷 扫码添加」即可自动识别</p>
    <p><b>方式三：直接手动输入</b><br>
    点下方「手动输入编码」按钮，输入商品编码</p>
  </div>`;
  const dlg = document.createElement('dialog');
  dlg.className = 'modal';
  dlg.innerHTML = html + `<div class="dlg-actions"><button class="primary" onclick="this.closest('dialog').close()">知道了</button></div>`;
  document.body.appendChild(dlg);
  // 播放音效提示
  try {
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.connect(gain); gain.connect(audioCtx.destination);
    gain.gain.value = 0.15;
    // 统计成功数量决定音调
    const okCount = r.results.filter(it=>it.ok).length;
    if(okCount === r.results.length && okCount > 0){
      osc.frequency.value = 880; osc.type = "sine";
      osc.start(); osc.stop(audioCtx.currentTime + 0.15);
      setTimeout(()=>{ osc.frequency.value = 1100; osc.start(); osc.stop(audioCtx.currentTime + 0.3); }, 150);
      showToast("✅ "+okCount+" 件商品 "+r.direction+"成功", "success");
    } else {
      osc.frequency.value = 300; osc.type = "square";
      osc.start(); osc.stop(audioCtx.currentTime + 0.3);
      showToast("⚠️ 部分操作失败，请查看详情", "warn");
    }
  } catch(e) {}
  dlg.showModal();
  dlg.addEventListener('close', ()=>dlg.remove());
}

async function submit(){
  if(!scanned.length){ alert('请先扫码或手动添加至少一个商品'); return; }
  const direction = $('#f-direction').value;
  const body = {
    direction,
    items: scanned.map(s=>({code:s.code, quantity:s.qty})),
  };
  const d = await api('/api/scan/stockmove', {method:'POST', body:JSON.stringify(body)});
  if(!d) return;
  const r = d.data;
  let html = `<h3>${direction==='in'?'入库':'出库'}完成</h3>`;
  html += `<p>操作人: ${r.operator} &nbsp; 时间: ${r.time}</p>`;
  html += '<div class="table-wrap"><table class="data-table"><thead><tr><th>编码</th><th>结果</th><th>名称</th><th>原库存</th><th>新库存</th></tr></thead><tbody>';
  r.results.forEach(it=>{
    if(it.ok){
      html += `<tr><td>${it.code}</td><td><span class="tag paid">成功</span></td><td>${it.name}</td><td>${it.before}</td><td>${it.after}</td></tr>`;
    }else{
      html += `<tr><td>${it.code}</td><td><span class="tag credit">失败</span></td><td colspan="3">${it.msg}</td></tr>`;
    }
  });
  html += '</tbody></table></div>';
  html += `<div class="dlg-actions"><button class="primary" onclick="document.getElementById('result').close();clearList();">确定</button></div>`;
  const dlg = document.createElement('dialog');
  dlg.id='result';
  dlg.className='modal large';
  dlg.innerHTML = html;
  document.body.appendChild(dlg);
  // 播放音效提示
  try {
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.connect(gain); gain.connect(audioCtx.destination);
    gain.gain.value = 0.15;
    // 统计成功数量决定音调
    const okCount = r.results.filter(it=>it.ok).length;
    if(okCount === r.results.length && okCount > 0){
      osc.frequency.value = 880; osc.type = "sine";
      osc.start(); osc.stop(audioCtx.currentTime + 0.15);
      setTimeout(()=>{ osc.frequency.value = 1100; osc.start(); osc.stop(audioCtx.currentTime + 0.3); }, 150);
      showToast("✅ "+okCount+" 件商品 "+r.direction+"成功", "success");
    } else {
      osc.frequency.value = 300; osc.type = "square";
      osc.start(); osc.stop(audioCtx.currentTime + 0.3);
      showToast("⚠️ 部分操作失败，请查看详情", "warn");
    }
  } catch(e) {}
  dlg.showModal();
  dlg.addEventListener('close',()=>{ dlg.remove(); clearList(); });
}

// ---------- 初始化：检查 URL hash 是否有 code（微信扫一扫入口）----------
async function initFromHash(){
  const hash = location.hash;
  if(hash && hash.startsWith('#code=')){
    const code = decodeURIComponent(hash.substring(6));
    // 清掉 hash 避免刷新重复添加
    history.replaceState(null, '', location.pathname);
    if(code){
      const status = $('#scan-status');
      status.style.display = 'block';
      status.textContent = `微信扫一扫识别到编码：${code}，正在添加商品…`;
      await addByCode(code, 1);
      // 5 秒后自动隐藏提示
      setTimeout(()=>{ status.style.display = 'none'; }, 5000);
    }
  }
}


function showToast(msg, type){
  const t = document.createElement("div");
  t.textContent = msg;
  t.style.cssText = "position:fixed;top:20px;left:50%;transform:translateX(-50%);padding:12px 24px;border-radius:8px;color:#fff;font-size:16px;font-weight:bold;z-index:9999;animation:fadeInOut 2.5s ease;white-space:nowrap;pointer-events:none;";
  t.style.background = type==="success" ? "#1e6b3a" : "#e76f51";
  document.body.appendChild(t);
  setTimeout(()=>{ t.style.opacity="0"; t.style.transition="opacity 0.5s"; }, 2000);
  setTimeout(()=>{ t.remove(); }, 2500);
}
renderList();
initFromHash();
