#!/usr/bin/env python3
"""
insane-review PoC — repomix 패킹 → 구독 ChatGPT(웹)에 투입 → 분석 회수 (API 비용 0)

핵심 아이디어:
  1) 분석 대상 폴더를 repomix로 단일 파일 패킹 (--compress로 토큰 절감, --token-budget 가드)
  2) Comet/Chrome를 CDP로 attach → 로그인된 chatgpt.com 세션 재사용 (구독 요금제 그대로)
  3) repomix 출력을 '파일 첨부' 또는 '붙여넣기'로 투입 + 분석 프롬프트
  4) stop-button이 사라질 때까지 폴링(최대 20분, Pro thinking 대비) → 복사버튼/클립보드로 회수
  5) 응답을 .md로 저장

test_v4.py(Budongsan_AI_Book/70-playground)의 검증된 ChatGPT 자동화 프리미티브를 일반화한 것.

Usage:
  # 패킹만 (브라우저 안 띄움) — 오프라인 검증용
  python pack_and_ask.py --target ../../plugins/show-me-the-prd --compress --pack-only

  # 실제 ChatGPT 투입 (Comet 로그인 세션 필요)
  python pack_and_ask.py --target ../../plugins/kkirikkiri --include "scripts/**" --compress \
      --prompt "이 코드베이스의 아키텍처를 분석하고 개선점 3가지를 짚어줘"

  # 큰 패킹은 붙여넣기 대신 파일 첨부
  python pack_and_ask.py --target ../../plugins/pumasi --compress --attach
"""

from __future__ import annotations

import argparse
import re
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# ---- 선택 의존성(라이브 모드에서만 필요) ----
try:
    import pyperclip
except ImportError:
    pyperclip = None
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

# ---------------------------------------------------------------------------
# 설정 (test_v4.py에서 검증된 값 재사용)
# ---------------------------------------------------------------------------
COMET_PATH = "/Applications/Comet.app/Contents/MacOS/Comet"
CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CDP_PORT = 9222
CDP_URL = f"http://127.0.0.1:{CDP_PORT}"

CHATGPT_URL = "https://chatgpt.com/"
INPUT_SELECTORS = ["#prompt-textarea", 'div[contenteditable="true"]']
FILE_INPUT_SELECTOR = 'input[type="file"]'
COPY_BTN = 'button[data-testid="copy-turn-action-button"]'
STREAMING_BTN = 'button[data-testid="stop-button"]'
RESPONSE_SELECTORS = [
    'div[data-message-author-role="assistant"]',
    "div.markdown",
    "div.prose",
    'div[class*="markdown"]',
]
ATTACH_CHIP_SELECTORS = [
    'div[data-testid="attachment"]',
    'div[class*="attachment"]',
    'button[aria-label*="remove" i]',
]

MAX_WAIT_SECS = 1200   # Pro 모델 긴 thinking 대비 (20분)
MIN_WAIT_SECS = 30
STABLE_CHECK_SECS = 10
STATUS_INTERVAL = 15

OUT_DIR = Path(__file__).parent / "out"

DEFAULT_PROMPT = (
    "첨부(또는 위)는 repomix로 패킹한 코드베이스입니다. "
    "다음을 한국어로 분석해줘:\n"
    "1) 이 프로젝트가 하는 일과 전체 아키텍처\n"
    "2) 핵심 모듈 간 데이터 흐름\n"
    "3) 잠재적 버그/리스크 또는 개선점 3가지 (근거 파일 경로 포함)\n"
    "결론부터 말하고 근거는 그 뒤에."
)


