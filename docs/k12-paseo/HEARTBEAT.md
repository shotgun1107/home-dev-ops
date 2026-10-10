# P0_HEARTBEAT — 수명·동시 tick·장애 격리 검증

2026-10-10 KST, 기준 ops SHA `a29f66e0a676afb0e621f5942a696152e87b181f`.
Paseo 0.10.3, Node v22.22.1의 설치 ScheduleService/Store/Cron을 사용했다.
실제 daemon·schedule·Provider·설정은 조작하지 않았다. 새 `/tmp/k12-heartbeat-night-*`
안에서만 합성 schedule 파일을 만들고 시간을 주입했다. 실제24시간 관찰·OS crash 시험은 아니다.

[재현 시험](../../tests/test_heartbeat_lifecycle.mjs), [패치 후보](proposals/paseo-heartbeat-schedule.patch),
[선별 결과·hash·조건](evidence/heartbeat-lifecycle.json). **패치는 설치하지 않았다.**
기존 Astra Max·Director·Worktree·사용자 서비스를 유지했고 Kerbe를 읽거나 변경하지 않았다.

## 시험 조건과 결과

19개 조건을 설치본/패치 복사본에 동일 적용한 **Node38개 OK, skipped0**다.
설치본의 알려진 결함을 확인하는 assertion도 포함하므로 "설치본 운영34개 통과"가 아니다.
Python 기존68개는 source/tests hash 일치로 재사용했다. Python discover는 Node 시험을 실행하지 않는다.

| 조건·성공 기준 또는 관찰 범위 | 설치본 결과 | 패치 후보 결과 |
|---|---|---|
| 13:08:05Z 생성, Asia/Seoul */20 cron,24h/max72 | 72개 terminal 성공, 슬롯72개, 완료 뒤 재실행 없음 | 동일 |
| 정각 생성, 정확히24h 만료 | 만료 경계 슬롯 제외로71개 후 completed | 동일.72회 성공 보장으로 해석하지 않음 |
| 첫 슬롯과 expiry 동일 | 실행0, completed | 동일 |
| 실행 중 expiry 경과 | running 유지, runner 해제 후 succeeded/completed | 동일. expiry는 실행 제한 시간이 아님 |
| 실행을 붙잡은 상태의9개 중첩 tick | runner1회 | 동일 |
| 오래된 list 결과를 다른 tick 완료 후 처리, max1 | **같은 슬롯2회 실행, 상한 초과** | 재검증해1회 유지 |
| list 이후 pause, 그 뒤 오래된 tick 처리 | **pause 뒤 runner1회** | runner0회 |
| list 대기 중 expiry 경과 | **expiry 뒤 runner1회** | claim 시 현재 시각 확인, runner0회; 다음 tick에 completed |
| append 저장 실패1회 뒤 저장소 정상화 | **메모리 running guard 잔류, 후속 runner0회** | finally로 guard 해제, 후속 runner1회 |
| 종료 성공/실패 저장이 모두 실패한 뒤 저장소 정상화, 상한·만료 없음 | orphan running 잔류·후속3 tick에서 추가3회 실행 | orphan 때문에 추가0회. **active/running 상태에서 자동 진행 정지** |
| list 이후 A 삭제, 같은 tick의 B 대기 | tick 오류·A guard 잔류, 다음 tick에서 B 진행 | tick 오류는 동일, A guard는 해제·다음 tick에서 B 진행 |
| A 실행 보류 중 B 슬롯 도착 | B는 진행하나 A 종료 후 오래된 목록으로 B2회 | B 진행 유지, A/B 각각1회. tick 전체를 잠그지 않음 |
| 실제 executeSchedule 경로 + busy agent stub, max2 | 시작0, failed2로 상한 소모·completed | 동일. busy는 성공/유예로 집계하지 않음 |
| 같은 경로 + permission 대기 stub | schedule failed/completed, stub pending 유지 | 동일. agent 종료·승인 취소를 증명하지 않음 |
| persisted running을 새 객체로 복구 | failed 처리, 놓친 슬롯 재생 없음, 미래 슬롯으로 이동, 반복 복구 동일 | 동일. 실제 daemon 재시작은 안 함 |
| 합성 부작용 기록 후 종료 영수증 전 crash 상태 복원 | failed 기록 뒤 다음 실행으로 부작용2회 | 동일. exactly-once가 아님 |
| expiry 후 manual runOnce2회, max1 | 2회 실행, 다음 일반 tick에서 completed | 동일. manual API를 자동 복구로 사용하지 않음 |
| paused 상태로 expiry 경과 | paused 유지, 실행0 | 동일. 모든 record가 만료 즉시 completed되는 것은 아님 |
| target 없음 stub | 실행 시작0, failed/completed | 동일 |

