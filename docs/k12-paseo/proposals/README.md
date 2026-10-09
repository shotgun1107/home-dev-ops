# CI 적용 제안 — 미적용

v2.4 15/18장에 따라 workflow는 일반 agent 작업 branch의 .github/workflows에 commit하지 않았다.
[patch](home-dev-ops-ci.patch)는 현재 후보의 두 unittest 파일을 검사하는 작은 제안이다.
기준 Git HEAD는 `2873a57a804c96225b774bc1c9f86dae87628db3`이며 이후 변경은 이 PR에서 확인한다.

- Git patch 형식 검사와 YAML 파싱만 완료했다. **GitHub Actions 실행은 미실행**이다.
- Python 3.12 / GitHub-hosted Ubuntu / 5분 상한 / contents:read / checkout credential 보존 끔.
- unittest 두 파일의 존재를 검사해 테스트 없는 branch에서 0개 검사로 성공하는 것을 막는다.
- K12 자체 호스트·운영 서비스·비밀정보를 사용하지 않으며 배포/merge/외부 게시 작업이 없다.
- actions/checkout v7과 actions/setup-python v6의 full SHA는 2026-10-09 GitHub refs GET으로 확인했다.
  [checkout](https://github.com/actions/checkout), [setup-python](https://github.com/actions/setup-python)의 공식 사용법을 대조했다.

사람은 이 PR 후보의 코드가 있는 기준에서 별도 CI branch/PR을 만들고 patch를 검토·반영해야 한다.
CI PR을 이 task branch에 통합하는 경우도 사람이 수행한다. 후보가 바뀌면 tests/리뷰와 CI 결과를
새 SHA에 연결한 뒤 운영 개정안을 검토한다. agent가 workflow를 활성화하거나 merge하지 않는다.
패치 전문은 같은 Draft PR 코멘트에도 보존하고 재조회한다. 실제 CI 비용/사용 가능 범위는 사람 검토 대상이다.
