from django import template

register = template.Library()

@register.filter
def dictget(d, key):
    """Get value from dictionary by key in template."""
    # <QuerySet [<Product: Redmi>, <Product: iphone>]>
    return d.get(key)
