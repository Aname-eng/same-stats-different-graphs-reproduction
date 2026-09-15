# 当前执行任务：目标图形复杂度 → 最小所需点数的经验关系

TASK_ID: SSDG_COMPLEXITY_NREL_20260915
STATUS: READY_FOR_EXECUTION
REPOSITORY: Aname-eng/same-stats-different-graphs-reproduction
WORK_BRANCH: feature/gemini-fixed-n-evolution
REVIEWED_REMOTE_HEAD: 6a464262fce8f434eae6bced0579ef3d6d620e58
EXECUTOR_PROFILE: Gemini 3.7 Flash High；因此本任务将定义、步骤、停止条件和输出格式写死，禁止自行扩题。

## 0. 这轮为什么做

项目现在已经能够在固定 N、固定 point_id、五项统计量守恒的前提下，把高密度恐龙演化成较复杂的南开校徽；最新分支已有 N=2840、5680、11360 的 6-layer 版本，含英文环字。现在不再把主要精力放在“把某一张校徽继续优化得更漂亮”，而是回答一个更一般、但仍然直接服务本项目的问题：

> 在固定显示尺度和固定验收标准下，一个目标图形越复杂，需要至少多少散点才能清晰表示，并且在本项目的五项统计量约束下仍可演化到该目标？

本轮要得到的是“项目内、可复现的经验关系”，不是宣称发现适用于所有图片、所有 marker 大小、所有优化算法的普适定律。

必须区分两个概念：

1. **表示下限 N_repr**：不考虑优化器是否会陷入局部最优，只问 N 个等权点能否在该目标几何上形成足够清晰的离散表示，同时目标密度与参考矩足够相容。
2. **演化下限 N_evo**：在当前保矩演化算法和冻结计算预算下，从密集恐龙实际运行，最小测试通过点数是多少。

N_evo 一般应 >= N_repr。若某个几何支持在矩约束下本身不可行，则“增加 N”不一定解决问题；必须单独标记为 moment-incompatible，不能把它解释成“点还不够多”。

## 1. 启动和安全边界

1. 先执行 git status、git branch -vv、git remote -v、git fetch origin。
2. 安全同步 feature/gemini-fixed-n-evolution；上述 REVIEWED_REMOTE_HEAD 只是本 prompt 编写时的检查点，不要求回退。
3. 禁止 reset --hard、git clean、force push、覆盖未提交改动、擅自合并 main。
4. 本轮不要重新生成任何长 GIF，不要重跑 11360 点的 60k 动画，不要修改已有成品和旧实验目录。
5. 不要修改现有统计量定义、三点保矩核、旧结果 CSV/GIF、原校徽图片。
6. 除非发现阻塞本实验的明确 bug，否则不要修改生产演化算法。研究代码优先放在新的独立模块/analysis/complexity/ 下。
7. 不使用语言模型逐步参与优化；全部指标和实验应由确定性 Python 代码完成。

## 2. 本轮只需先阅读这些文件

必须阅读：
- prompt.md（本文件）
- src/stats_audit.py
- src/geometry_ground_truth.py
- src/target_emblem_v2.py
- src/target_emblem_6layer.py
- src/dino_densifier.py
- src/nankai_optimizer_v2.py
- src/fast_assignment.py
- 南开校徽.jpg
- 最新 N=2840、5680、11360 的目标诊断、metrics、末帧 CSV（存在什么读什么）

可按需阅读：
- 旧 circle / flower / octagram 结果，用作外部形状验证；不要为了收集更多样本而重新跑大规模动画。

不要重新吞整个旧 transcript，不要修 Flash01 验收器边界问题；它与本轮研究问题无关。

## 3. 研究问题与需要产出的结论

最终报告必须能回答以下四个问题：

A. 哪个几何复杂度指标与最小点数 N_repr 最相关？
B. 一个简单关系，例如 N ~ a*(L/g)^b，能否较好预测最小点数？
C. 分叉、端点、环路、高曲率等拓扑/几何结构，在 L/g 之外是否有稳定增量解释力？
D. 五项统计量约束是否产生一个独立的“矩相容性门槛”，即某些图形不是增加 N 就能解决？

不得预设答案。若 L/g 表现不好，要如实报告。若样本太少，只能称探索性经验关系。

## 4. 冻结坐标、显示与成功定义

复杂度和 N* 没有脱离显示尺度的绝对意义，因此本轮必须先冻结统一尺度：

