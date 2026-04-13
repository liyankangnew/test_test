"""
获取十年期国债利率数据并生成可视化 HTML 文件
数据来源: akshare -> 东方财富 中美国债收益率
"""

import akshare as ak
import json
from datetime import datetime, timedelta


def fetch_bond_data():
    """获取近一年的中国十年期国债收益率数据"""
    start = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
    df = ak.bond_zh_us_rate(start_date=start)
    # 只保留日期和中国10年期
    df = df[["日期", "中国国债收益率10年"]].dropna(subset=["中国国债收益率10年"])
    df["日期"] = df["日期"].astype(str)
    return df


def generate_html(df):
    """生成带 ECharts 折线图的 index.html"""
    dates = df["日期"].tolist()
    values = df["中国国债收益率10年"].tolist()

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>十年期国债收益率走势</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
         background: #f5f7fa; display: flex; flex-direction: column; align-items: center;
         padding: 40px 20px; }}
  h1 {{ color: #333; margin-bottom: 8px; font-size: 24px; }}
  .sub {{ color: #888; font-size: 14px; margin-bottom: 24px; }}
  #chart {{ width: min(1200px, 95vw); height: 500px; background: #fff;
            border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.08);
            padding: 20px; }}
</style>
</head>
<body>
<h1>中国十年期国债收益率</h1>
<p class="sub">数据来源：东方财富 &middot; 更新时间：{datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
<div id="chart"></div>
<script>
var chart = echarts.init(document.getElementById('chart'));
var option = {{
  tooltip: {{
    trigger: 'axis',
    formatter: function(p) {{
      return p[0].axisValue + '<br/>收益率: ' + p[0].value + '%';
    }}
  }},
  grid: {{ left: 60, right: 30, top: 30, bottom: 60 }},
  xAxis: {{
    type: 'category',
    data: {json.dumps(dates)},
    axisLabel: {{ rotate: 45, fontSize: 11 }},
    boundaryGap: false
  }},
  yAxis: {{
    type: 'value',
    name: '收益率 (%)',
    axisLabel: {{ formatter: '{{value}}%' }},
    scale: true
  }},
  dataZoom: [
    {{ type: 'inside', start: 0, end: 100 }},
    {{ type: 'slider', start: 0, end: 100, height: 20, bottom: 5 }}
  ],
  series: [{{
    name: '10年期国债收益率',
    type: 'line',
    data: {json.dumps(values)},
    smooth: true,
    symbol: 'none',
    lineStyle: {{ width: 2, color: '#e74c3c' }},
    areaStyle: {{
      color: {{
        type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
        colorStops: [
          {{ offset: 0, color: 'rgba(231,76,60,0.25)' }},
          {{ offset: 1, color: 'rgba(231,76,60,0.02)' }}
        ]
      }}
    }}
  }}]
}};
chart.setOption(option);
window.addEventListener('resize', function() {{ chart.resize(); }});
</script>
</body>
</html>"""
    return html


def main():
    print("正在获取十年期国债收益率数据...")
    df = fetch_bond_data()
    print(f"获取到 {len(df)} 条数据 ({df['日期'].iloc[0]} ~ {df['日期'].iloc[-1]})")

    html = generate_html(df)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("已生成 index.html，用浏览器打开即可查看。")


if __name__ == "__main__":
    main()
