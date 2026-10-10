# OPS_CI — 최신 suite와 CI Draft의 대조

**역사적 OPS_CI task 기록.** ONE-SHOT의 현재 source는d8099f0…, CI 검토 후보65b2573…이며
[hosted133 실행](https://github.com/shotgun1107/home-dev-ops/actions/runs/38031284245)을 확인했다.
최신 전달/사람 통합 순서는 [현재 제안](proposals/README.md)·[E21](EVIDENCE.md#e21-one-shot-통합-검증)을 따른다.
아래115개·5d7d1e1…·원격21개와 후속 독립 보강125개/8045543… bundle은 당시 고정 기록이다.
현재 적용 후보나 hosted 대기 상태로 읽지 않는다.

2026-10-10 KST. 범위는 home-dev-ops의 합성 시험과 CI 제안이다.
기존 PR #1 Worktree의 Supervisor만 쓴다. Kerbe, 운영 서비스, 권한·인증·보호 설정은 변경하지 않는다.

## 확인한 차이

| 대상 | 실제 조회·실행 결과 |
|---|---|
| PR #1 시작 | `44a8fa593310d11d5d4d2de045e4f3ac54926555`, clean, open/Draft, Python 97개 |
| CI PR #2 | `f069ac35b0553f69f0a485784df0bc4f11341f1b`, open/Draft, workflow 1개만 추가 |
| 과거 CI | [run 37941584724](https://github.com/shotgun1107/home-dev-ops/actions/runs/37941584724), 2026-10-09 14:05 UTC, Python 3.12.15의 21개 성공 기록 |
| PR #2 API base | `73afc54ba6ba046ad5f527c08d77fd3a20ce2a58`; 실제 PR #1 branch ref는 위 44a8… |
| PR #2 merge ref | `1f95e837edc2c8b2d20372740e908f1f01052cfe`, 부모는 73afc54…와 f069ac3…; 최신 PR #1을 포함하지 않음 |
| K12 전용 Node | heartbeat 38개 + PID 9개. 설치 Paseo 소스/hash에 의존하므로 GitHub-hosted Python 검사에는 미포함 |

처음 격리 clone을 만들 때 merge ref가 최신 base를 포함할 것이라는 assertion이 실패했다.
그 시도에서는 시험을 실행하지 않았다. 같은 task-owned clone에서 44a8…를 정상 local merge한
`26c5cc1442013a9985e324770758f3a229f662f0`에서 기존 workflow의 unittest 명령을 실행해
Python 3.14.4 **97개, 실패/skip 0**을 확인했다. 이 local Git merge는 GitHub PR merge가 아니다.
3.12 현재 suite 실행과 최신 GitHub CI 성공을 주장하지 않는다.

기존 두 파일 존재 검사는 실행 개수를 보장하지 않는다. 두 빈 파일은 현재 3.14.4에서
`Ran 0 / NO TESTS RAN`, exit 5로 실패했다. 0개 false-green이라는 최초 가설은 이 환경에서 기각했다.
반면 두 파일 중 하나에 성공하는 합성 시험 하나만 남기면 존재 검사와 unittest 모두 exit 0이었다.
3.12에서 이 축소 사례를 실행한 증거는 없다.

## 개선 후보와 범위

- `scripts/run_ops_ci.py`와 `tests/ci-manifest.json`: Python 파일 목록·실제 수집 개수·고유 test ID를 대조한다.
  import 실패, 누락/추가/중복, 개수 차이, skip/expected failure, 실행 실패, source/test byte 변화를 실패 처리한다.
  run ID·시각·Python·checkout SHA·파일 hash와 실행 수를 남기고 외부 guard override를 거부한다.
- 신규 합성 18개는 위 실패와 provenance를 disposable child Python에서 확인한다.
  manifest의 후보 총수는 기존 97 + 신규 18 = **115개**다. fixture 내부 실패는 바깥 regression의 예상 결과다.
- K12 전용 `.mjs` 파일도 목록에 명시하되 실행하지 않는다. 그 47개를 Python CI 통과 수에 합치지 않는다.
  suite/manifest 동시 변경은 리뷰 대상이며 manifest는 악의적인 테스트 코드를 막는 보안 경계가 아니다.
- [workflow 갱신 patch](proposals/home-dev-ops-ci-refresh.patch)는 PR #2의 workflow blob을 기준으로 한다.
  실제 workflow 파일은 격리 clone에만 적용한다. 일반 ops branch에는 활성 `.github/workflows`를 추가하지 않는다.
- 후보는 ubuntu-24.04, CPython 3.14.4, 5분 job/120초 시험 상한을 쓴다.
  K12 실측 Python과 버전을 일치시키며, 이 변경은 3.12 호환성을 보증하지 않는다.
  [공식 배포 manifest](https://github.com/actions/python-versions/blob/main/versions-manifest.json)의
  blob `6e449c983a836ebb17364e5225798bd8b160b647`에서 3.14.4 Linux x64/24.04 배포를 확인했다.
  OS/Actions 서비스 동작은 별도 실제 hosted run이 필요하다.
- checkout v7/setup-python v6의 기존 full SHA pin, `persist-credentials: false`, `contents: read`를 유지한다.
  `pull_request_target`, self-hosted runner, credential·서비스 연결은 추가하지 않는다.

## 원격 적용 판단

private ops repo의 main protection/rulesets GET은 모두 403(Pro/public 필요), 활성 pre-push guard는 없다.
현재 Supervisor Full Access의 merge 차단도 미검증이다. task branch push 자체의 API 거부를 본 것은 아니다.
이 보호 공백과 v2.4 15장의 workflow 별도 사람 적용 경로를 고려해 **원격 workflow 갱신은 보류**하고,
사용자가 허용한 정확한 사람 적용 제안 경로를 수행한다. ops 보고·합성 코드 branch의 기존 예외는 유지한다.
보호 설정을 변경하거나 광범위한 권한을 요청하지 않는다.

GitHub [pull_request 문서](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#pull_request)에 따르면
기본 checkout/GITHUB_SHA는 PR merge ref를 쓴다. 따라서 head SHA, 실제 base ref, merge 부모, 실행 SHA를 함께 기록한다.
base가 진전됐다고 과거 green을 승계하지 않는다. 새 candidate/head push 후에도 실제 새 run의 merge tree·suite 수를 확인해야 한다.
권한은 [workflow permissions 문서](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#permissions)의
명시적 `contents: read`를 유지한다.

## 고정 후보의 실측과 전달

| 구분 | 정확한 값·판정 |
|---|---|
| ops source | `ad3acae8d0f420c9deab7567d3d100881dbc68b0` |
| 통합 candidate | `5d7d1e1177c5a1991582bee7113d239dda01fe83` |
| candidate 부모 | `acce8c92e43d8ba527118cd6291768db1d0d5767` + `ad3acae8d0f420c9deab7567d3d100881dbc68b0` |
| workflow blob | `bd24fba430a97ea5dee3c29fb1370eea970fb131` |
| 동일 scripts tree | `4ccdd57afb52c6efbe37a69b0fc9b051338b51dd` |
| 동일 tests tree | `9e5794abc0d09f229f249a7333fb0b15209b5f98` |
| 동일 docs tree (source commit 기준) | `472c1252089b5f560b8266e1fc79ef5fe1c6d039` |
| 실행 | `timeout 120s python -I -B scripts/run_ops_ci.py`, local Python 3.14.4, 115 passed / 0 skip / 0 error |
| run ID | `2eacb78e-520b-4c03-8fff-74aeb44b8308` |
| 시각 | `2026-10-09T20:40:48.766067+00:00` → `2026-10-09T20:40:50.464805+00:00` |
| 전후 | scripts/tests hash 동일, candidate clean, 실제 hosted CI 미실행 |

source와 candidate의 전체 tree 차이는 workflow 하나다. [선별 영수증](evidence/ops-ci-validation.json)에
115개 case ID·파일 hash·stdout/stderr hash·이전97개·실패 가정·PR/API·보호 조회를 보존했다.
Node38+9는 기록된 설치 소스/harness/patch hash 전부 일치로 재사용했다. 새 실행 횟수로 세지 않는다.

[전달 bundle과 사람이 적용할 정확한 절차](proposals/README.md)는 source와 candidate를 모두 보존한다.
2472-byte bundle을 별도 task-owned clone에 import해 candidate full SHA를 복원했다.
f069ac3…가 candidate의 조상이므로 원격 상태가 그대로라면 force 없는 task branch push가 가능하다.
후속 보고 commit은 문서/증거만 바뀌며 이 표의 source/tests 실행 근거를 승계한다.
source가 진전되거나 remote PR #2가 움직이면 해당 동등성부터 다시 확인한다.

## 독립 리뷰와 남은 결정

기존 Claude Opus 5.5 Plan reviewer가 위 두 full SHA를 읽기 전용으로 검토했다.
[원문 대리 게시·GET 확인](https://github.com/shotgun1107/home-dev-ops/pull/1#issuecomment-6088962998) 결과는 Critical/High/Medium0, Low1, Info2다.
Low1은 초기 source commit의 빈 후속 증거 문단이었고 위 정확한 SHA·tree·bundle·절차로 보완했다.
Info의 patch trailing space는 unified diff가 빈 context 행을 나타내는 형식이다.
`git apply --check --reverse`로 실제 후보와 patch의 대응을 확인했고 context space를 제거하지 않았다.
다른 Info는 manifest 동시 변경의 리뷰 책임과 hosted 환경 미검증으로, 그대로 한계에 기록한다.
reviewer는 시험을 실행하지 않았으며 Plan mode의 기술적 readonly를 보증하지 않는다.

**이번 safe fallback 산출물:** 최신 suite 대조·실패 주입·개선·고정 후보 검증·복원 가능한 제안.
**미완료:** 보호 공백에 대한 사람 결정, 원격 CI branch 적용, 실제 새 hosted run, 필수 검사/main 채택.
AI Ready/Merge/main push·권한/보호 변경·Kerbe 수정은 하지 않았다. P0 전체 또는 P1 전체의 완료 선언이 아니다.

후속 고정 SHA `3d68f76e456f03f423533b02642117705770a1b6`의 [독립 delta 원문](https://github.com/shotgun1107/home-dev-ops/pull/1#issuecomment-6089010542)은
Low1 해소·새 Low 이상0·Info1이다. Info의 bundle 경로는 위 보고 commit이 checkout된 별도 검토 clone 기준으로 명시했다.
최종 후속 변경은 문서/리뷰 영수증뿐이며 source/tests/manifest/workflow/patch/bundle bytes는 검증·리뷰 당시와 같다.
