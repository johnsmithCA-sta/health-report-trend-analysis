#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
健康管理工作台生成器
读取 data/trend_analysis.json，生成单文件、离线可用、无云存储的交互式 HTML 工作台：
- 健康总览（来自体检趋势报告"一、健康总览"）
- 趋势折线图 + 参考范围区间带（SVG 自绘，无外部依赖）
- 指标筛选（分类 + 健康方向 + 只看异常/显著变化）
- 指标分组显示：趋好 / 趋坏 / 复杂 三组
- 时间跨度切换（近2年/近3年/全部）
- 异常高亮、变化健康方向标注、临床意义与分层建议
输出: output/health_dashboard.html
"""
import json
import os

BASE = os.environ.get("WORK_DIR") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TREND_PATH = os.path.join(BASE, "data", "trend_analysis.json")
OUT_DIR = os.path.join(BASE, "output")
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PATH = os.path.join(OUT_DIR, "health_dashboard.html")

with open(TREND_PATH, encoding="utf-8") as f:
    trend = json.load(f)

DATA_JSON = json.dumps(trend, ensure_ascii=False)

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>健康管理工作台 · 体检指标趋势分析</title>
<style>
:root{
  --bg:#f5f7fa; --card:#ffffff; --border:#e3e8ef; --text:#1f2937; --muted:#6b7280;
  --blue:#1a73e8; --red:#d93025; --red-bg:#fdecea; --green:#188038; --green-bg:#e6f4ea; --amber:#b06000; --amber-bg:#fef7e0;
  --band:#e8f0fe; --grid:#e5e7eb; --purple:#7c3aed;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;padding:24px;line-height:1.6}
.container{max-width:1180px;margin:0 auto}
header{background:linear-gradient(135deg,#1a73e8,#0d47a1);color:#fff;border-radius:14px;padding:24px 28px;margin-bottom:20px}
header h1{font-size:22px;font-weight:700}
header .sub{margin-top:6px;font-size:13px;opacity:.9}
header .privacy{margin-top:10px;font-size:12px;background:rgba(255,255,255,.14);border-radius:8px;padding:8px 12px;display:inline-block}
.overview{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:20px}
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px 16px}
.card .label{font-size:12px;color:var(--muted)}
.card .val{font-size:20px;font-weight:700;margin-top:4px}
.card .meta{font-size:11px;color:var(--muted);margin-top:2px}
.badge{display:inline-block;font-size:11px;border-radius:10px;padding:1px 8px;margin-left:6px;vertical-align:2px}
.badge-up{background:var(--red-bg);color:var(--red)}
.badge-ok{background:var(--green-bg);color:var(--green)}
.badge-down{background:#eef2f6;color:var(--muted)}
.badge-trend{background:var(--amber-bg);color:var(--amber)}
.health-overview{margin-bottom:20px}
.health-overview h2{font-size:16px;margin-bottom:10px;display:flex;align-items:center;gap:8px}
.health-overview h2::before{content:"📋";font-size:18px}
.health-overview .card{padding:18px 22px}
.summary-line{font-size:13.5px;line-height:1.85;color:var(--text);margin-bottom:12px;padding:12px 16px;background:linear-gradient(90deg,#fef9e7,#fefefe);border-left:3px solid var(--amber);border-radius:0 10px 10px 0}
.summary-line b{color:var(--amber)}
.ov-table{width:100%;border-collapse:collapse;font-size:13px;margin-top:6px}
.ov-table th, .ov-table td{border:1px solid var(--border);padding:7px 10px;text-align:left;vertical-align:top}
.ov-table th{background:#fafbfc;font-weight:600;color:var(--muted);width:96px;font-size:12px}
.ov-table .direction{display:inline-block;font-size:11px;border-radius:8px;padding:1px 7px;font-weight:600;margin-left:4px;vertical-align:1px}
.ov-table .d-good{background:var(--green-bg);color:var(--green)}
.ov-table .d-bad{background:var(--red-bg);color:var(--red)}
.ov-table .d-mid{background:#eef2f6;color:var(--muted)}
.layout{display:grid;grid-template-columns:300px 1fr;gap:20px}
@media(max-width:900px){.layout{grid-template-columns:1fr}}
.sidebar .card{padding:0;overflow:hidden;margin-bottom:14px}
.sidebar .card h3{font-size:14px;padding:12px 16px;border-bottom:1px solid var(--border);background:#fafbfc}
.side-filter{padding:10px 12px;border-bottom:1px solid var(--border)}
.side-filter label{font-size:12px;color:var(--muted);display:block;margin-bottom:4px}
.side-filter select, .side-filter input[type=checkbox]{font-size:13px}
.side-filter select{width:100%;padding:6px 8px;border:1px solid var(--border);border-radius:8px;background:#fff;color:var(--text)}
.chk-row{display:flex;gap:10px;flex-wrap:wrap;margin-top:4px}
.chk-row label{display:flex;align-items:center;gap:4px;color:var(--text);font-size:12px;cursor:pointer;margin:0}
.chk-row input{width:auto!important}
.group-section{border-bottom:1px solid var(--border)}
.group-section:last-child{border-bottom:none}
.group-head{display:flex;justify-content:space-between;align-items:center;padding:10px 14px;cursor:pointer;background:#fafbfc;font-size:13px;font-weight:600;user-select:none}
.group-head:hover{background:#f1f5fa}
.group-head .arrow{transition:transform .2s;color:var(--muted)}
.group-section.collapsed .arrow{transform:rotate(-90deg)}
.group-section.collapsed .group-body{display:none}
.group-body{max-height:280px;overflow-y:auto;padding:4px 8px}
.group-body .indic-item{display:flex;align-items:center;gap:6px;padding:6px 10px;border-radius:6px;cursor:pointer;font-size:12.5px;border:1px solid transparent;margin-bottom:2px}
.group-body .indic-item:hover{background:#f0f4fa}
.group-body .indic-item.active{background:#e8f0fe;border-color:#aecbfa}
.group-body .indic-item .name{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.group-body .indic-item .cat{font-size:10px;color:var(--muted);background:#f1f3f5;padding:0 5px;border-radius:6px;flex-shrink:0}
.group-body .indic-item .arr{font-size:11px;font-weight:700;flex-shrink:0;width:14px;text-align:center}
.group-good .group-head{color:var(--green)}
.group-bad .group-head{color:var(--red)}
.group-mid .group-head{color:var(--amber)}
.arr-up{color:var(--red)} .arr-down{color:var(--green)} .arr-eq{color:var(--muted)}
.main .card{padding:20px 24px;margin-bottom:20px}
.chart-head{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px;flex-wrap:wrap;gap:10px}
.chart-head h2{font-size:17px}
.chart-head .info{font-size:12px;color:var(--muted)}
.range-switch{display:flex;gap:6px;margin-top:8px}
.range-switch button{border:1px solid var(--border);background:#fff;border-radius:8px;padding:5px 12px;font-size:12px;cursor:pointer;color:var(--text)}
.range-switch button.active{background:var(--blue);color:#fff;border-color:var(--blue)}
.chart-wrap{width:100%;overflow-x:auto}
svg text{font-family:inherit}
.legend{display:flex;gap:16px;font-size:12px;color:var(--muted);margin-top:8px;flex-wrap:wrap}
.legend span{display:inline-flex;align-items:center;gap:5px}
.dot{width:10px;height:10px;border-radius:50%;display:inline-block}
.dot-normal{background:var(--blue)}
.dot-ab{background:var(--red)}
.dot-sig{background:var(--amber)}
.band-sample{width:18px;height:10px;background:var(--band);border:1px solid #b3c9ee;display:inline-block;border-radius:2px}
.desc{margin-top:14px;padding-top:14px;border-top:1px solid var(--border);font-size:13px;color:var(--text)}
.desc .clinical{background:#f8fafc;border-left:3px solid var(--blue);padding:10px 14px;border-radius:0 8px 8px 0;margin-bottom:10px}
.advice{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;margin-top:10px}
.advice .a-item{background:#f8fafc;border-radius:10px;padding:10px 12px;font-size:12.5px}
.advice .a-item b{display:block;font-size:12px;color:var(--blue);margin-bottom:4px}
.advice .see-doctor{border-left:3px solid var(--red)}
table.data-table{width:100%;border-collapse:collapse;margin-top:12px;font-size:13px}
table.data-table th, table.data-table td{border:1px solid var(--border);padding:6px 10px;text-align:center}
table.data-table th{background:#f8fafc;font-weight:600;font-size:12px}
td.ab{color:var(--red);font-weight:700}
td.normal{color:var(--text)}
td.miss{color:#c0c6cf}
.chg-row{display:flex;align-items:center;gap:8px;padding:4px 0;font-size:12.5px;color:var(--muted)}
.chg-row .tag-good{color:var(--green);font-weight:600}
.chg-row .tag-bad{color:var(--red);font-weight:600}
.chg-row .tag-neutral{color:var(--muted)}
.note{font-size:12px;color:var(--muted);margin-top:12px}
.empty{padding:40px;text-align:center;color:var(--muted)}
footer{margin-top:24px;text-align:center;font-size:12px;color:var(--muted)}
</style>
</head>
<body>
<div class="container">
<header>
  <h1>🏥 健康管理工作台 · 体检指标趋势分析</h1>
  <div class="sub">覆盖历年体检 · 116 项标准指标 · 折线图 + 参考范围区间带 · 异常高亮 · 趋好/趋坏标记</div>
  <div class="privacy">🔒 本地数据处理，无云端存储 · 身份信息已脱敏，仅保留指标数值</div>
</header>

<div class="overview" id="overview"></div>

<div class="health-overview">
  <div class="card">
    <h2>健康总览（来自体检趋势报告）</h2>
    <div class="summary-line" id="summaryLine"></div>
    <table class="ov-table" id="overviewTable"></table>
  </div>
</div>

<div class="layout">
  <div class="sidebar">
    <div class="card">
      <h3>指标筛选</h3>
      <div class="side-filter">
        <label>分类</label>
        <select id="catFilter"></select>
      </div>
      <div class="side-filter">
        <label>健康方向</label>
        <select id="dirFilter">
          <option value="__all">全部方向</option>
          <option value="趋好">🟢 趋好</option>
          <option value="趋坏">🔴 趋坏</option>
          <option value="复杂">🟡 复杂</option>
          <option value="中性">⚪ 中性</option>
        </select>
      </div>
      <div class="side-filter">
        <div class="chk-row">
          <label><input type="checkbox" id="onlyAb"> 仅异常</label>
          <label><input type="checkbox" id="onlySig"> 仅显著变化</label>
        </div>
      </div>
    </div>
    <div class="card">
      <h3>指标分组</h3>
      <div id="groupList"></div>
    </div>
  </div>

  <div class="main">
    <div class="card">
      <div class="chart-head">
        <div>
          <h2 id="chartTitle">—</h2>
          <div class="info" id="chartInfo"></div>
        </div>
        <div class="range-switch" id="rangeSwitch"></div>
      </div>
      <div class="chart-wrap"><div id="chart"></div></div>
      <div class="legend">
        <span><span class="dot dot-normal"></span>正常</span>
        <span><span class="dot dot-ab"></span>超参考范围</span>
        <span><span class="dot dot-sig"></span>显著变化</span>
        <span><span class="band-sample"></span>参考范围区间</span>
        <span><span style="width:10px;height:10px;background:#9ca3af;display:inline-block"></span>OCR 提取（2022 扫描件）</span>
      </div>
      <div class="desc" id="desc"></div>
      <div id="changeList"></div>
      <table class="data-table" id="dataTable"></table>
      <div class="note" id="note"></div>
    </div>
  </div>
</div>

<footer>健康管理工作台 · 本地生成 · 2026-08-16 · 本工具为健康管理参考，不构成诊疗意见</footer>
</div>

<script>
const DATA = __DATA_JSON__;
const YEARS = DATA.years;
const INDICATORS = DATA.indicators;
const MEAS = DATA.measurements;
let allItems = INDICATORS.concat(MEAS);
// 提取 2022 OCR 数据点，用于图表显示
let ALL_OCR = {};
for(const it of INDICATORS){
  if(it.ocr_points && it.ocr_points.length){
    ALL_OCR[it.key] = it.ocr_points;
  }
}

// ---------- 健康总览（数据驱动，不硬编码个体数值） ----------
const OVERVIEW_DIMS = [
  {name:"血糖/糖尿病", keys:["空腹血糖","糖化血红蛋白"]},
  {name:"血脂", keys:["总胆固醇","甘油三酯","低密度脂蛋白胆固醇","高密度脂蛋白胆固醇"]},
  {name:"体重/肥胖", keys:["体重指数"]},
  {name:"血压", keys:["收缩压","舒张压"]},
  {name:"肝功能", keys:["丙氨酸氨基转移酶(ALT)","天门冬氨酸氨基转移酶(AST)","γ-谷氨酰转移酶"]},
  {name:"尿酸/肾功能", keys:["尿酸","肌酐","尿素氮"]},
  {name:"同型半胱氨酸", keys:["同型半胱氨酸"]},
];
function findItem(key){ return allItems.find(x=>x.key===key); }
function ovStatus(keys){
  const parts = [];
  for(const k of keys){
    const it = findItem(k);
    if(!it || !it.points || !it.points.length) continue;
    const p = it.points[it.points.length-1];
    const st = p.status==="偏高" ? "偏高" : (p.status==="偏低" ? "偏低" : "正常");
    parts.push(`${it.display} ${p.year}年${st}（${p.value}${it.unit||""}）`);
  }
  return parts.join("；") || "—";
}
function ovTrend(keys){
  const parts = [];
  for(const k of keys){
    const it = findItem(k);
    if(!it || !it.points || !it.points.length) continue;
    const pct = it.total_change_pct!=null ? `（${it.total_change_pct>0?"+":""}${it.total_change_pct}%）` : "";
    parts.push(`${it.display} ${it.trend}${pct} ${it.good_direction||"中性"}`);
  }
  return parts.join("；") || "—";
}
function renderOverview(){
  const el = document.getElementById("overviewTable");
  let html = "<tr><th>维度</th><th>现状</th><th>趋势结论</th></tr>";
  for(const d of OVERVIEW_DIMS){
    const dir = classifyDim(d.keys);
    let dirTag = "";
    if(dir === "趋好") dirTag = '<span class="direction d-good">↑ 趋好</span>';
    else if(dir === "趋坏") dirTag = '<span class="direction d-bad">↓ 趋坏</span>';
    else if(dir === "复杂") dirTag = '<span class="direction d-mid">~ 复杂</span>';
    html += `<tr><td><b>${d.name}</b></td><td>${ovStatus(d.keys)}</td><td>${ovTrend(d.keys)}${dirTag}</td></tr>`;
  }
  el.innerHTML = html;
  // 自动生成一句话结论（数据驱动）
  const bad = allItems.filter(it=>it.good_direction==="趋坏" && it.has_abnormal);
  const good = allItems.filter(it=>it.good_direction==="趋好" && it.has_abnormal);
  let line = "<b>一句话结论：</b>";
  if(bad.length) line += `需重点关注：${bad.slice(0,4).map(x=>`${x.display}（${x.trend}）`).join("、")}；`;
  else line += "未检出明显趋坏的核心指标；";
  if(good.length) line += `已改善：${good.slice(0,4).map(x=>`${x.display}（${x.trend}）`).join("、")}。`;
  else line += "暂无明显改善项。";
  const abN = allItems.filter(it=>it.has_abnormal).length;
  line += `全部 ${allItems.length} 项指标中 ${abN} 项曾超出参考范围，详见下方明细。`;
  document.getElementById("summaryLine").innerHTML = line;
}
function classifyDim(keys){
  const dirs = keys.map(k=>{ const it=findItem(k); return it?it.good_direction:null; }).filter(Boolean);
  if(!dirs.length) return "中性";
  if(dirs.every(d=>d==="趋好")) return "趋好";
  if(dirs.every(d=>d==="趋坏")) return "趋坏";
  return "复杂";
}

// ---------- 概览卡片 ----------
function overviewCards(){
  const keys = ["空腹血糖","糖化血红蛋白","体重指数","收缩压","总胆固醇","甘油三酯","尿酸","同型半胱氨酸"];
  const titles = {"空腹血糖":"空腹血糖","糖化血红蛋白":"糖化血红蛋白","体重指数":"BMI","收缩压":"收缩压","总胆固醇":"总胆固醇","甘油三酯":"甘油三酯","尿酸":"尿酸","同型半胱氨酸":"同型半胱氨酸"};
  const units = {"空腹血糖":"mmol/L","糖化血红蛋白":"%","体重指数":"kg/m²","收缩压":"mmHg","总胆固醇":"mmol/L","甘油三酯":"mmol/L","尿酸":"μmol/L","同型半胱氨酸":"μmol/L"};
  let html = "";
  for(const k of keys){
    const it = allItems.find(x=>x.key===k);
    if(!it) continue;
    const p = it.points[it.points.length-1];
    const status = p ? p.status : "缺失";
    const badge = status==="偏高" ? '<span class="badge badge-up">偏高</span>' :
                  status==="偏低" ? '<span class="badge badge-down">偏低</span>' : '<span class="badge badge-ok">正常</span>';
    const dirTag = it.good_direction === "趋好" ? '<span class="badge badge-ok">↑趋好</span>' :
                   it.good_direction === "趋坏" ? '<span class="badge badge-up">↓趋坏</span>' :
                   it.good_direction === "复杂" ? '<span class="badge badge-trend">~复杂</span>' : "";
    html += `<div class="card"><div class="label">${titles[k]} ${badge}${dirTag}</div>
      <div class="val">${p ? p.value : "—"}<span style="font-size:12px;font-weight:400;color:var(--muted)"> ${units[k]||""}</span></div>
      <div class="meta">${it.trend}${it.total_change_pct!=null?"（"+(it.total_change_pct>0?"+":"")+it.total_change_pct+"%）":""}</div></div>`;
  }
  document.getElementById("overview").innerHTML = html;
}

// ---------- 筛选 ----------
const catSet = [...new Set(allItems.map(i=>i.category))].sort();
function renderCatFilter(){
  const sel = document.getElementById("catFilter");
  sel.innerHTML = `<option value="__all">全部类别</option>` + catSet.map(c=>`<option value="${c}">${c}</option>`).join("");
}

// 指标按 good_direction 分组
function groupedItems(){
  const groups = {"趋好":[], "趋坏":[], "复杂":[], "中性":[]};
  for(const it of allItems){
    const dir = it.good_direction || "中性";
    if(!groups[dir]) groups[dir] = [];
    groups[dir].push(it);
  }
  return groups;
}
function filteredItems(){
  const cat = document.getElementById("catFilter").value;
  const dir = document.getElementById("dirFilter").value;
  const onlyAb = document.getElementById("onlyAb").checked;
  const onlySig = document.getElementById("onlySig").checked;
  return allItems.filter(it=>{
    if(cat!=="__all" && it.category!==cat) return false;
    if(dir!=="__all" && it.good_direction !== dir) return false;
    if(onlyAb && !it.has_abnormal) return false;
    if(onlySig && !it.has_significant) return false;
    return true;
  });
}
function renderGroupList(){
  const groups = groupedItems();
  const filteredSet = new Set(filteredItems().map(x=>x.key));
  const order = ["趋好","趋坏","复杂","中性"];
  const labels = {"趋好":"🟢 趋好","趋坏":"🔴 趋坏","复杂":"🟡 复杂","中性":"⚪ 中性"};
  const cssCls = {"趋好":"group-good","趋坏":"group-bad","复杂":"group-mid","中性":"group-mid"};
  let html = "";
  for(const dir of order){
    const items = groups[dir] || [];
    if(!items.length) continue;
    // 默认展开：异常、显著变化、选中项
    const isOpen = false; // 默认折叠，避免长列表
    html += `<div class="group-section ${cssCls[dir]}${isOpen?'':' collapsed'}" data-dir="${dir}">
      <div class="group-head" onclick="toggleGroup(this.parentElement)">
        <span>${labels[dir]}</span>
        <span style="display:flex;align-items:center;gap:6px"><span style="font-size:11px;color:var(--muted);font-weight:400">${items.length}项</span><span class="arrow">▼</span></span>
      </div>
      <div class="group-body">`;
    for(const it of items){
      if(!filteredSet.has(it.key)) continue;
      const arr = (it.total_change_pct == null) ? "·" :
                  it.total_change_pct > 5 ? "↑" :
                  it.total_change_pct < -5 ? "↓" : "·";
      const arrCls = arr==="↑" ? "arr-up" : arr==="↓" ? "arr-down" : "arr-eq";
      html += `<div class="indic-item" data-key="${it.key}" onclick="selectItem('${it.key}')">
        <span class="arr ${arrCls}">${arr}</span>
        <span class="name">${it.display}</span>
        <span class="cat">${it.category}</span>
      </div>`;
    }
    html += `</div></div>`;
  }
  document.getElementById("groupList").innerHTML = html || '<div class="empty" style="padding:30px 12px">无匹配指标</div>';
}
function toggleGroup(el){
  el.classList.toggle("collapsed");
}
let selectedKey = null;

// ---------- 时间跨度 ----------
let rangeMode = "all";
function renderRangeSwitch(){
  const el = document.getElementById("rangeSwitch");
  const opts = [["all","全部"],["3","近3年"],["2","近2年"]];
  el.innerHTML = opts.map(([v,l])=>`<button class="${rangeMode===v?'active':''}" onclick="setRange('${v}')">${l}</button>`).join("");
}
function setRange(m){ rangeMode=m; renderRangeSwitch(); renderChart(); }
function activeYears(){
  if(rangeMode==="all") return YEARS;
  const n = parseInt(rangeMode);
  return YEARS.slice(-n);
}
function selectItem(key){
  selectedKey = key;
  document.querySelectorAll(".indic-item").forEach(n=>n.classList.toggle("active", n.dataset.key===key));
  // 自动展开所在组
  document.querySelectorAll(".group-section").forEach(g=>{
    if(g.querySelector(`[data-key="${key}"]`)) g.classList.remove("collapsed");
  });
  renderChart();
}
function highlightSelected(){
  if(!selectedKey) return;
  document.querySelectorAll(".indic-item").forEach(n=>n.classList.toggle("active", n.dataset.key===selectedKey));
}

// ---------- 图表绘制（SVG） ----------
const W=720, H=330, PL=64, PR=24, PT=20, PB=36;
function renderChart(){
  const it = allItems.find(x=>x.key===selectedKey);
  if(!it){ document.getElementById("chart").innerHTML = '<div class="empty">请选择指标</div>'; return; }
  const ys = activeYears();
  // 包含 OCR 数据（如果有 2022）
  const ocrPts = ALL_OCR[it.key] || [];
  const ocrActive = ocrPts.filter(p=>ys.includes(p.year));
  const pts = it.points.filter(p=>ys.includes(p.year));
  const allPoints = [...pts, ...ocrActive].sort((a,b)=>a.year-b.year);
  // Y 轴范围基于所有点（含 OCR）
  const refLo = it.points.length? it.points[0].ref_lo : null;
  const refHi = it.points.length? it.points[0].ref_hi : null;
  let vals = allPoints.map(p=>p.value);
  if(refLo!=null) vals.push(refLo);
  if(refHi!=null) vals.push(refHi);
  if(!vals.length) vals=[0,1];
  let ymin = Math.min(...vals), ymax = Math.max(...vals);
  const span = (ymax-ymin)||1;
  ymin -= span*0.12; ymax += span*0.12;
  const yearList = [...new Set(allPoints.map(p=>p.year))].sort((a,b)=>a-b);
  const yearStart = yearList[0] ?? ys[0];
  const yearEnd = yearList[yearList.length-1] ?? ys[ys.length-1];
  const X = y => PL + (y - yearStart)/(yearEnd-yearStart||1)*(W-PL-PR);
  const Y = v => PT + (ymax - v)/(ymax-ymin)*(H-PT-PB);
  let html = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">`;
  // 网格
  const gridN = 5;
  for(let i=0;i<=gridN;i++){
    const gy = PT + i*(H-PT-PB)/gridN;
    const gv = ymax - i*(ymax-ymin)/gridN;
    html += `<line x1="${PL}" y1="${gy}" x2="${W-PR}" y2="${gy}" stroke="#e5e7eb" stroke-width="1"/>`;
    html += `<text x="${PL-8}" y="${gy+4}" text-anchor="end" font-size="10.5" fill="#6b7280">${gv.toFixed(1)}</text>`;
  }
  // 参考范围带
  if(refLo!=null && refHi!=null){
    const y1=Y(refHi), y2=Y(refLo);
    html += `<rect x="${PL}" y="${y1}" width="${W-PL-PR}" height="${Math.max(0,y2-y1)}" fill="#e8f0fe" fill-opacity="0.6" stroke="#b3c9ee" stroke-dasharray="3 3"/>`;
    html += `<text x="${W-PR-4}" y="${y1-4}" text-anchor="end" font-size="10" fill="#5f79b0">上限 ${refHi}</text>`;
    html += `<text x="${W-PR-4}" y="${y2+12}" text-anchor="end" font-size="10" fill="#5f79b0">下限 ${refLo}</text>`;
  }
  // 折线（连接所有点，包括 OCR 点，OCR 段虚线）
  if(allPoints.length>1){
    // 拆分普通段和 OCR 段
    let inOcr = false, segs = [], cur = [];
    for(let i=0;i<allPoints.length;i++){
      const p = allPoints[i];
      const isOcr = p.source === "ocr";
      if(i===0){ cur.push([X(p.year),Y(p.value), isOcr]); continue; }
      const prev = allPoints[i-1];
      const prevOcr = prev.source === "ocr";
      if(isOcr !== prevOcr){
        segs.push(cur); cur = [];
        cur.push([X(prev.year),Y(prev.value), prevOcr]);
        cur.push([X(p.year),Y(p.value), isOcr]);
      } else {
        cur.push([X(p.year),Y(p.value), isOcr]);
      }
    }
    segs.push(cur);
    for(const seg of segs){
      const pts_str = seg.map(s=>`${s[0]},${s[1]}`).join(" ");
      const ocr = seg.some(s=>s[2]);
      if(ocr){
        html += `<polyline points="${pts_str}" fill="none" stroke="#9ca3af" stroke-width="1.8" stroke-dasharray="4 3" stroke-linejoin="round"/>`;
      } else {
        html += `<polyline points="${pts_str}" fill="none" stroke="#1a73e8" stroke-width="2.5" stroke-linejoin="round"/>`;
      }
    }
  }
  // 数据点
  for(const p of allPoints){
    const cx=X(p.year), cy=Y(p.value);
    const isOcr = p.source === "ocr";
    let isAb = false, sig=false;
    if(!isOcr){
      // 正常数据：判定异常/显著
      const ch = it.changes||[];
      // 找到最近相邻的显著变化（指向本点）
      isAb = p.status==="偏高"||p.status==="偏低";
      // 简化：仅基于 status 显示异常标记
    }
    if(isOcr){
      // OCR 数据点：灰色方块 + OCR 标记
      html += `<rect x="${cx-5}" y="${cy-5}" width="10" height="10" fill="#9ca3af" stroke="#fff" stroke-width="1.5"/>`;
      html += `<text x="${cx}" y="${cy-10}" text-anchor="middle" font-size="10" font-weight="600" fill="#6b7280">${p.value}Ⓞ</text>`;
    } else {
      const fill = isAb ? "#d93025" : "#1a73e8";
      html += `<circle cx="${cx}" cy="${cy}" r="${isAb?5:4.2}" fill="${fill}" stroke="#fff" stroke-width="1.5"/>`;
      let labelY = cy-9;
      if(refHi!=null && Math.abs(cy-Y(refHi))<18) labelY = cy+16;
      else if(refLo!=null && Math.abs(cy-Y(refLo))<18) labelY = cy-9;
      html += `<text x="${cx}" y="${labelY}" text-anchor="middle" font-size="11" font-weight="${isAb?700:600}" fill="${isAb?"#d93025":"#374151"}">${p.value}</text>`;
    }
    html += `<text x="${cx}" y="${H-PB+18}" text-anchor="middle" font-size="12" fill="#374151" font-weight="600">${p.year}</text>`;
  }
  html += `</svg>`;
  document.getElementById("chart").innerHTML = html;
  // 标题 + 整体方向
  const dirTag = it.good_direction === "趋好" ? '<span class="badge badge-ok" style="margin-left:8px">↑ 整体趋好</span>' :
                 it.good_direction === "趋坏" ? '<span class="badge badge-up" style="margin-left:8px">↓ 整体趋坏</span>' :
                 it.good_direction === "复杂" ? '<span class="badge badge-trend" style="margin-left:8px">~ 复杂</span>' : "";
  document.getElementById("chartTitle").innerHTML = (it.display + (it.unit?"（"+it.unit+"）":"")) + dirTag;
  const ocrNote = ocrActive.length ? ` · 含${ocrActive.length}个OCR点(灰)` : "";
  document.getElementById("chartInfo").textContent = `${it.category} · ${it.trend}${it.total_change_pct!=null?"（"+(it.total_change_pct>0?"+":"")+it.total_change_pct+"%）":""}${it.abnormal_years.length?` · 异常年份：${it.abnormal_years.join("、")}`:""}${ocrNote}`;
  // 解读
  const desc = document.getElementById("desc");
  let dh = "";
  if(it.desc) dh += `<div class="clinical"><b style="color:#1a73e8">临床意义（参考默沙东诊疗手册/丁香医生/临床指南）</b><br>${it.desc}</div>`;
  const adv = it.advice||{};
  const advHtml = [];
  if(adv.lifestyle) advHtml.push(`<div class="a-item"><b>生活方式</b>${adv.lifestyle}</div>`);
  if(adv.diet) advHtml.push(`<div class="a-item"><b>饮食</b>${adv.diet}</div>`);
  if(adv.exercise) advHtml.push(`<div class="a-item"><b>运动</b>${adv.exercise}</div>`);
  if(adv.see_doctor) advHtml.push(`<div class="a-item see-doctor"><b>就医指征</b>${adv.see_doctor}</div>`);
  if(advHtml.length) dh += `<div class="advice">${advHtml.join("")}</div>`;
  // OCR 提示
  if(ocrActive.length){
    dh += `<div class="clinical" style="border-left-color:#9ca3af;background:#f8f8f8;margin-top:8px"><b style="color:#6b7280">2022 数据说明</b><br>2022 年报告为扫描件，使用 macOS Vision framework OCR 识别并经参考范围反推指标归属（数据点 Ⓞ 标注）。准确率有限，仅供参考，不参与显著变化判定。</div>`;
  }
  desc.innerHTML = dh;
  // 变化列表（带趋好/趋坏标签）
  const chgEl = document.getElementById("changeList");
  let chgHtml = "";
  for(const c of it.changes){
    let gdTag = "";
    if(c.good_direction === "趋好") gdTag = '<span class="tag-good">🟢 趋好</span>';
    else if(c.good_direction === "趋坏") gdTag = '<span class="tag-bad">🔴 趋坏</span>';
    else gdTag = '<span class="tag-neutral">— 中性</span>';
    const sigTag = c.significant ? '<span class="badge badge-trend">显著</span>' : '';
    chgHtml += `<div class="chg-row">
      <span style="font-weight:600;color:var(--text)">${c.from_year}→${c.to_year}</span>
      <span>${c.from} → ${c.to} (${c.pct}%) ${c.direction}</span>
      ${sigTag}
      ${gdTag}
    </div>`;
  }
  chgEl.innerHTML = chgHtml;
  // 数据表（包含 OCR 行）
  const tbl = document.getElementById("dataTable");
  let th = `<tr><th>年份</th><th>数值</th><th>参考范围</th><th>状态</th><th>来源</th></tr>`;
  const rows = allPoints.map(p=>{
    const isOcr = p.source === "ocr";
    const cls = isOcr ? "miss" : (p.status==="偏高"||p.status==="偏低" ? "ab" : "normal");
    const status = isOcr ? "OCR提取" : p.status;
    const src = isOcr ? "<span class='badge badge-trend'>OCR</span>" : "电子报告";
    const ref = isOcr ? `${refLo}-${refHi}` : (p.ref_str||"—");
    return `<tr><td>${p.year}</td><td class="${cls}">${p.value}${isOcr?' Ⓞ':''}</td><td>${ref}</td><td>${status}</td><td>${src}</td></tr>`;
  }).join("");
  tbl.innerHTML = th+rows;
  const miss = it.missing_years||[];
  const noteParts = [];
  if(miss.length) noteParts.push(`缺失年份：${miss.join("、")}`);
  if(ocrActive.length) noteParts.push(`${ocrActive.length} 个 2022 OCR 点（扫描件提取，供参考）`);
  document.getElementById("note").textContent = noteParts.join(" · ");
}

// ---------- 事件 ----------
function refreshFilters(){
  renderGroupList();
  if(selectedKey && !filteredItems().find(x=>x.key===selectedKey)){ selectedKey=null; }
  highlightSelected();
  renderChart();
}
document.getElementById("catFilter").onchange = refreshFilters;
document.getElementById("dirFilter").onchange = refreshFilters;
document.getElementById("onlyAb").onchange = refreshFilters;
document.getElementById("onlySig").onchange = refreshFilters;

// ---------- 初始化 ----------
renderOverview();
overviewCards();
renderCatFilter();
renderGroupList();
renderRangeSwitch();
if(allItems.length) selectItem(allItems[0].key);
</script>
</body>
</html>
"""

def main():
    html = HTML_TEMPLATE.replace("__DATA_JSON__", DATA_JSON)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"已生成: {OUT_PATH} ({os.path.getsize(OUT_PATH)/1024:.0f} KB)")

if __name__ == "__main__":
    main()