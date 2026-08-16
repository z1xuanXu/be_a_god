const sampleDashboard = {
  world_id: "river-world",
  branch_id: "main",
  time: "year 1, day 13",
  weather: "小雨",
  focal_place: "河湾集市",
  current_scene: "十二天过去，河水上涨。",
  pieces: [
    { id: "CHAR-0001", kind: "character", label: "米拉", status: "plot-ready", x: 42, y: 61, source: "story/main/state/entities/CHAR-0001-mira.md" },
    { id: "CHAR-0002", kind: "character", label: "无名旅人", status: "ignored", x: 68, y: 34, source: "story/main/state/entities/CHAR-0002.md" }
  ],
  pins: [
    { id: "EVT-0001", kind: "event", label: "世界正式开始", x: 25, y: 74, source: "story/main/events/EVT-0001-world-confirmed.md" },
    { id: "EVT-0002", kind: "event", label: "米拉承认旧身份", x: 45, y: 58, source: "story/main/events/EVT-0002-米拉承认旧身份.md", target_id: "CHAR-0001" }
  ],
  pending_action_requests: [
    { request_id: "AR-0001", status: "requested", action: "intervene", target_id: "CHAR-0001", target_kind: "character", intent: "降下梦兆", source: "story/main/runtime/action-requests/AR-0001/request.json" }
  ],
  advance_profile: {
    source: "setup/advance-profile.json",
    default_preset: "hybrid",
    presets: [
      { id: "step", mode: "step", days: 1, wander: false, wander_limit: 0, stop_on_queue: true, summary: "Advance one short world step." },
      { id: "hybrid", mode: "hybrid", days: 7, wander: true, wander_limit: 3, stop_on_queue: true, summary: "Advance with mixed attention." },
      { id: "chronicle", mode: "chronicle", days: 30, wander: true, wander_limit: 5, stop_on_queue: true, summary: "Advance in chronicle view." },
      { id: "event-watch", mode: "event-priority", days: 90, wander: true, wander_limit: 6, stop_on_queue: true, until_next_queue: true, summary: "Advance to the next queued major event." }
    ]
  },
  narrative_profile: {
    source: "setup/narrative-profile.json",
    default_profile: "hybrid-historical",
    label: "混合模式，但偏真实历史感",
    default_scale: "mixed-closeup-chronicle",
    priority_order: ["causality", "world_continuity", "character_agency", "historical_texture", "dramatic_presentation"],
    required_output_layers: ["visible_narration", "gm_summary", "settlement_plan"]
  },
  world_rules: {
    source: "setup/world-rules.json",
    active: [
      { rule_id: "RULE-RIVER-OATH", scope: "global", text: "河誓不能被无征兆地违背。", tags: ["oath", "river"] }
    ]
  },
  random_log: {
    source: "story/main/random/random-log.jsonl",
    count: 2,
    latest: { index: 2, purpose: "weather", kind: "weather", mode: "override", value: "神降暴雨" },
    recent: [
      { index: 2, purpose: "weather", kind: "weather", mode: "override", value: "神降暴雨" },
      { index: 1, purpose: "wandering", kind: "wander", mode: "random", value: "LOC-002", entity_id: "CHAR-0001" }
    ]
  },
  attention: {
    followed_count: 0,
    ignored_count: 1,
    plot_ready_count: 1,
    followed: [],
    ignored: [{ id: "CHAR-0002", label: "无名旅人", status: "ignored", attention: "ignored", source: "story/main/state/entities/CHAR-0002.md" }],
    plot_ready: [{ id: "CHAR-0001", label: "米拉", status: "plot-ready", attention: "normal", source: "story/main/state/entities/CHAR-0001-mira.md" }]
  },
  story: {
    current: { id: "CURRENT-SCENE", title: "河湾集市", time: "year 1, day 13", state: "current", narrative: "十二天过去，河水上涨。", source: "story/main/SAVE.md" },
    entries: [
      { id: "EVT-0001", title: "世界正式开始", time: "year 1, day 1", state: "confirmed", narrative: "玩家确认了世界草案，正式世界开始存在。", source: "story/main/events/EVT-0001-world-confirmed.md" }
    ]
  }
};

const sampleTimeline = {
  nodes: [
    { id: "CHR-0001", event_id: "EVT-0001", time: "year 1, day 1", label: "世界正式开始", state: "confirmed", source: "story/main/events/EVT-0001-world-confirmed.md" },
    { id: "CHR-0002", event_id: "EVT-0002", time: "year 1, day 13", label: "米拉透露旧身份", state: "confirmed", source: "story/main/events/EVT-0002-米拉承认旧身份.md" },
    { id: "LOCK-RULE-RIVER-OATH", event_id: "RULE-RIVER-OATH", time: "year 1, day 13", label: "锁定规则：河誓", state: "locked", source: "setup/world-rules.json" },
    { id: "Q-QUEUE-0001", event_id: "QUEUE-0001", time: "year 1, day 18", label: "预定：洪水警报", state: "queued", source: "story/main/queues/events.jsonl" },
    { id: "IGNORED-CHAR-0002", event_id: "CHAR-0002", time: "year 1, day 13", label: "被忽略动态：无名旅人", state: "ignored", source: "story/main/events/EVT-0002-米拉承认旧身份.md" },
    { id: "BR-0001", event_id: "EVT-0001", time: "year 1, day 13", label: "可能的分支：阻止放逐", state: "branch", source: "story/main/branches/save-mira/SAVE.md" }
  ]
};

const sampleMapLayers = {
  schema: "be-a-god.map-layers.v1",
  levels: ["world", "region", "scene"],
  nodes: [
    { id: "LOC-001", name: "河湾集市", level: "scene", x: 42, y: 61, source: "story/main/state/locations/LOC-001-river-market.md" },
    { id: "REG-001", name: "下游平原", level: "region", x: 38, y: 48 }
  ],
  places: [],
  brushes: [
    { id: "BRUSH-RIVER-001", kind: "river", label: "主河道", level: "region", points: [[12, 24], [28, 38], [42, 61], [74, 74]], width: 7, density: 18, jitter: 2, color: "#315b76", source: "base/maps/terrain-brushes.json", mutable_by_divine_action: true },
    { id: "BRUSH-FOREST-001", kind: "forest", label: "林地", level: "region", points: [[62, 26], [67, 31], [72, 28], [69, 36]], width: 5, density: 14, jitter: 4, color: "#557542", source: "base/maps/terrain-brushes.json", mutable_by_divine_action: true }
  ]
};

let dashboard = sampleDashboard;
let timeline = sampleTimeline;
let mapLayers = sampleMapLayers;
let selected = null;
let brushEditor = { enabled: false, points: [] };
let mapView = { scale: 0.7, x: 0, y: 0, isPanning: false, moved: false, startX: 0, startY: 0, originX: 0, originY: 0 };
let backendConnected = false;
let actionInFlight = false;
let draggedActionRequestId = null;
let pendingFrontendAction = null;
let activeStoryId = "CURRENT-SCENE";
let tutorialStepIndex = 1;

const MAP_ZOOM = { min: 0.6, max: 12, factor: 1.25, taskCloseup: 4 };
const HEX_SIZE_METERS = 5000;
const MAP_LEVELS = {
  world: { label: "世界", max: 0.82 },
  region: { label: "地区", min: 0.82, max: 1.46 },
  scene: { label: "近景", min: 1.46 }
};
const MAP_ASSETS = {
  flag: "./img/flag-marker.png",
  uiFrame: "./img/ui-frame.png",
  forest: "./img/forest-stamp.png",
  forestCluster: "./img/forest-cluster-stamp.png",
  hills: "./img/hills-stamp.png",
  rockyHills: "./img/rocky-hills-stamp.png",
  mountain: "./img/mountain-ridge-stamp.png",
  creek: "./img/creek-stamp.png",
  castle: "./img/castle-stamp.png",
  village: "./img/village-stamp.png",
  bridge: "./img/bridge-stamp.png",
  road: "./img/road-stamp.png",
  farm: "./img/farm-stamp.png",
  ruins: "./img/ruins-stamp.png",
  marsh: "./img/marsh-stamp.png",
  lake: "./img/lake-stamp.png",
  shoreRocks: "./img/shore-rocks-stamp.png",
  parchment: "./img/parchment-overlay.png",
  corner: "./img/corner-ornament.png",
  hexGrassland: "./img/hex-grassland.png",
  hexForest: "./img/hex-forest.png",
  hexHills: "./img/hex-hills.png",
  hexMountain: "./img/hex-mountain.png",
  hexRiver: "./img/hex-river.png",
  hexLake: "./img/hex-lake.png",
  hexMarsh: "./img/hex-marsh.png",
  hexDesert: "./img/hex-desert.png",
  hexVillage: "./img/hex-village.png",
  hexCastle: "./img/hex-castle.png",
  hexFarm: "./img/hex-farm.png",
  hexRuins: "./img/hex-ruins.png",
  hexCoast: "./img/hex-coast.png",
  hexTundra: "./img/hex-tundra.png",
  hexSnow: "./img/hex-snow.png",
  hexVolcanic: "./img/hex-volcanic.png",
  hexBadlands: "./img/hex-badlands.png",
  hexMeadow: "./img/hex-meadow.png",
  pieceFerryman: "./img/pieces/piece-character-ferryman.png",
  pieceClerk: "./img/pieces/piece-character-clerk.png",
  piecePriest: "./img/pieces/piece-character-priest.png",
  pieceSoldier: "./img/pieces/piece-character-soldier.png",
  pieceCart: "./img/pieces/piece-vehicle-cart.png",
  pieceBoat: "./img/pieces/piece-vehicle-boat.png",
  pieceMarket: "./img/pieces/piece-building-market.png",
  pieceGranary: "./img/pieces/piece-building-granary.png",
  pieceShrine: "./img/pieces/piece-building-shrine.png",
  pieceGrain: "./img/pieces/piece-resource-grain.png",
  pieceTimber: "./img/pieces/piece-resource-timber.png",
  pieceTools: "./img/pieces/piece-resource-tools.png",
  pieceRelic: "./img/pieces/piece-object-relic.png",
  pieceEvent: "./img/pieces/piece-event-banner.png",
  pieceGeneric: "./img/pieces/piece-generic-unit.png",
  pieceCityVillage: "./img/pieces/piece-city-village.png",
  pieceCityTown: "./img/pieces/piece-city-town.png",
  pieceCityCity: "./img/pieces/piece-city-city.png",
  pieceCityFortress: "./img/pieces/piece-city-fortress.png"
};

const MAP_DECOR_STAMPS = [
  { asset: "mountain", className: "decor-mountain", x: 13, y: 18, width: 21, opacity: 0.55, level: "world" },
  { asset: "castle", className: "decor-castle", x: 22, y: 36, width: 14, opacity: 0.58, level: "world" },
  { asset: "village", className: "decor-village", x: 58, y: 68, width: 13, opacity: 0.55, level: "region" },
  { asset: "bridge", className: "decor-bridge", x: 42, y: 60, width: 12, opacity: 0.58, level: "region" },
  { asset: "road", className: "decor-road", x: 34, y: 50, width: 24, rotation: -15, opacity: 0.42, level: "region" },
  { asset: "farm", className: "decor-farm", x: 70, y: 73, width: 15, opacity: 0.54, level: "scene" },
  { asset: "lake", className: "decor-lake", x: 78, y: 30, width: 16, opacity: 0.45, level: "world" },
  { asset: "marsh", className: "decor-marsh", x: 18, y: 76, width: 16, opacity: 0.42, level: "region" },
  { asset: "ruins", className: "decor-ruins", x: 84, y: 57, width: 12, opacity: 0.5, level: "scene" },
  { asset: "shoreRocks", className: "decor-shore", x: 87, y: 20, width: 16, opacity: 0.42, level: "world" }
];

const HEX_LEVELS = {
  world: { cols: 23, rows: 16, label: "世界蜂窝" },
  region: { cols: 31, rows: 21, label: "地区蜂窝" },
  scene: { cols: 47, rows: 32, label: "近景蜂窝" }
};

