"""Git helper methods and class."""

import logging
import os
import re
from urllib.parse import quote

from git import Repo
from nautobot.extras.choices import SecretsGroupAccessTypeChoices, SecretsGroupSecretTypeChoices
from nautobot.extras.datasources.git import ensure_git_repository
from nautobot.extras.models import GitRepository, SecretsGroupAssociation

LOGGER = logging.getLogger(__name__)


def get_secret_value(secret_type, git_obj):
    """
    Get value for a secret based on secret type and device.

    Args:
        secret_type (SecretsGroupSecretTypeChoices): Type of secret to check.
        git_obj (extras.GitRepository): Nautobot git object.

    Returns:
        str: Secret value.
    """
    try:
        value = git_obj.secrets_group.get_secret_value(
            access_type=SecretsGroupAccessTypeChoices.TYPE_HTTP,
            secret_type=secret_type,
            obj=git_obj,
        )
    except SecretsGroupAssociation.DoesNotExist:
        value = None
    return value


def _get_secrets(git_obj):
    """Get Secrets Information from Associated Git Secrets Group."""
    user_token = get_secret_value(secret_type=SecretsGroupSecretTypeChoices.TYPE_USERNAME, git_obj=git_obj)
    token = get_secret_value(secret_type=SecretsGroupSecretTypeChoices.TYPE_TOKEN, git_obj=git_obj)
    return (user_token, token)


class GitRepo:  # pylint: disable=too-many-instance-attributes
    """Git Repo object to help with git actions."""

    def __init__(self, git_slug, job_result):  # noqa: D417
        """Set attributes to easily interact with Git Repositories.

        Args:
            obj (GitRepository): Django ORM object from GitRepository.
            job_result: stored job results
        """
        self.obj = GitRepository.objects.get(slug=git_slug)

        self.job_result = job_result
        self.path = self.obj.filesystem_path
        self.url = self.obj.remote_url
        self.secrets_group = self.obj.secrets_group
        if self.secrets_group:
            self.token_user, self.token = _get_secrets(self.obj)
        else:
            self.token = self.obj._token
            self.token_user = self.obj.username
        if self.token and self.token not in self.url:
            # Some Git Providers require a user as well as a token.
            if self.token_user:
                self.url = re.sub(
                    "//", f"//{quote(str(self.token_user), safe='')}:{quote(str(self.token), safe='')}@", self.url
                )
            else:
                # Github only requires the token.
                self.url = re.sub("//", f"//{quote(str(self.token), safe='')}@", self.url)

        self.branch = self.obj.branch

        if os.path.isdir(self.path):
            LOGGER.debug("Git path `%s` exists, initiate", self.path)
            self.repo = Repo(path=self.path)
        else:
            LOGGER.debug("Git path `%s` does not exists, clone", self.path)
            self.repo = Repo.clone_from(self.url, to_path=self.path)

        if self.url not in self.repo.remotes.origin.urls:
            LOGGER.debug("URL `%s` was not currently set, setting", self.url)
            self.repo.remotes.origin.set_url(self.url)

        self.refresh()

    def refresh(self):
        """Wrapper function to call ensure_git_repository to make sure that the given Git repo is present, up-to-date, and has the correct branch selected."""
        ensure_git_repository(self.obj, self.job_result)

    def commit_with_added(self, commit_description):
        """Make a force commit.

        Args:
            commit_description (str): the description of commit
        """
        LOGGER.debug("Committing with message `%s`", commit_description)
        self.repo.git.add(self.repo.untracked_files)
        self.repo.git.add(update=True)
        self.repo.index.commit(commit_description)
        LOGGER.debug("Commit completed")

    def push(self):
        """Push latest to the git repo."""
        LOGGER.debug("Push changes to repo")
        self.repo.remotes.origin.push()
