import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_commits import check_commit_files, check_message


VALID_FEAT = """\
feat(session): 新一轮会取消上一轮播放

验证：pytest tests/test_session.py::test_new_turn_cancels_previous -q
"""

VALID_DOCS = """\
docs(commit): 补充提交记录的阅读方式

验证：pytest -q
"""


def test_feat_message_names_a_specific_test():
    assert check_message(VALID_FEAT) == []


def test_docs_message_can_run_the_full_suite():
    assert check_message(VALID_DOCS) == []


def test_feat_rejects_a_vague_subject_and_a_generic_pytest_command():
    message = """\
feat: 修复

验证：pytest -q
"""
    errors = check_message(message)
    assert any("具体行为" in item for item in errors)
    assert any("点名测试" in item for item in errors)


def test_message_requires_a_verification_command():
    message = """\
docs(commit): 补充提交记录的阅读方式

这里没有验证命令
"""
    errors = check_message(message)
    assert any("验证" in item for item in errors)


def test_git_log_keeps_the_chinese_verification_line():
    from check_commits import _commit_message, _git

    message = _commit_message(_git("rev-parse", "HEAD"))
    assert "验证：" in message


def test_feat_commit_must_include_the_named_test_file():
    errors = check_commit_files(VALID_FEAT, ["session.py"])
    assert errors

    included = check_commit_files(VALID_FEAT, ["session.py", "tests/test_session.py"])
    assert included == []