const DETAIL_TERM_LABELS = {
  "map-node": "地图节点",
  "hex": "地形格",
  "piece": "棋子/单位",
  "pin": "事件图钉",
  "timeline": "时间线节点",
  "character": "角色",
  "event": "事件",
  "location": "地点",
  "system": "系统",
  "world": "世界",
  "region": "地区",
  "scene": "近景",
  "pending-action": "待提交动作",
  "brush-editor": "画笔编辑器",
  "confirmed": "已确认",
  "requested": "已请求",
  "accepted": "已接受",
  "executed": "已执行",
  "cancelled": "已取消",
  "blocked": "已阻塞",
  "waiting": "等待中",
  "queued": "已排队",
  "due": "已到期",
  "locked": "已锁定",
  "ignored": "已忽略",
  "followed": "已关注",
  "normal": "普通",
  "plot-ready": "剧情就绪",
  "danger": "危险",
  "paused": "已暂停",
  "moving": "移动中",
  "wandering": "漫游中",
  "dead": "死亡",
  "hidden": "隐藏",
  "ordinary": "普通",
  "unknown": "未知",
  "preview-action": "动作预览",
  "pending-submit": "等待提交",
  "copied": "已复制",
  "manual-copy": "需要手动复制",
  "terrain-brush": "地形画笔",
  "grassland": "草地",
  "plain": "平原",
  "forest": "森林",
  "hills": "丘陵",
  "mountain": "山地",
  "river": "河流",
  "tributary": "支流",
  "lake": "湖泊",
  "marsh": "沼泽",
  "desert": "沙漠",
  "coast": "海岸",
  "tundra": "苔原",
  "snow": "雪地",
  "volcanic": "火山",
  "badlands": "荒原",
  "meadow": "草甸"
};

const $ = (selector) => document.querySelector(selector);

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function bilingualTerm(value, fallback = "--") {
  const raw = String(value ?? fallback);
  const key = raw.toLowerCase();
  const label = DETAIL_TERM_LABELS[key];
  return label ? `${label}（${raw}）` : raw;
}

function classToken(value, fallback = "unknown") {
  const token = String(value || fallback).toLowerCase().replace(/[^a-z0-9_-]+/g, "-").replace(/^-+|-+$/g, "");
  return token || fallback;
}

function commandJsonArg(value) {
  return JSON.stringify(value)
    .replaceAll("\\", "\\\\")
    .replaceAll('"', '\\"');
}

function setText(id, value) {
  const node = document.getElementById(id);
  if (node) node.textContent = value;
}

function setLoadStatus(message, isError = false) {
  const node = document.getElementById("load-status");
  if (!node) return;
  node.textContent = message;
  node.dataset.state = isError ? "error" : "ok";
}

async function backendJson(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    }
  });
  const data = await response.json();
  if (!response.ok || data.ok === false) {
    throw new Error(data.error || `HTTP ${response.status}`);
  }
  return data;
}

async function detectBackend() {
  try {
    await backendJson("/api/health");
    backendConnected = true;
    setLoadStatus("已连接本地后端，可直接创建行动请求");
  } catch {
    backendConnected = false;
  }
  return backendConnected;
}

function applyBackendState(state) {
  if (!state) return;
  dashboard = validateDashboardData(state.dashboard);
  timeline = validateTimelineData(state.timeline);
  mapLayers = validateMapLayersData(state.map_layers);
  selected = null;
  renderAll();
}

async function loadBackendState() {
  if (!backendConnected) return false;
  try {
    const data = await backendJson("/api/state?refresh=1");
    applyBackendState(data);
    setLoadStatus("已从本地后端刷新世界数据");
    return true;
  } catch (error) {
    setLoadStatus(`本地后端刷新失败：${error.message}`, true);
    return false;
  }
}

async function submitBackendActionRequest(request) {
  if (!backendConnected) return null;
  try {
    const data = await backendJson("/api/action-request", {
      method: "POST",
      body: JSON.stringify(request)
    });
    if (data.state) applyBackendState(data.state);
    setLoadStatus(`已创建行动请求：${data.request_id || "--"}`);
    return data;
  } catch (error) {
    setLoadStatus(`行动请求创建失败：${error.message}`, true);
    return null;
  }
}

async function submitBackendAdvanceWorld(request) {
  if (!backendConnected) {
    setLoadStatus("未连接本地后端，无法直接推进世界时间", true);
    return null;
  }
  try {
    const data = await backendJson("/api/advance-world", {
      method: "POST",
      body: JSON.stringify(request)
    });
    if (data.state) applyBackendState(data.state);
    setLoadStatus(`世界时间已推进：${data.stdout || "完成"}`);
    return data;
  } catch (error) {
    setLoadStatus(`推进世界时间失败：${error.message}`, true);
    return null;
  }
}

async function submitBackendMapBrush(request) {
  if (!backendConnected) {
    setLoadStatus("未连接本地后端，无法应用地图画笔", true);
    return null;
  }
  try {
    const data = await backendJson("/api/map-brush/apply", { method: "POST", body: JSON.stringify(request) });
    if (data.state) applyBackendState(data.state);
    setLoadStatus(`地图画笔已生效：${data.brush_id || "--"}`);
    return data;
  } catch (error) {
    setLoadStatus(`地图画笔执行失败：${error.message}`, true);
    return null;
  }
}

async function submitBackendCancelActionRequest(requestId) {
  if (!backendConnected) {
    setLoadStatus("未连接本地后端，无法取消待处理动作", true);
    return null;
  }
  try {
    const data = await backendJson("/api/action-request/cancel", {
      method: "POST",
      body: JSON.stringify({ request_id: requestId, reason: "cancelled from frontend" })
    });
    if (data.state) applyBackendState(data.state);
    setLoadStatus(`已取消待处理动作：${requestId}`);
    return data;
  } catch (error) {
    setLoadStatus(`取消待处理动作失败：${error.message}`, true);
    return null;
  }
}

async function submitBackendActionRequestOrder(requestIds) {
  if (!backendConnected) {
    setLoadStatus("未连接本地后端，无法保存待处理动作排序", true);
    return null;
  }
  try {
    const data = await backendJson("/api/action-requests/reorder", {
      method: "POST",
      body: JSON.stringify({ request_ids: requestIds })
    });
    if (data.state) applyBackendState(data.state);
    setLoadStatus("已保存待处理动作优先级");
    return data;
  } catch (error) {
    setLoadStatus(`保存待处理动作排序失败：${error.message}`, true);
    return null;
  }
}

function renderBackendResult(result) {
  if (!result) return;
  $("#detail").innerHTML += `<p>本地后端结果：</p><pre>${escapeHtml(JSON.stringify(result, null, 2))}</pre>`;
}

function updatePendingActionStatus() {
  const status = $("#pending-action-status");
  const button = $("#commit-action");
  if (!status || !button) return;
  if (!pendingFrontendAction) {
    status.textContent = "还没有待提交的操作。先点击神权按钮或在画笔编辑器生成地形神谕。";
    button.disabled = true;
    return;
  }
  status.textContent = `待提交：${pendingFrontendAction.label || pendingFrontendAction.kind || "未命名操作"}。点击“确认提交 / 开始运行”后才会写入待处理或推进时间。`;
  button.disabled = false;
}

function clearPendingFrontendAction() {
  pendingFrontendAction = null;
  updatePendingActionStatus();
  setLoadStatus("已撤销当前操作草稿");
}

function setPendingFrontendAction(actionDraft) {
  pendingFrontendAction = actionDraft;
  showDetail(actionDraft.detailKind || "pending-action", actionDraft.detailItem || {
    id: actionDraft.payload?.target_id || "WORLD",
    label: actionDraft.label || "待提交操作",
    state: "pending-submit",
    source: "frontend pending action"
  });
  $("#detail").innerHTML += `
    <p>这只是操作草稿，还没有开始运行。确认后才会提交：</p>
    <pre>${escapeHtml(JSON.stringify(actionDraft.payload || actionDraft.backendRequest || {}, null, 2))}</pre>
  `;
  updatePendingActionStatus();
  setLoadStatus(`已生成操作草稿：${actionDraft.label || "待提交操作"}`);
}

async function submitPendingFrontendAction() {
  if (!pendingFrontendAction || actionInFlight) return;
  actionInFlight = true;
  const draft = pendingFrontendAction;
  try {
    setLoadStatus(`正在提交：${draft.label || "操作"}`);
    if (draft.submitType === "advance-world") {
      renderBackendResult(await submitBackendAdvanceWorld(draft.backendRequest));
    } else if (draft.submitType === "map-brush") {
      renderBackendResult(await submitBackendMapBrush(draft.backendRequest));
    } else {
      renderBackendResult(await submitBackendActionRequest(draft.backendRequest));
    }
    pendingFrontendAction = null;
    updatePendingActionStatus();
  } catch (error) {
    setLoadStatus(`提交失败：${error.message}`, true);
  } finally {
    actionInFlight = false;
  }
}

function positionOf(item, fallbackIndex = 0) {
  const parsedX = Number(item.x);
  const parsedY = Number(item.y);
  const x = Number.isFinite(parsedX) ? parsedX : 18 + ((fallbackIndex * 19) % 72);
  const y = Number.isFinite(parsedY) ? parsedY : 18 + ((fallbackIndex * 29) % 68);
  return { x, y };
}

function normalizeBrushPoint(point) {
  if (!Array.isArray(point) || point.length < 2) return null;
  const x = Number(point[0]);
  const y = Number(point[1]);
  if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
  return { x: Math.max(0, Math.min(100, x)), y: Math.max(0, Math.min(100, y)) };
}

function brushPoints(brush) {
  return (brush.points || []).map(normalizeBrushPoint).filter(Boolean);
}

function svgPathFromPoints(points) {
  if (!points.length) return "";
  if (points.length === 1) return `M ${points[0].x} ${points[0].y}`;
  let d = `M ${points[0].x} ${points[0].y}`;
  for (let index = 1; index < points.length; index += 1) {
    const previous = points[index - 1];
    const current = points[index];
    const midX = (previous.x + current.x) / 2;
    const midY = (previous.y + current.y) / 2;
    d += ` Q ${previous.x} ${previous.y} ${midX} ${midY}`;
  }
  const last = points[points.length - 1];
  d += ` T ${last.x} ${last.y}`;
  return d;
}

