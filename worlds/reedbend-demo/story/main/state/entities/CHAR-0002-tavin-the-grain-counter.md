# CHAR-0002 Tavin the Grain Counter

- schema: be-a-god.entity-card.v1
- id: CHAR-0002
- kind: character
- public_name: Tavin the Grain Counter
- branch_id: main
- status: wandering
- attention: normal
- summary: A careful clerk whose ledgers can feed the town or expose theft.
- location: LOC-002
- x: 31.0
- y: 31.0
- level: region
- source: demo-world

## Public state

Tavin counts jars under a red awning and avoids looking at the river.

## Model semantic draft

The language model may generate or revise this section; the script only stores it.

```json
{
  "desire": "prove the granary losses are not his fault",
  "fear": "a public accusation before the flood audit",
  "misunderstanding": "thinks Mira wants to seize grain transport fees",
  "resources": [
    "ledger tablets",
    "two guards",
    "access to sealed grain rooms"
  ],
  "relationships": {
    "CHAR-0001": "rival",
    "CHAR-0003": "ritual superior"
  },
  "secret": "his assistant falsified one delivery to feed refugees",
  "god_view": "He responds to evidence, not intimidation."
}
```


## Queued event update

第一次洪水钟时，塔文将配粮记录公开刻在市场柱上，并与米拉共同组成临时河粮议席。


## Interaction update

塔文确认未入账救济粮的存在，并要求所有审问和账目核验公开进行。


## Interaction update

河粮议席完成首次公开审理：责任人被撤销配粮权，难民名册开始补录，第二次审计已成为公开承诺。

## Wandering log

- wandered_at: 2026-08-14T17:38:00.658477+00:00
- from: LOC-001
- to: LOC-002
- mode: random
- note: world tick wandering
