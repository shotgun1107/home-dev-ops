# P1_PARALLEL_ISOLATED — 폐기 가능한 mock 동시 작업

2026-10-10 KST. **정식 P1 병렬은 미진입**이다. 저장된 S 완주 증거와 M Draft 전달 증거를
재사용하며 M의 사람 채택·main 대조 선행 조건을 완화하지 않는다. 이번에는 Kerbe 저장소를 조회·수정하지 않는다.

## 시험 범위와 성공 기준

기존 Astra Max Supervisor와 ops Worktree를 유지한다. [독립 probe](evidence/parallel-mock-probe.py)는
새 task-owned 임시 경로에 두 Git 저장소와 각각의 `.runtime`을 만든다. 원격은 없고 기존
설정/공통 hook을 변경하지 않는다. task A는 합성 상태 개수, task B는 합성 이름 중복 제거 결과를 낸다.
이들은 **AI/Provider agent가 아닌 Python mock writer 프로세스**다. 새 Supervisor·Paseo workspace·
Provider 세션·서비스·Heartbeat를 생성하지 않는다. mock Git의 local commit만 만들고 remote push는 없다.

- 각 writer는 자신의 task/입력/결과/runtime만 사용한다. Git/common dir와 inode를 구분한다.
- 두 writer의 lease 획득과 실제 생존이 겹치는 구간을 확인한다. pending 상태도 active writer로 센다.
  Supervisor는 이 구간에서 ops source/report 편집을 멈추고 읽기/요청별 mock 결정만 한다.
- 같은 task의 추가 writer는 nonblocking flock 실패/exit75로 거부하고 새 writer를 획득하지 못한다.
- mock 요청은 full writer/request/task ID와 정확한 operation hash에 묶는다. Supervisor가 각 요청의
  root·output·결과 hash·local commit 범위를 직접 검토한 후 한 건씩 결정한다. allow-all·영구 규칙은 없다.
- B의 요청을 보류한 상태에서도 A가 완료·local commit·clean에 도달해야 한다. 그 뒤 B도 독립 완료한다.
- fixture 결과·각 HEAD/parent·clean·자식 종료를 대조하고 실패/timeout을 성공으로 세지 않는다.

## 계약 회귀와 재현

probe의 `--self-test`는 최종15개를 독립 임시 fixture에서 실행한다. ID/hash 오염·재사용·누락·
영구 허용 필드·actor 불일치·중복 writer·저장소 분리·원자적 신규 JSON 발행·거부/timeout 뒤
결과와 commit 부재를 확인한다. 자동으로 공급한 unit fixture의 `actor`는 합성 표기이며 실제 승인이 아니다.

```sh
python3 -I -B docs/k12-paseo/evidence/parallel-mock-probe.py --self-test
python3 -I -B docs/k12-paseo/evidence/parallel-mock-probe.py --launch
```

launch는 생성한 경로와 두 PID를 출력한다. 요청은 각 task의 `.runtime/request.json`이다.
각 요청을 검토하고 같은 네 식별 필드(`taskId`, `writerId`, `requestId`, `operationHash`)와
`decision: allow|deny`, `actor: supervisor`, `reviewedAt`만 가진 JSON을 해당 task의
`.runtime/decision.json`으로 원자적으로 신규 발행한다. 없는 승인/시간 경과를 허용으로 취급하지 않는다.
120초 내 결정이 없으면 worker는 exit77이고 결과를 만들지 않는다. 거부79, 잘못된 응답78,
초기 소유/branch 조건 불충족76은 실패/차단이다. launcher는 자신이 생성한 child만 회수한다.
반복 실행은 항상 새 경로를 만든다. 기존 task runtime을 지우거나 재시도에 재사용하지 않는다.

이 파일은 상시 dispatcher/승인 정책·보안 sandbox가 아니라 Linux의 신뢰된 합성 fixture용 수동
실험이다. `--worker`는 launcher가 만든 task 경로에만 사용한다. 실제 approval 인증·PID 신원 보증·
OS 계정 격리·다중 host·power loss 복구를 제공하지 않는다. mock gate의 actor는 인증 주체 증명이 아니다.
stdout/receipt는 비밀 없는 합성 자료만 기록한다.

