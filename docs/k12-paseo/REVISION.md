# K12 Paseo 운영 체계 v2.4.1 개정안 — Draft

2026-10-10. [v2.4 정본](source/K12_Paseo_v2.4.md)을 보존한 추가 개정안이다.
**검토 전 정본을 대체하지 않는다. 전체 P0/P1의 통과 선언도 아니다.**
판정 근거는 [현황](STATUS.md)과 [실측](EVIDENCE.md)을 따른다.

## 유지할 운영 경계

결과 하나=task worktree/branch/PR 하나, worktree당 writer 하나, 동시 writer 최대 2명,
고정 full SHA 리뷰, 사람이 main 채택, AI merge 비활성, 수동 정리 원칙을 유지한다.
이번 사용자 요청은 기존 Supervisor·기존 ops Worktree 재사용이며 별도 review/조사는
소유권·범위·종료 조건을 확인한 경우에만 허용된다. 새 Supervisor나 중복 작업 공간을 만들지 않는다.

Full Access는 이번 사용자의 명시적 선택에 따른 실행 조건이다.
v2.4의 기본 승인 정책을 변경하는 근거로 채택하지 않는다. ops는 서버 보호 불가·hook 미설치이며 Full Access의 Provider 차단 미검증이다. 현재 보고·격리 개선 경로는 사용자가 선택한 예외로서 운영 규칙 준수에 의존하며 P0-A 미통과로 남긴다. AI merge 활성화 승인은 아니다.
권한·인증·Ruleset·공통 Git hook 설정은 agent가 임의 변경하지 않는다.

## 검증을 마친 수정안

