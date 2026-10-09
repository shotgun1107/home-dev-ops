# P1_PARALLEL_ISOLATED — 폐기 가능한 mock 동시 작업

2026-10-10 KST. **정식 P1 병렬은 미진입**이다. 저장된 S 완주 증거와 M Draft 전달 증거를
재사용하며 M의 사람 채택·main 대조 선행 조건을 완화하지 않는다. 이번에는 Kerbe를 조회·수정하지 않는다.

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

probe의 `--self-test`는 신규14개를 독립 임시 fixture에서 실행한다. ID/hash 오염·재사용·누락·
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

실행 시각·ID·고정 SHA·결과와 독립 리뷰는 후속 검증 기록에 보존한다.

후속 반례: mock worker의 첫 구현은 이미 도착한 결정이 있으면 0초 만료 조건도 실행했다.
새 계약 시험에서 exit0(기대77)을 재현했고 부작용 직전 만료 확인으로 보정했다. 이는 이 실험 harness의
구현 결함이며 실제 Paseo 승인 정책의 결함이라는 증거가 아니다. 만료는 gate 진입 제한으로,
이미 허용된 작업의 실행/commit을 강제로 취소하는 제한은 아니다. 수정 뒤14개 통과, 동일 두 작업을 새 경로에서 재검증한다.
