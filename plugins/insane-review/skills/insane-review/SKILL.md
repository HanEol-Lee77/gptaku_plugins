---
name: insane-review
description: GPT-5.5 Pro(웹 전용·API 없음)를 Claude Code 안에서 활용한다. 사용자가 검토/수정/문제/리뷰/의견을 요청하면, 의도를 파악해 repomix로 관련 코드만 정밀 패킹한 뒤 구독 ChatGPT Pro에 투입하고 분석을 회수해 반영한다. 트리거 — "GPT한테 물어봐", "Pro 모델 의견", "다른 모델로 검토해줘", "GPT Pro로 리뷰", "repomix로 묶어서 GPT에 넣어줘", "GPT는 어떻게 생각해", "ask gpt pro", "second opinion". agent-council의 웹 전용 멤버로도 동작.
---

# insane-review

**왜 존재하나:** GPT-5.5 Pro는 **웹(구독)에서만** 쓸 수 있고 **API가 없다.** 그래서 Codex CLI·`omc ask`·agent-council의 기존 API provider로는 못 부른다. 이 스킬은 **구독 ChatGPT 웹을 자동화해 Pro를 Claude Code 안으로 끌어오는 유일한 경로**다. API 비용 0, 사용자의 요금제로 동작.

핵심 가치는 "통째 패킹"이 아니라 **"의도 파악 → 관련 타겟만 정밀 선별 → 그것만 패킹"** 이다. 이 선별을 Claude(너)가 수행하는 것이 이 도구의 차별점이다.

## 선행 조건 (한 번 확인)

- Comet 또는 Chrome가 **디버그 포트(9222)로** 실행 + `chatgpt.com` 로그인. 이미 떠 있는데 포트가 없으면 **재시작 필요**(쿠키는 디스크 보존 → 로그인 유지). 스크립트가 자동 실행하지만, 이미 일반 모드로 떠 있으면 사용자에게 종료를 요청하라.
- **모델을 5.5 Pro로** (스크립트 `--model pro`가 자동선택; 안되면 사용자가 1회 수동 설정하면 새 채팅이 상속).
- `playwright`·`pyperclip`(pip), `npx`(repomix는 `npx -y`로 자동설치) 필요. **처음 쓸 땐 `python3 bin/pack_and_ask.py --check-env`로 점검**(부족하면 `--install`로 pip 의존성 자동설치). 브라우저 로그인·Pro 모델은 자동설치 불가 → 위 안내대로.

## 핵심 절차 (검토/수정/리뷰 요청을 받았을 때)

### 1) 의도 파악
사용자가 GPT Pro에게 **무엇을** 묻고 싶은지 한 문장으로 정리한다. (버그 원인? 설계 리뷰? 리팩터 방향? 특정 함수 검증?)

### 2) 타겟 정밀 선별 — **이게 핵심**
전체 레포를 넣지 말고, 의도에 직접 관련된 파일 + 관련 의존부만 고른다:
- 사용자가 지목한 파일/기능에서 시작.
- **관련 확장**: import/require 추적, 호출자·피호출자(grep 또는 LSP `find_references`/`goto_definition`), 관련 테스트, 타입 정의.
- 결과를 **정확한 파일 목록**(→ `--stdin`) 또는 **글롭**(→ `--include "src/auth/**,*.test.ts"`)으로 만든다.
- 큰 코드 본문은 `--compress`(tree-sitter 골격, 토큰 ~74%↓ — 단 **코드 파일만**, 마크다운엔 효과 없음).

### 3) 패킹 + 투입 + 회수 — 스크립트 실행
```bash
python3 <plugin>/bin/pack_and_ask.py \
  --target <repo_root> --include "<globs>" --compress \
  --model pro --force-answer-after 120 \
  --prompt "<의도를 담은 정확한 질문>"
```
또는 정확한 파일 목록을 직접 줄 때(레포를 cwd로):
```bash
printf "src/a.ts\nsrc/b.ts\n" > /tmp/files.txt
# (현재 스크립트는 --include 기반; 정밀 목록은 --include 글롭으로 대체하거나 repomix --stdin 직접 사용)
```
**레포 없이 순수 질문(의견)만:** `--target` 생략 → 프롬프트만 전송.
```bash
python3 <plugin>/bin/pack_and_ask.py --model pro --force-answer-after 90 \
  --prompt "<질문>"
```

### 4) 회수 & 반영
- 응답은 `<plugin>/bin/out/response_*.md`에 저장되고, stdout 끝에 미리보기가 나온다.
- 그 의견을 읽고 **GPT-5.5 Pro의 의견임을 명시**하여 사용자에게 반영/요약한다. 동의/이견을 너의 판단과 함께 제시하라.

## 주의/가드 (실측 기반)

- **git submodule**: 부모 레포 루트에서 서브모듈 파일은 repomix가 제외한다. 서브모듈 안에서 실행하거나 `--target <submodule>` 또는 `--no-gitignore --no-default-patterns`.
- **압축은 코드 파일만** 줄인다(마크다운/문서 위주 폴더엔 무효).
- **Pro 리즈닝은 길다(수 분~수십 분).** `--force-answer-after N`으로 N초 후 "지금 답변 받기"를 눌러 강제 종료·회수. 스크립트 MAX_WAIT는 20분.
- 큰 콘텐츠는 **파일 첨부**로 들어간다(붙여넣기 X). 스크립트가 자동 처리.
- 실패 시 `--retries N`으로 전송/회수를 재시도.

## 주요 플래그
`--target`(생략=프롬프트only) · `--include`(정밀 글롭) · `--compress` · `--model pro` · `--force-answer-after N` · `--retries N` · `--style xml|markdown|plain` · `--browser comet|chrome` · `--pack-only` · `--council`

## agent-council 멤버로 쓰기
`references/council-setup.md` 참고. `--council` 모드는 프롬프트를 위치인자로 받고 **응답만 stdout**으로 내보내(진행로그는 stderr) council worker가 그대로 캡처한다. Pro를 웹 전용 council 멤버로 등록하면 다른 모델들과 토론에 참여시킬 수 있다.
