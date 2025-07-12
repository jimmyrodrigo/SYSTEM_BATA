from django import template
from urllib.parse import urlencode

register = template.Library()

@register.simple_tag
def querystring(request, **kwargs):
    params = request.GET.copy()
    for key, value in kwargs.items():
        params[key] = value
    return params.urlencode()