function deterministicJitter(seed, amount) {
  const x = Math.sin(seed * 12.9898) * 43758.5453;
  return (x - Math.floor(x) - 0.5) * amount * 2;
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function opacityForLevel(level, scale = mapView.scale) {
  return (level || "region") === mapLevelForScale(scale) ? 1 : 0;
}

function mapLevelForScale(scale = mapView.scale) {
  if (scale < MAP_LEVELS.world.max) return "world";
  if (scale < MAP_LEVELS.region.max) return "region";
  return "scene";
}

function currentMapMode(scale = mapView.scale) {
  const level = mapLevelForScale(scale);
  const label = scale >= MAP_ZOOM.taskCloseup ? "任务近景" : MAP_LEVELS[level].label;
  return { level, label, opacity: 1 };
}

function visualLevelForPiece(piece) {
  return piece.kind === "character" ? "scene" : (piece.level || "scene");
}

function updateMapZoomMode() {
  const node = $("#map-zoom-mode");
  if (!node) return;
  const mode = currentMapMode();
  node.textContent = `自动层级：${mode.label}`;
}

function activeBrushes() {
  return mapLayers.brushes || [];
}

function updateMapZoomLabel() {
  const label = $("#map-zoom-label");
  if (label) label.textContent = `${Math.round(mapView.scale * 100)}%`;
  updateMapZoomMode();
}

function applyMapViewTransform() {
  const content = $("#map-content");
  if (!content) {
    updateMapZoomLabel();
    return;
  }
  content.style.transform = `translate(${mapView.x}px, ${mapView.y}px) scale(${mapView.scale})`;
  updateMapScaleBar();
  updateMapZoomLabel();
}

function updateMapScaleBar() {
  const bar = $("#map .scale-bar");
  const map = $("#map");
  if (!bar || !map) return;
  const metrics = hexTileMetrics(mapLevelForScale());
  const width = map.getBoundingClientRect().width * metrics.drawWidth / 100 * mapView.scale;
  bar.style.setProperty("--scale-width", `${width}px`);
}

function centerMapAnchor() {
  const rect = $("#map")?.getBoundingClientRect();
  if (!rect) return null;
  return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
}

function setMapZoom(nextScale, anchor = centerMapAnchor()) {
  const rect = $("#map")?.getBoundingClientRect();
  if (!rect) return;
  const previousScale = mapView.scale;
  const previousLevel = mapLevelForScale(previousScale);
  const scale = clamp(nextScale, MAP_ZOOM.min, MAP_ZOOM.max);
  if (scale === previousScale) return;
  const anchorX = (anchor?.x ?? (rect.left + rect.width / 2)) - rect.left;
  const anchorY = (anchor?.y ?? (rect.top + rect.height / 2)) - rect.top;
  const contentX = (anchorX - mapView.x) / previousScale;
  const contentY = (anchorY - mapView.y) / previousScale;
  mapView.scale = scale;
  mapView.x = anchorX - contentX * scale;
  mapView.y = anchorY - contentY * scale;
  if (mapLevelForScale(scale) !== previousLevel) renderMap();
  else applyMapViewTransform();
}

function resetMapView() {
  mapView = { ...mapView, scale: 0.7, x: 0, y: 0, isPanning: false, moved: false };
  $("#map")?.classList.remove("is-panning");
  applyMapViewTransform();
}

function handleMapWheel(event) {
  event.preventDefault();
  const direction = event.deltaY < 0 ? 1 : -1;
  const nextScale = direction > 0 ? mapView.scale * MAP_ZOOM.factor : mapView.scale / MAP_ZOOM.factor;
  setMapZoom(nextScale, { x: event.clientX, y: event.clientY });
}

function beginMapPan(event) {
  if (brushEditor.enabled || event.button !== 0 || event.target?.closest?.("input, select, textarea, label")) return;
  mapView.isPanning = true;
  mapView.moved = false;
  mapView.startX = event.clientX;
  mapView.startY = event.clientY;
  mapView.originX = mapView.x;
  mapView.originY = mapView.y;
  $("#map")?.classList.add("is-panning");
  event.currentTarget.setPointerCapture?.(event.pointerId);
}

function moveMapPan(event) {
  if (!mapView.isPanning) return;
  event.preventDefault();
  const dx = event.clientX - mapView.startX;
  const dy = event.clientY - mapView.startY;
  if (Math.abs(dx) + Math.abs(dy) > 4) mapView.moved = true;
  mapView.x = mapView.originX + dx;
  mapView.y = mapView.originY + dy;
  applyMapViewTransform();
}

function endMapPan(event) {
  if (!mapView.isPanning) return;
  mapView.isPanning = false;
  $("#map")?.classList.remove("is-panning");
  event.currentTarget.releasePointerCapture?.(event.pointerId);
}

function preventMapNativeDrag(event) {
  event.preventDefault();
}

function suppressMapClickAfterPan(event) {
  if (!mapView.moved) return;
  event.preventDefault();
  event.stopPropagation();
  event.stopImmediatePropagation?.();
}

function interpolateBrush(points, step, total) {
  if (!points.length) return { x: 50, y: 50 };
  if (points.length === 1 || total <= 1) return points[0];
  const t = step / (total - 1);
  const scaled = t * (points.length - 1);
  const index = Math.min(points.length - 2, Math.floor(scaled));
  const local = scaled - index;
  const a = points[index];
  const b = points[index + 1];
  return {
    x: a.x + (b.x - a.x) * local,
    y: a.y + (b.y - a.y) * local
  };
}

function brushTangentAngle(points) {
  if (points.length < 2) return 0;
  const first = points[0];
  const last = points[points.length - 1];
  return Math.atan2(last.y - first.y, last.x - first.x) * 180 / Math.PI;
}

function renderImageStamp(parent, src, className, x, y, width, rotation = 0, opacity = 0.82) {
  const image = document.createElement("img");
  image.className = className;
  image.src = src;
  image.alt = "";
  image.loading = "lazy";
  image.style.left = `${clamp(x, -8, 108)}%`;
  image.style.top = `${clamp(y, -8, 108)}%`;
  image.style.width = `${width}%`;
  image.style.opacity = String(opacity);
  image.style.transform = `translate(-50%, -50%) rotate(${rotation}deg)`;
  parent.appendChild(image);
}

function applyZoomFade(node, level, baseOpacity = 1, minOpacity = 0) {
  const fadeLevel = level || "region";
  const isActive = opacityForLevel(fadeLevel) === 1;
  const opacity = isActive ? baseOpacity : 0;
  node.dataset.zoomLevel = fadeLevel;
  node.style.setProperty("--base-opacity", String(baseOpacity));
  node.style.setProperty("--min-opacity", String(minOpacity));
  node.style.opacity = String(opacity);
  node.style.pointerEvents = isActive && opacity >= 0.18 ? "auto" : "none";
  node.setAttribute("aria-hidden", isActive ? "false" : "true");
}

function applyZoomFadeToRenderedMap() {
  document.querySelectorAll("#map [data-zoom-level]").forEach((node) => {
    const level = node.dataset.zoomLevel || "region";
    const baseOpacity = Number(node.style.getPropertyValue("--base-opacity") || 1);
    const minOpacity = Number(node.style.getPropertyValue("--min-opacity") || 0);
    applyZoomFade(node, level, baseOpacity, minOpacity);
  });
}

function nodeAssetName(item) {
  const raw = `${item.kind || ""} ${item.type || ""} ${item.level || ""} ${item.id || ""} ${item.name || ""}`.toLowerCase();
  if (raw.includes("granary") || raw.includes("粮仓")) return "pieceGranary";
  if (raw.includes("shrine") || raw.includes("temple") || raw.includes("神龛")) return "pieceShrine";
  if (raw.includes("fortress") || raw.includes("castle") || raw.includes("keep") || raw.includes("要塞")) return "pieceCityFortress";
  if (raw.includes("city") || raw.includes("capital") || raw.includes("城市")) return "pieceCityCity";
  if (raw.includes("town") || raw.includes("城镇")) return "pieceCityTown";
  if (raw.includes("village") || raw.includes("村庄")) return "pieceCityVillage";
  if (raw.includes("market") || raw.includes("集市")) return "pieceCityTown";
  return "pieceMarket";
}

function pieceAssetName(piece) {
  const raw = `${piece.kind || ""} ${piece.type || ""} ${piece.status || ""} ${piece.id || ""} ${piece.label || ""}`.toLowerCase();
  if (raw.includes("mira") || raw.includes("ferry rope") || raw.includes("渡船人")) return "pieceFerryman";
  if (raw.includes("tavin") || raw.includes("clerk") || raw.includes("counter") || raw.includes("书记")) return "pieceClerk";
  if (raw.includes("sela") || raw.includes("priest") || raw.includes("祭司")) return "piecePriest";
  if (raw.includes("soldier") || raw.includes("guard") || raw.includes("warrior") || raw.includes("士兵")) return "pieceSoldier";
  if (raw.includes("boat") || raw.includes("ship") || raw.includes("ferry") || raw.includes("船")) return "pieceBoat";
  if (raw.includes("cart") || raw.includes("wagon") || raw.includes("carriage") || raw.includes("车")) return "pieceCart";
  if (raw.includes("fortress") || raw.includes("castle") || raw.includes("keep") || raw.includes("要塞")) return "pieceCityFortress";
  if (raw.includes("city") || raw.includes("capital") || raw.includes("城市")) return "pieceCityCity";
  if (raw.includes("town") || raw.includes("城镇")) return "pieceCityTown";
  if (raw.includes("village") || raw.includes("村庄")) return "pieceCityVillage";
  if (raw.includes("granary") || raw.includes("粮仓")) return "pieceGranary";
  if (raw.includes("shrine") || raw.includes("temple") || raw.includes("神龛")) return "pieceShrine";
  if (raw.includes("market") || raw.includes("building") || raw.includes("建筑")) return "pieceMarket";
  if (raw.includes("grain") || raw.includes("food") || raw.includes("粮")) return "pieceGrain";
  if (raw.includes("timber") || raw.includes("wood") || raw.includes("木材")) return "pieceTimber";
  if (raw.includes("tool") || raw.includes("supply") || raw.includes("物资")) return "pieceTools";
  if (raw.includes("tablet") || raw.includes("relic") || raw.includes("object") || raw.includes("item") || raw.includes("遗物")) return "pieceRelic";
  if (raw.includes("event") || raw.includes("warning")) return "pieceEvent";
  return "pieceGeneric";
}

function hexSpec(level) {
  return HEX_LEVELS[level || "region"] || HEX_LEVELS.region;
}

function hexTileMetrics(level) {
  const spec = hexSpec(level);
  const rect = $("#map")?.getBoundingClientRect();
  const mapHeightToWidth = rect && rect.width ? rect.height / rect.width : 0.68;
  const hexWidthToHeight = Math.sqrt(3) / 2;
  const gridWidthFactor = spec.cols + (spec.rows > 1 ? 0.5 : 0);
  const gridHeightFactor = 1 + (spec.rows - 1) * 0.75;
  const targetCoverage = 104;
  const overdraw = 1.018;
  const widthByColumns = targetCoverage / gridWidthFactor;
  const widthByRows = (targetCoverage * hexWidthToHeight * mapHeightToWidth) / gridHeightFactor;
  const width = Math.min(widthByColumns, widthByRows);
  const height = width / (hexWidthToHeight * mapHeightToWidth);
  const gridWidth = width * gridWidthFactor;
  const gridHeight = height * gridHeightFactor;
  return {
    width,
    height,
    drawWidth: width * overdraw,
    drawHeight: height * overdraw,
    x0: (100 - gridWidth) / 2 + width / 2,
    y0: (100 - gridHeight) / 2 + height / 2
  };
}

function makeHexCells(level) {
  const spec = hexSpec(level);
  const metrics = hexTileMetrics(level);
  const cells = [];
  for (let row = 0; row < spec.rows; row += 1) {
    for (let col = 0; col < spec.cols; col += 1) {
      const x = metrics.x0 + (col + (row % 2 ? 0.5 : 0)) * metrics.width;
      const y = metrics.y0 + row * metrics.height * 0.75;
      if (x < -5 || x > 105 || y < -5 || y > 105) continue;
      cells.push({
        level,
        row,
        col,
        x,
        y,
        width: metrics.width,
        height: metrics.height,
        drawWidth: metrics.drawWidth,
        drawHeight: metrics.drawHeight
      });
    }
  }
  return cells;
}

function distanceToBrush(cell, brush) {
  const points = brushPoints(brush);
  if (!points.length) return Infinity;
  return Math.min(...points.map((point) => Math.hypot(cell.x - point.x, cell.y - point.y)));
}

function deterministicNoise(x, y, salt = 0) {
  const value = Math.sin((x + 17.17) * 12.9898 + (y + 31.31) * 78.233 + salt * 37.719) * 43758.5453;
  return value - Math.floor(value);
}

function backgroundTerrainForPoint(point) {
  const zoneX = Math.floor(point.x / 10);
  const zoneY = Math.floor(point.y / 10);
  const seed = deterministicNoise(zoneX, zoneY, 7);
  if (point.x < 8 || point.x > 92) return seed > 0.5 ? "coast" : "lake";
  if (point.y < 24) return seed > 0.45 ? "snow" : "tundra";
  if (point.x > 78 && point.y > 22 && point.y < 48 && seed > 0.32) return seed > 0.72 ? "badlands" : "desert";
  if (point.x > 74 && point.y < 36 && seed > 0.7) return "lake";
  if (point.y > 72 && seed > 0.72) return "marsh";
  if (seed > 0.965) return "volcanic";
  if (seed > 0.93) return "mountain";
  if (seed > 0.82) return "hills";
  if (seed > 0.66) return "forest";
  if (seed > 0.42) return "meadow";
  return "grassland";
}

function brushTerrainRadius(cell, brush) {
  const brushWidth = Number(brush.width || 5);
  const cellReach = Math.max(Number(cell.width || 0), Number(cell.height || 0)) * 0.34;
  return Math.max(4, Math.min(13, brushWidth + cellReach));
}

function rawTerrainForHexCell(cell) {
  const candidates = activeBrushes()
    .map((brush) => ({ brush, distance: distanceToBrush(cell, brush), radius: brushTerrainRadius(cell, brush) }))
    .sort((a, b) => a.distance - b.distance);
  const nearest = candidates[0];
  if (nearest && nearest.distance < nearest.radius) {
    const brushKind = classToken(nearest.brush.kind, "grassland");
    return brushKind === "plain" || brushKind === "custom" ? "grassland" : brushKind;
  }
  return backgroundTerrainForPoint(cell);
}

function terrainAnchorForHexCell(cell) {
  if (!cell || cell.level === "region") return cell;
  if (cell.level === "scene") return nearestHexCenter(cell, "region");
  if (cell.level === "world") return cell;
  return cell;
}

function terrainForHexCell(cell) {
  const anchor = terrainAnchorForHexCell(cell);
  return rawTerrainForHexCell(anchor);
}

function terrainAssetForKind(kind) {
  const assets = {
    grassland: "hexGrassland",
    plain: "hexGrassland",
    forest: "hexForest",
    hills: "hexHills",
    mountain: "hexMountain",
    river: "hexRiver",
    tributary: "hexRiver",
    lake: "hexLake",
    marsh: "hexMarsh",
    desert: "hexDesert",
    village: "hexVillage",
    castle: "hexCastle",
    farm: "hexFarm",
    ruins: "hexRuins",
    coast: "hexCoast",
    tundra: "hexTundra",
    snow: "hexSnow",
    volcanic: "hexVolcanic",
    badlands: "hexBadlands",
    meadow: "hexMeadow"
  };
  return MAP_ASSETS[assets[kind] || "hexGrassland"];
}

function nearestHexCenter(point, level = mapLevelForScale()) {
  const cells = makeHexCells(level);
  let best = cells[0] || { x: point.x, y: point.y };
  let bestDistance = Infinity;
  for (const cell of cells) {
    const distance = Math.hypot(point.x - cell.x, point.y - cell.y);
    if (distance < bestDistance) {
      bestDistance = distance;
      best = cell;
    }
  }
  return { level: best.level || level, x: best.x, y: best.y, row: best.row, col: best.col, width: best.width, height: best.height, drawWidth: best.drawWidth, drawHeight: best.drawHeight };
}

// hex-terrain-img remains the semantic terrain layer marker.
function renderHexGrid(parent, level) {
    const layer = document.createElement("div");
    layer.className = `hex-grid hex-grid-${level}`;
    layer.dataset.zoomLevel = level;
    layer.style.setProperty("--base-opacity", "1");
    layer.style.setProperty("--min-opacity", "0");
    applyZoomFade(layer, level, 1, 0);
    for (const cell of makeHexCells(level)) {
      const tile = document.createElement("button");
      const terrain = terrainForHexCell(cell);
      tile.type = "button";
      tile.draggable = false;
      tile.className = `hex-tile terrain-${terrain}`;
      tile.style.left = `${cell.x}%`;
      tile.style.top = `${cell.y}%`;
      tile.style.width = `${cell.drawWidth || cell.width}%`;
      tile.style.height = `${cell.drawHeight || cell.height}%`;
      tile.style.setProperty("--terrain-image", `url("${terrainAssetForKind(terrain)}")`);
      tile.style.backgroundImage = `url("${terrainAssetForKind(terrain)}")`;
      tile.style.backgroundSize = "100% 100%";
      tile.style.backgroundRepeat = "no-repeat";
      tile.style.zIndex = String(cell.row * 2 + (cell.col % 2));
      tile.title = `${HEX_LEVELS[level].label} ${cell.col},${cell.row}`;
      tile.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        if (mapView.moved) return;
        showDetail("hex", {
          id: `HEX-${level}-${cell.col}-${cell.row}`,
          label: `${HEX_LEVELS[level].label} ${cell.col},${cell.row}`,
          kind: "location",
          status: terrain,
          x: Number(cell.x.toFixed(1)),
          y: Number(cell.y.toFixed(1)),
          source: "frontend hex projection"
        });
      });
      layer.appendChild(tile);
    }
    parent.appendChild(layer);
}

