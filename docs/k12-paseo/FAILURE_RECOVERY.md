# P0_RECOVERY — 중단·PID 가시성·작업 복구의 격리 시험

2026-10-10 KST. 기준 ops `243ecdffa65992b661184560ed2d5932739262ba`.
기존 Astra Max·Director·Worktree를 유지했다. Kerbe 저장소, 실제 세션, daemon,
설정·권한·credential store·DB·volume은 시험 대상으로 사용하지 않았다.

## 성공 기준과 실측

- Python 신규27개 + 변경된 preflight의 기존9개 = **36개 OK, skipped0**.
- 설치 PID/daemon 읽기 코드의 Node **9개 OK, skipped0**. process.kill은 모든 호출에서
  stub이며 실제 signal0도 보내지 않았다. 잠금 acquire/release나 start/stop은 호출하지 않았다.
- 영향 없는 Python59개와 Heartbeat Node38개는 source/test/설치 hash 일치로 재사용했다.
  이번 실행 수에 합산하거나 현재 CI 성공으로 해석하지 않는다.
- [시험별 결과·조건·hash](evidence/recovery-regression.json), [Python 재현](../../tests/test_recovery.py),
  [설치 PID 재현](../../tests/test_recovery_pid.mjs).

| 실패 주입/조건 | 관찰과 개선 후 판정 |
|---|---|
| preflight status 조회 중 PID 동일·startedAt 변경 또는 PID 교체 | 기존 connection_verified=true 재현. 후보는 observation-changed/false, CLI의 당시 reachable은 별도 보존 |
| 조회 중 PID 메타데이터 소실 | 연결의 안정된 관찰로 확정하지 않음. 재시작 대신 읽기 전용 재대조 |
| PID가 현재 /proc에서 보이지 않음 | namespace 비가시성/종료/stale을 구분할 증거 부족. stopped로 확정하지 않음 |
| 같은 boot에서 다른 프로세스가 같은 PID를 사용 | 설치 kill(pid,0) 양성만으로 owner 인증 불가. preflight는 pid_identity_verified=false 명시 |
| boot 이전 startedAt | 설치 코드가 PID probe 없이 오래된 lock을 제외하며 파일은 보존 |
| EPERM / ESRCH / EACCES | 설치 경로는 EPERM을 생존으로 처리, 나머지는 null. 권한 수정·실제 프로세스 신호 없음 |
| 잘린 PID JSON | 설치 읽기 재시도 후 고정 error code, 원본 파일 보존. 실제 손상 복구/삭제 미실행 |
| invalid startedAt | 설치 schema가 받아들이고 PID probe 양성이면 instance를 반환. boot/실제 owner 신뢰 근거 아님 |
| 부분 handoff 저장 후 새 시험 child의 즉시 종료 | 비원자적 파일은 잘린 JSON으로 거부. 자동 재실행 없음 |
| 원자적 저장의 replace 직전/직후 child 종료 | 각각 이전/새 완전한 snapshot이 남음. 기존 서비스 프로세스는 종료하지 않음 |
| replace 전 저장 오류 / replace 후 directory fsync 오류 | 전자는 이전 파일·실패 temp 보존, 후자는 새 파일이 있어도 결과 불확정. 재조회 없이 재쓰기/롤백하지 않음 |
| idle이나 pending·child·native 종료 근거 중 하나가 부족 | 이전 Writer 종료 미확정으로 차단. 같은 branch/HEAD만으로 넘기지 않음 |
| local/remote/PR/handoff SHA 불일치, dirty, runtime/epoch 불일치 | 손실·소유권 충돌을 별도 이유로 차단하며 파일/작업을 지우지 않음 |
| 새 로컬 bare Git으로 push 성공 후 응답을 버림 | 실제 task ref를 읽어 HEAD 일치 확인. 네트워크 장애·GitHub API 유실 실측은 아님 |
| 합성 부작용만 있고 완료 영수증 없음 | fresh Python 프로세스는 reconcile-effects. 부작용 파일은 그대로. job/head 성공 영수증과 결과 대조 뒤 already-completed |

## 개선 후보

[paseo_preflight.py](../../scripts/paseo_preflight.py)는 PID의 전후 pid/startedAt 변화를
확인하고, 보이는 PID와 실제 daemon 신원을 분리한다. PID 입력은64KiB 이하의 일반 파일만
읽고 symlink/FIFO를 거부한다. parser RecursionError와 잘못된 CLI 출력을 고정 판정으로
처리하며 raw 오류·note·secret 필드를 출력하지 않는다. CLI는 기존15초 timeout과1MiB
출력 수용 한도를 쓴다. subprocess capture 자체의 메모리 상한을 보장하는 구현은 아니다.
설치 CLI도 내부적으로 instance를 재대조하지만, 바깥의 PID 관찰 시점은 별도이므로 둘을 혼합하지 않는다.

