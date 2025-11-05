# config/views.py
from django.conf import settings
from django.http import HttpResponseRedirect
from django.views import View
from django.utils.translation import activate, get_supported_language_variant
try:
    from django.utils.translation import LANGUAGE_SESSION_KEY
except Exception:
    LANGUAGE_SESSION_KEY = settings.LANGUAGE_COOKIE_NAME

class ActivateLanguageView(View):
    def get(self, request, lang):
        next_url = request.GET.get("next", request.META.get("HTTP_REFERER", "/"))

        try:
            lang_code = get_supported_language_variant(lang, strict=False)
        except Exception:
            lang_code = settings.LANGUAGE_CODE

        activate(lang_code)

        resp = HttpResponseRedirect(next_url)
        resp.set_cookie(
            key=settings.LANGUAGE_COOKIE_NAME,
            value=lang_code,
            max_age=60 * 60 * 24 * 365,  # 1 год
            samesite="Lax",
        )

        if hasattr(request, "session"):
            request.session[LANGUAGE_SESSION_KEY] = lang_code

        return resp
