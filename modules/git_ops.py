"""
Git Operations Module — Status, commit, push, pull, branch management.
"""

import subprocess
from pathlib import Path


def _run_git(args: list[str], cwd: str = ".") -> str:
    """Run a git command and return output."""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True, text=True, timeout=30,
            cwd=cwd,
        )
        output = result.stdout.strip()
        error = result.stderr.strip()
        if result.returncode != 0:
            return f"Git error: {error or output}"
        return output or "(no output)"
    except FileNotFoundError:
        return "Git is not installed or not in PATH."
    except subprocess.TimeoutExpired:
        return "Git command timed out."
    except Exception as e:
        return f"Git error: {e}"


def git_status(repo_path: str = ".") -> str:
    """Get git repository status."""
    return _run_git(["status", "--short", "--branch"], repo_path)


def git_log(repo_path: str = ".", count: int = 10) -> str:
    """Get recent git commits."""
    return _run_git(
        ["log", f"-{count}", "--oneline", "--graph", "--decorate"],
        repo_path,
    )


def git_diff(repo_path: str = ".") -> str:
    """Show git diff of unstaged changes."""
    diff = _run_git(["diff", "--stat"], repo_path)
    return diff if diff else "No unstaged changes."


def git_commit(message: str, repo_path: str = ".") -> str:
    """Stage all changes and commit."""
    add_result = _run_git(["add", "-A"], repo_path)
    if "error" in add_result.lower():
        return f"Failed to stage: {add_result}"
    return _run_git(["commit", "-m", message], repo_path)


def git_push(repo_path: str = ".", remote: str = "origin", branch: str = "") -> str:
    """Push to remote."""
    args = ["push", remote]
    if branch:
        args.append(branch)
    return _run_git(args, repo_path)


def git_pull(repo_path: str = ".", remote: str = "origin", branch: str = "") -> str:
    """Pull from remote."""
    args = ["pull", remote]
    if branch:
        args.append(branch)
    return _run_git(args, repo_path)


def git_branch(repo_path: str = ".") -> str:
    """List branches."""
    return _run_git(["branch", "-a"], repo_path)


def git_checkout(branch: str, repo_path: str = ".", create: bool = False) -> str:
    """Switch or create branch."""
    args = ["checkout"]
    if create:
        args.append("-b")
    args.append(branch)
    return _run_git(args, repo_path)


def git_clone(url: str, dest: str = "") -> str:
    """Clone a repository."""
    args = ["clone", url]
    if dest:
        args.append(dest)
    return _run_git(args, ".")


def git_stash(action: str = "push", repo_path: str = ".") -> str:
    """Stash or pop changes."""
    return _run_git(["stash", action], repo_path)


def git_operation(operation: str, repo_path: str = ".", **kwargs) -> str:
    """Unified git operation handler."""
    ops = {
        "status": lambda: git_status(repo_path),
        "log": lambda: git_log(repo_path, kwargs.get("count", 10)),
        "diff": lambda: git_diff(repo_path),
        "commit": lambda: git_commit(kwargs.get("message", "Auto commit"), repo_path),
        "push": lambda: git_push(repo_path),
        "pull": lambda: git_pull(repo_path),
        "branch": lambda: git_branch(repo_path),
        "checkout": lambda: git_checkout(kwargs.get("branch", "main"), repo_path, kwargs.get("create", False)),
        "clone": lambda: git_clone(kwargs.get("url", ""), kwargs.get("dest", "")),
        "stash": lambda: git_stash(kwargs.get("action", "push"), repo_path),
    }
    handler = ops.get(operation)
    if handler:
        return handler()
    return f"Unknown git operation: {operation}. Available: {', '.join(ops.keys())}"
