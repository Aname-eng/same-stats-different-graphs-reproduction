# 当前执行任务：Flash 01——只修验收输入与文件检查，不运行演化

TASK_ID: SSDG_FLASH_01_AUDIT_CONTRACT_20260915
STAGE: 01
STATUS: READY_FOR_EXECUTION
REPOSITORY: Aname-eng/same-stats-different-graphs-reproduction
WORK_BRANCH: feature/gemini-fixed-n-evolution
REVIEWED_CODE_BASE: ee3ad149b0c37814e76e90763546303f0d207ea3
EXECUTOR_PROFILE: 用户选择的 3.7flash-high，本任务不依赖模型专属 API

## 1. 任务只做这一件事

修复 src/independent_verifier.py 对输入、点身份、必需快照与 GIF 文件的误判，用已提供的契约测试验证。不要改变优化算法、重新生成校徽、重做整个 V2。完成本阶段后提交、推送并停止；不得自行进入下一阶段。

用户最终目标仍是：在第 0 帧前按目标选择 N；同一组等权点从密集恐龙演化到完整校徽；全程 N、point_id、五项统计量不变；校徽比例不变。当前只是修复这个项目的验收基础，不是宣布最终目标已经实现。

本 prompt 替换上一版“一轮完成所有修复”的执行安排。历史 prompt 保留在 Git 历史中，旧提示词的不变量仍有效，但本轮不再完整重读长日志或执行旧任务清单。必须遵循工作区中适用的项目/安全指令。

## 2. 范围、起点与节约额度

先检查 git status、当前分支、remote；fetch 后安全同步 WORK_BRANCH。上述 SHA 只是审查起点，不是回退要求。不能 reset --hard、clean、force push、覆盖未提交改动或合并 main。已有同名修改时先比较，不重复实现；确有冲突则保留内容，用独立 worktree 或输出 BLOCKED。

本轮只需阅读：
1. 本文件。
2. review_tests/test_flash01_audit_contract.py。
3. src/independent_verifier.py。
4. src/stats_audit.py 中 stats5、signature2、is_legal 的接口。
5. 必要时 output/repair_v2/seed_42/metrics.json 的字段，以及对应快照的表头。

允许修改：
- src/independent_verifier.py。
- analysis/flash01/ 下本次日志、一次真实现有运行的复核 JSON、简短 stage_result.json 和 checkpoint.md。
- 如确有必要，可在 tests/ 下新增补充测试；不能改已有测试。

禁止修改：
- 本 prompt 与 review_tests/test_flash01_audit_contract.py 的要求和断言。
- 优化器、目标生成器、几何真值、统计公式、种子 CSV、Slots、舍入规则与阈值。
- 旧实验输出和旧报告；不运行 src/generate_reports.py。

禁止为本阶段启动模拟退火、候选 N 扫描、GIF 重渲染、GPU 任务、整仓重构、联网调研或多个子代理。测试里的 32 点合成样本与 8×8 GIF 只是局部测试夹具，不得当作真实恐龙/校徽成果。

## 3. 已确认的错误位置

当前源代码存在以下逻辑；用实际代码定位，不按易变化行号操作：
- 缺 point_id 时用 np.arange 补造身份。
- point_id 先转 int，可能将非整数值截断后放行。
- expected_n 不一致只追加原因，之后仍以实际行数作为正确 N。
- 第一份、最后一份匹配文件被直接当作第 0 帧与真正末帧。
- metrics.json 只检查存在，不读必需字段。
- 动画只看路径存在，且会借用兄弟目录 seed_42 的 GIF。
- 仅检查少量 CSV，却命名为 trajectory_invariants_pass。

本轮不修几何缺口算法、不证明文字可辨、不证明 GIF 与轨迹对应；这些必须明确保留为待审计，不能让总 task_pass 变成 true。

## 4. 保留接口，按下列返回契约实现

保持现有两个函数的参数兼容：
  audit_snapshot_invariants(csv_path, expected_n, ref_ids) -> dict
  audit_trajectory_and_run(run_dir, expected_n=None, gt=None) -> dict

可以增加模块内小辅助函数，不要创建另一套验收框架。保持现有可用返回字段，同时补全下面字段。数据错误返回可序列化失败字典，不应发生 KeyError/min(empty)/NaN JSON。不能以捕获所有异常并返回成功或空字典来掩盖程序错误。

### 4.1 单个快照

