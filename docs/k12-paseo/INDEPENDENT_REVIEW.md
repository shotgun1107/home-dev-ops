# REVIEW_INDEPENDENT — 고정 SHA 독립 리뷰와 반례 보정

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

## 고정 후보와 검증

- 구현 source: `0c91fd95b4e6c3f87a7c8b4a25887d2d157879c3`.
- CI 통합 후보: `a14365297170fbc79eae167a686ca311abee50b2`.
  새 disposable clone의 local 통합이며 GitHub merge가 아니다. source 대비 workflow 파일 하나만 다르고,
  workflow bytes는 과거5d7d1e1… 후보와 같다. 실제 ops branch에 활성 workflow를 추가하지 않았다.
- 정확한 workflow 명령 `timeout 120s python -I -B scripts/run_ops_ci.py`를 local Python3.14.4에서
  실행해 **125개 OK / skip0 / failure0 / error0**, 실행 전후 bytes 동일·clean을 확인했다.
  CI21 + cleanup15 + permission39 + recovery29 + preflight9 + guard12다.
- run ID `9fa1c691-e717-45ac-8336-ef2d0911478e`, 완료 시각 `2026-10-09T21:31:05.961559+00:00`.
  old115의 성공은 당시 고정 후보의 역사이며 최신125개 성공으로 바꿔 적지 않았다.
- Node38+9와 수동 mock15는 source/harness/patch hash 일치로 증거를 재사용했다.
  새 실행이나 hosted Python 검사 수에 합산하지 않는다.
- [새 bundle·사람 적용 절차](proposals/README.md)를 제공한다. 별도 clone에서 bundle verify/import,
  같은 full SHA 복원, PR #2 f069ac3…의 ancestor 관계, source tree 차이를 다시 확인했다.
  기존115개 bundle도 역사로 보존했다. 원격 PR #2와 실제 hosted 최신 run은 변경/실행하지 않았다.

[선별 증거](evidence/independent-review.json)에 full SHA,125개 case ID·hash·실행 시각,
전후 반례, 초기 harness 실패, reviewer 원문 hash·게시 영수증과 재사용 조건을 보존한다.
후속 고정 SHA 재리뷰 결과는 이 기록과 PR handoff에 추가한다. 그 전에는 재리뷰 통과를 주장하지 않는다.

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
