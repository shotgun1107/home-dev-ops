# CI 적용 제안 — 독립 리뷰 후 최신 후보

2026-10-10 KST. [REVIEW_INDEPENDENT](../INDEPENDENT_REVIEW.md)의 보정 후 후보가 최신이다.
기존 workflow bytes는 유지하고 suite의 조기 exit0·파일 입력 검사를 보강했다.
**원격 적용은 사람 결정 대기다.** 이 문서는 AI Ready/Merge/main push 또는 설정 변경 승인이 아니다.

| 최신 전달 대상 | 정확한 값 |
|---|---|
| ops source | `1edd2ef4702031dd6fe2d59adc01e4504c5c57db` |
| CI 통합 후보 | `80455437960f3db0cbec5f1f3df0392ad47def3c` |
| 유지된 PR #2 head | `f069ac35b0553f69f0a485784df0bc4f11341f1b` |
| [새 bundle](ops-ci-reviewed-candidate.bundle) | 3269 bytes, SHA256 `076a4de9fe76eaa5c8b08603f36d96d31d11081f04d7e69b782f2565f9f0dcd9` |
| bundle ref | `refs/heads/ci/ops-ci-independent-review` |
| 실제 local 검사 | `timeout 120s python -I -B scripts/run_ops_ci.py`, Python3.14.4, **125개 OK / skip0** |
| 미실행 | 최신 GitHub-hosted run·Ready·merge·main 필수 검사 채택 |

새 후보의 source 대비 전체 tree 차이는 `.github/workflows/ops-check.yml` 하나다.
workflow는 과거5d7d1e1…와 동일하다. PR #2 f069ac3…가 조상이며 별도 clone에서 새 bundle
verify/import·같은 full SHA 복원을 확인했다. prerequisite는 f069ac3…,73afc54…,ad3acae…,
44a8fa5…,0c91fd9…,1edd2ef…의 full object이며 [영수증](../evidence/independent-review.json)에 모두 있다.
이는 PR #1/#2 이력을 가져온 clone을 위한 bundle이며 단독 완전 백업이 아니다.

## 최신 후보의 사람 적용 절차

1. 보호 공백/guard·workflow 적용 경로를 사람이 결정한다. 별도 검토 clone에서 PR #1과
   `ci/k12-ops-check`를 fetch한다. PR #2의 실제 remote head가 위 f069ac3…인지 확인한다.
   움직였으면 새 base에서 다시 검토하고 force/reset으로 맞추지 않는다.
2. **PR #1 최신 handoff에 적힌 최종 보고 HEAD를 그 clone의 새 local branch에 checkout**한다.
   그 commit에 최신 bundle이 있어야 한다. source commit checkout에는 이전 bundle만 있거나 없을 수 있으며 fetch만으로 working tree 파일은 갱신되지 않는다.
   위 SHA256을 대조하고 `git bundle verify docs/k12-paseo/proposals/ops-ci-reviewed-candidate.bundle`을 실행한다.
3. 아직 없는 local ref로 가져온다:
   `git fetch docs/k12-paseo/proposals/ops-ci-reviewed-candidate.bundle refs/heads/ci/ops-ci-independent-review:refs/heads/review/ops-ci-8045543`.
   같은 ref가 이미 있으면 SHA를 먼저 비교한다. `git rev-parse review/ops-ci-8045543`의 full SHA와
   `git merge-base --is-ancestor f069ac35b0553f69f0a485784df0bc4f11341f1b review/ops-ci-8045543`의 exit0을 확인한다.
4. 고정 SHA의 source/manifest/workflow와 독립 리뷰를 확인한다. 사람이 채택한 경우에만 정상 task push:
   `git push origin 80455437960f3db0cbec5f1f3df0392ad47def3c:refs/heads/ci/k12-ops-check`.
   거부되면 실제 ref/오류를 재대조한다. force·권한 확대는 하지 않고 PR #2 Draft를 유지한다.
