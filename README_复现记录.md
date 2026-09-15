# Same Stats, Different Graphs：课程复现记录

## 课程来源与原始材料

- 雨课堂课程：`大数据可视化基础`，Lec1/1.1。
- 已下载的课程原始压缩包：`SameStatsCode-论文python源码.zip`。
- 原始解压内容保留在 `course_source/`，未修改。
- `course_source/seed_datasets/Datasaurus_data.csv` 是本次 dino 的原始坐标数据。

## 运行环境

- Python 3.14.6
- pandas、numpy、matplotlib、seaborn、pytweening、tqdm、docopt

## 兼容性处理

课程源码按旧版 Seaborn API 写成，在 seaborn 0.13 下会在第一帧报错：
`TypeError: regplot() got multiple values for argument 'data'`。

为复现运行而创建了 `run_default_dino_to_circle/` 副本；该副本仅作如下兼容性修正：

1. `sns.regplot("x", y="y", data=df, ...)` 改为 `sns.regplot(x="x", y="y", data=df, ...)`；
2. 将命令行指定的 `decimals` 传入 `run_pattern()`；
3. 修正课程源码中错误地以 `<decimals>` 判断 `<frames>` 的一行。

原始课程源码仍保留在 `course_source/same_stats.py`。

## 已完成的默认复现

执行命令：

```powershell
python same_stats.py run dino circle
```

这使用课程源码默认配置：100,000 次扰动、2 位小数统计量约束、保存 100 个过程帧。

- 输出目录：`run_default_dino_to_circle/results/`
- 输出数量：100 个 PNG 过程图与 100 个 CSV 坐标文件。
- 过程性能数据：`analysis/default_run_metrics.csv`。
- 过程拼图：`analysis/dino_to_circle_progress.png`。
- 性能图：`analysis/performance_vs_iterations.png`。

## 指标定义与结果

圆形完美度采用平均径向误差：对每个点计算到课程源码目标圆心 `(54.26, 47.83)` 的距离，取其与半径 `30` 的绝对差，再对全体点取平均。数值越低，越接近目标圆。

| 扰动次数 | 平均径向误差 | 相对初始图的最大统计量绝对差 |
|---:|---:|---:|
| 0 | 9.626 | 0.0013 |
| 10,000 | 8.188 | 0.0049 |
| 20,000 | 6.833 | 0.0043 |
| 40,000 | 4.537 | 0.0058 |
| 60,000 | 2.666 | 0.0039 |
| 80,000 | 1.969 | 0.0048 |
| 99,000 | 1.800 | 0.0044 |

结论：在这次随机运行中，100,000 次默认扰动使圆形误差从 9.626 降至 1.800，约下降 81.3%。改进在 0–60,000 次最明显，80,000 次后趋于平缓；同时五项统计量相对初始 dino 的最大差始终小于 0.006，符合两位小数约束。

## 可重复运行

```powershell
Set-Location 'D:\课程\数据可视化\same-stats-different-graphs-reproduction\run_default_dino_to_circle'
python same_stats.py run dino circle
```

运行完成后：

```powershell
Set-Location 'D:\课程\数据可视化\same-stats-different-graphs-reproduction'
python analyze_default_run.py
```
