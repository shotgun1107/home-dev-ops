# K12 Paseo 운영 체계 v2.4.1 개정안 — Draft

2026-10-09. [v2.4 정본](source/K12_Paseo_v2.4.md)을 보존한 추가 개정안이다.
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
| 7·16장 권한/복구 | daemon 연결 오류에서 sandbox와 host 가시성을 먼저 대조한다. CLI stopped 하나로 start/restart하지 않는다 | E1 실제 namespace 차이·host 연결·진단 도구 9개 회귀. sandbox 접근 개방은 아님 |
| 13·18장 자동 재개 | Heartbeat 생성/실제 주기 실행/idle 재개/삭제를 구분해 기록한다. agent-target 조회를 일반 schedule 조회와 구분한다 | 0.10.3 CLI filtering 원인 확인·생성/삭제 성공. idle 자동 복원은 미확인 |
| 9장 보호 확인 | classic branch protection과 Rulesets/effective rules를 각각 확인한다. 보호 기능 미지원은 repo별 정책 결함으로 기록한다 | Kerbe classic404+effective active, private ops403 실측 |
| 9장 local guard | 설치 여부·실효 경로와 guard 로직 통과를 분리한다. 기존 Kerbe 후보를 hash와 격리 시험으로 검토한다 | 12개 guard 시험 통과. ops 설치·LFS chaining·서버 강제 차단 검증은 별도 |
| 9·13장 PR 복구 | gh pr edit의 projectCards 호환성 오류에는 승인된 동일 본문 REST PATCH와 GET 확인을 허용된 복구 경로로 둔다 | 같은 오류 재현 및 현재 PR 갱신 성공. 권한 거부 우회가 아님 |
| 10장 리뷰 | 직접 게시 실패 시 원문·SHA·provider·대리 게시 표기를 보존하고 재조회한다 | Kerbe #2의 기존 2개 review 전달·게시 증거 재사용 |
| 14·19장 접근 확인 | Direct 비밀번호 미전송 거부를 별도 확인 완료로 기록한다 | 공개 /ws에서 password_required·4401, credential 미사용. relay/모바일 UX 보장 아님 |
| 15장 비밀정보 | ops 작업 파일의 env/runtime 제외를 추가하고 공개 example 추적 가능성을 확인한다 | .gitignore 전후 check-ignore 실측. 명시적 stage/비밀 검사는 계속 필요 |
| 19장 결과 재사용 | SHA·실효 모드·실행 주체·시간·대상 조건이 맞는 기존 증거를 재사용한다 | Python 후속 실측·현재 import 검사·CI와 기존 review 대조 |

연결 문제는 운영 daemon 구현 실패로 다루기보다 진단과 실행 경계의 문제로 다루는 편이 맞다.
기존 host 경로는 동작하므로 재시작/인증 완화가 필요하지 않다.
PR 편집은 운영 승인 정책 문제가 아니라 CLI/API 호환성 문제이므로 보호 정책 완화가 필요하지 않다.
private ops 보호 API403은 반대로 로컬 구현 수정만으로 해결되지 않는 계정/저장소 정책 문제다.

## 확인된 불편과 아직 채택하지 않은 제안

| 항목 | 문제·대안 | 채택 전 조건 |
|---|---|---|
| Claude Auto | 읽기 전용 조회도 거부된 기록, merge 차단 결정 주체 불명확. Auto를 항상 무인 실행 가능하다고 표현하지 않는다 | 사람이 사용할 모드/지침 loading을 확인하고 지정 무해한 호출에 실제 거부 주체를 확보. deny 변경 없이 기록 부족부터 해결 |
| Codex 기본 실행 | 기본 workspace-write의 편집/차단 증거는 있으나 현 Full Access 원격 쓰기를 기본 모드 통과로 승계할 수 없음 | 기본 경로를 채택할 때 branch push/PR의 필요한 명령별 승인·네트워크 조건 확인. broad gh/shell allow를 넣지 않음 |
| ops 서버 보호 | private 유지+현재 계정 기능으로는 보호 API 사용 불가 | Pro 등 보호 기능 확보, 또는 private 유지와 보호 공백의 명시적 위험 수용을 사람 결정. public 전환은 자동 제안 채택하지 않음 |
| ops CI | 코드가 포함된 이 PR의 check-runs가 비어 있음 | 준비한 workflow patch를 사람이 별도 branch/PR로 적용하고 실제 CI 성공을 후보 SHA에 연결. 로컬 21개 통과로 대신하지 않음 |
| guard 배포 | 검증 후보가 있어도 ops에는 미설치 | 공통 Git 영향·기존 hook/LFS 연결 검토 후 사람이 설치하고 task 경로에서 재검증 |
| Kerbe setup | .venv 수동 경로는 실측, base의 자동 setup은 없음 | 경량 Python repo에서 수동 on-demand 유지 또는 최소 dev-setup/paseo.json 도입을 선택. 후자를 도입하면 별도 chore PR 검증·사람 merge 후 새 Worktree에서 시험 |
| A/B 조건 | 기존 실험은 승인 모드/거부 하네스가 달라 능력 비교 불가 | 동일 작업/기준 SHA/권한 조건/종료 조건으로 별도 설계. P1 독립 결과 병렬 시험과 구분 |
| 중복 workspace | 과거 Claude A/B 같은 경로에 unarchived workspace 2개 | 하나를 소유 기록으로 선택하고 다른 세션을 비writer로 유지. 정리/Archive는 별도 사람 결정 |
| reviewer | Claude Plan은 기술적 read-only가 아님 | 고정 Git 객체 정적 검토·운영상 수정 금지 fallback 명시, 필요 시 검증된 sandbox 사용. 도구 이름만으로 격리 보장하지 않음 |

## P1에 사용할 시험 설계 — 아직 실행 결과가 아님

P0 미확인은 영향을 받는 기능/Provider 경로만 제한한다. 다만 S/M/병렬 선행 관계는 바꾸지 않는다.
P1 성공 정의를 문서 작성/정적 review로 낮춰 통과시키지 않는다.

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
