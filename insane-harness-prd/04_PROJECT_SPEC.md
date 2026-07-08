# insane-harness — 프로젝트 스펙 (AI 행동 규칙)

> AI가 이 플러그인을 구현할 때 지켜야 할 규칙. 코드 작업 시 항상 함께 공유할 것.

---

## 기술 스택

| 영역 | 선택 | 이유 |
|------|------|------|
| 커맨드/스킬 | Markdown 지시서 (commands/, skills/) | Claude Code 플러그인 표준. 커맨드 파일이 실행 지시서 |
| 스크립트 | Python 3 표준 라이브러리만 | 의존성 0 — 어떤 머신에서도 설치 없이 동작 (A9). insane 시리즈 중 가장 보수적 선택 |
| 훅 | 플러그인 hooks.json (SessionStart) + `bin/cadence_check.py` | 워크스페이스 settings.json 무조작 (A3) |
| 상태 저장 | JSON 파일 (`.insane-harness/`) | DB 불필요, 워크스페이스 자체가 격리 단위 |
| 배포 | 서브모듈 레포 (github.com/fivetaku/insane-harness) + gptaku-plugins 마켓플레이스 | insane 시리즈 컨벤션 |

---

## 프로젝트 구조

```
insane-harness/
├── .claude-plugin/plugin.json     # 버전 정보 (릴리즈 태그와 1:1)
├── commands/
│   ├── insane-harness.md          # 메인 — 셋업→진단→제안→승인→적용 지시서
│   ├── status.md                  # 장부·하네스 현황 조회
│   └── config.md                  # 모드·주기 변경
├── skills/insane-harness/
│   ├── SKILL.md                   # 트리거·개요 (참고 문서)
│   └── references/
│       └── harness-catalog.md     # 시그널→처방 매핑표 (초기 10종)
├── hooks/hooks.json               # SessionStart → cadence_check.py
├── bin/                           # ⚠️ scripts/ 금지 — 루트 .gitignore 함정
│   ├── scan.py                    # 진단: 세션 통계+인벤토리+카탈로그 → ScanReport
│   ├── apply.py                   # 적용: 백업→머지/주입→검증→롤백, ledger 갱신
│   └── cadence_check.py           # 주기 판정 (config 없으면 무출력 종료)
├── setup/setup.sh                 # 첫-실행 셋업 (update-hook 컨벤션)
├── LICENSE                        # MIT
├── DISCLAIMER.md                  # 무보증·무제휴·사용자책임
└── README.md (+ 5개국어)
```

---

## 절대 하지 마 (DO NOT)

- [ ] **커맨드 frontmatter `allowed-tools`에 AskUserQuestion 넣지 마** — auto-approve 버그로 UI가 렌더링되지 않고 빈 답변 통과됨 (tools/validate_commands.py CI 게이트 대상)
- [ ] **`scripts/` 디렉토리 만들지 마** — 부모 레포 루트 .gitignore가 `scripts/`를 막음. 반드시 `bin/` 사용
- [ ] **승인 없이 적용하지 마** — settings.json·CLAUDE.md·스킬 생성 모두 AskUserQuestion 승인 후에만. 제거·수정 제안도 동일
- [ ] **CLAUDE.md의 마커 구획(`<!-- insane-harness:begin/end -->`) 밖을 수정하지 마** — 사용자 작성 영역 불가침
- [ ] **백업 없이 덮어쓰지 마** — apply.py는 변경 전 원본을 `.insane-harness/backups/<timestamp>/`에 보존, 실패 시 롤백
- [ ] **세션 로그 원문을 컨텍스트에 통째로 붓지 마** — scan.py 통계 요약만. 심층 읽기는 서브에이전트가 선정된 세션만 (A5)
- [ ] **플러그인을 자동 설치하지 마** — 설치 명령 안내까지만 (A2)
- [ ] **커밋 메시지·릴리즈 문구에 "star" 계열 단어 쓰지 마** — 중립 표현("first-run setup prompt") 사용
- [ ] **플러그인 내부에 워크스페이스 상태를 저장하지 마** — 상태는 전부 워크스페이스의 `.insane-harness/`
- [ ] **동작 미확인 상태로 버전 올리지 마** — 검증 후 bump, bump = GitHub 릴리즈 발행

---

## 항상 해 (ALWAYS DO)

- [ ] 제안마다 **근거 시그널을 명시** — "왜 이 하네스인가"를 scan 데이터로 설명
- [ ] AskUserQuestion 카드에 **"전부 건너뛰기" 옵션 상시 포함**
- [ ] 질문·리포트는 **사용자 언어**로 (setup.sh 언어 감지 컨벤션)
- [ ] scan.py는 **방어 파싱** — 파싱 실패 라인 스킵, 알 수 없는 포맷에서 크래시 금지 (A1)
- [ ] cadence_check.py는 **config 없으면 무출력 종료** — 미사용 워크스페이스에 소음 0
- [ ] apply 후 **검증 단계** — JSON 유효성, 마커 짝 확인, 실패 시 자동 롤백 + 보고
- [ ] `--dry-run` 지원 — 변경 예정 diff만 출력
- [ ] ledger 갱신은 apply 성공 후에만 (장부와 실상의 불일치 금지)

---

## 테스트 방법

```bash
# 진단 단독 (읽기 전용 — 안전)
python3 bin/scan.py --workspace /Users/chulrolee/gptaku_plugins --output /tmp/scan-test.json
python3 -c "import json; json.load(open('/tmp/scan-test.json'))"  # JSON 유효성

# 적용 dry-run (파일 변경 0 검증)
python3 bin/apply.py --dry-run --plan /tmp/plan-test.json
git status --short  # 변경 없어야 함

# 주기훅 침묵 검증
cd /tmp && python3 <plugin>/bin/cadence_check.py  # config 없음 → 출력 0

# E2E: 본 워크스페이스에서 /insane-harness 실행 → 승인 → git diff 확인
```

---

## 배포 방법

부모 레포 CLAUDE.md의 8단계 체크리스트 그대로: 서브모듈 커밋·푸시 → `gh release create v<ver>` → 부모 포인터 업데이트 → 마켓플레이스 pull → 캐시 교체 → installed_plugins.json → 검증 → CC 재시작.

---

## [NEEDS CLARIFICATION]

- [x] ~~hooks.json의 SessionStart 훅이 플러그인 배포로 전역 활성화되는 동작 확인~~ → **확정 (2026-07-08, 공식 문서)**: 플러그인 hooks.json은 "When plugin is enabled" 자동 활성 (settings.json 무수정). 훅 command는 "current directory"에서 실행되므로 `os.getcwd()` 워크스페이스 판별 유효. `hookSpecificOutput.additionalContext` JSON 형식도 문서 예시와 일치. 출처: code.claude.com/docs/en/hooks
- [ ] skillers-suda 위임 시 인터페이스: 커맨드 체이닝 방식(다음 턴 유도) vs 설치 안내만 — v0.1은 안내 방식으로 구현됨, 체이닝은 v0.2 검토