按此顺序检查：
1. 文件可读，CSV 不是零字节或仅表头；否则 SNAPSHOT_EMPTY 或 SNAPSHOT_UNREADABLE。
2. 必须有 point_id、x、y 三列，允许已有附加列。缺任何必需列：SNAPSHOT_COLUMNS_MISSING。
3. 行数严格等于外部 expected_n，不能用实际行数覆盖 expected_n。否则 POINT_COUNT_MISMATCH_EXPECTED。
4. 在转整数前检查 IDs 可解析、有限、值为整数且在所采用整数类型范围内；1000.25 不能转成 1000 后通过。非法：POINT_ID_INVALID。
5. IDs 唯一；重复：POINT_ID_DUPLICATE。与 ref_ids 按原始行顺序逐项相同；不同：POINT_ID_ORDER_MISMATCH。不能先排序，不要求 ID 从 0 开始。ref_ids 本身也应检查长度、唯一性和合法性。
6. x/y 是可解析的有限数，NaN/Inf：COORDINATES_NONFINITE。不能清理、补值、丢行或重排后验收。
7. 严格 0 < x,y < 100，等于 0 或 100 也不合法：COORDINATES_OUT_OF_BOUNDS。
8. 用现有 signature2(..., ddof=1) 从真实坐标重算，对照 ['54.26','47.83','16.77','26.94','-0.06']；不同：STAT_SIGNATURE_MISMATCH。

返回至少包括原有 invariants_pass、signature2，以及 reason_codes。通过时 reason_codes 可为空。无法计算的统计量或 bounds 用 null，而不是 NaN/Inf；所有返回都必须能 json.dumps(result, allow_nan=False)。实际合法输入必须得到 invariants_pass=true，不能一律返回 false。

### 4.2 运行输入契约

先读取并解析本 run_dir 的 metrics.json：
- 必需 n_points：非布尔整数且 >=3。
- 必需 total_steps：非布尔整数且 >0。
- random_seed 可记录，但不是本阶段必需字段。
- 缺文件、坏 JSON、缺键或上述类型/范围不对，返回 METRICS_INVALID。

预期 N 的规则必须唯一：
- 调用者传 expected_n 时，以它为约束；metrics.n_points 必须与它相同。
- 未传时，以已校验的 metrics.n_points 为约束。
- 绝不能用 frame 0 的行数替代外部约束来掩盖不一致。

快照必须包含 snapshots/frame_000000.csv，以及按 total_steps 格式化的 snapshots/frame_{total_steps:06d}.csv。
- 缺第 0 帧：FRAME0_MISSING。
- 缺真正末帧：FINAL_FRAME_MISSING。最后一份较早快照不能代替末帧。
- 支持稀疏快照，但这只说明这些保存状态可审计，不能说明全部接受状态可重放。
- 文件名 step 需可解析为整数，按 step 排序，不接纳超出声明总步数的状态。
- 从合法第 0 帧读取参考 IDs，再调用快照验收逐一比较；缺 ID 不能合成。
- 先验证空数据/非有限坐标，不能把坏数组传入 gt.evaluate。

新增布尔字段：
- input_contract_pass：metrics 合法、N 约束一致、必需端点齐全、全部快照结构和不变量合法。
- snapshot_invariants_pass：已提供快照的不变量合取，同时预期 N 必须一致；不许空列表 all() 通过。
- 保留 final_geometry_pass：安全输入才调用真实 gt.evaluate；传入 gt 时使用其 evaluate 接口，不得把 false 改成 true。

### 4.3 GIF 文件有效性——只验文件，不冒充轨迹一致性

本阶段只核对本 run_dir/evolution_pure_scatter.gif。不存在：ANIMATION_MISSING。
使用 Pillow 实际打开它，确认 GIF、至少 2 帧、每帧能 seek/load 解码且有正播放时长。零字节、损坏或只有静态一帧：ANIMATION_INVALID。
新增 media_valid 字段表示这项结果。有效 GIF 必须可得到 media_valid=true。
禁止使用兄弟目录的 GIF、任意 *.gif 路径或只看文件大小来通过。

整个项目最终可以只交付一个选定种子的代表动画，不要求每种子都做一遍；但未来须用明确 manifest 绑定该动画和它自己的轨迹。本阶段不实现共享动画政策，也不把 seed_42 动画当作 seed_101 的媒体证据。

重要：两帧可解码 GIF 只证明文件能播放，不能证明它画的是这些坐标。因此 media_valid 不等于 deliverables_complete 或任务通过。

### 4.4 明确保留“未做完整轨迹审计”

当前只有少量 CSV、抽样事件和文字 all_frames_legal，不足以证明完整轨迹。本阶段不实现重放：
- trajectory_invariants_pass=false。
- trajectory_audit_status='NOT_AUDITED'。
- reason_codes 包含 TRAJECTORY_NOT_AUDITED。
- deliverables_complete=false，task_pass=false，直到后续阶段真正接入完整证据检查。

这是诚实区分验收范围，不是允许将所有子检查写死失败：合法快照、完整输入契约、有效 GIF、真实几何评价仍分别返回计算结果。测试中的正例明确检查这一点。

每个运行结果无论失败在哪里，都应具有 input_contract_pass、snapshot_invariants_pass、media_valid、trajectory_invariants_pass、final_geometry_pass、deliverables_complete、task_pass、reason_codes。其他旧字段尽量兼容。不能读取旧报告的 task_pass 来替代计算。

CLI 对请求却不存在的运行目录，应输出一个有原因的失败记录，而不是跳过。必要项未通过时退出码非零。不要为使 CLI 退出 0 而修改判据。

