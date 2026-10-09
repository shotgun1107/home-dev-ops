# 실측 근거와 결함 재현

2026-10-09~10 KST 수집. 원문/세션 전문·인증값은 저장하지 않는다. 판정은 실행 범위에 한정한다.
[실제 상태 JSON](evidence/live-snapshot.json), [21개 회귀 결과](evidence/regression.txt), [기존 hook 직접 시험](evidence/existing-guard.txt). 일괄 수집 시작 시각·Python/Git 버전·시험한 파일 hash를 출력에 보존했다.

## E1 Heartbeat

### 조건과 원인

- Paseo 0.10.3, Codex 0.160.1. 같은 ~/.paseo, loopback 6767. `paseo.pid`의 lock 소유자는 supervisor PID 2316이고, daemon worker는 PID 2365다. preflight의 recorded_pid는 supervisor를 뜻한다.
- 최초 sandbox와 재개 전 `paseo status --json`: pid null / localDaemon stopped / connectedDaemon not_probed. Heartbeat 생성은 DAEMON_NOT_RUNNING.
- 승인된 host 실행: running/reachable. 데몬은 10/07부터 실행 중이며 새로 시작하지 않았다.
- 재현: `codex sandbox -- paseo status --json`. Codex 0.160.1은 `sandbox -- <command>` 문법이다. 잘못 시도한 `sandbox linux --help`는 execvp linux 실패, 상태 변경 없음.
- sandbox 안 PID는 2, 기록된 supervisor PID 2316은 /proc에 없음. host에서는 존재. PID/network namespace inode가 각각 다르다. 현재 CLI 보조 재현이며 이전 Paseo 실측과 구분한다.
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
- f854c66d는 22:35:42 KST 정상 `paseo heartbeat delete`의 `{id:f854c66d,status:deleted}` 응답과 파일 부재를 확인했다. native session `01a120af-820b-76e0-9f02-1e3fb9ed575b` JSONL 527/530행(UTC 13:35:40/42)이 출처다. 해당 heartbeat run은 22:20에 이미 failed로 끝났으며, 삭제를 실행한 것은 사용자가 시작한 Supervisor 턴이다. E8의 '그 Heartbeat가 시작한 run 안에서 자기 삭제'와 다르다. Issue #3과 재개 조회에서도 부재를 확인했다.
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
.env.example 추적 가능을 git check-ignore --no-index로 확인했다. 당시 발견한 Kerbe의 .env.local 누락은
이후 E10의 별도 S branch에서 수정·검증했으며 main 채택은 대기 중이다.
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

user paseo/docker active, system docker.service/docker.socket disabled·inactive, Docker securityOptions rootless,
Minecraft/geyser/viaproxy/backup 4개 healthy. docker/lxd 그룹 없음. 서비스·volume·prune 조작은 하지 않았다.
[추가 관찰 증거](evidence/additional-observations.json)에 credential mode·system units·groups·Docker securityOptions를 저장했다. PID 2041(node)이 2316(Paseo supervisor)의 부모이고 2365(daemon worker)가 그 자식임을 ps로 확인했다. unit MainPID·PID lock의 supervisor·daemon worker가 다른 이유가 이 process chain이다. 관찰 시점 상태이며 내부 데이터 무결성 전체 검사는 아니다.

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
이 리뷰 당시 후보에는 GitHub checks가 없었다. 이후 사람이 허용한 별도 CI PR #2에서 실행된 결과와 운영 PR #1의 관계는 [CI 기록](proposals/README.md) 및 E8에 구분한다.

최초 리뷰 지적 반영 후 Claude의 fd8f1f28abf8dab17d3a926f3dfd394e0fc54d6c 재리뷰에서 Medium 이상 없음. 남은 Low 2건은 supervisor/worker 용어와 batch 시각 표기로 수정했다. 최종 후보 리뷰의 원문·SHA는 PR에 보존한다. 그 재리뷰부터 73afc54…까지 코드와 테스트 bytes는 동일했다. Issue #3 이후 추가한 도구·시험은 E8로 구분한다.

## E8 Issue #3 재개와 Heartbeat 정리

### 실제 상태와 CI

