# Language Policy (SSOT) — gptaku-plugins

모든 gptaku 플러그인의 **출력 언어 계약**. 목표: 한국에서 먼저 출시됐지만, **사용자가 쓰는 언어로 출력**되어 누구나 쓸 수 있게 한다.

> ⚠️ **런타임 미로드**: `shared/`는 설치 시 플러그인 캐시(`~/.claude/plugins/cache/<plugin>/`)에 들어가지 않는다.
> 따라서 이 파일은 **저자용 마스터 카피**다. 실제 규칙은 각 플러그인의 command/SKILL에 **인라인**하고, 이 파일을 동기화 기준점으로 쓴다.
> (질문 정책 `shared/questioning-policy.md`와 동일한 운영 방식.)

---

## §1. 출력 언어 결정 — 자동 감지 (Language Lock)

매 호출마다 새로 판단하고 **저장하지 않는다**. 본문을 읽기 전에 언어를 먼저 잠근다(`output_lang`).

1. **요청에 텍스트가 있으면** → 그 텍스트의 언어 (`/x 만들어줘` → 한국어, `/x make it` → 영어).
2. **요청 텍스트가 없으면** → 직전까지 사용자가 쓰던 대화 언어 (이미 컨텍스트에 있음).
3. **새 세션 + 빈 호출**(텍스트도 직전 대화도 없음) → 영어로, 또는 한 번만 어느 언어인지 물어본다.

> **한국에서 만들어졌다는 이유로 한국어를 기본값으로 두지 말 것.**

감지된 `output_lang`은 사용자에게 보이는 **모든 산출물**에 적용된다: 대화 응답, 설명/코칭, 상태 메시지, 그리고 **디스크에 쓰는 문서**(헤딩·본문 포함).

## §2. 식별자는 번역하지 않는다

언어를 바꿔도 그대로 두는 것: 파일명, 명령어/플래그, 코드, 슬롯 토큰(`{SLOT}`), 약어/고유명사(`PRD`, `SDD`, `JWT`, `viewport`, `scope`, `public API`, `DB 스키마`), URL.

## §3. AskUserQuestion 라벨도 사용자 언어로

`question` / `header` / `label` / `description` 전부 `output_lang`으로 **번역해서** 호출한다.
스킬 파일 안의 JSON 예시는 **템플릿**이다 — 그대로 내보내지 말고 감지 언어로 옮긴다.
참조 구현: `insane-research`(query/main SKILL) — *"Detect user language and translate all labels."*

## §4. 페르소나/브랜드명은 유지

브랜드·페르소나 명칭(`깃선생`, `바선생` 등)은 번역하지 않고 그대로 둔다. 다만 그 **주변 설명·코칭 내용**은 `output_lang`을 따른다.
(예: 영어 사용자에게도 페르소나 이름은 `깃선생`이되, git 설명은 영어로.)

## §5. 디스크 산출물 + 결정론적 검증

문서를 파일로 쓰는 플러그인(goaljaby, insane-design 등)은 산출물도 `output_lang`으로 생성한다.

검증 로직이 헤딩/언어를 grep으로 확인한다면, **고정 언어 가정(=한국어)을 버리고 `output_lang` 기준으로 반전**한다:
- 언어별 **헤딩 세트**(canonical heading map)를 정의해 두고, 생성물의 헤딩이 감지 언어 세트에 속하는지 검증.
- 한국어/영어는 1급 지원(결정론적 grep 가능). 그 외 언어는 헤딩 세트가 없으면 **섹션 존재(개수) 검증**으로 폴백하고, 그 한계를 사용자에게 알린다(침묵 폴백 금지).

## §6. 인라인 스니펫 (각 플러그인에 복붙)

플러그인 command/SKILL 상단에 넣는 짧은 블록:

```
> **언어 정책 (shared/language-policy.md)**: 사용자 요청 언어(output_lang)로 출력한다. 한국 제작이라고
> 한국어를 기본값으로 두지 말 것(§1). 파일명·명령·약어 등 식별자는 번역 안 함(§2).
> AskUserQuestion의 question/label/description도 사용자 언어로 번역해 호출한다(§3).
> 브랜드명(예: 깃선생)은 유지하되 설명은 사용자 언어로(§4).
```

## §7. 이미 준수하는 참조 구현

- `dd/skills/dd/SKILL.md` — `## Language` 섹션 (자동 감지, 영어 폴백, "Never default to Korean")
- `docs-guide` — *"Match the user's language. Korean → Korean, English → English."*
- `insane-research` — AskUserQuestion 라벨 번역 지시
