# K12 Paseo 운영 체계 v2.4 운영 정본

작성 기준: 2026-10-08  
범위: K12에서 Paseo로 Claude Code와 Codex를 교대·병렬 운용하는 개발 작업. 첫 적용 대상은 Kerbe다.  
상태: Pro 운영 검토를 반영한 파일럿 시작안. 사용할 기본 경로를 확인한 뒤 사람 직접 merge·수동 정리로 시작한다. AI merge·자동 archive는 별도 활성화 조건을 충족했을 때만 사용한다. 검토 요청과 판정 이력은 별도 변경 이력으로 분리한다.

[검토와 변경 이력](K12_Paseo_Review_History.md)

## 0. 운영 모델과 적용 경계

**합칠 수 있는 결과 단위로 작업 공간을 나누고 한 worktree에는 writer를 하나만 둔다. 리뷰와 승인은 특정 커밋을 대상으로 한다. 작업 상태는 다른 세션이 복원할 수 있게 남긴다.**

이 구조가 필요한 이유는 다음과 같다.

- 작업별 branch와 worktree는 서로 다른 작업의 수정·커밋이 섞이는 것을 줄인다.
- 한 worktree의 writer를 하나로 제한하면 Claude·Codex·사람 사이의 덮어쓰기와 소유권 혼선을 막는다.
- SHA를 고정하면 무엇을 검토하고 승인했는지 확인할 수 있다.
- task·commit·PR·검증 결과가 남으면 세션이나 provider가 바뀌어도 재개할 수 있다.
- 사람은 main 반영을 결정하고 AI는 그 앞단과 승인된 실행을 맡는다.

worktree가 분리하는 것은 주로 소스 작업 공간이다. OS 사용자 권한·자격증명·외부 서비스·공유 DB까지 격리하는 보안 경계는 아니다.

기본 관계는 **독립적으로 합칠 결과 하나 = task worktree 하나 = branch 하나 = PR 하나**다. 같은 목적의 구현·테스트·문서는 한 결과에 포함한다.

예외는 명시한다.

- git이 아닌 scratch는 Local에서 자유롭게 쓴다. 파일럿에서는 `trunk-direct`를 사용하지 않으며 `home-dev-ops`도 일반 PR 흐름을 따른다.
- 경쟁 구현은 같은 목표를 별도 작업 공간에서 비교할 수 있다.
- detached review worktree는 검증용 보조 공간이다. 사람이 추가 생성을 요청한 경우에만 만들며 별도 branch나 PR은 필요 없다.
- 버릴 조사에는 PR이 필요 없다. 남길 연구 결과가 있을 때 문서 PR을 만든다.
- 큰 목표는 독립적으로 합칠 수 있는 slice로 나누고 slice마다 위 관계를 적용한다.

새 repo의 최초 main 생성은 사람이 GitHub UI 등 관리 경로에서 수행한다. 이후 agent는 작업 branch·PR 흐름을 따른다. 나중에 trunk-direct가 실제로 필요해지면 별도 정책으로 승인하며 일반 main push guard에 자동 예외를 추가하지 않는다.

이 문서는 개발용 worktree와 연결된 자원에 적용한다. 기존 서버 서비스와 그 데이터는 개발 자원 정리 대상이 아니다.

개발 결과의 완료는 Acceptance를 충족한 후보를 검증하고 사람이 채택해 실제 main 반영까지 확인한 상태다. 배포·운영 확인은 Acceptance에 포함된 경우에만 추가한다. worktree·runtime 삭제 준비는 별도이며, 자동 삭제를 켠 작업에서는 merge 전에 충족해야 한다.

## 1. 불변 원칙 5개

### 1. 작업별 분리

변경은 해당 task worktree에서 한다. 원본 checkout은 기준점으로 유지한다. 예외는 0장에 한정한다.

### 2. 동시 수정 방지

worktree당 writer는 하나다. 사람의 직접 편집도 writer로 친다.

교대할 때는 의도한 소스·문서 변경을 커밋하고 이전 writer의 백그라운드 명령·하위 agent·heartbeat가 종료됐는지 확인한다. 비밀정보나 ignored runtime data를 커밋하라는 뜻은 아니다. 권한상 일반 branch에 커밋하지 않는 workflow 변경은 15장의 patch 보존·전달로 대체한 뒤 작업 트리를 정리한다.

리뷰어는 수정하지 않는다. 지적 반영은 writer가 맡는다. 테스트도 캐시·DB·산출물을 바꿀 수 있으므로 공유 runtime에서 동시에 돌리지 않는다.

### 3. 검토 대상 고정

리뷰 결과에는 검토한 full head SHA를 기록한다. 필요하면 base SHA와 통합 검증 범위도 적는다.

그 뒤 추가된 변경은 자동으로 리뷰된 것이 아니다. 변경된 diff와 영향을 받는 맥락을 다시 검토한다.

### 4. 교대 시 상태 기록

중단·교대 전 작업 상태를 기록하고 필요한 변경을 커밋·push한다. 검증 결과는 **통과 / 실패 / 미실행**으로 구분한다.

진행 중에는 task 파일을 기본으로 쓴다. 이미 유효한 PR handoff가 있으면 크기 분류만으로 task를 새로 만들지 않는다. **task 내용을 PR로 승격하고 삭제한 직후부터** 진행 기록은 PR에 남긴다. 아직 Draft 상태이거나 리뷰·지적 반영 중이어도 동일하다. task와 PR에 별개의 최신 handoff를 유지하지 않는다.

push에 실패했으면 그 사실과 남은 local commit을 기록한다. “백업 완료”라고 적지 않는다.

### 5. main 반영은 사람이 승인한 대상만

사람이 저장소·PR·head SHA·merge 방식을 확인하고 명시적으로 승인한다.

파일럿 기본은 사람이 GitHub UI에서 직접 merge하는 것이다. 후보를 검토하는 동안 writer를 멈추고, merge 직전에 PR head와 필요한 검사·리뷰 상태를 대조한다. UI 조작이 CLI의 원자적인 head 일치 조건과 같다고 가정하지 않는다. 그 조건이 필요하면 사람이 권한 있는 환경에서 11장의 고정 명령을 직접 실행한다.

AI merge를 별도로 활성화한 경우에는 Paseo의 **해당 merge 명령에 대한 사람 권한 프롬프트**로 승인한다. 채팅의 “ㅇㅋ”를 AI merge 실행 승인으로 해석하지 않는다.

AI merge는 승인 당시의 head SHA가 일치하는 조건으로만 실행한다. 프롬프트가 매번 사람에게 뜨는 것을 확인하지 못했으면 AI merge를 활성화하지 않는다.

## 2. 기본값

| 영역 | 기본값과 변경 조건 |
|---|---|
| 분기 | 최신 `origin/main`. 선행 작업에 의존하면 기준 branch·SHA를 task에 기록 |
| 브랜치 갱신 | 깨끗한 작업 트리·index에서 `origin/main`을 merge하고 관련 check 후 push한다. workflow 충돌·권한 거부는 15장의 중단·사람 경로를 따른다. force push와 공유 history 재작성은 하지 않는다 |
| main 반영 | 파일럿에서는 squash merge |
| 이름 | Paseo 자동 이름 허용. 직접 지정하면 `<type>/<slug>`. 버릴 조사는 `spike/` |
| 동시 writer와 진행량 | 상한 2명. 먼저 S·M을 직렬로 완료한 뒤 병렬 시험. 구현·리뷰·승인 대기 결과를 합쳐 최대 2개로 시작 |
| 리뷰 | writer를 멈춘 같은 worktree. 병렬 실행이 필요하면 독립 runtime을 갖춘 detached worktree |
| 일시중단 | worktree 유지. writer·불필요한 서비스 중지 후 handoff |
| 7일 경과 | 정리 검토 대상. 자동 폐기·archive 조건이 아님 |
| merge 실행·archive | 사람 직접 merge·수동 정리로 시작. 자동 archive는 끄고, 선택 기능은 19장의 조건 충족 후 활성화 |
| 프로필 | Plan·C / Work·C / Build·X / Review·C / Review·X를 후보로 둔다. 당장 사용할 경로만 먼저 확정 |
| 권한 | 최소한의 필요한 승인. Full Access·Bypass를 기본값으로 쓰지 않음 |
| 세션 교체 | 역할·provider 변경 또는 문맥 혼선 등 실제 신호에 따라 결정 |
| 비밀 원본 | `~/.config/dev-secrets/<repo>/development.env` |
| Paseo tools | 파일럿 동안 끔. 이후 사람이 요청한 제한된 용도로 사용 |

## 3. 디렉터리와 문서 위치

| 경로 | 용도 |
|---|---|
| `~/workspace/kerbe/` 및 각 repo 원본 | main 기준점. 일반 AI 편집·커밋 금지 |
| `~/workspace/home-dev-ops/` | 운영 모델과 복구 절차를 담는 private repo. 비밀값 없음 |
| `~/scratch/` | git이 아닌 일회성 실험 |
| `~/.paseo/worktrees/` | Paseo 관리 영역. 수동 생성·삭제를 하지 않음 |
| `~/review-worktrees/` | 필요할 때만 쓰는 수동 detached review 공간 |
| `~/.config/dev-secrets/<repo>/` | 개발용 비밀 원본 |
| `~/.config/git/ignore` | 전역 ignore. `.env.example` 등 공개 템플릿은 추적 가능하게 유지 |

각 repo에는 필요한 문서만 둔다.

- `AGENTS.md`: 해당 repo의 agent 실행 지침 정본. 원칙 5·merge 명령 형태·handoff·재개·setup 금지 우회·workflow·Docker 규칙과 실제 명령 지도를 200줄 이내로 둔다.
- `CLAUDE.md`: AGENTS import와 필요한 Claude 전용 설정. 공통 지침 복제 금지.
- `README.md`, `paseo.json`, `Makefile`, `scripts/dev-setup`, `.env.example`.
- `docs/PRD.md`, `ARCHITECTURE.md`, `STATE.md`, `ROADMAP.md`.
- `docs/decisions/YYYY-MM-DD-<slug>.md`, `docs/research/YYYY-MM-DD-<slug>.md`.
- `docs/tasks/<branch-id>.md`: 진행 중 handoff. branch 이름을 경로에 안전하게 정규화하고 충돌하면 짧은 hash를 붙인다.

worktree는 공통 Git 디렉터리의 객체·설정 등을 공유한다. 원본 repo의 삭제·이동·공통 설정 변경은 관리 작업으로 다룬다. worktree 폴더만 복사하는 것을 완전한 Git 백업으로 보지 않는다.

지침은 repo 내부 또는 provider가 실제로 읽는 사용자 전역 위치에 둔다. `~/workspace/AGENTS.md`가 `~/.paseo/worktrees/`에 자동 적용된다고 가정하지 않는다.

