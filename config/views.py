from django.http import HttpResponseRedirect
from django.utils.translation import activate
from django.views import View
from urllib.parse import urlparse, urlunparse
from django.urls import resolve, reverse
from django.conf import settings
from django.shortcuts import redirect


class ActivateLanguageView(View):

    def get(self, request, lang):
        next_url = request.GET.get('next') or request.META.get('HTTP_REFERER') or '/'
        parsed = urlparse(next_url)

        if parsed.netloc and parsed.netloc != request.get_host():
            parsed = parsed._replace(path='/', netloc='')

        path = parsed.path
        parts = path.split('/')

        if len(parts) > 1 and parts[1] in dict(settings.LANGUAGES).keys():
            parts[1] = lang
        else:
            parts.insert(1, lang)
        new_path = '/'.join(parts)

        new_parsed = parsed._replace(path=new_path)
        redirect_url = urlunparse(new_parsed)

        activate(lang)
        response = HttpResponseRedirect(redirect_url)
        response.set_cookie(settings.LANGUAGE_COOKIE_NAME, lang)
        return response

        activate(lang)
        response = HttpResponseRedirect(next_url)
        response.set_cookie(settings.LANGUAGE_COOKIE_NAME, lang)
        return response

