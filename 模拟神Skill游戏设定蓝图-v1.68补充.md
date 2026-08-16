# 模拟神 Skill 游戏设定蓝图 v1.68 补充

日期：2026-08-13

## 本轮完成项

- 新增 `be-a-god/scripts/create_demo_world.py`：生成一个小而完整的真实开局演示世界。默认世界 ID 为 `reedbend-demo`，需要 `--confirmed` 才写入，不会静默覆盖已有世界。
- demo 世界包含：确认过的 `WORLD-BRIEF`、3 个地点、3 个可见角色棋子、1 个高优先级 queued flood-pressure 事件、1 个 pending action request、天气/random log、3 条可被神谕修改的 terrain brush、dashboard/timeline/map-layers 导出，以及可直接打开的 frontend。
- 新增 5 个小型叙事/事件模板，放在 `be-a-god/assets/narrative-templates/`：
  - `interaction-result.template.json`
  - `queued-event-result.template.json`
  - `character-seed.template.json`
  - `faction-pressure.template.json`
  - `divine-intervention-result.template.json`
- 新增 `be-a-god/references/narrative-template-guide.md`，用于按场景选择一个最小模板。模板只约束结构和因果检查，不作为固定剧情库。
- `SKILL.md`、`player-quickstart.md`、`script-catalog.md`、`validation-scenarios.md`、`smoke_test.py`、`check_install_ready.py` 已同步更新。

## 设计边界

- demo 世界是可生成资产，不把大量存档直接塞进 skill 包。
- 叙事模板数量保持小，避免 token 膨胀和剧情重复。
- demo 与模板都进入安装前 Gate：`check_install_ready.py --run-smoke` 会检查 demo 生成、模板数量、模板路由和世界验证。
