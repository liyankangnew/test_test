"""
投资市场数据面板生成脚本
数据源: 腾讯财经(指数K线) + 新浪财经(商品期货) + akshare/funddb(股息率)
输出: index.html
"""
import json
import requests
import pandas as pd
from datetime import datetime, timedelta

end_date = datetime.now().strftime("%Y-%m-%d")
start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
print(f"数据范围: {start_date} ~ {end_date}")


def fetch_index_tencent(symbol, name):
    """从腾讯财经获取指数日K线"""
    url = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
    params = {"param": f"{symbol},day,{start_date},{end_date},500,qfq"}
    try:
        r = requests.get(url, params=params, timeout=20)
        data = r.json()
        stock_data = data["data"][symbol]
        days = stock_data.get("day") or stock_data.get("qfqday", [])
        rows = [{"date": d[0], "close": float(d[2])} for d in days]
        df = pd.DataFrame(rows)
        print(f"  {name}: {len(df)} 条")
        return df
    except Exception as e:
        print(f"  {name} 失败: {e}")
        return pd.DataFrame(columns=["date", "close"])


def fetch_sina_commodity(symbol, name):
    """从新浪财经获取国际商品期货日K线"""
    url = f"https://stock2.finance.sina.com.cn/futures/api/jsonp.php/var%20chart/GlobalFuturesService.getGlobalFuturesDailyKLine?symbol={symbol}&_=1"
    try:
        r = requests.get(url, headers={"Referer": "https://finance.sina.com.cn"}, timeout=15)
        text = r.text
        start_idx = text.find('(')
        end_idx = text.rfind(')')
        data = json.loads(text[start_idx + 1:end_idx])
        rows = [{"date": item["date"], "close": float(item["close"])} for item in data]
        df = pd.DataFrame(rows)
        # 只保留近一年
        df = df[df["date"] >= start_date].reset_index(drop=True)
        print(f"  {name}: {len(df)} 条")
        return df
    except Exception as e:
        print(f"  {name} 失败: {e}")
        return pd.DataFrame(columns=["date", "close"])


def fetch_dividend_yield():
    """获取中证红利股息率"""
    print("正在获取中证红利股息率...")
    try:
        import akshare as ak
        df = ak.index_value_hist_funddb(symbol="中证红利", indicator="股息率")
        df = df[["日期", "股息率"]].rename(columns={"日期": "date", "股息率": "value"})
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        cutoff = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        df = df[df["date"] >= cutoff].reset_index(drop=True)
        print(f"  股息率: {len(df)} 条")
        return df, True
    except Exception as e:
        print(f"  funddb失败({e})，用中证红利指数代替")
        df = fetch_index_tencent("sh000922", "中证红利指数")
        df = df.rename(columns={"close": "value"})
        return df, False