## 원인과 후보 변경

설치 `schedule/service.js:396-417`은 list snapshot과 메모리 guard를 검사한다.
runner를 기다리는 사이 다른 tick이 같은 목록의 후속 schedule을 끝낼 수 있다.
`runSchedule:514-575`와 `appendRunningRun`은 오래된 snapshot의 slot/status를 재검증하지 않고
run을 추가한다. 따라서 같은 슬롯 완료·pause·만료 뒤 실행이 가능한 순서를 재현했다.
append가 try 밖에 있어 저장 실패 때 finally가 실행되지 않는 별도 guard 누수도 확인했다.

후보는 store의 동일 instance·schedule별 mutation 직렬화 안에서 최신 status/slot/due/
expiry/maxRuns/persisted running을 확인한다. 만료에는 최초 tick 시각 대신 **claim 시 현재 시각**을 쓴다.
append를 try/finally 범위로 옮겨 실패·skip에도 메모리 guard를 해제한다.
runner와 finishRun의 기본 의미, manual runOnce 동작은 유지한다.
전역 tick 잠금은 긴 A 때문에 독립 B까지 막으므로 사용하지 않았다.
이것은 단일 service/store instance 후보이며 프로세스 간 락이나 완전한 exactly-once 해결책이 아니다.
`startedAt`은 최초 tick의 시각을 계속 사용하므로 실제 Provider 시작 시각의 정밀 증거도 아니다.

