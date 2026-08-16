# Be A God

一个以智能体 Skill 为核心的持久化叙事模拟游戏，附带确定性后端脚本、世界文件和本地网页前端。

## 项目组成

- `be-a-god/`：核心 Skill、脚本、规则、前端模板和素材
- `worlds/reedbend-demo/`：当前演示世界与正史存档
- `tests/`：事件回溯、大地图和教程回归测试
- `HANDOFF.md`：当前项目状态、验证结果和接手说明

## 快速验证

```bash
PY='C:/Users/xuzix/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
node --check 'F:/be_a_god/be-a-god/assets/frontend-template/app.js'
uv run --with pytest pytest 'F:/be_a_god/tests' -q
"$PY" 'F:/be_a_god/be-a-god/scripts/validate_world.py' \
  --world 'F:/be_a_god/worlds/reedbend-demo' --json
```

## 启动本地前端

```bash
"$PY" 'F:/be_a_god/be-a-god/scripts/prepare_frontend.py' \
  --world 'F:/be_a_god/worlds/reedbend-demo' --confirmed --overwrite
"$PY" 'F:/be_a_god/be-a-god/scripts/serve_frontend.py' \
  --world 'F:/be_a_god/worlds/reedbend-demo' --port 8765
```

打开 `http://127.0.0.1:8765/`。

## 安全说明

- 不提交真实 API Key；优先使用环境变量。
- `worlds/*/frontend/` 是可重新生成的前端副本，已从 Git 忽略。
- 前端只展示过滤后的玩家可见剧情，不应直接读取 GM 秘密或原始正史 Markdown。
