# -*- coding: utf-8 -*-
"""生成「GUS审批时效趋势看板」——模仿 GEU 考勤差错率看板的结构：
   浅灰底 + 白卡片 + Plotly 折线（点位标数值）+ 卡片右上角汇总框 + 页脚口径说明。

数据源：dashboard_build/data_weekly.json（同审批时效看板口径）
输出：  D:\\工作文件夹wei\\审批时效看板OA源数据\\GUS审批时效趋势看板.html
"""
import io, json, os, datetime

BASE = r"D:\Users\Downloads\ai"
JSON_PATH = os.path.join(BASE, "dashboard_build", "data_weekly.json")
OUT_PATH = r"D:\工作文件夹wei\审批时效看板OA源数据\GUS审批时效趋势看板.html"

EX_FLOW = "考勤异常申诉申请"
SKIP_DEPT = "GEU人力资源部"
GROUPS = [("履约前台", "Fulfillment Front"), ("业务前台", "Business Front"),
          ("运营中台", "Operations Middle"), ("后台", "Back Office")]
COLORS = ["#2563eb", "#0e7c86", "#d97706", "#b03a5b", "#6d4ad8", "#15803d", "#c2410c", "#0891b2", "#7c3aed", "#65a30d"]


def group_of(d):
    if any(k in d for k in ("大区", "分区", "Ground")):
        return "履约前台"
    if any(k in d for k in ("跨境客户", "本地客户")):
        return "业务前台"
    if any(k in d for k in ("人力", "财务", "行政")):
        return "后台"
    return "运营中台"


def week_label(d):
    s = datetime.date.fromisoformat(d)
    e = s + datetime.timedelta(days=6)
    return f"{s.month:02d}-{s.day:02d}~{e.month:02d}-{e.day:02d}"


def main():
    j = json.load(io.open(JSON_PATH, encoding="utf-8"))
    docs, pos = j["docs"], j.get("pos") or {}
    weeks = j["weeks"]
    wl = [week_label(w) for w in weeks]

    # 周 × 部门：审批次数、时长合计、单据集合、单据最长动作
    agg = {}
    for a in j["acts"]:
        d = docs[a["k"]]
        if d["s"] == EX_FLOW:
            continue
        if a["ap"] == "凌霄" and a["a3"] == "GUS 人力资源部":
            continue
        if a["a3"] == SKIP_DEPT or a["nd"] in ("起草节点", "被考核人自评"):
            continue
        if not a["a3"] or a["a3"] == "未知":
            continue
        key = (a["w"], a["a3"])
        o = agg.setdefault(key, {"n": 0, "sum": 0.0, "docs": set(), "dmax": {}})
        o["n"] += 1
        o["sum"] += float(a["d"])
        o["docs"].add(a["k"])
        o["dmax"][a["k"]] = max(o["dmax"].get(a["k"], 0.0), float(a["d"]))

    depts = sorted({k[1] for k in agg})
    dept_by_group = {g: [d for d in depts if group_of(d) == g] for g, _ in GROUPS}

    def series(dept):
        vals, cnts = [], []
        for wi in range(len(weeks)):
            o = agg.get((wi, dept))
            vals.append(round(o["sum"] / o["n"] * 24, 1) if o else None)
            cnts.append(o["n"] if o else 0)
        return vals, cnts

    last = len(weeks) - 1
    cards = []
    for g, en in GROUPS:
        ds = dept_by_group[g]
        if not ds:
            continue
        # 汇总框：本周该板块
        n_docs, n_acts, sum_d, long_docs = set(), 0, 0.0, 0
        dmax_all = {}
        for d in ds:
            o = agg.get((last, d))
            if not o:
                continue
            n_docs |= o["docs"]
            n_acts += o["n"]
            sum_d += o["sum"]
            for k, v in o["dmax"].items():
                dmax_all[k] = max(dmax_all.get(k, 0.0), v)
        for v in dmax_all.values():
            if v > 2:
                long_docs += 1
        doc_n = len(dmax_all)
        cards.append(dict(
            group=g, en=en, depts=ds,
            summary=dict(docs=len(n_docs), acts=n_acts,
                         avg=round(sum_d / n_acts * 24, 1) if n_acts else 0,
                         p48=round(long_docs / doc_n * 100, 1) if doc_n else 0),
            series=[dict(name=d, vals=series(d)[0], cnts=series(d)[1]) for d in ds]))

    # 顶部总览：4 个板块平均
    over = []
    for g, _ in GROUPS:
        ds = dept_by_group[g]
        vals = []
        for wi in range(len(weeks)):
            s = n = 0
            for d in ds:
                o = agg.get((wi, d))
                if o:
                    s += o["sum"]; n += o["n"]
            vals.append(round(s / n * 24, 1) if n else None)
        over.append(dict(name=g, vals=vals))

    data = dict(weeks=wl, cards=cards, overview=over, colors=COLORS,
                updated=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))

    html = TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False))
    io.open(OUT_PATH, "w", encoding="utf-8", newline="\n").write(html)
    print("written:", OUT_PATH, len(html), "bytes")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>GUS 审批时效趋势看板</title>
