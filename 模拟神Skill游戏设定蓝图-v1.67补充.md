# 模拟神 Skill 游戏设定蓝图 v1.67 补充

日期：2026-08-13

## 本轮完成项

- 新增 `be-a-god/scripts/external_play_turn.py`：把“脱离 Codex 的外部 API 回合”包装成一个可复制流程。它可以创建或加载 compact interaction packet，默认 dry-run，不联网；只有显式 `--call` 才调用 `setup/llm-api.config.json` 配置的 OpenAI-compatible API。
- `external_play_turn.py` 只写 support-only run artifacts 到当前枝丫的 `runtime/external-model-runs/<run-id>/`，包括 packet、请求记录、LLM 响应、候选结算 JSON；不会直接修改 canon。候选 JSON 会先经过 `validate_settlement_result.py`，然后只输出建议的 `settle_interaction.py` 命令。
- 前端画笔编辑器增强：新增 width、density、jitter、color 控件；新增 copyable `points-json`、undo、clear；生成的 `terrain-brush` action payload 会携带样式字段，后续仍然通过 `create_action_request.py` -> `set_map_brush.py` 确认路径写入。
- `be-a-god/references/player-quickstart.md` 已重写为可读版本，覆盖安装、开局、继续、前端、画笔、handoff、外部 API 包装/低层调用。
- 验收场景扩展到 34 条，新增 `External model packaged turn` 与 `Brush editor controlled styling`；`smoke_test.py` 和 `check_install_ready.py` 已纳入对应检查。

## 设计边界

- 外部模型只负责语义生成与候选结算，不拥有直接写正史权限。
- 前端画笔只负责预览和生成 action request，不直接改 `dashboard/map-layers.json` 或世界正史。
- 命令式地形修改和画笔式修改共用同一套 terrain brush 数据层，避免出现两套地图格式。
