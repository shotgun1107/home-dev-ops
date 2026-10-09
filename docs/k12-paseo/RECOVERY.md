# 권한·Git·Runtime 복구 절차

이 문서는 현재 실측한 경로와 미실행 복구를 구분한다. 모든 경로에서 AI merge 비활성,
main 직접 push/Ready 전환 금지, 기존 데이터 보존을 유지한다.

## 1. 연결·권한

승인 라벨을 실제 actor로 해석하지 않는다. user-rejected는 steer/중단에서도 생기고
reviewer=user는 전달 경로다. full agent/request ID의 응답과 native 실행 결과를 따로
대조하고, 중복·상충은 [오프라인 권한 감사](PERMISSIONS.md)의 방식으로 확인한다.
kind=plan/updatedPermissions는 모드·정책 변경 가능성이 있어 일상 도구 허용과 분리한다.
설치 Claude의 bypass launch capability와 현재 활성 모드는 별개다. 모드 변경 및
updatedPermissions 응답은 사람이 결정할 항목이며 Supervisor가 일상 요청으로 승인하지 않는다.

1. 현재 cwd/branch/HEAD·dirty 여부·담당 writer·기존 명령과 Heartbeat를 확인한다.
2. `python3 -B scripts/paseo_preflight.py`로 읽기 전용 진단한다. exit 0은 연결 확인, exit 2는 미확정이다.
3. recorded-pid-not-visible이면 daemon 중지로 단정하지 않는다. 권한이 허용된 host에서 `paseo status --json`을 대조한다. 기존 승인이 없다면 그 경로만 보류한다.
4. host 연결은 되는데 sandbox만 실패하면 서비스·인증 설정을 변경하지 않는다. 허용된 개별 명령 승격이 가능한 경로를 사용하거나 운영자에게 그 명령만 넘긴다. Full Access를 자동 해결책으로 설정하지 않는다.
5. 오류 메시지의 start 안내를 자동 실행하지 않는다. 연결 정보·현재 PID·timestamp·실효 모드만 기록하고 credential 값은 출력하지 않는다.

검증: host/sandbox 차이 재현, 기존 host 연결, Heartbeat 생성/삭제까지 통과.
수동 daemon 시작/재시작/손상 복구는 미실행이며 별도 승인 대상이다.

P0_RECOVERY의 [실패 주입](FAILURE_RECOVERY.md) 후 preflight는 조회 전후 pid/startedAt이
달라지면 observation-changed/exit2로 판정한다. CLI reachable과 PID 신원 확인을 구분하며
현재 /proc의 PID만으로 같은 daemon이라고 단정하지 않는다. 원본 lock을 지우거나 daemon을
재시작하지 않고 허용된 읽기 경로에서 해당 관찰만 재대조한다.

Claude Auto 거부는 요청/도구/거부 문구/시각을 기록한다. 같은 호출을 근거 없이 반복하거나
shell wrapper·직접 API로 우회하지 않는다. 독립적으로 승인된 작업은 계속한다.
권한 파일의 deny/forbidden과 classifier를 구분하지 못하면 해당 경로를 통과로 선언하지 않는다.
Plan이라는 이름도 파일시스템 read-only 보장으로 사용하지 않는다.