# ---------------------------------------------------------------------------
# 1) repomix 패킹
# ---------------------------------------------------------------------------
def pack_repo(target: Path, *, include: str | None, ignore: str | None,
              compress: bool, style: str, token_budget: int | None,
              out_path: Path) -> tuple[Path, int | None]:
    if shutil.which("npx") is None:
        sys.exit("❌ npx가 없습니다. Node.js를 설치하세요.")

    cmd = ["npx", "-y", "repomix@latest", str(target), "-o", str(out_path), "--style", style]
    if compress:
        cmd.append("--compress")
    if include:
        cmd += ["--include", include]
    if ignore:
        cmd += ["--ignore", ignore]
    if token_budget:
        cmd += ["--token-budget", str(token_budget)]

    print(f"  $ {' '.join(cmd)}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    out = proc.stdout + proc.stderr

    # repomix 요약에서 Total Tokens 파싱
    tokens = None
    m = re.search(r"Total Tokens:\s*([\d,]+)", out)
    if m:
        tokens = int(m.group(1).replace(",", ""))

    if token_budget and proc.returncode != 0 and tokens and tokens > token_budget:
        print(f"  ⚠️  토큰 예산 초과: {tokens:,} > {token_budget:,}")
        print("     → --include로 범위를 좁히거나 --compress를 켜세요. (그래도 파일은 생성됨)")
    elif proc.returncode != 0:
        print("  ⚠️  repomix 경고/오류:")
        print("     " + "\n     ".join(out.strip().splitlines()[-6:]))

    if not out_path.exists():
        sys.exit("❌ repomix 출력 파일이 생성되지 않았습니다.")

    size = out_path.stat().st_size
    print(f"  ✓ 패킹 완료: {out_path}  ({size:,} bytes"
          + (f", ~{tokens:,} tokens)" if tokens else ")"))
    return out_path, tokens


# ---------------------------------------------------------------------------
# 2) 브라우저(CDP) 준비 — test_v4 패턴
# ---------------------------------------------------------------------------
def is_port_open(port: int = CDP_PORT) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        return s.connect_ex(("127.0.0.1", port)) == 0
    finally:
        s.close()


def ensure_browser(browser: str) -> bool:
    if is_port_open():
        print(f"  ✓ 브라우저 CDP 연결됨 (port {CDP_PORT})")
        return True
    path = COMET_PATH if browser == "comet" else CHROME_PATH
    if not Path(path).exists():
        print(f"  ❌ 브라우저 미설치: {path}")
        return False
    print(f"  {browser} 시작 중 (CDP {CDP_PORT})...")
    subprocess.Popen([path, f"--remote-debugging-port={CDP_PORT}"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for i in range(30):
        if is_port_open():
            print(f"  ✓ 시작 완료 ({i + 1}s)")
            time.sleep(2)
            return True
        time.sleep(1)
    print("  ❌ 브라우저 시작 타임아웃")
    return False


def check_env(do_install: bool = False) -> int:
    """환경 점검 — node/npx, repomix(npx 자동), pyperclip, playwright, 브라우저 CDP. 반환=부족 개수."""
    import importlib.util
    print("=== insane-review 환경 점검 ===")
    ok, issues = [], []

    npx, node = shutil.which("npx"), shutil.which("node")
    if node and npx:
        ok.append("node/npx 있음")
        ok.append("repomix: `npx -y repomix@latest`로 자동 설치됨 (사전설치 불필요)")
    else:
        issues.append(("node/npx 없음", "Node.js 설치: https://nodejs.org 또는 `brew install node`"))

    for mod, pip in (("pyperclip", "pyperclip"), ("playwright", "playwright")):
        if importlib.util.find_spec(mod):
            ok.append(f"python {mod} 있음")
        else:
            issues.append((f"python {mod} 없음", f"pip install {pip}"))

    if is_port_open(CDP_PORT):
        ok.append(f"브라우저 CDP({CDP_PORT}) 열림 — 로그인/모델(Pro)은 직접 확인")
    else:
        issues.append((f"브라우저 CDP({CDP_PORT}) 닫힘",
                       f"Comet/Chrome를 --remote-debugging-port={CDP_PORT}로 실행 + chatgpt.com 로그인 + 모델 Pro "
                       "(스크립트가 자동 실행도 시도함)"))

    for o in ok:
        print(f"  ✓ {o}")
    for name, hint in issues:
        print(f"  ✗ {name}\n      → {hint}")

    if do_install:
        import subprocess as sp
        for mod, pip in (("pyperclip", "pyperclip"), ("playwright", "playwright")):
            if not importlib.util.find_spec(mod):
                print(f"\n[--install] pip install {pip} ...")
                sp.run([sys.executable, "-m", "pip", "install", pip])
        print("  (브라우저/로그인은 자동설치 불가 — 위 안내 참고)")

    print(f"\n결과: {len(ok)} OK / {len(issues)} 부족" + ("  — 전부 준비됨 ✅" if not issues else "  ⚠️"))
    return len(issues)


# ---------------------------------------------------------------------------
# 3) ChatGPT 상호작용 — test_v4 프리미티브
# ---------------------------------------------------------------------------
def find_input(page):
    for sel in INPUT_SELECTORS:
        try:
            el = page.query_selector(sel)
            if el:
                return el
        except Exception:
            continue
    return None


def count_responses(page) -> int:
    for sel in RESPONSE_SELECTORS:
        try:
            els = page.query_selector_all(sel)
            if els:
                return len(els)
        except Exception:
            continue
    return 0


def is_streaming(page) -> bool:
    try:
        return page.query_selector(STREAMING_BTN) is not None
    except Exception:
        return False


def normalize(text: str | None) -> str:
    return re.sub(r"\s+", " ", text).strip() if text else ""


def latest_via_copy(page) -> str | None:
    if pyperclip is None:
        return None
    try:
        pyperclip.copy("")
        btns = page.query_selector_all(COPY_BTN)
        if not btns:
            return None
        btn = btns[-1]
        for _ in range(3):
            btn.click(force=True)
            time.sleep(1)
            txt = pyperclip.paste()
            if txt and len(txt) > 10:
                return txt
            pyperclip.copy("")
            time.sleep(0.5)
        return None
    except Exception:
        return None


def latest_via_dom(page) -> str:
    for sel in RESPONSE_SELECTORS:
        try:
            els = page.query_selector_all(sel)
            if els:
                txt = els[-1].inner_text()
                if txt and len(txt) > 30:
                    return txt
        except Exception:
            continue
    return ""


MODEL_SWITCHER_SELECTORS = [
    'button.__composer-pill[aria-haspopup="menu"]',   # 실측: 모델 pill (텍스트=현재 모델, 예: "Pro")
    'button[data-testid="model-switcher-dropdown-button"]',
    'button[aria-label*="model" i]',
]


def read_model_pills(page) -> list[str]:
    """작성창의 pill 버튼 텍스트들(현재 모델/옵션)을 읽어 검증용으로 반환. 예: ['Pro', '중간']"""
    out = []
    for el in page.query_selector_all('button.__composer-pill'):
        try:
            t = (el.inner_text() or "").strip()
            if t:
                out.append(t)
        except Exception:
            continue
    return out
# 실측 구조: pill("Pro") 클릭 → menuitemradio(즉시/중간/높음/매우 높음/Pro) + menuitem("GPT-5.5")
MENU_ITEM_SELECTORS = ['[role="menuitemradio"]', '[role="menuitem"]', '[role="option"]']
SUBMENU_TRIGGERS = ["legacy", "레거시", "more models", "다른 모델", "기타"]


def select_model(page, want: str) -> bool:
    """모델 스위처를 열고 want(부분일치, 대소문자 무시)에 맞는 항목을 클릭."""
    want_l = want.lower()
    switcher = None
    for sel in MODEL_SWITCHER_SELECTORS:
        try:
            el = page.query_selector(sel)
            if el:
                switcher = el
                break
        except Exception:
            continue
    if not switcher:
        print(f"  ⚠️  모델 스위처를 못 찾음 → 기본 모델로 진행")
        return False
    try:
        switcher.click()
        time.sleep(1.5)
    except Exception:
        print("  ⚠️  모델 스위처 클릭 실패 → 기본 모델")
        return False

    def find_and_click(substr: str) -> bool:
        cands = []
        for sel in MENU_ITEM_SELECTORS:
            try:
                cands.extend(page.query_selector_all(sel))
            except Exception:
                continue
        for exact in (True, False):  # 정확일치 우선 → 부분일치
            for it in cands:
                try:
                    t = (it.inner_text() or "").strip()
                    low = t.lower()
                    if (exact and low == substr) or (not exact and substr in low):
                        it.click()
                        print(f"  ✓ 모델 선택: '{t.splitlines()[0][:40]}'")
                        time.sleep(1)
                        return True
                except Exception:
                    continue
        return False

    if find_and_click(want_l):
        return True
    # 1차에 없으면 서브메뉴(레거시/기타 모델)를 열고 재시도
    for trig in SUBMENU_TRIGGERS:
        if find_and_click(trig):
            time.sleep(1)
            if find_and_click(want_l):
                return True
    print(f"  ⚠️  '{want}' 모델 항목을 메뉴에서 못 찾음 → 기본 모델로 진행")
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass
    return False


def attach_file(page, path: Path) -> bool:
    try:
        inp = page.query_selector(FILE_INPUT_SELECTOR)
        if not inp:
            print("  ⚠️  파일 입력 요소를 못 찾음 → 붙여넣기 모드로 폴백")
            return False
        inp.set_input_files(str(path))
        print(f"  파일 첨부 시도: {path.name} (업로드 대기...)")
        for _ in range(30):  # 업로드 칩 등장 대기
            time.sleep(1)
            for sel in ATTACH_CHIP_SELECTORS:
                if page.query_selector(sel):
                    print("  ✓ 첨부 확인됨")
                    time.sleep(2)
                    return True
        print("  ⚠️  첨부 칩을 확인 못함(그래도 진행 시도)")
        return True
    except Exception as exc:
        print(f"  ⚠️  첨부 실패({str(exc)[:60]}) → 붙여넣기 폴백")
        return False


SEND_BTN_SELECTORS = [
    'button[data-testid="send-button"]',
    'button[data-testid="composer-send-button"]',
    'button[aria-label*="send" i]',
    'button[aria-label*="보내기" i]',
    'button[aria-label*="프롬프트 보내기" i]',
]


def put_text(page, message: str):
    """입력창에 텍스트를 넣는다(전송은 안 함). 큰 텍스트면 ChatGPT가 자동 첨부로 바꿀 수 있음."""
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(0.3)
    page.evaluate(
        """() => { const el = document.querySelector('#prompt-textarea')
            || document.querySelector('div[contenteditable=\\"true\\"]');
            if (el) { el.scrollIntoView({block:'center'}); el.focus(); } }"""
    )
    time.sleep(0.3)
    if pyperclip is not None:
        pyperclip.copy(message)
        time.sleep(0.2)
        page.keyboard.press("Meta+v")
    else:
        page.keyboard.type(message)
    time.sleep(0.6)


def click_send(page) -> bool:
    """전송 버튼(↑)을 클릭. 없으면 Enter 폴백."""
    for sel in SEND_BTN_SELECTORS:
        try:
            btn = page.query_selector(sel)
            if btn and btn.is_enabled():
                btn.click()
                print("  ✓ 전송 버튼 클릭")
                time.sleep(1)
                return True
        except Exception:
            continue
    print("  ⚠️  전송 버튼 못 찾음 → Enter 폴백")
    page.keyboard.press("Enter")
    time.sleep(1)
    return False


def click_answer_now(page) -> bool:
    """Pro 리즈닝 중 '지금 답변 받기'를 눌러 답변을 강제로 받는다.
    실측: 버튼은 <button>이 아닌 클릭가능 div, data-testid='stage-thread-flyout' 안. 칩='Pro 생각 중'."""
    def try_click_answer() -> bool:
        try:
            loc = page.get_by_text("지금 답변 받기", exact=True)
            if loc.count() > 0:
                loc.first.click(timeout=3000)
                return True
        except Exception:
            pass
        return False

    if try_click_answer():
        return True
    # 패널이 닫혀 있으면 리즈닝 칩('생각 중')을 눌러 연 뒤 재시도
    try:
        chip = page.get_by_text(re.compile("생각\\s*중"))
        if chip.count() > 0:
            chip.first.click(timeout=3000)
            time.sleep(1.2)
    except Exception:
        pass
    return try_click_answer()


def wait_for_response(page, baseline_count: int, baseline_text: str, force_after=None) -> str:
    start = time.time()
    last_status = 0
    forced = False
    base_snap = normalize(baseline_text)
    extra = f", {force_after}s 후 '지금 답변 받기' 클릭" if force_after else ""
    print(f"    응답 대기 중... (최대 {MAX_WAIT_SECS}s{extra})")
    while time.time() - start < MAX_WAIT_SECS:
        elapsed = int(time.time() - start)
        if force_after and not forced and elapsed >= force_after and is_streaming(page):
            forced = True  # 한 번만 시도
            if click_answer_now(page):
                print(f"    ⚡ {elapsed}s — '지금 답변 받기' 클릭(리즈닝 강제 종료)")
            else:
                print(f"    ⚠️  {elapsed}s — '지금 답변 받기' 버튼 못 찾음(계속 대기)")
        if elapsed - last_status >= STATUS_INTERVAL and elapsed > 0:
            status = "⏳ 생성중" if is_streaming(page) else f"응답 {count_responses(page)}개"
            print(f"    {elapsed}s | {status}")
            last_status = elapsed
        if elapsed < MIN_WAIT_SECS or is_streaming(page):
            time.sleep(2)
            continue
        time.sleep(2)
        if is_streaming(page):
            continue
        new = count_responses(page) > baseline_count
        dom = latest_via_dom(page)
        if not new and dom and len(dom) > 50:
            new = normalize(dom) != base_snap
        if not new:
            time.sleep(2)
            continue
        time.sleep(STABLE_CHECK_SECS)
        txt = latest_via_copy(page)
        if txt and len(txt) > 50 and normalize(txt) != base_snap:
            print(f"    ✅ 응답 수신: {len(txt)}자 ({int(time.time()-start)}s, copy)")
            return txt
        txt = latest_via_dom(page)
        if txt and len(txt) > 50 and normalize(txt) != base_snap:
            print(f"    ✅ 응답 수신: {len(txt)}자 ({int(time.time()-start)}s, DOM)")
            return txt
        time.sleep(3)
    print("    ❌ 타임아웃")
    return latest_via_dom(page)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="repomix → 구독 ChatGPT 분석 PoC")
    ap.add_argument("--target", default=None, help="분석 대상 폴더(생략 시 프롬프트만 전송 = GPT 의견 모드)")
    ap.add_argument("--include", default=None, help='repomix --include 글롭 (예: "src/**,*.md")')
    ap.add_argument("--ignore", default=None, help="repomix --ignore 글롭")
    ap.add_argument("--compress", action="store_true", help="tree-sitter 골격만 (토큰 절감)")
    ap.add_argument("--style", default="markdown", choices=["xml", "markdown", "plain"], help="패킹 포맷")
    ap.add_argument("--token-budget", type=int, default=None, help="이 토큰 넘으면 경고")
    ap.add_argument("--attach", action="store_true", help="붙여넣기 대신 파일 첨부로 투입")
    ap.add_argument("--prompt", default=None, help="분석 프롬프트(직접)")
    ap.add_argument("--prompt-file", default=None, help="분석 프롬프트 파일 경로")
    ap.add_argument("--model", default=None, help='모델 스위처에서 선택할 모델 부분일치(예: "pro", "5.5")')
    ap.add_argument("--force-answer-after", type=int, default=None,
                    help="N초 후에도 리즈닝 중이면 ' 지금 답변 받기' 버튼을 눌러 강제로 답변 받기(Pro 긴 리즈닝 컷)")
    ap.add_argument("--browser", default="comet", choices=["comet", "chrome"])
    ap.add_argument("--pack-only", action="store_true", help="패킹만(브라우저 안 띄움)")
    ap.add_argument("--check-env", action="store_true",
                    help="환경 점검(node/npx·playwright·pyperclip·브라우저 CDP)만 하고 종료")
    ap.add_argument("--install", action="store_true",
                    help="--check-env와 함께: 부족한 pip 의존성 자동 설치")
    ap.add_argument("--council", action="store_true",
                    help="agent-council 멤버 모드: 진행로그는 stderr, 최종 응답만 stdout(output.txt 캡처용)")
    ap.add_argument("--retries", type=int, default=1, help="브라우저 전송/회수 실패 시 재시도 횟수(기본 1)")
    ap.add_argument("prompt_args", nargs="*", help="프롬프트(위치인자 — council 호환; --prompt가 우선)")
    args = ap.parse_args()

    if args.check_env:
        sys.exit(check_env(do_install=args.install))

    # council 모드: 모든 진행 출력을 stderr로 돌리고, 최종 응답만 진짜 stdout으로
    real_stdout = sys.stdout
    if args.council:
        sys.stdout = sys.stderr

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pack_path = None
    tokens = None
    label = "prompt"

    if args.target:
        target = Path(args.target).resolve()
        if not target.exists():
            sys.exit(f"❌ 대상 폴더 없음: {target}")
        label = target.name
        ext = {"xml": "xml", "markdown": "md", "plain": "txt"}[args.style]
        pack_path = OUT_DIR / f"pack_{label}_{ts}.{ext}"
        print(f"\n[1/3] repomix 패킹 — {label}")
        pack_path, tokens = pack_repo(
            target, include=args.include, ignore=args.ignore, compress=args.compress,
            style=args.style, token_budget=args.token_budget, out_path=pack_path)
        if args.pack_only:
            print("\n[pack-only] 패킹만 수행. 브라우저는 띄우지 않음.")
            print(f"산출물: {pack_path}")
            return
    else:
        if args.pack_only:
            sys.exit("❌ --pack-only는 --target이 필요합니다.")
        print("\n[프롬프트-only] 레포 패킹 없이 질문만 전송 (GPT 의견 모드)")

    if sync_playwright is None:
        sys.exit("❌ playwright 미설치. pip install playwright")
    if pyperclip is None:
        print("⚠️  pyperclip 미설치 — 붙여넣기/복사회수 신뢰도 하락 (pip install pyperclip 권장)")

    positional = " ".join(args.prompt_args).strip() if args.prompt_args else ""
    prompt = (args.prompt or positional
              or (Path(args.prompt_file).read_text(encoding="utf-8") if args.prompt_file else None)
              or DEFAULT_PROMPT)

    print(f"\n[2/3] 브라우저 준비 ({args.browser})")
    if not ensure_browser(args.browser):
        sys.exit(1)

    print(f"\n[3/3] ChatGPT 투입 & 응답 회수")
    response = ""
    attempts = max(1, args.retries + 1)
    for attempt in range(1, attempts + 1):
        if attempt > 1:
            print(f"  ↻ 재시도 {attempt - 1}/{args.retries} ...")
            time.sleep(3)
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.connect_over_cdp(CDP_URL)
                ctx = browser.contexts[0] if browser.contexts else browser.new_context()
                page = ctx.new_page()
                try:
                    page.goto(CHATGPT_URL, wait_until="load", timeout=60000)
                    time.sleep(3)

                    for _ in range(10):
                        if find_input(page):
                            break
                        time.sleep(1)
                    if not find_input(page):
                        raise RuntimeError("ChatGPT 입력창 못 찾음 (로그인 필요? chatgpt.com 로그인 확인)")

                    print(f"  현재 작성창 모델/옵션 pill: {read_model_pills(page)}")
                    if args.model:
                        print(f"  모델 선택 시도: '{args.model}'")
                        select_model(page, args.model)
                        print(f"  선택 후 pill: {read_model_pills(page)}")

                    baseline = count_responses(page)
                    baseline_text = latest_via_dom(page)

                    # 레포가 있으면 본문을 '첨부'로 (입력창엔 짧은 프롬프트만 → 전송이 실제로 되게)
                    if pack_path is not None:
                        attached = attach_file(page, pack_path)
                        if not attached:
                            if args.attach:
                                raise RuntimeError("파일 첨부 실패(--attach 강제)")
                            print("  본문 붙여넣기 폴백 (ChatGPT 자동 첨부 변환 기대)")
                            put_text(page, pack_path.read_text(encoding="utf-8"))
                            time.sleep(2)

                    put_text(page, prompt)
                    click_send(page)
                    response = wait_for_response(page, baseline, baseline_text,
                                                 force_after=args.force_answer_after)
                finally:
                    try:
                        page.close()
                    except Exception:
                        pass
            if response:
                break
            print(f"  ⚠️  시도 {attempt}: 응답이 비어있음")
        except Exception as exc:
            print(f"  ⚠️  시도 {attempt} 실패: {str(exc)[:140]}")

    if not response:
        sys.exit("❌ 응답 회수 실패 (모든 재시도 소진)")

    resp_path = OUT_DIR / f"response_{label}_{ts}.md"
    pack_line = f"- 패킹: `{pack_path.name}`" + (f" (~{tokens:,} tokens)\n" if tokens else "\n") \
        if pack_path is not None else "- 패킹: (없음 / 프롬프트-only)\n"
    resp_path.write_text(
        f"# {label} — GPT 응답 (구독 ChatGPT)\n\n"
        + pack_line
        + f"- 프롬프트: {prompt[:80]}...\n\n---\n\n{response}\n",
        encoding="utf-8")
    print(f"\n[완료] 응답 저장: {resp_path}")
    if args.council:
        real_stdout.write(response + "\n")  # council worker가 stdout을 output.txt로 캡처
        real_stdout.flush()
    else:
        print("─" * 50)
        print(response[:800] + ("\n...(생략)" if len(response) > 800 else ""))


if __name__ == "__main__":
    main()
