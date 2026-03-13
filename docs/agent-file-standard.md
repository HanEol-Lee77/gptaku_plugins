# .claude/agents/ 에이전트 파일 표준 포맷

> kkirikkiri와 skillers-suda 플러그인이 공유하는 에이전트 파일 스키마 정의.

## 1. Frontmatter (YAML)

```yaml
---
name: {agent-name}                    # 필수. 에이전트 식별자 (파일명과 일치 권장)
description: {트리거 설명}              # 필수. Pushy 전략 적용 — 역할 + 트리거 상황
model: inherit                        # 필수. inherit | haiku | sonnet | opus
tools: [{도구 목록}]                   # 선택. 미지정 시 기본 도구 사용

# 확장 메타데이터 (플러그인 연동용)
source: manual                        # 선택. manual | kkirikkiri | skillers-suda
created: 2026-03-14                   # 선택. 생성일
recommended-for: [research, analysis] # 선택. kkirikkiri 프리셋 매핑용 태그
---
```

### 필수 필드

| 필드 | 타입 | 설명 |
|------|------|------|
| `name` | string | 에이전트 이름. 파일명과 일치 권장 (`my-agent.md` → `name: my-agent`) |
| `description` | string | 에이전트 트리거 설명. Pushy 전략 적용 |
| `model` | enum | `inherit` (세션 모델 사용), `haiku`, `sonnet`, `opus` |

### 선택 필드

| 필드 | 타입 | 설명 | 사용처 |
|------|------|------|--------|
| `tools` | string[] | 에이전트가 사용할 도구 목록 | Claude Code 에이전트 시스템 |
| `source` | enum | 생성 출처 (`manual`, `kkirikkiri`, `skillers-suda`) | 추적/관리 |
| `created` | date | 생성일 (YYYY-MM-DD) | 정리/관리 |
| `recommended-for` | string[] | 적합한 프리셋 태그 | kkirikkiri 프리셋 매핑 |

## 2. 본문 구조

```markdown
# {Agent Name}

## 역할
{에이전트의 핵심 역할과 목적 — 1-3문장}

## 전문 분야
{에이전트가 특화된 도메인 — 목록 형태}

## 작업 방식
{작업 수행 방법과 절차}

## 도구 사용 가이드 (tools 필드가 있을 때)
{각 도구의 사용 시점과 방법}

## R&R
### 해야 할 것
- ...

### 하지 말 것
- ...
```

### 필수 섹션

| 섹션 | 필수 여부 | 설명 |
|------|----------|------|
| 역할 | 필수 | 핵심 목적 |
| R&R | 필수 | 범위 제한 |
| 전문 분야 | 권장 | 도메인 명시 |
| 작업 방식 | 권장 | 절차 기술 |
| 도구 사용 가이드 | 선택 | tools가 있을 때 |

## 3. 파일명 규칙

- 소문자 + 하이픈: `my-agent.md` (O), `MyAgent.md` (X)
- 역할 기반 네이밍: `code-reviewer.md`, `data-analyst.md`
- `name` 필드와 파일명 일치 권장

## 4. 분량 가이드

| 항목 | 기준 |
|------|------|
| 전체 | 500-1,500 단어 |
| 역할 | 1-3 문장 |
| R&R | 각 3-7 항목 |
| 작업 방식 | 3-10 단계 |

## 5. 호환성

### kkirikkiri (소비자)
- Step 2 환경 스캔: `.claude/agents/*.md` 자동 스캔
- frontmatter의 `recommended-for`로 프리셋 매핑
- `subagent_type`에 파일명 사용하여 스폰
- `description`과 본문의 "역할" 섹션으로 관련성 판단

### skillers-suda (생산자/관리자)
- Phase E: 에이전트 컴포넌트 선택 시 이 포맷으로 생성
- Phase D: 기존 에이전트 스캔으로 중복 방지
- 분석 모드: 기존 에이전트 품질 분석 + 개선
- `source: skillers-suda` 태그로 자동 생성 식별

## 6. 검증 (verify-agent.py)

에이전트 파일 품질 검증 항목:

| 항목 | 기준 | 상태 |
|------|------|------|
| frontmatter_exists | YAML frontmatter 존재 | PASS/FAIL |
| name_field | name 필드 존재 + 비어있지 않음 | PASS/FAIL |
| description_field | description 존재 + 20자 이상 | PASS/FAIL |
| model_field | model 유효값 (inherit/haiku/sonnet/opus) | PASS/FAIL |
| tools_field | tools 배열 + 유효 도구 이름 | PASS/WARN |
| role_section | "역할" 또는 "Role" 섹션 존재 | PASS/FAIL |
| rnr_section | R&R 섹션 존재 | PASS/WARN |
| word_count | 본문 500-1,500 단어 | PASS/WARN |
| filename_match | 파일명과 name 필드 일치 | PASS/WARN |