사람이 수행하는 P0 실측·PAT 관리·guard 설치·자동 archive 설정·복구 절차와 검토 이력은 `home-dev-ops`에 둔다. AGENTS에 설치 과정과 과거 판정표를 복제하지 않는다. `K12_AGENTS_draft.md`는 적용 초안이며 Kerbe의 실제 명령·문서 경로·핫 파일과 P0 결과를 채운 뒤 반영한다.

## 4. Workspace와 병렬 작업

| Workspace | 허용 작업 |
|---|---|
| 원본 Local | 코드 Q&A·여러 작업에 걸친 조사·PR diff 정적 리뷰. 테스트·설치·생성물 출력 없음 |
| Task Worktree | 계획의 저장·구현·테스트·문서·커밋. writer 1명 |
| Spike Worktree | 조사·프로토타입. writer 1명 |
| 기존 PR Worktree | 해당 PR 수정. 이미 같은 branch의 worktree가 있으면 그것을 재사용 |
| Detached Review Local | 고정 SHA의 리뷰. 필요한 테스트는 별도 runtime에서만 실행 |

원본 Local의 “읽기 전용”은 우선 운영 규칙이다. 실제 sandbox 보장이 있는지는 7장의 실측 결과로 구분한다.

파일럿에서는 **한 worktree를 하나의 활성 workspace에서 관리한다.** 사람이 Paseo에서 task worktree를 준비한 뒤 agent에 작업을 맡긴다. agent는 배정된 공간에서 필요한 commit·작업 branch push·PR 생성을 자율적으로 수행하지만 요청 범위 밖의 새 결과나 추가 worktree를 임의로 만들지 않는다. detached review·경쟁 구현용 추가 worktree도 사람의 생성 요청이 있을 때만 만든다. provider 교대는 같은 workspace의 세션·실행을 넘기며 archive로 처리하지 않는다.

원본의 local main이 오래됐을 수 있으므로 새 task의 기준은 최신 `origin/main`으로 확인한다. 원본의 fetch·main 동기화와 Git 설정 관리는 일반 구현과 구분해 실행한다.

병렬 작업은 다음만 조율한다.

- AGENTS에 적힌 핫 파일은 가능한 한 한 branch가 먼저 처리한다. lockfile·migration·등록 테이블·라우팅·STATE가 대표적이다.
- STATE 때문에 모든 작업을 직렬화하지 않는다. Ready 시점에 필요한 문서 갱신 순서를 조율한다.
- ADR 이름은 날짜와 slug로 구분한다.
- migration은 사용하는 도구의 식별자·의존 순서를 따른다. 지원할 때 타임스탬프를 사용하며 이름이 달라도 스키마 충돌은 별도로 검토한다.
- lockfile 충돌은 요구 의존성을 먼저 결정한 뒤 고정된 도구 버전으로 재생성하고 diff를 확인한다.
- Ready 전에 최신 base를 반영하고 관련 check를 다시 돌린다. 테스트 통과만으로 모든 의미상 충돌이 없어졌다고 보지 않는다.

## 5. Worktree·branch lifecycle과 데이터 보존

### 일시중단

오늘·내일 이어갈 작업은 worktree를 유지한다. task를 갱신하고 commit·push한 뒤 writer와 불필요한 서비스를 멈춘다.

**Archive는 일시중단이 아니다.** 마지막 연결 workspace의 archive는 관리되는 worktree와 그 안의 ignored 파일을 제거할 수 있다. 설정한 teardown은 별도 volume까지 지울 수 있다. 디렉터리가 남아 있다는 사실만으로 runtime이 보존됐다고 보지 않는다.

Paseo v0.10.3 소스에는 teardown 뒤 다른 활성 workspace의 디렉터리 참조를 확인하는 경로가 있다. 동일 worktree의 공유 runtime을 먼저 정리할 수 있으므로 4장의 단일 활성 workspace 원칙을 따른다. 이 소스 확인과 K12 설치본의 재현 시험은 구분한다.

### Archive 허용 조건

다음을 모두 만족해야 한다.

1. merge 완료 또는 사람이 명시적으로 종료·폐기·원격 보존 후 보류를 결정했다.
2. 보존해야 할 소스·문서·local-only commit이 남아 있지 않다.
3. 필요한 ignored 파일·DB·volume 데이터의 보존이 끝났다.
4. writer와 해당 자원을 사용하는 실행이 끝났고 정리 대상이 특정됐다.

7일 경과는 위 판단을 시작하는 신호다. push만 확인해서 archive하지 않는다.

### 자동 archive

파일럿 시작 시 merge 후 자동 archive는 끈다. 수동 archive도 같은 보존 조건을 따르며, 첫 파괴적 정리 전에 폐기 가능한 자원으로 소유 범위와 실패 처리를 확인한다. 자동 archive는 실제 조작을 줄일 가치와 안전한 적용 범위가 확인된 뒤 별도로 켠다.

개발 데이터는 seed·migration 등으로 재생성 가능하게 만든다. 대체할 수 없는 데이터는 처음부터 삭제 범위 밖의 보존 경로나 external volume에 둔다. 영속 자원도 작업별로 분리하며 여러 writer가 같은 DB를 공유하지 않는다.

자동 archive는 **삭제될 worktree와 연결 runtime data가 재생성 가능하거나 이미 별도 보존된 작업**에만 허용한다. external volume은 Compose의 down으로 지워지지 않지만 그 자체가 백업은 아니다. 예상 밖에 생긴 ignored 산출물의 보존 확인도 생략하지 않는다.

자동 archive를 켠 작업은 task 삭제와 Ready 전환 전에 필요한 데이터를 worktree·삭제 예정 volume 밖으로 보존한다. 자동 삭제가 꺼져 있으면 보존·정리 대기를 PR에 남긴 채 Ready·merge할 수 있다. 단, Acceptance나 검증 근거가 데이터 보존에 의존하면 보존도 Ready 조건이다. 삭제 전에는 어느 경로든 필요한 데이터의 보존을 완료하고, 복원 위치·절차를 삭제되지 않는 기록에 남긴다. 비밀값 자체를 PR에 올리지 않는다.

task 파일의 “백업 필요” 한 줄은 보존 완료의 증거가 아니다. 자동 archive의 범위를 작업별로 제한할 수 없는 환경에서는 예외 데이터가 있는 동안 해당 자동화를 끄고 수동으로 처리한다.

### Teardown

이 worktree의 정확한 compose project와 소유 자원만 정리한다. 프로젝트 전용 volume은 보존 조건 충족 후 삭제할 수 있다. 외부·공유 volume과 다른 작업 자원은 삭제하지 않는다.

보존 실패가 있으면 파괴적 정리를 시작하지 않는다. 정리 명령이 실패하면 성공으로 숨기지 않고 남은 자원 이름·오류를 삭제될 worktree 밖에 남긴다. workspace의 보관 표시와 teardown·디렉터리 제거 완료는 구분한다. 실패 후에는 실제 남은 자원·실행 결과를 확인하며 archive 재시도가 같은 teardown을 다시 실행하거나 안전하게 완료한다고 가정하지 않는다.

### 브랜치 정리

`[gone]`은 remote tracking ref가 사라졌다는 뜻이다. merge 증명이 아니다.

삭제 전에 다음을 확인한다.

- 대응 PR이 merged이거나 사람이 명시적으로 폐기했다. **closed만으로는 부족하다.**
- PR에 포함되지 않은 추가 커밋이나 보존하지 않은 local-only 작업이 없다.
- 연결된 활성 worktree와 writer가 없다.
- 필요한 작업 기록과 데이터가 보존돼 있다.

squash merge는 단순한 Git ancestry 판정과 다를 수 있으므로 PR의 병합 기록과 실제 변경도 확인한다.

## 6. 역할과 프로필

역할 분담은 초기 가설이다. 실제 결과로 조정한다.

| 작업 | 시작 방식 |
|---|---|
| 명확한 구현·테스트·재현 가능한 버그 | Build·X |
| 원인 불명 버그 | Codex로 재현·계측. 같은 방향으로 반복 실패하면 Claude 독립 분석 검토 |
| 모호한 요구·설계 선택 | Plan·C로 범위·대안을 정리 |
| PRD·ARCHITECTURE·ADR·research | Claude를 우선 고려하고 Codex가 사실·코드 대조 |
| 작은 정비·문서 수정 | 현재 provider |
| 의존성 갱신·merge 충돌 | Codex 우선. 리뷰 여부는 위험 트리거로 판정 |

독립 리뷰는 마지막 writer와 반대 provider를 기본 선택으로 한다. provider 차이만으로 독립성이나 정확성을 보장하지 않는다. 여러 provider가 작성에 참여했다면 그 사실도 reviewer에게 알리고 새 검토 맥락에서 실패 조건·반례를 확인한다. 반대 provider를 사용할 수 없을 때의 대체 판단은 10장을 따른다.

| 프로필 | 초기 설정 | 역할과 제한 |
|---|---|---|
| Plan·C | Claude / 높은 추론 / Plan | 분석·초안. task·ADR 저장은 승인된 쓰기 또는 Work 전환으로 처리 |
| Work·C | Claude / 중간 추론 / Accept Edits | 문서와 Claude 구현 |
| Build·X | Codex / 중간 추론 / Default Permissions | 구현·테스트·Git·PR. 실효 sandbox·approval 정책 확인 |
| Review·C | Claude / 높은 추론 / Plan | 수정 금지. Plan이라는 이름만으로 OS 수준 읽기 전용이라고 표현하지 않음 |
| Review·X | Codex / 높은 추론 / 검증된 Read-only 우선 | 지원 여부와 실제 제한을 P0에서 확인. 불충분하면 운영상 수정 금지 fallback 사용 |

Review·X fallback은 Default Permissions + 수정 금지 지침 + 전후 tracked/untracked 상태·diff 확인이다. 이것은 읽기 전용 sandbox와 동등하지 않으며 ignored 파일이나 DB의 무변경을 증명하지 못한다.

기술적 Read-only에서는 쓰기가 필요한 테스트가 막힐 수 있다. 기본은 정적 리뷰이고 실행 검증은 writer·CI가 맡는다. 읽기 전용 리뷰를 계속하려고 소스·설정 쓰기나 sandbox 밖 실행의 승격을 승인하지 않는다. 필요한 독립 실행 검증은 처음부터 허용 범위와 runtime이 분리된 환경에서 한다. PR 코멘트도 원격 쓰기이므로 리뷰 결과 기록을 이유로 권한을 넓히지 않는다. 현재 권한에서 작성할 수 없거나 미확인이면 10장의 사람 전달·writer 대리 게시 경로를 사용한다.

