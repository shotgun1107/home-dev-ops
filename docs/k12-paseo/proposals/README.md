# CI 적용 제안 — 별도 Draft PR 실행 확인

v2.4 15/18장에 따라 workflow는 일반 agent 작업 branch의 .github/workflows에 commit하지 않았다.
[patch](home-dev-ops-ci.patch)는 현재 후보의 두 unittest 파일을 검사하는 작은 제안이다.
기준 Git HEAD는 `2873a57a804c96225b774bc1c9f86dae87628db3`이며 이후 변경은 이 PR에서 확인한다.

- 최초 제출 당시에는 patch 형식/YAML 검사만 완료했다. 이후 사람 허용에 따른 별도 [CI PR #2](https://github.com/shotgun1107/home-dev-ops/pull/2)가 생성됐다.
- Python 3.12 / GitHub-hosted Ubuntu / 5분 상한 / contents:read / checkout credential 보존 끔.
- unittest 두 파일의 존재를 검사해 테스트 없는 branch에서 0개 검사로 성공하는 것을 막는다.
- K12 자체 호스트·운영 서비스·비밀정보를 사용하지 않으며 배포/merge/외부 게시 작업이 없다.
- actions/checkout v7과 actions/setup-python v6의 full SHA는 2026-10-09 GitHub refs GET으로 확인했다.
  [checkout](https://github.com/actions/checkout), [setup-python](https://github.com/actions/setup-python)의 공식 사용법을 대조했다.

2026-10-09 조회한 관계:

| 대상 | base | head / 실행 결과 |
|---|---|---|
| 운영 PR #1 | main `bf50f2bdb44e4d71fc29b31dcb0629719a345a95` | 재개 시 `73afc54ba6ba046ad5f527c08d77fd3a20ce2a58`, checks 없음 |
| CI PR #2 | PR #1의 `docs/k12-paseo-autopilot`, 당시 `73afc54…` | `f069ac35b0553f69f0a485784df0bc4f11341f1b`, 추가 파일은 workflow 하나 |
| CI run 37941584724 | 위 PR #2 기준 | CPython 3.12.15, 21 tests OK, success |

[실제 로그·workflow hash](../evidence/issue-3-resume.json)는 제안 patch와 byte 일치함을 확인한다.
PR #1 작업 branch가 진행하면 기존 CI run 당시 base와 달라진다. API `.base.sha`가 과거 값을
반환할 수도 있으므로 실제 branch ref도 조회한다. 이전 run이 새 통합 상태를 검증했다고 쓰지 않는다.
cleanup 도구의 최초 7개·리뷰 반영 후 9개 추가 시험까지 포함한 30개는 로컬 통과이며, 위 CI에는 21개만 포함됐다.

두 PR은 Draft/open이다. main에는 workflow가 없고 `ops-check`가 main의 필수 검사로 설정된 증거도 없다.
사람은 CI PR을 최신 PR #1 base와 대조하고 새 통합 SHA에서 CI를 확인한 뒤 task branch에 채택할지,
운영 PR 채택 뒤 CI PR의 base를 main으로 다시 정할지 결정한다. 어느 경로든 base 변경 후 새 CI가 필요하다.
CI PR 통합·Ready·main 반영은 사람이 수행한다. agent는 workflow나 보호 설정을 변경하지 않았다.
패치 전문과 원문 대리 게시 기록도 PR #1에 보존한다.
