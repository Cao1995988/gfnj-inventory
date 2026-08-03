// 公共请求封装
async function api(url, opts={}) {
  const res = await fetch(url, {
    headers: {'Content-Type':'application/json'},
    credentials: 'same-origin',
    ...opts,
  });
  if (res.status === 401) {
    alert('登录已过期，请重新登录');
    location.href = '/login' + (location.hash ? '?next=' + encodeURIComponent(location.pathname + location.hash) : '');
    return null;
  }
  const data = await res.json().catch(()=>({ok:false,msg:'响应解析失败'}));
  if (!data.ok) {
    alert(data.msg || '操作失败');
    return null;
  }
  return data;
}
const $ = s => document.querySelector(s);
const fmt = n => (Number(n)||0).toFixed(2);
function tag(status) {
  const m = {paid:['paid','已结清'],credit:['credit','欠款'],settled:['settled','已还清']};
  const [cls,txt] = m[status]||['',''];
  return `<span class="tag ${cls}">${txt}</span>`;
}