S에서 확인한 Accept Edits도 일반 Bash에 승인을 요청한다. 사용자가 이미 허용한 task 동작을
Supervisor가 맡아 처리할 때는 pending full agent/request ID와 실제 명령을 먼저 대조하고
`paseo permit allow <agent-id> <request-id>`로 그 요청 하나만 응답한다. ID 생략/`--all`은 쓰지 않는다.
agent와 request는 **full ID만** 사용한다. CLI는 request prefix의 첫 일치를 선택하므로 짧은 prefix도 금지한다.
`--input`으로 입력을 좁힐 때도 full ID가 가리키는 대상 요청이 정확히 하나인지 먼저 대조한다.
이 경로는 사람 클릭이나 무인 자동 승인 시험이 아니다. 허용 범위를 벗어난 검색은 실행 전에
입력을 좁히거나 `permit deny <agent-id> <request-id> --message ...`로 거부하고 결과를 확인한다.
denied 동작의 wrapper/API 우회, merge/Ready/main push 승인, rules/mode/영구 allow 변경은 포함하지 않는다.
S의 실제 범위 통제와 승인 내역은 [E10](EVIDENCE.md#e10-kerbe-p1-s--실제-writer-경로)을 따른다.

M의 Codex 기본 경로에서는 network=false의 DNS/연결 실패와 linked Worktree의 공용 Git
index.lock 쓰기 제한을 확인했다. 이미 허용된 task의 정확한 조회·branch push·stage·commit·
PR 쓰기·build 명령만 on-request로 검토한다. 정상 개별 승인은 설정 변경이나 Full Access 전환과 구분한다.
금지 명령의 거부를 네트워크 오류로 바꿔 해석하거나 같은 명령을 wrapper로 우회하지 않는다.

실행 중 `paseo send`는 현재 명령을 중단시킬 수 있다. 중단됐다면 native의 user-rejected
라벨만으로 사람이 거부했다고 기록하지 말고 실제 발신자·명령·완료 여부를 대조한다.
남은 프로세스와 부작용을 먼저 확인하고 로그/잔여 fixture를 보존한 뒤 필요한 시험만 재개한다.

handoff에는 task/job·full SHA·writer/session·정규화 worktree/runtime·소유권 세대를 대조할
정보를 남긴다. 전환 전 local/remote/PR/handoff SHA, dirty, pending/하위 실행/native 종료,
runtime 소유권 반납과 실제 부작용을 읽는다. [오프라인 검사 후보](../../scripts/paseo_recovery_audit.py)의
exit0은 검토 가능 판정이며 실행 승인/소유권 획득이 아니다. 오래된 snapshot이나 하나의 idle
표시로 새 Writer를 시작하지 않는다. 원자적 발행 도중 오류가 나면 이전 또는 새 완전한 기록이
남을 수 있으므로 실제 파일을 읽는다. 부작용이 있고 receipt가 없거나 응답만 유실됐다면
원격 ref/정확한 job 결과부터 대조하고 무조건 push/작업을 반복하지 않는다.
already-completed는 exit3으로 분리한다. exit0도 즉시 실행 조건으로 연결하지 말고
decision·정본 task/PR의 Next·현재 소유권을 확인한다. detached/remote 참조는 작업 branch로
해석하지 않는다. 후보의 좁은 branch 입력 규격이 기존 Git 권한 정책을 바꾸는 것은 아니다.

## 2. Heartbeat

P0_HEARTBEAT [격리 검증](HEARTBEAT.md)에 따라 expiry와 실제 실행 종료를 구분한다.
failed도maxRuns를 소모하고 permission 대기 실패는 underlying agent의 종료가 아니다.
crash 복원 후에는 PR/HEAD·task 영수증·실제 실행을 대조한다. failed 표시는 부작용 롤백 증거가 아니다.
manual runOnce는 expiry/maxRuns를 강제하지 않으므로 자동 복구 우회로로 사용하지 않는다.
설치본의 stale tick·저장 실패 guard 결함은 패치 후보만 검증했으며 운영 적용은 사람이 결정한다.
종료 성공·실패 결과 저장이 모두 실패하면 디스크에 orphan running이 남을 수 있다.
후보는 이때 중복 실행을 막지만 저장소가 복구돼도 active/running에서 자동 진행이 멈춘다.
실제 agent/native·하위 실행·PR/HEAD·부작용과 저장 실패 로그를 먼저 대조해
실행 중/종료/미확인을 구분하고 정확한 schedule/run ID와 마지막 저장 시각을 남긴다.
만료·maxRuns·completed만으로 underlying run 종료를 추정하지 않는다. run 파일 수동 편집,
runOnce 우회, 무단 daemon 재시작은 하지 않는다. 확인된 저장 장애의 해소와 해당 run의
복구 방식은 사람이 위험 검토한다. 새 객체의 복구 성공은 실제 서비스 재시작 승인이나
무손실 복구 보장이 아니다. 설치본 stop()도 interval만 지우며 진행 중 작업을 취소하지 않는다.

- 같은 Supervisor/목표의 기존 Heartbeat를 먼저 확인한다. 0.10.3의 일반 `schedule inspect`는 agent-target을 제외함을 확인했다. 일반 ls/logs도 Heartbeat 부재 판단 근거로 사용하지 않는다.
- 현재 agent의 schedule 파일에서 id/cadence/target/expiry/maxRuns/runs만 읽거나 해당 버전의 검증된 Heartbeat 조회 경로를 사용한다. 파일 직접 편집 금지.
- 허용된 연결 경로에서만 생성한다. 이 미션은 20분, Asia/Seoul, 24시간, 72회 상한을 사용했다.
- 생성 응답과 저장된 target이 현재 agent인지 확인한다. 실행 기록이 없으면 자동 재개 검증 완료로 쓰지 않는다.
- writer가 실행 중이면 새 Supervisor/중복 Worktree를 만들지 않고 기존 PR handoff와 소유권을 유지한다.
- 사용자 일시중단/종료 또는 사람 결정만 남을 때 정확한 ID로 `paseo heartbeat delete <id> --json`을 수행하고 응답을 확인한다.
- 삭제 실패 시 ID와 만료 시각을 PR에 남기고 성공으로 보고하지 않는다. 다른 자동화로 무단 대체하지 않는다.

Issue #3의 idle 시험은 같은 agent, `maxRuns=1`, 짧은 만료로 범위를 제한한다.
시험 전 PR·commit을 보존하고 턴을 실제로 종료한다. tool sleep/wait 중인 agent는 idle이 아니다.
자동 알림의 ID/run ID, native session의 직전 종료와 다음 시작, 저장된 run 시각을 대조한다.
새 agent 생성이나 수동 send로 만든 재개를 Heartbeat 통과로 기록하지 않는다.

Paseo 0.10.3은 해당 Heartbeat가 시작한 run 안에서 자기 Heartbeat를 지우면 종료 결과 저장에서 오류가 난다.
[격리 재현](EVIDENCE.md#e8-issue-3-재개와-heartbeat-정리)을 근거로, 실제 시험의 정리는
종료 뒤 `python3 -B scripts/paseo_heartbeat_cleanup.py <id> --timeout 900`으로 수행한다.
이 명령은 같은 caller의 1회 Heartbeat만 대상으로 하며 completed까지 기다려 CLI로 삭제한다.
scheduled 턴 밖에서 실행하는 한시적 정리 명령이다. 실행 위치·PID·ID·기한을 PR에 기록하고,
scheduled 턴 안에서 완료를 기다리지 않는다. 소유권 환경 변수를 바꿔 다른 agent를 가장하지 않는다.
이번 실행은 Python `subprocess.Popen(start_new_session=True, close_fds=True)`으로 프로세스 session을
분리하고 stdin을 DEVNULL, stdout/stderr를 `.runtime/<id>-cleanup.log`로 돌린다.
한시적 wrapper `.runtime/heartbeat_cleanup_report.py`가 정리 명령의 stdout JSON을 별도로 받아
`.runtime/<id>-cleanup.json`에 먼저 저장하고 PR #1 코멘트로 게시·재조회한다. wrapper 자체의 stdout/stderr만
위 `.log`로 보낸다. wrapper는 게시 실패를 `.runtime/<id>-cleanup-publication.json`에 기록하며 반복 게시하지 않는다.
이 wrapper의 경로·hash도 PR에 남긴다. 부모 tool이 즉시 종료됐는지
확인하고, 자동 재개한 턴에서는 이전 task_complete→새 task_started와 helper PID 생존을 대조한다.
helper는 Git source 수정·commit·push를 하지 않으며 다른 agent를 시작하지 않는다.
첫 cron까지의 대기(약 3분)+재개 턴 목표 시간(5분)이 대기 상한 900초보다 작게 잡는다.
expiry는 첫 cron 시각+예상 재개 시간 이후로 잡고, 생성 응답의 nextRunAt < expiresAt도 확인한다.
재개 턴이 길어져 timeout이면 정리 성공으로 쓰지 않는다. 만료/상한으로 completed된 record는
재실행되지 않으므로, 다음 승인된 같은 agent 턴에서 record의 종료를 읽고 정상 CLI로 삭제한다.

receipt는 삭제 성공과 runOutcome을 분리한다. no-run/failed-run/1개가 아닌 run은 재개 통과가 아니다.
active-run 거부·승인 대기로 failed가 된 경우도 자동 재개 통과가 아니며 원래 run 오류를 선별해 대조한다.
succeeded-one-run도 native idle 전환·자동 알림·동일 agent/session 확인이 추가로 필요하다.
삭제 RPC 응답 유실은 `deletionConfirmed:false`와 `preDeleteReceipt`로 보존하고 먼저 실제 파일 부재를 읽는다.
소유권 불일치·상한 불일치·완료 대기 timeout은 삭제 단계 전이므로 `preDeleteReceipt:null`이며 삭제를 시도하지 않는다.
timeout이면 완료/삭제를 추정하지 않고 남은 ID·expiry·오류를 기록한다. raw CLI stderr나 prompt는 게시하지 않는다.

REVIEW_INDEPENDENT 보강 후보는 schedule의 leaf symlink/FIFO를 거부하고64KiB 상한·중복 key·
정수 maxRuns·full caller UUID·선택 출력 필드 자료형을 검사한다. 오류는 삭제 전에 고정 문자열로 남긴다.
이는 신뢰한 상위 home 경로나 caller 환경의 인증을 대체하지 않는다. 조회→delete RPC는 원자적이지 않으므로
동시 record 변경을 막는 서버 CAS/lock을 검증했다고 하지 않는다. 새15개 cleanup 검사는 모두 fake CLI/주입 함수였다.

`schedule-too-large`는 정상 prompt/agent output으로도 발생한다.64KiB를 넘는 record의 자동 삭제는
지원하지 않으며 원본은 보존한다. schedule JSON을 잘라내거나 cap·caller 환경을 바꾸어 재시도하지 않는다.
기존 선별 영수증과 **agent-target Heartbeat를 포함한다고 별도 검증된 정상 조회 경로**에서
전체 prompt/output을 출력하지 않고 schedule/run/full agent ID,
maxRuns=1·completed 및 실제 native/하위 실행 종료를 대조한다. 그 근거를 확보한 **같은 agent의 승인된
후속 턴**에서만 정상 `paseo heartbeat delete <정확한 ID> --json` 경로를 검토하고 응답·record 부재를 확인한다.
자료를 안전하게 확인할 수 없으면 삭제하지 않고 ID·관찰 크기·마지막 시각·미확인 사유를 남긴다.
이번 검증은70,000-byte 합성 output의 보존/오류 구분뿐이며 실제 대용량 record 삭제는 미실행이다.
앞서 확인한 일반 `schedule inspect/ls/logs`의 필터 경로로 Heartbeat 부재를 추정하지 않는다.
이번에는 대용량 record를 안전하게 선별 조회하는 새 경로를 검증하지 않았다.64KiB helper를
다시 호출하거나 파일 전체를 출력하는 대안도 아니다. 필요한 조회 증거가 없으면 record를 유지하고
안전한 조회·삭제 방법의 사람 검토를 대기한다. completed만으로 native/하위 실행 종료를 추정하지 않는다.

## 3. Git·PR

시작/재개 시 `git status --short --branch`, `git rev-parse HEAD`, `git log`,
원격 PR의 head/base/draft를 비교한다. 원격 추적 ref만으로 실시간 서버 상태를 확정하지 않는다.

push 실패 시 local commit을 보존하고 branch·local/remote full SHA·오류를 PR 또는 응답에 기록한다.
네트워크 오류와 보호 규칙 거부를 구분한다. 원격 확인 전에는 백업 완료로 쓰지 않는다.
강제 push/reset/clean/stash로 맞추지 않는다. 분기 상태와 소유권을 확인한 뒤 안전한 후속 경로를 선택한다.

`gh pr edit`가 projectCards 오류로 실패한 경우, 같은 PR 본문 갱신이 이미 승인되어 있으면 다음 경로를 쓴다.

```sh
gh api --method PATCH repos/shotgun1107/home-dev-ops/pulls/1 \
  -F body=@/tmp/k12-pilot-pr-body.md --jq '{html_url,draft,head:.head.sha}'
gh api --method GET repos/shotgun1107/home-dev-ops/pulls/1 \
  --jq '{body,draft,head:.head.sha}'
```

위 `/tmp/k12-pilot-pr-body.md`는 이번 실행에서 사용한 파일 예시다. 새 작업에서는 `mktemp`로 별도 파일을 만들고 소유권·내용을 확인한다. 파일에는 실제 줄바꿈을 유지한다. PATCH 전/후 대상 repo/번호/HEAD를 확인한다.
실패가 권한 정책의 거부라면 이 경로를 우회 수단으로 사용하지 않는다.
현재 사례는 GraphQL 호환성 오류이며 기존 자격증명으로 PATCH/GET이 성공했다.
전역 gh 업그레이드는 이 복구의 필요 조건이 아니다.

reviewer가 직접 게시하지 못하면 원문·full SHA·검토 방식·미확인 범위를 writer에게 전달한다.
writer는 `reviewer: <provider> / writer 대리 게시` 표기와 원문을 보존하고 PR 게시물을 재조회한다.
실제 게시 전에는 PR 기록 완료라고 쓰지 않는다. 후보가 바뀌면 변경 부분과 영향 맥락을 재리뷰한다.

Supervisor 작업 branch에 workflow 변경을 추가하지 않았다. 사람이 허용한 CI PR #2는 별도로 존재한다.
원문 v2.4 15장의 patch 보존·사람 반영 경로를 유지한다.
base 수신 중 workflow 충돌 시 pre-merge HEAD/base/충돌 경로 기록 후 merge --abort,
원래 HEAD와 clean 복귀 확인이 원문 절차다. **이번에 재현한 복구는 아니다.** 실패 시 reset을 강행하지 않는다.

## 4. guard 설치 전 위험 검토 — 사람 작업

현재 ops에는 활성 hook이 없다. 후보 `scripts/k12-pre-push`는 Kerbe의 검증된 SHA-1 branch guard와 동일하다.
설치 권고와 실행 승인은 다르며 이 PR은 설치를 자동 수행하지 않는다.

1. `git config --show-origin --get core.hooksPath`와 `git rev-parse --git-path hooks/pre-push`로 실효 위치를 확인한다. linked worktree의 공통 .git 변경은 다른 작업에도 적용된다.
2. 기존 hook이 있으면 백업·내용 확인 후 명시적 연결 설계를 검토한다. 덮어쓰지 않는다.
3. LFS 사용 여부를 tracked .gitattributes와 기존 hook에서 읽는다. 진단을 위해 git lfs install/track를 실행하지 않는다.
4. LFS 등 연결 hook은 동일 argv/stdin·실패코드·재귀 방지를 검증해야 한다. 현재 후보에는 일반 hook dispatcher가 없다.
5. 사람 설치 후 task worktree에서 실효 위치·hash·execute bit를 확인하고 격리 harness를 다시 실행한다. 실제 main push로 시험하지 않는다.
6. 서버 보호 공백은 local hook으로 해결됐다고 하지 않는다. ops private/protection 정책을 별도로 결정한다.

서버 설정의 롤백·업그레이드/공개 전환은 위험 검토와 사람 결정 대상이며 이 문서의 자동화 범위가 아니다.

## 5. Runtime·데이터

현재 Python 검증 경로는 worktree별 .venv/editable/import assertion이다.
`ensurepip` 문제는 PR #2의 후속 운영자 실측으로 해소됐고 이번에도 import 경로를 확인했다.
재발 시 shared Python/PYTHONPATH/sudo로 검사 성공을 꾸미지 않는다.
설치 실패와 코드 테스트 실패를 분리한다. 관련 파일/경로/Python 버전이 바뀌면 import assertion부터 다시 확인한다.

M에서 Git fixture의 TMPDIR을 Worktree 안에 두면 상위 저장소를 발견해 기존 2개 시험이 실패했다.
저장소 밖에 새 작업 전용 임시 디렉터리를 만들고 0700·소유 UID·Git 비저장소 판정을 확인한다.
이 경로와 workspace 소유권을 handoff에 남기고 두 번째 Writer도 같은 venv/TMPDIR을 재사용한다.
검사 실패를 없애려고 테스트 기대값이나 Git 전역 설정을 바꾸지 않는다. 기존 임시 경로와
중단 fixture는 보존한다. 이 보정에서 동일 실패 2개 재시험은 OK, 이후 전체 suite는 Ran 184, OK(skipped=2)였다.

Kerbe의 실제 init/status/collect/sync는 이 미션에서 실행하지 않았다.
다음 runtime 시험은 별도 config/state DB/ledger/source fixture/in-memory secret store 등
모든 접근 지점을 정한 뒤 실행해야 한다. --config 하나나 임의 HOME 변경만으로 격리됐다고 보지 않는다.
원본 Codex 세션·실제 Credential Manager·공유 장부를 시험 데이터로 쓰지 않는다.

Docker는 rootless context와 대상 자원 소유경로를 확인한다. DB/volume/container/port의
worktree별 고유성 확인 전에는 해당 runtime 경로를 보류한다. 현재 Kerbe 범위는 Python이며
Compose 스택·migration·volume 보존/restore/teardown 시험은 미실행이다.
기존 Minecraft·Paseo·Docker 서비스는 어떤 개발 정리에서도 제외한다.

중단된 부작용 명령은 먼저 실제 반영 상태를 읽는다. 결과 불명확 시 쓰기를 재시도하지 않는다.
Git lock은 실제 Git 프로세스와 소유권 확인 전 삭제하지 않는다.
기존 미커밋/ignored/영속 데이터를 지우지 않고, 최초 파괴적 복구는 폐기 가능 자원에서
별도 보존·복원 검증을 거친다. 이번 미션에서는 정리/Archive를 실행하지 않았다.

## 7. CI 실행과 현재 후보가 어긋날 때

PR API base만 믿지 말고 실제 branch ref, PR merge ref 부모, Actions run head/checkout SHA를 대조한다.
OPS_CI에서 merge ref 자체도 과거73afc54…를 가리킨 사실을 확인했다. stale ref를 최신이라고
가정한 검사를 멈추고 task-owned clone의 local 통합 후보로 별도 실측했다. 운영 repo reset/force나
서비스 조작은 필요하지 않았다. [정확한 후보와 사람 적용 순서](proposals/README.md).

manifest 개수/파일/버전이 맞지 않으면 검사를 생략하거나 숫자를 성공시키기 위해 낮추지 않는다.
의도된 suite 변경인지 검토하고 source+manifest를 같은 후보로 고친 뒤 다시 실행한다.
Node K12 시험을 hosted Python 검사에 합산하지 않는다. bundle prerequisite 또는 원격 HEAD가
변했다면 새 base에서 다시 대조하고 새 후보·새 CI 결과를 남긴다. 이 작업은 기존 CI PR2를
원격 갱신하지 않았으므로 서버 측 rollback은 없다. 새 task-owned fixture들은 보존했다.

REVIEW_INDEPENDENT 이후 기본 CI 명령은 child exit0뿐 아니라 parent의 완료 영수증 확인까지
성공해야 한다. `completion-unconfirmed` 또는 `child-unavailable-or-timeout`은 통과가 아니다.
내부 child 옵션으로 parent를 생략하지 않는다. child110초/외부120초이며 악의적 코드 격리나
모든 자손 종료 증명은 아니다. 최신125개 후보·과거115개 후보를 [전달 절차](proposals/README.md)에서 구분한다.

## 8. 독립 mock 작업의 대기·종료

[수동 mock probe](PARALLEL_ISOLATED.md)는 요청별 full ID/hash와 task root를 확인한 결정만 받는다.
파일이 있다는 사실만으로 미만료라고 판단하지 않고 부작용 직전 만료를 확인한다. 잘못된 결정78,
거부79, 대기 만료77, 이미 사용 중인 writer75를 완료로 세지 않는다. 이는 실제 Paseo permission
오류 코드나 복구 API가 아니다. stale PID만 보고 기존 세션을 종료하거나 lock을 지우지 않는다.

독립 task A가 완료돼도 B가 pending이면 전체 결과를 완료로 기록하지 않는다. 각 후보 SHA/clean/결과와
launcher의 owned child 종료·회수까지 대조한다. 재시험은 새 disposable 경로에서 수행하고 기존
source/runtime/결정 파일을 덮어쓰지 않는다. 현실 Provider나 영속 runtime의 복구는 기존 P0 조건을 따른다.