function showMapObjectDetail(kind, item, snapped) {
  const detailItem = {
    ...item,
    label: item.label || item.name || item.id,
    status: item.status || item.state || item.level || kind,
    source: item.source,
    x: item.x,
    y: item.y,
    hex: snapped ? `${snapped.col},${snapped.row}` : undefined
  };
  showDetail(kind, detailItem);
}

function renderHexUnit(parent, item, kind, index, options = {}) {
  const pos = positionOf(item, index);
  const level = mapLevelForScale();
  const snapped = nearestHexCenter(pos, mapLevelForScale());
  const pieceWidth = snapped.drawWidth * 0.72;
  const pieceHeight = snapped.drawHeight * 0.72;
  const node = document.createElement("button");
  const cityAsset = String(options.asset || "").includes("piece-city-");
  node.draggable = false;
  node.className = `${options.className || "hex-unit"}${cityAsset ? " city-unit" : ""} ${classToken(item.status || item.state || level, "ordinary")}`;
  node.style.left = `${snapped.x}%`;
  node.style.top = `${snapped.y}%`;
  node.style.setProperty("--piece-width", `${pieceWidth}%`);
  node.style.setProperty("--piece-height", `${pieceHeight}%`);
  node.style.setProperty("--unit-icon", `url("${options.asset || MAP_ASSETS.flag}")`);
  node.title = `${item.label || item.name || item.id}｜坐标 ${pos.x.toFixed?.(1) || pos.x},${pos.y.toFixed?.(1) || pos.y}｜六边形 ${snapped.col},${snapped.row}`;
  node.innerHTML = `
    <span class="unit-icon" aria-hidden="true"></span>
    <span class="unit-label">${escapeHtml(item.label || item.name || item.id || "--")}</span>
    ${options.speed ? `<span class="unit-speed">${escapeHtml(options.speed)}</span>` : ""}
  `;
  node.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    if (mapView.moved) return;
    showMapObjectDetail(kind, item, snapped);
  });
  applyZoomFade(node, level, 1, 0);
  parent.appendChild(node);
}

function renderMapBackdropStamps(parent) {
  MAP_DECOR_STAMPS.forEach((stamp) => {
    const beforeCount = parent.children.length;
    renderImageStamp(
      parent,
      MAP_ASSETS[stamp.asset],
      `map-decor-stamp ${stamp.className}`,
      stamp.x,
      stamp.y,
      stamp.width,
      stamp.rotation || 0,
      stamp.opacity
    );
    const image = parent.children[beforeCount];
    if (image) applyZoomFade(image, stamp.level || "world", stamp.opacity ?? 0.82, 0.08);
  });
}

function renderBrushAssetStamps(parent) {
  activeBrushes().forEach((brush, brushIndex) => {
    const points = brushPoints(brush);
    if (!points.length) return;
    const kind = classToken(brush.kind, "custom");
    const density = Math.max(1, Math.min(80, Number(brush.density || 12)));
    const jitter = Math.max(0, Math.min(12, Number(brush.jitter || 2)));
    const angle = brushTangentAngle(points);
    const count = kind === "forest" ? Math.min(10, density) : kind === "hills" ? Math.min(7, density) : ["river", "tributary"].includes(kind) ? Math.min(4, Math.ceil(density / 5)) : 0;
    for (let index = 0; index < count; index += 1) {
      const base = interpolateBrush(points, index, count);
      const x = base.x + deterministicJitter((brushIndex + 11) * 300 + index, jitter);
      const y = base.y + deterministicJitter((brushIndex + 11) * 400 + index, jitter);
      if (kind === "forest") {
        const beforeCount = parent.children.length;
        renderImageStamp(parent, MAP_ASSETS.forestCluster, "terrain-stamp terrain-forest", x, y, 9.5 + (index % 3) * 1.4, deterministicJitter(index + brushIndex, 7), 0.72);
        applyZoomFade(parent.children[beforeCount], brush.level || "region", 0.72, 0.1);
      } else if (kind === "hills") {
        const beforeCount = parent.children.length;
        renderImageStamp(parent, MAP_ASSETS.rockyHills, "terrain-stamp terrain-hills", x, y, 13 + (index % 2) * 2, deterministicJitter(index + brushIndex, 5), 0.66);
        applyZoomFade(parent.children[beforeCount], brush.level || "region", 0.66, 0.08);
      } else if (["river", "tributary"].includes(kind)) {
        const beforeCount = parent.children.length;
        renderImageStamp(parent, MAP_ASSETS.creek, `terrain-stamp terrain-${kind}`, x, y, kind === "river" ? 24 : 17, angle + deterministicJitter(index + brushIndex, 6), kind === "river" ? 0.44 : 0.34);
        applyZoomFade(parent.children[beforeCount], brush.level || "region", kind === "river" ? 0.44 : 0.34, 0.08);
      }
    }
  });
}

function renderTopbar() {
  setText("world-title", dashboard.world_id || "未命名世界");
  setText("world-time", `时间：${dashboard.time || "--"}`);
  setText("weather", `天气：${dashboard.weather || "--"}`);
  const preset = dashboard.advance_profile?.default_preset || "--";
  setText("branch", `枝丫：${dashboard.branch_id || "--"}｜推进：${preset}`);
}

function renderTimeline() {
  const list = $("#timeline");
  list.innerHTML = "";
  for (const node of timeline.nodes || []) {
    const item = document.createElement("li");
    item.className = classToken(node.state, "confirmed");
    item.innerHTML = `<strong>${escapeHtml(node.time || "unknown")}</strong><p>${escapeHtml(node.label || node.event_id)}</p>`;
    item.addEventListener("click", () => {
      showDetail("timeline", node);
      if (storyEntryById(node.event_id || node.id)) showStory(node.event_id || node.id, true);
    });
    list.appendChild(item);
  }
}

function storyEntries() {
  const story = dashboard.story || {};
  return [story.current, ...(Array.isArray(story.entries) ? story.entries : [])].filter(Boolean);
}

function storyEntryById(id) {
  return storyEntries().find((entry) => entry.id === id) || null;
}

function renderStoryParagraphs(text) {
  const blocks = String(text || "当前没有可显示的剧情正文。")
    .split(/\n\s*\n/)
    .map((block) => block.trim())
    .filter(Boolean);
  return blocks.map((block) => {
    if (block.startsWith("## ")) return `<h3>${escapeHtml(block.slice(3))}</h3>`;
    return `<p>${escapeHtml(block).replaceAll("\n", "<br>")}</p>`;
  }).join("");
}

