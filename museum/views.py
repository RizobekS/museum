# apps/museum/views.py
import os
from typing import Literal, Tuple, Optional

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse, Http404, HttpRequest
from django.shortcuts import get_object_or_404, render
from django.utils.translation import get_language
from django.views.generic import ListView, DetailView
from .models import Exhibit, MuseumBlock, MuseumSection

from django.views.decorators.http import require_GET
from django.utils.decorators import method_decorator
from django.views import View
from django.conf import settings

Lang = Literal["ru", "uz", "en", "ar"]


def _resolve_lang(request: HttpRequest, url_lang: Optional[str] = None) -> Lang:
    """
    Определяем язык показа:
    1) если передан в URL (ru|uz|en) — используем его;
    2) иначе — берём активный язык из Django (LocaleMiddleware / i18n).
    """
    if url_lang in {"ru", "uz", "en", "ar"}:
        return url_lang  # type: ignore
    lang = (get_language() or "ru").lower()
    return lang if lang in {"ru", "uz", "en", "ar"} else "ru"  # fallback


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
        "ar": exhibit.title_ar or exhibit.title_ru or exhibit.title_uz or exhibit.slug,
    }[lang]

    # Подзаголовки
    subtitle = {
        "ru": exhibit.sub_title_ru or exhibit.sub_title_en or exhibit.sub_title_uz or exhibit.description_ru or exhibit.slug,
        "uz": exhibit.sub_title_uz or exhibit.sub_title_ru or exhibit.sub_title_en or exhibit.description_uz or exhibit.slug,
        "en": exhibit.sub_title_en or exhibit.sub_title_ru or exhibit.sub_title_uz or exhibit.description_en or exhibit.slug,
        "ar": exhibit.sub_title_ar or exhibit.sub_title_ru or exhibit.sub_title_uz or exhibit.description_ar or exhibit.slug,
    }[lang]

    # Описание
    description = {
        "ru": exhibit.description_ru or exhibit.description_en or exhibit.description_uz or "",
        "uz": exhibit.description_uz or exhibit.description_ru or exhibit.description_en or "",
        "en": exhibit.description_en or exhibit.description_ru or exhibit.description_uz or "",
        "ar": exhibit.description_ar or exhibit.description_ru or exhibit.description_uz or "",
    }[lang]

    # Аудио (url либо None)
    audio_field = {
        "ru": exhibit.audio_ru or exhibit.audio_en or exhibit.audio_uz,
        "uz": exhibit.audio_uz or exhibit.audio_ru or exhibit.audio_en,
        "en": exhibit.audio_en or exhibit.audio_ru or exhibit.audio_uz,
        "ar": exhibit.audio_ru or exhibit.audio_en or exhibit.audio_uz,
    }[lang]
    audio_url = audio_field.url if audio_field else None

    return title, subtitle, description, audio_url