def generate_html(cb_data, dividend_data, is_yield, indices_data, oil_data, gold_data):
    """生成 index.html"""
    cb_json = {"dates": cb_data["date"].tolist(), "values": cb_data["close"].tolist()}
    div_json = {"dates": dividend_data["date"].tolist(), "values": dividend_data["value"].tolist()}
    indices_json = {}
    for name, df in indices_data.items():
        indices_json[name] = {"dates": df["date"].tolist(), "values": df["close"].tolist()}
    oil_json = {"dates": oil_data["date"].tolist(), "values": oil_data["close"].tolist()}
    gold_json = {"dates": gold_data["date"].tolist(), "values": gold_data["close"].tolist()}

    dividend_title = "中证红利指数股息率日趋势" if is_yield else "中证红利指数日趋势"

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>投资市场数据面板</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
            background: #0f1923; color: #e0e0e0; min-height: 100vh;
        }}
        .header {{ text-align: center; padding: 24px 20px 12px; border-bottom: 1px solid #1e2a3a; }}
        .header h1 {{ font-size: 24px; font-weight: 600; color: #fff; letter-spacing: 2px; }}
        .header .subtitle {{ font-size: 13px; color: #6b7d8e; margin-top: 6px; }}
        .dashboard {{
            max-width: 1400px; margin: 0 auto; padding: 20px;
            display: grid; grid-template-columns: 1fr 1fr; gap: 20px;
        }}
        .chart-card {{
            background: #1a2634; border-radius: 12px; padding: 20px; border: 1px solid #253545;
        }}
        .chart-card.full-width {{ grid-column: 1 / -1; }}
        .chart-card h3 {{
            font-size: 15px; font-weight: 500; color: #b0c4d8;
            margin-bottom: 12px; padding-left: 10px; border-left: 3px solid #4fc3f7;
        }}
        .chart-container {{ width: 100%; height: 350px; }}
        .chart-card.full-width .chart-container {{ height: 420px; }}
        .data-note {{ text-align: center; padding: 12px; font-size: 12px; color: #4a5d6e; }}
        @media (max-width: 900px) {{ .dashboard {{ grid-template-columns: 1fr; }} }}
    </style>
</head>
<body>
    <div class="header">
        <h1>投资市场数据面板</h1>
        <div class="subtitle">近一年日趋势 · 更新: {datetime.now().strftime("%Y-%m-%d %H:%M")}</div>
    </div>
    <div class="dashboard">
        <div class="chart-card">
            <h3>中证转债指数日趋势</h3>
            <div class="chart-container" id="chart-cb"></div>
        </div>
        <div class="chart-card">
            <h3>{dividend_title}</h3>
            <div class="chart-container" id="chart-dividend"></div>
        </div>
        <div class="chart-card">
            <h3>布伦特原油期货价格（美元/桶）</h3>
            <div class="chart-container" id="chart-oil"></div>
        </div>
        <div class="chart-card">
            <h3>COMEX黄金现货价格（美元/盎司）</h3>
            <div class="chart-container" id="chart-gold"></div>
        </div>
        <div class="chart-card full-width">
            <h3>主要宽基指数日趋势（归一化涨跌幅%）</h3>
            <div class="chart-container" id="chart-indices"></div>
        </div>
    </div>
    <div class="data-note">数据来源: 腾讯财经 / 新浪财经 / funddb · 生成: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
    <script>
    const cbData = {json.dumps(cb_json, ensure_ascii=False)};
    const dividendData = {json.dumps(div_json, ensure_ascii=False)};
    const indicesData = {json.dumps(indices_json, ensure_ascii=False)};
    const oilData = {json.dumps(oil_json, ensure_ascii=False)};
    const goldData = {json.dumps(gold_json, ensure_ascii=False)};
    const isYield = {'true' if is_yield else 'false'};

    function baseOption() {{
        return {{
            tooltip: {{ trigger: 'axis', backgroundColor: '#1a2634', borderColor: '#253545', textStyle: {{ color: '#e0e0e0', fontSize: 12 }} }},
            grid: {{ left: '3%', right: '4%', bottom: '14%', top: '8%', containLabel: true }},
            dataZoom: [
                {{ type: 'inside', start: 0, end: 100 }},
                {{ type: 'slider', start: 0, end: 100, height: 20, bottom: 5, borderColor: '#253545', fillerColor: 'rgba(79,195,247,0.1)', handleStyle: {{ color: '#4fc3f7' }}, textStyle: {{ color: '#6b7d8e' }} }}
            ]
        }};
    }}

    function renderSimpleChart(domId, data, color, unit) {{
        const chart = echarts.init(document.getElementById(domId));
        chart.setOption({{
            ...baseOption(),
            xAxis: {{ type: 'category', data: data.dates, axisLine: {{ lineStyle: {{ color: '#253545' }} }}, axisLabel: {{ color: '#6b7d8e' }}, boundaryGap: false }},
            yAxis: {{ type: 'value', scale: true, axisLine: {{ lineStyle: {{ color: '#253545' }} }}, axisLabel: {{ color: '#6b7d8e', formatter: unit ? '{{value}}' + unit : '{{value}}' }}, splitLine: {{ lineStyle: {{ color: '#1e2a3a' }} }} }},
            series: [{{ type: 'line', data: data.values, smooth: true, symbol: 'none', lineStyle: {{ width: 2, color: color }}, areaStyle: {{ color: new echarts.graphic.LinearGradient(0,0,0,1,[{{offset:0,color:color.replace(')', ',0.3)').replace('rgb','rgba')}},{{offset:1,color:color.replace(')', ',0.02)').replace('rgb','rgba')}}]) }} }}]
        }});
        window.addEventListener('resize', () => chart.resize());
    }}

    // 中证转债指数
    renderSimpleChart('chart-cb', cbData, '#4fc3f7', '');

    // 中证红利
    (function() {{
        const chart = echarts.init(document.getElementById('chart-dividend'));
        chart.setOption({{
            ...baseOption(),
            xAxis: {{ type: 'category', data: dividendData.dates, axisLine: {{ lineStyle: {{ color: '#253545' }} }}, axisLabel: {{ color: '#6b7d8e' }}, boundaryGap: false }},
            yAxis: {{ type: 'value', scale: true, axisLine: {{ lineStyle: {{ color: '#253545' }} }}, axisLabel: {{ color: '#6b7d8e', formatter: isYield ? '{{value}}%' : '{{value}}' }}, splitLine: {{ lineStyle: {{ color: '#1e2a3a' }} }} }},
            series: [{{ type: 'line', data: dividendData.values, smooth: true, symbol: 'none', lineStyle: {{ width: 2, color: '#ff8a65' }}, areaStyle: {{ color: new echarts.graphic.LinearGradient(0,0,0,1,[{{offset:0,color:'rgba(255,138,101,0.3)'}},{{offset:1,color:'rgba(255,138,101,0.02)'}}]) }} }}]
        }});
        window.addEventListener('resize', () => chart.resize());
    }})();

    // 布伦特原油
    renderSimpleChart('chart-oil', oilData, '#66bb6a', '');

    // COMEX黄金
    renderSimpleChart('chart-gold', goldData, '#ffd54f', '');

    // 宽基指数
    (function() {{
        const chart = echarts.init(document.getElementById('chart-indices'));
        const colors = {{ '上证50':'#4fc3f7','沪深300':'#81c784','中证500':'#ffb74d','中证1000':'#e57373','国证2000':'#ba68c8','创业板指':'#4dd0e1' }};
        const firstKey = Object.keys(indicesData)[0];
        const dates = indicesData[firstKey] ? indicesData[firstKey].dates : [];
        const series = Object.entries(indicesData).map(([name, data]) => {{
            const base = data.values[0];
            const norm = data.values.map(v => ((v - base) / base * 100).toFixed(2));
            return {{ name, type: 'line', data: norm, smooth: true, symbol: 'none', lineStyle: {{ width: 1.8, color: colors[name]||'#fff' }}, itemStyle: {{ color: colors[name]||'#fff' }} }};
        }});
        chart.setOption({{
            ...baseOption(),
            legend: {{ data: Object.keys(indicesData), top: 0, textStyle: {{ color: '#b0c4d8', fontSize: 12 }}, icon: 'roundRect', itemWidth: 14, itemHeight: 3 }},
            grid: {{ left: '3%', right: '4%', bottom: '14%', top: '36px', containLabel: true }},
            xAxis: {{ type: 'category', data: dates, axisLine: {{ lineStyle: {{ color: '#253545' }} }}, axisLabel: {{ color: '#6b7d8e' }}, boundaryGap: false }},
            yAxis: {{ type: 'value', scale: true, axisLine: {{ lineStyle: {{ color: '#253545' }} }}, axisLabel: {{ color: '#6b7d8e', formatter: '{{value}}%' }}, splitLine: {{ lineStyle: {{ color: '#1e2a3a' }} }} }},
            series
        }});
        window.addEventListener('resize', () => chart.resize());
    }})();
    </script>
</body>
</html>"""
    return html


if __name__ == "__main__":
    print("=" * 50)
    print("投资市场数据面板 - 数据获取")
    print("=" * 50)

    # 1. 中证转债指数
    print("\n[1/5] 中证转债指数")
    cb_data = fetch_index_tencent("sh000832", "中证转债指数")

    # 2. 中证红利股息率
    print("\n[2/5] 中证红利股息率")
    dividend_data, is_yield = fetch_dividend_yield()

    # 3. 布伦特原油
    print("\n[3/5] 布伦特原油期货")
    oil_data = fetch_sina_commodity("OIL", "布伦特原油")

    # 4. COMEX黄金
    print("\n[4/5] COMEX黄金")
    gold_data = fetch_sina_commodity("GC", "COMEX黄金")

    # 5. 宽基指数
    print("\n[5/5] 宽基指数")
    indices_config = {
        "上证50": "sh000016",
        "沪深300": "sh000300",
        "中证500": "sh000905",
        "中证1000": "sh000852",
        "国证2000": "sz399303",
        "创业板指": "sz399006",
    }
    indices_data = {}
    for name, symbol in indices_config.items():
        indices_data[name] = fetch_index_tencent(symbol, name)

    # 生成 HTML
    print("\n生成 index.html...")
    html = generate_html(cb_data, dividend_data, is_yield, indices_data, oil_data, gold_data)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n✅ 完成!")
    print(f"   转债指数: {len(cb_data)} 条")
    print(f"   红利数据: {len(dividend_data)} 条 ({'股息率' if is_yield else '指数点位'})")
    print(f"   布伦特原油: {len(oil_data)} 条")
    print(f"   COMEX黄金: {len(gold_data)} 条")
    for name, df in indices_data.items():
        print(f"   {name}: {len(df)} 条")