function showStory(id = "CURRENT-SCENE", scrollIntoView = false) {
  const entry = storyEntryById(id) || dashboard.story?.current || storyEntries()[0];
  if (!entry) return;
  activeStoryId = entry.id;
  setText("story-title", entry.title || entry.id || "剧情");
  setText("story-time", `时间：${entry.time || "--"}`);
  setText("story-state", bilingualTerm(entry.state || "confirmed"));
  setText("story-source", `来源：${entry.source || "dashboard.json"}`);
  const body = $("#story-body");
  if (body) body.innerHTML = renderStoryParagraphs(entry.narrative);
  document.querySelectorAll("#story-directory button[data-story-id]").forEach((button) => {
    button.classList.toggle("active", button.dataset.storyId === entry.id);
  });
  if (scrollIntoView) $("#story-reader")?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderStoryDirectory() {
  const list = $("#story-directory");
  if (!list) return;
  list.innerHTML = "";
  for (const entry of storyEntries()) {
    const item = document.createElement("li");
    item.innerHTML = `<button type="button" data-story-id="${escapeHtml(entry.id || "")}">
      <span>${escapeHtml(entry.title || entry.id || "未命名剧情")}</span>
      <small>${escapeHtml(entry.time || "--")} · ${escapeHtml(bilingualTerm(entry.state || "confirmed"))}</small>
    </button>`;
    item.querySelector("button").addEventListener("click", () => showStory(entry.id, true));
    list.appendChild(item);
  }
  showStory(activeStoryId);
}

function renderMapDecorations(map, content) {
  const terrain = document.createElement("div");
  terrain.className = "terrain-layer";
  terrain.setAttribute("aria-hidden", "true");
  renderMapBackdropStamps(content);
  terrain.appendChild(renderBrushSvg());
  content.appendChild(terrain);
  renderBrushAssetStamps(content);

  ["top-left", "top-right", "bottom-left", "bottom-right"].forEach((corner) => {
    const ornament = document.createElement("img");
    ornament.className = `map-corner-ornament ${corner}`;
    ornament.src = MAP_ASSETS.corner;
    ornament.alt = "";
    ornament.setAttribute("aria-hidden", "true");
    map.appendChild(ornament);
  });

  const title = document.createElement("div");
  title.className = "map-scroll-title";
  title.textContent = dashboard.focal_place || dashboard.world_id || "神视地图";
  map.appendChild(title);

  const compass = document.createElement("div");
  compass.className = "compass-rose";
  compass.setAttribute("aria-hidden", "true");
  compass.innerHTML = "<span>北</span>";
  map.appendChild(compass);

  const scale = document.createElement("div");
  scale.id = "map-scale-bar";
  scale.className = "scale-bar";
  scale.setAttribute("aria-hidden", "true");
  scale.innerHTML = "<small>0</small><span></span><small>5 km</small>";
  map.appendChild(scale);

  const legend = document.createElement("div");
  legend.className = "map-legend";
  legend.setAttribute("aria-label", "地图图例");
  legend.innerHTML = `
    <span><i class="legend-piece"></i>棋子</span>
    <span><i class="legend-pin"></i>事件</span>
    <span><i class="legend-place"></i>地点</span>
    <span><i class="legend-plot"></i>剧情就绪</span>
    <span><i class="legend-danger"></i>危险/暂停</span>
  `;
  map.appendChild(legend);
}

function renderBrushSvg() {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("class", "brush-svg");
  svg.setAttribute("viewBox", "0 0 100 100");
  svg.setAttribute("preserveAspectRatio", "none");
  activeBrushes().forEach((brush, brushIndex) => {
    const points = brushPoints(brush);
    if (!points.length) return;
    const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
    group.setAttribute("class", `brush brush-${classToken(brush.kind, "custom")}`);
    group.setAttribute("data-brush-id", brush.id || `brush-${brushIndex}`);
    group.dataset.zoomLevel = brush.level || "region";
    group.style.setProperty("--base-opacity", "1");
    group.style.setProperty("--min-opacity", "0.08");
    group.style.opacity = String(opacityForLevel(brush.level || "region"));
    const color = brush.color || (brush.kind === "forest" ? "#557542" : brush.kind === "hills" ? "#765c38" : "#315b76");
    const displayWidth = brushDisplayWidth(brush);
    if (["river", "tributary", "custom"].includes(brush.kind)) {
      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("d", svgPathFromPoints(points));
      path.setAttribute("stroke", color);
      path.setAttribute("stroke-width", String(displayWidth));
      path.setAttribute("fill", "none");
      path.setAttribute("stroke-linecap", "round");
      path.setAttribute("stroke-linejoin", "round");
      group.appendChild(path);
    }
    const density = Math.max(1, Math.min(80, Number(brush.density || 12)));
    const jitter = Math.max(0, Math.min(12, Number(brush.jitter || 2)));
    for (let index = 0; index < density; index += 1) {
      const base = interpolateBrush(points, index, density);
      const x = base.x + deterministicJitter((brushIndex + 1) * 100 + index, jitter);
      const y = base.y + deterministicJitter((brushIndex + 1) * 200 + index, jitter);
      if (brush.kind === "forest") {
        const tree = document.createElementNS("http://www.w3.org/2000/svg", "path");
        tree.setAttribute("d", `M ${x} ${y - 1.8} L ${x - 1.3} ${y + 1.2} L ${x + 1.3} ${y + 1.2} Z`);
        tree.setAttribute("fill", color);
        tree.setAttribute("opacity", "0.68");
        group.appendChild(tree);
      } else if (brush.kind === "hills") {
        const hill = document.createElementNS("http://www.w3.org/2000/svg", "path");
        hill.setAttribute("d", `M ${x - 2.2} ${y + 1.1} Q ${x} ${y - 2.2} ${x + 2.2} ${y + 1.1}`);
        hill.setAttribute("stroke", color);
        hill.setAttribute("stroke-width", "0.75");
        hill.setAttribute("fill", "none");
        hill.setAttribute("opacity", "0.7");
        group.appendChild(hill);
      } else {
        const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        dot.setAttribute("cx", String(x));
        dot.setAttribute("cy", String(y));
        dot.setAttribute("r", String(Math.max(0.14, displayWidth / 3.4)));
        dot.setAttribute("fill", color);
        dot.setAttribute("opacity", brush.kind === "tributary" ? "0.38" : "0.5");
        group.appendChild(dot);
      }
    }
    svg.appendChild(group);
  });
  return svg;
}

function brushDisplayWidth(brush) {
  const raw = Number(brush?.width || 3);
  const kind = classToken(brush?.kind, "custom");
  const scale = kind === "river" ? 0.34 : kind === "tributary" ? 0.28 : kind === "custom" ? 0.3 : 0.24;
  return Number(Math.max(0.32, Math.min(2.6, raw * scale)).toFixed(2));
}

function brushEditorKind() {
  return $("#brush-editor-kind")?.value || "river";
}

function brushEditorColor(kind = brushEditorKind()) {
  return $("#brush-editor-color")?.value || (kind === "forest" ? "#557542" : kind === "hills" ? "#765c38" : kind === "tributary" ? "#4b7992" : "#315b76");
}

function defaultBrushStyle(kind = brushEditorKind()) {
  return {
    width: kind === "river" ? 3 : kind === "tributary" ? 2 : kind === "forest" ? 2 : kind === "hills" ? 2.5 : 2.5,
    density: kind === "forest" ? 18 : kind === "hills" ? 10 : 12,
    jitter: kind === "forest" ? 4 : kind === "hills" ? 3 : 2,
    color: kind === "forest" ? "#557542" : kind === "hills" ? "#765c38" : kind === "tributary" ? "#4b7992" : "#315b76"
  };
}

function numberInputValue(id, fallback) {
  const raw = document.getElementById(id)?.value;
  const value = Number(raw);
  return Number.isFinite(value) && value >= 0 ? value : fallback;
}

function syncBrushEditorOutputs() {
  const pointsJson = JSON.stringify(brushEditor.points);
  const output = $("#brush-editor-points-json");
  if (output) output.value = pointsJson;
}

function setBrushEditorStatus() {
  const status = $("#brush-editor-status");
  if (!status) return;
  const pointsJson = JSON.stringify(brushEditor.points);
  syncBrushEditorOutputs();
  status.textContent = `${brushEditor.enabled ? "点选中" : "已暂停"} · 点数 ${brushEditor.points.length} · points-json: ${pointsJson}`;
}

function mapPointFromEvent(event) {
  const rect = $("#map").getBoundingClientRect();
  const localX = (event.clientX - rect.left - mapView.x) / mapView.scale;
  const localY = (event.clientY - rect.top - mapView.y) / mapView.scale;
  const x = Math.min(100, Math.max(0, (localX / rect.width) * 100));
  const y = Math.min(100, Math.max(0, (localY / rect.height) * 100));
  return [Number(x.toFixed(1)), Number(y.toFixed(1))];
}

function renderBrushEditorPreview(map) {
  if (!brushEditor.enabled && !brushEditor.points.length) return;
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("class", "brush-editor-preview");
  svg.setAttribute("viewBox", "0 0 100 100");
  svg.setAttribute("preserveAspectRatio", "none");
  const points = brushEditor.points.map(normalizeBrushPoint).filter(Boolean);
  const color = brushEditorColor();
  if (points.length) {
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", svgPathFromPoints(points));
    path.setAttribute("stroke", color);
    path.setAttribute("stroke-width", String(Math.max(0.25, numberInputValue("brush-editor-width", 3) * 0.28)));
    svg.appendChild(path);
  }
  points.forEach((point, index) => {
    const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    dot.setAttribute("cx", String(point.x));
    dot.setAttribute("cy", String(point.y));
    dot.setAttribute("r", index === points.length - 1 ? "0.95" : "0.65");
    svg.appendChild(dot);
  });
  map.appendChild(svg);
}

function renderMap() {
  const map = $("#map");
  map.innerHTML = "";
  map.classList.toggle("brush-editor-active", brushEditor.enabled);
  const content = document.createElement("div");
  const visibleLevel = mapLevelForScale();
  content.id = "map-content";
  content.className = "map-content";
  map.appendChild(content);
  renderHexGrid(content, visibleLevel);
  renderMapDecorations(map, content);
  const worldOverview = document.createElement("button");
  worldOverview.draggable = false;
  worldOverview.className = "hex-unit map-node world overview city-unit";
  const center = nearestHexCenter({ x: 50, y: 45 }, visibleLevel);
  const pieceWidth = center.drawWidth * 0.72;
  const pieceHeight = center.drawHeight * 0.72;
  worldOverview.style.left = `${center.x}%`;
  worldOverview.style.top = `${center.y}%`;
  worldOverview.style.setProperty("--piece-width", `${pieceWidth}%`);
  worldOverview.style.setProperty("--piece-height", `${pieceHeight}%`);
  worldOverview.style.setProperty("--node-icon", `url("${MAP_ASSETS.pieceCityCity}")`);
  worldOverview.style.setProperty("--unit-icon", `url("${MAP_ASSETS.pieceCityCity}")`);
  worldOverview.innerHTML = `<span class="unit-icon" aria-hidden="true"></span><span class="unit-label">${escapeHtml(dashboard.focal_place || dashboard.world_id || "世界总览")}</span>`;
  worldOverview.title = "世界总览";
  worldOverview.addEventListener("click", () => showDetail("map-node", {
    id: dashboard.world_id || "WORLD",
    kind: "world",
    label: dashboard.focal_place || dashboard.world_id || "世界总览",
    status: "world",
    source: "dashboard.json"
  }));
  applyZoomFade(worldOverview, visibleLevel, 1, 0);
  content.appendChild(worldOverview);
  (mapLayers.nodes || []).forEach((layerNode, index) => {
    renderHexUnit(content, {
      ...layerNode,
      label: layerNode.name || layerNode.id,
      kind: "location"
    }, "map-node", index + 13, {
      className: "hex-unit map-node",
      level: visibleLevel,
      asset: MAP_ASSETS[nodeAssetName(layerNode)]
    });
  });
  (dashboard.pieces || []).forEach((piece, index) => {
    renderHexUnit(content, piece, "piece", index, {
      className: "hex-unit piece",
      level: visibleLevel,
      asset: MAP_ASSETS[pieceAssetName(piece)],
      speed: piece.speed || piece.move_speed || piece.speed_label || ""
    });
  });
  (dashboard.pins || []).forEach((pin, index) => {
    renderHexUnit(content, pin, "pin", index + 7, {
      className: "hex-unit pin",
      level: visibleLevel,
      asset: MAP_ASSETS.pieceEvent
    });
  });
  if (false) {
  (mapLayers.nodes || [])
    .forEach((layerNode, index) => {
      const pos = positionOf(layerNode, index + 13);
      const node = document.createElement("button");
      node.className = `map-node ${classToken(layerNode.level, "world")}`;
      node.style.left = `${pos.x}%`;
      node.style.top = `${pos.y}%`;
      node.style.setProperty("--node-icon", `url("${MAP_ASSETS[nodeAssetName(layerNode)]}")`);
      node.textContent = layerNode.name || layerNode.id;
      node.title = `${layerNode.name || layerNode.id}｜${layerNode.level || "map"}`;
      node.addEventListener("click", () => showDetail("map-node", {
        id: layerNode.id,
        kind: "location",
        label: layerNode.name || layerNode.id,
        status: layerNode.level || "map",
        source: layerNode.source
      }));
      applyZoomFade(node, layerNode.level || "region", 1, 0.05);
      content.appendChild(node);
    });
  (dashboard.pieces || []).forEach((piece, index) => {
    const pos = positionOf(piece, index);
    const node = document.createElement("button");
    node.className = `piece ${classToken(piece.status, "ordinary")}`;
    node.style.left = `${pos.x}%`;
    node.style.top = `${pos.y}%`;
    node.title = `${piece.label}｜${piece.status || "ordinary"}`;
    node.textContent = piece.label ? piece.label.slice(0, 2) : piece.id.slice(0, 2);
    node.addEventListener("click", () => showDetail("piece", piece));
    applyZoomFade(node, visualLevelForPiece(piece), 1, 0);
    content.appendChild(node);
  });
  (dashboard.pins || []).forEach((pin, index) => {
    const pos = positionOf(pin, index + 7);
    const node = document.createElement("button");
    node.className = "pin";
    node.style.left = `${pos.x}%`;
    node.style.top = `${pos.y}%`;
    node.textContent = "✦ " + (pin.label || pin.id);
    node.addEventListener("click", () => showDetail("pin", pin));
    applyZoomFade(node, pin.level || "scene", 1, 0);
    content.appendChild(node);
  });
  }
  renderBrushEditorPreview(content);
  applyMapViewTransform();
}

function showDetail(kind, item) {
  const safeItem = item && typeof item === "object" ? item : { id: "UNKNOWN", label: "未知目标", state: "unknown" };
  selected = { kind, item: safeItem };
  const title = safeItem.label || safeItem.id || "未命名";
  const detailKind = bilingualTerm(kind);
  const detailStatus = bilingualTerm(safeItem.status || safeItem.state || safeItem.level || "confirmed");
  const source = safeItem.source ? `<p>来源：<code>${escapeHtml(safeItem.source)}</code></p>` : "";
  const target = safeItem.target_id ? `<p>关联目标：<code>${escapeHtml(safeItem.target_id)}</code></p>` : "";
  $("#detail").innerHTML = `
    <h3>${escapeHtml(title)}</h3>
    <p>类型：${escapeHtml(detailKind)}</p>
    <p>ID：<code>${escapeHtml(safeItem.id || safeItem.event_id || "--")}</code></p>
    <p>状态：${escapeHtml(detailStatus)}</p>
    ${target}
    ${source}
  `;
}

function selectedActionTarget() {
  if (!selected || !selected.item || typeof selected.item !== "object") return null;
  const id = selected.item.id || selected.item.event_id || selected.item.target_id;
  if (!id) return null;
  const targetKind = selected.item.kind || selected.kind || "world";
  const allowedKinds = new Set(["piece", "pin", "timeline", "map-node", "hex", "character", "event", "location"]);
  const isActionable = allowedKinds.has(selected.kind) || allowedKinds.has(targetKind);
  if (!isActionable) return null;
  return { id, targetKind, fromEvent: selected.item.event_id || selected.item.id || id };
}

function promptBranchDraft(fromEvent) {
  const branchId = window.prompt("新枝丫 ID（例如 save-mira）", "");
  if (!branchId || !branchId.trim()) {
    showDetail("system", { id: "BRANCH_CANCELLED", label: "创建分支已取消：缺少新枝丫 ID", state: "cancelled" });
    return null;
  }
  const changeSummary = window.prompt("这一枝丫要改变什么？", "");
  if (!changeSummary || !changeSummary.trim()) {
    showDetail("system", { id: "BRANCH_CANCELLED", label: "创建分支已取消：缺少改变摘要", state: "cancelled" });
    return null;
  }
  return {
    branch_id: branchId.trim(),
    fork_event: fromEvent,
    change_summary: changeSummary.trim()
  };
}

function promptTerrainBrushDraft() {
  const brushId = window.prompt("地形笔刷 ID（例如 BRUSH-RIVER-NEW）", "");
  if (!brushId || !brushId.trim()) {
    showDetail("system", { id: "TERRAIN_CANCELLED", label: "改地形已取消：缺少笔刷 ID", state: "cancelled" });
    return null;
  }
  const kind = window.prompt("地形类型：river / tributary / hills / forest / custom", "river");
  if (!kind || !kind.trim()) {
    showDetail("system", { id: "TERRAIN_CANCELLED", label: "改地形已取消：缺少地形类型", state: "cancelled" });
    return null;
  }
  const changeSummary = window.prompt("你要怎样改变地图？AI 会据此生成 points-json 预览。", "");
  if (!changeSummary || !changeSummary.trim()) {
    showDetail("system", { id: "TERRAIN_CANCELLED", label: "改地形已取消：缺少改变描述", state: "cancelled" });
    return null;
  }
  const pointsJson = window.prompt("可选：直接输入 points-json，例如 [[18,22],[30,31],[42,61]]；留空则交给 AI 生成。", "");
  return {
    brush_id: brushId.trim(),
    kind: kind.trim(),
    label: changeSummary.trim().slice(0, 32),
    change_summary: changeSummary.trim(),
    points_json: pointsJson && pointsJson.trim() ? pointsJson.trim() : "<points-json>"
  };
}

async function emitAction(action) {
  const target = selectedActionTarget();
  if (!target) {
    showDetail("system", { id: "NO_SELECTION", label: "请先选择棋子、图钉或时间线节点", state: "waiting" });
    return;
  }
  const { id, targetKind, fromEvent } = target;
  const branchDraft = action === "branch" ? promptBranchDraft(fromEvent) : null;
  if (action === "branch" && !branchDraft) return;
  const branchPayloadJson = branchDraft
    ? commandJsonArg({
        branch_id: branchDraft.branch_id,
        fork_event: branchDraft.fork_event,
        change_summary: branchDraft.change_summary
      })
    : "";
  const suggestedCommand = action === "branch"
    ? `scripts/create_action_request.py --world <world> --action branch --target-id ${id} --target-kind ${targetKind} --intent "branch from ${fromEvent}" --payload-json "${branchPayloadJson}" --confirmed`
    : `scripts/create_action_request.py --world <world> --action ${action} --target-id ${id} --target-kind ${targetKind} --intent ${action} --confirmed`;
  const payload = {
    action,
    target_id: id,
    target_kind: targetKind,
    canonical_effect: "none until executed by Codex/script",
    suggested_command: suggestedCommand
  };
  const backendRequest = {
    action,
    target_id: id,
    target_kind: targetKind,
    intent: action
  };
  if (action === "branch") {
    payload.branch_id = branchDraft.branch_id;
    payload.fork_event = branchDraft.fork_event;
    payload.change_summary = branchDraft.change_summary;
    backendRequest.intent = `branch from ${fromEvent}`;
    backendRequest.payload = {
      branch_id: branchDraft.branch_id,
      fork_event: branchDraft.fork_event,
      change_summary: branchDraft.change_summary
    };
  }
  $("#detail").innerHTML += `<p>动作请求：</p><pre>${escapeHtml(JSON.stringify(payload, null, 2))}</pre>`;
  setPendingFrontendAction({
    submitType: "action-request",
    label: actionRequestActionLabel(action),
    detailKind: "pending-action",
    detailItem: { id, label: actionRequestActionLabel(action), state: "pending-submit", source: "frontend action panel" },
    payload,
    backendRequest
  });
}

async function emitGlobalAction(action) {
  if (actionInFlight) {
    setLoadStatus("已有一个操作正在处理，请稍等", true);
    return;
  }
  actionInFlight = true;
  try {
  let payload;
  let backendRequest;
  if (action === "advance-time") {
    const preset = dashboard.advance_profile?.default_preset || "hybrid";
    payload = {
      action,
      target_id: dashboard.world_id || "WORLD",
      target_kind: "world",
      canonical_effect: "advance_world.py applies immediately through local backend",
      advance_preset: preset,
      suggested_command: `scripts/advance_world.py --world <world> --preset ${preset} --confirmed`
    };
    backendRequest = { preset };
  } else if (action === "weather-override") {
    const weather = window.prompt("新天气 / 天象覆盖", "");
    if (!weather || !weather.trim()) {
      showDetail("system", { id: "WEATHER_CANCELLED", label: "改天气已取消：缺少天气文本", state: "cancelled" });
      return;
    }
    payload = {
      action,
      target_id: "weather",
      target_kind: "random",
      canonical_effect: "none until executed by Codex/script",
      value: weather.trim(),
      suggested_command: `scripts/create_action_request.py --world <world> --action weather-override --value "${weather.trim().replaceAll("\\", "\\\\").replaceAll('"', '\\"')}" --confirmed`
    };
    backendRequest = { action, target_id: "weather", target_kind: "random", intent: "weather override", value: weather.trim() };
  } else if (action === "set-rule") {
    const ruleText = window.prompt("要锁定的世界规则", "");
    if (!ruleText || !ruleText.trim()) {
      showDetail("system", { id: "RULE_CANCELLED", label: "锁定规则已取消：缺少规则文本", state: "cancelled" });
      return;
    }
    payload = {
      action,
      target_id: "WORLD",
      target_kind: "world",
      canonical_effect: "none until executed by Codex/script",
      text: ruleText.trim(),
      suggested_command: `scripts/create_action_request.py --world <world> --action set-rule --text "${ruleText.trim().replaceAll("\\", "\\\\").replaceAll('"', '\\"')}" --payload-json "{\\\"scope\\\":\\\"global\\\"}" --confirmed`
    };
    backendRequest = { action, target_id: "WORLD", target_kind: "world", intent: ruleText.trim(), text: ruleText.trim(), payload: { scope: "global" } };
  } else if (action === "terrain-brush") {
    const draft = promptTerrainBrushDraft();
    if (!draft) return;
    const terrainPayloadJson = commandJsonArg(draft);
    const terrainIntent = draft.change_summary.replaceAll("\\", "\\\\").replaceAll('"', '\\"');
    payload = {
      action,
      target_id: "MAP",
      target_kind: "world",
      canonical_effect: "none until executed by Codex/script",
      brush_id: draft.brush_id,
      kind: draft.kind,
      change_summary: draft.change_summary,
      points_json: draft.points_json,
      suggested_command: `scripts/create_action_request.py --world <world> --action terrain-brush --target-id MAP --target-kind world --intent "${terrainIntent}" --payload-json "${terrainPayloadJson}" --confirmed`
    };
    backendRequest = {
      action,
      target_id: "MAP",
      target_kind: "world",
      intent: draft.change_summary,
      payload: draft
    };
  } else {
    payload = { action, target_id: "WORLD", target_kind: "world" };
    backendRequest = { action, target_id: "WORLD", target_kind: "world", intent: action };
  }
  showDetail("world-action", {
    id: payload.target_id,
    label: action === "advance-time" ? "推进世界时间" : action === "set-rule" ? "锁定世界规则" : action === "terrain-brush" ? "改写地图地形" : "覆盖天气",
    state: "global-action",
    source: "frontend action panel"
  });
  $("#detail").innerHTML += `<p>动作请求：</p><pre>${escapeHtml(JSON.stringify(payload, null, 2))}</pre>`;
  setPendingFrontendAction({
    submitType: action === "advance-time" ? "advance-world" : "action-request",
    label: actionRequestActionLabel(action),
    detailKind: "pending-action",
    detailItem: { id: payload.target_id, label: actionRequestActionLabel(action), state: "pending-submit", source: "frontend action panel" },
    payload,
    backendRequest
  });
  } finally {
    actionInFlight = false;
  }
}

function validateDashboardData(data) {
  if (!data || typeof data !== "object" || Array.isArray(data)) {
    throw new Error("dashboard 必须是 JSON 对象");
  }
  if (data.pieces && !Array.isArray(data.pieces)) {
    throw new Error("dashboard.pieces 必须是数组");
  }
  if (data.pins && !Array.isArray(data.pins)) {
    throw new Error("dashboard.pins 必须是数组");
  }
  return {
    world_id: data.world_id || "未命名世界",
    branch_id: data.branch_id || "--",
    time: data.time || "--",
    weather: data.weather || "--",
    focal_place: data.focal_place || "",
    current_scene: data.current_scene || "",
    pieces: data.pieces || [],
    pins: data.pins || [],
    pending_action_requests: data.pending_action_requests || [],
    advance_profile: data.advance_profile || null,
    narrative_profile: data.narrative_profile || null,
    world_rules: data.world_rules || { active: [] },
    random_log: data.random_log || { recent: [] },
    attention: data.attention || { followed: [], ignored: [], plot_ready: [] },
    story: data.story || {
      current: { id: "CURRENT-SCENE", title: data.focal_place || "当前剧情", time: data.time || "--", state: "current", narrative: data.current_scene || "当前没有可显示的场景正文。", source: "dashboard.json" },
      entries: []
    }
  };
}

function validateTimelineData(data) {
  if (!data || typeof data !== "object" || Array.isArray(data)) {
    throw new Error("timeline 必须是 JSON 对象");
  }
  if (!Array.isArray(data.nodes)) {
    throw new Error("timeline.nodes 必须是数组");
  }
  return { nodes: data.nodes };
}

function validateMapLayersData(data) {
  if (!data || typeof data !== "object" || Array.isArray(data)) {
    throw new Error("map layers 必须是 JSON 对象");
  }
  if (data.nodes && !Array.isArray(data.nodes)) {
    throw new Error("map layers.nodes 必须是数组");
  }
  if (data.places && !Array.isArray(data.places)) {
    throw new Error("map layers.places 必须是数组");
  }
  return {
    schema: data.schema || "be-a-god.map-layers.v1",
    levels: Array.isArray(data.levels) ? data.levels : ["world", "region", "scene"],
    nodes: data.nodes || [],
    places: data.places || [],
    brushes: Array.isArray(data.brushes) ? data.brushes : []
  };
}

function renderAll() {
  renderTopbar();
  renderTimeline();
  renderStoryDirectory();
  renderMap();
  renderActionRequests();
  renderWorldRules();
  renderNarrativeProfile();
  renderRandomLog();
  renderAttention();
  updatePendingActionStatus();
}

function actionRequestActionLabel(action) {
  const labels = {
    observe: "观察",
    speak: "对话",
    intervene: "降下神谕",
    "advance-time": "推进世界时间",
    "weather-override": "覆盖天气",
    "set-rule": "锁定世界规则",
    "terrain-brush": "改写地图地形",
    branch: "创建剧情分支",
    ignore: "忽略此人",
    follow: "关注此人",
    custom: "自定义动作"
  };
  return labels[action] || `未知动作：${action || "--"}`;
}

function actionRequestStatusLabel(status) {
  const labels = {
    requested: "等待处理",
    queued: "已排队",
    accepted: "已接受",
    processing: "处理中",
    done: "已完成",
    completed: "已完成",
    cancelled: "已取消",
    rejected: "已拒绝",
    stale: "已过期"
  };
  return labels[status] || `状态：${status || "--"}`;
}

function actionRequestTargetKindLabel(kind) {
  const labels = {
    character: "角色",
    location: "地点",
    object: "物体",
    place: "地点",
    event: "事件",
    piece: "棋子",
    random: "随机项",
    world: "世界",
    unknown: "未知目标"
  };
  return labels[kind] || `目标类型：${kind || "--"}`;
}

function actionRequestIntentLabel(request) {
  const intent = String(request.intent || "").trim();
  const action = request.action;
  if (!intent || intent === action) {
    return actionRequestActionLabel(action);
  }
  if (intent.startsWith("preset:")) {
    return `使用推进方案：${intent.slice("preset:".length) || "--"}`;
  }
  if (intent === "weather override") return "玩家指定新天气";
  if (intent.startsWith("branch from ")) {
    return `从 ${intent.slice("branch from ".length)} 创建分支`;
  }
  return intent;
}

function actionRequestTitle(request) {
  return `待处理：${actionRequestActionLabel(request.action)}`;
}

function actionRequestSummary(request) {
  const status = actionRequestStatusLabel(request.status);
  const targetKind = actionRequestTargetKindLabel(request.target_kind);
  const targetId = request.target_id || "WORLD";
  const intent = actionRequestIntentLabel(request);
  return `${status} · 目标：${targetKind} ${targetId} · 内容：${intent}`;
}

function currentActionRequestOrder() {
  return Array.from(document.querySelectorAll("#action-requests li[data-request-id]"))
    .map((item) => item.dataset.requestId)
    .filter(Boolean);
}

async function saveActionRequestOrderFromDom() {
  const requestIds = currentActionRequestOrder();
  if (!requestIds.length) return;
  await submitBackendActionRequestOrder(requestIds);
}

function moveActionRequestInDashboard(fromId, toId) {
  if (!fromId || !toId || fromId === toId) return false;
  const requests = dashboard.pending_action_requests || [];
  const fromIndex = requests.findIndex((request) => request.request_id === fromId);
  const toIndex = requests.findIndex((request) => request.request_id === toId);
  if (fromIndex < 0 || toIndex < 0) return false;
  const [moved] = requests.splice(fromIndex, 1);
  requests.splice(toIndex, 0, moved);
  return true;
}

function renderActionRequests() {
  const list = $("#action-requests");
  if (!list) return;
  list.innerHTML = "";
  const requests = dashboard.pending_action_requests || [];
  if (!requests.length) {
    const empty = document.createElement("li");
    empty.textContent = "暂无待处理动作";
    list.appendChild(empty);
    return;
  }
  for (const request of requests) {
    const item = document.createElement("li");
    item.draggable = true;
    item.dataset.requestId = request.request_id || "";
    item.innerHTML = `
      <div class="request-row">
        <button class="request-main" type="button" title="点击查看详情；拖动整条可调整优先级">
          <span class="request-drag-handle" aria-hidden="true">☰</span>
          <span class="request-title">${escapeHtml(actionRequestTitle(request))}</span>
          <span class="request-summary">${escapeHtml(actionRequestSummary(request))}</span>
          <span class="request-id">${escapeHtml(request.request_id || "--")}</span>
        </button>
        <button class="request-cancel" type="button" title="取消这个待处理动作">取消</button>
      </div>
    `;
    item.querySelector(".request-main").addEventListener("click", () => {
      showDetail("action-request", {
        id: request.request_id,
        label: `${actionRequestActionLabel(request.action)} → ${actionRequestTargetKindLabel(request.target_kind)} ${request.target_id || "WORLD"}`,
        state: actionRequestStatusLabel(request.status),
        source: request.source
      });
      $("#detail").innerHTML += `
        <p>玩家可读摘要：${escapeHtml(actionRequestSummary(request))}</p>
        <p>原始动作请求：</p><pre>${escapeHtml(JSON.stringify(request, null, 2))}</pre>
      `;
    });
    item.querySelector(".request-cancel").addEventListener("click", async (event) => {
      event.stopPropagation();
      const requestId = request.request_id;
      if (!requestId) return;
      const confirmed = window.confirm(`确认取消这个待处理动作吗？\n${actionRequestTitle(request)}\n${requestId}`);
      if (!confirmed) return;
      await submitBackendCancelActionRequest(requestId);
    });
    item.addEventListener("dragstart", (event) => {
      draggedActionRequestId = request.request_id || null;
      item.classList.add("dragging");
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", draggedActionRequestId || "");
    });
    item.addEventListener("dragend", () => {
      item.classList.remove("dragging");
      draggedActionRequestId = null;
    });
    item.addEventListener("dragover", (event) => {
      event.preventDefault();
      if (!draggedActionRequestId || draggedActionRequestId === request.request_id) return;
      item.classList.add("drag-over");
    });
    item.addEventListener("dragleave", () => {
      item.classList.remove("drag-over");
    });
    item.addEventListener("drop", async (event) => {
      event.preventDefault();
      item.classList.remove("drag-over");
      const fromId = event.dataTransfer.getData("text/plain") || draggedActionRequestId;
      const toId = request.request_id;
      if (!moveActionRequestInDashboard(fromId, toId)) return;
      renderActionRequests();
      await saveActionRequestOrderFromDom();
    });
    list.appendChild(item);
  }
}

function renderWorldRules() {
  const list = $("#world-rules");
  if (!list) return;
  list.innerHTML = "";
  const rules = dashboard.world_rules?.active || [];
  if (!rules.length) {
    const empty = document.createElement("li");
    empty.textContent = "暂无锁定规则";
    list.appendChild(empty);
    return;
  }
  for (const rule of rules) {
    const item = document.createElement("li");
    item.innerHTML = `<button type="button">${escapeHtml(rule.rule_id || "--")} · ${escapeHtml(rule.scope || "--")}</button>`;
    item.querySelector("button").addEventListener("click", () => {
      showDetail("world-rule", {
        id: rule.rule_id,
        label: rule.text || "世界规则",
        state: rule.scope || "active",
        source: dashboard.world_rules?.source || "setup/world-rules.json"
      });
      $("#detail").innerHTML += `<p>规则：</p><pre>${escapeHtml(JSON.stringify(rule, null, 2))}</pre>`;
    });
    list.appendChild(item);
  }
}

function renderNarrativeProfile() {
  const list = $("#narrative-profile");
  if (!list) return;
  list.innerHTML = "";
  const profile = dashboard.narrative_profile;
  if (!profile) {
    const empty = document.createElement("li");
    empty.textContent = "暂无叙事配置";
    list.appendChild(empty);
    return;
  }
  const item = document.createElement("li");
  const label = profile.label || profile.default_profile || "narrative-profile";
  item.innerHTML = `<button type="button">${escapeHtml(label)} · ${escapeHtml(profile.default_scale || "--")}</button>`;
  item.querySelector("button").addEventListener("click", () => {
    showDetail("narrative-profile", {
      id: profile.default_profile || "narrative-profile",
      label,
      state: profile.default_scale || "active",
      source: profile.source || "setup/narrative-profile.json"
    });
    $("#detail").innerHTML += `<p>叙事配置：</p><pre>${escapeHtml(JSON.stringify(profile, null, 2))}</pre>`;
  });
  list.appendChild(item);
}

function renderRandomLog() {
  const list = $("#random-log");
  if (!list) return;
  list.innerHTML = "";
  const entries = dashboard.random_log?.recent || [];
  if (!entries.length) {
    const empty = document.createElement("li");
    empty.textContent = "暂无随机记录";
    list.appendChild(empty);
    return;
  }
  for (const entry of entries) {
    const item = document.createElement("li");
    const label = `#${entry.index || "--"} · ${entry.kind || "--"} · ${entry.mode || "--"}`;
    item.innerHTML = `<button type="button">${escapeHtml(label)}</button>`;
    item.querySelector("button").addEventListener("click", () => {
      showDetail("random-log", {
        id: `RNG-${entry.index || "--"}`,
        label: `${entry.purpose || "random"} → ${entry.value || "--"}`,
        state: entry.mode || "random",
        source: dashboard.random_log?.source || "story/main/random/random-log.jsonl"
      });
      $("#detail").innerHTML += `<p>骰点记录：</p><pre>${escapeHtml(JSON.stringify(entry, null, 2))}</pre>`;
    });
    list.appendChild(item);
  }
}

function renderAttention() {
  const list = $("#attention-list");
  if (!list) return;
  list.innerHTML = "";
  const groups = [
    ["剧情就绪", dashboard.attention?.plot_ready || []],
    ["关注", dashboard.attention?.followed || []],
    ["忽略", dashboard.attention?.ignored || []]
  ];
  let rendered = 0;
  for (const [label, items] of groups) {
    for (const item of items) {
      const row = document.createElement("li");
      row.innerHTML = `<button type="button">${escapeHtml(label)} · ${escapeHtml(item.label || item.id || "--")}</button>`;
      row.querySelector("button").addEventListener("click", () => {
        showDetail("attention", {
          id: item.id,
          label: item.label || item.id,
          state: item.attention || item.status,
          source: item.source
        });
      });
      list.appendChild(row);
      rendered += 1;
    }
  }
  if (!rendered) {
    const empty = document.createElement("li");
    empty.textContent = "暂无关注/忽略提醒";
    list.appendChild(empty);
  }
}

function readJsonFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.addEventListener("load", () => {
      try {
        resolve(JSON.parse(reader.result));
      } catch (error) {
        reject(error);
      }
    });
    reader.addEventListener("error", () => reject(reader.error || new Error("读取文件失败")));
    reader.readAsText(file, "utf-8");
  });
}