독립 리뷰의 [Low1 반례](https://github.com/shotgun1107/home-dev-ops/pull/1#issuecomment-6088278361)를
추가 재현했다. runner의 성공 결과와 catch의 실패 결과 저장이 모두 실패하면 메모리 guard는
해제되지만 디스크의 running이 남는다. 저장소 복구 후 후보는 자동 재실행을 거부하므로
expiry·maxRuns가 없는 조건에서 진행이 멈춘다. 실행 중인지 고아 기록인지 임의 판정해
재실행하는 변경은 하지 않았다. 이 **중복 방지를 우선한 정지 상태**는 해결된 자동 복구가 아니다.
새 객체의 recoverInterruptedRuns 후 다음 슬롯 실행은 합성 검증했지만 실제 daemon 재시작은 안 했다.
실제 실행·부작용·저장소 상태 대조와 복구 방식의 사람 결정은 [복구 절차](RECOVERY.md#2-heartbeat)에 남긴다.
삭제된 A가 같은 tick의 B를 지연시키는 기존 동작도 재현했으며 다음 tick의 B 실행을 확인했다.

patch는 원본 service.js SHA256
`325066fba80c259ed0f5385042f15045820791fe048e622151259ed036dcd3c6`에만 검증했다.
시험은 새 임시 복사본에 git apply를 수행하고 상대 import를 원래 설치 의존성의 file URL로
연결한다. 전역 설치 파일은 전후 hash가 같다. service.start/실제 agent/provider/Archive는 호출하지 않는다.
실제 대상은 agent-target만이다. new-agent schedule의 복구/종료에는 Archive 부수 효과가 있을 수 있어
이번 결과를 new-agent workspace 자동 정리의 검증으로 확대하지 않는다.

## 재현과 초기 실패의 분류

```sh
node --test --test-concurrency=1 tests/test_heartbeat_lifecycle.mjs
```

K12 설치 의존성과 위 hash가 전제다. 환경이 없거나 버전이 다르면 통과로 건너뛰지 않고 실패한다.
각 case는5초 상한, patch 적용 child command도5초 상한이다. 실시간24시간 대기나 interval을 시작하지 않는다.
정상 종료 때 이 시험이 만든 mkdtemp root만 정리한다. 실제 schedule 파일은 접근하지 않는다.

초기 시험의6개 case 실패(+집계 hook1)는 stub의 필수 nullable output 누락과
tryRunOutOfBand 누락이었다. 합성 runner 계약을 바로잡은 뒤32개가 통과했다.
추가 expiry 경계 시험 때 crash fixture2개(+hook1)는 주입 시각을 due로 옮기지 않아
새 claim 검사가 거부한 것이었다. 실제 due에서 running을 보존하도록 고친 뒤34개가 통과했다.
이후 리뷰의 종료 저장 실패·list 이후 삭제 조건을 추가해38개가 통과했다. 패치 bytes는 그대로다.
이 실패들을 daemon 운영 결함으로 세지 않았으며 로그 hash는 증거에 보존했다.
실패한 시험의 작업 전용 fixture는 보존했고 기존 영속 데이터는 정리하지 않았다.

## 검증된 운영 해석과 사람 결정

- expiry는 신규 자동 dispatch를 제한하는 조건이며 이미 시작한 작업의 hard timeout이 아니다.
  실행 종료는 실제 agent/native/하위 실행·runtime 상태로 별도 확인한다.
- 설치 소스상 stop()도 interval만 지우며 이미 시작한 tick/runner를 취소하지 않는다.
  이것은 정적 확인이며 start()/interval/stop()의 실운영 시험은 하지 않았다.
- maxRuns는 succeeded뿐 아니라 failed도 센다. busy·승인 대기로 예산이 소진될 수 있다.
  종료 상태만으로 목표 완료를 보고하지 않는다.
- 재시작 복구의 failed는 작업 부작용이 없거나 취소됐다는 증거가 아니다. 다음 작업은
  PR·정확한 HEAD·기존 task 영수증을 먼저 대조해 논리적 작업을 중복 수행하지 않는다.
- 수동 runOnce로 expiry/maxRuns를 우회해 자동 재개를 흉내 내지 않는다. paused record의
  잔류와 active-run/pending 상태는 정확한 ID와 다음 사람 행동을 기록한다.
- 설치본에서 재현된 중복/guard 결함은 남아 있다. 패치 배포·Paseo 버전 갱신·운영 daemon 적용은
  사람 위험 검토와 별도 승인 이후 작업이다. 이번에는 후보만 Draft로 제공한다.

실제 idle→자동 재개→succeeded→종료 뒤 삭제는 기존427d614c 영수증을 재사용했다.
기존 busy tick과 자기 run 안 삭제 충돌도 source hash가 같아 재실행하지 않았다.
실제24시간 운영, 실제 프로세스 crash/디스크 장애, 다중 daemon, Provider 장기 안정성,
새 후보의 운영 설치 효과는 미확인이다. 기존 Director의 dispatch 정책도 바꾸지 않았다.

고정 SHA `a2311a7fc640bea9c6148e8b516dd5dd4cadef14`의 [Claude delta 리뷰](https://github.com/shotgun1107/home-dev-ops/pull/1#issuecomment-6088341624)는 새 지적이 없었다. Low1은 반례 시험과 한계 명시로 처리했으며 자동 복구 자체는 미해결이다. reviewer는 정적 검토만 했고38개 실행은 Supervisor 실측이다. 저장 실패는 write() 경계의 합성 주입이며 실제 I/O·atomic temp/rename 장애를 일으킨 것이 아니다. [리뷰 영수증](evidence/heartbeat-review.json)에 검토 SHA·원문 hash·게시 GET 검증을 보존했다.
