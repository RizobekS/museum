# apps/museum/admin.py
from dal import autocomplete
from django.contrib import admin, messages
from django import forms
from django.http import JsonResponse
from django.urls import path
from django.utils.html import format_html
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .resources import *

from .models import Museum, MuseumBlock, MuseumSection, Exhibit, ExhibitPhoto

@admin.register(Museum)
class MuseumAdmin(admin.ModelAdmin):
    list_display = ("title_ru", "slug")
    search_fields = ("slug", "title_ru", "title_uz", "title_en")

@admin.register(MuseumBlock)
class MuseumBlockAdmin(admin.ModelAdmin):
    list_display = ("title_ru", "slug", "museum")
    list_filter = ("museum",)
    search_fields = ("slug", "title_ru", "title_uz", "title_en")
    fields = ("museum", "slug", "title_uz", "title_en", "title_ru", "description_uz", "description_en", "description_ru")

@admin.register(MuseumSection)
class MuseumSectionAdmin(admin.ModelAdmin):
    list_display = ("title_ru", "code_num", "museum_block", "museum")
    list_filter = ("museum", "museum_block",)
    search_fields = ("title_ru", "title_uz", "title_en")
    fields = ("museum", "museum_block", "code_num", "title_uz", "title_en", "title_ru",
              "description_uz", "description_en", "description_ru")


# --- Exhibit form c DAL ---
class ExhibitAdminForm(forms.ModelForm):
    class Meta:
        model = Exhibit
        fields = "__all__"
        widgets = {
            "section": autocomplete.ModelSelect2(
                url="section-autocomplete",
                forward=["block"],
                attrs={"data-placeholder": "---------"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        data = self.data or {}
        block_id = data.get("block") or (self.instance.block_id if getattr(self.instance, "pk", None) else None)

        if block_id:
            self.fields["section"].queryset = (
                MuseumSection.objects
                .filter(museum_block_id=block_id)
                .order_by("code_num", "id")
            )
        else:
            # Нет выбранного блока — список секций пуст
            self.fields["section"].queryset = MuseumSection.objects.none()

    def clean(self):
        cleaned = super().clean()
        block = cleaned.get("block")
        section = cleaned.get("section")
        # 2) Страховка: если пользователь как-то выбрал «чужую» секцию — отклоняем
        if block and section and section.museum_block_id != block.id:
            self.add_error("section", "Экспозиция не принадлежит выбранному блоку.")
        return cleaned

class ExhibitPhotoFrameForm(forms.ModelForm):
    class Meta:
        model = ExhibitPhoto
        fields = ("frame_index", "image", "is_active",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # до валидации модели фиксируем тип
        if self.instance and not self.instance.pk:
            self.instance.kind = "frame"

class ExhibitPhotoGalleryForm(forms.ModelForm):
    class Meta:
        model = ExhibitPhoto
        fields = ("image", "is_active",)  # без frame_index

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and not self.instance.pk:
            self.instance.kind = "gallery"


class ExhibitFrameInline(admin.TabularInline):
    model = ExhibitPhoto
    form = ExhibitPhotoFrameForm
    extra = 0
    fields = ("frame_index", "image", "preview", "is_active", "created_at")
    readonly_fields = ("preview", "created_at")
    ordering = ("frame_index",)

    def get_queryset(self, request):
        return super().get_queryset(request).filter(kind="frame")

    def preview(self, obj):
        if not getattr(obj, "image", None):
            return "-"
        try:
            url = obj.image.url
        except Exception:
            return "-"
        return format_html('<img src="{}" style="height:70px;border-radius:6px;" />', url)


class ExhibitGalleryInline(admin.TabularInline):
    model = ExhibitPhoto
    form = ExhibitPhotoGalleryForm
    extra = 0
    fields = ("image", "preview", "is_active", "created_at")
    readonly_fields = ("preview", "created_at")
    ordering = ("created_at", "id")

    def get_queryset(self, request):
        return super().get_queryset(request).filter(kind="gallery")

    def preview(self, obj):
        if not getattr(obj, "image", None):
            return "-"
        try:
            url = obj.image.url
        except Exception:
            return "-"
        return format_html('<img src="{}" style="height:70px;border-radius:6px;" />', url)


@admin.register(Exhibit)
class ExhibitAdmin(ImportExportModelAdmin):
    resource_classes = [ExhibitResource]
    form = ExhibitAdminForm
    actions = ("regenerate_qr",)

    list_display = ("title_ru", "description_ru", "slug", "block", "section", "sequence_no",
                    "is_3d", "frames_count", "is_published")
    list_filter = ("is_published", "is_3d", "block__museum", "block", "section")
    search_fields = ("slug", "title_ru", "title_uz", "title_en",
                     "description_ru", "description_uz", "description_en")
    readonly_fields = ("sequence_no", "created_at", "updated_at", "qr_code", "slug")

    fieldsets = (
        ("Связи", {"fields": ("block", "section")}),
        ("Коды", {"fields": ("slug", "sequence_no", "qr_code")}),
        ("Публикация", {"fields": ("is_published", "is_3d", "frames_required")}),
        ("Фото (если без 3D)", {"fields": ("single_image",)}),
        ("Заголовки", {"classes": ("collapse",), "fields":
            ("title_uz","title_en","title_ru","title_ar","sub_title_uz","sub_title_en","sub_title_ru","sub_title_ar")}),
        ("Описания", {"classes": ("collapse",), "fields":
            ("description_uz","description_en","description_ru","description_ar")}),
        ("Аудио", {"fields": ("audio_uz","audio_en","audio_ru")}),
        ("Служебное", {"classes": ("collapse",), "fields": ("created_at","updated_at")}),
    )

    def get_inlines(self, request, obj=None):
        if obj and obj.is_3d:
            return [ExhibitFrameInline]
        # если карточка новая (obj is None) — покажем инлайн галереи,
        # а после сохранения переключится в зависимости от чекбокса is_3d
        return [ExhibitGalleryInline]

    def regenerate_qr(self, request, queryset):
        count = 0
        for ex in queryset:
            # заново сгенерируем файл и сохраним
            ex.qr_code.delete(save=False)
            ex._generate_qr()
            ex.save(update_fields=["qr_code"])
            count += 1
        self.message_user(request, f"QR обновлён для {count} экспонатов.", level=messages.SUCCESS)

    regenerate_qr.short_description = "Перегенерировать QR"
