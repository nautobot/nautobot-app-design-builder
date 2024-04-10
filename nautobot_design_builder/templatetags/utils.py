"""Jinja filters for design_builder."""

from django import template
from django_jinja import library


register = template.Library()


@library.filter()
@register.filter()
def get_last_journal(design_instance):
    """Get last run journal in a design instance."""
    return design_instance.journals.order_by("created").last()
