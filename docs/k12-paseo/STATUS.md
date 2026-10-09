# K12 Paseo P0/P1 검증 현황

2026-10-10 KST. **P0 부분 검증, P1 S 완주 확인, M 교대·구현·검증·독립 리뷰·Draft 전달 완료. M의 사람 채택과 실제 main 확인은 대기 중이며 미션 전체 완료가 아니다.**
최신 후보 SHA·writer 상태·Next·Heartbeat 상태는 [Draft PR #1](https://github.com/shotgun1107/home-dev-ops/pull/1)의 handoff를 따른다.

야간 **P0_PERMISSIONS 감사**: 설치 승인 라우팅과 기존 S/M 기록 대조, 집계 결함 수정,
독립 리뷰 반례 재현·보강 후 신규 합성38개+기존30개=68개 통과. [권한 감사](PERMISSIONS.md).
새 실환경 권한 시험·설정 변경은 없으며 Auto-review의 실제 결정은 미확인이다.

야간 **P0_HEARTBEAT**: 설치본의 stale tick/guard 누수 결함 재현, 미설치 패치 후보의
동일 조건 보정과 장기·만료·crash 상태 복원 **Node34개 격리 시험 통과**.
실제24시간·daemon crash는 미실행. [수명·동시성 감사](HEARTBEAT.md).

## 기준

- [v2.4 원문](source/K12_Paseo_v2.4.md)과 [AGENTS 초안](source/K12_AGENTS_draft.md)은 입력과 byte 동일. 원문 참조 `K12_Paseo_Review_History.md`는 입력에 없어 미확인.
- 기존 `docs/k12-paseo-autopilot` Worktree 재사용. 시작 HEAD `bf50f2bdb44e4d71fc29b31dcb0629719a345a95`, 재개 때 clean·open PR 없음 확인.
- 기존 Supervisor `c9bb4cb7-d656-4fb6-a6a5-e8fbcd3745cd`가 ops의 유일한 writer다. S는 허용된 별도 Kerbe Worktree의 Claude Writer가 담당했다. 최대 동시 writer는 2명, Worktree별 1명이며 조사·리뷰는 수정 금지였다. S Writer/reviewer와 M의 Claude→Codex Writer/독립 reviewer 모두 종료·idle을 확인했다.
- 사용자가 이번 Supervisor를 Full Access로 전환했다. 기본 승인 경로 검증과 분리하며, agent가 권한 설정을 변경한 것은 아니다.
- [Issue #3](https://github.com/shotgun1107/home-dev-ops/issues/3) 재개: `73afc54ba6ba046ad5f527c08d77fd3a20ce2a58`에서 local/PR HEAD 일치·clean 확인. 실제 Supervisor는 `gpt-6-astra` / `max`, 같은 workspace이며 이전 Heartbeat 파일은 없다. [재개 시점 조회](evidence/issue-3-resume.json)
- ops main에는 서버 보호를 사용할 수 없고 활성 hook도 없다. 현 Full Access 경로의 Provider 차단은 미검증이므로 **확인된 기술적 main/merge 차단에 의존할 수 없으며 운영 규칙 준수에 의존한다.** 사용자 선택으로 실행한 이번 보고·격리 개선은 v2.4 기본 개발 경로의 예외로 기록한다. 이 경로의 P0-A는 미통과다. AI merge 활성화 예외나 merge 승인은 아니다.
- **통과**는 표에 적힌 시험 범위만 뜻한다. 정적 검토, 구성 조회, 실제 실행, 사용자 보고 재사용을 구분한다. skipped는 실행 통과로 세지 않는다.

## P0

| ID | 항목·성공 기준 | 판정 | 증거·제한 |
|---|---|---|---|
| P0-H1 | 기존 daemon 연결 원인 식별·안전한 생성 | 통과(호스트 경로) | PID namespace로 기본 탐색 실패 재현, 기존 host PID에 연결·Heartbeat 생성. sandbox 연결 자체는 해결하지 않음. [E1](EVIDENCE.md#e1-heartbeat) |
| P0-H2 | 자동 재개·중복 방지·만료·정리 | 실제1회 수명 통과 / 장기·만료 격리 검증 / 실24h 미실행 | 427d614c의 실제 idle→succeeded→삭제 영수증 재사용. expiry는 실행 강제 종료가 아니고 failed도maxRuns를 소모함. 설치본 stale tick 결함은 H3에 분리. [E9](EVIDENCE.md#e9-실제-idle-자동-재개-1회), [E14](EVIDENCE.md#e14-p0_heartbeat-야간-격리-검증) |
| P0-H3 | 동시 tick·저장 실패·crash 상태 복원 | 설치본 결함 재현 / 후보 격리 통과 / 운영 미적용 | 같은 슬롯 중복·pause/expiry 뒤 dispatch·append 실패 guard 누수를 후보에서 차단. Node34개, 기존 Python68 hash 재사용. crash 부작용 exactly-once·실제 daemon 장애 복구 보장은 아님. [수명 감사](HEARTBEAT.md) |
| P0-A1 | Codex 기본 모드·merge 실행 전 차단 | 과거 gh pr merge 형태 통과 / 현 Full Access 미통과 | 과거 Paseo on-request/workspace-write의 forbidden 거부. 현재 Full Access를 대체 증거로 쓰지 않음. [E2](EVIDENCE.md#e2-provider) |
| P0-A2 | Claude Auto·merge deny 실제 적용 | 부분 검증 | gh pr merge 형태의 실행 전 거부 확인, deny rule인지 classifier인지 미확인. 정상 조회 거부 사례도 있어 writer 승인 안정성은 보류 |
| P0-A3 | source 편집·commit·branch push·Draft PR | 경로별 통과 | S Work·C의 PR 생성과 M의 Claude→Codex 실제 source·Git·Draft/PR 본문 쓰기를 확인. M은 Claude 승인16/명시거부2/입력조정3, Codex 승인34(초기2+구현21+리뷰후속11). Supervisor 개입이며 무인 승인 성공이 아님. [E12](EVIDENCE.md#e12-m-같은-worktree의-claude--codex-복원) |
| P0-A4 | S Work·C의 실제 모드·merge 차단·현재 보호 대조 | 이번 S 범위 통과 | 동일 Opus 5.5/medium/Accept Edits의 과거 실행 전 permission-rule 거부 재사용. 현재 버전·deny·신규 native 모드·hook·Ruleset 대조. 새 위험 호출 없음. matched-rule ID와 모든 우회 경로 봉쇄는 미확인. [E10](EVIDENCE.md#e10-kerbe-p1-s--실제-writer-경로) |
| P0-A5 | 승인 라우팅·주체·집계 정확성 | 설치 소스/선별 기록/합성 회귀 통과 | reviewer=user와 Supervisor 응답 구분. S 조정 누락1건 보충, 허용59/명시거부3의 선별62건 재집계. Auto-review 실결정·특정 Claude rule·Full Access 차단은 미확인. [E13](EVIDENCE.md#e13-p0_permissions-야간-감사) |
| P0-G1 | Kerbe 서버 측 main 보호 | 통과(실효 구성 조회) | ruleset active, PR 필수, 삭제/non-FF 금지, 2 CI strict, bypass 없음. 위험 push/merge 실험은 안 함 |
| P0-G2 | home-dev-ops 서버 측 보호 | 차단 | private repo 보호 API 403: Pro/public 필요. 공개 전환·구독 변경은 사람 결정. [E3](EVIDENCE.md#e3-git) |
| P0-G3 | pre-push 사고 방지 | Kerbe 로직 통과 / ops 설치 대기 | 실제 Kerbe hook·동일 후보 각각 12개 격리 시험. ops 활성 hook 없음. 설치/공통 Git 설정 변경 미실행 |
| P0-W1 | Worktree·writer 소유권 | 현재 미션 통과 / 과거 결함 | ops 기존 workspace 유지, S 단일 writer, M의 같은 wks_6ff707e7c396efdb에서 Claude 종료·Git/runtime 확인 뒤 fresh Codex 인수. 과거 A/B dirty worktree와 중복 registry 보존 |
| P0-R1 | Python setup·import 격리 | 확인 범위 통과 | PR #2 운영자 실측 182 tests OK, skipped 2·wheel. 이번에는 기존 .venv/source 경로 재확인, clean 유지. [E4](EVIDENCE.md#e4-runtime) |
| P0-R2 | 새 Worktree setup·runtime 분리 | M의 Python fixture 범위 통과 | 신규 .venv 설치·import assert, 외부 task TMPDIR 0700/owner/비저장소, 같은 runtime 교대 재사용. 내부 TMPDIR 실패 2개→보정 후 2개 OK, 최종 수정 후 Ran185 OK(skip2)·wheel. 실제 계정/장부/DB/volume 격리와 자동 setup은 미검증. [E12](EVIDENCE.md#e12-m-같은-worktree의-claude--codex-복원) |
| P0-V1 | 고정 SHA 리뷰·대리 게시 복구 | 통과 | S의 Codex 리뷰와 M 7ff930c…의 독립 Claude delta 리뷰·원문 대리 게시·GET 일치. M의 P2 1건 재현·수정 후 새 P0/P1/P2 0건. 직접 게시 권한과 기술적 readonly는 미확인. [E12](EVIDENCE.md#e12-m-같은-worktree의-claude--codex-복원) |
| P0-C1 | 이 ops PR의 필요한 CI | 별도 PR 통과 / 현재 후보 미확인 | CI PR #2의 f069ac3…에서 Python 3.12.15·21개 통과. PR #1을 base로 한 Draft이며 main 미반영. PR #1 HEAD의 checks 및 로컬 30개 회귀의 CI 성공으로 승계하지 않음. Kerbe PR #4 CI와도 별개. [CI 관계](proposals/README.md) |
| P0-V2 | PR 본문 갱신 | 개선 후 통과 | gh 2.46.0 projectCards 오류→동일 PR REST PATCH→GET 일치. 인증/권한 변경 없음 |
| P0-S1 | 기존 서비스 보호 | 기존 관찰 재사용·미조작 | 관찰 당시 rootless Docker, system docker/socket disabled·inactive, Minecraft 4개 healthy·Paseo active. 이번 M에서 재시작/삭제/초기화·설정 조작 없음. 과거 관찰로 현재 전체 데이터 무결성을 보장하지 않음 |
| P0-S2 | Direct 무인증 요청 거부 | 통과 | Public WSS에 인증정보 없이 hello→password_required / 4401. [실측](evidence/direct-no-auth.json) |
| P0-S3 | 비밀정보·자동 Archive | 부분 검증 | 주요 credential 파일 0600, raw 값 미출력. autoArchiveAfterMerge 설정 없음·설치 코드 기본 false. runtime/UI의 별도 override까지 보장하지 않음 |

## P1 진입 판정

Kerbe의 ignore만 바꾸는 S에 필요한 경로를 통과해 실제 작업에 진입했다.
[PR #4](https://github.com/shotgun1107/kerbe/pull/4)의 구현·검증·독립 리뷰·원격 전달까지 마쳤다.
이후 사람의 squash merge와 K12 fetch 결과를 대조해 S 완주를 확인했다.
M도 같은 전용 Worktree에서 Claude→Codex 순차 교대, 구현·검증·독립 리뷰와 Draft 전달까지 마쳤다.
사람의 M Ready/merge와 실제 main 확인은 아직이다.

| 순서 | 성공 기준 | 현재 판정·정확한 다음 행동 |
|---|---|---|
| 선행 | 사용할 Provider 승인/차단·branch push/PR·작업에 필요한 setup 경로 확정 | S는 Work·C의 동일 프로필과 ignore-only 쓰기 경로를 대조했다. M은 새 Work·C/Build·X의 native·task 원격 쓰기·신규 venv/import·fixture TMPDIR을 실제 확인한 뒤 진입했다. [범위별 조건](REVISION.md#p1-s-첫-후보와-범위별-진입-조건) |
| S | 한 writer의 요청→검증→리뷰→사람 merge→main 확인 | **완주 확인.** PR #4 후보 f0f73a8…가 사람에 의해 squash merge됨. 실제 main `efd539a6ab5cd05a2c7f33cf3b8db13c021458be`와 K12 origin/main·후보의 전체 tree 일치, main 필수 CI 2개 성공. 기존 42개·리뷰·제품 CI 증거 재사용. [E11](EVIDENCE.md#e11-s-main-반영과-m-진입) |
| M | 종료 확인·handoff·Git/runtime 대조만으로 반대 Provider가 Next 실행 | **교대·개발·전달 통과 / 사람 채택 대기.** Claude 종료·push/runtime 확인 후 새 Codex가 기록만으로 복원. 최종 `7ff930cefd308c37702aff7c7efd48fc4c9e4c9b`, 로컬 선택22 OK·전체 Ran185 OK(skip2)·wheel, 새 Windows/Ubuntu CI 각185 OK(skip1/2), 독립 P2 해결·새 P0/P1/P2 0. [PR #5](https://github.com/shotgun1107/kerbe/pull/5)를 사람이 Ready/merge한 뒤 main 대조 필요 |
| 병렬 | S/M 후 독립 결과 2개 완주·개입 부담 비교 | 미실행. 과거 A/B는 같은 목표 경쟁·승인 조건 불일치·미커밋이라 대체 불가 |
| 모바일 | 사람이 Acceptance·증거·미확인·후보 SHA 판단 | 미실행. 이 PR을 검토 후보로 제공했으나 실제 모바일 판단은 사람에게 남음 |

## 개선과 남은 결정

- **적용·검증:** 읽기 전용 연결 진단, ops env/runtime ignore, REST PR 본문 복구, Heartbeat 정리 도구 30개 회귀와 실제 idle 1회 수명·삭제. S `.gitignore` 3줄 개선은 사람의 main 채택 및 K12 대조까지 확인했다. M의 오류 계약·traceback 보정은 Draft 후보로 검증했고, 외부 task TMPDIR과 실제 실행 종료에 따른 교대 절차를 실측했다.
- **검증된 설치 후보:** scripts/k12-pre-push. 기존 Kerbe hook과 byte 동일. ops 설치·Git 공통 설정 변경은 사람이 해야 한다.
- **정책 검토:** ops 보호 기능 확보 또는 private 유지 시 보호 공백 수용 여부, 이번 S/M 밖의 writer 경로, Kerbe bootstrap 채택, ops CI PR #2의 사람이 수행할 통합 순서와 새 후보 검증. S는 이미 사람이 채택했다. 명령별 Supervisor 승인을 프로젝트 전체 영구 허용으로 확대하지 않는다.
- **아직 주장하지 않는 것:** 전체 P0/P1 완료, Full Access에서 merge 기술적 차단 보장, 모바일 판단 성공, runtime 전체 백업·격리, 자동 복구/정리 보장.

근거는 [EVIDENCE](EVIDENCE.md), 복구는 [RECOVERY](RECOVERY.md), 검증된 변경과 미검증 제안을 구분한 개정안은 [REVISION](REVISION.md)을 따른다.
