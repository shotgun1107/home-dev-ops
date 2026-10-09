# P0_PERMISSIONS — 야간 권한 라우팅 감사

2026-10-10 KST. 기준 ops HEAD `5a17e3d5ff5d1d72b550516da2b957ba55e8357d`.
기존 Astra Max Supervisor/ops Worktree를 유지했다. 이 감사 완료는 P0 전체 통과나
기본 권한 정책 채택을 뜻하지 않는다. 새 merge/push 차단 probe, Kerbe 변경,
권한·설정·서비스 변경 없이 저장 증거와 설치 소스를 읽었다.
버전은 Paseo 0.10.3, Codex 0.160.1, Claude 2.1.292다.
설치 파일 hash·행 범위와 선별 native 행 hash는 [감사 증거](evidence/permission-audit.json)에 있다.

## 실효 라우팅과 결정 주체

| 대상 | 확인한 사실 | 적용 한계 |
|---|---|---|
| Codex 명시 `auto` | on-request / workspace-write / reviewer=user | user는 전달 경로이며 실제 사람이 응답했다는 뜻이 아니다 |
| Codex 명시 `auto-review` | 같은 sandbox/policy, reviewer=auto_review | 모든 명령의 자동 검토·허용을 뜻하지 않는다 |
| 새 Codex 기본 선택 | 설치 provider의 >=0.115 version gate에서 catalog/default resolver가 auto-review 선택 | fallback 상수 auto나 Default Permissions 라벨만으로 실효값을 확정하지 않는다. 새 세션 시험은 안 함 |
| override와 native | mode override가 있으면 preset reviewer를 전달; providerOptions의 approval/sandbox는 별도 우선 조건 | preset 표를 모든 설정 조합으로 확대하지 않는다. 실제 turn_context/thread 응답 확인 필요 |
| M Codex native 8·71·325행 | on-request, workspace-write/network=false, reviewer=user | M Supervisor 허용34건은 Codex auto-review 허용34건이 아니다 |
| 현 Supervisor | Astra Max / Full Access 유지, never 경로 | 승인창 없음은 자동 검토 성공이 아니다. 기술적 merge 차단 미확인 |
| Claude 설정 전달 | SDK에 user/project/local sources와 실제 permissionMode 전달 | 설정 파일 존재만으로 전 호출 경로의 강제 차단을 보장하지 않는다 |
| Claude bypass 가능성 | SDK launch에 allowDangerouslySkipPermissions=true를 전달해 같은 세션의 후속 bypassPermissions 전환이 가능 | 활성 bypass라는 뜻은 아니다. 해당 모드에서 deny 유지 여부는 미검증. 모드·updatedPermissions 변경은 사람만 결정하며 이번 Supervisor 승인 대상에서 제외 |
| 과거 Claude Auto·Accept Edits | 선별 native toolDenialKind=permission-rule | 특정 deny rule ID·classifier 내부 결정은 미확인. Auto 기록의 classifier context 존재만으로 결정 주체를 정하지 않는다 |
| Claude steer/abort | steer supersession·abort·cleanup에서도 deny resolution 생성 가능 | user-rejected/permission_resolved를 사람의 명시 거부로 자동 집계하지 않는다 |
| Paseo permission 응답 | CLI/UI가 같은 transport 사용; allowed는 응답 전달 결과 | pending 해제·실행 시작·성공은 별도 사실 |
| 별도 voice 예외 | 활성 voice의 speak tool 전용 auto-allow 코드 | shell/Git 허용이나 이번 미션에서 사용한 증거는 아님 |

