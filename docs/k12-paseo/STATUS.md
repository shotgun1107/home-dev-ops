# K12 Paseo P0/P1 검증 현황

2026-10-09 KST. **P0 부분 검증, P1 미진입. 미션 전체 완료가 아니다.**
최신 후보 SHA·writer 상태·Next·Heartbeat 상태는 [Draft PR #1](https://github.com/shotgun1107/home-dev-ops/pull/1)의 handoff를 따른다.

## 기준

- [v2.4 원문](source/K12_Paseo_v2.4.md)과 [AGENTS 초안](source/K12_AGENTS_draft.md)은 입력과 byte 동일. 원문 참조 `K12_Paseo_Review_History.md`는 입력에 없어 미확인.
- 기존 `docs/k12-paseo-autopilot` Worktree 재사용. 시작 HEAD `bf50f2bdb44e4d71fc29b31dcb0629719a345a95`, 재개 때 clean·open PR 없음 확인.
- 기존 Supervisor `c9bb4cb7-d656-4fb6-a6a5-e8fbcd3745cd`가 유일한 writer. 증거 조사는 읽기 전용 agent가 수행했다.
- 사용자가 이번 Supervisor를 Full Access로 전환했다. 기본 승인 경로 검증과 분리하며, agent가 권한 설정을 변경한 것은 아니다.
- ops main에는 서버 보호를 사용할 수 없고 활성 hook도 없다. 현 Full Access 경로의 Provider 차단은 미검증이므로 **확인된 기술적 main/merge 차단에 의존할 수 없으며 운영 규칙 준수에 의존한다.** 사용자 선택으로 실행한 이번 보고·격리 개선은 v2.4 기본 개발 경로의 예외로 기록한다. 이 경로의 P0-A는 미통과다. AI merge 활성화 예외나 merge 승인은 아니다.
- **통과**는 표에 적힌 시험 범위만 뜻한다. 정적 검토, 구성 조회, 실제 실행, 사용자 보고 재사용을 구분한다. skipped는 실행 통과로 세지 않는다.

## P0

| ID | 항목·성공 기준 | 판정 | 증거·제한 |
|---|---|---|---|
| P0-H1 | 기존 daemon 연결 원인 식별·안전한 생성 | 통과(호스트 경로) | PID namespace로 기본 탐색 실패 재현, 기존 host PID에 연결·Heartbeat 생성. sandbox 연결 자체는 해결하지 않음. [E1](EVIDENCE.md#e1-heartbeat) |
| P0-H2 | 자동 재개·중복 방지·만료·정리 | 부분 검증 | 생성·소유·상한·삭제 확인. 22:20 tick은 active run 때문에 failed, 중복 실행 없음. idle 재개 미확인 |
| P0-A1 | Codex 기본 모드·merge 실행 전 차단 | 과거 gh pr merge 형태 통과 / 현 Full Access 미통과 | 과거 Paseo on-request/workspace-write의 forbidden 거부. 현재 Full Access를 대체 증거로 쓰지 않음. [E2](EVIDENCE.md#e2-provider) |
| P0-A2 | Claude Auto·merge deny 실제 적용 | 부분 검증 | gh pr merge 형태의 실행 전 거부 확인, deny rule인지 classifier인지 미확인. 정상 조회 거부 사례도 있어 writer 승인 안정성은 보류 |
| P0-A3 | source 편집·commit·branch push·Draft PR | 경로별 통과 | 과거 Claude PR #2, 현재 Codex Full Access PR #1. Codex 기본 모드 원격 쓰기까지 동일 판정하지 않음 |
| P0-G1 | Kerbe 서버 측 main 보호 | 통과(실효 구성 조회) | ruleset active, PR 필수, 삭제/non-FF 금지, 2 CI strict, bypass 없음. 위험 push/merge 실험은 안 함 |
| P0-G2 | home-dev-ops 서버 측 보호 | 차단 | private repo 보호 API 403: Pro/public 필요. 공개 전환·구독 변경은 사람 결정. [E3](EVIDENCE.md#e3-git) |
| P0-G3 | pre-push 사고 방지 | Kerbe 로직 통과 / ops 설치 대기 | 실제 Kerbe hook·동일 후보 각각 12개 격리 시험. ops 활성 hook 없음. 설치/공통 Git 설정 변경 미실행 |
| P0-W1 | Worktree·writer 소유권 | 현재 미션 통과 / 과거 결함 | 현재 하나의 기존 workspace·writer. 과거 Claude A/B 경로에 unarchived workspace 2개. 모두 idle이며 동시 writer 실행 증거는 아님 |
| P0-R1 | Python setup·import 격리 | 확인 범위 통과 | PR #2 운영자 실측 182 tests OK, skipped 2·wheel. 이번에는 기존 .venv/source 경로 재확인, clean 유지. [E4](EVIDENCE.md#e4-runtime) |
| P0-R2 | 새 Worktree setup·runtime 분리 | 미실행/제한 | base/head 모두 paseo.json/dev-setup 없음. 실제 CLI 계정·장부·Credential Manager, DB/volume 격리 미검증. 해당 경로 보류 |
| P0-V1 | 고정 SHA 리뷰·대리 게시 복구 | 통과 | Codex→Claude writer 대리 게시 2건·GET 확인. reviewer 직접 게시 권한은 미확인. [E5](EVIDENCE.md#e5-review) |
| P0-C1 | 이 PR의 필요한 CI | 사람 적용 대기 | 현재 GitHub check-runs=[]; [workflow patch](proposals/home-dev-ops-ci.patch) 준비·형식 검사만 완료. 실제 CI 미실행 |
| P0-V2 | PR 본문 갱신 | 개선 후 통과 | gh 2.46.0 projectCards 오류→동일 PR REST PATCH→GET 일치. 인증/권한 변경 없음 |
| P0-S1 | 기존 서비스 보호 | 현재 상태 확인 | rootless Docker, system docker/socket disabled·inactive, Minecraft 4개 healthy·Paseo active. 재시작/삭제/초기화 없음 |
| P0-S2 | Direct 무인증 요청 거부 | 통과 | Public WSS에 인증정보 없이 hello→password_required / 4401. [실측](evidence/direct-no-auth.json) |
| P0-S3 | 비밀정보·자동 Archive | 부분 검증 | 주요 credential 파일 0600, raw 값 미출력. autoArchiveAfterMerge 설정 없음·설치 코드 기본 false. runtime/UI의 별도 override까지 보장하지 않음 |

## P1 진입 판정

P0 미확인 경로를 제외한 문서 검토·격리 시험은 계속할 수 있다. 실제 파일럿은 다음 선행 조건 때문에 미진입이다.

| 순서 | 성공 기준 | 현재 판정·정확한 다음 행동 |
|---|---|---|
| 선행 | 사용할 Provider 승인/차단·setup 경로 확정 | Claude deny 출처 확인 또는 검증된 Codex 기본 경로 선택. 새 Worktree setup 방식 검토·확정 |
| S | 한 writer의 요청→검증→리뷰→사람 merge→main 확인 | Kerbe #2 Draft/open. S 후보로 채택할지도 사람 판단 필요. 사용자가 Ready/merge를 금지했으므로 agent가 완료시킬 수 없음 |
| M | 종료 확인·handoff·Git/runtime 대조만으로 반대 Provider가 Next 실행 | 미실행. S·선행 setup 반영 후 하나의 M 작업에서 시험 |
| 병렬 | S/M 후 독립 결과 2개 완주·개입 부담 비교 | 미실행. 과거 A/B는 같은 목표 경쟁·승인 조건 불일치·미커밋이라 대체 불가 |
| 모바일 | 사람이 Acceptance·증거·미확인·후보 SHA 판단 | 미실행. 이 PR을 검토 후보로 제공했으나 실제 모바일 판단은 사람에게 남음 |

## 개선과 남은 결정

- **적용·검증:** 읽기 전용 연결 진단, 이 Worktree의 env/runtime ignore, REST PR 본문 복구 경로. 회귀 21개 통과, host/sandbox 차이 실제 재시험.
- **검증된 설치 후보:** scripts/k12-pre-push. 기존 Kerbe hook과 byte 동일. ops 설치·Git 공통 설정 변경은 사람이 해야 한다.
- **정책 검토:** ops 보호 기능 확보 또는 private 유지 시 보호 공백 수용 여부, Claude Auto 사용할 경로, Kerbe bootstrap/setup 반영과 S 선정, ops workflow patch 사람 적용·실제 CI.
- **아직 주장하지 않는 것:** 전체 P0/P1 완료, Full Access에서 merge 기술적 차단 보장, 모바일 판단 성공, runtime 전체 백업·격리, 자동 복구/정리 보장.

근거는 [EVIDENCE](EVIDENCE.md), 복구는 [RECOVERY](RECOVERY.md), 검증된 변경과 미검증 제안을 구분한 개정안은 [REVISION](REVISION.md)을 따른다.