| 원문 관련 항목 | 변경 내용 | 근거와 적용 한계 |
|---|---|---|
| 4·19장 동시 작업 관찰 | 승인 대기 writer도 상한에 포함하고, source·Git/common dir·runtime과 요청 ID를 분리해 기록한다. 한 작업의 대기가 독립 작업의 완료를 막는지 관찰한다 | 두 Python mock writer·15개 계약 회귀로 격리 검증. 전역 상한 자동 강제는 미검증이며 이번 실행은 운영상2개를 지켰다. 실제 Paseo dispatch/Provider 부담·정식 P1 결과가 아니므로 M main 선행과 기존 진입 조건은 유지한다. [E17](PARALLEL_ISOLATED.md) |
| 15·19장 CI 증거 | 실제 base ref·head·merge 부모·checkout SHA와 suite inventory/실행 수를 함께 기록한다. source/tests byte 동일할 때만 로컬 증거를 재사용한다 | OPS_CI 과거21→시작97→후보115개. 일부 suite만 남은 성공을 차단했다. Node47은 K12 별도 증거. 정확한 통합 bundle은 격리 검증했으나 실제 hosted 최신 run과 사람 채택은 대기. [검증](OPS_CI.md) |
| 13·16장 중단 복구 | handoff의 원격 SHA·Writer/native/하위 실행 종료·runtime 소유권·부작용 결과를 각각 대조한다. PID 전후 stamp 변화를 미확정으로 판정한다 | P0_RECOVERY Python38·설치 PID Node9 격리 시험. 원자적 발행 전후 새 child 종료 실측. 오프라인 판정은 lease/실행 허가가 아니며 controller에 연결하지 않음. [범위](FAILURE_RECOVERY.md) |
| 7·16장 권한/복구 | daemon 연결 오류에서 sandbox와 host 가시성을 먼저 대조한다. CLI stopped 하나로 start/restart하지 않는다 | E1 실제 namespace 차이·host 연결·진단 도구 9개 회귀. sandbox 접근 개방은 아님 |
| 13·18장 자동 재개 | 생성/주기 실행/idle 재개/종료 결과 저장/삭제를 각각 기록한다. agent-target 조회를 일반 schedule 조회와 구분한다. 자기 run이 끝난 뒤 삭제한다 | CLI filtering·자기 삭제 충돌 격리 재현, 정리 도구 9개 시험 통과. E9의 실제 idle 1회 재개와 이후 succeeded·정상 삭제·게시 GET 영수증까지 확인 |
| 9장 보호 확인 | classic branch protection과 Rulesets/effective rules를 각각 확인한다. 보호 기능 미지원은 repo별 정책 결함으로 기록한다 | Kerbe classic404+effective active, private ops403 실측 |
| 9장 local guard | 설치 여부·실효 경로와 guard 로직 통과를 분리한다. 기존 Kerbe 후보를 hash와 격리 시험으로 검토한다 | 12개 guard 시험 통과. ops 설치·LFS chaining·서버 강제 차단 검증은 별도 |
| 9·13장 PR 복구 | gh pr edit의 projectCards 호환성 오류에는 승인된 동일 본문 REST PATCH와 GET 확인을 허용된 복구 경로로 둔다 | 같은 오류 재현 및 현재 PR 갱신 성공. 권한 거부 우회가 아님 |
| 10장 리뷰 | 직접 게시 실패 시 원문·SHA·provider·대리 게시 표기를 보존하고 재조회한다 | Kerbe #2의 기존 2개 review 전달·게시 증거 재사용 |
| 14·19장 접근 확인 | Direct 비밀번호 미전송 거부를 별도 확인 완료로 기록한다 | 공개 /ws에서 password_required·4401, credential 미사용. relay/모바일 UX 보장 아님 |
| 15장 비밀정보 | ops 작업 파일의 env/runtime 제외를 추가하고 공개 example 추적 가능성을 확인한다 | .gitignore 전후 check-ignore 실측. 명시적 stage/비밀 검사는 계속 필요 |
| 19장 결과 재사용 | SHA·실효 모드·실행 주체·시간·대상 조건이 맞는 기존 증거를 재사용한다 | Python 후속 실측·현재 import 검사·CI와 기존 review 대조 |
| 6·7장 프로필 확인 | 현재 UI mode·과거 persistence metadata와 실제 호출 당시 native mode를 구분한다. task에 적용할 버전·deny·project/local override·hook을 확인한다 | S의 Work·C는 동일 조합의 과거 보호/쓰기 증거와 새 native 세션을 대조. Auto 쓰기나 Full Access 보호 증거로 확대하지 않음 |
| 7장 일상 승인 | 이미 허용된 task의 pending 명령을 Supervisor가 검토할 때는 full agent/request ID 하나씩 응답하고 주체·범위·입력 조정을 기록한다 | S에서 개별 승인 9건·범위 밖 거부 1건. `permit allow` ID 생략/`--all`과 첫 일치 선택을 하는 짧은 prefix 모두 금지. 영구 규칙 변경·무인 승인·사람 클릭 성공과 구분 |
| 8·13장 runtime | Git 탐색을 검사하는 fixture의 TMPDIR은 저장소 밖의 작업 전용 경로로 둔다. owner·권한·Git 비저장소 판정을 확인하고 handoff에 기록한다 | M에서 Worktree 내부 TMPDIR은 기존 2개 시험 실패, 새 0700 외부 TMPDIR에서는 같은 2개 통과. venv는 Worktree 안에 유지. 기존 임시 자료 삭제나 전역 환경 변경은 필요 없음 |
| 13장 진행 중 통신 | 실행 중 `paseo send`를 무중단 메시지 큐로 간주하지 않는다. 변경 지시가 필요하면 명령 종료 여부와 취소 영향을 확인한다 | M baseline 중 Supervisor의 보충 메시지가 tool 실행을 중단시킴. native의 user-rejected 표기만으로 실제 사람이 거부했다고 기록하지 않음. 기존 로그·잔여 fixture 보존과 실행 종료 확인 후 재시험 |
| 13장 Provider 교대 | 이전 Writer의 idle/pending·native 종료·자식 실행·commit/push·runtime 소유를 확인한 뒤 새 세션은 정본+Git/runtime으로 복원한다. task를 PR로 승격할 때는 저장 GET 확인 후 해당 task만 삭제한다 | M의 Claude→fresh Codex 같은 Worktree 실측 통과. 사용자 업무 재설명 0회지만 Supervisor 개입은 별도로 존재. UpdatedAt 하나로 실행 종료/재개를 판정하지 않음 |
| 10장 리뷰 후 변경 | 비회귀 지적도 현재 범위에서 안전하게 재현·개선할 수 있으면 합성 자료로 검증한다. source가 바뀌면 새 SHA의 검사와 delta 리뷰를 받는다 | M P2의 합성 traceback RED→최소 수정→22/185 시험·wheel·새 CI→독립 재리뷰. 기존 cwd probe adapter까지 임의 확장하지 않음 |

연결 문제는 운영 daemon 구현 실패로 다루기보다 진단과 실행 경계의 문제로 다루는 편이 맞다.
기존 host 경로는 동작하므로 재시작/인증 완화가 필요하지 않다.
PR 편집은 운영 승인 정책 문제가 아니라 CLI/API 호환성 문제이므로 보호 정책 완화가 필요하지 않다.
private ops 보호 API403은 반대로 로컬 구현 수정만으로 해결되지 않는 계정/저장소 정책 문제다.