검토자 교체와 sandbox 경계의 구분은
[OpenAI 공식 Auto-review 문서](https://learn.chatgpt.com/docs/sandboxing/auto-review)와 대조했다.
문서는 의미 해석용이며 K12의 자동 검토 실측을 대신하지 않는다.
실제 auto-review decision/rationale 영수증은 이번 선택 증거에서 확인하지 못했다.
새 프로필·권한 변경과 실환경 시험은 별도 사람 결정으로 남긴다.

## 승인 집계와 실제 결함 수정

| 선별 기록 | 허용 | 명시 거부 | 허용 중 입력 조정 | 주체 근거 |
|---|---:|---:|---:|---|
| S Claude | 9 | 1 | 3 | 기존 Supervisor ledger·native 요청/응답 |
| M Claude | 16 | 2 | 3 | full agent/request ID별 Supervisor ledger |
| M Codex | 34 | 관찰 없음 | 관찰 없음 | 같은 ledger + native reviewer=user |

총62개 선별 응답(허용59/거부3)이며 작업 성공62회나 사람 클릭62회가 아니다.
M baseline 중단1건은 이미 허용한 명령에 Supervisor가 메시지를 보낸 사건이다.
명시 deny2건에 중복 가산하지 않는다. 전체 도구 호출·개입의 전수 통계는 아니다.

새 집계기로 **S ledger의 구조화 입력 조정이 2건만 집계되는 결함**을 발견했다.
기존 문서의3건 중 `permission-a76046a1-7d93-4847-8227-44da399e82ea`는
action/actualInput에는 조정 내용이 있었지만 inputAdjustment 필드가 없었다.
Supervisor native1219행의 --input 요청과1222행의 allowed 응답을 확인하고 필드·행 참조를
보충했다. 재집계는3건, 허용/거부는9/1 그대로다. prose로 수치를 추측하거나 승인을 재실행하지 않았다.

## 오프라인 회귀 도구

[paseo_permission_audit.py](../../scripts/paseo_permission_audit.py)는 승인 실행기가 아니다.
network/subprocess/provider/config 쓰기 없이 지정한 선별 JSON을 읽어 집계한다.
원본 로그·prompt·명령·credential을 입력하지 않는다. 사건별 source citation은 검토자가
확인해 정규화한다. actorEvidence 문자열은 인증 증명이 아니라 검토 가능한 참조다.

- response, native denial observation, terminal execution observation을 분리한다.
- agentId/requestId별 중복 응답을 제거하고 상충하는 outcome/actor는 실패로 처리한다.
- 입력 조정은 허용의 부분집합이다. 허용 후 error/interrupted는 명시 deny가 아니다.
- full UUID agent/request ID를 요구한다. prefix·ID 생략·--all을 식별자로 받지 않는다.
- 출처 없는 human/auto-review 주장은 unknown, permission-rule/forbidden은 provider layer까지만 분류한다.
- 필드 whitelist, 2 MiB/10,000 events 한도, 잘못된 JSON/schema의 무노출 오류 출력을 사용한다.
- 없는 항목은 미관찰이다. unknown을 0회 개입이나 통과로 바꾸지 않는다.

독립 리뷰 후 보강: provider-rule/forbidden에 human 등 모순된 actor를 붙이면 거부한다.
provider 계층과 daemon의 응답 주체를 구분한다. 혼합 actor/reviewer 필드가 있는 ledger는
일괄 --actor로 덮어쓰지 않고 events 형식으로 선별하도록 거부한다. 입력 조정은 명시적
inputAdjusted=true와 설명이 모두 있어야 하며 서술의 truthiness로 세지 않는다.
S/M의 기존 확인된6건에만 marker를 보충했다. 깊은 JSON도 고정 오류로 종료한다.

ID 검사는 저장 S/M에서 확인한 permission-UUID와 permission-exec-UUID만 지원한다.
설치 Codex는 parsed.itemId를 붙이기도 하므로 모든 Provider ID의 일반 검증기가 아니다.
다른 형태는 근거를 확인해 별도 지원하며 prefix로 완화하지 않는다. codex_route도 설치
Paseo의 workspace-write 판정 범위로 제한한다. read-only/granular는 이 도구에서 미확인이다.

재현 명령(읽기 전용):

```sh
python3 -B scripts/paseo_permission_audit.py ledger docs/k12-paseo/evidence/kerbe-s-permits.json --actor supervisor --actor-evidence kerbe-s-permits.json/reviewer
python3 -B scripts/paseo_permission_audit.py ledger docs/k12-paseo/evidence/kerbe-m-permissions.json --actor supervisor --actor-evidence EVIDENCE.md/E12
python3 -B -m unittest discover -s tests -v
```

최초 검증은 신규 합성32개+기존30개=**62개 OK, skipped0**.
리뷰 반례를 이전 SHA 코드에 적용하면38개 중20개 assertion/subtest failure를 재현했다.
보강 후 신규 합성38개+기존30개=**68개 OK, skipped0**. failure 수는 실패 method 수와 다르다.
기존 guard 시험도 가상 Git 저장소·hook stdin 시험이며 원격 push probe가 아니다.
테스트는 작업 전용 임시 디렉터리만 사용하고 정리하며 실서비스·데이터를 쓰지 않는다.
고정 SHA 독립 리뷰와 최종 결과는 [PR #1](https://github.com/shotgun1107/home-dev-ops/pull/1)에 기록한다.

## 운영 적용과 남은 제한

permit allow는 ID 생략/--all 시 전부, prefix 시 첫 일치 요청을 처리한다.
full agent/request ID 하나와 최신 pending 내용을 대조한다. kind=plan은 모드 변경을,
updatedPermissions는 정책 변경을 동반할 수 있으므로 일반 명령 허용으로 취급하지 않는다.
위험 범주는 이번 작업의 승인 대상이 아니다. 이 감사는 설치 소스를 바꾸지 않는다.

승인 기록은 대상·조건·실제 actor 근거·응답·입력 조정·실행 결과를 따로 남긴다.
Auto-review 무인 안정성, 특정 Claude deny 매칭 ID, Full Access 차단, ops 보호/guard/CI 통합은
미확인 또는 사람 결정으로 남는다. Kerbe 회사 측 미동기화 변경은 조사·수정·fetch하지 않았다.
Kerbe PR #2/#5 채택도 이 작업 밖이다.

최종 delta 리뷰는7edc8b9c6e2cc694cd104ffe97abcaa96638f835의 Low4/Info3 해소, 새 Low 이상0으로
종료했다. [원문·주체·GET 검증](evidence/permission-review.json). 새 Info2건은 다음처럼 구분한다.
최상위 reviewer 설명과 --actor의 일치는 검토자가 확인하며 도구가 인증하지 않는다.
Python3.14.4의2000-depth 시험은 이전 코드에서도 OK여서 RecursionError 재현으로 세지 않는다.
별도 작업 전용 fixture와 json.loads 오류 주입으로 해당 catch의 exit2·고정 오류·무노출을
확인했다. 이 추가 확인은68개 unittest에 합산하지 않는다. 코드/시험 bytes는 리뷰 SHA와 같다.