기존 hosted 후보 Python115·K12 Node47은 이번 probe에 합산하지 않는다. 이 수동 실험 artifact는
기존 CI manifest를 변경하지 않으며 CI 자동 실행 대상이 아니다. probe 성공을 실제 Paseo agent의
승인 부담이나 Provider 처리량으로 확대하지 않는다. 정식 병렬에서는 같은 조건의 직렬 사례와
실제 승인·재설명·재검증 부담을 따로 비교해야 한다.

실행 시각·full ID·정확한 SHA와 결과는 [선별 증거](evidence/parallel-isolated.json)에 보존한다.

후속 반례: mock worker의 첫 구현은 이미 도착한 결정이 있으면 0초 만료 조건도 실행했다.
새 계약 시험에서 exit0(기대77)을 재현했고 부작용 직전 만료 확인으로 보정했다. 이는 이 실험 harness의
구현 결함이며 실제 Paseo 승인 정책의 결함이라는 증거가 아니다. 만료는 gate 진입 제한으로,
이미 허용된 작업의 실행/commit을 강제로 취소하는 제한은 아니다. 수정 뒤14개 통과, 동일 두 작업을 새 경로에서 재검증해 각각 완료했다.


## 실측 결과

시작 ops HEAD는 `646ffd91d5eab7213f14a079415d53d327374a4b`(clean/local=remote=PR1 Draft)다.
첫 구현 `6d6caea1434c9bb5ca15e142b780d8f2dd24cacd`과 만료 보정 구현
`135c10c81b87628a8d781ffcb0083eb8806fabe2`, 최종 source/cwd 격리 구현
`ec7e809f37a587621384338b04ddbc7eaa80ddf7`를 구분한다. 최종 probe SHA-256은
`2d85a6ecc329700795daaa9d6b3072be5f0c7e899c68d0de55db6acd16471dd5`이다.

| 조건 | 최초 | 만료 보정 후 | 최종 source/cwd 격리 후 |
|---|---|---|---|
| task root suffix | `9y0yp_01` | `nfxmtkg4` | `1hdbs2ow` |
| 두 lease/프로세스 겹침 하한 | 33.797178초 | 16.928993초 | 20.800057초 |
| A 요청→mock 결정 | 33.773430초 | 16.913598초 | 20.768599초 |
| B 요청→mock 결정 | 54.673245초 | 32.801289초 | 37.464339초 |
| B 대기 중 A commit·clean / B HEAD 불변·결과 없음 | 관찰 통과 | 관찰 통과 | 관찰 통과 |
| 추가 writer 시도 | exit75, lease 미획득 | 동일 | 동일 |
| 결과·local commit·clean | 2/2 통과 | 2/2 통과 | 2/2 통과 |
| child 종료 | 두 exit0·parent 회수 | 동일 | 동일 |
| mock 수동 결정 | 2건 allow | 2건 allow | 2건 allow |
| 각 task의 worker source/cwd | 공통 harness / cwd 미기록 | 동일 | 별도 tracked 사본 / 실제 PID cwd 일치 |

세 경로의 prefix는 `/tmp/k12-parallel-mock-`다. 서로 다른 보정 조건의 순차 실행이며
세 round를 동시에 실행하지 않았다.

최종 A 후보는 `362c9674711699e00debf75fb1e6d192f98c5afe`,
B 후보는 `6bc663e16b09d313fa1cc5720783aaef3aa94efe`다. 각각 별도 remote 없는
Git 저장소의 local SHA이며 GitHub commit으로 게시한 것이 아니다. A 결과는
`{"failed":1,"ok":2,"waiting":1}`, B 결과는 `["alpha","beta"]`로 원래 acceptance와 일치했다.
최종 round의 source/task/result는 각 저장소에 있고 runtime은 각각 ignore된다.
Git/common dir·runtime·worker source inode가 다르며 child가 보고한 cwd와 실제 소유 PID의 `/proc/<pid>/cwd`를 대조했다.

