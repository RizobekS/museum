# apps/museum/views.py
from typing import Literal, Tuple, Optional
from django.http import JsonResponse, Http404, HttpRequest
from django.shortcuts import get_object_or_404, render
from django.utils.translation import get_language
from django.views.generic import ListView, DetailView
from .models import Exhibit

from django.views.decorators.http import require_GET
from django.utils.decorators import method_decorator
from django.views import View

Lang = Literal["ru", "uz", "en"]


def _resolve_lang(request: HttpRequest, url_lang: Optional[str] = None) -> Lang:
    """
    Определяем язык показа:
    1) если передан в URL (ru|uz|en) — используем его;
    2) иначе — берём активный язык из Django (LocaleMiddleware / i18n).
    """
    if url_lang in {"ru", "uz", "en"}:
        return url_lang  # type: ignore
    lang = (get_language() or "ru").split("-")[0].lower()
    return lang if lang in {"ru", "uz", "en"} else "ru"  # fallback


def _localized_content(exhibit: Exhibit, lang: Lang) -> Tuple[str, str, str, Optional[str]]:
    """
    Возвращает (title, description, audio_url) c учётом языка и разумных фолбэков.
    Логика:
      - если поле на выбранном языке пустое, падаем на RU, потом на EN.
      - для аудио — аналогично.
    """
    # Заголовок
    title = {
        "ru": exhibit.title_ru or exhibit.title_en or exhibit.title_uz or exhibit.slug,
        "uz": exhibit.title_uz or exhibit.title_ru or exhibit.title_en or exhibit.slug,
        "en": exhibit.title_en or exhibit.title_ru or exhibit.title_uz or exhibit.slug,
    }[lang]

    # Подзаголовки
    subtitle = {
        "ru": exhibit.sub_title_ru or exhibit.sub_title_en or exhibit.sub_title_uz or exhibit.slug,
        "uz": exhibit.sub_title_uz or exhibit.sub_title_ru or exhibit.sub_title_en or exhibit.slug,
        "en": exhibit.sub_title_en or exhibit.sub_title_ru or exhibit.sub_title_uz or exhibit.slug,
    }[lang]

    # Описание
    description = {
        "ru": exhibit.description_ru or exhibit.description_en or exhibit.description_uz or "",
        "uz": exhibit.description_uz or exhibit.description_ru or exhibit.description_en or "",
        "en": exhibit.description_en or exhibit.description_ru or exhibit.description_uz or "",
    }[lang]

    # Аудио (url либо None)
    audio_field = {
        "ru": exhibit.audio_ru or exhibit.audio_en or exhibit.audio_uz,
        "uz": exhibit.audio_uz or exhibit.audio_ru or exhibit.audio_en,
        "en": exhibit.audio_en or exhibit.audio_ru or exhibit.audio_uz,
    }[lang]
    audio_url = audio_field.url if audio_field else None

    return title, subtitle, description, audio_url


class ExhibitListView(ListView):
    """
    Список экспонатов. Показываем локализованный заголовок и короткое описание.
    Шаблон: museum/exhibit_list.html
    """
    model = Exhibit
    context_object_name = "exhibits"
    template_name = "museum/exhibit_list.html"
    paginate_by = 20

    def get_queryset(self):
        return (Exhibit.objects
                .filter(is_published=True)
                .order_by("slug"))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        lang = _resolve_lang(self.request)
        # Примешиваем локализованные поля для карточек
        items = []
        for ex in ctx["exhibits"]:
            title, subtitle, desc, audio_url = _localized_content(ex, lang)
            items.append({
                "obj": ex,
                "title": title,
                "qr": ex.qr_code,
                "subtitle": subtitle,
                "description": desc,
                "audio_url": audio_url,
                "is_3d": ex.is_3d,
                "single_url": ex.single_image.url if ex.has_single_image() else "",
                "frames_count": ex.frames_count(),
                "folder": ex.ci360_folder(),
                "filename_pattern": ex.ci360_filename_pattern(),
                "first_frame_url": ex.first_frame_url(),
            })
        ctx["lang"] = lang
        ctx["items"] = items
        return ctx


class ExhibitDetailByCodesView(View):
    """
    Детальная страница по QR-маршруту: /<museum_code>/<exhibit_code>
    Пример: /ISC/ISC-REN2-1.0001
    """
    template_name = "museum/exhibit_detail.html"

    def get(self, request, museum_code: str, exhibit_code: str, *args, **kwargs):
        ex = get_object_or_404(Exhibit, slug=exhibit_code, is_published=True)
        if ex.block.museum.slug != museum_code:
            raise Http404("Exhibit not in this museum")

        lang = _resolve_lang(request)
        title, subtitle, description, audio_url = _localized_content(ex, lang)
        ctx = {
            "exhibit": ex,
            "lang": lang,
            "museum_slug": ex.block.museum.slug,
            "slug": ex.slug,
            "title_localized": title,
            "subtitle_localized": subtitle,
            "description_localized": description,
            "audio_url": audio_url,
            "frames_count": ex.frames_count(),
            "folder": ex.ci360_folder(),
            "filename_pattern": ex.ci360_filename_pattern(),
        }
        ctx.update({
            "is_3d": ex.is_3d,
            "single_url": ex.single_image.url if ex.has_single_image() else "",
        })
        return  render(request, self.template_name, ctx)


# --- API/сервисный эндпоинт: JSON манифест для 360 ----



@method_decorator(require_GET, name="dispatch")
class ExhibitCi360Manifest(View):
    """
    GET /exhibits/api/<slug>/ci360.json
    Возвращает короткий JSON для инициализации виджета (на случай, если
    захотите инициализировать Cloudimage 360 через JS).
    """
    def get(self, request, slug: str):
        exhibit = get_object_or_404(Exhibit, slug=slug, is_published=True)
        data = {
            "slug": exhibit.slug,
            "frames": exhibit.frames_count(),
            "folder": exhibit.ci360_folder(),
            "filename": exhibit.ci360_filename_pattern(),
        }
        return JsonResponse(data)
