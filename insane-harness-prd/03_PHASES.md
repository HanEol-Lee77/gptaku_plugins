# insane-harness — Phase 분리 계획

> 사용자 결정: **v0.1에 기능 블록 6개 전부** (풀 MVP). 대신 Phase 1 내부를 검증 가능한 3단계로 나눠 순서대로 완성한다.

---

## Phase 1: v0.1 풀 MVP

### 목표
단일 워크스페이스에서 "셋업 → 진단 → 제안 → 승인 → 적용 → 장부 → 주기훅"의 자가성장 루프 전체가 실동작.

### 내부 순서 (1a → 1b → 1c)

**1a. 진단 코어** — 가장 위험한 부분 먼저
- [ ] `bin/scan.py`: 세션 jsonl 통계 + 인벤토리 + 카탈로그 수집 → ScanReport JSON
- [ ] 성격 다른 워크스페이스 3곳(gptaku_plugins/집필/실험)에서 산출 검증
- [ ] `references/harness-catalog.md` 초기 10종 시그널 작성

**1b. 제안·적용 루프**
- [ ] 메인 커맨드 `commands/insane-harness.md`: 셋업 카드 → scan 호출 → 프로필+제안 → AskUserQuestion 승인 → apply 호출
- [ ] `bin/apply.py`: 훅 머지(백업→적용→검증→롤백) / CLAUDE.md 마커 구획 / 플러그인 설치 안내 / skillers-suda 위임 / ledger 기록
- [ ] dry-run 모드 (`--dry-run`: 변경 예정 diff만 출력)
- [ ] `/insane-harness:status`, `/insane-harness:config` 커맨드

**1c. 자가성장 + 주기훅**
- [ ] ledger diff 기반 증분 제안 (신규 + 유효성 재검증 + 스테일 제거 제안)
- [ ] `bin/cadence_check.py` + 플러그인 hooks.json SessionStart 훅 (config 없으면 침묵)
- [ ] 재실행 시 중복 제안 0건 검증

### 데이터
- 전체: WorkspaceConfig, ScanReport, HarnessLedger, HarnessCatalog

### "진짜 제품" 체크리스트 (플러그인 버전)
- [ ] 실제 세션 jsonl 파싱 (목업 데이터 X)
- [ ] AskUserQuestion이 실제 UI로 렌더링됨 (frontmatter allowed-tools 버그 회피 확인)
- [ ] 승인 없이 파일 변경 0건 (git diff로 검증)
- [ ] gptaku_plugins 워크스페이스에서 E2E 1회 완주
- [ ] insane 시리즈 컨벤션: MIT+DISCLAIMER.md, setup.sh, 5개국어 README, 서브모듈 레포 + GitHub 릴리즈

### Phase 1 시작 프롬프트
```
이 PRD를 읽고 insane-harness Phase 1을 구현해주세요.
@insane-harness-prd/01_PRD.md
@insane-harness-prd/02_DATA_MODEL.md
@insane-harness-prd/04_PROJECT_SPEC.md

순서: 1a(scan.py+카탈로그) → 1b(커맨드+apply.py) → 1c(증분+주기훅)
반드시 지켜야 할 것:
- 04_PROJECT_SPEC.md의 "절대 하지 마" 목록 준수
- 실제 세션 로그로 검증 (목업 X)
- 각 단계 완료 시 성공 기준 항목으로 검증 후 다음 단계
```

---

## Phase 2: v0.2 성장 품질

### 전제 조건
- Phase 1이 본인 워크스페이스 3곳 이상에서 안정 동작

### 목표
제안의 정확도와 성장 루프의 신뢰도를 올린다.

### 기능
- [ ] 하네스 카탈로그 확장 (도메인 프리셋: 플러그인개발/집필/리서치/실험/웹개발)
- [ ] 스테일 감지 고도화 (훅 실행 로그·스킬 호출 흔적 기반 사용률 측정)
- [ ] status 리포트 강화 (하네스 건강도 표시)
- [ ] 진단 리포트 md 파일 출력 옵션 (`.insane-harness/reports/`)
- [ ] cadence `auto_diagnose` 모드 UX 다듬기

---

## Phase 3: v0.3+ 측정과 확장

### 전제 조건
- 장부 데이터가 여러 워크스페이스에서 수 주 이상 누적

### 목표
하네스가 실제로 효과 있었는지 측정하고, 추천 범위를 넓힌다.

### 기능
- [ ] 하네스 효과 측정: 적용 전후 세션 지표 비교 (에러율·중단율·반복 절차 감소)
- [ ] 크로스-워크스페이스 인사이트 (여러 워크스페이스 공통 패턴 → 글로벌 하네스 제안)
- [ ] 외부 레지스트리 추천 (웹 검색, 검증 경고 라벨 부착)
- [ ] insane-loop/goaljaby 연동 (하네스 세팅 → 골 실행 파이프라인)

### 주의사항
- 효과 측정은 인과가 아닌 상관 — 리포트에 명시
- 외부 추천은 미검증 플러그인 리스크 → 기본 꺼짐

---

## Phase 로드맵 요약

| Phase | 핵심 | 상태 |
|-------|------|------|
| Phase 1 (v0.1) | 자가성장 루프 전체 (6블록) — 1a 진단 → 1b 제안·적용 → 1c 성장·주기 | 시작 전 |
| Phase 2 (v0.2) | 카탈로그 확장·스테일 감지·리포트 품질 | Phase 1 완료 후 |
| Phase 3 (v0.3+) | 효과 측정·크로스 워크스페이스·외부 추천·골 연동 | Phase 2 완료 후 |
