#!/usr/bin/env python3
"""Marketplace command-frontmatter validator.

Primary gate: a command MUST NOT list `AskUserQuestion` under `allowed-tools`.
Claude Code auto-approves any tool in `allowed-tools`, so an AskUserQuestion there
is silently auto-passed with an empty answer and the question UI never renders.
(See plugins/insane-review/commands/insane-review.md for the in-repo warning.)

Usage:
    python3 tools/validate_commands.py            # scan plugins/*/commands/**/*.md
    python3 tools/validate_commands.py path ...   # scan explicit files

Exit code 0 = clean, 1 = violations found. Dependency-free (stdlib only).
"""
import glob
import os
import sys

FORBIDDEN_TOOL = "AskUserQuestion"


def split_frontmatter(text):
    """Return the YAML frontmatter block (between the first two '---' lines) or ''."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i])
    return ""


def allowed_tools_has_forbidden(frontmatter):
    """True if `allowed-tools` (block list or inline array) contains the forbidden tool."""
    lines = frontmatter.splitlines()
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.lower().startswith("allowed-tools:"):
            continue
        # inline form:  allowed-tools: [Bash, AskUserQuestion]  or  allowed-tools: Bash, AskUserQuestion
        inline = stripped.split(":", 1)[1].strip()
        if FORBIDDEN_TOOL in inline:
            return True
        # block form: subsequent more-indented "- Tool" lines
        base_indent = len(line) - len(line.lstrip())
        for follow in lines[idx + 1:]:
            if not follow.strip():
                continue
            indent = len(follow) - len(follow.lstrip())
            if indent <= base_indent and follow.lstrip().startswith("-") is False:
                break  # next top-level key → end of allowed-tools block
            if follow.lstrip().startswith("-") and FORBIDDEN_TOOL in follow:
                return True
            if indent <= base_indent:
                break
        return False
    return False


def collect_targets(argv):
    if argv:
        return argv
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return sorted(glob.glob(os.path.join(root, "plugins", "*", "commands", "**", "*.md"), recursive=True))


def main(argv):
    targets = collect_targets(argv)
    violations = []
    scanned = 0
    for path in targets:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
        except OSError as exc:
            print(f"  ! could not read {path}: {exc}", file=sys.stderr)
            continue
        scanned += 1
        fm = split_frontmatter(text)
        if fm and allowed_tools_has_forbidden(fm):
            violations.append(path)

    print(f"validate_commands: scanned {scanned} command file(s)")
    if violations:
        print(f"\nFAIL — {FORBIDDEN_TOOL} found in allowed-tools (auto-approve bug):")
        for v in violations:
            print(f"  - {v}")
        print(f"\nFix: remove `{FORBIDDEN_TOOL}` from the command's `allowed-tools` frontmatter.")
        return 1
    print("OK — no AskUserQuestion in any command allowed-tools.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