## 5. 已提供不可削弱的契约测试

文件：review_tests/test_flash01_audit_contract.py，包含 18 个 test 方法及部分 subTest。
UTF-8/LF 原始 SHA256：e0b99fe6d5c9fbfaa5ac3333fd16aa2a026d24e091fbdfb5fab7811b3a22b08c。
Windows 换行转换可能改变工作树字节哈希；与 Git blob/规范化 LF 内容核对，不能因换行单独声称内容被篡改。

测试覆盖：合法快照；缺 ID；小数 ID；重复/乱序 ID；预期 N 不符；空/缺列 CSV；NaN/Inf；边界与统计跨签名；合法文件不等于完整轨迹；运行 N 约束；缺首/末帧；坏 metrics；metadata N；坏/静态 GIF；兄弟 GIF 误用；空目录；几何 false 不被覆盖。

GeometryProbe 仅在这些测试中隔离几何模块，使测试不依赖真实图片。它不是几何验收证据，也不得复制到生产代码或实际审计中。合成正例与已有校徽正例不同，不得把其通过写成“校徽已可辨”。

本阶段外部已做：测试文件语法检查、合成正例五项统计和坐标边界检查。
尚未做：此测试与修复后仓库的集成验收；你必须在本地执行。不准引用“18 个测试”就声称“18 个测试已经通过”。

## 6. 严格执行顺序与停止条件

A. 不改代码先跑一次定向测试，保存原始 stdout/stderr、命令、退出码到 analysis/flash01/tests_before.log。旧版本存在缺字段和失败是预期诊断，不是删测试的理由。依赖/导入错误与业务断言失败要分开记录。

命令：
  python -m unittest discover -s review_tests -p test_flash01_audit_contract.py -v

B. 只修改 independent_verifier.py，按第 4 节顺序处理输入，再处理文件有效性和范围字段。不要让语言模型另起算法设计；不要改调用者数据来迁就验收器。

C. 再运行同一命令，保存 tests_after.log。失败时只阅读对应 traceback 与相关函数；同一根因最多追加两轮修复/复测，仍失败则写 BLOCKED、保留实际证据并停止。不许改期望值、skip、expectedFailure 或缩小测试范围来全绿。

D. 所有 18 个方法无 skip/expectedFailure 地通过后，运行：
  python -m py_compile src/independent_verifier.py
  git diff --check

然后只复核一次已有 Seed 42，不重新优化、不渲染：
  python -m src.independent_verifier --run-dirs output/repair_v2/seed_42 --output analysis/flash01/existing_run_audit.json

本阶段真实审计返回 task_pass=false、TRAJECTORY_NOT_AUDITED，并可能返回非零退出码是预期；不能因此反复跑演化来追求“全部 PASS”。记录实际子项结果，不预填。

E. 写 analysis/flash01/stage_result.json，字段至少：
  task_id, starting_commit, modified_files, tests_command,
  tests_run, failures, errors, skipped, test_exit_code,
  stage_status, project_task_pass, pending_items, evidence_paths。
- stage_status 只能是 READY_FOR_REVIEW 或 BLOCKED；测试通过仍需外部审查，不自封最终 VERIFIED。
- project_task_pass=false；本阶段通过不等于整个项目完成。
- tests 统计必须从实际 unittest 输出/结果读取，不抄本 prompt 的 18 当作运行数。
- pending_items 至少包含真实几何/笔画缺口、完整事件重放与动画绑定、自动 N 正式入口、真实多种子方法比较及报告修正。

F. 写不超过 40 行 checkpoint.md，说明改了什么、实际卡在哪、下一次从哪个命令/失败继续；不要复制整份提示词或长历史。

G. 仅暂存本阶段允许修改的文件；检查 git diff 和 git status 后提交、推送现有功能分支。不要 git add .，不改旧输出，不合并 main。最终用 git rev-parse HEAD 和远端 ref 实际核对 SHA；不要人工拼写哈希，不循环刷新 manifest 追求自引用 commit。

## 7. 给用户的结束回复固定为短交接

不超过 12 行，提供 TASK_ID、阶段状态、实际修改文件、测试运行/失败/跳过数、原始日志路径、现有 Seed42 复核结果、剩余项、真实本地/远端 SHA 及 push 状态。
不能说“无未完成项”“整个校徽项目完成”或“已目视确认”——本阶段没有授权做这些。

## 8. 后续路线仅供定位，不得本轮自行执行

02：按真实原图核验几何；有序笔画与闭合曲线缺口；从合格样例出发的真正删笔画/压环测试。
03：只用一套优化循环，优先验证简洁 Method C；记录完整事件，动画从同一轨迹渲染；自动 N 接到正式入口。
04：必要的多种子与同口径对照；报告从实算指标生成，不再硬编码 PASS、覆盖率或 D 最优结论。

审核通过或用户明确授权后，才读取新的当前任务单进入后续阶段。停止在本阶段，是分阶段交付，不是放弃整个项目。
