# Be A God

一个以智能体 Skill 为核心的持久化叙事模拟游戏。项目使用 Markdown 保存正史，使用确定性 Python 脚本维护世界、地图数据、时间线、随机日志和分支存档；**不再包含本地网页前端**。

## 项目组成

- `be-a-god/`：核心 Skill、脚本、规则与模板
- `worlds/reedbend-demo/`：演示世界与正史存档
- `worlds/plain-sea-marsh/`：当前玩家世界存档
- `tests/`：事件回溯与世界地图语义回归测试
- `HANDOFF.md`：项目状态、验证结果和接手说明

## 快速验证

```bash
uv run --with pytest pytest tests/test_event_recall.py -q
python3 be-a-god/scripts/check_install_ready.py --skill-dir be-a-god --run-smoke --json
python3 be-a-god/scripts/validate_world.py --world worlds/plain-sea-marsh --json
```

## 安全说明

- 不提交真实 API Key；优先使用环境变量。
- `dashboard/`、`indexes/` 与 `system/file-manifest.json` 是可重建的派生数据；正史以 `story/`、`setup/`、`base/maps/` 为准。
- 不要静默覆盖玩家确认的事实、分支指针、随机日志或手动 Markdown 编辑。
