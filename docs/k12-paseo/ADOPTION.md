# v2.4.1 채택 판단 자료 — ONE-SHOT-20261010

2026-10-10 KST. [사용자 승인 전문](https://github.com/shotgun1107/home-dev-ops/pull/1#issuecomment-6094528847)의
A–F를 기존 Astra Max가 수행했다. 정본 v2.4·기존 세션·서비스는 보존했다.
이 문서는 **사람이 선택할 실행 계획**이며 보호 설정·hook·설치 패치를 적용한 기록이 아니다.
시험 source는 `d8099f00188ffd35c9cec87b83d370c41c536a17`, 선별 근거는
[one-shot.json](evidence/one-shot.json), 현재 후보와 최종 CI는 [PR #1 handoff](https://github.com/shotgun1107/home-dev-ops/pull/1)를 따른다.

## A–F의 결과와 남은 경계

| 작업 | 안전한 범위의 결과 | 남은 판정 |
|---|---|---|
| A CI | 기존125 hosted의 checkout/부모/tree/완료 영수증/hash를 직접 대조. 새로운 Git 통합8개를 더한133개와 기존 CI branch를 통합·검토 | Ready·PR 통합·main 필수 검사 채택은 NEEDS_HUMAN. 최종 실제 run/SHA는 handoff 참조 |
| B Git 보호 | Rulesets/classic 모두 다시403, 공통 hook 없음. 실제 Git→hook·linked worktree·경로/execute bit·체인 계약과 우회를 로컬 fixture에서 검증 | 서버 보호·hook 설치·기본 writer 보호 경로는 BLOCKED/NEEDS_HUMAN |
| C Heartbeat | 설치/패치 hash 대조·고정 SHA 독립 리뷰. 신규 manual/orphan 조합까지 Node40개 통과, 패치 bytes 유지 | 미배포. 실제24h/OS crash/다중 프로세스/exactly-once·orphan 자동 복구는 미검증/미해결 |
| D 권한·복구 | production scripts와 설치 권한 소스8개가 기존 검토 bytes와 같음. Python133개 새 실측, PID9·mock15는 hash 기반 재사용 | 실제 Auto-review 결정 주체·야간 승인 전수/청구 총액 미확인. offline 도구는 lease/실행 허가가 아님 |
| E 개정안 | 원문 hash 보존, Review History 부재 유지. REVISION을 실측/격리/사람/미검증으로 구분 | Draft 후보이며 정본 교체 승인 아님 |
| F P1 | S의 main 실측 보존, M 전달과 mock 병렬을 정식 완주와 분리. 아래 모바일 검토 카드 준비 | Kerbe 완전 동결·회사 PC 동기화 결정, M main·정식 AI 병렬·모바일 실측 대기 |

Director는 과거 취침 중 임시 보조장치였고 상시 구조에서 제외한다. 기존 기록·세션은 유지한다.
새 Supervisor/Director/Heartbeat/controller는 만들지 않았다. 자동 재개를 보장하지 않는다.

## B. Git 보호 선택과 정확한 적용 순서

현재 `home-dev-ops`는 두 보호 API가403이고 활성 hook이 없다. `core.hooksPath`는 unset,
공통 git dir은 `/home/shotgun1107/workspace/home-dev-ops/.git`이다. 따라서 기존 main checkout과
ops linked worktree는 기본 hook 위치를 공유한다. Full Access의 기술적 main/merge 차단은 미검증이다.
이번 task push는 사용자가 승인한 운영상 예외이지 보호 공백 해소나 상시 수용이 아니다.

| 선택 | 비용 | 보호 범위·우회 | 작업 영향과 판단 |
|---|---|---|---|
| private 유지·서버 보호 기능 확보 | 유료 계정 기능 필요. 실제 결제 금액/세금은 가입 화면에서 사람 확인, 이번 작업은 과금/계정 변경 없음 | 적절히 설정된 main 서버 규칙은 다른 checkout·웹/API에도 적용. 관리자/bypass 구성은 별도 검토 | 우선 검토 후보. 기능 확보만으로 보호가 생기지 않으며 적용·GET·허용된 task 쓰기를 확인해야 함 |
| private 현 기능·local guard 추가 | 구독 추가 없이 설치/운영 검토 비용 | 같은 공통 Git의 실효 hook 호출에만 사고 방지. `--no-verify`, 다른 hooksPath, 비실행 파일, 다른 checkout·웹/API는 보호하지 못함 | 기본 writer 보호와 서버 보호 부재 위험 수용은 별도 사람 결정. 이것만으로 P0-G2 통과 아님 |
| public 전환·서버 보호 | 공개 repo의 해당 기능은 Free 지원. 별도 공개 검토 비용 | 보호 규칙 적용 이후에만 강제. 모든 과거 Git 기록의 공개 위험이 추가됨 | 추천 기본값 아님. 공개 적합성·이력 검토 없이 전환 금지 |
| 현재 제한된 예외만 유지 | 추가 구독/설치 없음 | 운영 규칙에 의존, 기술적 차단 미확인 그대로 | 보고·격리 시험·승인된 task branch/Draft 전달 범위에 한정. 일상 기본 writer 승인으로 확대하지 않음 |

기능 범위는 [GitHub 공식 Rulesets 문서](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets)와
[요금 안내](https://github.com/pricing/calculator)를 2026-10-10 조회했다. 개인 Pro와 조직 Team은 같은 선택이 아니며
저장소 소유형태·실제 청구 조건을 다시 확인한다. 토큰/권한 확대를 이 선택에 자동 포함하지 않는다.

서버 보호를 채택한다면 사람이 실제 repo/소유계정/기능을 확인하고, 현재 설정을 보호된 위치에
보존한 뒤 main 대상 PR 필수·삭제/force 금지·bypass 없음·실제 CI context를 검토한다.
CI가 main에서 실행되는 단계 전에 존재하지 않는 required check를 설정하지 않는다.
적용 뒤 classic/rulesets/effective rules GET을 각각 확인하고, 정상 task branch/Draft의 CI만 검증한다.
위험 main push/merge로 차단을 시험하지 않는다. API403/예상 밖 bypass/검사 이름 불일치면 도입을 멈추고
사람이 설정 차이를 검토한다. 롤백은 보존한 **이번 변경분만** 사람에게 재승인받아 복원하며
보호를 자동 완화하거나 다른 운영자의 후속 변경을 덮어쓰지 않는다.

local guard를 별도로 채택할 때의 사람 작업 순서:

1. 모든 영향을 받는 worktree의 writer·진행 중 Git·pending 상태, 공통 dir, 실효 hooksPath,
   pre-push의 존재/파일 종류/owner/mode/hash를 다시 읽는다. 이번 관찰 뒤 새 hook이 생겼으면 멈춘다.
2. 기존 hook/LFS 사용 계약을 확인한다. 이번 ops에는 non-sample hook·tracked `.gitattributes`가 없고
   git-lfs3.7.1 binary만 있다. binary 존재를 실제 LFS 체인 검증으로 세지 않는다.
3. 현재 후보 hash `d9488d892f3da43cbd2cabf7fb7a9e98639d70e62d34518243bbdb04ac8dafdc`를 대조한다.
   기존 파일·mode·symlink/부재 상태를 접근 제한된 별도 보존 경로에 기록하고 설치 범위를 승인한다.
   기존 hook이 있으면 덮어쓰지 않고 별도 chain 설계를 먼저 리뷰한다.
4. 연결 시 argv와 stdin을 양쪽에 동일하게 재전달하고 첫 실패를 보존해야 한다. 단순 순차 호출은
   stdin EOF를 전달할 수 있다. 새8개 시험의 replay shim과 후속 stub은 합성 계약 예시이며
   **배포용 dispatcher나 실제 LFS 업로드 시험이 아니다.** LFS를 도입하면 별도 폐기용 LFS 경로로 검증한다.
5. 설치는 사람이 수행한다. 설치 뒤 hash·execute bit·실효 경로를 재확인하고 승인된 topic push를 관찰한다.
   로직12개와 합성 Git 통합8개는 실제 설치 확인을 대체하지 않는다. main/force probe는 하지 않는다.
6. 예상하지 못한 차단/chain 오류면 해당 쓰기를 멈춘다. 설치 당시 파일이 그대로인지 확인하고 사람 승인으로
   보존본을 되돌린다. 처음 부재였다면 이번에 설치한 동일 hash 파일만 대상이며, 다른 변경은 삭제하지 않는다.

실측으로 새 topic/FF 전달, linked worktree의 삭제 차단, 선택한 hooksPath 적용, 미실행 bit와 두 우회,
동일 stdin/argv 재전달·후속 실패 보존을 확인했다. 모두 새 임시 저장소의 `mock-topic`과 file transport만
사용했고 main/force/network push는 없었다. SHA-256 object-format guard 지원·실제 LFS·서버 강제 차단은 미검증이다.

## C. Heartbeat 패치의 사람 실행 계획

분류: **격리 시험 통과했지만 미배포**. 기존19조건×2=38에 독립 리뷰가 제시한
manual orphan 조합1×2를 추가하여 **Node40개**를 실행했다. 결과는 [HEARTBEAT](HEARTBEAT.md)에 있다.
패치는 그대로이며 stale tick/pause/expiry/append guard 결함만 대상으로 한다.
manual runOnce→종료 저장 실패는 orphan을 하나 더 남길 수 있고, 한 번의 객체 복구는 첫 running만 실패 처리한다.
후보는 남은 running 때문에 진행을 거부한다. 반복 재시작/runOnce/record 편집을 복구로 권하지 않는다.

다음은 **미실행인 유지보수 계획**이며 이 문서로 서비스 조작을 승인하지 않는다.

1. 사람은 미배포 유지·검토된 상위 버전으로 업그레이드·현재 버전 패치의 선택을 한다. 상위 버전에서
   해결됐다는 증거는 이번에 확보하지 않았으므로 업그레이드를 해결책으로 확정하지 않는다.
2. 적용 대상 K12의 Paseo0.10.3/Node22.22.1, service hash
   `325066fba80c259ed0f5385042f15045820791fe048e622151259ed036dcd3c6`, patch hash
   `12ee2e3efb6e778a5c2642b23d1406888950afa00b5c101a1a80529055178ce0`와 store/cron hash를 대조한다.
   달라지면 적용하지 않고 새 source diff·격리 회귀·독립 리뷰부터 수행한다.
3. 현재 패키지/lock/파일 mode·owner·실제 서비스 실행 경로를 보호된 별도 백업으로 보존한다.
   schedule ID/target/cron/timezone/expiry/maxRuns/status/run ID와 agent/native/child/pending의
   선별 목록을 확보한다. 비밀 prompt/output/인증값을 Git·공개 로그에 복사하지 않는다.
   schedule 데이터 백업은 사람이 접근 통제를 정한 뒤 일관된 snapshot 방식으로 수행·검증한다.
4. 실행 중 작업·승인 대기·잔여 child를 모두 정합 대조한다. stop()은 기존 tick/runner를 취소하지 않는다.
   quiescence나 백업 일관성을 증명할 수 없으면 유지보수를 시작하지 않는다. 신규 tick을 어떻게 막고
   어느 schedule을 보존/재개할지는 정확한 ID별로 사람에게 승인받는다. 무관한 Director/서비스를 건드리지 않는다.
5. 다운타임은 미측정이다. 새 패키지 사본에 patch 적용/구문·Node40 회귀를 먼저 통과시키고,
   사람이 정한 점검 시간과 실패 중단 기준 안에서만 실제 설치/정상 재시작을 별도 수행한다.
   실행 중인 패키지를 덮어쓰거나 version 문자열만으로 적용을 확인하지 않는다.
6. 설치 후 파일 hash·연결·schedule 보존 목록을 대조한다. 재시작 recovery가 terminal 상태와 nextRunAt을
   바꿀 수 있으므로 기존 run 부작용/PR/영수증을 먼저 확인한다. 승인된 무해한 별도 agent-target 1회 시험만
   설계하고 기존 schedule의 runOnce·재발행·DB 편집을 대신 사용하지 않는다. 현재 미션에서는 만들지 않았다.
7. hash/record/연결 불일치, 새 중복, orphan, 허가되지 않은 상태 전이가 보이면 재실행하지 않고 실패를 보존한다.
   사람은 기존 실행 종료를 확인한 뒤 정확히 보존한 패키지를 복원할지 결정한다. schedule DB를 과거 백업으로
   무조건 되돌리면 실행 이력을 잃고 중복될 수 있으므로 **자동 데이터 롤백은 하지 않는다**.
   원복 후에도 installed 결함은 돌아오며, 모든 runtime 종료나 exactly-once를 보장하지 않는다.

## 한 번에 선택할 사람 결정과 모바일 검토 카드

| 결정 | 후보·기본 제안 | 완료로 인정할 후속 증거 |
|---|---|---|
| Git 보호/기본 writer | private 유지·서버 기능 확보를 우선 검토. guard는 별도 사고 방지 층. 현 예외만 유지할지도 명시 | 적용한 보호 GET·정확한 writer 프로필/무해한 쓰기 경로·hook 실효 위치 확인. Full Access를 기본으로 자동 채택하지 않음 |
| ops CI·문서 | [PR #2](https://github.com/shotgun1107/home-dev-ops/pull/2)→PR #1 branch 통합 후 PR #1→main을 사람 검토 후보로 제시 | 고정 SHA 일치·Draft 해제/통합은 사람 수행. PR #1 최신 main merge checkout의 CI 성공 뒤 main 채택. [절차](proposals/README.md) |
| Heartbeat | 당장은 미설치 후보 보존. 적용하려면 위 유지보수 범위/백업/중단/rollback 별도 승인 | 새 source/운영 적용 hash·실제 안전한 수명/보존 시험. Node40만으로 배포 성공 처리하지 않음 |
| Kerbe M·병렬 | 회사 PC의 미커밋·미푸시 내용을 사람이 먼저 보존·대조. 기존 PR #5 후보 `7ff930cefd308c37702aff7c7efd48fc4c9e4c9b`는 이전 증거만 유지 | 회사 변경과 새 후보를 정한 뒤 재검증/리뷰·사람 main 채택 확인. 그 전 Kerbe 동결·정식 AI 병렬 미진입 |
| 모바일·운영 미검증 | 아래 정보를 실제 휴대폰에서 확인할 시험 시점 선택 | 사용자의 기기/시각/읽은 SHA/Acceptance 판단/위험 이해/선택 행동 기록. 문서 링크 검사만으로 통과하지 않음 |

모바일 카드: PR #1 최종 handoff의 **full HEAD와 PR #2 HEAD**, Python133와 Node40/PID9/mock15의
서로 다른 범위, ops403/no-hook/Full Access 미검증, Heartbeat 미배포·orphan 한계, Kerbe 동결을 읽는다.
사용자는 각 결정의 채택/보류와 정확한 허용 동작을 선택한다. 버튼을 눌러 merge해 보라는 시험은 아니다.
모바일 실제 판단은 미실행이며 승인/비용 통계에도 가산하지 않는다.

선별 S/M 응답62=allow59+deny3(조정6은 allow 일부), mock 수동 결정6은 과거 기록이다.
사람 클릭·야간 신규 요청·실행 성공으로 바꾸지 않는다. CostUsd0은 미제공 대체값일 수 있어 무료가 아니다.
이번 reviewer CLI 값도 청구 총액이나 미션 증분 비용으로 사용하지 않는다. 전체 비용/승인 전수는 미확인이다.
