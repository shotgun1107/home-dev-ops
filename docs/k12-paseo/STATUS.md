# K12 Paseo P0/P1 검증 현황

2026-10-09 KST 실측 시작. **미션 진행 중, P0 미완료, P1 미진입.**
이 문서는 운영 결과 보고이며 최신 재개 지점과 writer 소유권은 이 branch의 Draft PR에서 관리한다.

## 기준과 소유권

- 정본: [v2.4 원문](source/K12_Paseo_v2.4.md), [AGENTS 초안](source/K12_AGENTS_draft.md). 입력 파일을 수정하지 않고 그대로 복사했다.
- 원문이 참조하는 `K12_Paseo_Review_History.md`는 입력 폴더에 없어 미확인이다.
- 작업 저장소: `shotgun1107/home-dev-ops`, branch `docs/k12-paseo-autopilot`.
- 시작 HEAD: `bf50f2bdb44e4d71fc29b31dcb0629719a345a95`. 재개 시 tracked/untracked 변경 없음.
- writer: 기존 Paseo Codex Supervisor `c9bb4cb7-d656-4fb6-a6a5-e8fbcd3745cd` 한 명. 추가 조사는 읽기 전용이다.
- 사용자가 Full Access로 변경한 뒤 재개했다. 현재 세션은 기본 sandbox 승인 경로의 통과 증거로 사용하지 않는다. 권한·인증·보호 규칙은 agent가 변경하지 않는다.

## 현재 확인한 결과

| 항목 | 판정 | 근거와 한계 |
|---|---|---|
| 이전 중단의 Git 무변경 보고 | 통과 | 재개 시 clean, 초기 HEAD와 일치. GitHub의 기존 open PR도 없음 |
| Paseo 데몬 실행 | 통과 | 0.10.3, 기존 supervisor PID 2316 / worker 2365, host에서 reachable. 재시작하지 않음 |
| Heartbeat 기본 연결 | 실패 재현·경로 확인 | sandbox에서는 `pid:null`, `localDaemon:stopped`; 승인된 host에서는 같은 home·endpoint가 running/reachable. daemon 장애라고 단정하면 안 됨 |
| Heartbeat 생성 | 통과(등록) | 호스트 경로에서 `ae4c33cd` 생성 후 사용자 일시중단 때 삭제. 재개 후 `f854c66d` 생성. 20분 간격, Asia/Seoul, 72회/24h 상한. 실제 주기 실행은 아직 미확인 |
| Kerbe PR #2 | 통과(조회) | Draft/open, HEAD `1a02ad66780604909d49044ddfe14c803b0332f9`, base `026a8a0e4cd6a0a7782f90f0848e641b33759a3e` |
| Kerbe 필수 CI | 통과 | 위 HEAD의 `test (ubuntu-latest)`와 `test (windows-latest)` success. [run 37779471349](https://github.com/shotgun1107/kerbe/actions/runs/37779471349) |
| Kerbe main Ruleset | 통과(구성 조회) | active, main PR 필수, 삭제/non-FF 금지, required checks 2개, bypass actors 없음/current user bypass never. 실제 위험 push는 하지 않음 |
| home-dev-ops 보호 규칙 | 차단 | private repo에 rulesets·branch protection GET 모두 HTTP 403, Pro/public 필요 응답. 공개 전환이나 계정 변경은 하지 않음 |
| pre-push guard | 부분 확인 | Kerbe 실제 hook 있음. home-dev-ops는 sample만 있고 활성 hook 없음. 동작 검증은 계속 진행 |
| Minecraft·Docker·Paseo | 기준 상태 확보 | rootless Docker, minecraft 관련 4개 container healthy, user Docker/Paseo active. 서비스 변경 없음 |
| Kerbe Python 환경 | 기존 증거 있음 | PR #2 comment 6080143637에 운영자 실측: worktree .venv editable/import 검사, 182 tests OK(skipped=2), wheel 성공. 재실행 여부는 증거 검토 후 판단 |

## 계속 확인할 항목

P0: 기존 merge 차단·Claude Auto·Codex 기본 모드의 실제 기록, AGENTS 로딩,
guard의 격리 시험, runtime/setup 경계, 리뷰 대리 게시와 복구 경로,
설정과 문서의 차이. 읽을 수 없는 기록은 미확인으로 남긴다.

P1: S의 사람 merge까지 완주, M 세션/Provider 교대 복원, 이후 독립 결과 2개
병렬 비교, 모바일 실제 판단. P0 조건과 선행 작업의 충족 증거가 있어야 진입한다.
PR #2가 Draft/open인 상태를 완주로 세지 않는다.

## 남은 승인 및 위험

- home-dev-ops 보호 규칙과 hook 설치는 정책 변경이므로 사람 검토 대상이다.
- 현재 Full Access는 사용자 선택에 따른 이번 Supervisor 실행 조건이다. v2.4 기본값 변경으로 확정하지 않는다.
- Heartbeat 등록만으로 자동 재개를 보장하지 않는다. 연결·스케줄 실행·동일 세션 대상 여부를 더 확인한다.
- AI merge, main 직접 push, Ready 전환, 자동 Archive, 운영 데이터 삭제·초기화는 수행하지 않는다.
