# Be A God 项目接手文档

更新时间：2026-08-15  
项目根目录：`F:\be_a_god`  
主源码：`F:\be_a_god\be-a-god`  
当前保留世界：`F:\be_a_god\worlds\reedbend-demo`

## 1. 项目定位

Be A God 是一个可持久化叙事模拟游戏：

- 正史、角色状态、分支、随机日志和地图状态保存在世界文件中；
- 本地前端是观察与命令界面，不是正史作者；
- 玩家动作通常先生成待提交请求，再由后端脚本/模型结算；
- 前端只读取过滤后的玩家可见剧情，不得直接读取原始 Markdown 或泄露 GM 内容。

## 2. 当前目录结构

```text
F:\be_a_god\
├─ be-a-god\                         核心 skill、脚本、模板和素材
│  ├─ SKILL.md
│  ├─ assets\frontend-template\     长期前端源文件
│  │  ├─ index.html
│  │  ├─ app.js
│  │  ├─ styles.css
│  │  ├─ tutorial.css
│  │  └─ img\
│  ├─ assets\world-template\
│  ├─ references\
│  └─ scripts\
├─ worlds\reedbend-demo\            当前唯一保留的可玩世界
├─ tests\                            项目专项测试
├─ 模拟神Skill游戏设定蓝图*.md
└─ 验证记录-片段*.md
```

前端长期修改必须先改：

```text
F:\be_a_god\be-a-god\assets\frontend-template\
```

然后用 `prepare_frontend.py` 同步；不要只改世界内的生成副本。

## 3. 当前世界状态

活动世界：`reedbend-demo`  
活动分支：`story/main`  
当前时间：`year 1, day 12`  
当前地点：`Reedbend Market`  
最新确认事件：`EVT-0007`  
最新编年条目：`CHR-0007`

当前场景摘要：

> 五天里河水继续退落。河粮议席补录了新来难民，米拉带渡船队清理旧河道，塔文公布第二轮粮仓核验，老塞拉则把见证绳结写入神龛仪式。第十二日清晨，集市周围的浅滩露出一圈旧水痕，像等待河神重新落笔。

重要说明：

- 第 8～12 天只保存在 `CURRENT.md`/`SAVE.md` 摘要中；没有对应 `EVT-0008+` 和 `CHR-0008+`。
- 因此前端历史剧情目录仍只到第 7 天，这是现有数据事实，不是前端漏读。
- `SAVE.md` 仍列出 `AR-DEMO-MIRA` 与 `QUEUE-DEMO-FLOOD`；需通过正常状态流程处理，不能直接删除审计文件。

关键路径：

```text
F:\be_a_god\worlds\reedbend-demo\ACTIVE.md
F:\be_a_god\worlds\reedbend-demo\PLAYER.md
F:\be_a_god\worlds\reedbend-demo\story\main\SAVE.md
F:\be_a_god\worlds\reedbend-demo\story\main\CURRENT.md
F:\be_a_god\worlds\reedbend-demo\story\main\events\
F:\be_a_god\worlds\reedbend-demo\story\main\state\entities\
F:\be_a_god\worlds\reedbend-demo\story\main\state\terrain-brushes.json
F:\be_a_god\worlds\reedbend-demo\dashboard\
F:\be_a_god\worlds\reedbend-demo\frontend\
```

## 4. 已实现的剧情与上下文机制

- 交互包默认只读当前存档、玩家配置、目标状态卡和必要规则；
- 自动查询事件图；
- 按人物、地点、标签和意图选择最多 3 个关键旧事件；
- 沿事件 `source` 指针在字符预算内读取正文；
- 当前分支可读取父分支分叉点以前的事件；
- 禁止读取兄弟分支；
- 因果引用使用结构化 ID，普通自然语言存入 cause/effect notes；
- 多分支回溯测试位于 `F:\be_a_god\tests\test_event_recall.py`。

完整剧情目前不是一个单独小说文件，而分散在：

```text
events\                 已确认事件与玩家可见正文
CURRENT.md              当前场景摘要
SAVE.md                 当前状态与剧情指针
chronicle\objective.md  客观编年
state\entities\         人物经历与状态
runtime\                交互包和结算支持文件
```

最终剧本导出可以补过渡、动作和文学衔接，但不得临时创造缺失的重大选择、秘密、死亡、关系或分支结果。

## 5. 当前前端能力

### 地图

- 世界层默认 `23 × 16 = 368` 格，超过原 35 格十倍；
- 地区层 651 格，近景层 1504 格；
- 只渲染当前缩放层，避免同时创建三套网格；
- 默认缩放 70%，最大缩放 1200%；
- 400% 以上显示“任务近景”；
- 拖动和同层缩放只更新容器 transform；
- 城邦、角色、地点和事件吸附到当前可见层六边格中心；
- 单格固定代表 `5000 米 × 5000 米`；
- 棋子宽高约为单格 72%，不得跨格；
- 左下比例尺为 `0 — 5 km`，长度随缩放等于一个格子屏幕宽度。

### 地形

已有草地、森林、丘陵、山脉、河流、湖泊、沼泽、沙漠、海岸、苔原、雪地、火山、荒原、草甸等素材。

确认画笔后：

