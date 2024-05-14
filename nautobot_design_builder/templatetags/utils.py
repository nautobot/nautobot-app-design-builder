"""Jinja filters for design_builder."""

from django import template
from django_jinja import library


register = template.Library()


@library.filter()
@register.filter()
def get_last_journal(deployment):
    """Get last run journal in a design instance."""
    return deployment.journals.order_by("last_updated").last()