2026-10-09 23시 KST [Issue #3](https://github.com/shotgun1107/home-dev-ops/issues/3)과
PR #1·#2·현재 Git을 대조했다. 시작 local/PR #1 HEAD는 `73afc54ba6ba046ad5f527c08d77fd3a20ce2a58`,
clean이었다. Supervisor는 같은 `c9bb4cb7-d656-4fb6-a6a5-e8fbcd3745cd`,
workspace `wks_91760bd37449c714`, 실제 model/thinking=`gpt-6-astra`/`max`, mode=full-access다.
설정 변경이나 새 Supervisor 생성은 하지 않았다. [선별한 API·로컬 증거](evidence/issue-3-resume.json).
ops 보호 API의 403, core.hooksPath unset, 활성 pre-push 부재를 다시 확인했다.

CI PR #2의 head `f069ac35b0553f69f0a485784df0bc4f11341f1b`는 기존 PR #1 HEAD를 부모로 하며
base는 `docs/k12-paseo-autopilot`이다. `.github/workflows/ops-check.yml`만 추가됐고
기존 제안 patch와 byte 일치한다. [run 37941584724](https://github.com/shotgun1107/home-dev-ops/actions/runs/37941584724),
job 113857032952의 실제 로그에서 CPython 3.12.15·`Ran 21 tests`·`OK`를 재조회했다.
그 성공을 이후 PR #1 변경이나 main의 필수 check로 승계하지 않는다. 정리 도구의
시험은 그 CI 실행에 포함되지 않았다. 새 로컬 회귀는 Python 3.14.4에서 최초 28개,
독립 리뷰 반영 후 30개 통과했다.
[명령·파일 hash·결과](evidence/regression-issue-3.json).

### 자기 Heartbeat 삭제 충돌: 재현 → 개선 → 재시험

설치 Paseo 0.10.3 `schedule/service.js`의 `executeSchedule`은 agent의 종료를 기다린 뒤
`finishRun`으로 결과를 저장한다. 이 Heartbeat가 시작한 run 안에서 자기 Heartbeat를 삭제하면
`finishRun`의 `requireSchedule`이 실패한다. 이는 daemon 연결 실패와 별개의 구현 결함이다.

[재현 코드](evidence/heartbeat-cleanup-probe.mjs)는 실제 설치 모듈을 불러오되 새 `/tmp` 저장소,
고정된 가짜 agent ID, 로컬 runner만 사용한다. `start()`를 호출하지 않고 daemon/provider에 연결하지 않는다.
[실측](evidence/heartbeat-cleanup-race.json):

| 조건 | 결과 |
|---|---|
| 실행 안에서 schedule 삭제 | 파일 삭제 후 `Schedule not found: <fixture-id>` 오류, 결과 저장 불가 |
| maxRuns=1 실행 종료 후 삭제 | completed / run succeeded 저장, 삭제 성공, 오류 없음 |

운영 daemon/전역 설치를 패치하지 않았다. [정리 명령](../../scripts/paseo_heartbeat_cleanup.py)은
동일 caller의 `maxRuns=1` Heartbeat가 completed이고 모든 run이 종료됐을 때만
정상 CLI `heartbeat delete`를 호출한다. 최대 15분 대기, CLI 30초 제한, 삭제 응답·파일 부재 확인,
선별한 종료 결과 영수증을 제공한다. 새 세션 실행·자동 재개·권한 변경 기능은 없다.
9개 시험에서 실행 중 대기, timeout 시 무삭제, 타 owner·반복 미션 거부, 실패 상태 보존,
오류 출력 비노출, 잘못된 성공 응답의 파일 부재 확인, run 없는 만료의 판정,
삭제 응답 유실 후에도 삭제 전 run 증거 보존을 검증했다. `--home`/`PASEO_HOME`도 preflight와 같은 우선순위다.

이 보조 명령은 **scheduled agent 턴 밖에서** 기다려야 한다. 같은 턴이 자기 완료를 기다리면 종료되지 않는다.
실제 idle 시험에서는 원래 agent를 한 번 재개하고, 종료 후 정리만 수행하는 한시적 로컬 명령을 사용한다.
다른 자동 재개 방식으로 대체하는 것이 아니다. 새 cron/systemd/daemon은 만들지 않는다.
실제 one-run 수명·삭제의 최종 판정은 PR #1의 해당 ID·receipt를 따른다. 격리 결과만으로 실측 통과를 선언하지 않는다.

[1891c5d… 독립 리뷰 원문](https://github.com/shotgun1107/home-dev-ops/pull/1#issuecomment-6083052359)을 대리 게시하고 GET으로 원문 일치를 확인했다.
Medium 2건(정리/재개 판정 분리, 보조 프로세스 분리 실행)과 Low 4건(삭제 전 영수증 보존,
S 후보 표 일치, 과거 삭제 경위, Paseo home 선택)을 반영했다. receipt의 `runOutcome`은
no-run/failed-run/succeeded-one-run 등을 구분한다. 성공 run 하나여도 실제 idle 전환·자동 알림·동일 세션의
증거 대조 전에는 idle 재개 통과가 아니다(`idleResumeVerifiedByReceipt:false`).

## E9 실제 idle 자동 재개 1회

Heartbeat `427d614c`, run `f398d566-5e92-447c-9020-f5edd6c3024d`가 같은 Supervisor를
**idle에서 실제로 자동 재개했다.** [선별한 관찰 증거](evidence/heartbeat-idle-entry.json)는 다음 순서를 확인한다.

| 시각 (2026-10-09 UTC, KST=+9시간) | 실제 관찰 |
|---|---|
| 14:45:37.682 | 같은 agent 대상 생성, maxRuns=1, nextRunAt=14:48, expiresAt=15:00:37.676 |
| 14:46:53.539 | 기존 native 턴 task_complete (JSONL 937행) |
| 14:46:53.938748 | 분리된 관찰 명령이 agent idle / run 0 / 같은 native session / Astra Max를 읽음 |
| 14:48:00.662 | 등록된 schedule run 시작 |
| 14:48:00.674 | 같은 native session의 새 task_started (939행) |
| 14:48:00.702 | 해당 schedule ID/run ID/고유 marker의 자동 알림 수신 (941행) |

Supervisor·workspace·native session·Worktree가 그대로이며 수동 send/새 agent로 재개하지 않았다.
재개 후 model/thinking/mode는 `gpt-6-astra`/`max`/`full-access`, pending permissions는 없다.
helper PID 718949는 이전 턴 종료 뒤에도 살아 있고 새 process session 및 지정 wrapper 명령이 일치한다.
전체 세션·prompt·credential은 복사하지 않고 위 식별자·이벤트·시각만 보존했다.

이것은 기존 host/Full Access 조건의 **idle 자동 진입 1회 통과**다. 22:20 active-run 거부 시험과 구분한다.
daemon 재시작·sandbox·승인 정책 변경 뒤의 복원까지 보장하지 않는다.
자동 재개 턴에서 보존한 최초 관찰은 running / endedAt=null이었다. 이후 2026-10-10 KST의
S 착수 턴에서 [종료·삭제 영수증](evidence/heartbeat-idle-completion.json)과
[GitHub 게시 원문](https://github.com/shotgun1107/home-dev-ops/pull/1#issuecomment-6083354266)을 대조했다.
같은 run이 14:52:41.857Z에 succeeded로 종료됐고 helper는 completed 확인 후 CLI 삭제를 수행했다.
14:52:42.715659Z의 deleted=true, helper exit=0, 게시 GET 일치와 현재 schedule 파일 부재를 확인했다.
실행 중 자기 삭제 없이 **idle 재개→run 종료→정상 삭제→영수증 게시 1회**가 통과했다.
receipt의 `idleResumeVerifiedByReceipt:false`는 도구가 자체적으로 idle 진입을 판정하지 않는다는 뜻이다.
idle 진입은 앞 표의 native 이벤트·자동 알림·발화 전 관찰을 함께 대조해 판정했다.
현재 Heartbeat는 없으며 이후 자동 재개는 보장되지 않는다.

코드/시험 6개 hash가 기존 30개 회귀 실측과 모두 일치해 테스트를 재실행하지 않았다.
이 관찰 기록만으로 Provider 권한 보호·S/M·병렬·모바일 시험을 통과시키지 않는다.

## E10 Kerbe P1 S — 실제 Writer 경로

2026-10-10 KST [Kerbe Issue #3](https://github.com/shotgun1107/kerbe/issues/3)과
[실행 handoff](https://github.com/shotgun1107/kerbe/issues/3#issuecomment-6083911066)를 읽었다.
시작 main은 `026a8a0e4cd6a0a7782f90f0848e641b33759a3e`, bootstrap PR #2는 Draft·미병합이다.
새 작업에 필요한 보호 경로만 확인했고 제품 runtime/setup 시험을 추가 선행 조건으로 삼지 않았다.

### 기존 증거 재사용과 현재 경로 대조

[선별한 gate 기록](evidence/kerbe-s-gate.json)에 시각·행 번호·설정 hash와 한계를 보존했다.

- **같은 Work·C 조합:** Claude `claude-opus-5-5 / medium / acceptEdits`.
  CL-WRITER의 실제 commit/push/Draft 호출은 143/150/160행, 성공은 144/151/162행이다.
  해당 사용자 턴의 native permissionMode는 acceptEdits였다. 현재 그 과거 agent의 Auto 표시를
  소급 적용하지 않는다. 다른 모드의 원격 쓰기 성공으로도 확대하지 않는다.
- **동일 조합의 merge 실행 전 거부:** f9f790e3의 native
  `~/.claude/projects/-home-shotgun1107-workspace-kerbe/0972fce4-f77c-4fe4-98e4-222044eed621.jsonl`
  3행은 사용자가 PR 999999·zero match-head의 단일 호출을 지정한 acceptEdits 턴이다.
  21행(10/08 10:28:08.512Z)의 실제 호출과 22행(.535Z)의 permission-rule 거부를 확인했다.
  당시와 현재 Claude 버전은 2.1.292다. 별도의 새 위험 호출을 수행하지 않았다.
- **거부 근거의 한계:** matched-rule ID는 없다. permission-rule 필드 하나로 자동 deny를 확정하지 않는다.
  일치 deny가 시험 전에 존재한 기록·변하지 않은 settings mtime/hash, 23ms의 실행 전 거부,
  daemon 집계의 해당 30초 창에 수동 permission response가 없는 점을 함께 대조했다.
  후속 설정 조회는 10:34:11.526Z에 사람이 거절한 별도 요청이다.
  정확한 `gh pr merge` 호출 형태의 권한 계층 거부 증거이며 모든 shell/API 경로 봉쇄는 아니다.
- **현재 조건:** global `Bash(gh pr merge *)` deny 유지, 새 Worktree에 project/local override 없음.
  Ruleset 24715075 active·main PR/strict CI 필수·bypass 없음. 새 Worktree가 상속한 실행 가능한
  pre-push의 hash는 기존 12개 fixture 시험 대상과 같다. 보호 규칙·hook은 수정하지 않았다.

프로젝트 전체 provider/model 기본값 지정은 조사한 설정에서 확인되지 않았다. 다른 프로젝트 기본값을
변경하지 않고, v2.4의 Work·C와 실제 성공 이력이 일치하는 조합을 이번 S에만 재사용했다.
Supervisor는 기존 Astra Max/ops Worktree를 유지한다. 새 Writer는
`010fafb2-a8ee-4b16-bb83-692dc75c3a8d`, workspace `wks_ac69cdda2677c33b`,
branch `fix/ignore-local-dotenv`의 유일한 writer다. 실제 native session
`28804af0-349f-4e75-ab76-15a1dbb074c9`의 3행과 21행에서도 버전·모드·모델·medium을 확인했다.
초기 읽기 전용 턴이 clean/base/hook을 확인한 뒤에만 후속 편집을 허용했다.
동시 writer는 ops Supervisor와 S Writer 두 명이며 원본 Kerbe와 bootstrap은 비writer다.

### 승인 방식에서 발견한 운영 차이

Accept Edits의 일반 Bash는 개별 승인 대기가 발생했다. 현재 사용자가 허용한 조사·작업 branch
쓰기 범위의 요청은 Supervisor가 실제 명령을 읽고 **요청 ID 하나씩** 정상 `permit` 경로로 처리한다.
사람이 클릭한 시험이나 무인 자동 승인 통과로 기록하지 않는다. mode/rules/allow 목록은 변경하지 않는다.

초기 두 번째 요청에는 불필요한 `~/.paseo` 전체 JSON 검색이 섞여 있었다. 실행 전에
`updatedInput`으로 가상 경로 검사·tracked 이름·worktree 조회만 남겼다. 다음 요청에 같은 검색이
포함돼 명시적으로 거부하자 Writer가 재시도 없이 종료했다. 실제 광범위 검색은 실행하지 않았다.
후속 턴은 repo 안의 필요한 작업만 다시 지정했다. 이 거부는 **Supervisor 범위 통제**이며
자동 merge deny 증거가 아니다. CLI의 `permit allow`는 ID를 생략하면 모든 대기를 승인하므로
운영 명령에서는 agent ID와 request ID를 모두 지정한다. 영구 권한 변경을 전송하지 않는다.

[개별 요청 기록](evidence/kerbe-s-permits.json)은 승인 9건(Bash 8건·임시 PR 본문 Write 1건),
거부 1건이다. 승인 9건 중 전역 검색 제거, 시험 명령의 shell 인용 수정, PR 본문의 시점·주체
정정은 `updatedInput`으로 실행 전에 반영했다. 영구 `updatedPermissions`는 전송하지 않았다.
Writer의 최종 '승인 대기로 멈춘 명령 없음'은 종료 시점에 남은 대기가 없다는 사실이며,
그 문구를 실행 도중 승인 개입 0건으로 계산하지 않는다.

### 재현 → 개선 → 재시험 → 독립 검토

- **이전:** 실제 새 Worktree에서 8개 가상 이름을 조회했다. `.env`만 제외되고
  `.env.local`·`.env.production`·`.env.development.local`·`nested/.env.local`은 제외되지 않았다.
  공개 example/sample은 이미 추적 가능했다. tracked dotenv 후보는 파일명 검사에서 없었다.
- **개선:** 기존 `.env` 다음에 `.env.*`, `!.env.example`, `!.env.sample` 3줄만 추가했다.
  `.gitignore` 외의 제품·workflow·권한 파일은 변경하지 않았다. 실제 비밀 파일도 생성·열람하지 않았다.
- **이후:** 같은 경로와 중첩/예외/회귀를 포함한 [42개 가상 경로](evidence/kerbe-s-virtual-paths.json)가
  모두 통과했다. `--no-index -q`의 exit 0/1을 단언했고 다른 코드는 실패로 처리했다.
  `git diff --check` 통과, tracked-but-ignored 목록 없음, 변경 파일은 `.gitignore` 하나였다.
  Supervisor는 Writer의 Python 시험 코드에 포함된 shell 인용 충돌을 실행 전 quoted heredoc으로
  바꿨다. 실제 42개 명령 실행은 같은 Claude Writer의 Bash 도구에서 이뤄졌다.
- **전달:** `f0f73a87821a6b3d990142b948d13c7e2b6e067d`를 `fix/ignore-local-dotenv`에 일반 push해
  [Draft PR #4](https://github.com/shotgun1107/kerbe/pull/4)를 생성했다. [실제 결과](evidence/kerbe-s-result.json)의
  local/remote/PR SHA·clean·Draft·미병합을 대조했다. 원본 main checkout도 clean이었다.
- **독립 검토:** 기존 Codex reviewer `349afd27-7108-41c1-a870-e3be8ef7bef1`가 같은 full SHA를
  정적으로 검토해 P0/P1/P2 모두 0건. [원문](https://github.com/shotgun1107/kerbe/pull/4#issuecomment-6084290891)을
  Supervisor가 대리 게시하고 GET 일치를 확인했다. [로컬 선별 증거](evidence/kerbe-s-review.json).
  reviewer는 테스트나 소스 수정을 하지 않았고 전후 원본 checkout은 clean이다.
- **CI:** [run 37954147794](https://github.com/shotgun1107/kerbe/actions/runs/37954147794)의 기존
  Ubuntu·Windows job이 모두 성공했다. 각 `Ran 182 tests` / `OK`이고 skip은 Ubuntu 2개,
  Windows 1개다. 설치·wheel도 모두 성공했다. [job/선별 로그](evidence/kerbe-s-ci.json).
  실제 checkout은 PR 시험 merge `96e852f564830e5d19106455b7959e707992f9cd`이며
  head f0f73a8…와 base 026a8a0…를 조합한다. 이는 AI가 main을 병합했다는 뜻이 아니다.

로컬 제품 설치·전체 테스트·wheel은 ignore-only 영향 판단으로 미실행이며 위 CI와 구분한다.
제품 runtime/setup·DB·실제 계정 격리는 이번 S가 사용하지 않아 통과 범위에 포함하지 않는다.
무시된 부모 폴더의 예제, 이미 tracked인 파일, 강제 add는 `.gitignore`만으로 보호되지 않는다.

**판정: S 실행 부분 완료 / 사람 채택 대기.** 사람이 정확한 PR #4 후보를 직접 Ready·merge한 뒤
Supervisor가 실제 main 반영을 확인해야 완주다. 현재 main은 026a8a0…이며 M·병렬·모바일은
미실행 그대로다. Writer와 reviewer는 idle, pending permission은 없다. 기존 dirty A/B와 PR #2는 보존했다.