## 확인된 불편과 아직 채택하지 않은 제안

P0_HEARTBEAT: maxRuns는 성공 횟수가 아니라 terminal 시도 수이며 expiry는 이미 시작한
agent를 종료시키지 않는다. schedule completed/failed와 업무·runtime 종료를 별도로 판정한다.
crash 뒤에는 실제 PR/HEAD·task 영수증을 대조하고 중복 부작용을 피한다. runOnce로 자동 재개를
대체하지 않는다. stale tick과 append 실패 guard 누수는 동일 조건의 미설치 패치 복사본에서
보정했고 Node38개가 통과했다. 실제 배포·daemon 변경은 사람이 결정할 별도 위험 검토다.
후보는 종료 저장의 연속 실패로 남은 orphan running에서 재실행을 거부한다. 저장소가
복구돼도 자동 진행이 멈추는 한계까지 실측했으며, 임의 재실행·daemon 재시작을 복구 정책으로
채택하지 않는다. 실제 실행·부작용을 대조한 뒤 사람이 복구 방식을 결정한다.
[시험·설치 후보·미확인 범위](HEARTBEAT.md)를 적용 근거로 보존한다.

P0_PERMISSIONS 추가 검증으로 승인 기록에는 **전달 경로와 결정 주체, 응답과 실행 결과**를
별도로 남긴다. reviewer=user나 user-rejected만으로 사람 개입을 세지 않는다.
중복 response는 full agent/request ID로 묶고 입력 조정은 허용의 부분집합으로 센다.
설치 Codex 새 기본 resolver는 지원 버전에서 auto-review를 고를 수 있으므로 명시 auto
preset과 구분하고 native approval/sandbox/reviewer를 확인한다. 프로필을 변경한 것은 아니다.
S ledger의 조정 필드 누락을 native와 대조해 보충했고 리뷰 반례 보강 후 합성38개 포함68개가 통과했다.
혼합 actor ledger를 일괄 덮어쓰지 않고, 조정은 명시 bool과 설명으로 남긴다. 모드 변경과
updatedPermissions는 Supervisor의 일상 승인 대상에서 제외하고 사람이 결정한다.
설치 소스·검증 범위와 미확인은 [권한 감사](PERMISSIONS.md)에 있다.

| 항목 | 문제·대안 | 채택 전 조건 |
|---|---|---|
| Claude Auto | 읽기 전용 조회도 거부된 기록, merge 차단 결정 주체 불명확. Auto를 항상 무인 실행 가능하다고 표현하지 않는다 | 사람이 사용할 모드/지침 loading을 확인하고 지정 무해한 호출에 실제 거부 주체를 확보. deny 변경 없이 기록 부족부터 해결 |
| Codex 기본 실행 | M에서 새 on-request/workspace-write의 편집·commit·task branch push·PR 쓰기를 확인했다. network=false와 공용 Git 디렉터리 제한으로 개별 승인이 필요함 | 해당 task 경로의 통과이며 무인 실행/모든 repo의 권한 보장은 아님. broad gh/shell allow나 Full Access 전환을 기본 해결책으로 넣지 않음 |
| ops 서버 보호 | private 유지+현재 계정 기능으로는 보호 API 사용 불가 | Pro 등 보호 기능 확보, 또는 private 유지와 보호 공백의 명시적 위험 수용을 사람 결정. public 전환은 자동 제안 채택하지 않음 |
| ops CI | PR #2의 과거21개 green과 stale merge ref는 현재 PR #1 검증이 아님 | [정확한 후보](proposals/README.md)의 로컬115개 통과·Node47 재사용. 보호 정책과 workflow 경로를 사람이 선택한 뒤 일반 task push 및 새 실제 CI 확인. Ready/main 채택은 별도이며 자동 변경하지 않음 |
| guard 배포 | 검증 후보가 있어도 ops에는 미설치 | 공통 Git 영향·기존 hook/LFS 연결 검토 후 사람이 설치하고 task 경로에서 재검증 |
| Kerbe setup | .venv 수동 경로는 실측, base의 자동 setup은 없음 | 경량 Python repo에서 수동 on-demand 유지 또는 최소 dev-setup/paseo.json 도입을 선택. 후자를 도입하면 별도 chore PR 검증·사람 merge 후 새 Worktree에서 시험 |
| A/B 조건 | 기존 실험은 승인 모드/거부 하네스가 달라 능력 비교 불가 | 동일 작업/기준 SHA/권한 조건/종료 조건으로 별도 설계. P1 독립 결과 병렬 시험과 구분 |
| 중복 workspace | 과거 Claude A/B 같은 경로에 unarchived workspace 2개 | 하나를 소유 기록으로 선택하고 다른 세션을 비writer로 유지. 정리/Archive는 별도 사람 결정 |
| reviewer | Claude Plan은 기술적 read-only가 아님 | 고정 Git 객체 정적 검토·운영상 수정 금지 fallback 명시, 필요 시 검증된 sandbox 사용. 도구 이름만으로 격리 보장하지 않음 |

