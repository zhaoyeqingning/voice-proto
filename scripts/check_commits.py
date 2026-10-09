#!/usr/bin/env python3
"""检查提交说明，并在 --walk 时确认每一次提交单独检出后测试仍然通过。"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STRICT_TYPES = {"feat", "fix", "test"}
SUBJECT_RE = re.compile(
    r"^(feat|fix|test|refactor|docs|chore)(\([a-z0-9-]+\))?: (\S.*)$"
)
VERIFY_RE = re.compile(r"^验证[:：]\s*(\S.*?)\s*$", re.MULTILINE)
VAGUE_RE = re.compile(
    r"^(更新|修改|修复|调整|优化|完善|提交|update|fix|wip|tmp)$",
    re.IGNORECASE,
)
WIP_RE = re.compile(r"\bWIP\b|临时提交", re.IGNORECASE)
SPECIFIC_TEST_RE = re.compile(r"(tests/\S+\.py|::)")
NAMED_TEST_RE = re.compile(r"tests/\S+?\.py")


def check_message(text: str) -> list[str]:
    """返回这条提交说明违反规范的地方。合格时返回空列表。"""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return ["提交说明是空的"]

    lines = normalized.split("\n")
    subject = lines[0].strip()
    match = SUBJECT_RE.match(subject)
    if match is None:
        return [
            "标题需写成「类型(范围): 做了什么」。"
            "类型只限 feat、fix、test、refactor、docs、chore"
        ]

    kind = match.group(1)
    description = match.group(3).strip()
    errors: list[str] = []
    if len(subject) > 72:
        errors.append(f"标题超过 72 个字符（当前 {len(subject)}）")
    if len(description) < 4:
        errors.append("标题里的说明至少 4 个字")
    if VAGUE_RE.match(description) or WIP_RE.search(subject):
        errors.append("标题要写出具体行为，不能只用「更新」「修复」或 WIP")
    if len(lines) < 2 or lines[1].strip() != "":
        errors.append("标题和正文之间要空一行")

    body = "\n".join(lines[2:]) if len(lines) > 2 else ""
    found = VERIFY_RE.search(body)
    if found is None:
        errors.append("正文需要一行「验证：」并写上可执行的命令")
        return errors

    command = found.group(1)
    if "pytest" not in command:
        errors.append("验证命令需要运行 pytest")
    if kind in STRICT_TYPES and SPECIFIC_TEST_RE.search(command) is None:
        errors.append("feat、fix、test 的验证命令要点名测试文件或具体测试，不能只写 pytest -q")
    return errors


def check_commit_files(text: str, files: list[str]) -> list[str]:
    """feat、fix、test 必须纳入验证命令点名的测试文件。"""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []
    match = SUBJECT_RE.match(normalized.split("\n", 1)[0].strip())
    if match is None or match.group(1) not in STRICT_TYPES:
        return []

    body = normalized.split("\n", 2)[-1] if "\n" in normalized else ""
    found = VERIFY_RE.search(body)
    command = found.group(1) if found else ""
    named = [path.replace("\\", "/") for path in NAMED_TEST_RE.findall(command)]
    changed = [path.replace("\\", "/") for path in files]
    changed_tests = [path for path in changed if path.startswith("tests/") and path.endswith(".py")]
    if not changed_tests:
        return ["feat、fix、test 的提交里要包含这次改动的测试文件（tests/ 下的 .py）"]
    missing = [path for path in named if path not in changed]
    if missing:
        return ["验证命令点名的测试文件不在这次提交里：" + "、".join(missing)]
    return []


def _git(*args: str, check: bool = True) -> str:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    result = subprocess.run(
        ["git", "-c", "i18n.logOutputEncoding=utf-8", *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=check,
        env=env,
    )
    return (result.stdout or "").strip()


def _commit_message(sha: str) -> str:
    return _git("log", "-1", "--format=%B", sha)


def _commit_files(sha: str) -> list[str]:
    output = _git("diff-tree", "--root", "--no-commit-id", "--name-only", "-r", sha)
    return [line for line in output.splitlines() if line]


def _resolve_base(explicit: str | None) -> str | None:
    base = explicit or os.environ.get("BASE") or os.environ.get("BEFORE") or ""
    base = base.strip()
    if not base or set(base) <= {"0"}:
        return None
    return base


def walk(base: str | None) -> list[str]:
    """逐条检出并运行 pytest。工作区有未提交内容时拒绝执行。"""
    status = _git("status", "--porcelain")
    if status:
        return ["工作区还有未提交内容，不能逐条检出检查"]

    if base is None:
        revisions = _git("rev-list", "--reverse", "--no-merges", "HEAD")
    else:
        revisions = _git("rev-list", "--reverse", "--no-merges", f"{base}..HEAD")
    shas = [line for line in revisions.splitlines() if line]
    if not shas:
        return ["这次推送里没有需要检查的提交"]

    branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    original = _git("rev-parse", "HEAD")
    failures: list[str] = []
    try:
        for sha in shas:
            message = _commit_message(sha)
            subject = message.splitlines()[0] if message else sha
            problems = check_message(message) + check_commit_files(message, _commit_files(sha))
            _git("checkout", "--force", sha)
            tests = subprocess.run(
                [sys.executable, "-m", "pytest", "-q"],
                cwd=ROOT,
            )
            if tests.returncode != 0:
                problems.append("单独检出后 pytest 未通过")
            if problems:
                failures.append(f"{sha[:7]} {subject}\n" + "\n".join(f"- {item}" for item in problems))
    finally:
        restore = branch if branch != "HEAD" else original
        subprocess.run(["git", "checkout", "--force", restore], cwd=ROOT, check=False)
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="检查提交是否独立可测")
    parser.add_argument("--message-file", type=Path, help="检查单条提交说明文件")
    parser.add_argument("--walk", action="store_true", help="逐条检出并运行测试")
    parser.add_argument("--base", help="只检查这个提交之后的新提交")
    args = parser.parse_args(argv)

    if args.message_file:
        message = args.message_file.read_text(encoding="utf-8")
        errors = check_message(message)
    elif args.walk:
        errors = walk(_resolve_base(args.base))
    else:
        parser.error("请指定 --message-file 或 --walk")

    if errors:
        print("\n\n".join(errors))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
