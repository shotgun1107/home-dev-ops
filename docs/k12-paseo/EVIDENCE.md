# 실측 근거와 결함 재현

2026-10-09 KST 수집. 원문/세션 전문·인증값은 저장하지 않는다. 판정은 실행 범위에 한정한다.
[실제 상태 JSON](evidence/live-snapshot.json), [21개 회귀 결과](evidence/regression.txt), [기존 hook 직접 시험](evidence/existing-guard.txt). 실행 시각·Python/Git 버전·시험한 파일 hash를 출력에 보존했다.

## E1 Heartbeat

### 조건과 원인

- Paseo 0.10.3, Codex 0.160.1. 같은 ~/.paseo, 기존 PID 2316/worker 2365, loopback 6767.
- 최초 sandbox와 재개 전 `paseo status --json`: pid null / localDaemon stopped / connectedDaemon not_probed. Heartbeat 생성은 DAEMON_NOT_RUNNING.
- 승인된 host 실행: running/reachable. 데몬은 10/07부터 실행 중이며 새로 시작하지 않았다.
- 재현: `codex sandbox -- paseo status --json`. Codex 0.160.1은 `sandbox -- <command>` 문법이다. 잘못 시도한 `sandbox linux --help`는 execvp linux 실패, 상태 변경 없음.
- sandbox 안 PID는 2, daemon PID 2316은 /proc에 없음. host에서는 존재. PID/network namespace inode가 각각 다르다. 현재 CLI 보조 재현이며 이전 Paseo 실측과 구분한다.
- 설치 파일 `@getpaseo/server/dist/src/server/daemon-instance.js:29–31`은 isPidLockOwnerRunning=false면 null 반환. `pid-lock.js:33–41`은 process.kill(pid,0) 실패가 EPERM이 아니면 false다. 격리된 PID 공간의 결과를 호스트 daemon 중지로 해석하는 진단 결함이다.
- 네트워크 namespace도 달라 --host 문자열만 바꾸면 해결된다고 주장하지 않는다. 임의 재시작은 금지했다.

### 개선과 재시험

[진단 도구](../../scripts/paseo_preflight.py)는 pid 메타데이터·현재 /proc 가시성·CLI 연결 결과만 읽는다.
credential·CLI raw stderr 출력, start/restart/fallback 연결이 없다. 보이지 않는 PID는 stale일 수도 있으므로 running이라고 추정하지 않는다.

| 동일 조건 | 기존 CLI | 개선 도구 |
|---|---|---|
| 호스트 | running/reachable | reachable, exit 0 |
| Codex sandbox | stopped/not_probed | recorded-pid-not-visible, exit 2, 승인된 host 대조 안내 |

작업 cwd는 이 ops Worktree다. host 명령은 `python3 -B scripts/paseo_preflight.py`, sandbox 명령은 `codex sandbox -- python3 -B scripts/paseo_preflight.py`다.
[실제 출력](evidence/paseo-preflight.json). CLI 원문 판정은 `cli_local_daemon_raw`로 명시하고 전체 판정은 verdict/connection_verified를 따른다. CLI 부재·timeout·실행 오류·비정상 종료·잘못된 출력을 구분한다. 9개 회귀는 namespace 불일치, stale PID, 연결 미확인,
정상 연결, 비밀 출력 차단, 잘못된 메타데이터/timeout을 검사한다. sandbox 접근 자체를 여는 변경은 없다.

### 생성·수명

- ae4c33cd: 승인된 host에서 생성, 사용자의 일시중단 요청 후 delete 성공.
- f854c66d: 재개한 기존 Supervisor에 생성. target c9bb4cb7-d656-4fb6-a6a5-e8fbcd3745cd, cron `*/20 * * * *`, Asia/Seoul, maxRuns 72, expiresAt `2026-10-10T13:08:05.160Z`.
- 설정 확인은 ~/.paseo/schedules/f854c66d.json의 cadence/target/runs 필드로 수행. 최종 상태는 PR handoff를 따른다.
- `paseo schedule inspect f854c66d`는 존재해도 not found. 설치 CLI commands/schedule/inspect.js:12가 target.type != new-agent를 의도적으로 제외한다. 일반 schedule ls/logs로 Heartbeat 부재를 단정하지 않는다. 파일을 편집해서 고치지 않는다.
- 22:20 KST 실제 cron tick은 `already has an active run`으로 failed였다. 중복 실행은 시작되지 않았고 nextRunAt=22:40으로 갱신됐다. [기록](evidence/heartbeat-tick.json). 자동 재개 통과로 세지 않는다.
- 등록은 idle 세션 재개 완료와 다르다. daemon·인증·모드·세션·writer 소유권이 유지돼야 한다. Heartbeat가 없거나 실패하면 자동 재개는 보장되지 않는다.

