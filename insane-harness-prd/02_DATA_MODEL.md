# insane-harness — 데이터 모델

> 이 플러그인이 다루는 상태 파일과 스키마 정의.
> 모든 상태는 워크스페이스 루트의 `.insane-harness/` 디렉토리에 존재한다 (플러그인 내부는 무상태).

---

## 전체 구조

```
[WorkspaceConfig] --1:1--> [HarnessLedger] --1:N--> [LedgerEntry]
       |                                                  ▲
       └--(주기 판정 입력)                                  │ (승인 시 생성)
[ScanReport] --(진단 산출물)--> [Proposal] ---------------┘
       ▲
[HarnessCatalog] (플러그인 동봉, 읽기 전용 — 시그널→처방 매핑)
```

```
<workspace>/.insane-harness/
├── config.json        # WorkspaceConfig — 모드·주기 설정
├── ledger.json        # HarnessLedger — 적용 장부 (자가성장 모드만)
├── scan-latest.json   # ScanReport — 마지막 진단 결과 (다음 diff 기준선)
└── backups/           # apply 직전 원본 백업 (settings.json, CLAUDE.md)
```

> ⚠️ 가정: `.insane-harness/`는 gitignore를 조작하지 않고 생성만 합니다. 커밋 여부는 사용자 재량 — 아니라면 알려주세요. (A6)

---

## 엔티티 상세

### WorkspaceConfig (`config.json`)
워크스페이스별 동작 방식. 첫 셋업 카드의 답이 그대로 저장된다.

| 필드 | 설명 | 예시 | 필수 |
|------|------|------|------|
| schema_version | 스키마 버전 (마이그레이션 대비) | 1 | O |
| mode | 성장 모드 | `"growth"` \| `"snapshot"` | O |
| cadence.type | 주기 종류 | `"manual"` \| `"days"` \| `"sessions"` | O |
| cadence.value | 주기 값 (manual이면 null) | 7 | X |
| cadence.action | 주기 도래 시 동작 | `"notify"`(기본) \| `"auto_diagnose"` | O |
| deep_read | 심층 분석 설정 | `{recent: 10, outliers: 3}` | O |
| created_at / updated_at | 생성·수정 시각 (ISO) | 2026-07-07T12:00:00+09:00 | O |

### HarnessLedger (`ledger.json`)
자가성장의 핵심 — "무엇을 왜 깔았고 아직 유효한가"의 장부.

| 필드 | 설명 | 예시 | 필수 |
|------|------|------|------|
| schema_version | 스키마 버전 | 1 | O |
| last_run_at | 마지막 진단 완료 시각 | 2026-07-07T… | O |
| last_run_session_count | 그 시점 누적 세션 수 (세션 주기 판정용) | 142 | O |
| entries[] | LedgerEntry 배열 | 아래 참조 | O |

### LedgerEntry (entries[] 원소)

| 필드 | 설명 | 예시 | 필수 |
|------|------|------|------|
| id | 고유 식별자 | `hook-precommit-verify-001` | O |
| type | 하네스 종류 | `"plugin_install"` \| `"hook"` \| `"claude_md_rule"` \| `"skill_delegation"` | O |
| name | 사람이 읽는 이름 | "커밋 전 검증 게이트 훅" | O |
| detail | 적용 내용 요약 + 대상 경로 | `settings.json PreToolUse[2]` | O |
| source_signals[] | 제안 근거가 된 scan 시그널 id | `["repeat_manual_verify", "commit_after_error"]` | O |
| applied_at | 적용 시각 | 2026-07-07T… | O |
| status | 상태 | `"active"` \| `"removed"` \| `"stale_candidate"` | O |
| last_verified_at | 마지막 유효성 재검증 시각 | 2026-07-28T… | X |
| removed_reason | 제거 시 사유 (승인 기록 포함) | "최근 40세션 미사용, 사용자 승인 제거" | X |

### ScanReport (`scan-latest.json`)
scan.py의 출력. 세션 원문은 절대 포함하지 않는다 — 통계와 경로만.

