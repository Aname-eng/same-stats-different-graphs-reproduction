# Same Stats, Different Graphs Reproduction & Custom Shape Evolution

本项目是基于 ACM CHI 2017 经典论文 **《Same Stats, Different Graphs: Generating Datasets with Varied Appearance and Identical Statistics through Simulated Annealing》**（Justin Matejka & George Fitzmaurice）的完整复现与拓展研究项目。

本项目包含：
1. **论文基准复现**：Datasaurus 恐龙数据集（142 点）平滑演化为圆形（Circle）；
2. **自定义任意形状演化**：五瓣花朵（Flower）在 142 点与 284 点下的演化对比；
3. **程序性能量化评估**：迭代次数与形状契合度、边际递减效应、五项统计量严格不变性监控；
4. **课程作业报告**：包含完整分析与演化全过程的 Markdown 报告与正式导出的 PDF 文件；
5. **复杂多层级图案（南开校徽、校训）演化探索与失败尝试记录**：供后续使用先进大模型（如 GPT-6 / Astra）深入攻坚与算法改进。

---

## 一、 统计量严格守恒定义

在演化过程中，所有生成点集的以下 5 项汇总统计指标（四舍五入保留两位小数后）必须与初始恐龙数据集完全一致：
- $x$ 坐标均值 $\bar{x} = 54.26$
- $y$ 坐标均值 $\bar{y} = 47.83$
- $x$ 坐标样本标准差 $s_x = 16.77$
- $y$ 坐标样本标准差 $s_y = 26.94$
- Pearson 相关系数 $r = -0.06$

---

## 二、 成功复现与成果展示

### 1. 概念概览与统计量一致性 (`paper_figures/fig1_overview_concept.png`)
展示原始恐龙、默认圆形、自定义五瓣花形（142 点）与高密度五瓣花形（284 点），所有数据集下方标注的 5 项统计量完全相同。

### 2. 恐龙变圆形演化时序 (`paper_figures/fig2_default_dino_to_circle.png`)
展示 0、10k、20k、40k、60k、99k 步的演化时序，平均径向误差由 9.626 降至 1.800（降幅 81.3%）。

### 3. 五瓣花形演化与点密度对比 (`paper_figures/fig3_flower_density_comparison.png`)
展示 0、25k、50k、100k 步下五瓣花形的演变过程，对比 142 点与 284 点的边缘覆盖饱满度。

### 4. 程序性能量化分析图谱 (`paper_figures/fig4_performance_evaluation.png`)
- **(a) 误差收敛曲线**：形状平均距离误差随扰动次数增加呈单调下降；
- **(b) 边际递减效应**：前 40%（4 万步）完成超 70%~75% 的整体形变，后 60% 为局部微调平滑；
- **(c) 统计量守恒监控**：全过程单项最大绝对偏差控制在 0.003 ~ 0.007，严格受控于 0.010 阈值之下。

### 5. 课程正式作业报告
- 📄 PDF: [`课程作业报告_Same_Stats_Different_Graphs_复现与图形演化实验.pdf`](./课程作业报告_Same_Stats_Different_Graphs_复现与图形演化实验.pdf)
- 📝 Markdown: [`课程作业报告_Same_Stats_Different_Graphs_复现与图形演化实验.md`](./课程作业报告_Same_Stats_Different_Graphs_复现与图形演化实验.md)

---

## 三、 复杂图案（南开校徽、校训）的探索与失败尝试记录 (For GPT-6 Astra)

### 1. 目标图案
- `南开校徽.jpg`：包含外圆环、中圆环、八角星（Octagram）以及核心篆体字“南開”；
- `校训.jpg`：“允公允能 日新月异” 八个汉字。

### 2. 遇到的问题与现象
当我们试图将恐龙数据集演化成包含内部文字和细密花纹的图案时，经典退火算法遇到了严重的挑战：**点集散不开，演化 10 万步后依然保留恐龙的大致轮廓，或者内部文字无法清晰呈现**。