- 数据坐标范围：[0,100] x [0,100]
- equal aspect
- 所有图形统一映射到与当前项目相同的数据尺度；不得为了让某图更容易而单独放大/缩小后又直接比较 N。
- 研究用几何验收不依赖 PNG 抗锯齿，而使用数据空间中的骨架/曲线距离。

复杂度指标从**高分辨率真实目标几何**计算，不允许从已经抽样的 N 个 target slots 反推复杂度；否则会出现“点越多，测出的图越复杂”的循环定义。

### 4.1 表示成功 N_repr 的冻结定义

对某个目标形状和某个 N，先在目标几何上构造 N 个等权候选 slots，然后同时检查：

1. 所有必需图层都有正配额，关键小结构不能被压成 0。
2. target-to-slot 的覆盖率 >= 0.98。
3. p95(target geometry -> nearest slot) <= 0.25 * g05。
4. 最大连续未覆盖几何长度 <= 0.75 * g05。
5. 所有端点和 junction 在 <= 0.25 * g05 范围内至少有一个 slot。
6. 目标密度的矩相容性满足下文 moment gate；若几何支持本身不可行，不能因为覆盖很好而算表示成功。

其中 g05 是本轮定义的 robust non-local feature separation，见第 6 节。若 g05 无法定义，必须返回 reason code，不得偷偷用 0 或无穷。

N_repr* 定义为：在测试范围内，**最小测试通过 N**。它不是数学证明的全局最小点数。

### 4.2 演化成功 N_evo 的冻结定义

只对少量代表性形状做实际演化验证。成功必须满足：

- frame 0 和 final 均为同一 N、同一组 point_id；
- final signature2(ddof=1) == ['54.26','47.83','16.77','26.94','-0.06']；
- final 使用与 N_repr 相同的几何覆盖门槛；
- 至少 3 个随机种子中 3/3 通过才称“可靠通过”；2/3 只能称 borderline；
- 不以 MSE 单独定义成功，MSE 只作诊断。

不同 N 的优化预算必须公平：三点更新一次参与 3 个点，因此用“每点提案暴露次数”定义预算：

    exposure = 3 * total_steps / N

pilot 统一 exposure=20；确认性运行 exposure=50。于是：

    total_steps = ceil(exposure * N / 3)

禁止所有 N 都固定跑 60000 步然后比较最低点数，因为那会让小 N 获得远多于大 N 的每点更新机会。

本轮实际演化验证不生成 GIF，只输出末帧 CSV、必要 PNG 和 metrics，节省计算和仓库空间。

## 5. 构造目标形状套件，不只用一个校徽

至少建立 10 个受控目标变体，尽量复用现有真实几何，不创造无关花哨数据。

建议最低集合如下；如果某个变体无法从现有几何稳定构造，可换成等价受控变体，但必须在 target_suite.json 记录：

1. outer_ring_only
2. double_ring
3. octagram_only
4. rings_plus_octagram
5. chinese_nan_only
6. chinese_nan_kai
7. english_1919_only
8. core_emblem_5layer = rings + octagram + 南 + 開
9. full_emblem_6layer = core + NANKAI UNIVERSITY 1919
10. 一个现有非校徽形状，例如 flower，作为不同拓扑结构的外部检查

为了增加样本量，可以再加入 2~4 个明确、可解释的嵌套变体，例如：
- ring_plus_chinese
- star_plus_chinese
- ring_plus_english
- core_without_outer_ring

不要生成几十个随机图案。目标是形成可解释的复杂度梯度，而不是扩大工程范围。

每个 shape 必须有：
- shape_id
- included_layers
- source_geometry
- mandatory_components
- geometry_hash 或确定性版本标识

输出：analysis/complexity/target_suite.json

## 6. 图形复杂度指标：必须按下列定义实现

创建 src/shape_complexity.py。所有指标都基于高分辨率骨架/有序曲线几何 G，而不是 target slots。

### 6.1 尺度项

设 D = 目标几何 bounding-box diagonal，所有比较使用同一 0~100 数据尺度，同时也报告归一化量。

- L_total：所有曲线/骨架的总欧氏弧长。
- L_norm = L_total / D。

对于 raster skeleton，8 邻接图边长必须按真实数据坐标计算：水平/垂直边为实际像素映射长度，对角边用真实欧氏距离；不能简单用“像素个数 * 常数”冒充长度。