## ops 보호 공백의 선택지 — 사람 결정

현재 결합은 private 보호 API 403 + 활성 local hook 없음 + Full Access 차단 미검증이다.
Full Access 선택을 이 세 가지의 해결 또는 상시 위험 수용으로 확대 해석하지 않는다.

| 선택지 | 범위와 남는 위험 | 최소 다음 행동 |
|---|---|---|
| private 유지·서버 보호 기능 확보 | 비용/계정 정책 결정 필요. 보호를 만들기 전까지 현재 공백 유지 | 사람이 사용 가능한 계정 기능을 선택하고 main PR 필수·삭제/non-FF 제한·실제 CI 이름·bypass를 검토. agent는 적용 후 GET 검증 |
| private 유지·현 기능 유지 | local guard는 로컬 사고 방지이며 웹/API merge나 다른 checkout을 막지 못함 | 사람이 guard 설치·사용할 기본 Provider 차단 검증 범위를 승인. 서버 보호 부재의 위험 수용 여부를 별도로 명시. 이것만으로 P0-G2 통과 처리하지 않음 |
| 공개 전환 | 보호 기능 외에 운영 기록·과거 Git 이력까지 공개되는 위험 | 별도 공개 적합성 검토와 명시 승인 필요. 이번 미션에서는 채택·실행하지 않음 |
| 현재 예외 범위 유지 | 보고·임시 fixture 시험·작업 branch/PR 갱신을 운영 규칙에 의존 | 사용자에게 이미 허용받은 현재 범위만 계속. 기술적 차단을 전제한 일상 writer 경로는 보류 |

위 선택은 Kerbe public의 확인된 Ruleset을 없애거나 불필요하게 막는 이유가 아니다.
실제 작업 repo·Provider·runtime별로 진입 조건을 판정한다. 전역 gh/shell 허용, sudo 확대,
token 교체, 기존 hook 덮어쓰기는 어느 선택에도 자동 포함되지 않는다.

## P1 S 첫 후보와 범위별 진입 조건