### 3. 历次失败与尝试记录

| 尝试方案 | 核心实现与文件 | 实验现象与失败根因 |
| :--- | :--- | :--- |
| **Attempt 1: 密集栅格位图 + 二阶矩仿射拉伸** | `custom_chain_568_logo/`<br>`paper_figures/fig4_dense_chain_logo_to_motto.png` | **原因1**：仿射拉伸将正圆校徽强行压成 $s_y/s_x \approx 1.61$ 的瘦长椭圆，扭曲了目标几何；<br>**原因2**：位图布满密集墨水像素，恐龙身上的点身边处处都是笔画，在局部 1~2 像素内就满足了距离阈值因而“就地躺平”，失去全局迁移势能。 |
| **Attempt 2: 纯空心几何线框 (八角星)** | `custom_nankai_octagram/`<br>`analysis/test_octagram_annealed.png`<br>`paper_figures/fig4_nankai_octagram_progress.png` | 恐龙完全溶解并完美贴合在八角星 16 条线段上（误差降至 1.05），但内部完全被掏空，**丢失了校徽核心的“南開”字样和内环**。 |
| **Attempt 3: 动态一对一分配 (Hungarian Matching)** | `test_full_logo.py`<br>`analysis/test_full_logo_assignment.png`<br>`targets/南开校徽_components.csv` | 目标采样点集是均匀分布的（$s_x \approx s_y$），而统计量硬性要求 $s_y/s_x \approx 1.61$。一对一匹配锁死了点的去向，点集无法通过上下自适应聚集来满足方差，导致上下拉伸脱节、左右无法贴合。 |
| **Attempt 4: 分组配额退火 (Grouped Quota Annealing)** | `test_grouped_annealing.py`<br>`analysis/test_grouped_emblem.png` | 将点集固定分配给外环、八角星、内字“南開”三组分别计算最近邻，但在单点随机微扰下，内部文字与外部几何框架之间存在较强的空间方差竞争，内部笔画点易受限于局部微扰步长。 |

---

## 四、 核心代码结构

```
.
├── course_source/             # 课程原始代码与种子数据集 (Datasaurus_data.csv, same_stats.py)
├── targets/                   # 抽取的点云目标 (南开校徽 components, flower, etc.)
├── paper_figures/             # 报告高清图表 (fig1 ~ fig4, 及失败案例对比图)
├── analysis/                  # 探索过程中的各类诊断可视化与 PDF 页面预览
├── custom_flower_142/         # 142点五瓣花演化数据与时序快照
├── custom_flower_284/         # 284点五瓣花演化数据与时序快照
├── run_default_dino_to_circle/# 默认恐龙变圆形演化数据与时序快照
├── custom_chain_568_logo/     # 密集位图演化尝试数据 (Attempt 1)
├── custom_chain_568_motto/    # 密集校训演化尝试数据 (Attempt 1)
├── custom_nankai_octagram/    # 八角星空心线框演化数据 (Attempt 2)
├── image_to_points.py         # 位图转点阵与连通域采样工具
├── run_custom_target.py       # 自定义目标模拟退火演化主脚本
├── test_full_logo.py          # 动态一对一分配测试脚本 (Attempt 3)
├── test_grouped_annealing.py  # 分组配额退火测试脚本 (Attempt 4)
├── generate_paper_figures.py  # 报告图表绘制脚本
├── render_complete_report.py  # Markdown 与 PDF 报告渲染生成脚本
├── 南开校徽.jpg               # 原始校徽素材
├── 校训.jpg                   # 原始校训素材
├── 课程作业报告_Same_Stats_Different_Graphs_复现与图形演化实验.md # 正式报告 Markdown
└── 课程作业报告_Same_Stats_Different_Graphs_复现与图形演化实验.pdf # 正式报告 PDF
```