최대 추론 강도는 필요할 때만 사용한다. 다섯 프로필 전체 확정은 개발 착수 조건이 아니다. 실제 사용할 writer·review 경로만 먼저 확인하고 프로필 수는 사용 후 조정한다.

## 7. 권한 정책과 실측

다음 표는 **운영 의도**다. 두 provider에 동일한 설정 문법이나 동일한 승인 동작이 있다고 가정하지 않는다.

| 구분 | 의도 |
|---|---|
| 일상적으로 허용 | task 편집·개발 검증·git add/commit·작업 branch push·PR 생성/조회/설명 갱신 |
| 별도 승인 | AI merge 활성화 후 PR merge 매회, 승인 범위를 벗어나는 migration·외부 부작용·비용 발생 |
| 일반 개발 agent에 금지 | 비활성 상태의 merge·main 직접 push·force push·권한 설정/rules 및 AGENTS의 AI merge 상태 줄 직접 변경·repo 삭제/관리 설정 변경·sudo/rootful Docker로 우회 |

개발용 DB migration의 사전 승인 범위가 없다면 실행 전에 묻는다. 단순 조회 API까지 일괄적으로 매번 승인 대상으로 만들지는 않는다.

### 파일럿의 merge 차단

**merge 차단은 P0 필수이고 AI merge의 승인 시험은 선택 기능이다.** 사람이 사용할 Claude 사용자 설정에 `Bash(gh pr merge *)`를 deny로, Codex rules에 아래 prefix를 forbidden으로 둔다. 실제로 사용하는 Paseo provider·프로필에서 차단을 확인하고, 아직 확인하지 않은 실행 경로는 개발용으로 열지 않는다. 사용하지 않을 provider 전체를 미리 시험할 필요는 없다.

```python
# 파일럿: 사람이 설치하는 Codex merge 차단 규칙
prefix_rule(
    pattern = ["gh", "pr", "merge"],
    decision = "forbidden",
    justification = "AI merge is disabled. The user merges directly.",
)
```

Claude는 matching deny가 ask·allow보다, Codex는 matching forbidden이 prompt·allow보다 우선한다. 이 규칙은 해당 호출 형태를 막는 사고 방지 장치이며 직접 API나 모든 shell 형태를 차단하는 보안 경계는 아니다. 운영상 merge 금지는 모든 호출 경로에 적용한다.

**차단 시험:** 사람이 대상과 호출을 지정한 명시적 시험 요청으로만 수행한다. 시험 repo의 존재하지 않음을 확인한 PR 번호 또는 merge돼도 무해한 폐기용 PR을 사용한다. 개발 중인 실제 PR로 시험하지 않는다. Codex는 관련 프로세스를 안전하게 재시작해 rules를 로드한 뒤 실제 사용할 네트워크·권한 설정의 Paseo 세션에서 시험한다. 요청에는 “지정한 명령을 한 번만 실행하고, 거부되면 다른 방법을 시도하지 말고 결과만 보고하라”를 포함한다. 다른 호출 경로를 시도했다면 그 사실도 시험 결과에 기록한다.

- 권한 규칙이 해당 호출을 실행 전에 거부했다는 증거가 있으면 차단 성공이다. agent의 말로 된 거절이나 `execpolicy check` 결과만으로 통과시키지 않는다.
- gh 프로세스가 실행돼 “PR 없음”·인증 오류 등을 출력했다면 **차단 실패**다. 그 오류 덕분에 merge가 안 된 것을 성공으로 세지 않는다.
- 거부 주체나 실행 여부를 확인할 수 없으면 통과로 기록하지 않고 해당 경로를 보류한다.
- provider·실효 설정·시험 호출·거부 근거를 운영 기록에 남긴다. 규칙·버전·실행 모드가 바뀌면 영향받는 차단을 다시 확인한다.

**권한 설정의 소유권:** agent는 사용자·project·local의 권한 설정과 rules 파일, AGENTS의 AI merge 상태 줄을 수정하지 않는다. 단, base 갱신으로 main의 AI merge 상태 줄을 그대로 받는 것은 허용한다. 권한 규칙을 스스로 완화하거나 다른 호출 경로로 우회하지 않는다. 필요한 변경은 사람이 수행하고 트리거 6번의 독립 리뷰와 적용 후 검증으로 처리한다. agent는 제안·리뷰만 맡으며 설정이나 상태 줄을 직접 바꾸지 않는다. 같은 OS 사용자이므로 이 변경 금지 자체는 운영 규칙이다.

AGENTS 상단에 AI merge 상태를 명시한다. 상태가 없거나 불명확하면 비활성으로 취급한다. 비활성 상태의 유일한 시험 예외는 위의 명시적으로 요청된 차단 시험이며, 그 요청을 업무 PR의 merge 승인으로 확대하지 않는다.

### AI merge 활성화 시 추가할 승인 경로

사람이 차단 규칙을 ask·prompt로 바꾸고 아래 승인 시험을 진행한다. 기존 deny·forbidden에 prompt를 추가하는 것만으로 전환하지 않는다. 시험이 통과한 provider·프로필과 기록을 명시하고 AGENTS 상태를 사람이 갱신한 뒤에만 AI merge를 사용한다.

승인 시험 실패뿐 아니라 **AI merge를 비활성화할 때마다** 사람이 deny·forbidden을 복구한다. 관련 프로세스의 rules 로딩과 실제 사용할 Paseo 세션의 차단을 다시 확인하고 AGENTS 상태·운영 기록을 비활성으로 갱신한다. 상태 줄은 branch별 사본이므로 기존 branch에 남은 “활성” 문구가 차단 복구를 대신하지 못한다. 사람 직접 merge로 전환하는 동안 agent의 merge 실행은 중단한다.

- Codex의 Git 변경 승인은 필요한 명령 범위로 처리한다. 불편하다고 Full Access로 전환하지 않는다. AI merge 활성화 후에는 네트워크 차단에 따른 승격 요청에 의존하지 않고 명령별 prompt 규칙으로 지정한다. 영구 allow는 사람이 실제 허용 범위와 승인 피로를 검토해 결정한다. `git commit`의 sandbox 밖 실행은 hook도 포함하므로 직접 만든 repo라는 이유만으로 전역 allow를 추가하지 않는다.
- Claude 사용자 설정에는 `Bash(gh pr merge *)`처럼 사용하는 merge 호출을 잡는 명시적 ask 규칙을 둔다. 현재 공식 문서의 우선순위는 deny → ask → allow다. 기존 allow가 저장됐어도 matching ask가 우선하는지 설치 버전에서 확인한다. broad shell·`gh` 전체 허용에 기대지 않는다.
- merge는 CLI·직접 API·다른 도구 등 경로와 관계없이 같은 사람 승인 규칙을 적용한다.
- Auto-review는 코드 리뷰와 다르다. Codex의 권한 자동 검토와 Paseo의 버전별 명칭·UI를 구분한다. 파일럿 Build와 merge 승인에는 사용하지 않는다.
- 규칙 파일과 local hook은 같은 OS 사용자 agent를 기술적으로 봉쇄하는 보안 경계가 아니다.

Codex의 기본 구성 의도는 `approval_policy = "on-request"`와 `approvals_reviewer = "user"`다. granular 정책을 쓴다면 execpolicy prompt 범주의 승인을 허용해야 한다. 이 활성화 시험에서는 승인 범주 차단에 따른 거부를 사람 승인 성공으로 기록하지 않는다. P0 차단 시험의 성공 기준과 구분한다.

```python
# AI merge 활성화 시험용: 사람이 기존 forbidden을 바꾸는 예시
prefix_rule(
    pattern = ["gh", "pr", "merge"],
    decision = "prompt",
    justification = "PR merge requires the user's approval for this exact command.",
)
```

규칙은 prefix와 호출 형태에 의존한다. merge 명령은 11장의 형태로 통일하고 다른 옵션 순서·절대 경로·복잡한 shell wrapper·직접 API로 규칙을 우회하지 않는다. `execpolicy check`의 prompt 결과는 규칙 판정 자료이며 Paseo UI의 사람 승인을 증명하지 않는다.

사람은 제안된 영구 allow의 실제 허용 범위를 확인한 뒤 수락한다. `gh`·`gh pr`·`gh api` 전체처럼 merge 규칙이 다루지 않는 쓰기 경로까지 여는 broad allow는 수락하지 않는다. 하위 명령까지 좁혔다는 이유만으로 자동 승인하지도 않는다.

현재 Claude 공식 문서는 v2.1.211 이후 영구 승인을 원본 checkout의 `.claude/settings.local.json`에 저장해 worktree에도 적용한다고 설명한다. 설치 버전을 먼저 확인한다. 해당 local 설정 파일은 ignore하며 자동 저장에 따른 관리 파일 변경을 source 구현으로 취급하지 않는다.

검증한 프로필에서 세션을 만들고 실효 설정을 확인한다. 프로필 이름만으로 보장하지 않으며 네트워크·권한 모드·provider 버전이 바뀌면 영향을 받는 차단·승인 동작을 다시 확인한다. Codex 규칙은 실험 기능이므로 AI merge를 쓰는 경우 Codex 업데이트 후 merge prompt와 승인 경로를 다시 검증하기 전에는 해당 AI merge를 중단한다.

**모든 권한 실측은 Paseo에서 생성한 Claude·Codex 세션으로 수행한다.** 독립 CLI 시험은 보조 자료이며 통과 판정의 대체가 아니다. Codex 규칙 변경은 Codex writer가 실행 중이지 않은 점검 시간에 한다. Paseo가 agent별 프로세스를 띄우는지 공유 app-server를 쓰는지 확인하고 재시작 영향을 받는 세션의 상태를 보존한 뒤 관련 실행을 정상 종료한다. 규칙 변경 후 실제 Codex 프로세스 재시작을 확인하며 새 대화만 만드는 것으로 충분하다고 보지 않는다. 다른 작업을 강제로 종료해 적용하지 않는다.

사람은 Paseo의 Claude SDK·실행 방식이 읽는 `settingSources`와 설정 파일을 확인한다. 사용자 설정에 규칙이 있다는 사실만으로 로드됐다고 가정하지 않는다. 사용자 설정을 읽지 않으면 project 설정을 실제로 읽는 경우에 한해 사람이 repo의 `.claude/settings.json`에 같은 규칙을 둔다. 파일럿은 deny, AI merge 활성화 시험은 ask다. project의 deny·ask는 workspace trust에 따른 allow 제한과 구분되지만 source 자체를 읽지 않으면 효력이 없다. 변경은 트리거 6번 대상이며 agent의 직접 수정은 금지한다. 차단 단계에는 실제 거부, 활성화 단계에는 Paseo 사람 승인 카드까지의 전달을 각각 확인한다.

