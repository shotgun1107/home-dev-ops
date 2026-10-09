# 권한·Git·Runtime 복구 절차

이 문서는 현재 실측한 경로와 미실행 복구를 구분한다. 모든 경로에서 AI merge 비활성,
main 직접 push/Ready 전환 금지, 기존 데이터 보존을 유지한다.

## 1. 연결·권한

1. 현재 cwd/branch/HEAD·dirty 여부·담당 writer·기존 명령과 Heartbeat를 확인한다.
2. `python3 -B scripts/paseo_preflight.py`로 읽기 전용 진단한다. exit 0은 연결 확인, exit 2는 미확정이다.
3. recorded-pid-not-visible이면 daemon 중지로 단정하지 않는다. 권한이 허용된 host에서 `paseo status --json`을 대조한다. 기존 승인이 없다면 그 경로만 보류한다.
4. host 연결은 되는데 sandbox만 실패하면 서비스·인증 설정을 변경하지 않는다. 허용된 개별 명령 승격이 가능한 경로를 사용하거나 운영자에게 그 명령만 넘긴다. Full Access를 자동 해결책으로 설정하지 않는다.
5. 오류 메시지의 start 안내를 자동 실행하지 않는다. 연결 정보·현재 PID·timestamp·실효 모드만 기록하고 credential 값은 출력하지 않는다.

검증: host/sandbox 차이 재현, 기존 host 연결, Heartbeat 생성/삭제까지 통과.
수동 daemon 시작/재시작/손상 복구는 미실행이며 별도 승인 대상이다.

Claude Auto 거부는 요청/도구/거부 문구/시각을 기록한다. 같은 호출을 근거 없이 반복하거나
shell wrapper·직접 API로 우회하지 않는다. 독립적으로 승인된 작업은 계속한다.
권한 파일의 deny/forbidden과 classifier를 구분하지 못하면 해당 경로를 통과로 선언하지 않는다.
Plan이라는 이름도 파일시스템 read-only 보장으로 사용하지 않는다.

## 2. Heartbeat

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
정리 결과는 `.runtime/<id>-cleanup.json` 및 PR #1 코멘트에 보존한다. 부모 tool이 즉시 종료됐는지
확인하고, 자동 재개한 턴에서는 이전 task_complete→새 task_started와 helper PID 생존을 대조한다.
helper는 Git source 수정·commit·push를 하지 않으며 다른 agent를 시작하지 않는다.
첫 cron까지의 대기(약 3분)+재개 턴 목표 시간(5분)이 대기 상한 900초보다 작게 잡는다.
재개 턴이 길어져 timeout이면 정리 성공으로 쓰지 않는다. 만료/상한으로 completed된 record는
재실행되지 않으므로, 다음 승인된 같은 agent 턴에서 record의 종료를 읽고 정상 CLI로 삭제한다.

receipt는 삭제 성공과 runOutcome을 분리한다. no-run/failed-run/1개가 아닌 run은 재개 통과가 아니다.
active-run 거부·승인 대기로 failed가 된 경우도 자동 재개 통과가 아니며 원래 run 오류를 선별해 대조한다.
succeeded-one-run도 native idle 전환·자동 알림·동일 agent/session 확인이 추가로 필요하다.
삭제 RPC 응답 유실은 `deletionConfirmed:false`와 `preDeleteReceipt`로 보존하고 먼저 실제 파일 부재를 읽는다.
timeout이면 완료/삭제를 추정하지 않고 남은 ID·expiry·오류를 기록한다. raw CLI stderr나 prompt는 게시하지 않는다.

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
