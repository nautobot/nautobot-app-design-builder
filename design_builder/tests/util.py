"""Utilities for setting up tests and test data."""
from os import getenv

from django.contrib.contenttypes.models import ContentType
from nautobot.extras.models import GitRepository, JobResult, Job
from nautobot.tenancy.models import Tenant

from design_builder.models import Design, DesignInstance, Journal, JournalEntry
from design_builder.util import nautobot_version


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
        if nautobot_version < "2.0.0":
            git_repo.save(trigger_resync=False)  # pylint: disable=unexpected-keyword-arg
        else:
            git_repo.save()


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

    job = Job.objects.get(name="Initial Data")
    job_result, _ = JobResult.objects.get_or_create(
        name="Test", obj_type=ContentType.objects.get_for_model(Job), job_id=job.pk
    )

    design, _ = Design.objects.get_or_create(job=job)
    design_instance, _ = DesignInstance.objects.get_or_create(design=design, name="Initial Data", owner="Test User")
    journal, _ = Journal.objects.get_or_create(design_instance=design_instance, job_result=job_result)


def create_test_view_data():
    """Creates test data for view and API view test cases."""
    owners = [
        "Peter Müller",
        "Maria Meyer",
        "Otto Fischer",
    ]
    for i in range(1, 4):
        # Core models
        job = Job.objects.create(name=f"Fake Design Job {i}")
        job_result = JobResult.objects.create(
            name=f"Test Result {i}", obj_type=ContentType.objects.get_for_model(Job), job_id=job.pk
        )
        object_created_by_job = Tenant.objects.create(name=f"Tenant {i}")

        # Design Builder models
        design = Design.objects.create(job=job)
        instance = DesignInstance.objects.create(design=design, name=f"Test Instance {i}", owner=owners[i - 1])
        journal = Journal.objects.create(design_instance=instance, job_result=job_result)
        full_control = i == 1  # Have one record where full control is given, more than one where its not.
        JournalEntry.objects.create(journal=journal, design_object=object_created_by_job, full_control=full_control)
