from pathlib import Path

ROOT = Path(r"F:/be_a_god/be-a-god/assets/frontend-template")
HTML = (ROOT / "index.html").read_text(encoding="utf-8")
JS = (ROOT / "app.js").read_text(encoding="utf-8")


def test_main_page_has_no_accidental_read_file_line_prefixes():
    assert not any(line.split("|", 1)[0].isdigit() for line in HTML.splitlines() if "|" in line)
    assert HTML.lstrip("\ufeff").startswith("<!doctype html>")
    assert '<main class="shell">' in HTML
    assert '</main>' in HTML


def test_tutorial_has_complete_start_to_play_chapters():
    for marker in (
        'data-tutorial-step="1"',
        'data-tutorial-step="2"',
        'data-tutorial-step="3"',
        'data-tutorial-step="4"',
        'data-tutorial-step="5"',
        'data-tutorial-step="6"',
        '从零开始',
        '地图与棋子',
        '进行一回合',
        '地形画笔',
        '全部按钮',
        '注意事项',
    ):
        assert marker in HTML


def test_tutorial_documents_every_static_button():
    labels = (
        '使用教程', '创世填空', '回到当前剧情', '缩小地图', '放大地图', '重置视角',
        '观察', '对话', '降下神谕', '推进时间', '改天气', '锁定规则', '改地形',
        '创建分支', '忽略此人', '关注此人', '确认提交 / 开始运行', '撤销草稿',
        '开始点选', '撤销一点', '清空点', '复制点位', '生成地形神谕',
        '生成草稿', '下载 WORLD-BRIEF.md',
    )
    for label in labels:
        assert f'<dt>{label}</dt>' in HTML


def test_tutorial_has_navigation_and_progress_logic():
    for marker in (
        'id="tutorial-prev"', 'id="tutorial-next"', 'id="tutorial-progress"',
        'function showTutorialStep', 'tutorialStepIndex',
        'data-tutorial-target',
    ):
        assert marker in HTML or marker in JS


def test_tutorial_uses_existing_game_art_for_visual_examples():
    for asset in (
        './img/pieces/piece-character-ferryman.png',
        './img/pieces/piece-city-town.png',
        './img/hex-river.png',
        './img/ui/medieval-button-frame.png',
    ):
        assert asset in HTML