1. 写入 `story/<branch>/state/terrain-brushes.json`；
2. 重建 `dashboard/map-layers.json`；
3. 覆盖范围内六边格切换对应地形图；
4. 同时显示 SVG 连续路径/粒子细节。

点选预览阶段不会修改正式地图。

### 棋子与城市

透明旗帜棋子目录：

```text
F:\be_a_god\be-a-god\assets\frontend-template\img\pieces\
```

已覆盖：角色、士兵、车辆、船、建筑、粮仓、神龛、资源、物件、事件、村庄、城镇、城市和要塞。所有地图棋子要求透明底、强深色描边、无圆形/方形/卡片底板。

### 控件素材

```text
img\ui\medieval-button-frame.png
img\ui\medieval-input-frame.png
```

所有普通按钮、输入框、下拉框和文本域使用透明中世纪素材，真实 DOM 文字叠在素材上。控件和装饰图禁止原生拖动，但地图平移与动作排序等应用拖拽保留。

### 教程

教程源文件：

```text
index.html
tutorial.css
app.js 中 showTutorialStep / bindTutorialNavigation
```

教程共六章：从零开始、认识界面、地图与棋子、进行一回合、地形画笔、全部按钮。主页面曾因行号前缀误写被破坏，现已清除并增加回归测试：

```text
F:\be_a_god\tests\test_tutorial_guide.py
```

## 6. 测试与验证状态

当前专项测试：

```text
F:\be_a_god\tests\test_event_recall.py
F:\be_a_god\tests\test_expanded_map_assets.py
F:\be_a_god\tests\test_tutorial_guide.py
```

最近验证结果：

```text
node --check app.js               通过
教程专项测试                       5 passed
事件回溯测试                       3 passed
大地图专项测试                     7 passed（最近阶段记录）
smoke_test.py                     passed
check_install_ready.py            ready: true, errors: 0
```

唯一常见 warning：全局 Codex skill 目录已存在；不代表源码失败。

曾在独立 QA 世界完成全新十回合测试：开局设定、规则、规则检查、人物移动/关注、地形、队列、互动结算、索引和导出均通过。该 QA 世界现已按用户要求清理，不再保留于项目目录。

## 7. 常用命令（当前终端为 bash）

Python：

```bash
PY='C:/Users/xuzix/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
```

同步前端：

```bash
"$PY" 'F:/be_a_god/be-a-god/scripts/prepare_frontend.py' \
  --world 'F:/be_a_god/worlds/reedbend-demo' --confirmed --overwrite
```

启动后端（默认端口通常 8765；端口被占用时改用其他端口）：

```bash
"$PY" 'F:/be_a_god/be-a-god/scripts/serve_frontend.py' \
  --world 'F:/be_a_god/worlds/reedbend-demo' --port 8765
```

语法和专项测试：

```bash
node --check 'F:/be_a_god/be-a-god/assets/frontend-template/app.js'
uv run --with pytest pytest 'F:/be_a_god/tests' -q
```

世界验证：

```bash
"$PY" 'F:/be_a_god/be-a-god/scripts/validate_world.py' \
  --world 'F:/be_a_god/worlds/reedbend-demo' --json
```

完整检查：

```bash
"$PY" 'F:/be_a_god/be-a-god/scripts/check_install_ready.py' \
  --skill 'F:/be_a_god/be-a-god' --run-smoke --json
```

## 8. 当前已知问题与后续优先级

1. `reedbend-demo` 第 8～12 天只有摘要，没有正式事件和编年正文。若继续游戏，应先决定忠实补录为事件，或明确把它作为时间跳跃。
2. 当前剧情目录是事件级玩家可见正文，不是完整连续小说；未来需要 scene/manuscript 持久化机制。
3. `SAVE.md unresolved_choices` 可能保留已结算队列 ID；应通过脚本修正状态同步，不能手删审计文件。
4. 前端部分使用原生 `prompt()` 的按钮较难自动化；后续可考虑改成应用内表单，但未经用户要求不要扩大范围重构。
5. 本项目不是 Git 仓库，不能依赖 `git diff`；修改前后需靠专项测试、文件检查和浏览器验证。

## 9. 清理记录（2026-08-15）

已删除可重新生成内容：

- `worlds\reedbend-qa-10turns*` 共 5 个 QA 世界，约 315MB；
- 根目录 `_tmp_*.png` 调试截图，约 11MB；
- `be-a-god\scripts\__pycache__` 与 `tests\__pycache__`，约 1.2MB。

保留：

- `worlds\reedbend-demo` 正式演示世界；
- 全部源码、模板、素材和测试；
- 设计蓝图与验证记录；
- 世界中的正史、运行支持文件和审计记录。

## 10. 接手顺序

1. 读本文件；
2. 读 `F:\be_a_god\be-a-god\SKILL.md`；
3. 读 `references\frontend-contract.md`、`storage-contract.md`、`game-master-protocol.md`；
4. 读当前世界 `ACTIVE.md`、`PLAYER.md`、`story\main\SAVE.md`；
5. 只按需求读取目标实体和关键事件，不要一上来读取全部历史；
6. 前端修改只改模板，之后同步；
7. 每次交付明确区分“已实际验证”和“尚未验证”。