### 6.2 robust non-local feature separation g05

g05 不是相邻骨架采样点距离，也不是 marker size。

目的：衡量两个“几何上不同的局部结构”彼此有多近，例如两条相邻文字笔画。

实现要求：

1. 将 skeleton/curve 建图，保留 8-neighbor 或有序 polyline 邻接。
2. 对每个节点，用有限 BFS/局部图距离排除其同一局部邻域；至少排除图上 10 个 edge-hop 或等价的局部弧长窗口。
3. 在剩余非局部节点中找欧氏最近距离 d_nonlocal(i)。可用 KDTree 生成邻近候选，再过滤 graph-neighborhood，避免 O(M^2)。
4. g05 = d_nonlocal 的 5th percentile；同时保存 median、min 仅用于诊断。
5. 绝不能直接使用 absolute min 作为主指标，因为一个像素噪声/交点会让它接近 0。
6. 对真实 junction 处不同分支相交，距离 0 是拓扑本身，不应使整个 g05 崩溃；junction 邻域应在局部排除窗口中处理。

写单元测试：两条靠近的平行线的 g05 必须显著小于两条远离的平行线；整体等比例缩放 s 后 L 和 g05 同乘 s，而 L/g05 基本不变。

### 6.3 拓扑与曲率项

从 skeleton graph 计算并保存：

- n_components
- n_endpoints：degree == 1
- n_junctions：degree >= 3；相邻的 junction 像素应聚类成一个 junction region，不能一个交叉处计几十次。
- cycle_rank：E_graph - V_graph + n_components，按图论第一 Betti 数；需要先避免重复边计数。
- total_turning：有序曲线上的总绝对转角 / pi。对 raster 分支，可分解成 junction-to-junction / endpoint-to-junction paths 后计算。
- n_sharp_turns：局部转角超过 30 degrees 的稳定转折数，邻近高曲率节点要聚类，避免一处尖角被多次计数。

不要把“汉字/英文”本身作为 complexity dummy；如果指标合理，文字复杂性应由长度、间距、分叉和转折体现。

### 6.4 主复杂度变量

先定义不带拟合参数的主变量：

    S_sampling = L_total / g05

并另外报告 topology vector，而不是先拍脑袋规定 alpha/beta/gamma 权重。

可附加一个纯诊断 composite：

    T_raw = n_endpoints + n_junctions + cycle_rank + total_turning

但 T_raw 不得被预先称为“真正复杂度”。

## 7. 矩相容性必须与几何复杂度分开

这是本项目最重要的识别点之一：图形很简单，也可能与参考均值/协方差不相容；增加 N 不能自动修复支持集的矩冲突。

创建研究用 moment feasibility 检查，不修改生产统计定义。

### 7.1 连续/分数密度松弛

从目标高密几何候选位置 g_j 上求非负权重 w_j，检查：

sum w_j = 1
sum w_j * (g_j - MU_0) = 0
sum w_j * (g_j - MU_0)(g_j - MU_0)^T = C_target

这里对应固定 N 时，经验分布二阶中心矩为 ((N-1)/N) * COV_0；但为了先判断几何支持本身，另做 N -> infinity 的连续支持检查，目标用 COV_0。

同时加入每个 mandatory layer 的最低质量约束，最低质量按弧长占比给出下限，并设置一个很小的 floor，禁止 LP 把难画的小层权重压成 0。

若 exact LP feasible：moment_support_feasible=true。

若 exact infeasible：再求最小标准化 moment residual，输出 moment_residual_min，不得直接说“永远无解”，只能说在当前冻结几何支持和层质量约束下不可精确匹配。

### 7.2 离散 N 的目标矩差异

对每个实际 N 构造 slots 后，重算：

- target mean
- target sample covariance
- LB_mean
- LB_cov
- LB_total

LB_total 的计算使用与项目已经采用的一致 Bures/Wasserstein 二阶矩下界；必须有回归测试：
- Q=P 时约 0；
- 纯平移时 LB_mean 等于平移向量平方范数；
- 实际 assignment MSE 不应显著小于适用下界。

表示成功 moment gate 暂定：LB_total <= 0.05。若大多数现有成功目标都明显高于/低于 0.05，不要私自调整；先在报告中列分布，再说明该阈值是否需要外部复核。

## 8. 搜索 N_repr*：先便宜地做，不跑演化

