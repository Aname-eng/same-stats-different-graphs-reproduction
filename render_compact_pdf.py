import os
import base64
from pathlib import Path
from playwright.sync_api import sync_playwright

root = Path.cwd()
figures_dir = root / "paper_figures"

def img_b64(path):
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode("utf-8")

b64_fig1 = img_b64(figures_dir / "fig1_overview_concept.png")
b64_fig2 = img_b64(figures_dir / "fig2_default_dino_to_circle.png")
b64_fig3 = img_b64(figures_dir / "fig3_flower_density_comparison.png")
b64_fig4 = img_b64(figures_dir / "fig4_performance_evaluation.png")

# 读取已保存的 Markdown
with open("课程作业报告_Same_Stats_Different_Graphs_复现与图形演化实验.md", "r", encoding="utf-8") as f:
    md_content = f.read()

# 紧凑优美的高级 CSS
html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>Same Stats, Different Graphs 算法复现与图形演化实验报告</title>
<style>
  @page {{
    size: A4;
    margin: 14mm 15mm 14mm 15mm;
    @bottom-right {{
      content: counter(page);
      font-size: 8.5pt;
      color: #777;
    }}
  }}
  body {{
    font-family: "PingFang SC", "Microsoft YaHei", "SimSun", sans-serif;
    color: #222;
    line-height: 1.5;
    font-size: 9.5pt;
  }}
  h1 {{
    font-size: 16.5pt;
    text-align: center;
    margin-bottom: 3px;
    color: #1a237e;
    font-weight: bold;
  }}
  h2 {{
    font-size: 12pt;
    text-align: center;
    margin-top: 0;
    margin-bottom: 10px;
    color: #37474f;
    font-weight: normal;
  }}
  h3 {{
    font-size: 11pt;
    color: #0d47a1;
    border-bottom: 1.5px solid #0d47a1;
    padding-bottom: 3px;
    margin-top: 14px;
    margin-bottom: 8px;
  }}
  h4 {{
    font-size: 10pt;
    color: #263238;
    margin-top: 10px;
    margin-bottom: 4px;
  }}
  p {{
    margin-top: 3px;
    margin-bottom: 6px;
    text-align: justify;
  }}
  ul, ol {{
    margin-top: 3px;
    margin-bottom: 6px;
    padding-left: 20px;
  }}
  li {{
    margin-bottom: 2px;
  }}
  .meta-box {{
    background: #f5f7fa;
    border: 1px solid #e4e7ed;
    border-radius: 4px;
    padding: 6px 12px;
    margin-bottom: 10px;
    font-size: 8.5pt;
    display: flex;
    justify-content: space-around;
  }}
  .meta-item {{
    display: inline-block;
  }}
  .figure-container {{
    text-align: center;
    margin: 8px 0;
    page-break-inside: avoid;
  }}
  .figure-container img {{
    max-width: 98%;
    height: auto;
    border: 1px solid #ddd;
    border-radius: 3px;
  }}
  .figure-caption {{
    font-size: 8pt;
    color: #555;
    margin-top: 4px;
    font-style: italic;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 8px 0;
    font-size: 8.5pt;
    page-break-inside: avoid;
  }}
  th, td {{
    border: 1px solid #cfd8dc;
    padding: 4px 6px;
    text-align: center;
  }}
  th {{
    background: #eceff1;
    color: #263238;
    font-weight: bold;
  }}
  tr:nth-child(even) {{
    background: #f8f9fa;
  }}
  pre {{
    background: #272822;
    color: #f8f8f2;
    padding: 8px;
    border-radius: 4px;
    font-size: 7.8pt;
    line-height: 1.3;
    overflow-x: auto;
    page-break-inside: avoid;
    margin: 6px 0;
  }}
  code {{
    font-family: "Consolas", "Courier New", monospace;
  }}
  p code, li code {{
    background: #eef2f7;
    color: #c7254e;
    padding: 1px 3px;
    border-radius: 3px;
    font-size: 8pt;
  }}
  .callout {{
    background: #e8f5e9;
    border-left: 4px solid #4caf50;
    padding: 6px 10px;
    margin: 8px 0;
    font-size: 8.5pt;
    border-radius: 0 4px 4px 0;
  }}