후보 결과는 **Kerbe의 `.env.local` 등 환경 파일 제외 누락 보완**으로 좁힌다.
이미 발견한 누락을 수정하는 작은 결과이며 신규 기능 설계나 실제 개인 데이터가 필요 없다.
[Kerbe Issue #3](https://github.com/shotgun1107/kerbe/issues/3)의 승인된 S를 별도 전용 Worktree에서
실행했고 [PR #4](https://github.com/shotgun1107/kerbe/pull/4)로 검증·리뷰까지 전달했다.
bootstrap PR #2는 별개이며 main에 아직 합쳐지지 않았다.

- Acceptance: 임시 파일명에 대한 `git check-ignore --no-index`로 `.env`, `.env.local`,
  `.env.test` 제외와 `.env.example` 추적 가능을 확인한다. 실제 비밀 파일은 열지 않는다.
  제품 코드·workflow·권한 파일 무변경과 diff를 검사하고 보안 경계 변경으로 고정 SHA 반대 Provider 리뷰를 받는다.
- 시작 조건: 기본 writer 프로필과 merge 차단의 실제 적용을 확인한다. 이미 통과한 동일 조건 증거는 재사용하되
  현재 Full Access 실측으로 대체하지 않는다. 그 프로필의 branch push/PR 경로도 확인한다.
  Kerbe bootstrap PR #2가 미반영이라는 사실과 base 지침 차이를 기록하고,
  현재 승인된 v2.4 안전 지침을 적용한다. 자동 setup의 base 변경을 사용하지 않는 이 후보에 bootstrap merge를 별도 필수 관문으로 추가하지 않는다.
  지침을 실제 어디서 로드했는지(예: 사용자 미션 프롬프트와 읽은 정본)도 S 기록에 남긴다.
  허용된 task Worktree 하나·writer 하나를 정하고 main/base SHA·기존 hook·Ruleset을 읽어 대조한다.
- 불필요한 선행 조건: 이 후보는 Python 실행·설치·개인 장부·Credential Manager·DB·컨테이너를 쓰지 않는다.
  새 setup 자동화나 runtime 분리 전체를 이 S의 전제 조건으로 요구하지 않는다.
  나중에 코드/runtime 범위가 추가되면 그때 해당 격리를 먼저 검증한다.
- 끝 조건: 하나의 Draft PR에서 검증·리뷰까지 진행한 뒤 사람이 Ready/merge를 수행한다.
  agent가 실제 main 반영을 확인해야 S 완주다. 그 전에는 검토 준비까지의 부분 진행으로 기록한다.

이번 S의 Writer 경로는 실제 대조·개별 승인으로 통과했다. 이후 사람이 PR #4를 squash merge했고
K12 fetch·전체 tree 일치·실제 main 필수 CI를 확인해 S 완주를 확정했다([E11](EVIDENCE.md#e11-s-main-반영과-m-진입)).
프로젝트 전체 기본 모델/무인 승인 정책을 이 한 번의 결과로 확정하지 않는다. `.gitignore`는
기존 tracked 파일·강제 add·이미 무시된 부모 디렉터리를 바꾸지 않으며 비밀값 검사 기능도 아니다.
서버 보호가 다른 repo인 ops에서 미지원이라는 이유나 사용하지 않을 DB가 미검증이라는 이유를 추가 관문으로 만들지 않는다.

## P1 추가 시험과 진입 조건

P0 미확인은 영향을 받는 기능/Provider 경로만 제한한다. 다만 S/M/병렬 선행 관계는 바꾸지 않는다.
P1 성공 정의를 문서 작성/정적 review로 낮춰 통과시키지 않는다.
S는 E11, M의 복원·구현·검증·독립 리뷰·Draft 전달은 E12에서 실측했다. M의 사람 채택·main 확인은 남아 있으며 병렬·모바일은 미실행이다.

1. **진입:** 사용할 writer의 권한/merge 차단, source 쓰기·branch push/PR 경로,
   실제 setup/check/import 경계, repo 보호/guard, 수동 merge·정리 정책을 확인한다.
   제품 runtime이 필요한 작업은 해당 자원의 분리도 먼저 통과해야 한다.
2. **S:** 사람의 신규 설명 없이 Acceptance가 결정된 작은 결과 하나를 선정한다.
   한 writer가 검증·필요 review까지 진행한다. 사람이 Ready/채택/merge를 수행하고
   agent가 main 반영 commit과 검사를 읽어 확인할 때 완주다. Kerbe #2는 자동으로 S 완료가 되지 않는다.
3. **M:** 기록할 내용은 목표/Acceptance/base+head/writer/검증/Next/runtime 소유/함정이다.
   이전 writer의 명령·하위 agent·Heartbeat 종료와 의도한 commit/push를 확인한다.
   새 Provider는 기록+Git+runtime만 읽고 Next를 진행한다. 사람이 맥락을 다시 설명했다면
   누락 항목을 보완해 그 복원 경로만 한 번 재시험한다.
4. **병렬:** S/M 완료 후 의존하지 않는 결과 두 개를 각 Worktree/branch/PR에서 운영한다.
   writer≤2·같은 Worktree writer=1을 유지한다. 승인 대기/재설명/base 재검증/직접 개입을
   기존 PR 로그에 짧게 기록하고 직렬 사례와 비교한다. 통계적 우월성을 주장하지 않는다.
5. **모바일:** 사용자가 휴대폰에서 후보 SHA, 결과/Acceptance, 통과 근거, 미확인/위험,
   승인할 정확한 동작을 판단한다. 버튼 작동/반응형 문서가 있다는 사실만으로 통과시키지 않는다.

## 완료·차단·재개

개발 결과 완료와 runtime 정리 완료는 분리한다. 필요한 사람 채택이 없으면 미달성으로 기록한다.
안전한 독립 작업이 끝나고 사람 결정만 남으면 PR에 결정별 정확한 다음 행동과 현재 SHA를 남기고
Heartbeat를 삭제한다. 자동 재개가 없다는 사실을 명시한다.

재개 시 같은 PR/Worktree에서 actual HEAD·dirty·원격 상태·writer/Heartbeat를 확인하고
이미 완료된 실측은 재사용한다. 자격증명/보호 규칙 변경이나 승인되지 않은 동작으로 대기 상태를 우회하지 않는다.