候选初始网格：

[142, 284, 426, 568, 852, 1136, 1704, 2272, 2840, 4260, 5680, 8520, 11360]

对每个 shape：

1. 计算一次 complexity metrics 和 continuous moment feasibility。
2. 若 support moment infeasible，仍计算纯视觉 coverage threshold，但 N_repr_moment 标记为 null，并注明 POINT_COUNT_NOT_THE_ONLY_BOTTLENECK。
3. 若 feasible，对候选 N 逐个构造 slots，检查第 4.1 节的 coverage + moment gate。
4. 找到首个 fail -> pass bracket 后，在两个 N 之间用整数二分/自适应搜索细化；但是只有在局部结果近似单调时才使用二分。
5. 检查至少前后 2 个 N 的单调性。若 pass/fail 非单调，停止二分，记录 NON_MONOTONIC_THRESHOLD，并报告最小测试通过值而不是假装有唯一理论阈值。
6. N 可以是任意整数，不要求 142 的倍数。

输出：analysis/complexity/point_thresholds.csv
至少包含：
shape_id, L_total, g05, S_sampling, topology metrics, moment_support_feasible, moment_residual_min, N_repr_visual, N_repr_moment, threshold_status, tested_Ns。

## 9. N_evo 实际验证：只选少量代表形状

不要对全部 10+ shape 做大规模演化。只验证至少 4 个代表：

- outer_ring_only 或同级简单形状
- rings_plus_octagram（中等）
- core_emblem_5layer（复杂）
- full_emblem_6layer（最高复杂度）

如果 flower 的旧算法接口容易复用，可把 flower 作为第 5 个；否则不强求。

对每个代表 shape，在 N_repr_moment 附近选择：
- ~0.8 * N_repr
- ~1.0 * N_repr
- ~1.25 * N_repr

取整数并确保 >=142。每个 N 用 3 seeds，pilot exposure=20；只有 transition 附近需要确认时再 exposure=50。

不得生成 GIF；只保存最终 CSV、必要 metrics、一个低分辨率 comparison PNG。

输出：analysis/complexity/evolution_validation.csv
字段至少：shape_id, N, exposure, steps, seed, invariant_pass, geometry_pass, success, runtime_sec。

N_evo*：3/3 seeds 通过的最小测试 N；若只有 2/3，标 borderline。

## 10. 拟合“复杂度 → 点数”的关系：简单模型优先

只在 moment-support-feasible 且 N_repr_moment 有定义的 shape 上拟合。

至少比较下面三个模型：

M1: log(N_repr) = a + b * log(L_total)

M2: log(N_repr) = a + b * log(S_sampling)

M3: log(N_repr) = a + b1*log(S_sampling) + b2*log(1 + n_endpoints + n_junctions + cycle_rank + total_turning)

如果样本数 >= 12，可额外比较 ridge 回归，将 endpoints, junctions, cycle_rank, total_turning 分开；否则禁止上高维模型。

模型评价不能只报训练 R^2。必须做 leave-one-shape-out cross-validation，输出：
- CV MAE on log N
- median multiplicative error = median(exp(abs(error)))
- max underprediction factor
- in-sample R^2 仅作为补充

模型选择规则：选择 CV 误差接近最佳（<=最佳的 1.10 倍）中最简单的模型。若 M2 已经足够好，不要为了更高训练 R^2 强行选 M3。

最终给出一个经验形式，例如：

    N_hat = exp(a) * S_sampling^b

但系数必须来自实际拟合，不得在 prompt 里预填。

再根据 leave-one-out 的正向残差给一个保守 safety factor，例如 90th percentile underprediction factor；样本太少无法稳定估计时，就报告 observed max underprediction factor，不伪造 90% 置信保证。

## 11. 关键解释：必须避免几个错误结论

报告中必须明确：

1. “最少点数”依赖显示尺度、目标几何和验收阈值，没有绝对通用 N。
2. N_repr* / N_evo* 都是“已测试范围中的最小通过值”，不是数学证明的最小值。
3. 更复杂通常需要更多点，但 point count 不能修复所有 moment-incompatibility。
4. 现有 2840/5680/11360 结果可以作为证据，但不能因为它们恰好是倍数就拟合出“点数按倍数增长”的假规律。
5. 同一个目标在不同 marker 大小/画布分辨率下，视觉最小 N 会改变。
6. 不得把算法收敛失败等同于表示能力不足；因此本轮专门分 N_repr 和 N_evo。
7. 不得把同一 shape 的多个 N 当成多个独立 shape 样本去拟合 complexity -> N*。
8. 若只有 10~14 个 shape，报告必须称 exploratory empirical relation。

