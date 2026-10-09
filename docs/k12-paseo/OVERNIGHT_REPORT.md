# K12 야간 운영 검증 handoff — 2026-10-10 KST

**허용된 격리 감사·개선·문서 전달은 진행했지만 전체 P0/P1은 미완료다.** 운영 설정을 배포하거나
미실행 항목을 통과시킨 보고가 아니다. 기존 Astra Max Supervisor·Director·ops Worktree를 유지했다.
집계 기준 HEAD는 `a332a1b756006cca4851ccd0a52fb3d6e5e220f8`이며 최종 보고 HEAD와 actor 상태는
[Draft PR #1의 마지막 handoff](https://github.com/shotgun1107/home-dev-ops/pull/1)를 따른다.

coordinator 시작은 `2026-10-09T19:20:41.261515Z`(10/10 04:20:41 KST)다.
`22:11:05Z` 조회에서 선행 task 영수증7개 completed·controller failures0, OVERNIGHT_REPORT는 active였다.
이는 task별 제한된 목표의 전달 상태다. 의도한 실패 주입·초기 harness 실패가 없었다는 뜻도,
이 보고의 영수증·controller 종료·root idle이 이미 완료됐다는 뜻도 아니다.
선별 coordinator 기록·receipt hash·과거 handoff GET·원격 SHA·비용 출처는
[보고 증거](evidence/overnight-report.json)에 보존한다. 개인 token 장부·credential·DB는 읽지 않았다.

## 야간 실측과 개선

다음 검사는 해당 task에서 실행한 결과다. **이번 보고에서는 source/hash가 일치하는 증거를 재사용하며
제품·회귀 시험을 반복 실행하지 않는다.** 각 행의 숫자는 서로 중복되므로 더하지 않는다.

| 작업 | 확인한 결과와 개선 | 남은 한계 |
|---|---|---|
| [P0_PERMISSIONS](PERMISSIONS.md) | 승인 전달/결정 주체/실행 결과를 분리. S 입력 조정 누락 보정. 당시 신규38+기존30=68개 OK; 후속 입력 보강으로 permission suite는39개 | Auto-review 실제 결정·Claude 특정 deny/classifier·Full Access 차단 미확인. 응답62건은 사람 클릭/성공62회가 아님 |
| [P0_HEARTBEAT](HEARTBEAT.md) | 설치본 stale tick 중복/늦은 dispatch·append 실패 guard 누수 재현. 미설치 패치 복사본으로 Node38개 통과 | orphan running은 후보에서도 자동 진행 정지. 가상24h·합성 crash 상태이며 실제24h/OS crash/다중 프로세스/exactly-once 미검증 |
| [P0_RECOVERY](FAILURE_RECOVERY.md) | preflight 조회 전후 identity race 보정. handoff 중단·소유권·부작용 재대조를 Python38개(신규29+preflight9), 설치 PID Node9개로 검증 | offline 판정은 lease/실행 승인 아님. 실제 daemon 재시작/GitHub 장애/정전 복구 미실행 |
| [OPS_CI](OPS_CI.md) | 과거 hosted21과 당시 source97의 불일치 확인. inventory/outcome 회귀18개 추가, 격리 workflow115개 통과. 최신 전달 후보는 아래125개 | 원격 CI branch 갱신·최신 hosted 실행·main 필수 검사 채택 없음. 오래된 green은 최신 ops 검증이 아님 |
| [P1_PARALLEL_ISOLATED](PARALLEL_ISOLATED.md) | 만료 우회와 공통 source/cwd 의존 보정. 계약15개 통과, 별도 Git/source/cwd/runtime의 mock 결과2개·commit/clean/child 회수. 최종 lease 겹침 하한20.800057초, B 대기 중 A 완료 | 실제 AI/Paseo Provider가 아닌 Python mock. 전역 writer 상한 강제·Provider 승인 부담·직렬 대비 우위 미측정. 정식 병렬은 M main 선행 때문에 미진입 |
| [REVIEW_INDEPENDENT](INDEPENDENT_REVIEW.md) | `_exit(0)` CI false-green·FIFO 대기·receipt 자료형 보정. 새10개 전후 대조 후 최신125개 OK(skip0). 정상70KB output은 명시적 보존 경로 | 실제 삭제는 fake/injected뿐. CI receipt는 악의적 코드 보안 경계 아님. 대용량 선별 조회/삭제·서버 CAS·모든 child 종료 보장 없음 |
| [DOCS_RECONCILE](EVIDENCE.md#e19-docs_reconcile-현황과-증거-대조) | 과거/현재 판정·125/115/21·cleanup15/9/전체30 정리. 기준 후보의 상대 참조113개·GitHub 참조35개 확인. 고정1de59fd… 문서 delta 새 지적0 | 근사 heading slug 검사이며 브라우저/모바일 검증 아님. Review_History 입력 없음. 설치 경로를 오기로 단정한 중간 오류도 두 실제 사본/hash로 정정·보존 |

실패 이력은 각 보고에 남겼다. CI 조기 종료 반례, FIFO paired harness45초 timeout,
JSON-depth 오류명 기대 차이, mock 만료·source/cwd 보정, gh2.46.0의 미지원 `--slurp` 등을
운영 정책 실패·daemon 장애·권한 거부와 구분했다. 근거 없는 재시도나 설정 완화는 없었다.

## 정확한 전달 SHA와 원격 상태

| 역할 | 고정 값 / 적용 상태 |
|---|---|
| 최신 검증 구현 source | `1edd2ef4702031dd6fe2d59adc01e4504c5c57db` |
| 최신 격리 CI 후보 | `80455437960f3db0cbec5f1f3df0392ad47def3c`; source 대비 workflow 한 파일만 차이 |
| 최신 CI bundle | `ops-ci-reviewed-candidate.bundle`,3269 bytes, SHA256 `076a4de9fe76eaa5c8b08603f36d96d31d11081f04d7e69b782f2565f9f0dcd9`; [정확한 전달/적용 절차](proposals/README.md) |
| 최신 실제 local run | `2318a21f-4f8f-49ba-827b-c183e40dce6e`, 종료 `2026-10-09T21:41:22.131355Z`, Python3.14.4, `timeout 120s python -I -B scripts/run_ops_ci.py` |
| local 검사 inventory | **125 executed / failure0 / error0 / skip0** = guard12 + preflight9 + cleanup15 + permission39 + recovery29 + test_ops_ci21. Node38+9와 mock15는 별도 증거이며125에 합산하지 않음 |
| ops PR #1 / main | 조회 기준 PR #1 a332a1b… open/Draft·check-runs0. 실제 main `bf50f2bdb44e4d71fc29b31dcb0629719a345a95`, protected=false |
| [ops PR #2](https://github.com/shotgun1107/home-dev-ops/pull/2) | `f069ac35b0553f69f0a485784df0bc4f11341f1b` open/Draft. API base73afc54…는 최신 ops branch와 다름. 유일한 [hosted run37941584724](https://github.com/shotgun1107/home-dev-ops/actions/runs/37941584724)은 과거21개 성공 |
| [Kerbe S PR #4](https://github.com/shotgun1107/kerbe/pull/4) | 후보 `f0f73a87821a6b3d990142b948d13c7e2b6e067d`, 사람 squash merge/main `efd539a6ab5cd05a2c7f33cf3b8db13c021458be`. S 완주 근거는 [E11](EVIDENCE.md#e11-s-main-반영과-m-진입) |
| [Kerbe M PR #5](https://github.com/shotgun1107/kerbe/pull/5) | `7ff930cefd308c37702aff7c7efd48fc4c9e4c9b` open/Draft·2 checks success·main 미반영. 로컬22/전체185(skip2)·wheel, CI185(skip1/2), 독립 P2 해소는 [E12](EVIDENCE.md#e12-m-같은-worktree의-claude--codex-복원) 재사용 |
| [Kerbe bootstrap PR #2](https://github.com/shotgun1107/kerbe/pull/2) | `1a02ad66780604909d49044ddfe14c803b0332f9` open/Draft·main 미반영, M/S 후보와 별개 |

원격 표는 `2026-10-09T22:12:08Z`부터 시작한 순차 GET이다. API의 unmerged PR `merge_commit_sha`는
시험 merge 정보일 수 있어 main 채택 근거로 쓰지 않는다. combined pending·status contexts0도
실행 대기 증거가 아니다. Kerbe는 GitHub metadata만 읽었으며 회사 로컬 변경·checkout/branch를
조회·수정·fetch하지 않았다. 회사 미동기화 변경에 기존 후보의 검증을 확대하지 않는다.

각 야간 task의 보고 HEAD는 다음과 같다. 실제 구현/시험 SHA와 보고 SHA를 구분한다.

| task | 당시 최종 보고 HEAD | GitHub handoff |
|---|---|---|
| P0_PERMISSIONS | `a29f66e0a676afb0e621f5942a696152e87b181f` | [기록](https://github.com/shotgun1107/home-dev-ops/pull/1#issuecomment-6088008156) |
| P0_HEARTBEAT | `243ecdffa65992b661184560ed2d5932739262ba` | [기록](https://github.com/shotgun1107/home-dev-ops/pull/1#issuecomment-6088366661) |
| P0_RECOVERY | `44a8fa593310d11d5d4d2de045e4f3ac54926555` | [기록](https://github.com/shotgun1107/home-dev-ops/pull/1#issuecomment-6088705504) |
| OPS_CI | `646ffd91d5eab7213f14a079415d53d327374a4b` | [기록](https://github.com/shotgun1107/home-dev-ops/pull/1#issuecomment-6089051704) |
| P1_PARALLEL_ISOLATED | `81e1547da5f7d6579471ad1f8f4c8b5fa3269c4e` | [기록](https://github.com/shotgun1107/home-dev-ops/pull/1#issuecomment-6089394906) |
| REVIEW_INDEPENDENT | `7b321124a79d1413c62dfb0ee398d784b6fb0568` | [기록](https://github.com/shotgun1107/home-dev-ops/pull/1#issuecomment-6089830356) |
| DOCS_RECONCILE | `a332a1b756006cca4851ccd0a52fb3d6e5e220f8` | [기록](https://github.com/shotgun1107/home-dev-ops/pull/1#issuecomment-6090069590) |

최종 mock A `362c9674711699e00debf75fb1e6d192f98c5afe`와 B
`6bc663e16b09d313fa1cc5720783aaef3aa94efe`는 원격 없는 각 임시 저장소의 local commit이다.
GitHub 결과 두 개나 Kerbe의 채택 commit으로 기록하지 않는다.

## 승인·개입 횟수

| 집계 범위 | 실제 확인 수치 | 해석 |
|---|---|---|
| 기존 S Claude 선별 응답 | allow9 / deny1 / allow 중 input adjustment3 | 과거 S 기록 재사용 |
| 기존 M Claude 선별 응답 | allow16 / deny2 / allow 중 adjustment3 | 과거 M 기록 재사용 |
| 기존 M Codex 선별 응답 | allow34; deny/adjustment 관찰 없음 | 없음이 전수0건의 증거는 아님 |
| S/M 선별 합계 | 응답62 = allow59 + deny3, 조정6은 allow의 부분집합 | Supervisor 응답이며 사람 클릭62·성공62·야간 신규 승인62가 아님. [근거](PERMISSIONS.md#승인-집계와-실제-결함-수정) |
| 야간 parallel mock | 세 순차 round 각각2, 총 **수동 결정6건 allow** | full writer/request/task ID와 operation hash를 root가 개별 검토. 실제 Paseo permit/Provider 승인/사람 클릭 아님. 자동 unit fixture 응답 제외 |
| M 실행 중 개입 | Supervisor 메시지로 허용 후 실행 중단1건, 업무 맥락 사용자 재설명0회 | deny에 중복 가산하지 않음. 교대 단계·승인 개입은 있었으므로 무인 완주가 아님 |
| 야간 전체 실제 Provider 승인·사람 클릭 | **전수 합계 미확인** | 선별 S/M 기록·mock6·pending0 스냅샷을 더해 만들지 않음. 전체 permission-event 집계를 별도 수집하지 않았음 |

현재 root Full Access의 승인창 부재는 auto-review 통과 근거가 아니다. 모든 위험 범주·영구 허용·
mode/updatedPermissions 변경은 이번 승인 대상에서 제외했다. 앞으로도 full ID별 요청 내용·실효
권한·부작용을 검토하고 응답과 실제 실행 결과를 분리한다.

## 비용과 집계 공백

아래는 `2026-10-09T22:11:05Z`(07:11:05 KST), **이 보고의 독립 리뷰 이전** agent inspect 스냅샷이다.
인증·청구 장부에 접근하지 않았으며 가격표로 환산하지 않았다.

| agent / 모델 | CLI CostUsd | 확인 가능한 의미 |
|---|---:|---|
| Supervisor c9bb4cb7… / Astra Max | 0 | 설치 Codex usage 변환은 last token만 전달하고 totalCostUsd를 제공하지 않음. CLI가 미제공 비용도0으로 표시하므로 비용0·무료로 판정할 수 없음 |
| Director e2f92291… / Astra Max | 0 | 같은 한계. 야간 controller 비용 미확인 |
| reviewer b8e68af1… / Claude Opus5.5 | 26.535271999999992 USD(표시 약26.535272) | Claude result의 total_cost_usd 전달값. 기존 세션 재사용·야간 시작 비용 기준값 부재로 야간 전용 합계/실청구액/이번 보고 비용으로 귀속할 수 없음 |
| **전체 야간 비용** | **미확인** | 위 값을 합산하거나 Codex를0으로 처리하지 않음 |

설치 CLI는 `snapshot.lastUsage.totalCostUsd ?? 0`을 출력한다. agent-manager는 usage_updated에서
lastUsage를 대체하고 turn_completed에서 병합하므로 LastUsage 자체가 task별 누적 장부는 아니다.
Codex 입력/출력도 `usage.last`에서 가져온다. token 스냅샷들을 더해 야간 합계를 만들지 않는다.
설치 소스4개/5개 행 범위와 SHA256을 증거에 보존했다. 이는 정적 매핑 확인이며 청구 정확성 시험이 아니다.

다음 비용 계측은 같은 agent/session·task 경계의 시작/종료 값과 비용 필드의 제공 여부·집계 단위를
먼저 기록해야 한다. Provider별 누적/턴 의미와 reset/재개를 검증한 뒤에만 차액을 귀속한다.
필드 미제공을0과 구분하는 표시 개선은 별도 후보이며 이번에 CLI/config를 변경하지 않았다.
이 보고 리뷰 이후의 새 스냅샷은 최종 PR handoff에 추가하며 과거 수치를 덮어쓰지 않는다.

## 남은 결정과 다음 안전한 행동

1. **ops 기본 경로 보호:** private 보호 API403·hook 미설치·Full Access 차단 미검증이 남아 있다.
   사람이 [보호 선택지](REVISION.md#ops-보호-공백의-선택지--사람-결정)와 공통 hook/LFS 영향·기본 writer
   범위를 선택한다. branch GET protected=false를 보호 통과로 바꾸지 않는다. 현재 허용된 문서·격리 분석은 계속 가능하다.
2. **CI 적용:** 보호/워크플로 적용 경로 결정 후 정확한8045543… bundle을 별도 검토 clone에서 확인한다.
   [정상 CI task branch push 절차](proposals/README.md)를 채택한 뒤 새 hosted 실행·실제 checkout/merge 부모·
   125개/skip0을 확인한다. 코드/manifest가 변하면 기존 결과 자동 승계 금지. Ready/main 채택은 별도 사람 작업이다.
3. **Heartbeat 배포·복구:** 미설치 patch 운영 적용은 별도 위험 검토다. orphan running과 대용량 record는
   소유권·실제 native/하위 실행·부작용·선별 조회 근거부터 확보한다. 확인 불가면 원본 보존/차단한다.
   runOnce 우회·daemon 재시작·record 편집·다른 agent 가장을 하지 않는다. [복구 조건](RECOVERY.md#2-heartbeat).
4. **M 채택:** 회사 로컬 미동기화 변경을 사람이 먼저 대조한다. 기존 PR #5 SHA가 바뀌면 새 조건으로
   검증·독립 리뷰한다. 사람이 채택한 뒤 실제 main/검사까지 확인해야 M 완주다. 그 전 정식 병렬은 진행하지 않는다.
5. **미실행 운영 경로:** 모바일은 사람이 실제 후보·Acceptance·증거·위험·승인 동작을 읽고 판단한 기록이 필요하다.
   실제 계정/장부/DB/volume·자동 setup·백업/복원은 필요한 자원부터 별도 fixture로 설계한다. 기존 서비스/데이터는 보존한다.
6. **관측 보강:** Auto-review/Claude 결정 주체는 현재 조건의 full ID·native 결과가 필요하다.
   비용·실제 승인/사람 개입은 위 범위를 가진 시작/종료 관찰부터 남긴다. 이를 위해 권한·토큰·보호를 변경하지 않는다.

새 Supervisor/writer/Worktree/Heartbeat/자동화를 만들지 않았다. 기존 Director/controller를 종료하거나
재설정하지 않는다. 과거 pilot Heartbeat 삭제를 현재 모든 자동화 부재나 자동 재개 보장으로 해석하지 않는다.
어떤 PR도 AI Ready/Merge하지 않았고 main/force push·Kerbe 변경·자동 Archive·서비스 조작은 없다.
`OVERNIGHT_REPORT.json`은 PR 게시/GET 검증 후 root만 원자 기록한다. 전체 운영 채택과 미션 완주를 뜻하지 않는다.

## 보고 검토와 최종 전달 관찰

고정 `d8ade7e32314ba137ada3dbedd04b31307d33019`의 [독립 Claude 리뷰](https://github.com/shotgun1107/home-dev-ops/pull/1#issuecomment-6090183386)는
새 Critical/High/Medium/Low/Info0이다. 종합 보고 전체·STATUS/EVIDENCE 변경과 비용 JSON 전체를 새로 읽고
다른 증거는 선택 필드만 대조했다. 과거 문맥 재사용·운영상 readonly이며 기술적 격리/blind 리뷰가 아니다.
실제 청구·야간 승인 전수·live GitHub 재실측·테스트 실행은 하지 않았다.

리뷰 뒤 `2026-10-09T22:18:24.265007+00:00`부터 순차 조회한 CLI CostUsd는 root0·Director0·Claude reviewer
**27.583550799999994 USD(약27.583551)**다. 앞서 보존한26.535272를 덮어쓰거나 이 차액을 해당 리뷰 비용으로
귀속하지 않는다. root/Director 비용 미제공과 야간 총비용 미확인은 그대로다. 이 시점 reviewer/Director는
idle·pending0, root는 현재 턴 running·pending0이다. 영수증 존재와 root idle은 별개다.
이 추가는 리뷰 결론·게시 영수증·시간이 붙은 관찰뿐이며 source/tests/proposals/원문 bytes는 그대로다.
최종 보고 HEAD·push/PR Draft/clean·coordinator 영수증은 PR의 마지막 handoff와 최종 응답에서 확인한다.
