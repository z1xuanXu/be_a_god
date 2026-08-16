# 模拟神 Skill 游戏设定蓝图 v1.71 补充：UI 全素材化与高清地图元素

## 本轮确定

- 前端 UI 不再只靠 CSS 画纸张、边框和按钮；纸质界面、面板、按钮、地图节点、棋子旗帜、地形和装饰都应优先复用本地 PNG 素材。
- 地图放大后素材发糊的主要原因是上一版把素材压得过小。新策略是保留高分辨率透明 PNG，CSS 只控制显示尺寸，不再把项目资产强行缩成小图。
- 生成素材必须保存进 skill 源文件 `assets/frontend-template/img/`，不能只停留在对话或全局生成图片目录。

## 新增 / 重置素材类型

当前地图和 UI 素材包括：

- UI：`ui-frame.png`
- 标记：`flag-marker.png`
- 自然地形：`forest-stamp.png`、`forest-cluster-stamp.png`、`hills-stamp.png`、`rocky-hills-stamp.png`、`mountain-ridge-stamp.png`、`creek-stamp.png`
- 人造/文明元素：`castle-stamp.png`、`village-stamp.png`、`bridge-stamp.png`、`road-stamp.png`、`farm-stamp.png`、`ruins-stamp.png`
- 水域/边缘：`marsh-stamp.png`、`lake-stamp.png`、`shore-rocks-stamp.png`
- 纸纹/边饰：`parchment-overlay.png`、`corner-ornament.png`

## 前端呈现规则

- `map-layers.brushes` 仍然是地形真相。PNG 地形印章只是让玩家更直观看到森林、山、河流、小溪。
- 地图默认背景可以铺少量低透明度的城堡、村镇、桥、道路、田地、遗迹、湖泊、沼泽、山脉等素材，避免地图空洞。
- 地点节点应根据 `kind/type/level/id/name` 自动推断素材，例如 castle、village、bridge、farm、ruins、lake、marsh、mountain、hills。
- UI 面板和按钮可以用 `ui-frame.png` 与 `parchment-overlay.png` 做装饰，但不能牺牲文字可读性。

## 验收边界

- `prepare_frontend.py` 必须复制完整 `img/` 目录。
- `check_install_ready.py` 与 `smoke_test.py` 必须验证新增 PNG 素材存在且有效。
- 高分辨率素材允许文件更大；优先保证地图放大后不糊。
- 不能为了视觉装饰改变 canon 文件、剧情分支、坐标或行动请求流程。
