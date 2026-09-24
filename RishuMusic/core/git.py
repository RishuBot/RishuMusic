import asyncio
import shlex
from typing import Tuple

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError

import config

from ..logging import LOGGER


def install_req(cmd: str) -> Tuple[str, str, int, int]:
    async def install_requirements():
        args = shlex.split(cmd)
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        return (
            stdout.decode("utf-8", "replace").strip(),
            stderr.decode("utf-8", "replace").strip(),
            process.returncode,
            process.pid,
        )

    return asyncio.get_event_loop().run_until_complete(install_requirements())


def _build_upstream_url() -> str:
    """Upstream URL, with token embedded if GIT_TOKEN is set."""
    repo_link = config.UPSTREAM_REPO
    if config.GIT_TOKEN and repo_link and "https://" in repo_link and "com/" in repo_link:
        git_username = repo_link.split("com/")[1].split("/")[0]
        temp_repo = repo_link.split("https://")[1]
        return f"https://{git_username}:{config.GIT_TOKEN}@{temp_repo}"
    return repo_link


def _update_from_upstream(repo: Repo, upstream_repo: str):
    """First-boot setup: fetch upstream, checkout branch, pull, install requirements."""
    if "origin" in repo.remotes:
        origin = repo.remote("origin")
    else:
        origin = repo.create_remote("origin", upstream_repo)
    origin.fetch()
    repo.create_head(
        config.UPSTREAM_BRANCH,
        origin.refs[config.UPSTREAM_BRANCH],
    )
    repo.heads[config.UPSTREAM_BRANCH].set_tracking_branch(
        origin.refs[config.UPSTREAM_BRANCH]
    )
    repo.heads[config.UPSTREAM_BRANCH].checkout(True)
    try:
        repo.create_remote("origin", config.UPSTREAM_REPO)
    except BaseException:
        pass
    nrs = repo.remote("origin")
    nrs.fetch(config.UPSTREAM_BRANCH)
    try:
        nrs.pull(config.UPSTREAM_BRANCH)
    except GitCommandError:
        repo.git.reset("--hard", "FETCH_HEAD")
    install_req("pip3 install --no-cache-dir -r requirements.txt")
    LOGGER(__name__).info("Fetching updates from upstream repository...")


def git():
    upstream_repo = _build_upstream_url()
    try:
        repo = Repo()
        LOGGER(__name__).info("Git Client Found [VPS DEPLOYER]")
    except GitCommandError:
        LOGGER(__name__).info("Invalid Git Command")
    except InvalidGitRepositoryError:
        repo = Repo.init()
        if not upstream_repo:
            LOGGER(__name__).warning(
                "UPSTREAM_REPO is not set - skipping auto-update."
            )
            return
        try:
            _update_from_upstream(repo, upstream_repo)
        except Exception as ex:
            # Private repo without GIT_TOKEN, wrong branch, no network, etc.
            # Don't crash the bot - just skip the auto-update.
            LOGGER(__name__).warning(
                f"Upstream update skipped ({type(ex).__name__}). "
                "Set GIT_TOKEN (and a correct UPSTREAM_REPO/UPSTREAM_BRANCH) "
                "if you want auto-update."
            )
