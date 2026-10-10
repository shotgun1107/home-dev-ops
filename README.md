# K12 운영 기록

- [P0/P1 검증 현황](docs/k12-paseo/STATUS.md)
- [실측 근거와 결함 재현](docs/k12-paseo/EVIDENCE.md)
- [권한·Git·Runtime 복구](docs/k12-paseo/RECOVERY.md)
- [v2.4.1 운영 개정안 — Draft](docs/k12-paseo/REVISION.md)

운영 v2.4 원문은 `docs/k12-paseo/source/`에 보존한다. 개정안과 실측 결과는
Draft PR에서 검토하며, AI merge와 Ready 전환은 이 미션의 허용 범위가 아니다.

로컬 회귀검사: `python3 -B -m unittest discover -s tests -v`.
읽기 전용 연결 진단: `python3 -B scripts/paseo_preflight.py`.
`scripts/k12-pre-push`는 검토용 설치 후보이며 이 저장소의 활성 hook이 아니다.
