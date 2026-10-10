# REVIEW_INDEPENDENT — 고정 SHA 독립 리뷰와 반례 보정

**보존된 야간 리뷰 기록.** 현재 source/tests d8099f0…·CI65b2573…의 추가 시험/리뷰/hosted133과
문서 통합 검토는 [E21](EVIDENCE.md#e21-one-shot-통합-검증)·[현재 제안](proposals/README.md)을 따른다.
아래125개·bundle·hosted 보류 등은 각 리뷰 당시의 관찰이다.

2026-10-10 KST. 기존 Astra Max Supervisor와 ops Worktree·Draft PR #1을 유지했다.
기준 HEAD는 `81e1547da5f7d6579471ad1f8f4c8b5fa3269c4e`다. 실제 서비스·Schedule·Kerbe·
보호/권한/인증 설정을 변경하지 않았다. 리뷰어는 별도 Claude agent이며 수정·시험 실행 금지다.

## 독립 리뷰의 실제 범위

기존 Claude Opus 5.5 / Plan reviewer `b8e68af1-5dee-40fe-ba4b-0465eb656ebf`의
idle·pending0을 확인한 뒤 같은 세션을 재사용했다. source 편집은 리뷰가 끝날 때까지 멈췄다.
고정 Git 객체를 읽는 정적 리뷰이며 기술적 readonly나 fresh/blind review가 아니다.

[초기 원문·Supervisor 대리 게시·GET 일치](https://github.com/shotgun1107/home-dev-ops/pull/1#issuecomment-6089553741)는
Critical/High/Medium0, 새 Low1, Info3을 기록했다. 6개 script·시험·mock·제안은 과거 읽은 내용과
현재 hash를 대조했고, 문서는 주로 변경 diff를 읽었다. 증거 JSON 전체, bundle 내부, 설치 소스,
EVIDENCE/RECOVERY 전체를 새로 읽은 리뷰가 아니다. reviewer는 테스트나 실환경 조회를 실행하지 않았다.

원문을 보존하되 오류도 기록했다. permission 입력을 regular-file/no-FIFO라고 한 문장은 당시 코드와
달랐고, 모든 원격 동작이 문서에만 있다는 설명도 실제 cleanup의 CLI delete 경로를 누락했다.
표의 “blob hash”는 Git object ID가 아닌 SHA-256 접두사다. 이 세 가지를 원문 바로 위에 정정했다.
독립 리뷰를 실행 증거나 무조건 옳은 판정으로 취급하지 않는다.

[후속 원문](https://github.com/shotgun1107/home-dev-ops/pull/1#issuecomment-6089709950)은6개 script와
변경된3개 시험 파일을 새로 읽어 Low1/입력 보정을 확인했다. 원문 v2.4를 과거에 “전부 읽었다”는
초기 설명도 선택 section 읽기였다고 정정했다. 증거 JSON은 일부 필드, bundle은 header만 읽었다.
대용량 지적을 위해 설치된 service/schema2개도 추가 정적 조회했으므로 모든 읽기가 고정 Git 객체였다는
설명은 하지 않는다. reviewer의 테스트 실행은 여전히0이다.

## 재현·원인·수정

| 문제 | 수정 전 실제 합성 관찰 | 후보와 동일 조건 결과 |
|---|---|---|
| Low1: CI 완료 집계 전 정상 코드 종료 | 시험 본문의 `os._exit(0)`으로 exit0, start만 있고 finish 없음 | 시험을 child에서 실행하고 parent가 같은 runId·양의 expected·실행 수·실패/skip0·bytes 유지·passed를 가진 완료 영수증을 확인. import/시험 중 `_exit(0)`은 exit1, 일반 sys.exit는 unittest error |
| cleanup·permission의 FIFO 입력 | 새 task FIFO에서 각각 2초 outer timeout. 해당 시험 child만 종료·회수 | NONBLOCK/NOFOLLOW로 leaf를 열고 regular file을 확인. FIFO/symlink/directory를 고정 오류로 거부, 실제 CLI 호출 없음 |
| cleanup의 잘못된 자료형과 출력 | maxRuns=true가1처럼 허용됨. 선택 필드의 중첩 객체가 receipt로 전달됨 | 정수 maxRuns=1·full caller UUID·상태/UUID/시간 필드 검증. 잘못된 입력은 삭제 전 거부하고 raw 값 미출력 |
| cleanup 입력/응답 파싱 | schedule 전체 read_text, duplicate key 허용; 깊이/자료형 오류 처리 부족 | schedule64KiB 상한·중복 key 거부·고정 parser 오류·ack 크기/깊이 오류를 보존된 preDeleteReceipt와 구분 |

모든 delete는 주입 함수 또는 task-owned fake CLI였다. 실제 Schedule/Provider 호출은 없었다.
receipt는 승인·작업 성공·idle 자동 재개의 증명이 아니며 기존 결과 구분을 유지한다.

새 회귀 **10개**를 같은 fixture로 전후 실행했다. 수정 전에는 **17 failure/2 error**가 발생했고
(subtest 포함 집계이므로19개 독립 시험이라는 뜻이 아님), 수정 후에는 **10개 OK / skip0**다.
처음 paired harness는 예상 FIFO 오류 후 fixture 제거가 빠져 뒤의 fixture writer가 막혔다.
45초 상한으로 시험 프로세스만 회수하고 per-case finally로 보정했다. 제품/daemon 결함으로 세지 않았다.
다음 시도의2개 실패는 Python3.14가 depth2000 JSON을 파싱해 decoder 대신 schema가 거부한
  오류 이름 차이였다. 고정 오류·부작용 없음 조건을 두 거부 경로에 맞췄고 제품 코드는 그대로였다.

## 대용량 정상 record — 자동 삭제 확대 대신 보존 경로

후속 Low1은 정상 prompt/agent output도 schedule JSON을64KiB보다 크게 만들 수 있다는 점이다.
한도를 임의로 늘리는 근거가 없으므로 **제한을 유지하고 큰 record의 자동 cleanup은 지원하지 않는**
정책을 명시했다. 새 `schedule-too-large`는 파손/실종과 구분되며 `preDeleteReceipt:null`,
`deletionConfirmed:false`다. record를 수정/삭제하지 않는다. 정상 completed 구조에70,000-byte 합성 output을
넣은 subcase를 기존 file-input 시험에 추가했다. 검사 수는 그대로125개다. 이전 코드의 모호한 오류와
새 오류를 같은1개 시험에서 대조해2 subtest 실패→통과했고 fake CLI가 호출되지 않았음을 확인했다.

정확한 다음 행동은 [복구 절차](RECOVERY.md#2-heartbeat)다. 원본을 자르거나 cap을 우회하지 않고,
같은 agent의 승인된 후속 턴에서 소유권·completed·실제 실행 종료를 별도로 확인한 뒤 정상 CLI 삭제를
검토한다. 확인할 수 없으면 ID·관찰 크기·마지막 시각과 미확인 이유를 보존한다. 자동 cleanup 성공은 아니다.

## 고정 후보와 검증

- 최종 구현 source: `1edd2ef4702031dd6fe2d59adc01e4504c5c57db`.
- 최종 CI 통합 후보: `80455437960f3db0cbec5f1f3df0392ad47def3c`.
  새 disposable clone의 local 통합이며 GitHub merge가 아니다. source 대비 workflow 파일 하나만 다르고,
  workflow bytes는 과거5d7d1e1… 후보와 같다. 실제 ops branch에 활성 workflow를 추가하지 않았다.
- 정확한 workflow 명령 `timeout 120s python -I -B scripts/run_ops_ci.py`를 local Python3.14.4에서
  실행해 **125개 OK / skip0 / failure0 / error0**, 실행 전후 bytes 동일·clean을 확인했다.
  test_ops_ci.py의 회귀21 + cleanup15 + permission39 + recovery29 + preflight9 + guard12다.
- 최종 run ID `2318a21f-4f8f-49ba-827b-c183e40dce6e`, 완료 시각 `2026-10-09T21:41:22.131355+00:00`.
  최초 source0c91fd9…/candidatea143652…의125개 run9fa1c691…도 별도로 보존했다.
  대용량 subcase 뒤 재시험을 추가125개 사례로 합산하지 않는다. old115의 성공도 당시 고정 후보의 역사다.
- Node38+9와 수동 mock15는 source/harness/patch hash 일치로 증거를 재사용했다.
  새 실행이나 hosted Python 검사 수에 합산하지 않는다.
- [새 bundle·사람 적용 절차](proposals/README.md)를 제공한다. 별도 clone에서 bundle verify/import,
  같은 full SHA 복원, PR #2 f069ac3…의 ancestor 관계, source tree 차이를 다시 확인했다.
  기존115개 bundle도 역사로 보존했다. 원격 PR #2와 실제 hosted 최신 run은 변경/실행하지 않았다.

[선별 증거](evidence/independent-review.json)에 full SHA,125개 case ID·hash·실행 시각,
전후 반례, 초기 harness 실패, reviewer 원문 hash·게시 영수증과 재사용 조건을 보존한다.
최종 고정 SHA `773a87bbb576f57194c42025183f35316a1b477b`의 [delta 원문](https://github.com/shotgun1107/home-dev-ops/pull/1#issuecomment-6089778176)은
기존 Low를 명시적 보존 정책으로 해소, 새 Critical/High/Medium/Low0·Info1이다. Info의 조회 경로는
RECOVERY에서 agent-target 포함 검증이 선행돼야 하며 미확인이면 보존/차단하도록 명확히 했다.
그 후속은 리뷰 게시 영수증·판정·조회 설명뿐이며 source/tests/bundle bytes는 검증·리뷰 SHA와 같다.
최종 문서 delta를 다시 독립 리뷰했다고 주장하지 않는다.

## 남은 경계와 사람 결정

- CI parent receipt는 우발적인 조기 종료 검출이다. 악의적인 시험이 receipt를 위조하거나 source와
  manifest를 함께 바꾸는 상황의 보안 경계가 아니다. 보호된 리뷰 기준과 actual checkout/merge 부모 대조가 필요하다.
  child110초와 외부120초 상한은 daemon이나 모든 자손 실행의 종료를 인증하는 장치가 아니다.
- cleanup은 신뢰한 home 경로와 caller 환경에 의존한다. leaf symlink 거부가 모든 상위 경로 격리나
  OS 권한 통제를 뜻하지 않는다. 조회와 delete RPC 사이의 상태 변경을 원자적으로 차단하는 CAS/lock은 없다.
  다른 실행/사람이 record를 바꿀 수 있는 상황에서 무인 삭제를 승인한 것이 아니다.
  실제 runtime 종료·소유권 대조와 기존 자기 run 밖 정리 조건을 유지한다.
- CLI stdout 크기 검사는 capture 뒤다. streaming 메모리 상한이 아니다. 새 FIFO 시험은 로컬 fixture이며
  모든 파일시스템의 I/O 지연에 대한 hard wall-clock 보장은 하지 않는다.
- ops 보호403·guard 미설치·Full Access merge 차단 미검증, heartbeat 패치 운영 적용,
  원격 CI 채택·실제 hosted run, M의 사람 채택/main 확인, 정식 병렬·모바일은 그대로 미완료다.
  AI Ready/Merge/main push, 권한·보호 변경, Archive는 수행하지 않았다.

이번 task의 완료 범위는 독립 리뷰·안전한 반례 보정·고정 후보 검증·Draft 전달이다.
전체 P0/P1 완료나 운영 설정 채택으로 승격하지 않는다.