[paseo_recovery_audit.py](../../scripts/paseo_recovery_audit.py)는 운영자가 선별한 JSON의
증거 일관성을 확인하는 **오프라인 검토 보조**다. 실행·재시작·lock 해제·승인·lease 획득을 하지 않는다.
snapshot은 schema1이며 다음의 정확한 필드를 요구한다. 테스트의 `snapshot()`은 합성 예제다.

- checkpoint: task/job/worktree/runtime/writer/session/branch/epoch/head.
- observation: 동일 identity8개, localHead/remoteHead/prHead/handoffHead, observedAt,
  clean, writerState, pendingPermissions, children, nativeComplete, runtimeOwner, effects, receipt.
- receipt: null 또는 job/head/outcome(succeeded/failed). SHA는40자리 전체 값이다.
- observedAt은 timezone이 있는 시각, 현재 기준60초 이내/미래5초 이내다. 이는 입력의 신선도
  기준이며 snapshot이 진짜이거나 그 이후 새 실행이 없다는 증명은 아니다.
- runtimeOwner=released는 현재 scope의 실행 소유권 반납 관찰이다. 기존 runtime 데이터 삭제를 뜻하지 않는다.
  worktree/runtime은 운영자가 정규화한 정확한 식별자를 제공한다. 도구가 실제 경로를 탐색하지 않는다.
- effects=absent/verified도 운영자가 실제 부작용을 조회한 근거를 별도로 남겨야 한다.
  PID 소실·failed/idle·메시지 없음으로 absent를 만들어 넣지 않는다.

출력은 fixed reason code와 decision만이며 arbitrary 입력값을 반사하지 않는다.
handoff-reviewable/retry-reviewable/already-completed의 exit0은 **검토 가능한 증거 조합**이다.
실행 허가나 배타적 소유권이 아니다. 그 외는 exit2, automaticAction은 항상none이다.
관찰 후 새 Writer가 시작되는 경쟁을 막는 fence/lock/CAS는 구현하지 않았다.

같은 모듈의 `publish_snapshot(path,data)`는 후보 Python API이며 CLI 쓰기 모드는 없다.
caller가 소유한 디렉터리에서 temp+file fsync+replace+directory fsync로 발행한다.
이번 사용은 새 fixture 안뿐이다. 파일시스템 power loss, 실제 daemon 장애, 다중 writer,
네트워크 파일시스템 durability, 실제 job의 exactly-once를 보장하지 않는다.
검사 결과만 보고 controller dispatch 정책이나 기존 handoff를 자동 교체하지 않는다.

## 재현·실패 분류

```sh
timeout 45s python3 -B -m unittest discover -s tests -p test_recovery.py -v
timeout 30s python3 -B -m unittest discover -s tests -p test_paseo_preflight.py -v
timeout 20s node --test --test-concurrency=1 tests/test_recovery_pid.mjs
```

각 시험 child/Git subprocess는5초, Node case는3초 상한이다. Git fixture는 새 repo/bare repo,
task branch만 쓰고 user/system Git 설정·signing·공통 hook을 로드하지 않는다. global config를
변경한 것이 아니다. task fixture의 종료 후 정리만 하며 기존 작업 자료·영속 데이터는 보존한다.

초기 depth2000 입력 probe는 예상한 parser overflow를 재현하지 않고 fake CLI의 차단
AssertionError에 도달했다. 이를 운영 결함 증거로 세지 않았다. 별도 명시적 RecursionError
주입에서 기존 예외 전파를 확인하고 후보의 고정 미확정 결과를 재시험했다. source와
fixture 문제를 구분한 원기록은 증거 JSON에 보존했다. 첫 신규26개 통과 후 fsync 반례1개를
추가했고 최종27개가 통과했다. 실 daemon·인증·부작용 명령은 재시도하지 않았다.

## 기존 증거와 남은 경계

과거 실제 host/sandbox 가시성, M의 send 중단·Git/runtime 복원, Heartbeat crash/중복 반례는
ops에 저장된 증거를 재사용했다. Kerbe의 현재 상태를 조회하거나 과거 결과를 갱신하지 않았다.
현재 테스트는 Claude/Codex의 실시간 교대나 GitHub handoff 유실 재현을 대신하지 않는다.
현재 세션의 live preflight를 실행해 credential/config를 읽는 시험도 하지 않았다.

원격 결과·이전 실행·실제 부작용이 불명확하면 그 job 쓰기만 보류하고 독립적인 읽기/검증을
계속한다. 기록 재조립만으로 완료/실행 종료/복구 성공을 추정하지 않는다. 후보 도구의 운영 채택,
자동화 연결, 서비스 적용 및 실제 orphan 복구는 별도 사람 검토다. 기존 보호·권한·CI 공백과
전체 P0/P1 미완료 상태는 유지한다.
