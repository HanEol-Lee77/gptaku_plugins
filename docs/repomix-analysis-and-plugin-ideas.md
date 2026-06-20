# repomix 분석 + gptaku 마켓플레이스 플러그인 아이디어

> 작성일: 2026-06-19 · 분석 대상: [github.com/yamadashy/repomix](https://github.com/yamadashy/repomix) `v1.15.0` (HEAD `bb4ac47`)
> 방법: 7개 서브시스템 병렬 정독(소스 file:line 인용) → 통합 → 우리 마켓 관점 아이데이션 → **실제 실행 검증**(하단 §검증)

---

## 0. TL;DR

repomix는 **레포 하나를 "AI가 바로 먹을 수 있는 단일 파일"로 패킹하는 CLI**다. 디렉토리/원격 GitHub 레포 → 수집·필터·압축·시크릿스캔 → 자기설명 헤더 + 디렉토리 트리 + 파일 본문을 담은 XML/Markdown/JSON/plain 문서 1개.

세 가지 킬러 기능 — **tree-sitter 코드 압축(토큰 ~70%↓)**, **토큰 카운팅/예산**, **secretlint 시크릿 스캔** — 이 정확히 "외부 AI에 코드 통째로 넘길 때"의 빈 구멍(맥락 선별·토큰 초과·키 유출)을 메운다. → 우리 마켓의 외부-AI 플러그인(pumasi 등)과 결합 가치가 높음.

---

## 1. repomix가 하는 일

- **입력:** 로컬 디렉토리(여러 개 가능) 또는 원격 레포(`user/repo`, URL, `.../tree/branch`)
- **출력:** 단일 문서(기본 `repomix-output.xml`), 스타일 4종(xml·markdown·json·plain)
- **가치:** ① 정액제 AI(Claude/ChatGPT/Gemini)에 코드베이스 전체 맥락을 한 번에, ② AI가 파일 탐색할 필요 제거, ③ 토큰·보안 리스크를 패킹 단계에서 처리
- MIT 라이선스, 공식 사이트 repomix.com, JSNation OSS Awards 2025 "Powered by AI" 후보

## 2. 아키텍처 / 핵심 파이프라인

전체 패킹은 `src/core/packager.ts`의 `pack()` 함수 하나가 오케스트레이션. 독립 단계를 `Promise.all`로 적극 겹쳐 CPU/IO 동시 포화. 로컬·원격 모두 동일한 `pack()` 호출(원격은 CLI가 temp에 shallow clone 후 호출).

```
탐색(globby) → ignore필터(.gitignore+.repomixignore+default+커스텀) → 정렬·dedupe
→ 읽기(인코딩 자동탐지: UTF-8 fast-path → jschardet/iconv로 Shift-JIS·EUC-KR)
   ↘ 시크릿스캔(secretlint, 동시)      ↘ git diff/log(동시)
→ 가공·압축(tree-sitter, 워커스레드) → 의심파일 제거 → 변경빈도 정렬
→ 출력생성(Handlebars)  ↘ 토큰카운팅(동시) → 캐시저장
```

**동시성:** tinypool 워커 3종(fileProcess·securityCheck·calculateMetrics). 스레드 수 `max(1, min(cpu, ceil(tasks/100)))`. 파일 수집만 워커 대신 메인스레드 promise pool(상한 50).

## 3. 킬러 기능 4개

| 기능 | 무엇 | 왜 중요 |
|---|---|---|
| **코드 압축 `--compress`** | web-tree-sitter(WASM)로 AST 파싱 → 언어별 쿼리로 시그니처·선언·import만 캡처(**함수 본문 버림**), `⋮----` 구분자로 연결. **16개 언어**(js·ts·py·go·rust·java·c#·rb·php·swift·c·cpp·css·solidity·vue·dart) | 의미 구조 보존 + **토큰 ~70% 절감** |
| **토큰 카운팅** | `gpt-tokenizer`(o200k_base 기본 등 5종). MD5 콘텐츠키 디스크 캐시. 출력 전체는 파일별 합산 + wrapper만 토크나이즈하는 fast-path. `--token-budget N` 초과 시 비정상 종료 | 한도를 **보내기 전에** 파악 + CI/에이전트 가드 |
| **시크릿 스캔** | secretlint(recommend 프리셋)로 전 파일 + git diff/log 스캔. **파일 hit은 출력에서 제거**, git hit은 경고만. 매칭값은 절대 로깅 안 함 | 외부 AI 전송 전 **API 키 유출 차단** |
| **원격 패킹 `--remote`** | `git clone --depth 1`(브랜치는 fetch, SHA는 full fetch 폴백). clone 전 `git ls-remote`로 도달성 검사. GitHub tarball fast-path | **수동 clone 없이** 남의 레포 분석 |

추가: git diff/log 통합(`--include-diffs/--include-logs`), 변경빈도 정렬(기본 on), 출력 분할(`--split-output`), 주석 제거(`--remove-comments`), 라인번호, 커스텀 instruction 주입.

## 4. 실행 / 통합 경로

`npx repomix@latest`(무설치) · npm 전역 · brew · Docker · **repomix.com 온라인** · 브라우저 확장(GitHub 페이지에 버튼 주입) · VSCode 확장 · GitHub Action · **MCP 서버** · **Claude Code 플러그인(자기 레포가 곧 마켓플레이스)** · Node 라이브러리(`pack`, `TokenCounter`, `parseFile`, `runSecurityCheck`, `defineConfig`…).

**Claude Code self-packaging:** repomix 레포 자체가 `.claude-plugin/marketplace.json`으로 3분할 플러그인 — `repomix-mcp`(MCP), `repomix-commands`(`/pack-local`·`/pack-remote`), `repomix-explorer`(분석 서브에이전트 + 스킬). 스킬은 "Trigger for / DO NOT trigger for" 양방향 스코핑 + "원격 팩은 항상 `/tmp`로, 읽기 전 grep" 같은 컨텍스트 절약 규칙을 절차로 박아둠 → **우리가 베껴올 패턴.**

## 5. MCP 서버가 노출하는 도구 8개 + 프롬프트 1개

`npx -y repomix --mcp`(stdio). 리소스 없음 — `outputId` 레지스트리 + read/grep 도구로 간접 노출.

| 도구 | 핵심 입력 | 핵심 출력 | 메모 |
|---|---|---|---|
| **pack_codebase** | `directory`(절대경로) | `outputId`, `directoryStructure`, `totalTokens` | 로컬 패킹 |
| **pack_remote_repository** | `remote`(user/repo·URL) | 동일 | 원격 clone+팩 |
| **generate_skill** | `directory`, `skillName` | `skillPath` | **유일하게 프로젝트에 쓰기**: `.claude/skills/<name>/` 생성 |
| **attach_packed_output** | `path` | `outputId` | 기존 출력 등록(비신뢰→read 시 재스캔) |
| **read_repomix_output** | `outputId`, `startLine/endLine` | `content` | 라인범위 읽기 |
| **grep_repomix_output** | `outputId`, `pattern` | `matches` | **전체 대신 슬라이스** 추출(토큰 절약 권장) |
| **file_system_read_file** | `path` | `content` | 읽기마다 시크릿 스캔 강제 |
| **file_system_read_directory** | `path` | `contents` | 디렉토리 나열 |

에이전트 실사용: 스폰 → `pack_*`로 `outputId` 획득 → `grep_repomix_output`으로 관련 슬라이스만 → `read_repomix_output` → 필요시 `file_system_read_*` → `generate_skill`로 재사용 스킬화.

## 6. 산출물(XML) 구조

섹션 순서(모든 스타일 동일): 생성헤더 → `<file_summary>`(purpose·format·usage_guidelines·notes) → (사용자 헤더) → `<directory_structure>` → `<files>`(파일별 `<file path="...">`) → (Git Diffs) → (Git Logs) → (`<instruction>`). 설계 철학: "지도(트리)를 영토(본문)보다 먼저", "읽기 계약을 코드보다 먼저", "지시는 마지막에"(LLM이 가장 무게 두는 위치). 기본 XML은 Handlebars 렌더(스키마검증 X), `--parsable-style`이면 fast-xml-builder로 진짜 XML.

---

## 7. 플러그인 아이디어 7개 (추천순)

### #1 외주이관 ⭐ (추천 Top 1)
pumasi가 Codex에 서브태스크를 넘기기 **직전**, 관련 디렉토리만 `--compress` 패킹 + **secretlint 게이트**를 끼운다.
- **문제:** pumasi는 지금 맥락을 손으로 정리 → 바이브코더는 모듈 경계를 모르고 토큰 초과/맥락 누락으로 외주 결과가 틀림. 더 큰 문제: **외부 AI에 코드 넘기기 전 키 유출을 아무도 안 봄.**
- **활용:** CLI(`--compress --include`) + secretlint hit 시 디스패치 차단(게이트)
- **형태:** skill+script (중) · pumasi 워크플로우에 1단계 추가
- **차별점:** repomix 단독=패킹만. 여기선 pumasi PM→디스패치 파이프라인에 **보안 게이트+토큰 예산 가드**로 박힘. 통합은 못 베낌. 컴포넌트가 #2·#5·#7로 재사용.

### #2 레포뜯기
`--remote`로 공개 레포 받아 아키텍처/패턴/의존성을 **한국어 구조 해설 + 따라만들기 가이드**로.
- **문제:** "이 레포 어떻게 짠 거지?"의 clone→탐색→이해 진입장벽 (이 분석 문서가 곧 출력 예시)
- **활용:** MCP(`pack_remote_repository`→`grep_repomix_output`→`read_repomix_output`), `--compress`로 골격 먼저
- **형태:** skill+MCP (중)
- **차별점:** insane-design이 "디자인을 뜯으면" 이건 "아키텍처를 뜯음". kkirikkiri/show-me-the-prd 연계로 "이 레포처럼 만들어줘→PRD화" 가능

### #3 토큰지킴이
폴더 던지기 전 토큰 예산 체크 + 압축/include 전략 추천.
- **문제:** 바이브코더는 "왜 느려/끊겨"가 컨텍스트 폭주인 걸 모름
- **활용:** `TokenCounter`/`calculateMetrics` API 또는 `--token-count-tree`/`--token-budget`
- **형태:** skill+script (하~중)
- **차별점:** repomix는 숫자만. 여기선 "o200k 기준 N토큰=Claude 200K의 X%, 이 3개 빼면 40%↓" 한국어 액션추천 + vibe-sunsang 성장지표 연계

### #4 스킬자판기
레퍼런스 폴더 → 재사용 Agent Skill 자동 발행(skillers-suda 검수).
- **문제:** skillers-suda는 아이디어→스킬은 되지만 "기존 폴더를 스킬화"는 없음
- **활용:** MCP `generate_skill`(또는 CLI `--skill-generate`)
- **형태:** skill+MCP (하) — repomix가 산출물 만들어주므로 한국어화+검수만
- **차별점:** generate_skill 원본=영어 기계생성. 우리는 skillers-suda "4인 검수"로 한국어화·트리거 최적화

### #5 인수인계
git diff/log + 압축으로 "PR 리뷰 묶음" / "오늘 한 일" 컨텍스트 생성.
- **문제:** PR 리뷰를 외부 AI에 맡길 때 변경맥락을 못 줌
- **활용:** `--include-diffs/--include-logs` + 변경빈도 정렬, 변경 파일+의존부만 include
- **형태:** skill+script (중)
- **차별점:** "바뀐 코드+주변+diff+이력"을 한 묶음으로. code-review 플러그인과 결합 시 강력

### #6 (인프라) 워커 골격 주입
kkirikkiri/pumasi 워커에 `--compress` tree-sitter 골격만 먼저 줘서 토큰 N배 절감.
- **활용:** `parseFile` 라이브러리 API (16개 언어)
- **형태:** skill+script (중~상) · 사용자 노출 아닌 내부 효율 개선

### #7 시크릿가드
dd/nopal/pumasi 공용 "외부 전송 전 secretlint 스캔" 훅.
- **활용:** `runSecurityCheck` API
- **형태:** hook (하~중) · #1에 흡수될 수 있어 순위 낮음

### 추천 Top 1 = #1 외주이관
① 이미 검증된 수요(간판 pumasi의 실존 흐름)의 빈 구멍을 정확히 메움 → 새 습관 불필요한 안전한 베팅. ② 차별점이 구조적으로 방어됨(pumasi 파이프라인 통합은 못 베낌). ③ 컴포넌트가 #2·#5·#7로 재사용되는 마켓 공용 인프라. 빠른 검증: `.pumasi/pumasi.config.yaml` 흐름에 `repomix --compress --include <subtask-dirs>` 1단계 + secretlint hit 시 차단 PoC(1~2일).

---

## 8. 실제 실행 검증 (분석 vs 실제)

repomix `v1.15.0`를 우리 플러그인 폴더(show-me-the-prd 16개, kkirikkiri 48개)와 합성/가짜 폴더에 실제 실행해 분석 주장을 대조했다. **7개 주장 전부 실측과 일치(✅).** (테스트 스크립트: `/tmp/repomix-test/run.sh`, 산출물: `/tmp/repomix-test/*.xml`)

| # | 분석 주장 | 테스트 | 실제 결과 | 판정 |
|---|---|---|---|---|
| 1 | XML 출력 구조: 헤더 → `<file_summary>(purpose·usage_guidelines·notes)` → `<directory_structure>` → `<files>` → `<file path="...">` | `repomix plugins/show-me-the-prd --stdout` | 첫 줄 = "This file is a merged representation…", 6개 섹션 마커 모두 존재, `<file path=` 15개 | ✅ |
| 2 | `--compress` tree-sitter가 함수 **본문 버리고 시그니처/선언/주석만** + `⋮----` 구분자 + 토큰 **~70%↓** | kkirikkiri JS 3파일 압축 ON/OFF | **6,724 → 1,750 토큰 (74%↓)**, `⋮----` 0→52개, `function hasCommand(name)` 뒤 본문 없이 `⋮----`, 주석 보존 | ✅ |
| 3 | 토큰 카운팅(o200k_base) 파일별/디렉토리별 + Top 파일 | `--token-count-tree` | Top 5 파일 + 트리 형태 per-file/per-dir 토큰(SKILL.md 4,723 등) 출력 | ✅ |
| 4 | secretlint가 시크릿 파일을 **출력에서 제거**, 스캔 끄면 포함 | 가짜 `leak.env`(AWS/GH/Slack)·`key.pem`(개인키)·`normal.js` | ON: "2 suspicious file(s) detected and excluded", `<files>`에 leak/key 0·normal 1. OFF(`--no-security-check`): 3파일 전부 포함 | ✅ |
| 5 | 출력 4종(xml·markdown·json·plain) 동일 섹션, json은 camelCase 키 | 합성 2파일에 `--style` 4종 | xml=태그, md=`# File Summary`, json=`{fileSummary, directoryStructure, files:{path:content}}`(camelCase), plain=`===` 배너 | ✅ |
| 6 | `generate_skill`(=CLI `--skill-generate`)이 `SKILL.md` + `references/` 생성 | `--skill-generate smtp-ref --skill-output …` | `SKILL.md`(frontmatter name/description + "Use this skill when…" + Files 표) + `references/{summary,files,project-structure}.md` 생성 | ✅ |
| 7 | `--remote user/repo`로 수동 clone 없이 패킹 | `--remote octocat/Hello-World --stdout` | 1,742 bytes, `<directory_structure>` + `<file path="README">` 정상 | ✅ |

**추가로 확인된 디테일(분석 보강):**
- json `notes`에 *"Files are sorted by Git change count (files with more changes are at the bottom)"* 가 박혀 있어 **변경빈도 정렬이 기본 on**임을 출력 자체가 증명.
- 압축률은 **문자수도 74%↓**(23,889→6,213) — 토큰/문자 동률로 감소.
- `--skill-generate`는 폴더명을 Title Case로 변환("show-me-the-prd"→"Show Me The Prd") — 한국어 플러그인엔 후처리 필요(→ #4 스킬자판기의 "skillers-suda 검수" 명분 보강).

**검증 한계(정직한 고지):** MCP 8개 도구는 **CLI 경로로만** 간접 검증했다. `--skill-generate`는 MCP `generate_skill`과 같은 `packSkill` 코어를 쓰므로 산출물은 동일하나, MCP 와이어 프로토콜(stdio 등록→`outputId`→`grep_repomix_output`)을 실제 MCP 클라이언트로 돌려보진 않았다. #2·#4를 진짜로 만들 땐 `npx -y repomix --mcp` 등록 후 도구 호출까지 한 번 확인 필요.

---

## 9. 메인 컨셉 — 구독 ChatGPT 브릿지 = **insane-review** ⭐ 플러그인화 완료 (`plugins/insane-review/`)

> **repomix로 패킹 → 구독 ChatGPT(웹) 자동 투입 → 분석 회수 = API 비용 0, 내 요금제로.**
> `Budongsan_AI_Book/70-playground/test_v4.py`의 검증된 ChatGPT 자동화 하네스를 "책 실습 러너"에서 "아무 폴더나 → 구독 AI 분석" 범용기로 일반화한 것.

### 왜 브라우저 자동화(Playwright+CDP)가 정답인가
핵심은 **Pro 모델의 긴 응답 시간**(수 분~십수 분). 이게 방식을 가른다.

| 기준 | ⭐ 브라우저 자동화(Playwright+CDP) | 컴퓨터유즈→데스크탑앱 | Claude-in-Chrome(MCP) |
|---|---|---|---|
| 긴 응답 대기(Pro 15분) | DOM 폴링 = 거의 공짜 | 스크린샷 폴링 = 토큰 폭발 | 중간 |
| 긴 응답 회수 | 복사버튼→클립보드 = 깔끔 | 비전/OCR = 엉망 | DOM 읽기 양호 |
| 패키지화(배포) | python = 무인·이식 | 비전루프 = 배포 불가 | 세션 종속 |
| 이미 검증됨 | ✅ run_v4 이력 | ❌ | ❌ |

→ 데스크탑앱+컴퓨터유즈는 **폴백 모드**(웹 UI가 캡차로 자동화 차단 시)로만. (ChatGPT.app 설치 확인됨)

### 진짜 중요한 건 "콘텐츠 채널"
repomix 출력은 크다. test_v4의 **붙여넣기**는 큰 패킹에서 깨진다 →
1. **파일 첨부로 투입**(`input[type=file].set_input_files`) — 길이 제한 회피, GPT-5 Pro가 첨부파일 읽음
2. **`--compress` + `--token-budget` 게이트**로 컨텍스트 창에 맞춤 (아이디어 #3 토큰지킴이 흡수)

### 아키텍처
```
repomix 패킹(--compress/--include/--token-budget) → 출력파일
 → Comet/Chrome CDP attach(로그인 세션 재사용) → 파일첨부+프롬프트
 → stop-button 폴링(최대 20분) → 복사버튼→클립보드 회수 → .md 저장
```

### 상태 — 플러그인화 완료 `plugins/insane-review/` (PoC 원본: `prototypes/gpt-bridge/`)
- **오프라인 절반 검증 완료 ✅**: 문법/`--help`/패킹·토큰파싱 동작. `--pack-only`로 show-me-the-prd `--compress` → 78,360 bytes / ~21,823 tokens 생성.
- **실측 발견(중요)**: show-me-the-prd는 `--compress`해도 21.8k 토큰 거의 그대로 — **tree-sitter 압축은 코드 파일만** 줄인다(마크다운 위주 폴더엔 무효). kkirikkiri JS에선 74%↓였음 → **압축 효과는 "코드 비중"에 비례**. 가드로 새길 것.
- **라이브 절반(ChatGPT 왕복) 검증 완료 ✅ (Pro 포함)**: Comet 디버그포트 attach → 새 채팅 → **파일 첨부** → 전송버튼 클릭 → 응답 회수 → `.md` 저장. kkirikkiri scripts(3,530토큰)로 왕복 성공, ChatGPT가 첨부파일을 정확히 분석. **기본모델 43초 / Pro 119초**.
- **실측 발견들 & 검증된 기능(라이브, 전부 관측됨)**:
  - 큰 붙여넣기는 ChatGPT가 "pasted text" 첨부로 자동 변환 + 빈 입력창 Enter는 no-op → **본문은 파일첨부, 짧은 프롬프트는 입력창 분리, 전송은 ↑버튼 클릭**이 정답.
  - **모델 자동선택 동작 ✅**: 스위처 = `button.__composer-pill[aria-haspopup="menu"]`(텍스트=현재모델). 클릭 시 `[role="menuitemradio"]`(즉시/중간/높음/매우 높음/**Pro**) + `[role="menuitem"]`("GPT-5.5"). → **"Pro"는 GPT-5.5의 지능 라디오 최상위.** `--model pro`로 `✓ 모델 선택: 'Pro'` 검증. (사용자 1회 수동설정 → 새 채팅 상속도 robust 폴백.)
  - **`--force-answer-after N` 검증 ✅**: Pro 긴 리즈닝 중 N초 후 **"지금 답변 받기"**(리즈닝 칩="Pro 생각 중", 버튼은 `<button>`이 아닌 클릭가능 div, `data-testid="stage-thread-flyout"` 내부) 클릭 → 리즈닝 강제 종료. 실측: 16초 클릭 → 3,424자 답변 68초 회수.
  - **프롬프트-only 모드 검증 ✅**: `--target` 생략 시 레포 없이 질문만 전송(= GPT 의견 모드). 모델 자동선택 + 회수 동작.
  - **정밀 타겟팅**: 전체 패킹 대신 `--include "globs"` 또는 **`--stdin`(정확한 파일 목록)**. 의도→타겟→관련파일 선별은 **Claude가 grep/LSP/import로 수행 → 그 목록만 패킹**(핵심 가치). ⚠️ **git submodule 주의**: 부모 루트에서 서브모듈 파일은 stdin이 제외(0개) → 서브모듈 안에서 실행하거나 `--no-gitignore --no-default-patterns` 또는 `--target <submodule> --include`.
  - Comet이 디버그포트 없이 실행 중이면 재시작 필요(쿠키는 디스크 보존 → 로그인 유지).
- 모드/플래그: `--target`(생략=프롬프트only) / `--include`·`--stdin`(정밀선별) / `--compress` / `--model "pro"`(자동선택) / `--force-answer-after N`(리즈닝 컷) / `--attach`·기본첨부 / `--pack-only` / `--browser comet|chrome` / `--style xml|markdown|plain`.

---

## 10. 발산 라운드 2 — 새 아이디어 12선 (6렌즈 × 36 raw → 큐레이션)

기존 7개·insane-review와 중복 제거 후 살아남은 테마별 정수. (전체 raw: 워크플로우 산출 36개)

**테마 A. 코드 아닌 코퍼스 (repomix의 "ANY 폴더" 정면 활용)**
- **원고 편집장** — 챕터 수십 개 원고를 한 컨텍스트에 올려 용어/모순/중복/떡밥회수 전역 검수. ANY md 패킹 + token-count-tree + split-output + instruction-file. ↔ book-wrap·humanize-korean·md2gdoc로 한국어 집필 파이프 완성.
- **내 노트 채굴(PKM Miner)** — 수백 .md 볼트에서 잊힌 씨앗 노트 발굴 + secretlint로 노트 속 키 위생.
- **회의록 판결(Decision Tracer)** — 날짜별 회의록에서 결정의 생애(생성→번복→미해결) 타임라인화.

**테마 B. 시간축 자아 (수신자가 "본인")**
- **방치레포 깨우기(Comeback Brief)** — 방치한 사이드프로젝트 복귀 비용 제거. include-logs/diffs로 "하다 만 변경=하려던 일" 역추정 + compress 1페이지 지도 + TODO grep. ↔ goaljaby로 복귀→다음 골.
- **성장증거** — vibe-sunsang이 대화만 봐서 생기는 성장 과대/과소평가를, 두 시점 골격 JSON diff(코드 증거)로 보강.

**테마 C. 나를 파는 자산 (비개발 독자가 소비자)**
- **포트폴리오 미끼** — 깃헙에 묻힌 레포를 채용담당자 30초 1-pager + 예상 면접질문으로. compress + 변경빈도 + include-logs(과장 없는 기여도) + secretlint.
- **강의짜개(Lesson Carver)** — 마일스톤 커밋=강의 챕터 경계, "코드가 자라는 과정"을 단계 분할.

**테마 D. 마켓 거버넌스 (운영자 본인의 1순위 DX 고통)**
- **캐시 집사(Cache Butler)** — CLAUDE.md 8단계 수동 캐시교체에서 version↔폴더명↔installPath↔SHA **4자 불일치를 머신리딩 적발**. repomix를 "설치 정합성 진단"에 전용.
- **마켓 지도(Market Cartographer)** — plugins/ 전체 compress 패킹 → 트리거 충돌 매트릭스 + 커버리지 공백 지도(신규 아이디어 중복판정 자동화).
- **표준 검문소(CCPS Gate)** — 마켓 등재 전 CCPS 위반·영한 README 비동기화·SSOT 드리프트·시크릿·토큰비대 자동 심사.

**테마 E. 미사용 기능 단발 유틸 (하 난이도, 빠른 출시)**
- **토큰 지도(Token Heatmap)** — token-count-tree + jq로 "이 5폴더가 78%, 빌드산출물이니 ignore 권장" + .repomixignore 자동 생성. (#3 토큰지킴이의 "범인 지목+처방" 강화판)
- **렌즈 주입(Lens Presets)** — instruction-file로 렌즈별(보안/온보딩/리팩터/면접) 지시를 패킹에 못박는 재사용 렌즈 팩.

### 패널 판정
- **신규 Top 3**: ① **캐시 집사**(운영자 즉시 도그푸딩·발상 도약) ② **원고 편집장**(ANY 폴더 정면·집필 파이프 완성) ③ **방치레포 깨우기**(보편적 고통·출시 장벽 최저)
- **전체 베스트(패널 의견)**: "캐시 집사" — repomix를 운영 인프라 진단으로 차원 전환. 사용자용 단일 베팅이면 "방치레포 깨우기".
- **단, 현재 사용자 선택 = insane-review(§9)** 가 활성 빌드 라인(플러그인화 완료). 위 12선은 백로그.