실제 Paseo·Codex·Claude 버전과 아래 동작을 **기능별로** 기록한다. 기본 개발 착수에는 사용할 writer·review 경로의 설정 로딩·쓰기 범위·commit/push/PR 권한·merge 차단과 Auto-review 관여 여부를 확인한다. reviewer가 기존 권한으로 PR 코멘트를 작성할 수 있는지도 확인하고, 불가하거나 미확인이면 10장의 전달·대리 게시 경로를 사용한다. 사용하지 않을 provider·프로필 전체를 먼저 시험하지 않는다.

아래 사람 승인·head 변경 거부 시험은 **AI merge를 실행할 provider·프로필의 활성화 조건**이다. AI merge를 사용하지 않으면 그 시험은 보류할 수 있지만 위 P0 차단 시험은 생략하지 않는다. 한 provider의 통과로 다른 provider를 대신하지 않는다.

1. Claude Plan / Accept Edits의 파일 쓰기·shell 권한과 실제 설정 로딩 범위. Paseo에서 영구 승인을 저장했을 때 파일 위치를 확인하고 ignore한다. worktree 안의 local 설정은 archive 시 사라질 수 있으며 필수 merge 차단·승인 규칙의 유일한 저장소로 삼지 않는다.
2. Codex Default / Read-only의 존재와 실제 쓰기 제한. merge 실행 세션의 실효 승인 정책이 `never`이거나 Full Access·자동 승인 경로가 아닌지도 확인한다.
3. commit·작업 branch push·PR 생성·merge에서 승인 요청이 뜨는 위치.
4. merge 규칙이 적용된 상태에서 네트워크 off/on 각각 **매번 사람에게 묻는지**. on 시험에는 `network_access = true`만 켜고 별도 proxy·도메인 제약에 기대지 않는 구성도 포함한다. 임시 시험 repo에서 영구 allow를 추가한 뒤에도 matching prompt/ask가 유지되는지 확인한다. 규칙 없는 기본 동작은 비교용 관찰이며 통과 조건이 아니다.
5. Auto-review가 어떤 승인에 관여하는지.
6. 승인 후 head가 바뀌면 merge가 거부되는지. 모바일에서도 repo·PR·방식·전체 명령과 full SHA를 펼쳐 확인할 수 있는지 점검한다.
7. Codex 프로세스가 agent별인지 공유인지와 안전한 재시작 범위. Claude 사용자 설정을 읽지 않을 경우 project 설정 fallback의 실제 로딩·ask 동작.

자동 merge 실행은 위 실측으로 실제 설정 로딩과 매회 사람 승인·head 변경 거부가 확인된 뒤 허용한다. 어느 조건이든 실패하면 AI merge를 중단하고 이 장의 비활성화 절차로 차단을 복구한 뒤 사람이 GitHub UI에서 처리한다. 네트워크를 끄는 것만으로 실패한 명령 승인 검증을 대신하지 않는다. 개발용 네트워크 설정은 merge 실행 허용 여부와 별도로 결정한다.

## 8. Setup과 runtime 식별

repo의 `paseo.json`이 `scripts/dev-setup`을 호출한다. 기본 작업 기준이 `origin/main`이므로 setup 변경은 chore PR로 먼저 merge하고 새 worktree에서 검증한다.

setup은 Paseo 밖의 detached worktree에서도 실행돼야 한다. `PASEO_*` 경로가 없으면 `git rev-parse --show-toplevel`과 `git rev-parse --path-format=absolute --git-common-dir` 등을 이용해 현재 worktree와 공통 저장소를 식별한다. 환경변수가 있더라도 실제 Git 경로와 대조한다. 분리된 Git 디렉터리 등에서 원본 checkout이 필요한데 확정할 수 없다면 명시적으로 받거나 실패한다. 빈 값·공용 기본 이름으로 계속하지 않는다. detached 상태의 빈 branch 이름만으로 실패시키지는 않는다.

Paseo가 읽는 base의 커밋된 설정과 현재 task의 편집 중인 설정을 혼동하지 않는다. 외부 repo처럼 설정을 커밋할 수 없는 경우에만 별도 Project Settings를 사용한다.

### Setup이 하는 일

- 멱등하게 실행하며 가벼운 repo는 90초 이내를 목표로 한다.
- LFS를 쓰는 repo에서만 필요한 LFS 데이터를 받는다.
- uv는 `uv sync --locked`, pnpm은 frozen-lockfile 설치를 사용한다.
- worktree의 `.env`가 있으면 유지한다. 없으면 repo 밖 원본에서 복사한다. 원본도 없으면 안전한 example을 사용하고 필수 값 부족은 명확히 알린다.
- runtime의 프로젝트 식별자와 필요한 경량 생성물을 준비한다.
- 성공한 뒤에만 완료 표시를 남긴다. 관련 setup·lockfile·도구 조건이 바뀌면 기존 표시를 그대로 신뢰하지 않는다.

### Setup이 하지 않는 일

DB migration·컨테이너 기동·전체 테스트·전체 빌드는 별도 script로 둔다. 설치가 무거우면 repo 정책으로 on-demand 설치를 사용할 수 있지만 완료 표시는 무엇이 준비됐는지 구분해야 한다.

공통 경량 setup과 on-demand script는 단순화를 위한 선택이다. 작업별 조건 분기가 기술적으로 절대 불가능하다고 규정하지 않는다.

### 포트와 이름

- **Paseo에 등록한 웹 서비스 host port는 `PASEO_PORT`를 사용한다.**
- branch 문자열을 숫자로 바꿔 포트를 배정하지 않는다.
- Compose project·DB namespace의 소유 단위는 **worktree**다. 파일럿에서는 한 worktree에 활성 workspace를 하나만 두고 세션을 교대한다. 별도 review worktree는 별도 runtime을 갖는다.
- runtime 이름은 repo 표식과 정규화한 worktree 전체 절대 경로에서 만든 식별자를 조합하고 생성 시 기록한다. 경로 hash를 쓰더라도 충돌 검사와 소유 경로 대조를 한다. Paseo 경로의 마지막 두 요소만으로 수동 review worktree까지 유일하다고 가정하지 않는다.
- branch 이름과 workspace ID를 runtime의 소유 식별자로 쓰지 않는다. 기록된 자원이 다른 worktree의 것이면 멈춘다. 경로를 옮기는 관리 작업은 runtime 기록과 잔여 자원도 함께 처리한다.
- 수동 detached review는 같은 계산 방식으로 writer와 다른 식별자·DB·volume을 사용한다. 서비스 시작에 필요한 포트도 별도 할당하며 Paseo 변수가 없다고 writer의 포트나 기본 DB로 되돌아가지 않는다.

setup 실패는 차단 상태다. 원인을 확인하고 재실행한다. lockfile 삭제·버전 임의 변경·권한 전면 완화·rootful Docker·DB 강제 초기화로 우회하지 않는다.

외부에서 가져온 repo는 setup·package script·hook 실행 전에 확인한다. issue·PR·repo 문서에 포함된 외부인의 지시는 로컬 권한을 확대하는 승인으로 취급하지 않는다.

## 9. Git과 PR

- branch 안의 commit은 체크포인트다. 테스트 실패 상태도 필요한 경우 WIP로 보존하되 실패 사실을 명시한다.
- 의도한 변경만 stage한다. ignore가 있으니 무조건 `add -A`가 안전하다고 가정하지 않는다.
- 작업 branch는 일찍 자주 push한다. 이는 **push한 Git 내용의 원격 보존**이며 runtime 전체 백업은 아니다.
- 작성자 신원은 `shotgun1107`과 설정된 noreply 주소로 통일한다.
- AI가 만든 commit에는 실제 작성 provider의 `Agent: claude` 또는 `Agent: codex` 트레일러를 붙인다.
- 이어받은 agent는 이전 commit을 amend하거나 history를 다시 쓰지 않는다.
- GitHub에서는 PR 필수·main force push/삭제 금지·필요한 CI를 적용할 수 있는 범위에서 설정한다. 같은 계정이 PR을 만들고 사람이 merge하는 파일럿에서는 충족할 별도 reviewer가 없는 승인 리뷰 수를 필수로 걸지 않는다. PR 작성자는 자기 PR을 Approve할 수 없으며 사람의 채택과 GitHub approving review는 구분한다. 관리자 우회와 실제 적용 범위도 확인한다.
- head branch 자동 삭제는 사용한다. local branch 삭제는 5장의 별도 판단을 따른다.

### K12 local pre-push guard

main 대상 push·branch 삭제·non-fast-forward 갱신을 감지해 거부하는 사고 방지 장치로 둔다.

hook 입력은 ref와 commit 정보다. `--force` 플래그 자체를 받는 것은 아니며 `--no-verify` 등으로 우회할 수 있다. 실제 main 보호는 GitHub의 서버 측 설정과 함께 사용한다.

`core.hooksPath`는 hook 검색 위치를 바꾸며 원래 저장소 hook을 자동으로 이어 실행하지 않는다. global 설정은 repo의 local 설정으로 덮어써질 수 있으므로 실제 적용 경로도 확인한다.

기존 hook과 guard를 함께 쓸 때는 LFS pre-push를 포함한 필요한 hook을 명시적으로 연결한다. 양쪽에 동일한 인자와 stdin을 전달하고 실패 코드를 보존하며 자기 자신을 다시 호출하지 않게 한다. guard가 stdin을 소비한 뒤 빈 stdin으로 LFS를 호출하는 구현은 피한다. LFS repo에서는 새 객체를 push한 뒤 별도 빈 LFS cache의 checkout에서 실제 객체를 받을 수 있는지 1회 확인한다.

## 10. 검증·교차 리뷰·Ready

### 모든 변경

writer가 변경에 맞는 `check`를 실행하고 사람이 diff를 확인한다. 새 동작에는 의미 있는 테스트를 추가한다. 문구 수정 같은 변경에 구현을 따라 쓰는 형식적 테스트를 강제하지 않는다.

**S 작업도 아래 트리거가 있으면 교차 리뷰한다.**

### 교차 리뷰 트리거

1. 인증·권한·비밀정보.
2. DB 스키마·migration·데이터 삭제나 변환.
3. 공개 API·CLI·설정 포맷 등 외부 계약.
4. 동시성·비동기·캐시.
5. 새 의존성·major 업그레이드.
6. CI·Docker·setup·agent 권한이나 지침.
7. 실패 원인의 해결 대신 기대값·검사 범위를 바꿔 테스트를 통과시킨 경우. 정당한 변경이라도 근거를 확인한다.
8. 구현이 반복 실패해 접근 방향을 바꾼 경우.
9. ARCHITECTURE·ADR·PRD의 의미 있는 변경.
10. 큰 변경. 테스트 제외 300줄 또는 파일 10개는 보조 신호이지 안전 판정의 절대선은 아니다.

