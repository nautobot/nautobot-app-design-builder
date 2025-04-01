"""Jinja filters for design_builder."""

from django import template
from django_jinja import library

register = template.Library()


@library.filter()
@register.filter()
def get_last_change_set(deployment):
    """Get last run change set in a design instance."""
    return deployment.change_sets.order_by("last_updated").last()