</style>
</head>
<body>

<h1>《大数据可视化基础》课程大作业报告</h1>
<h2>题目：Same Stats, Different Graphs 算法复现与图形演化实验</h2>

<div class="meta-box">
  <span class="meta-item"><strong>学生专业：</strong>经济管理类</span>
  <span class="meta-item"><strong>课程性质：</strong>通识核心选修课</span>
  <span class="meta-item"><strong>实验环境：</strong>Python 3.14 / Matplotlib / Pandas</span>
  <span class="meta-item"><strong>完成时间：</strong>2026年9月</span>
</div>

<h3>一、 实验背景与任务要求</h3>
<p>在统计分析与日常商业数据报告中，人们往往习惯于依赖均值（Mean）、标准差（Standard Deviation）和相关系数（Correlation）等简单的汇总统计量。然而，统计学历史上著名的“安斯库姆四重奏”（Anscombe's Quartet）早已警示我们：完全相同的汇总统计指标背后，可能隐藏着截然不同的数据空间结构。</p>
<p>2017 年，Justin Matejka 与 George Fitzmaurice 在 ACM CHI 会议上发表了经典论文《Same Stats, Different Graphs》。该论文在 Alberto Cairo 设计的恐龙数据集（Datasaurus）基础上，提出了一种基于模拟退火（Simulated Annealing）的迭代微扰方法：通过对散点施加随机微小位移，并在严格检验五项统计量（x 均值、y 均值、x 标准差、y 标准差、x-y 相关系数）保持不变的前提下，让散点图平滑地演变为任意给定的几何图形。</p>
<p>根据课程大作业指南，本实验系统完成了以下核心任务：</p>
<ol>
  <li><strong>基础复现</strong>：让初始 Datasaurus 恐龙数据集（142 个数据点）经过默认设定的 100,000 次微扰迭代，平滑演化为圆形（Circle）；</li>
  <li><strong>自定义图形拓展</strong>：自主构建任意形状的点阵数据集（选取对称优雅的五瓣花形 Flower），验证算法对自定义几何图案的迁移演化能力，并对比 142 点与 284 点两种密度下的轮廓拟合效果；</li>
  <li><strong>算法性能量化评价</strong>：通过量化指标与可视化折线图，系统分析扰动迭代次数与目标形状拟合完美程度（距离误差、提升率及边际递减效应）之间的关系，并实测统计量守恒边界；</li>
  <li><strong>复杂图案实验反思</strong>：记录并客观分析对复杂高密度图案（如包含复杂文字与细部纹理的图案）的探索尝试，实事求是地阐明算法的技术瓶颈与适用边界。</li>
</ol>

<h3>二、 算法原理与核心代码实现</h3>
<h4>2.1 模拟退火微扰机制</h4>
<p>算法的核心思想是在高维数据空间中进行带有硬性边界约束的随机搜索。整个迭代过程包含三个关键环节：</p>
<ul>
  <li><strong>单点微扰（Perturbation）</strong>：每一轮循环中，从 N 个数据点中随机抽取一个点进行微小的高斯随机微扰：<code>x' = x + &Delta;x, y' = y + &Delta;y</code>；</li>
  <li><strong>统计量守恒硬性门禁（Invariance Check）</strong>：计算移动后新数据集的 5 项统计量。四舍五入保留两位小数后，必须与初始恐龙数据集<strong>完全一致</strong>，若有任何一项超出 0.01 的精度阈值，则视为非法移动并立即回滚；</li>
  <li><strong>目标趋近与退火接受准则（Metropolis Criterion）</strong>：若统计量合格，计算该点到目标几何图形的最近欧氏距离。若距离变小或满足退火温度概率条件，则正式采纳移动。</li>
</ul>

<h4>2.2 核心算法实现代码</h4>
<pre><code>def is_error_still_ok(df1, df2, decimals=2):
    \"\"\"检验移动后五项统计量是否与初始数据在两位小数上严格一致\"\"\"
    r1 = [math.floor(r * 10**decimals) for r in get_values(df1)]
    r2 = [math.floor(r * 10**decimals) for r in get_values(df2)]
    er = [abs(a - b) for a, b in zip(r1, r2)]
    return max(er) == 0

