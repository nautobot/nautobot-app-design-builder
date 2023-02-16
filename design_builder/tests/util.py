"""Utilities for setting up tests and test data."""
from os import getenv

from nautobot.extras.models import GitRepository


def ensure_git_repo(name, slug, url, provides):
    """Ensure that a git repo is created in Nautobot.

    Args:
        name (str): Name of the repo.
        slug (str): Repo slug.
        url (str): URL for the git repo.
        provides (str): data provided (e.g. extras.jobs).
    """
    try:
        GitRepository.objects.get(slug=slug)
    except GitRepository.DoesNotExist:
        git_repo = GitRepository(
            name=name,
            slug=slug,
            remote_url=url,
            branch="main",
            provided_contents=provides,
        )
        git_repo.save(trigger_resync=False)


def populate_sample_data():
    """Populate the database with some sample data."""
    git_slug = getenv("DESIGN_BUILDER_CONTEXT_REPO_SLUG")
    ensure_git_repo(
        "Config Contexts",
        git_slug,
        getenv("DESIGN_BUILDER_GIT_SERVER") + "/" + getenv("DESIGN_BUILDER_CONTEXT_REPO"),
        "extras.configcontext",
    )
    ensure_git_repo(
        "Designs",
        "designs",
        getenv("DESIGN_BUILDER_GIT_SERVER") + "/" + getenv("DESIGN_BUILDER_DESIGN_REPO"),
        "extras.jobs",
    )
