#!/usr/bin/env python3

import re
import sys
from typing import List

from subprocess import CalledProcessError, run


def run_cmd(cmd: List[str]) -> List[str]:
    result = run(cmd, check=True, capture_output=True, text=True)
    return [line.strip() for line in result.stdout.split("\n") if len(line.strip())]


def merge_will_produce_changes(main_branch: str, dev_branch: str) -> bool:
    merge_base = run(
        ["git", "merge-base", main_branch, dev_branch],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    merge_result = run_cmd(["git", "merge-tree", merge_base, main_branch, dev_branch])

    merge_has_changes = False
    for line in merge_result:
        if line.startswith("+") or line.startswith("-"):
            merge_has_changes = True

    return merge_has_changes


def local_branches(main_branch: str) -> List[str]:
    branches = [b.replace("*", "").strip() for b in run_cmd(["git", "branch"])]
    branches = [b for b in branches if b != main_branch]
    return branches


def prompt_yes_no() -> bool:
    return input().strip().lower() == "y"


def delete_branch(branch: str, force: bool = False) -> None:
    args = ["git", "branch", "--delete"]
    if force:
        args.append("--force")
    args.append(branch)
    run(args, check=True)


def get_main_branch_for_remote(remote: str) -> str:
    """
    Query a remote to determine the main ("HEAD") branch name.

    This will not work if offline.
    """
    remote_info = run_cmd(["git", "remote", "show", remote])
    for line in remote_info:
        if line.startswith("HEAD branch:"):
            _, branch = line.split(":", 1)
            branch = branch.strip()
            return branch
    raise Exception("HEAD branch information not found")


# nb. In Python >= 3.9, `str.removeprefix(prefix)` can be used instead.
def remove_prefix(str_: str, prefix: str) -> str:
    if str_.startswith(prefix):
        return str_[len(prefix) :]
    else:
        return str_


IGNORED_BRANCHES = ["gh-pages"]


# Make sure we only run this on the main branch, otherwise we'd most likely
# end up deleting it if run on a topic branch.
default_remote = "origin"
main_branch = get_main_branch_for_remote(default_remote)

try:
    run(["git", "checkout", "--quiet", main_branch], check=True)
except CalledProcessError:
    print(f"Could not switch to {main_branch} branch")
    sys.exit(1)

# Delete all branches that are cleanly merged into main. Other branches may
# require rebasing.
merged_branches = run_cmd(["git", "branch", "--merged"])
merged_branches = [b.strip() for b in merged_branches]
merged_branches = [b for b in merged_branches if b and not b.startswith("*")]

for branch in merged_branches:
    if branch in IGNORED_BRANCHES:
        continue
    try:
        # nb. This will print the branch name and commit hash, so we don't need
        # to do that ourselves.
        delete_branch(branch, force=False)
    except CalledProcessError:
        print(f"Could not delete {branch} automatically")

# Delete all branches that would not produce any changes if merged into main.
for branch in local_branches(main_branch):
    if branch in IGNORED_BRANCHES:
        continue
    merge_has_changes = True
    try:
        merge_has_changes = merge_will_produce_changes(main_branch, branch)
    except Exception as ex:
        print(f"Failed to generate merge preview for {branch}", str(ex))

    if not merge_has_changes:
        print(
            f"Merging {branch} into {main_branch} would not produce any changes. Delete it? [y/n]"
        )
        if prompt_yes_no():
            delete_branch(branch, force=True)


# Prune remote tracking branches.
run_cmd(["git", "remote", "prune", default_remote])

# Find local branches which track remote branches that have no longer exist
# and prompt to remove them.
GONE_PATTERN = r"\[.*: gone\]"
gone_branches = [
    # `git branch -vv` outputs lines of the form:
    # `{branch name} {short hash} [{tracking remote}] {commit message}` with
    # ": gone" in the tracking remote name if the branch has been deleted.
    line
    for line in run_cmd(["git", "branch", "-vv"])
    if re.search(GONE_PATTERN, line)
]
gone_branches = [line.strip().split(" ")[0] for line in gone_branches]

for branch in gone_branches:
    print(f"Branch {branch} tracks removed remote branch. Delete it? [y/n]")
    if prompt_yes_no():
        delete_branch(branch, force=True)
