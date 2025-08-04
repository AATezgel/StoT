from django import template

register = template.Library()

@register.filter
def sub(value, arg):
    """Subtracts the arg from the value."""
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def percentage(value, total):
    """Calculates percentage of value from total."""
    try:
        if total == 0:
            return 0
        return round((float(value) / float(total)) * 100, 1)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0