여기서 겹침은 승인 대기를 포함한 두 살아 있는 writer/lease의 겹침이다. 두 CPU 작업의 동시 실행률이나
처리량을 뜻하지 않는다. duplicate probe는 잠시 세 번째 child이지만 lease 획득 전에 거부됐고
task 결과를 쓰지 않았다. **이번 각 launch가 만든 writer는2개다. 전역 writer 상한 강제는 구현·검증하지 않았다.**
per-root flock은 같은 task 중복만 거부한다. launch를 동시에 두 번 실행하는 반례는 소스로 확인했으며
실제4 writer 시험은 사용자 상한을 지키기 위해 실행하지 않았다. 운영상 상한은 계속 적용한다. Supervisor는 두 writer가
존재하는 구간에 ops 편집을 중단하고 요청별 mock 결정만 기록했다. 두 child 회수 후 보고 편집을 재개했다.

## 승인·조정 부담과 미확인

- 최종 round의 full writer/request ID 두 쌍, operation/hash와 직접 검토한 결정은 JSON에 있다.
  합성 승인 통로이며 실제 `paseo permit` 호출/Provider UI 승인/사람 클릭이 아니다.
- 최초2 + 만료 보정2 + source/cwd 격리2 = **Supervisor mock 결정6건**. 각 재시험 사유를 분리했다.
  자동 self-test fixture 응답은 이6건에 합산하지 않는다. 요구 맥락 재설명0, 정책/영구 허용 변경0.
- 대기 시간은 의도적으로 B를 보류한 시간·Supervisor tool/판단 시간을 포함한다. 세 round의
  차이를 개선 효과나 속도 비교로 보지 않는다. 같은 조건의 직렬 측정은 없으므로 우열 비교도 없다.
- **실제 Paseo dispatch·Provider 승인 부담은 미측정**이다. 기본 writer 수를2로 확정하거나
  Full Access/Auto/auto-review의 성능·안전성을 이 mock에서 도출하지 않는다.
- 정식 P1 병렬은 M의 사람 main 채택·실제 반영 확인 이후, 사용할 Writer 경로의 권한/보호/Setup
  조건을 먼저 충족하고 진행한다. 이번에는 그 선행 조건을 우회하지 않았다.

초기/보정 실행 디렉터리와 local commit/runtime 기록은 보존했다. 새 unit-test fixture만 자체
종료 시 정리했으며 기존 Worktree/영속 데이터/세션/서비스의 정리나 Archive는 하지 않았다.

추가 격리 보강: 앞선 두 round의 결과/저장소/runtime은 독립이었지만 실행 harness는 ops의
고정 파일을 공유했고 launcher가 cwd를 지정하지 않았다(설치 실행 경로의 소스 확인이며 당시 cwd는 미기록).
각 task Git에 `worker.py` 사본을 넣고 child cwd를 그 task로 지정했다. 새로운15번째 계약 시험은
이전 구현에서 실패했고 보정 후15개 통과했다. 최종 round에서 각 source 사본과 workerSource/보고 cwd/실제 PID cwd가 해당 task와 일치했고
같은 승인 보류 조건의 두 결과도 완료했다. 앞선 실행의 데이터 분리와 최종 source/cwd 분리를 구분한다.

## 독립 리뷰

[c98b27a… 원문](https://github.com/shotgun1107/home-dev-ops/pull/1#issuecomment-6089315397)은 Critical/High/Medium0, Low1, Info2다.
Low1에 따라 관찰한2 writer와 전역 상한 강제를 구분했다. 전역 lock/daemon·권한 정책을 새로 설치하지 않는다.
Info의 만료 gate 의미와 신뢰된 mock 결정 채널 한계는 유지했다. reviewer는 실험을 실행하지 않았다.
추가 source/cwd 격리와15개·최종 round 증거는 후속 고정 SHA 검토 대상으로 넘긴다.