function linesFrom(id) {
  const value = document.getElementById(id)?.value || "";
  return value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

function markdownList(lines) {
  if (!lines.length) return "- （未填写）";
  return lines.map((line) => `- ${line}`).join("\n");
}

function briefValue(id) {
  return (document.getElementById(id)?.value || "").trim();
}

function generateWorldBrief() {
  const worldId = briefValue("brief-world-id") || "unnamed-world";
  const created = new Date().toISOString();
  return `# WORLD-BRIEF

## Metadata

- draft_id: DRAFT-FRONTEND
- world_id: ${worldId}
- created_at: ${created}
- status_note: This is a player-editable draft. Do not initialize a formal world until Status is confirmed.

## Player-locked facts

- World premise: ${briefValue("brief-premise")}
- Starting era: ${briefValue("brief-era")}
- Starting region: ${briefValue("brief-region")}
- God role: ${briefValue("brief-god-role")}
- Absolute prohibitions:
${markdownList(linesFrom("brief-prohibitions"))}

## Polishable facts

- Tone: ${briefValue("brief-tone")}
- Genre references:
${markdownList(linesFrom("brief-refs"))}
- Initial cultures:
${markdownList(linesFrom("brief-cultures"))}

## AI-fill fields

- Geography
- Weather model
- Factions
- Initial conflicts
- Wandering characters

## Field source map

- World premise: player-locked
- Starting era: player-locked
- Starting region: player-locked
- God role: player-locked
- Absolute prohibitions: player-locked
- Tone: polishable
- Genre references: polishable
- Initial cultures: polishable
- Content boundary: player-setting
- Player notes: player-note
- Geography: ai-fill
- Weather model: ai-fill
- Factions: ai-fill
- Initial conflicts: ai-fill
- Wandering characters: ai-fill

## Content boundary

- profile: ${briefValue("brief-content-profile") || "standard"}
- notes:
- absolute bans:
${markdownList(linesFrom("brief-content-bans"))}

## Player notes

${briefValue("brief-notes") || "（无）"}

## Confirmation

Status: draft

Do not create the formal world until the player confirms this brief.
`;
}

function downloadText(filename, text) {
  const blob = new Blob([text], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

async function loadDashboardFile(file) {
  const data = validateDashboardData(await readJsonFile(file));
  dashboard = data;
  selected = null;
  renderAll();
  setLoadStatus(`已载入 dashboard：${file.name}`);
}

async function loadTimelineFile(file) {
  const data = validateTimelineData(await readJsonFile(file));
  timeline = data;
  selected = null;
  renderAll();
  setLoadStatus(`已载入 timeline：${file.name}`);
}

async function loadMapLayersFile(file) {
  const data = validateMapLayersData(await readJsonFile(file));
  mapLayers = data;
  selected = null;
  renderAll();
  setLoadStatus(`已载入 map layers：${file.name}`);
}

function toggleBrushEditor() {
  brushEditor.enabled = !brushEditor.enabled;
  const button = $("#brush-editor-toggle");
  if (button) button.textContent = brushEditor.enabled ? "暂停点选" : "开始点选";
  renderMap();
  setBrushEditorStatus();
}

function clearBrushEditor() {
  brushEditor = { enabled: brushEditor.enabled, points: [] };
  renderMap();
  setBrushEditorStatus();
}

function undoBrushEditorPoint() {
  brushEditor.points.pop();
  renderMap();
  setBrushEditorStatus();
}

async function copyBrushEditorPoints() {
  const pointsJson = JSON.stringify(brushEditor.points);
  syncBrushEditorOutputs();
  try {
    await navigator.clipboard.writeText(pointsJson);
    showDetail("brush-editor", { id: "BRUSH_POINTS_COPIED", label: "points-json 已复制", state: "copied", source: "frontend brush editor" });
  } catch {
    showDetail("brush-editor", { id: "BRUSH_POINTS_COPY_FALLBACK", label: "复制失败，请手动复制 points-json 文本框", state: "manual-copy", source: "frontend brush editor" });
  }
}

function handleBrushEditorMapClick(event) {
  if (!brushEditor.enabled) return;
  if (event.target?.closest?.("button")) return;
  if (mapView.moved) return;
  brushEditor.points.push(mapPointFromEvent(event));
  renderMap();
  setBrushEditorStatus();
}

function brushEditorPayload() {
  const brushId = ($("#brush-editor-id")?.value || "").trim();
  const kind = brushEditorKind();
  const defaults = defaultBrushStyle(kind);
  const summary = ($("#brush-editor-summary")?.value || "").trim() || `draw ${kind} terrain brush`;
  if (!/^[A-Za-z0-9_-]+$/.test(brushId)) {
    showDetail("system", { id: "BRUSH_ID_INVALID", label: "笔刷 ID 只能包含字母、数字、下划线或连字符", state: "blocked" });
    return null;
  }
  if (!brushEditor.points.length) {
    showDetail("system", { id: "BRUSH_POINTS_EMPTY", label: "请先在地图上点选至少一个地形点", state: "waiting" });
    return null;
  }
  return {
    brush_id: brushId,
    kind,
    label: summary.slice(0, 32),
    change_summary: summary,
    points_json: JSON.stringify(brushEditor.points),
    width: numberInputValue("brush-editor-width", defaults.width),
    density: numberInputValue("brush-editor-density", Math.max(defaults.density, Math.min(40, brushEditor.points.length * 4))),
    jitter: numberInputValue("brush-editor-jitter", defaults.jitter),
    color: brushEditorColor(kind)
  };
}

async function emitBrushEditorCommand() {
  const draft = brushEditorPayload();
  if (!draft) {
    setBrushEditorStatus();
    return;
  }
  const terrainPayloadJson = commandJsonArg(draft);
  const terrainIntent = draft.change_summary.replaceAll("\\", "\\\\").replaceAll('"', '\\"');
  const payload = {
    action: "terrain-brush",
    target_id: "MAP",
    target_kind: "world",
    canonical_effect: "none until executed by Codex/script",
    brush_id: draft.brush_id,
    kind: draft.kind,
    points_json: draft.points_json,
    width: draft.width,
    density: draft.density,
    jitter: draft.jitter,
    color: draft.color,
    suggested_command: `scripts/create_action_request.py --world <world> --action terrain-brush --target-id MAP --target-kind world --intent "${terrainIntent}" --payload-json "${terrainPayloadJson}" --confirmed`
  };
  showDetail("brush-editor", {
    id: draft.brush_id,
    label: draft.change_summary,
    state: "preview-action",
    source: "frontend brush editor"
  });
  $("#detail").innerHTML += `<p>画笔 points-json：</p><pre>${escapeHtml(draft.points_json)}</pre><p>动作请求：</p><pre>${escapeHtml(JSON.stringify(payload, null, 2))}</pre>`;
  setPendingFrontendAction({
    submitType: "map-brush",
    label: "地形神谕",
    detailKind: "pending-action",
    detailItem: { id: draft.brush_id, label: draft.change_summary, state: "pending-submit", source: "frontend brush editor" },
    payload,
    backendRequest: { ...draft, points_json: draft.points_json, level: "region" }
  });
}

function showTutorialStep(step) {
  tutorialStepIndex = clamp(Number(step) || 1, 1, 6);
  document.querySelectorAll("[data-tutorial-step]").forEach((chapter) => {
    chapter.hidden = Number(chapter.dataset.tutorialStep) !== tutorialStepIndex;
  });
  document.querySelectorAll("[data-tutorial-target]").forEach((button) => {
    const active = Number(button.dataset.tutorialTarget) === tutorialStepIndex;
    button.classList.toggle("active", active);
    button.setAttribute("aria-current", active ? "step" : "false");
  });
  const progress = $("#tutorial-progress");
  if (progress) progress.style.setProperty("width", `${tutorialStepIndex / 6 * 100}%`);
  setText("tutorial-step-label", `第 ${tutorialStepIndex} / 6 章`);
  const previous = $("#tutorial-prev");
  const next = $("#tutorial-next");
  if (previous) previous.disabled = tutorialStepIndex === 1;
  if (next) next.textContent = tutorialStepIndex === 6 ? "回到第一章 ↺" : "下一章 →";
  $("#tutorial-dialog .tutorial-page")?.scrollTo({ top: 0, behavior: "smooth" });
}

function bindTutorialNavigation() {
  document.querySelectorAll("[data-tutorial-target]").forEach((button) => {
    button.addEventListener("click", () => showTutorialStep(button.dataset.tutorialTarget));
  });
  $("#tutorial-prev")?.addEventListener("click", () => showTutorialStep(tutorialStepIndex - 1));
  $("#tutorial-next")?.addEventListener("click", () => showTutorialStep(tutorialStepIndex === 6 ? 1 : tutorialStepIndex + 1));
}

function bindActions() {
  $("#story-current")?.addEventListener("click", () => showStory("CURRENT-SCENE", true));
  $("#story-back-current")?.addEventListener("click", () => showStory("CURRENT-SCENE", true));
  $("#open-tutorial").addEventListener("click", () => {
    const dialog = $("#tutorial-dialog");
    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "open");
    showTutorialStep(tutorialStepIndex);
  });
  $("#open-creation").addEventListener("click", () => {
    const dialog = $("#creation-dialog");
    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "open");
  });
  $("#generate-brief").addEventListener("click", () => {
    $("#brief-output").value = generateWorldBrief();
  });
  $("#download-brief").addEventListener("click", () => {
    const output = $("#brief-output");
    if (!output.value) output.value = generateWorldBrief();
    const worldId = briefValue("brief-world-id") || "unnamed-world";
    downloadText(`${worldId}.WORLD-BRIEF.md`, output.value);
  });
  $("#map").addEventListener("click", handleBrushEditorMapClick);
  $("#map").addEventListener("click", suppressMapClickAfterPan, true);
  $("#map").addEventListener("dragstart", preventMapNativeDrag);
  $("#map").addEventListener("selectstart", preventMapNativeDrag);
  $("#map").addEventListener("wheel", handleMapWheel, { passive: false });
  $("#map").addEventListener("pointerdown", beginMapPan);
  $("#map").addEventListener("pointermove", moveMapPan);
  $("#map").addEventListener("pointerup", endMapPan);
  $("#map").addEventListener("pointercancel", endMapPan);
  $("#map-zoom-in")?.addEventListener("click", () => setMapZoom(mapView.scale * MAP_ZOOM.factor));
  $("#map-zoom-out")?.addEventListener("click", () => setMapZoom(mapView.scale / MAP_ZOOM.factor));
  $("#map-zoom-reset")?.addEventListener("click", resetMapView);
  $("#observe").addEventListener("click", () => emitAction("observe"));
  $("#speak").addEventListener("click", () => emitAction("speak"));
  $("#intervene").addEventListener("click", () => emitAction("intervene"));
  $("#advance").addEventListener("click", () => emitGlobalAction("advance-time"));
  $("#weather-override").addEventListener("click", () => emitGlobalAction("weather-override"));
  $("#set-rule").addEventListener("click", () => emitGlobalAction("set-rule"));
  $("#terrain-brush-action").addEventListener("click", () => emitGlobalAction("terrain-brush"));
  $("#commit-action").addEventListener("click", submitPendingFrontendAction);
  $("#clear-pending-action").addEventListener("click", clearPendingFrontendAction);
  $("#brush-editor-toggle").addEventListener("click", toggleBrushEditor);
  $("#brush-editor-undo").addEventListener("click", undoBrushEditorPoint);
  $("#brush-editor-clear").addEventListener("click", clearBrushEditor);
  $("#brush-editor-copy").addEventListener("click", copyBrushEditorPoints);
  $("#brush-editor-command").addEventListener("click", emitBrushEditorCommand);
  $("#brush-editor-kind").addEventListener("change", () => {
    const style = defaultBrushStyle(brushEditorKind());
    const width = $("#brush-editor-width");
    const density = $("#brush-editor-density");
    const jitter = $("#brush-editor-jitter");
    const color = $("#brush-editor-color");
    if (width) width.value = String(style.width);
    if (density) density.value = String(style.density);
    if (jitter) jitter.value = String(style.jitter);
    if (color) color.value = style.color;
    renderMap();
    setBrushEditorStatus();
  });
  ["brush-editor-width", "brush-editor-density", "brush-editor-jitter", "brush-editor-color"].forEach((id) => {
    document.getElementById(id)?.addEventListener("input", () => {
      renderMap();
      setBrushEditorStatus();
    });
  });
  $("#branch-action").addEventListener("click", () => emitAction("branch"));
  $("#ignore").addEventListener("click", () => emitAction("ignore"));
  $("#follow").addEventListener("click", () => emitAction("follow"));
  $("#dashboard-file").addEventListener("change", async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      await loadDashboardFile(file);
    } catch (error) {
      setLoadStatus(`dashboard 载入失败：${error.message}`, true);
    }
  });
  $("#timeline-file").addEventListener("change", async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      await loadTimelineFile(file);
    } catch (error) {
      setLoadStatus(`timeline 载入失败：${error.message}`, true);
    }
  });
  $("#map-layers-file").addEventListener("change", async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      await loadMapLayersFile(file);
    } catch (error) {
      setLoadStatus(`map layers 载入失败：${error.message}`, true);
    }
  });
  document.querySelectorAll("button, input, select, textarea, img").forEach((element) => {
    element.draggable = false;
    element.addEventListener("dragstart", (event) => event.preventDefault());
  });
  bindTutorialNavigation();
}