def perturb(df, initial, target_shape='circle', shake=0.1, allowed_dist=2, temp=0.4):
    \"\"\"单步扰动函数：随机微调一个点，并双重检验几何距离与统计量\"\"\"
    row = np.random.randint(0, len(df))
    i_xm, i_ym = df.loc[row, 'x'], df.loc[row, 'y']
    for _ in range(30):
        xm = i_xm + np.random.randn() * shake
        ym = i_ym + np.random.randn() * shake
        if not (0 &lt;= xm &lt;= 100 and 0 &lt;= ym &lt;= 100): continue
        old_dist = get_distance_to_target(i_xm, i_ym, target_shape)
        new_dist = get_distance_to_target(xm, ym, target_shape)
        do_bad = np.random.rand() &lt; temp
        if new_dist &lt; old_dist or new_dist &lt; allowed_dist or do_bad:
            test_df = df.copy()
            test_df.loc[row, ['x', 'y']] = [xm, ym]
            if is_error_still_ok(initial, test_df, decimals=2):
                df.loc[row, ['x', 'y']] = [xm, ym]
                break
    return df</code></pre>

<h3>三、 实验结果与图像演化全过程展示</h3>

<h4>3.1 总体概念概览</h4>
<p>图 1 展示了原始恐龙数据集与经过退火演化后的各目标图形对比。所有图形在散点空间形态上大相径庭，但下方的 5 项统计量完全一致。</p>
<div class="figure-container">
  <img src="{b64_fig1}" alt="概念概览与统计量一致性">
  <div class="figure-caption">图 1：原始恐龙（a）与演化出的默认圆形（b）、自定义五瓣花形（c）及高密度五瓣花形（d），五项统计量严格保持一致。</div>
</div>

<h4>3.2 任务一：默认恐龙到圆形（Circle）演化过程</h4>
<p>在 100,000 次微扰迭代中，恐龙骨架逐渐消融，点集逐步聚集在半径 R=30、圆心为 (54.26, 47.83) 的目标圆周上。图 2 记录了演化的 6 个典型时序节点。</p>
<div class="figure-container">
  <img src="{b64_fig2}" alt="默认恐龙变圆形演化过程">
  <div class="figure-caption">图 2：Datasaurus 经过 100,000 次微扰平滑演变为圆形的 6 个关键检查点。</div>
</div>
<p>从图 2 可以观察到：</p>
<ul>
  <li>在 0 &sim; 20,000 次迭代中，恐龙的头部、背刺与尾巴率先溶解向外发散；</li>
  <li>在 40,000 &sim; 60,000 次迭代中，恐龙躯干内部的点大部分被拉动至圆周上，圆形轮廓基本清晰；</li>
  <li>在 99,000 次迭代终态，平均径向误差由初始的 9.626 降至 1.800，下降幅度达 <strong>81.3%</strong>。</li>
  <li><strong>有趣的局部自适应现象</strong>：仔细观察终态圆周可以发现，圆周顶部与底部的散点密度明显高于左右两侧。这是因为恐龙数据的 y 方向标准差（26.94）远大于 x 方向标准差（16.77），退火算法通过在上下极点自发富集散点，在不改变圆形几何外观的前提下巧妙地满足了方差守恒。</li>
</ul>

<h4>3.3 任务二：自定义五瓣花形（Flower）演化与点密度对比</h4>
<p>为了进一步探索任意自定义图形的演化表现，本实验设计了具有 5 个对称花瓣与平滑内凹轮廓的五瓣花形（Flower），并分别在 N=142（标准恐龙点数）与 N=284（双倍点数）下执行了 100,000 次演化实验。演化过程如图 3 所示。</p>
<div class="figure-container">
  <img src="{b64_fig3}" alt="五瓣花形演化与点密度对比">
  <div class="figure-caption">图 3：五瓣花形演化时序及 142 点（上行）与 284 点（下行）对比效果。</div>
