# OPS_CI — 최신 suite와 CI Draft의 대조

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

정확한 통합 후보 SHA, 고정 SHA 리뷰, 전달 artifact와 사람 절차는 격리 실행 이후 아래에 기록한다.