단순 오탈자까지 아키텍처 변경으로 취급하지 않는다. 반대 provider를 사용할 수 없으면 사람이 변경 위험과 검토 근거를 보고 직접 기술 리뷰 또는 같은 provider의 새 리뷰 세션·표적 검증 같은 대체 경로를 선택할 수 있다. agent가 한도·대기를 이유로 스스로 대체하지 않는다. PR에는 실제 방식·대상 SHA·한계를 구분해 기록하며 교차 provider 리뷰를 했다고 표시하지 않는다. 고위험 변경에서 검토의 충분성을 뒷받침할 근거가 없거나 필요한 독립 검토를 수행하지 못하면 Ready·merge를 보류한다.

### 리뷰 입력과 출력

입력은 완료 조건·고정 SHA의 diff·관련 코드·검증 결과다. 구현자의 자기 정당화를 먼저 주지 않는다.

출력에는 심각도별 지적·위치·실패 조건·근거·검토 SHA·미확인 항목·merge 가능 여부를 적는다. 최종 기록 위치는 해당 PR의 리뷰 코멘트다. reviewer는 코드·task를 수정하지 않으며 기존 권한으로 작성할 수 있을 때만 직접 게시한다.

PR 코멘트 작성이 불가하거나 미확인이면 reviewer는 결과와 검토 full SHA를 현재 응답에 남기고 PR 미기록 상태임을 알린다. 사람이 그 결과를 writer 세션에 전달한다. writer는 원문과 검토 SHA를 바꾸지 않고 PR 코멘트로 옮기고 reviewer와 대리 게시 사실을 표시한 뒤 게시 결과를 확인한다. 필요한 리뷰가 PR에 기록되기 전에는 Ready로 전환하지 않는다. 기록을 위해 reviewer의 쓰기·sandbox 밖 실행을 승격하지 않는다.

같은 worktree 리뷰는 writer와 충돌하는 실행이 끝난 뒤 시작한다. 필요한 실행 검증의 범위를 합의하고 source 변경이 생기면 리뷰 과정의 변경으로 숨기지 않는다.

병렬 정적 리뷰는 원본 Local에서도 고정 SHA의 Git 객체를 읽는다. 예를 들어 `git show <REVIEWED_FULL_SHA>:<path>`로 관련 파일을 확인한다. PR diff의 head와 관련 소스의 SHA를 일치시키며 원본 작업 트리의 main 파일을 리뷰 대상 코드로 혼동하지 않는다. 같은 저장소의 다른 worktree에서 만든 commit은 공통 객체 DB에 있으므로 보통 추가 fetch가 필요 없다. 원격 PR 등 필요한 객체가 없는 경우에만 가져온 뒤 고정한다. 실행 검증이 필요할 때만 detached review 공간을 추가한다.

사람이 병렬 실행 리뷰용 추가 worktree 생성을 요청하면 고정 SHA의 detached worktree를 별도 경로에 만들고 Local로 연다. setup·runtime 분리·종료·수동 제거를 담당자가 맡는다. Git은 같은 branch 중복 checkout과 달리 detached SHA worktree를 지원한다.

### Ready 조건

1. Acceptance를 충족했다.
2. 필수 check가 실제 실행돼 통과했다. 미실행은 통과가 아니다. GitHub의 skipped·neutral이나 merge 가능 표시만으로 실행 완료를 판단하지 않는다. 해당 없는 검사는 이유를 적는다.
3. 필요한 테스트·독립 리뷰를 수행했고 실제 검토 방식과 대상 SHA가 PR의 검증·리뷰 기록에 연결돼 있다.
4. 문서 영향을 처리했거나 영향 없음의 이유를 적었다.
5. 필요한 STATE 갱신을 했다.
6. 자동 archive를 쓰거나 Acceptance·검증 근거에 필요한 데이터는 보존했다. 자동 삭제가 꺼진 나머지 정리·보존 대기는 PR에 남길 수 있으며 삭제 전 5장의 조건을 충족한다.
7. task의 지속할 정보를 정본·PR로 옮기고 task 파일을 삭제했다.
8. PR 본문에 결과·검증·리뷰·남은 위험이 있다.

### 최종 후보를 만드는 순서

코드·문서·Ready에 필요한 보존 처리를 마친다 → Draft PR에 task의 완료 조건·진행 상태·남은 검증·Next·정리 대기를 옮기고 저장을 확인한다 → task를 삭제한다 → commit·push해 최종 후보 H를 만든다 → H에 대한 필수 검사와 리뷰 결과를 확인한다 → Ready로 바꾼다. 처음부터 PR handoff를 쓰는 작업은 정보 이동·task 삭제 단계를 생략한다.

PR로 옮긴 뒤에는 리뷰 지적·반영 상태·다음 행동을 PR의 handoff 항목에 갱신한다. 이 구간에서 중단되면 다음 세션은 PR과 실제 Git 상태를 대조해 재개한다.

검사는 작업 중에도 수시로 돌린다. 최종 기록은 H에 대응해야 한다. 수정으로 H가 바뀌면 영향을 받은 검사·리뷰를 갱신한다. 코드 테스트와 무관한 문서 삭제처럼 재실행이 불필요한 항목은 동일성 근거를 적되 새 H 전체를 자동으로 검증됐다고 쓰지 않는다.

task 삭제가 리뷰 뒤의 “그냥 정리 commit”으로 남아 승인 대상을 흐리지 않게 한다.

## 11. 사람 승인과 merge 실행

파일럿 기본은 사람 직접 merge다. AI는 PR의 기존 요약을 다음 정보로 정리해 사람이 변경의 의미와 근거를 함께 확인할 수 있게 한다. 별도 승인 문서는 만들지 않는다.

- **결과:** 사용자에게 보이는 동작이나 작업 목적상 달성한 변화.
- **근거:** Acceptance별 확인 결과와 필요한 diff·검증 링크. 미실행은 구분한다.
- **검토 상태:** full 후보 SHA, 검증·리뷰 SHA와 실제 검토 방식, 이후 변경의 처리.
- **남은 위험:** 미해결·미확인 항목, base 영향, 되돌리기 제약.
- **요청:** 명시한 저장소·PR·후보를 squash로 main에 반영할지.

승인 범위는 이 main 반영이며 별도 migration·추가 비용·데이터 삭제까지 확대하지 않는다. 모바일에서 근거를 충분히 확인할 수 없으면 큰 화면 검토나 추가 확인까지 보류한다. SHA 대조는 의미 검토를 대신하지 않는다.

아래 명령은 기본적으로 사람 실행용 참고다. agent는 7장의 조건을 충족하고 AGENTS의 AI merge 상태가 사람에 의해 활성으로 갱신된 경우에만 실행한다. 상태가 없거나 불명확하면 실행하지 않는다. 별도 지정된 P0 차단 시험은 7장의 범위만 따른다.

merge는 **고정 리터럴 인자만 있는 단일 명령**으로 실행한다. 아래의 꺾쇠괄호 항목을 실제 repo·PR 번호·승인한 full SHA로 치환한다. 쉘 변수·`$(...)`·리다이렉트·다른 명령과의 연결을 넣지 않는다. 필요한 조회는 미리 별도 명령으로 수행한다.

복잡한 shell 문법에서는 Codex가 스크립트 내부를 개별 명령으로 분해하지 않을 수 있으므로 `gh pr merge` prefix 규칙의 적용을 보장하지 못한다. 다른 정책이 승인이나 차단을 요구할 수도 있어 “항상 무승인 실행된다”고 단정하지 않는다. 단순 연결 명령의 일부는 파싱되더라도 이 운영 모델의 merge는 단독 실행으로 제한한다.

```bash
gh pr merge <PR_NUMBER> --repo <OWNER/REPO> --squash --match-head-commit <APPROVED_FULL_HEAD_SHA>
```

사람이 확인할 명령에는 repo·PR·방식·SHA가 드러나야 한다. 승인 후 shell에서 “현재 head”를 새로 조회해 그 값으로 바꾸지 않는다. `--admin`·`--auto`·`--delete-branch`는 사용하지 않는다. 원격 branch 삭제는 GitHub가 맡고 local branch 정리는 5장에 따른다. 파일럿에서는 merge queue도 사용하지 않는다. queue가 필수인 repo는 이 즉시 merge 흐름의 적용 대상에서 제외한다.

요약에는 리뷰 SHA와 승인할 SHA의 짧은 표기를 나란히 보여줄 수 있다. 고정 8자 비교를 동일성 검증으로 삼지는 않는다. 필요하면 식별 가능한 길이로 늘리고 기계적 비교와 `--match-head-commit`에는 항상 full SHA를 쓴다. 카드가 잘리면 전체 명령을 펼쳐 확인할 수 있어야 한다. 그렇지 않으면 사람이 GitHub UI에서 처리한다.

head가 바뀌어 거부되면 새 검사·리뷰 상태를 확인하고 다시 승인받는다. 같은 승인을 다른 SHA에 재사용하지 않는다.

**head 일치 조건은 base branch가 변하지 않았다는 보장은 아니다.** main에 다른 PR이 들어오면 통합 결과가 달라질 수 있다. 가능하면 required CI와 up-to-date base 정책을 유지한다. 지원되지 않으면 merge 직전에 base를 반영해 관련 check를 수행하고 merge를 순서대로 처리한다.

다른 파일의 계약 변경도 서로 충돌할 수 있으므로 핫 파일 비중첩만으로 재검증을 생략하지 않는다. base 갱신은 Ready 직전과 필요할 때 집중하며 task worktree에서 merge·관련 check·push 순서로 처리한다. GitHub의 Update branch 버튼은 기본 경로로 쓰지 않되 15장의 workflow 권한 거부가 확인된 경우에는 사람의 원격 갱신을 예외로 허용한다. 원격에서 갱신됐다면 fetch해 차이를 대조하고 안전하게 통합한 뒤 check와 검토 기록을 갱신한다. head가 바뀌면 변경 영향에 맞게 리뷰 결과와 승인을 갱신하되 처음부터 모든 리뷰를 반복하지는 않는다. merge 후 main CI는 추가 감시이며 merge 전 필수 검증을 대체하지 않는다.

squash 이후 main의 commit SHA는 PR head와 다르다. 승인 대상은 PR 입력 SHA이고 실제 merge 결과 SHA와 반영 완료를 PR에서 확인한다. merge됐다고 바로 정리 완료로 표시하지 않는다.

같은 GitHub 자격증명을 공유하면 GitHub만으로 사람과 agent를 구분할 수 없다. 이 승인 절차는 실측된 권한 설정·운영 규칙·서버 보호를 조합한 사고 방지 장치다.

## 12. 문서의 정본과 STATE