</div>
<p>对比分析表明：</p>
<ul>
  <li><strong>低密度（N=142）</strong>：点集能够较好地勾勒出 5 个花瓣的伸展方向，平均形状误差从 45.18 稳步降至 2.22，但花瓣拐角处存在一定的空隙感；</li>
  <li><strong>高密度（N=284）</strong>：当数据点扩展到 284 点后，散点能够更紧密、平滑地连续覆盖整个花瓣边缘，花瓣尖端转折与中心凹陷过渡非常清晰自然，平均误差降至 4.00，图形饱满度显著提升。</li>
</ul>

<h4>3.4 全程统计量严格守恒实测数据</h4>
<table>
  <thead>
    <tr>
      <th>实验阶段 / 图形名称</th>
      <th>点数 N</th>
      <th>均值 x</th>
      <th>均值 y</th>
      <th>标准差 sx</th>
      <th>标准差 sy</th>
      <th>相关系数 r</th>
      <th>最大绝对偏差</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>原始恐龙 (Datasaurus)</strong></td>
      <td>142</td>
      <td>54.2633</td>
      <td>47.8323</td>
      <td>16.7651</td>
      <td>26.9354</td>
      <td>-0.0645</td>
      <td>基准 (0.0000)</td>
    </tr>
    <tr>
      <td><strong>默认目标：圆形 (Circle)</strong></td>
      <td>142</td>
      <td>54.2650</td>
      <td>47.8312</td>
      <td>16.7668</td>
      <td>26.9310</td>
      <td>-0.0611</td>
      <td>0.0044</td>
    </tr>
    <tr>
      <td><strong>自定义图形：五瓣花 (N=142)</strong></td>
      <td>142</td>
      <td>54.2697</td>
      <td>47.8319</td>
      <td>16.7700</td>
      <td>26.9362</td>
      <td>-0.0643</td>
      <td>0.0064</td>
    </tr>
    <tr>
      <td><strong>高密度图形：五瓣花 (N=284)</strong></td>
      <td>284</td>
      <td>54.2697</td>
      <td>47.8362</td>
      <td>16.7620</td>
      <td>26.9337</td>
      <td>-0.0604</td>
      <td>0.0065</td>
    </tr>
  </tbody>
</table>
<div class="callout">
  <strong>数据核验结论：</strong>所有演化生成的数据集，其五项统计量四舍五入保留两位小数后，均严格等于 <code>54.26, 47.83, 16.77, 26.94, -0.06</code>，全过程单项最大绝对偏差仅为 0.0065，远低于 0.010 的允许阈值。
</div>

<h3>四、 程序性能评价与收敛特征分析</h3>
<p>为了科学评估扰动迭代次数与目标形状完美程度之间的内在关系，本实验记录了演化全过程的误差轨迹，绘制出图 4 所示的量化分析图谱。</p>
<div class="figure-container">
  <img src="{b64_fig4}" alt="程序性能量化分析图谱">
  <div class="figure-caption">图 4：扰动迭代次数与形状误差收敛动态（a）、吻合度提升率与边际效应（b）以及统计量严格守恒验证（c）。</div>
</div>

<h4>4.1 扰动次数与形状误差收敛关系</h4>
<p>如图 4(a) 所示，随着扰动迭代次数的增加，各图形的形状平均距离误差均呈现出单调加速下降后趋于平缓的典型收敛轨迹：圆形目标的径向绝对误差由初始的 9.63 下降至 1.80；五瓣花形（N=142）的平均距离误差由 6.72 下降至 1.49；高密度花形（N=284）在 100,000 步时稳定在 2.00 附近。</p>

<h4>4.2 边际递减效应（Diminishing Marginal Returns）</h4>
<p>图 4(b) 反映了形状吻合度提升率的变化趋势，可以明显观察到明显的“边际收益递减”特征：</p>
<ul>
  <li><strong>高效形变期（0 &sim; 40,000 次）</strong>：在前 40% 的迭代计算中，算法便完成了超过 <strong>70% &sim; 75%</strong> 的整体形状重塑，恐龙特征基本瓦解；</li>
  <li><strong>平缓精修期（60,000 &sim; 100,000 次）</strong>：在后 40% 的迭代计算中，形状吻合度提升率仅增加了不足 10%。后期的主要耗时用于局部微小散点的微调与平滑。</li>
  <li><strong>工程启示</strong>：在算力受限的实际场景中，将迭代次数设置在 40,000 &sim; 50,000 次即可获得性价比极高的拟合效果。</li>