## E2 Provider

설치 버전은 Claude 2.1.292, Codex 0.160.1. 과거 증거를 버전/모드가 변경된 경로에 자동 승계하지 않는다.
로컬 증거 별칭(행 번호=JSONL 물리 행, 시각=UTC):

- C-MERGE: ~/.codex/sessions/2026/10/08/rollout-2026-10-08T19-38-26-01a11b17-c9d2-72f0-91f0-451e14eaa13a.jsonl
- C-AB: ~/.codex/sessions/2026/10/08/rollout-2026-10-08T22-10-48-01a11ba3-4a53-7d40-8a66-fbb4e14f0531.jsonl
- C-REVIEW: ~/.codex/sessions/2026/10/08/rollout-2026-10-08T21-23-01-01a11b77-8c04-79d2-8fd1-cb6028dc35dd.jsonl
- CL-WRITER: ~/.claude/projects/-home-shotgun1107--paseo-worktrees-007unhvc-juvenile-ostrich/4a9e801d-b672-41e4-b220-06d10474e769.jsonl
- CL-AUTO: ~/.claude/projects/-home-shotgun1107-paseo-ab-tests-20261008-221045-claude/06718c6f-59ff-4e14-ade6-11357d0b8026.jsonl
- CL-AB: 같은 디렉터리의 f601b8f1-a5ee-4bba-b485-c201cfc94ecc.jsonl
- CL-P0: ~/.claude/projects/-home-shotgun1107-workspace-kerbe/2bdc0cfc-b6eb-4462-84c3-ce6d1cb57946.jsonl

| 증거 | 결과·범위 |
|---|---|
| C-MERGE:8,24,26 / 10/08 10:38:39Z | on-request/workspace-write/network false. 지정 PR 999999·zero match-head 호출이 CreateProcess forbidden으로 실행 전 거부. 실제 PR로 재시험하지 않음 |
| CL-AUTO:38,46,49,52 / 10/08 15:49Z | Auto에서 merge Bash 실행 전 거부. deny/classifier 중 결정 주체 미확인 |
| CL-AUTO:55,58–65,68,71,74–81 | PR/base/ls-remote 정상 출력. 모델의 승인 대기 없음 보고와 도구 응답 증거 구분 |
| CL-WRITER:441–446,452 / 10/09 09:51Z | merge 시험과 함께 요청한 읽기 전용 gh pr view도 Auto-Mode Bypass로 거부 |
| CL-WRITER:455,458–461 / 11:15–11:16Z | 이후 단독 PR 조회 성공. 묶음 프롬프트가 원인이라는 설명은 가설. classifier 우회를 위한 명령 분할/변형을 권하지 않음 |
| CL-P0:13, CL-WRITER:12 | AGENTS instructions attachment 확인. CLAUDE import의 신규 세션 중복 로딩은 미확인 |
| C-AB:8,56,65 | 기본 workspace-write에서 문서 편집·링크 48개/구문/규칙 보존 검사 성공. 원격 쓰기 검증 아님 |

현재 ~/.claude/settings.json에는 `Bash(gh pr merge *)` deny,
~/.codex/rules/k12-pilot.rules에는 `[gh, pr, merge]` forbidden이 있다.
파일 존재를 로딩/전 경로 보장으로 바꾸지 않는다. 두 설정은 읽기만 했다.