| 문서 | 담당 내용 |
|---|---|
| AGENTS | 실행 규칙·명령·문서 지도·재개 절차 |
| README | 사람용 소개와 quickstart |
| PRD | 의도한 동작과 요구사항 ID |
| ARCHITECTURE | 현재 구조·불변식. 제안 단계 설계는 구분 |
| decisions | 결정과 근거. 결정을 바꿀 때 새 ADR로 대체 관계 표시 |
| STATE | 검증한 소스 상태·알려진 문제·드리프트·다음 우선순위 최대 3개 |
| ROADMAP | 미래 순서 |
| research | 비권위 조사 결과와 한계 |
| tasks | 해당 branch의 진행 중 handoff |

각 사실은 한 곳을 정본으로 정하고 다른 문서는 링크한다. 의미 없는 중복을 줄이되 PR의 완료 요약까지 금지하지 않는다.

STATE는 **해당 코드 상태에서 확인한 내용**을 적는다. 상태를 바꾸는 PR에서 함께 갱신할 수 있다. “main에서만 검증된 것”이라는 문구는 쓰지 않는다. 배포나 운영 검증이 필요한 사실은 소스 검증과 구분한다.

STATE·ARCHITECTURE에 마지막 검증 날짜와 **실제로 확인한 기준 commit 또는 PR**을 기록한다. 문서 수정 후 자기 자신의 최종 SHA를 문서에 넣으려 하지 않는다. 최종 PR head·CI·review SHA는 PR 기록으로 연결한다.

코드와 문서가 다르면 구현 버그·승인된 사양 변경·낡은 문서 중 무엇인지 판정한다. 작은 것은 같은 PR에서 고치고 큰 것은 알려진 드리프트로 남긴다. 코드가 우선이라는 서열로 PRD를 자동 변경하지 않는다.

provider의 자체 메모리만 프로젝트 사실의 유일한 저장소로 쓰지 않는다. 내용 감사는 큰 기능이 끝나거나 드리프트가 반복될 때 한다. 링크·명령 존재·생성 문서 최신 여부는 기계적으로 검사할 수 있다.

## 13. 세션과 handoff

새 세션은 역할·provider를 바꾸거나 제약 망각·같은 시도 반복·옛 대화를 실제 diff보다 신뢰하는 혼선이 생길 때 연다.

compaction 후에는 task 또는 PR·현재 commit·남은 검증을 재확인한다. 일관성이 유지되면 같은 세션을 이어간다. 날짜 변경이나 재인증만으로 무조건 새 세션을 만들지 않는다.

crash 후에는 실제 상태를 먼저 확인한다. 이전 실행이 남아 있으면 중복 실행을 막고 재개 가능한지 판단한다.

M·L slice·R은 시작할 때 추적되는 task 파일을 기본으로 만든다. S는 한 세션에 끝나면 필수가 아니며 미완료로 넘길 때 만든다. 이미 필요한 복원 정보가 있는 PR handoff를 쓰고 있다면 task를 중복 생성하지 않는다. PR을 정본으로 쓰는 경우 GitHub 조회가 필요하다는 의존성을 받아들이고 위치를 명시한다. ignored `.task.md`를 유일한 기록으로 쓰지 않는다. task는 대체로 한 화면에 담고 Git log로 충분한 변경 목록을 반복해 옮기지 않는다. task를 PR로 승격하고 삭제한 직후부터 기록은 PR에 남긴다.

- 목표·완료 조건.
- 범위·기준 branch와 commit.
- 현재 writer.
- 중요한 결정·버린 대안의 짧은 이유.
- 완료한 변경과 확인 가능한 commit.
- 검증 결과·대상 revision·미실행.
- 다음 행동.
- 함정·runtime 식별자·필요한 데이터 보존 상태.

비밀값과 장황한 추론 과정은 쓰지 않는다.

재개할 때는 AGENTS·STATE → task 또는 PR → cwd·branch·commit·diff → 기록과 실제 상태 대조 → 이전 실행과 setup 확인 → 필요한 검증 → Next 순서로 진행한다.

기존 검증이 유효한 짧은 재개마다 무조건 전체 테스트를 반복할 필요는 없다. 반대로 근거가 없으면 과거의 “통과”를 그대로 신뢰하지 않는다.

사용량 한도로 이전 provider가 기록을 못 남겼으면 다음 provider가 Git·PR·파일을 대조해 상태를 복원한다. 실행 중인 이전 writer가 없는지 먼저 확인한다.

### 사람이 응답하지 않을 때

승인된 목표·범위 안에서 독립적으로 진행 가능한 일만 수행한다. 범위 변경·권한 확대·불명확한 외부 부작용·merge를 추정 승인하지 않는다. 필요한 질문을 묶어 기존 task·PR에 남기고 안전한 checkpoint를 보존한 뒤 막힌 경로를 멈춘다. 대기를 피하려고 새 결과나 추가 agent를 임의로 시작하거나 같은 부작용 명령을 반복하지 않는다.

heartbeat는 기계적인 장기 작업에만 만료 시간을 정해 사용한다.

## 14. Rootless Docker와 원격 미리보기

- rootless를 유지한다. sudo·rootful Docker·docker 그룹으로 우회하지 않는다.
- host에 게시하는 개발 포트는 `127.0.0.1`의 고포트로 제한한다.
- 웹 서비스는 Paseo service의 할당 포트를 사용한다. 개발 서버를 공개 Caddy에 붙이지 않는다.
- Compose project·DB·volume은 작업별로 분리한다. 고정 `container_name`은 쓰지 않는다.
- 의존 서비스는 같은 compose 네트워크에서 통신하게 한다. 컨테이너가 호스트 loopback에 그대로 접근할 수 있다고 가정하지 않는다.
- DB와 cache는 named volume을 우선 사용한다. 호스트 도구가 쓰는 `.venv`와 `node_modules`는 호스트에서 관리한다.
- source bind mount에 컨테이너가 파일을 써야 하고 이미지가 지원한다면 rootless container UID 0을 우선 검토한다.
- 읽기 전용 mount 또는 non-root 실행이 필요한 이미지는 그 요구를 따른다. 실제 UID 매핑과 생성된 파일·디렉터리 권한을 확인한다.
- archive 권한 오류를 모두 subuid 소유권 때문이라고 단정하지 않는다. 부모 디렉터리 권한·실행 중 프로세스·mount 등 실제 원인을 본다.
- 무거운 서비스는 자원 제한을 설정하고 실제로 적용되는지 확인한다. rootless라는 이름만으로 cgroup 제한 적용을 가정하지 않는다.
- 전역 volume prune은 하지 않는다. 이미지·build cache 정리도 디스크 필요와 다른 작업 영향을 보고 수행한다.
- 원격 미리보기는 회사 PC에서 허용된 Tailscale TCP 22 경로로 SSH local forwarding을 사용한다.
- 휴대폰 미리보기는 필요해질 때 별도 설계한다.

## 15. 비밀정보와 자격증명

agent가 같은 OS 사용자로 실행되므로 홈의 자격증명에 접근할 수 있다고 전제한다. 대응은 권한 범위 축소·복구 가능성·프로덕션 비밀 반입 금지다.

- GitHub는 본인 소유의 필요한 repo만 선택한 fine-grained PAT를 우선 검토한다.
- Administration 권한은 주지 않고 Contents·Pull requests·Issues 권한도 실제 필요한 범위만 준다. 일상 PAT에는 Workflows 쓰기를 기본으로 주지 않는다. workflow 파일 변경은 이 권한이 필요한 별도 경로로 처리한다.
- gh의 실제 인증 경로와 저장 방식을 확인한다. 기존 OAuth·SSH·환경변수 토큰이 함께 접근 가능하면 PAT 하나를 좁힌 것만으로 agent 전체 권한이 줄었다고 말하지 않는다.
- Paseo의 PR 기능과 필요한 API가 작동하는지 검증하고 전환한다. 호환성 문제는 원인을 확인해 처리하며 권한을 무작정 넓히지 않는다. Paseo에서 검사 표시가 줄거나 없으면 GitHub의 해당 SHA 검사 결과를 확인한다. 조회 불가는 통과가 아니다.
- 가능한 main ruleset·push protection·전역 ignore·local guard를 함께 사용한다.
- 공개 템플릿인 `.env.example`은 추적 가능하게 유지한다. 이미 tracked인 비밀은 ignore만으로 해결되지 않는다.
- 개발용 key만 사용하고 가능하면 사용 한도를 둔다. 프로덕션 비밀은 K12에 두지 않는다.
- 모든 프로젝트 key를 Paseo daemon 환경에 넣지 않는다.
- 다른 시스템으로 가는 개인키를 K12에 두지 않는다. Git 접근은 HTTPS를 기본으로 한다.
- 비밀값을 프롬프트·로그·PR에 출력하지 않는다. 대화 기록에 남을 수 있음을 전제로 한다.
- 토큰이 유출됐으면 회수·재발급하고 노출 범위를 확인한다. 기록 삭제만으로 해결됐다고 보지 않는다.

### Workflow 변경과 base 반영

파일럿에서 agent가 새로 작성·수정·삭제한 `.github/workflows/` 변경은 일반 작업 branch에 커밋하지 않는다. 토큰 권한을 추측해 예외를 만들지 않는다. agent는 기준 full SHA와 적용 범위를 적은 patch를 준비하고, 사람은 권한 있는 본인 환경의 **별도 branch·PR**에서 반영한다. 이미 main에 반영된 workflow를 그대로 받는 base 갱신은 아래 절차로 구분한다.

작고 비밀값이 없는 텍스트 patch는 관련 Draft PR 코멘트의 diff 코드 블록에 기준 SHA와 함께 보존할 수 있다. 원문을 내려받아 patch가 온전히 보존됐는지 확인한다. 크기 제한·바이너리·민감한 내용 때문에 적합하지 않으면 접근 가능한 별도 보존 위치나 사람 수신 확인을 사용한다.

이미 main에 반영된 workflow를 그대로 받는 base 갱신은 신규 workflow 작성과 구분한다. 같은 repo에서 K12 fine-grained PAT로 가능한지는 19장의 해당 경로 사용 전 시험으로 확정한다. 시험에서는 merge 결과의 `.github/workflows/`를 대상 main SHA와 대조해 신규 변경을 섞지 않았는지 확인한다. AGENTS의 신규 workflow 커밋 금지 규칙은 유지한다. 허용되면 기존 worktree merge·check·push 흐름을 유지하며 단순히 workflow 변경이 있었다는 이유로 매번 수동 갱신하지 않는다.