async function tryLoadExternalData() {
  if (await loadBackendState()) return;
  let loadedDashboard = false;
  let loadedTimeline = false;
  let loadedMapLayers = false;
  try {
    const [dashResponse, timeResponse, mapResponse] = await Promise.allSettled([
      fetch("./dashboard.json"),
      fetch("./timeline.json"),
      fetch("./map-layers.json")
    ]);
    if (dashResponse.status === "fulfilled" && dashResponse.value.ok) {
      dashboard = validateDashboardData(await dashResponse.value.json());
      loadedDashboard = true;
    }
    if (timeResponse.status === "fulfilled" && timeResponse.value.ok) {
      timeline = validateTimelineData(await timeResponse.value.json());
      loadedTimeline = true;
    }
    if (mapResponse.status === "fulfilled" && mapResponse.value.ok) {
      mapLayers = validateMapLayersData(await mapResponse.value.json());
      loadedMapLayers = true;
    }
  } catch {
    // Opening index.html directly may block fetch; sample fallback remains available.
  }
  try {
    const [dashResponse, timeResponse, mapResponse] = await Promise.allSettled([
      fetch("./sample-dashboard.json"),
      fetch("./sample-timeline.json"),
      fetch("./sample-map-layers.json")
    ]);
    if (!loadedDashboard && dashResponse.status === "fulfilled" && dashResponse.value.ok) {
      dashboard = validateDashboardData(await dashResponse.value.json());
      loadedDashboard = true;
    }
    if (!loadedTimeline && timeResponse.status === "fulfilled" && timeResponse.value.ok) {
      timeline = validateTimelineData(await timeResponse.value.json());
      loadedTimeline = true;
    }
    if (!loadedMapLayers && mapResponse.status === "fulfilled" && mapResponse.value.ok) {
      mapLayers = validateMapLayersData(await mapResponse.value.json());
      loadedMapLayers = true;
    }
  } catch {
    // Bundled inline sample data remains available.
  }
  const source = loadedDashboard || loadedTimeline || loadedMapLayers ? "已自动载入 JSON 数据" : "当前使用内置样例数据";
  setLoadStatus(source);
}

async function main() {
  bindActions();
  await detectBackend();
  await tryLoadExternalData();
  renderAll();
  setBrushEditorStatus();
}

main();