## 12. 必须新增的代码和测试

建议新增：
- src/shape_complexity.py
- src/complexity_experiment.py
- tests/test_shape_complexity.py

测试至少覆盖：

A. 直线：2 endpoints、0 junction、0 cycle。
B. 圆：0 endpoints、0 junction、cycle_rank=1，长度接近 2*pi*r。
C. 两条平行线：near 版本 g05 < far 版本 g05。
D. scale invariance：整体缩放 s 后 L 和 g05 近似同乘 s，S_sampling=L/g05 近似不变。
E. T/junction 聚类：一个十字交叉只算一个 junction region，不是多个相邻像素。
F. deterministic：同一 geometry/config 重跑复杂度指标一致。
G. moment LB：identical moments -> ~0，pure translation -> correct mean term。

必须先跑测试再跑大规模实验。失败时修根因，不改测试期望来迁就代码。

## 13. 输出文件

全部新研究结果放 analysis/complexity/，不要覆盖已有 repair_v2 结果。

必须生成：

- analysis/complexity/target_suite.json
- analysis/complexity/shape_metrics.csv
- analysis/complexity/point_thresholds.csv
- analysis/complexity/evolution_validation.csv
- analysis/complexity/model_comparison.csv
- analysis/complexity/model_fit.json
- analysis/complexity/complexity_vs_points.png
- analysis/complexity/complexity_report.md
- analysis/complexity/checkpoint.md

complexity_vs_points.png 至少包含：
- x = S_sampling（建议 log scale）
- y = N_repr_moment（log scale）
- 每个 shape 标注 shape_id
- 拟合曲线
- moment-incompatible shape 用不同 marker，仅展示但不参与 N 拟合
- 若有 N_evo*，用另一种 marker 叠加

不要生成大量中间 PNG，不要提交缓存、临时帧、巨大 GIF。

## 14. complexity_report.md 的固定结构

1. Research question
2. Frozen display / acceptance definition
3. Shape suite
4. Complexity metric definitions
5. Moment-feasibility distinction
6. N_repr results
7. N_evo validation
8. Model comparison
9. Best empirical relation
10. Prediction example：以 full_emblem_6layer 为例，给出模型预测 N、实际最小测试通过 N、误差倍数
11. Limitations
12. Reproduction commands

在第 9 节必须写清：
- 拟合公式和系数
- 样本量
- CV 指标
- 能否支持“大致正比”或幂律说法
- 不能支持什么

## 15. 计算预算与停止条件

本轮重点是关系识别，不是再榨取极限画质。

停止条件：

- complexity metrics 单元测试通过；
- >=10 个 shape 得到 shape_metrics；
- feasible shape 得到 N_repr threshold；
- >=4 个代表 shape 有 N_evo 验证或明确记录为何无法运行；
- 三个基础模型完成 LOOCV；
- 报告和图生成。

若某个单独 shape 的 actual evolution 在两个 exposure 档和 3 seeds 下仍不稳定，记录 OPTIMIZER_LIMITED，不得无限加步直到它通过。

若 full 6-layer 的已有 2840/5680/11360 运行与本轮预算口径不一致，可作为 descriptive evidence，但 N_evo threshold 的正式比较必须使用本轮 exposure-normalized 运行。

## 16. Git 提交与结束

1. 不要 git add .；只暂存本轮新增/修改研究文件。
2. git diff --check。
3. 跑 tests/test_shape_complexity.py 和本轮实际使用的定向测试。
4. 提交到现有 feature/gemini-fixed-n-evolution 分支并 push。
5. 不合并 main。
6. 最终回复不超过 18 行，必须给：
   - TASK_ID
   - 实际远端 HEAD
   - shape 数量
   - moment-feasible 数量
   - 得到 N_repr* 的数量
   - 实际演化验证形状数
   - 最佳模型公式
   - LOOCV 指标
   - full 6-layer 的预测 vs 实测
   - 主要限制
   - 产物路径
   - 是否有未完成项

禁止把“测试通过”写成“普适定律已证明”。若关系弱或样本不足，直接报告关系弱/探索性，不得为了完成任务强行制造显著结论。