| 필드 그룹 | 설명 | 예시 필드 |
|------|------|------|
| meta | 스캔 메타 | workspace_path, scanned_at, session_count, date_range, scan_duration_ms |
| session_stats | 전 세션 기계 통계 | tool_histogram, top_bash_commands, error_count, interrupt_count, top_touched_files, skill_usage, avg_session_turns |
| deep_read_targets[] | LLM 심층 읽기 후보 (경로만) | 최근 10 + 에러 최다 3 세션의 jsonl 경로·선정 사유 |
| inventory | 워크스페이스 구성 | skills[], commands[], agents[], hooks[](settings.json+local), claude_md{exists, sections[], harness_block_present}, memory_index_exists |
| catalog | 플러그인 지형 | installed_plugins[], available_plugins[]{name, marketplace, description} |
| diff | 이전 scan-latest 대비 변화 (자가성장 모드) | new_sessions, new_top_commands, inventory_changes[] |

> ⚠️ 가정: 세션 로그는 `~/.claude/projects/<경로 인코딩>/*.jsonl`이고 라인 단위 JSON으로 파싱 가능. 포맷이 다른 라인은 스킵(방어 파싱) — 아니라면 알려주세요. (A1)

### HarnessCatalog (`references/harness-catalog.md`, 플러그인 동봉)
시그널→처방 매핑표. LLM이 제안 단계에서 참조하는 읽기 전용 지식. 초기 10종 예시:

| 시그널 (scan이 산출) | 임계 예시 | 처방 종류 | 처방 예시 |
|------|------|------|------|
| 동일 bash 절차 반복 | 같은 명령 시퀀스 ≥5회 | claude_md_rule | 체크리스트 구획 주입 |
| 검증 없는 커밋 후 수정 커밋 | fix-after-commit ≥3회 | hook | 커밋 전 검증 게이트 |
| 에러/중단율 높음 | interrupt ≥15% | plugin_install | fablize(완주·검증 하네스) 안내 |
| PRD·기획 대화 빈발 | 기획 키워드 세션 ≥20% | plugin_install | show-me-the-prd 안내 |
| 리서치 세션 빈발 | 검색 도구 비중 ≥30% | plugin_install | insane-research 안내 |
| 장문 문서 반복 생성 | Write 대형 md ≥10회 | skill_delegation | 문서 템플릿 스킬 (skillers-suda) |
| CLAUDE.md 부재/빈약 | 섹션 <2 | claude_md_rule | 워크스페이스 프로필 구획 생성 |
| 스킬 미사용 방치 | 정의됐으나 0회 호출 | 제거 제안 | 스킬 정리 |
| 동일 실수 교정 반복 | 같은 지적 ≥3회 | hook | hookify 연계 or 규칙 주입 |
| 특정 사이트 접근 실패 반복 | fetch 차단 ≥3회 | plugin_install | insane-search 안내 |

---

## 왜 이 구조인가

- **비교 가능성이 자가성장의 전제**: 진단을 LLM 감상이 아니라 scan.py의 결정론 통계로 고정해야 "지난번 대비 무엇이 변했나"(diff)가 성립한다. ScanReport를 파일로 남기는 이유.
- **장부와 설정의 분리**: config는 사용자가 정한 것, ledger는 시스템이 한 일. 스냅샷 모드에서 ledger만 없애면 되도록 분리했다.
- **확장성**: LedgerEntry.type에 새 하네스 종류가 추가돼도(Phase 2 카탈로그 확장) 스키마는 유지된다. schema_version으로 마이그레이션 대비. (A7)
- **단순성**: DB 없음, 전부 JSON 파일. 워크스페이스 하나 = 디렉토리 하나.

---

## [NEEDS CLARIFICATION]

- [ ] A3: 주기훅 배포 방식 (플러그인 hooks.json 전역 1개 vs 워크스페이스 settings.json 등록) — Turn 4 확인
- [ ] catalog.available_plugins의 스캔 대상: 마켓플레이스 클론의 marketplace.json만으로 충분한가 (플러그인별 상세 description 확보 경로)