설치 provider 코드는 Claude settingSources=user/project/local,
Codex auto=on-request/workspace-write/user, auto-review=auto_review,
full-access=never/danger-full-access/user로 정의한다. 현재 Supervisor는 마지막 모드다.
sandbox·승인 정책 역할은 [OpenAI 공식 문서](https://learn.chatgpt.com/docs/agent-approvals-security)와 대조했고 K12 판단은 실측에 근거한다.

Claude Plan은 기술적 read-only가 아니다. 과거 별도 session
~/.claude/projects/-home-shotgun1107-workspace-kerbe/1b785c6d-b855-4a61-b748-e100caed3229.jsonl:33–34에서
plan 파일 Write 성공. 해당 세션 merge 시험은 미실행이었다.

## E3 Git

Kerbe [Ruleset 24715075](https://github.com/shotgun1107/kerbe/rules/24715075)·effective rules GET을 모두 확인했다.
classic protection GET 404만으로 보호가 없다고 판정하면 안 된다. private ops는 두 보호 API 모두 403이다.
현재 OAuth scope 헤더는 gist/read:org/repo/workflow, 두 repo 계정 권한 admin=true다.
토큰 문자열은 출력하지 않았다. 최소 범위 fine-grained 인증 검증 완료가 아니며 전환하지 않았다.

기존 hook: ~/workspace/kerbe/.git/hooks/pre-push, hooksPath override 없음.
SHA-256 `d9488d892f3da43cbd2cabf7fb7a9e98639d70e62d34518243bbdb04ac8dafdc`.
[설치 후보](../../scripts/k12-pre-push)는 byte 동일하며 활성 hook에 설치하지 않았다.

[시험](../../tests/test_pre_push.py)은 임시 SHA-1 Git 저장소의 실제 commit graph에 pre-push stdin을 입력한다.
main 생성/FF, 삭제, rewind, divergence, unknown remote object, 복수 ref 차단 및
새 topic/FF/unchanged/tag/empty를 확인했다. 기존 hook 12/12, 후보 12/12 통과.
네트워크 push나 실제 main/삭제/force 시도는 없다. Git→hook 호출 통합·LFS 왕복·SHA-256 저장소까지 검증한 것은 아니다.
두 repo에 현재 tracked .gitattributes/LFS 계약이 없어 LFS 연계는 미적용 범위다.

home-dev-ops에는 활성 hook과 env ignore가 없었다. .gitignore 추가 후 .env/.env.local/.venv/.runtime 제외,
.env.example 추적 가능을 git check-ignore --no-index로 확인했다. Kerbe의 .env.local 누락은 발견만 기록한다.
ignore는 비밀 검사와 명시적 stage를 대체하지 않는다.

## E4 Runtime

Kerbe PR #2: HEAD `1a02ad66780604909d49044ddfe14c803b0332f9`, base `026a8a0e4cd6a0a7782f90f0848e641b33759a3e`.
[CI](https://github.com/shotgun1107/kerbe/actions/runs/37779471349) Ubuntu/Windows success를 현재 GET으로 확인했다.
두 job은 Python 3.12 일반 설치·unittest·wheel 경로다.

[운영자 실측 댓글](https://github.com/shotgun1107/kerbe/pull/2#issuecomment-6080143637)은 같은 SHA에서
Python 3.14.4 worktree .venv/editable/import 검사, 182 tests OK(skipped=2), wheel 성공을 기록한다.
운영자가 직접 실행했다고 게시한 증거이며 이번 agent의 전체 테스트 실행으로 소급하지 않는다.
이전 PYTHONPATH 보조 검사와 ensurepip 실패는 후속 증거로 갱신하되 역사적 실패를 지우지 않는다.

이번 재확인: PYTHONPATH를 제거한 subprocess와 .venv/bin/python -B로
sys.prefix가 juvenile-ostrich/.venv이며 source가 그 worktree/src 아래라는 assert 통과.
시작·종료 Git clean. 전체 제품 테스트/설치/wheel은 중복 실행하지 않았다.

base/head 모두 paseo.json/dev-setup 없음. uv.lock/frozen 설치 경로가 있다고 가정하지 않는다.
실제 Kerbe init/status는 계정·원본 Codex 홈·Credential Manager에 닿을 수 있어 실행하지 않았다.
임시 config 하나로 runtime 전체가 격리됐다고 판정하지 않는다.

user paseo/docker active, system docker.service/docker.socket disabled, Docker securityOptions rootless,
Minecraft/geyser/viaproxy/backup 4개 healthy. docker/lxd 그룹 없음. 서비스·volume·prune 조작은 하지 않았다.
[추가 관찰 증거](evidence/additional-observations.json)에 credential mode·system units·groups·Docker securityOptions를 저장했다. PID 2041(node)이 2316(Paseo supervisor)의 부모이고 2365(daemon)가 그 자식임을 ps로 확인했다. unit MainPID와 daemon PID가 다른 이유가 이 process chain이다. 관찰 시점 상태이며 내부 데이터 무결성 전체 검사는 아니다.

Public Direct 추가 시험: /ws에 Authorization/cookie/hello auth 없이 한 번 연결,
protocolVersion 1·hello_rejection capability 전송→hello.rejected/password_required, close 4401.
agent/session 조작 RPC는 보내지 않았다. TLS 성공·실제 거부 범위이며 relay로 확대하지 않는다.

## E5 Review

Codex 리뷰 원문·SHA·대리 게시 표기를 현재 GitHub에서 읽었다.

- [2a66bb8… 최초 리뷰](https://github.com/shotgun1107/kerbe/pull/2#issuecomment-6063013414)
- [1a02ad6… 재리뷰](https://github.com/shotgun1107/kerbe/pull/2#issuecomment-6063025988)

CL-WRITER:399,412,430의 게시/재조회와 일치. “P0 0건”은 리뷰 심각도이지 운영 P0 완주가 아니다.
C-REVIEW의 직접 게시 경로는 sandbox 네트워크 실패로 권한 미확인. 원문→writer 대리 게시는 실측 완료다.

gh 2.46.0의 gh pr edit --body-file은 CL-WRITER:425,430에서 실패했고 ops #1에서도
Projects classic repository.pullRequest.projectCards GraphQL 오류로 재현됐다.
권한 확대/전역 업그레이드 없이 같은 승인 범위의 PR body를 REST PATCH로 갱신하고
GET으로 body·Draft 유지·HEAD를 확인했다. 파일 기반 -F body=@...는 [gh api 공식 문서](https://cli.github.com/manual/gh_api)와 대조했다.

## E6 과거 A/B와 P1의 경계

~/paseo-ab-tests/20261008-221045/{claude,codex}는 둘 다 detached `2a66bb8b140af21af95e3f4398cd833d45fcd5d0`.
둘 다 AGENTS/CONTRIBUTING 미커밋 수정이 있어 보존했다. 중복 Worktree 생성·정리 없음.
Claude 경로에는 unarchived workspace 2개, 원본 Kerbe에도 과거 review/test workspace 여러 개가 남아 있다.
모두 idle인 현재 상태만 확인했으며 과거 동시 쓰기를 주장하지 않는다.

CL-AB:3,59,61,65,71,77은 default와 A/B test: unapproved operation 거부,
:86,92–112는 사용자 acceptEdits 전환 후 편집 성공, :120은 Phase 2: unapproved operation Bash 거부다.
승인 하네스 조건이 달라 provider 능력/속도 비교로 채택하지 않는다.
같은 목표의 경쟁 실험이며 commit/push/install/network가 금지돼 있었다.
S/M 선행 완주나 독립 결과 2개 병렬 완주의 증거가 아니다.

CL-P0:179는 과거 git lfs track/ls-files/env 진단 중 hook/config/.git/lfs 생성 부작용을 보고한다.
원복 완료 미확인. 이번에는 재실행하거나 과거 자원을 삭제하지 않았다.

## 보존과 검증 한계

원문 SHA-256은 [snapshot](evidence/live-snapshot.json)에 기록했다. 원문 Markdown 두 칸 줄바꿈 때문에
전체 git diff --check는 21개 공백 경고를 낸다. 원문을 변조하지 않고 신규 파일 검사를 분리했다.
흔한 token/private-key 패턴 검사는 통과했지만 모든 비밀 탐지의 보장은 아니다.
자료가 없는 모바일 판단·실제 Provider writer 교대·main 채택·파괴적 복구는 미실행으로 남긴다.

## E7 이번 독립 리뷰와 CI 공백

Claude reviewer b8e68af1은 고정 SHA `2873a57a804c96225b774bc1c9f86dae87628db3`를 읽기 전용으로 검토했다.
[원문 대리 게시](https://github.com/shotgun1107/home-dev-ops/pull/1#issuecomment-6081867053)는 GitHub GET으로 원문 일치를 확인했다.
Medium 1건(Full Access 예외/보호 공백 명시), Low 8건을 반영했다. Plan 파일 쓰기 없이 종료·idle을 확인하고 writer가 수정했다.
현 후보에는 GitHub checks가 없어 통과로 기록하지 않는다. [CI 제안](proposals/README.md)은 workflow patch로 보존하고 사람 적용 후 실행을 기다린다.