base merge는 깨끗한 작업 트리·index에서 시작하고 merge 전 HEAD와 대상 `origin/main`의 full SHA를 확인한다. `.github/workflows/` 충돌이 나면 agent는 해결·commit·push를 멈추고 두 SHA와 충돌 경로를 응답 또는 PR에 먼저 기록한다. 이어서 `git merge --abort`로 merge를 중단하고 HEAD가 merge 전 SHA인지, 작업 트리·index가 다시 깨끗한지 확인한다. 기록은 abort로 되돌려질 작업 파일에만 남기지 않는다. abort가 실패·거부되거나 복원이 확인되지 않으면 강제 reset하지 않고 남은 상태·오류를 보존해 사람에게 넘긴다. 사람은 기록한 SHA·경로와 Git 이력으로 원인을 확인하며 충돌만으로 규칙 위반을 확정하지 않는다.

시험에서 base 반영 push가 Workflows 권한 때문에 거부되면 다음 예외를 적용한다.

1. 아직 local merge를 만들기 전이라면 writer를 멈추고 작업을 commit·push해 local head와 원격 작업 branch head가 같으며 작업 트리가 깨끗한지 확인한다. PR이 없으면 Draft PR을 연다.
2. 사람이 GitHub의 **Update with merge commit**으로 base를 반영한다. rebase 갱신은 사용하지 않는다. 버튼이 없거나 충돌이 있으면 사람이 권한 있는 별도 환경에서 같은 원격 head를 기준으로 merge·충돌 해결·push한다.
3. K12는 fetch한 뒤 작업 branch를 **fast-forward only**로 받는다. 실패하면 멈추고 local-only commit·원격 변경을 대조한다. head가 바뀌었으므로 관련 check·리뷰 범위·승인 기록을 갱신한다.
4. **이미 local merge를 만들고 push가 거부된 경우에는 위 1~3을 그대로 재시도하지 않는다.** 해당 commit과 미보존 작업을 먼저 보존한다. 권한 있는 사람 환경에 그 commit을 그대로 전달해 원격이 그 commit까지 fast-forward 가능한지 확인한 뒤 push하는 복구를 우선한다. 원격도 움직였으면 양쪽 변경을 보존해 통합하며 강제 reset·force push로 맞추지 않는다.

원격 갱신 전에 맞춰 둔 head에서만 단순 fast-forward 복귀를 기대한다. 권한 거부가 아닌 검사 실패·branch 보호·인증 오류를 이 예외로 우회하지 않는다.

patch의 원격 보존 또는 사람 수신을 확인하기 전에는 완료·백업됐다고 적지 않고 작업 공간을 정리하지 않는다. handoff에는 보존 위치와 다음 담당을 남긴다. workflow 원본이 일반 코드의 stage에 섞이지 않게 확인하며 실수로 커밋했으면 먼저 commit·diff를 보존한다.

이 경로는 Workflows 쓰기를 일상 PAT에서 제외하기 위한 운영 선택이다. 수동 개입이 반복되면 사람이 비용과 권한 범위를 비교해 정책 변경을 결정할 수 있으나 agent가 스스로 더 넓은 token을 추가하지 않는다. workflow 파일 밖의 코드도 CI에서 실행될 수 있으므로 Workflows 권한 제한을 CI 전체의 보안 경계로 보지 않는다.

별도 OS 사용자·비밀 관리자·세밀한 egress 통제·매일 전체 백업은 현재 기본 구성에 추가하지 않는다. 필요해지는 위험이나 대체 불가능한 데이터가 생기면 재검토한다.

## 16. 장애 복구

**중복 실행 방지 → 상태 보존 → 실제 결과 확인 → 최소 단위 재개 → 정리** 순서로 한다.

Git은 소스의 정본이고 task·PR·검증 기록은 작업 상태의 정본이다. Paseo는 이 작업을 연결하는 인터페이스다. Git 밖의 runtime 상태와 데이터는 해당 시스템에서 확인하고 별도 보존한다.

| 상황 | 대응 |
|---|---|
| Direct 연결 끊김 | 재접속·허용된 Relay 경로 확인. 같은 요청을 다시 제출하기 전에 기존 agent 상태 확인 |
| agent crash | 이전 실행 종료 확인 → diff·task·PR 대조 → 보존할 변경 분류 → 필요한 check → 재개 |
| Paseo 재시작·서버 reboot | daemon·agent·compose·DB 상태를 각각 확인. 미완료 명령을 일괄 재실행하지 않음 |
| migration·push·PR·merge·외부 API 중단 | 실제 반영 여부부터 확인하고 미완료 부분만 재시도. 결과를 판별할 수 없으면 해당 쓰기를 멈추고 기존 요청·작업 식별자를 보존 |
| worktree만 남음 | Local에서 상태 확인·필요한 commit/push·runtime 보존 후 정리 |
| branch만 남음 | PR·main·추가 commit을 대조해 재개 또는 폐기 판단 |
| 디렉터리는 없고 Git 등록만 남음 | 실제 사용 중인 worktree·mount가 아닌지 확인 후 stale 메타데이터 정리 |
| Git lock 오류 | 실제 Git 프로세스와 작업 진행 여부 확인 후 stale lock인지 판단 |
| archive·teardown 실패 | 보관 표시와 실제 정리 완료를 구분하고 남은 파일·runtime·오류를 확인. 자동 재시도하지 않으며 권한 오류는 경로·mount·UID 매핑 등 원인에 맞춰 처리 |
| setup 실패 | 8장의 원인 확인과 금지 우회 규칙 적용 |
| 인증 만료·사용량 제한 | 재인증 또는 provider 교대. 현재 변경·검증 상태를 먼저 복원 |

hard reset·강제 worktree 삭제 전에 잃을 수 있는 데이터를 실제로 보존한다. stash나 backup branch가 있다고 해서 untracked·ignored 파일까지 보존됐다고 가정하지 않는다.

## 17. 작업 크기별 일상 흐름

| 크기 | 기본 흐름 |
|---|---|
| S | worktree → 한 문단 목표·Acceptance → 구현·check → 필요하면 교차 리뷰 → PR → 사람 승인 |
| M, 요구 명확 | worktree → Build가 짧은 task brief → 구현·검증 → 트리거 리뷰 → Ready·승인 |
| M, 요구 모호 | Plan이 범위·대안 초안 → 필요한 사람 판단 → task 저장 → Build 구현 → 동일한 검증·승인 |
| L | 필요한 설계·slice 계획을 먼저 합의 → 독립적으로 합칠 M 크기 PR로 진행. 설계 자체를 별도로 채택할 가치가 있으면 ADR PR을 먼저 merge |
| R | spike에서 조사 → 남길 결과만 research 문서로 승격 → 실험 코드는 최종 PR에서 제외하거나 폐기 |

S는 보통 당일, M은 보통 1~3일, R은 짧은 timebox를 목표로 한다. 날짜를 지키려고 검증을 생략하지 않는다. L을 장기 branch 하나로 끌고 가지 않는다.

먼저 S 하나와 교대를 포함한 M 하나를 직렬로 완료하고, 다음에 독립적인 두 결과를 병렬로 시험한다. 동시 writer 상한은 2명이며 항상 둘을 가동할 의무는 없다. 구현·리뷰·사람 승인 대기를 합쳐 현재 진행 중인 결과는 최대 2개로 시작한다. 사람이 명시적으로 보류하고 실행을 멈춘 작업과 merge 후 정리 대기는 활성 결과와 구분한다.

두 결과가 사람의 판단을 기다리면 새 결과를 추가하지 않는다. 병렬은 “Codex가 A 구현, Claude가 B brief 작성”처럼 서로 다른 worktree에서 진행하며 Plan의 파일 저장도 writer 활동이다. writer 수보다 채택된 결과와 사람의 재설명·조율 비용을 본다. 세션 시작·교대 조작은 자동화가 확인되지 않은 한 사람의 비용으로 센다.

마감 시 진행 중인 작업만 task·commit·push 상태를 정리한다. worktree를 매일 지우지 않는다.

주간 점검은 짧게 한다.

- 오래 멈춘 작업을 재개·계속 보류·종료 중 하나로 판단한다.
- `[gone]` branch는 5장의 조건을 확인해 정리한다.
- 디스크가 필요하면 안전한 범위의 이미지·cache를 정리한다.
- agent와 관련 실행이 없을 때 Paseo·provider 업데이트를 검토한다. Codex 규칙 변경도 7장의 점검 시간과 재시작 절차를 따른다.
- 이어받기 지연·변경 혼입·미검증 merge가 있었는지 보고 실패한 규칙만 수정한다.

## 18. 자동화와 오케스트레이션

repo의 `check`를 로컬과 CI에서 일관되게 사용한다. 환경상 실행 범위가 다르면 차이를 문서화한다. CI는 파일럿의 첫 의미 있는 PR부터 필요한 검사로 연결한다.

문서의 기계적 검사는 자동화하고 문서의 의미가 구현과 맞는지 판단하는 감사는 필요할 때 수행한다.

Paseo tools는 파일럿 동안 끈다. 이후 다음 용도에서 사람이 요청했을 때 사용한다.

- 읽기 전용 병렬 조사.
- 어려운 문제에 대한 독립 분석 두 개.
- 부재 중 진행하도록 범위를 정한 구현 후 리뷰.

AGENTS에는 “사람의 요청 없이 추가 agent를 생성하지 않는다”를 둔다. shell·CLI를 통한 생성도 포함한다. 위임을 요청받아도 작업 범위·writer 소유권·종료 조건을 정하며 재귀적으로 확장하지 않는다.

도구 활성화 자체가 무제한 위임이나 merge 승인을 뜻하지 않는다.

## 19. 현재 상태와 적용 순서

### 사용자가 전달한 최신 실행 보고 기준 완료

다음은 완료 보고를 받은 항목이다. 이 검토본 작성자가 K12에 접속해 재검증한 결과는 아니다.

- Rootless Docker 실제 동작.
- rootful Docker 비활성화.
- docker/lxd 그룹 제거.
- Public Paseo Direct 정상 연결.
- 새 도메인에서 잘못된 password 거부.
- 올바른 password의 Direct 연결.

**비밀번호를 아예 보내지 않은 요청의 거부**는 위 보고 문구만으로 확인되지 않는다. 기존 실행 기록에 있으면 완료로 표시하고 없다면 그 항목만 확인한다. 전체 Direct 검사를 다시 시작하지 않는다.

설치 버전은 전달된 Paseo 0.10.3을 출발점으로 삼되 실제 Paseo·Codex·Claude 버전을 함께 확인한다. 권한 파일의 저장 위치와 모드 의미는 provider 버전도 영향을 준다.

### P0 — 첫 작업에 필요한 경로