class ExhibitListView(ListView):
    """
    Список экспонатов. Показываем локализованный заголовок и короткое описание.
    Шаблон: museum/exhibit_list.html
    """

    login_url = "/accounts/login/"  # или settings.LOGIN_URL
    redirect_field_name = "next"

    model = Exhibit
    context_object_name = "exhibits"
    template_name = "museum/exhibit_list.html"
    paginate_by = 20

    def get_queryset(self):
        qs = (Exhibit.objects
              .filter(is_published=True)
              .order_by("slug"))

        museum_slug = self.kwargs.get("museum_slug")
        if museum_slug:
            qs = qs.filter(block__museum__slug__iexact=museum_slug)

        query = self.request.GET.get("q", "").strip()
        if query:
            qs = qs.filter(
                Q(title_ru__icontains=query) |
                Q(title_uz__icontains=query) |
                Q(title_en__icontains=query) |
                Q(slug__icontains=query)
            )

        block_id = self.request.GET.get("block", "").strip()
        if block_id:
            qs = qs.filter(block_id=block_id)

        section_id = self.request.GET.get("section", "").strip()
        if section_id:
            qs = qs.filter(section_id=section_id)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        lang = _resolve_lang(self.request)

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
                "first_frame_url": ex.first_frame_url(),
            })

        museum_slug = self.kwargs.get("museum_slug", "")

        # выбранные значения фильтров
        query = self.request.GET.get("q", "").strip()
        selected_block_id = self.request.GET.get("block", "").strip()
        selected_section_id = self.request.GET.get("section", "").strip()

        # список блоков (в рамках музея, если он есть)
        blocks_qs = MuseumBlock.objects.all()
        if museum_slug:
            blocks_qs = blocks_qs.filter(museum__slug__iexact=museum_slug)
        blocks_qs = blocks_qs.order_by("id")

        # список секций: если блок выбран — только его секции,
        # иначе все секции в рамках музея (чтобы начальный список не был пустой)
        if selected_block_id:
            sections_qs = MuseumSection.objects.filter(
                museum_block_id=selected_block_id
            ).order_by("code_num", "id")
        else:
            sections_qs = MuseumSection.objects.all()
            if museum_slug:
                sections_qs = sections_qs.filter(museum__slug__iexact=museum_slug)
            sections_qs = sections_qs.order_by("museum_block__slug", "code_num")

        ctx["lang"] = lang
        ctx["items"] = items
        ctx["museum_slug"] = museum_slug
        ctx["query"] = query

        ctx["blocks"] = blocks_qs
        ctx["sections"] = sections_qs
        ctx["selected_block_id"] = selected_block_id
        ctx["selected_section_id"] = selected_section_id

        return ctx

@require_GET
def sections_by_block(request):
    """
    AJAX-эндпоинт:
    GET /sections-json/?block_id=ID
    Возвращает список экспозиций для выбранного блока.
    """
    block_id = request.GET.get("block_id")
    if not block_id:
        return JsonResponse({"results": []})

    try:
        block_id_int = int(block_id)
    except (TypeError, ValueError):
        return JsonResponse({"results": []})

    lang = _resolve_lang(request)

    sections_qs = (
        MuseumSection.objects
        .filter(museum_block_id=block_id_int)
        .order_by("code_num", "id")
    )

    results = []
    for s in sections_qs:
        if lang == "uz":
            title = s.title_uz or s.title_ru or s.title_en
        elif lang == "en":
            title = s.title_en or s.title_ru or s.title_uz
        elif lang == "ar":
            title = s.title_en or s.title_ru or s.title_uz
        else:
            title = s.title_ru or s.title_uz or s.title_en

        results.append({
            "id": s.id,
            "title": f"{s.code_num} - {title}",
        })

    return JsonResponse({"results": results})



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

        video_url = ex.video.url if ex.video else ""
        video_mime = ""
        if ex.video:
            ext = os.path.splitext(ex.video.name)[1].lower()  # ".mp4"
            mime_map = {
                ".mp4": "video/mp4",
                ".webm": "video/webm",
                ".mov": "video/quicktime",
                ".avi": "video/x-msvideo",
            }
            video_mime = mime_map.get(ext, "video/mp4")

        ctx = {
            "base_url": settings.BASE_URL,
            "exhibit": ex,
            "lang": lang,
            "museum_slug": ex.block.museum.slug,
            "slug": ex.slug,
            "title_localized": title,
            "subtitle_localized": subtitle,
            "description_localized": description,
            "audio_url": audio_url,
            "is_3d": ex.is_3d,
            "frames_count": ex.frames_count(),
            "folder": ex.ci360_folder(),
            "filename_pattern": ex.ci360_filename_pattern(),
            "single_url": ex.single_image.url if ex.has_single_image() else "",
            "gallery": [p.image.url for p in ex.gallery_qs()],
            "video_url": video_url,
            "video_mime": video_mime,
        }
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