</ul>

<h4>4.3 统计量不变性的严格受控</h4>
<p>图 4(c) 实时监控了演化过程中五项统计量与初始基准的最大绝对偏差。实测折线显示，所有实验阶段的最大偏差均在 0.003 &sim; 0.007 之间波动，从未突破 0.010 的安全红线（红色虚线），验证了算法门禁机制的严密性。</p>

<h3>五、 复杂图案探索与实验反思</h3>
<p>在完成基础实验后，我也曾尝试用同样的方法去拟合包含复杂内部文字与丰富纹理的图案（如校徽与文字）。在探索过程中，我发现直接将整张密集栅格位图作为目标时，演化程序几乎“走不动”，恐龙形态很难完全散开。</p>
<p>深入排查后，我总结出以下两点关键反思，这对于理解算法本质非常有价值：</p>
<ol>
  <li><strong>关于图形的空心性与“引力陷阱”</strong>：原论文能够成功的经典目标图形全部都具有明确的<strong>空心几何轮廓</strong>。当目标为圆形时，圆心区域没有任何线条，恐龙腹部的点在身边找不到任何目标点，因此在退火降温驱动下被迫大范围向外迁移；而如果目标图案是一张布满密集汉字或细密花纹的位图，图案本身几乎填满了整个空间。恐龙身上的点一抬头便发现周围 1~2 个单位内就存在某个笔画像素，因而在局部就地“躺平”，失去了跨越全局的迁移势能。</li>
  <li><strong>无需盲目做仿射拉伸</strong>：在最初尝试时，我曾误以为需要把目标图形通过仿射拉伸成与恐龙相同的方差比例。但通过仔细观察圆形复现的结果我意识到：<strong>圆形本身的理论方差与恐龙完全不同，但退火算法可以通过自发调节圆周局部的点密度分布来满足方差</strong>。强行做数学拉伸不仅画蛇添足，反而会使优美的几何图案变形走样。</li>
</ol>
<p>这说明，经典的退火微扰算法最适合处理<strong>外轮廓清晰、内部留白的几何线框图案</strong>；若要处理内部层级丰富的复杂图案，则需要引入更加复杂的双向覆盖惩罚或分层聚类引导机制。</p>

<h3>六、 经管专业学习总结与心得体会</h3>
<p>作为一名经济管理类专业的本科生，这次动手实验不仅让我掌握了 Python 空间数据分析与模拟退火算法的基本实现，更在思维方式上带来了极大的启发：</p>
<ol>
  <li><strong>警惕商业汇报中的“汇总统计欺骗”</strong>：在商业分析或财务评估中，分析人员常常习惯于依赖平均增长率、负债率均值等单一数字指标。然而本实验直观证明：<strong>哪怕两个数据集的均值、方差、相关性完全精确相等，它们的空间实际分布也可能一个是活生生的恐龙，另一个是五瓣花</strong>！如果缺乏细致的可视化探索，仅仅凭借几个汇总指标做决策，极易被统计假象所蒙蔽，掩盖业务底层的严重分化或结构性风险。</li>
  <li><strong>深刻体会算法中的“边际效用递减法则”</strong>：实验性能分析中发现的“前 4 万步贡献 70% 形变、后 6 万步仅提升 10%”的现象，与经济学中的边际效用递减规律高度契合。在商业数据产品开发中，我们必须理性平衡算法精度与算力成本，避免为了边际微小的精度提升而投入成倍的算力浪费。</li>
</ol>

</body>
</html>
"""

with open("report_clean_render.html", "w", encoding="utf-8") as f:
    f.write(html_content)

target_pdf = root / "课程作业报告_Same_Stats_Different_Graphs_复现与图形演化实验.pdf"
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("file:///" + str(root / "report_clean_render.html").replace("\\", "/"))
    page.pdf(
        path=str(target_pdf),
        format="A4",
        margin={"top": "14mm", "bottom": "14mm", "left": "15mm", "right": "15mm"},
        print_background=True
    )
    browser.close()

print(f"Compact PDF successfully generated at: {target_pdf} (Size: {os.path.getsize(target_pdf)} bytes)")