1. 설치 버전과 사용할 writer·정적 review 경로를 확인한다. AGENTS·권한 설정의 실제 로딩, source 쓰기 범위, commit·작업 branch push·PR 생성, Auto-review의 관여 여부를 Paseo 세션에서 확인한다. reviewer의 PR 코멘트 작성 가능 여부와 불가할 때의 사람 전달·writer 대리 게시 경로도 확인한다. 사용하지 않는 프로필까지 모두 확정할 필요는 없다.
2. Kerbe의 실제 setup·check 명령과 작업 공간·runtime 소유 경계를 확인하고 AGENTS·CLAUDE의 명령·문서 지도를 채운다. DB·컨테이너를 쓰는 작업은 해당 자원의 분리를 먼저 확인한다.
3. 적용 가능한 GitHub main 보호·필수 검사와 K12 local guard·기존 hook 연결을 확인한다. 같은 계정의 PR에 충족할 수 없는 별도 승인 리뷰 수를 요구하지 않는다. 관리자 우회 범위도 기록한다. 사람이 Claude merge deny·Codex merge forbidden을 설치하고 **7장의 무해한 시험 대상으로 실제 사용할 Paseo 세션의 차단을 확인한다.** gh가 실행돼 낸 PR 없음·인증 오류는 차단 실패다. 이 확인은 AI merge 활성화와 별개이며 agent가 설정을 직접 바꾸지 않는다.
4. **사람 직접 merge·수동 정리로 시작하고 AGENTS 상단에 AI merge 비활성을 명시한다. 자동 archive도 끈다.** 한 worktree에는 활성 workspace를 하나만 둔다. 사용 중인 자격증명의 실제 범위·보관 방식과 비밀정보 노출 경로는 확인하되 PAT 전환 자체를 모든 개발의 전제로 삼지 않는다.

확인되지 않은 UI 기능을 AGENTS에 기술적 보장으로 적지 않는다. 미확인 사항이 있으면 그 기능·작업 경로를 제한하며 안전한 대체 경로까지 일괄 중단하지 않는다.

### P1 — Kerbe의 짧은 파일럿

1. 필요한 setup·on-demand script·check/CI를 준비한다. base에서 읽는 setup 수정은 chore PR로 먼저 반영한다. 첫 의미 있는 PR부터 필요한 CI를 연결하고 workflow 변경은 15장의 사람 경로를 따른다. 아직 쓰지 않을 정리 자동화까지 모두 구현할 필요는 없다.
2. S 하나를 한 writer로 요청부터 check·필요 리뷰·사람 merge·실제 반영 확인까지 완료한다.
3. M 하나에서 의도적으로 세션·provider를 교대한다. 이전 실행 종료와 기록·Git·runtime 대조만으로 Next를 수행하는지 확인한다. 사람이 작업 맥락을 다시 설명해야 했다면 빠진 정보만 보완하고 그 경로를 한 번 재시험한다.
4. 그 뒤 독립적인 두 결과를 병렬로 완료한다. 승인 대기·요구 질문·base 재검증·직접 개입 부담을 직렬 사례와 비교해 기본 writer 수를 선택한다. 몇 사례로 통계적 우월성을 주장하지 않는다.
5. 모바일에서 결과·Acceptance 근거·미확인 항목·후보를 실제로 판단할 수 있는지 확인한다. 버튼이 작동했다는 사실만으로 통과시키지 않는다.
6. private `home-dev-ops`에 운영·복구 문서를 두고, 첫 파괴적 정리 전에 폐기 가능한 자원으로 소유 범위·보존·실패·잔여 자원 확인을 시험한다. 정리가 끝나지 않았어도 개발 결과의 반영 완료와 구분해 기록한다.

별도 측정 시스템은 만들지 않는다. 기존 PR·commit·검사·Paseo 로그를 사용하고 파일럿 PR 종료 시 대략적인 사람의 직접 개입·재설명·불필요한 왕복만 짧게 남긴다. 이 기록은 초기 비교용이며 상시 시간 추적 의무가 아니다.

**파일럿 종료:** S·M 완주, 교대 복원, 두 결과의 병렬 비교로 일상 경로를 선택할 수 있으면 끝낸다. 선택 기능을 모두 활성화하거나 희귀 장애를 전부 재현할 필요는 없다. 데이터 손실·승인 없는 main 반영·다른 작업 자원 침범은 해당 기능을 멈추고 수정한다. task 형식·프로필 선택의 불편은 그 부분만 조정한다.

### 선택 기능 — 필요해질 때 활성화

- **AI merge:** 사람이 기존 deny·forbidden을 ask·prompt로 변경한 뒤 실제 사용할 provider·프로필에서 7장의 승인·head 변경 거부 시험을 수행한다. 통과한 설정·기록과 AGENTS의 활성 상태를 함께 반영한다. 시험 실패와 모든 비활성화 때 7장의 절차로 차단을 복구하고 사람 직접 merge를 유지한다. agent가 상태 줄을 수정하거나 스스로 활성화하지 않는다.
- **자동 archive:** 5장의 보존 조건·적용 범위·teardown 실패 및 재시도 결과를 확인하고 실제 정리 조작을 줄일 가치가 있을 때만 켠다. 예외 범위를 통제하지 못하면 수동 정리를 유지한다.
- **fine-grained PAT 전환:** 필요한 Paseo·GitHub 기능과 인증 경로를 확인해 전환한다. Workflows 쓰기가 없는 토큰으로 base의 workflow 변경을 받을 경로는 사용 전에 시험 repo에서 추가·수정·삭제 각각을 확인한다. **삭제는 별도 시험한다.** 신규 작성의 거부와 단순 수신을 구분하고 token 종류·권한·commit·응답만 기록한다. 거부되면 15장의 사람 경로를 사용하며 token 값은 남기지 않는다.
- **추가 프로필·Docker·미리보기:** 사용할 프로필, 이미지의 source 쓰기·UID 매핑, 무거운 스택의 실제 자원 제한, SSH forwarding을 필요할 때 확인한다.
- **Paseo tools·writer 확대:** 파일럿 이후 요청한 위임 범위에서만 켠다. writer를 3명으로 늘리는 판단은 자원뿐 아니라 진행 중 결과 수·사람의 리뷰 처리량도 본다. 역할·프로필·문서량은 실제 불편에 맞춰 조정한다.

## 20. 공식 근거와 남은 확인 범위

아래 링크는 기능 확인의 출발점이다. 최신 웹 문서의 설명을 설치된 K12 버전의 실측 결과와 동일시하지 않는다.

1. Paseo worktrees — base의 설정·setup/teardown·services  
   https://paseo.sh/docs/worktrees
2. Paseo workspaces — Local/Worktree와 archive 수명  
   https://paseo.sh/docs/workspaces
3. Paseo orchestration  
   https://paseo.sh/docs/orchestration
4. Paseo changelog — 버전별 권한·UI·자동화 변경  
   https://paseo.sh/changelog
5. Git worktree — detached worktree와 공유 저장소 구조  
   https://git-scm.com/docs/git-worktree
6. Git hooks — pre-push 입력과 동작  
   https://git-scm.com/docs/githooks
7. Git push — push 옵션과 hook 우회  
   https://git-scm.com/docs/git-push
8. Git ref 표시 — upstream gone의 의미  
   https://git-scm.com/docs/git-for-each-ref
9. GitHub CLI PR merge — head 일치 조건과 merge 옵션  
   https://cli.github.com/manual/gh_pr_merge
10. GitHub protected branches — PR·검사·base 갱신 보호  
    https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
11. GitHub merge methods — squash와 merge 결과 commit  
    https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/about-merge-methods-on-github
12. Claude permissions / modes / SDK 권한  
    https://code.claude.com/docs/en/permissions  
    https://code.claude.com/docs/en/permission-modes  
    https://code.claude.com/docs/en/agent-sdk/permissions
13. Codex approvals와 auto-review  
    https://learn.chatgpt.com/docs/agent-approvals-security  
    https://learn.chatgpt.com/docs/sandboxing/auto-review
14. Docker rootless와 UID/GID mapping  
    https://docs.docker.com/engine/security/rootless/  
    https://docs.docker.com/engine/security/rootless/uid-gid-mapping/
15. GitHub personal access tokens  
    https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens

추가 확인 근거:

- Codex command rules: https://learn.chatgpt.com/docs/agent-configuration/rules
- Codex 승인 설정값: https://learn.chatgpt.com/docs/config-file/config-reference
- 네트워크 허용 대상에도 command prompt를 적용하는 예: https://learn.chatgpt.com/docs/cyber-safety/recommended-configuration
- Git hooksPath: https://git-scm.com/docs/git-config#Documentation/git-config.txt-corehooksPath
- Git LFS pre-push: https://github.com/git-lfs/git-lfs/blob/main/docs/man/git-lfs-pre-push.adoc
- Docker external volume의 down 동작: https://docs.docker.com/reference/cli/docker/compose/down/
- Workflow 파일 관련 token 권한: https://docs.github.com/en/rest/repos/contents#create-or-update-file-contents
- 고정 객체의 내용 조회: https://git-scm.com/docs/git-show
- Git merge 중단과 작업 트리 복원 조건: https://git-scm.com/docs/git-merge
- Claude SDK 권한과 설정 source: https://code.claude.com/docs/en/agent-sdk/permissions
- Claude SDK 설정 로딩: https://code.claude.com/docs/en/agent-sdk/modifying-system-prompts
- Paseo 버전별 로컬 설정 적용 기록: https://paseo.sh/changelog
- OAuth workflow scope의 같은 repo·동일 경로·동일 내용 예외: https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps
- PR 작성자의 자기 승인 제한: https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/approving-a-pull-request-with-required-reviews
- Paseo v0.10.3 archive 소스: https://github.com/getpaseo/paseo/blob/v0.10.3/packages/server/src/server/workspace-archive-service.ts
- GitHub Update branch의 조건과 merge/rebase 구분: https://docs.github.com/en/pull-requests/how-tos/create-pull-requests/keeping-your-pull-request-in-sync-with-the-base-branch

GitHub의 OAuth scope 문서는 같은 저장소의 다른 branch에 경로와 내용이 동일한 workflow가 있으면 workflow scope 없이 반영할 수 있는 예외를 설명한다. 이것만으로 K12의 fine-grained PAT에서 같은 동작을 보장하거나 반대로 반드시 거부된다고 결론내리지 않는다. 15장의 base 반영 경로는 실제 토큰으로 시험해 확정한다.

먼저 **사용할 writer·review 권한과 merge 차단, 실제 repo 명령, 작업 공간·runtime 경계**를 확인한다. **AI merge 승인·head 변경 거부, 자동 archive, workflow base 반영 push**는 해당 기능을 쓰기 전 별도로 확인한다. 선택 기능의 미확인이 기본 개발 전체를 막지는 않으며 정책 문구를 실측 전 기술적 강제 보장으로 표현하지 않는다.