<style>
  :root { --bg:#f4f6fa; --card:#ffffff; --ink:#1f2937; --muted:#6b7280; --line:#e5e7eb; --accent:#1b4faf; }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { font-family:"Segoe UI","Microsoft YaHei",Arial,sans-serif; background:var(--bg); color:var(--ink); padding:20px; }
  header { max-width:1200px; margin:0 auto 8px; }
  h1 { font-size:27px; font-weight:600; }
  .sub { color:var(--muted); font-size:15px; margin-top:5px; }
  .legend-hint { color:var(--muted); font-size:14px; margin-top:7px; }
  .grid { max-width:1200px; margin:0 auto; display:grid; grid-template-columns:1fr; gap:18px; margin-top:14px; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:10px 8px 2px; box-shadow:0 1px 3px rgba(16,24,40,.06); }
  .card .head { display:flex; align-items:flex-start; justify-content:space-between; padding:6px 12px 0; gap:12px; }
  .card .head .titles { display:flex; align-items:baseline; gap:10px; }
  .card .head .cn { color:var(--accent); font-size:19px; font-weight:600; }
  .card .head .en { color:var(--muted); font-size:14px; }
  .card .summ { font-size:14px; line-height:1.6; text-align:right; border:1px solid var(--line); border-radius:8px; padding:7px 12px; background:#f8fafc; white-space:nowrap; }
  .card .summ b { color:var(--accent); }
  .chart { width:100%; height:420px; }
  .chart-top { height:440px; margin-top:4px; }
  footer { max-width:1200px; margin:18px auto 0; color:var(--muted); font-size:14px; line-height:1.8; }
  footer b { color:var(--ink); }
</style>
</head>
<body>
<header>
  <h1>GUS 审批时效趋势看板 <span style="color:var(--muted);font-weight:400;font-size:16px;">(按周 multi-week)</span></h1>
  <div class="sub">数据来源：GUS 海外 OA 审批流程导出（按周）｜按“板块”分卡，卡内按三级部门着色</div>
  <div class="legend-hint">横轴 = 自然周 · 纵轴 = 平均审批时长（h）· 每条线=一个三级部门 · 线尾标注最新一周数值 · 悬停可看每周审批次数</div>
</header>
<div class="grid" id="grid">
  <div class="card">
    <div class="head">
      <div class="titles"><span class="cn">各板块平均审批时长</span><span class="en">Overview</span></div>
      <div class="summ" id="summ-top"></div>
    </div>
    <div class="chart chart-top" id="chart-top"></div>
  </div>
</div>
<footer>
  <b>口径说明：</b><br/>
  1. <b>数据窗口</b>：2026-09-28 起的全部自然周（周一至周日），共 <span id="wc"></span> 周。<br/>
  2. <b>平均审批时长</b> = Σ单次审批时长 ÷ 审批次数 × 24，单位小时；只统计审批动作，不含起草节点与被考核人自评。<br/>
  3. <b>部门</b> = 审批人三级部门（按工号匹配花名册）；未匹配到部门的审批已剔除。<br/>
  4. <b>汇总框</b>：最后一行的单据数、审批次数、平均时长、>48h 单据占比均为最新一周口径。<br/>
  5. <b>缺失周</b>：该部门当周无审批动作时折线断开，不补 0。<br/>
  <span id="upd" style="font-size:12px;"></span>
</footer>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<script>
const D = __DATA__;
document.getElementById('wc').textContent = D.weeks.length;
document.getElementById('upd').textContent = '生成时间：' + D.updated;

function lineTraces(series, showLegend) {
  return series.map((s, i) => ({
    x: D.weeks, y: s.vals, name: s.name, mode: 'lines+markers+text',
    line: { width: 2, color: D.colors[i % D.colors.length] },
    marker: { size: 5, color: D.colors[i % D.colors.length] },
    text: s.vals.map((v, k) => (k === s.vals.length - 1 && v !== null) ? v.toFixed(1) : ''),
    textposition: 'top center', textfont: { size: 10, color: D.colors[i % D.colors.length] },
    connectgaps: false, showlegend: showLegend,
    customdata: s.cnts,
    hovertemplate: '<b>%{fullData.name}</b><br>%{x}<br>平均 %{y:.1f} h<br>审批 %{customdata} 次<extra></extra>'
  }));
}
const layoutBase = {
  margin: { l: 48, r: 24, t: 12, b: 56 },
  paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
  xaxis: { tickangle: -30, gridcolor: '#eef1f5' },
  yaxis: { title: '平均审批时长（h）', gridcolor: '#eef1f5', zerolinecolor: '#e5e7eb' },
  legend: { orientation: 'h', y: -0.28, font: { size: 11 } },
  hovermode: 'closest'
};

const grid = document.getElementById('grid');
D.cards.forEach((c, idx) => {
  const card = document.createElement('div');
  card.className = 'card';
  card.innerHTML = '<div class="head"><div class="titles"><span class="cn">' + c.group +
    '</span><span class="en">' + c.en + '</span></div><div class="summ">最新一周：单据 <b>' + c.summary.docs +
    '</b> 张 · 审批 <b>' + c.summary.acts + '</b> 次 · 平均 <b>' + c.summary.avg.toFixed(1) +
    '</b> h · &gt;48h 单据占比 <b>' + c.summary.p48.toFixed(1) + '%</b></div></div>' +
    '<div class="chart" id="ch' + idx + '"></div>';
  grid.appendChild(card);
  Plotly.newPlot('ch' + idx, lineTraces(c.series, true), Object.assign({}, layoutBase, { height: 420 }));
});

Plotly.newPlot('chart-top', lineTraces(D.overview, true), Object.assign({}, layoutBase, { height: 440 }));
const lastW = D.weeks[D.weeks.length - 1];
document.getElementById('summ-top').textContent = '最新一周：' + lastW;
window.addEventListener('resize', () => {
  document.querySelectorAll('.chart,.chart-top').forEach(el => { try { Plotly.Plots.resize(el); } catch (e) {} });
});
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
