# Paper Plan

## Paper Contract

- Working title: 保持统计量不变的图形转换：Datasaurus 到南开校徽与校训的复现实验
- Audience and venue: 《大数据可视化基础》课程作业；面向能够运行 Python 的本科生读者
- Paper archetype: empirical method / empirical mechanism hybrid
- Central question: 在保持均值、标准差和相关系数近似不变的条件下，模拟退火能否把 Datasaurus 恐龙点阵转换成课程文件夹中的南开校徽和校训形状？
- One-sentence answer: 课程算法能够在默认配置下把恐龙转为圆形，并在扩展为自定义目标点阵后生成可辨识的校徽与校训轮廓；形状误差随迭代下降，但后期出现边际收益递减。
- Demonstrated scope: 一次固定随机种子的 Datasaurus→circle 复现，以及两个各 60,000 次迭代的 Datasaurus→自定义目标点阵实验。
- Main limitation: 自定义目标被仿射归一化到恐龙数据的二阶统计量；目标点阵的像素抽样、点数和随机种子会影响形状质量，实验尚未进行多随机种子不确定性评估。

## Motivation Chain

- Practical or scientific problem: 仅查看均值、标准差和相关系数，无法判断二维数据的形状结构。
- Why it matters in the target setting: 数据可视化课程需要一个可运行的实验说明统计量与可视外观的差异。
- Prevailing method or explanation: 直接比较描述性统计量或相关系数。
- Concrete failure, mismatch, or tradeoff: Datasaurus 与圆形或其他图形可以共享近似统计量，但点云结构完全不同。
- Why existing evidence does not resolve it: 纸面示例说明了现象，却没有覆盖本课程文件夹中的校徽和校训自定义目标。
- Smallest conceptual move in this paper: 将目标形状从课程源码的硬编码几何规则扩展为 CSV 点阵，并在扰动前用仿射变换匹配源数据的一阶、二阶统计量。

## Claim-Evidence Map

| Priority | Claim | Evidence | Comparator or control | Scope | Main-paper location |
| --- | --- | --- | --- | --- | --- |
| 1 | 默认课程代码能将恐龙点阵转为圆形，同时保持五项统计量在两位小数约束下近似不变 | 100,000 次运行的 100 个过程帧、CSV 和统计量表 | 初始 dino 与最终 circle | 单次固定环境运行 | 结果 5.1 |
| 2 | 目标形状可扩展到课程文件夹中的南开校徽和校训 | 两个 142 点目标 CSV、60,000 次运行的过程图和最终图 | 目标点阵与初始 dino；统计量约束 | 自定义目标经仿射归一化 | 方法 4、结果 5.2 |
| 3 | 迭代次数增加通常会降低目标形状误差，但后期改进变慢 | 各检查点的平均分配误差、最近目标误差曲线 | 0 到 60,000 次检查点 | 每个目标一次随机种子 | 性能分析 5.3 |

## Figure Spine

- Figure 1: 从 Datasaurus 到目标形状的流程图，加上统计量约束和误差下降结果。
- Figure 2: 默认 dino→circle 的六个迭代检查点。
- Figure 3: dino→南开校徽和 dino→校训的最终目标对照。
- Figure 4: 两个自定义目标的迭代误差与统计量偏差曲线。
- Figure 5: 像素点阵提取和仿射归一化对目标形状的限制示意。

## Section Contracts

| Section | Question answered | Evidence introduced | Exit sentence |
| --- | --- | --- | --- |
| Introduction | 为什么要把同一组统计量画出来？ | Datasaurus 问题与课程任务 | 本文把现象复现为一个可检查的扰动实验。 |
| Preliminaries / formulation | 算法保持什么统计量？ | 五项统计量、接受规则、目标距离 | 目标距离与统计量约束共同决定每次移动是否被接受。 |
| Main result / method | 如何加入校徽和校训？ | PNG→CSV、仿射归一化、点对应目标 | 扩展只改变目标表示，保留课程算法的统计量门槛。 |
| Experiments / validation | 运行设置是什么？ | 运行次数、帧数、环境、随机种子 | 实验结果可以由项目内脚本重跑。 |
| Mechanism / understanding | 迭代次数怎样影响形状？ | 径向误差与自定义目标误差 | 形状改进并非与迭代次数线性增长。 |
| Related work | 本实验与原论文/课程源码的关系是什么？ | 论文与课程源码说明 | 本文是课程复现和受限扩展，不声称改进原算法。 |
| Discussion / conclusion | 结果支持什么，限制是什么？ | 统计量保持、图形变化、目标归一化 | 可视化是统计摘要之外的必要检查，但不能替代统计检验。 |

## Risk Audit

- Strongest alternative explanation: 自定义目标看起来接近目标，可能只是目标点阵本身已被强制归一化，而不是退火算法真正完成了形状转换。
- Required control: 报告归一化目标、初始 dino 和最终输出，并分别报告目标距离与统计量偏差。
- Closest prior work and exact difference: Matejka and Fitzmaurice 的 Same Stats, Different Graphs 与课程源码使用硬编码目标；本文新增课程文件夹校徽和校训的点阵目标。
- Most likely overclaim: 把单次运行说成普遍保证，或把平均径向/最近点误差说成严格的视觉相似度。
- Missing evidence: 多随机种子重复、与其他目标点数和分辨率的敏感性、人工视觉评分。
- Result that would weaken the story: 自定义目标最终仍不可辨识，或统计量约束频繁失败。
- Claim to narrow if that result appears: 改为“在本次参数和目标抽样下得到可辨识轮廓”。