5. 새 hosted run에서 실제 base ref·merge 부모·checkout SHA·source/test hash와
   **125 executed / skip0 / failure0 / 동일 runId finish / pass**를 확인한다. 테스트 source/manifest가
   달라졌으면 이 숫자를 강제하지 말고 새 변경을 리뷰한다. 후속 PR #1 보고 diff가 문서뿐인지도 확인한다.
   과거21개 hosted·115개 local·이번125개 local을 새 hosted 성공으로 대체하지 않는다.
6. 필요한 검사 후 PR 통합 순서·Ready/main 채택은 사람이 별도로 결정한다.

직전125개 후보a143652…의2874-byte bundle은 보고 commit
`c0d2cd0d7d1f38bc8746cacd6baed9fbc8435a2e`에 보존했다. 최신 후보는 대용량 record의
오류 구분·보존 subcase를 추가한 뒤 같은125개를 다시 통과했다. 자동 대용량 삭제를 지원한 변경은 아니다.

## 과거 OPS_CI 기록 — 115개 후보 보존

아래5d7d1e1… bundle과 당시 절차는 재현/역사 확인용이다. 현재 최신 적용 후보로 선택하지 않는다.

2026-10-10 KST. [OPS_CI 실제 대조·시험](../OPS_CI.md)을 먼저 읽는다.
[PR #2](https://github.com/shotgun1107/home-dev-ops/pull/2)는 여전히 open/Draft,
`f069ac35b0553f69f0a485784df0bc4f11341f1b`이며 실제 hosted CI는 과거 **21개** 성공뿐이다.
이전 30개는 당시의 로컬 기록이다. 이번 시작 suite는 Python **97개**, 개선 후 **115개**이며
K12 설치본에 의존하는 Node **47개**는 별도 증거 재사용이다.

원본 [home-dev-ops-ci.patch](home-dev-ops-ci.patch)는 기준
`2873a57a804c96225b774bc1c9f86dae87628db3`의 최초 제안으로 보존한다.
당시 두 파일 존재 검사로 충분하다는 설명은 폐기한다. 두 파일이 존재해도 실행 시험이 하나로
축소되면 성공할 수 있음을 재현했다. Python 3.14.4의 0개 실행 자체는 exit 5로 실패했다.

## 전달 후보

- ops source/manifest/tests: `ad3acae8d0f420c9deab7567d3d100881dbc68b0`.
- 통합 후보: `5d7d1e1177c5a1991582bee7113d239dda01fe83`.
  격리 clone의 local merge이며 GitHub PR merge가 아니다. 기존 PR #2 f069ac3…가 조상이다.
  source SHA와의 전체 tree 차이는 `.github/workflows/ops-check.yml` 하나다.
- [갱신 patch](home-dev-ops-ci-refresh.patch): 기존 PR #2 workflow blob `0846430…` 기준.
  patch만 적용해도 source/manifest가 따라오는 것은 아니다. 최신 source 통합이 선행 조건이다.
  빈 context 행의 한 칸은 unified diff 형식이므로 trailing whitespace 정리로 제거하지 않는다.
  실제 candidate에서 `git apply --check --reverse` 성공을 확인했다.
- [정확한 commit bundle](ops-ci-candidate.bundle): SHA-256
  `0066ff185ffb808ab472ea928065b8b27600810ce278ed461694afaff4f62ce6`, 2472 bytes.
  head ref는 `refs/heads/ci/ops-ci-isolated`; candidate full SHA를 보존한다.
  prerequisite는 f069ac3…, 73afc54…, ad3acae…, 44a8fa5…의 full object다.
  기존 PR #1/#2 branch를 fetch하면 이력을 얻을 수 있다.
- 별도 task-owned clone에서 bundle verify/import 후 동일 candidate SHA,
  PR #2의 ancestor 관계, source/tests byte 일치를 확인했다. 원격 workflow push는 하지 않았다.
- 실제 workflow의 명령을 local Python 3.14.4에서 **115개 OK, skip 0**으로 확인했다.
  K12 임시 `bin/python`은 `/usr/bin/python3`의 task-owned symlink이며 전역 설치/설정 변경이 아니다.
  YAML parse·pin/permission 검사를 했지만 actionlint와 GitHub-hosted 실행은 미실행이다.

## 사람이 선택한 뒤 적용할 순서

보호/guard 미확인과 v2.4 workflow 사람 경로 때문에 이번에는 제안으로 전달한다.
위험 수용·보호 확보 여부, CI 통합 순서, Ready/main 채택은 서로 별도의 사람 결정이다.
아래는 **기존 CI task branch를 갱신하는 선택지**이며 main push/merge 또는 Ready 전환 명령이 아니다.

1. PR #1 최신 handoff의 source/tests와 위 고정 후보·독립 리뷰를 대조한다. 별도 검토용 clone에서
   현재 PR #1과 `ci/k12-ops-check`를 fetch한다. 원격 PR #2 head가 아직 위 f069ac3…인지 확인한다.
   달라졌다면 중단하고 새 이력을 재대조한다. force/reset으로 맞추지 않는다.
2. 아래 repo-relative bundle 경로는 파일을 포함한 PR #1 보고 commit
   `3d68f76e456f03f423533b02642117705770a1b6` 또는 그 후속을 **별도 검토 clone의 새 local branch에서 checkout한 상태** 기준이다.
   fetch만으로 working tree 파일이 생기지는 않는다. 기존 운영 Worktree를 전환하지 않는다.
   그 checkout의 bundle SHA-256과 prerequisite를 검증한다. 비어 있는 새 local review ref로 import한다.
   `git bundle verify docs/k12-paseo/proposals/ops-ci-candidate.bundle`
   이후 `git fetch docs/k12-paseo/proposals/ops-ci-candidate.bundle refs/heads/ci/ops-ci-isolated:refs/heads/review/ops-ci-5d7d1e1`.
   같은 local ref가 이미 있으면 재사용을 추정하지 말고 그 SHA부터 대조한다.
3. `git rev-parse review/ops-ci-5d7d1e1`이 위 full candidate와 일치하는지,
   `git merge-base --is-ancestor f069ac35b0553f69f0a485784df0bc4f11341f1b review/ops-ci-5d7d1e1`이 0인지 확인한다.
   `git show review/ops-ci-5d7d1e1:.github/workflows/ops-check.yml`과 helper/manifest를 검토한다.
4. 사람이 위 경로를 채택한 뒤 **일반 task branch push**만 수행한다:
   `git push origin 5d7d1e1177c5a1991582bee7113d239dda01fe83:refs/heads/ci/k12-ops-check`.
   거부/원격 이동은 새 검토 조건이다. 인증 확대·force로 우회하지 않는다. PR #2 Draft를 유지한다.
5. 새 `pull_request` run의 head, 실제 base ref, merge 부모와 checkout SHA, manifest/hash,
   115 executed / 0 skipped / pass를 확인한다. 과거 run이나 candidate 로컬 성공으로 대신하지 않는다.
   최종 PR #1 보고 commit은 candidate 이후일 수 있으므로 GitHub 합성 merge SHA가 candidate와
   다를 수 있다. 그 차이가 문서/증거뿐인지 확인한다. base 변경 후에도 새 run이 필요하다.
6. 필요한 검사가 통과한 뒤 PR #2→ops task 통합 또는 PR #1 채택 후 CI base 변경 중 하나를
   사람이 선택한다. agent는 어느 PR도 Ready/merge하지 않고 main 필수 검사도 설정하지 않는다.

`pull_request` merge ref 동작과 권한 근거는 [OPS_CI](../OPS_CI.md#원격-적용-판단)에 링크했다.
main에는 현재 workflow/필수 CI가 없으며 이 제안 자체로 P0-C1이 완전히 통과한 것은 아니다.

독립 고정 SHA [리뷰 원문](https://github.com/shotgun1107/home-dev-ops/pull/1#issuecomment-6088962998)과 [보완 내역](../OPS_CI.md#독립-리뷰와-남은-결정)을 함께 검토한다.
