# CI 적용 제안 — ONE-SHOT 최신 검증 후보

2026-10-10 KST. 기존 [CI PR #2](https://github.com/shotgun1107/home-dev-ops/pull/2)를 유지해
최신 ops source와 통합했다. **task branch 전달·hosted 검증까지 수행했고 Ready/PR merge/main 채택은 사람 결정이다.**
최종 보고 문서 통합 뒤의 정확한 PR #1/#2 HEAD와 run은 [PR #1 최종 handoff](https://github.com/shotgun1107/home-dev-ops/pull/1)를 따른다.

| 검토·실측한 고정 후보 | 값 |
|---|---|
| ops source/tests | `d8099f00188ffd35c9cec87b83d370c41c536a17` |
| CI workflow 고정 리뷰 후보 | `65b2573ac39199a22e65d02f27d3dbd4cd196032` |
| 이전 CI head / 정상 ancestry | `0bef44431f52ae1c24aec77b2c655e80ba03ed72` → merge `23f662c309f42416031fce5cfd2a0836cc368e6d` → 위 후보. force/rewrite 없음 |
| 실제 hosted | [38031284245](https://github.com/shotgun1107/home-dev-ops/actions/runs/38031284245), Python3.14.4 **133 executed / skip0 / failure0 / error0**, 동일 runId finish·filesUnchanged·passed |
| 실행 checkout | `bb132130040c82665d8a7ca1bcd29bd2df24fd39`, 부모 d8099f0… + 65b2573…, CI 후보와 tree 동일 |
| 처음 대조한125 hosted | [38029622244](https://github.com/shotgun1107/home-dev-ops/actions/runs/38029622244), head0bef444… / checkout0dcfeff… / 125개. 이번133과 분리 |
| 별도 K12 시험 | Heartbeat40 새 실행, 설치 PID9·mock15 hash 재사용. hosted133에 합산하지 않음 |
| evidence | [선별 실행·source hash·리뷰](../evidence/one-shot.json), [추가 시험 원문 리뷰](https://github.com/shotgun1107/home-dev-ops/pull/1#issuecomment-6094678310) |

source 대비 전체 차이는 workflow 한 파일이다. 원래 checkout/setup pin·pull_request·contents:read·
persist-credentials:false·ubuntu24.04·Python3.14.4·job5분/명령120초/child110초는 유지했다.
workflow 수정은 step의 고정125 표시를 `manifest-verified suite`로 바꾼 한 줄이다.
실행 수는 문구가 아니라 manifest/실제 discover/종료 receipt가 강제한다.
[고정65b2573 workflow delta 리뷰](https://github.com/shotgun1107/home-dev-ops/pull/2#issuecomment-6094699772)는 새 P0/P1/P2가 없었다.
계정·토큰·보호·공통 hook은 바꾸지 않았으며 새 CI Worktree/PR도 만들지 않았다.
기존 task-owned clone의 clean/소유권/ancestry를 확인하고 같은 CI branch를 사용했다.
별도 과거 delivery-check clone의 dirty 상태는 그대로 보존했다.

## 최신 후보의 사람 적용 절차

1. [Git 보호 선택](../ADOPTION.md#b-git-보호-선택과-정확한-적용-순서)과 사용할 기본 writer 경계를 결정한다.
   현재403/no-hook/Full Access 미검증을 해결·상시 수용으로 간주하지 않는다. CI 채택은 보호 설정 적용과 별개다.
2. PR #1/#2 최신 full HEAD·Draft·base·check를 GET으로 다시 읽고 최종 handoff와 대조한다.
   old bundle을 현재 head에 push하지 않는다. base/head가 바뀌면 source/manifest/workflow 차이부터 검토한다.
3. 권장 검토 순서는 **사람이 PR #2를 PR #1의 docs branch로 통합 → PR #1의 main 대비 CI 확인 → 사람이 PR #1 main 채택**이다.
   사람의 Ready/merge 전 최신 GitHub checkout/부모·suite/skip·완료 영수증을 확인한다. main 직접 push는 사용하지 않는다.
4. PR #2 통합 후 PR #1이 실제 main merge checkout에서 같은133개/skip0·정상 finish를 통과했는지 확인한다.
   PR #2의 성공만으로 main 통합 성공을 주장하지 않는다. source가 바뀌면 숫자를 억지로 유지하지 않고 새 리뷰·시험을 한다.
5. 실제 main에서 workflow/검사 이름이 확인되고 서버 보호 기능을 사용할 수 있을 때만 사람이 required check를 설정한다.
   check context 이름·strict/bypass를 다시 확인한다. 존재하지 않는 검사나 과거21개 green을 필수검사로 채택하지 않는다.
6. push/API/CI 실패면 local commit과 실제 원격 SHA·오류를 보존하고 원인을 확인한다. force/reset/권한 확대/직접 main 반영은 하지 않는다.
   이미 통합한 변경의 원복은 영향 검토한 새 task PR로 사람이 결정한다. 자동 보호 완화나 배포 rollback은 포함하지 않는다.

후속 보고 commit은 문서·증거뿐인지 diff로 확인한 뒤 기존 CI branch에 정상 merge하고 최종 hosted run을 다시 확인한다.
최종 HEAD와 이미 리뷰한 workflow/source SHA가 다르면 동일 bytes와 문서 delta를 함께 적는다.
리뷰는 Claude Plan의 운영상 읽기 전용이며 기술적 sandbox가 아니다. 실제 읽은/재사용한 범위는 원문에 있다.

## 과거 bundle과 patch 보존

아래는 과거 전달 후보이며 **현재 적용 대상으로 push하지 않는다**. 파일·Git 이력은 보존했다.

- `80455437960f3db0cbec5f1f3df0392ad47def3c`: [125개 bundle](ops-ci-reviewed-candidate.bundle),
  SHA256 `076a4de9fe76eaa5c8b08603f36d96d31d11081f04d7e69b782f2565f9f0dcd9`.
- `5d7d1e1177c5a1991582bee7113d239dda01fe83`: [115개 bundle](ops-ci-candidate.bundle),
  SHA256 `0066ff185ffb808ab472ea928065b8b27600810ce278ed461694afaff4f62ce6`.
- [최초 patch](home-dev-ops-ci.patch), [과거 refresh patch](home-dev-ops-ci-refresh.patch)는 당시 기준의 제안이다.
  patch만으로 최신 source/manifest가 따라오지 않는다.
- [이전 전달 문서와 prerequisite](https://github.com/shotgun1107/home-dev-ops/blob/7ae69a92e3e6f8462ec1a6446fe31bb48294bd63/docs/k12-paseo/proposals/README.md)·
  [OPS_CI 역사](../OPS_CI.md)·[독립 보강](../INDEPENDENT_REVIEW.md)은 당시 실측을 확인하는 자료다.
