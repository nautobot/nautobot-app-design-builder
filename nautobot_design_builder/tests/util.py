"""Utilities for setting up tests and test data."""
from django.contrib.contenttypes.models import ContentType
from nautobot.extras.models import JobResult, Job
from nautobot.tenancy.models import Tenant

from nautobot_design_builder.models import Design, DesignInstance, Journal, JournalEntry


def populate_sample_data():
    """Populate the database with some sample data."""
    job = Job.objects.get(name="Initial Data")
    job_result, _ = JobResult.objects.get_or_create(
        name="Test", obj_type=ContentType.objects.get_for_model(Job), job_id=job.pk
    )

    design, _ = Design.objects.get_or_create(job=job)
    design_instance, _ = DesignInstance.objects.get_or_create(design=design, name="Initial Data", owner="Test User")
    Journal.objects.get_or_create(design_instance=design_instance, job_result=job_result)


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
