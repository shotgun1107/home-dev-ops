# CI 적용 제안 — OPS_CI 갱신 후보

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
2. bundle SHA-256과 prerequisite를 검증한다. 비어 있는 새 local review ref로 import한다.
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
