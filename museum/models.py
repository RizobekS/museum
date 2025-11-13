# apps/museum/models.py
from django.core.exceptions import ValidationError
from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.urls import reverse
from uuid import uuid4
import os
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import qrcode

# ---------------------- базовые сущности ----------------------

class Museum(models.Model):
    slug = models.SlugField(_("Код музея (slug)"), unique=True, max_length=32,
                            help_text=_("Напр.: ISC"))
    # названия
    title_ru = models.CharField(_("Название (RU)"), max_length=255)
    title_uz = models.CharField(_("Название (UZ)"), max_length=255, blank=True, default="")
    title_en = models.CharField(_("Название (EN)"), max_length=255, blank=True, default="")
    # описания
    description_ru = models.TextField(_("Описание (RU)"), blank=True, default="")
    description_uz = models.TextField(_("Описание (UZ)"), blank=True, default="")
    description_en = models.TextField(_("Описание (EN)"), blank=True, default="")

    class Meta:
        verbose_name = _("Музей")
        verbose_name_plural = _("Музеи")
        ordering = ["slug"]

    def __str__(self):
        return f"{self.title_ru} — {self.slug}"


class MuseumBlock(models.Model):
    museum = models.ForeignKey(Museum, on_delete=models.CASCADE, related_name="blocks",
                               verbose_name=_("Музей"))
    slug = models.SlugField(_("Код блока (slug)"), max_length=32,
                            help_text=_("Напр.: REN2"))
    # названия
    title_ru = models.CharField(_("Название (RU)"), max_length=255)
    title_uz = models.CharField(_("Название (UZ)"), max_length=255, blank=True, default="")
    title_en = models.CharField(_("Название (EN)"), max_length=255, blank=True, default="")
    # описания
    description_ru = models.TextField(_("Описание (RU)"), blank=True, default="")
    description_uz = models.TextField(_("Описание (UZ)"), blank=True, default="")
    description_en = models.TextField(_("Описание (EN)"), blank=True, default="")

    class Meta:
        verbose_name = _("Блок")
        verbose_name_plural = _("Блоки")
        unique_together = (("museum", "slug"),)
        ordering = ["id", "museum__slug", "slug"]

    def __str__(self):
        return f"{self.title_ru} - {self.slug}"


class MuseumSection(models.Model):
    museum = models.ForeignKey(Museum, on_delete=models.CASCADE, related_name="sections",
                               verbose_name=_("Музей"))
    museum_block = models.ForeignKey(MuseumBlock, on_delete=models.CASCADE, related_name="museum_block",
                               verbose_name=_("Блок"), null=True)
    code_num = models.PositiveIntegerField(_("Номер экспозиции"), default=0)

    title_ru = models.CharField(_("Название (RU)"), max_length=255)
    title_uz = models.CharField(_("Название (UZ)"), max_length=255, blank=True, default="")
    title_en = models.CharField(_("Название (EN)"), max_length=255, blank=True, default="")
    description_ru = models.TextField(_("Описание (RU)"), blank=True, default="")
    description_uz = models.TextField(_("Описание (UZ)"), blank=True, default="")
    description_en = models.TextField(_("Описание (EN)"), blank=True, default="")

    class Meta:
        verbose_name = _("Экспозиция")
        verbose_name_plural = _("Экспозиции")
        ordering = ["museum_block__slug", "code_num"]

    def __str__(self):
        return f"{self.code_num} - {self.title_ru}"

# ---------------------- вспомогательные upload_to ----------------------

def single_upload_to(instance, filename):
    ext = filename.split('.')[-1].lower()
    return f"exhibits/{instance.slug}/single/single.{ext}"

def frame_upload_to(instance, filename):
    ext = filename.split('.')[-1].lower()
    if instance.kind == "gallery":
        return f"exhibits/{instance.exhibit.slug}/gallery/{uuid4()}.{ext}"
    idx = f"{(instance.frame_index or 0):03d}"
    return f"exhibits/{instance.exhibit.slug}/frames/frame-{idx}.{ext}"

def audio_upload_to(instance, filename):
    ext = filename.split('.')[-1].lower()
    return f"exhibits/{instance.slug}/audio/{instance._current_lang}/{uuid4()}.{ext}"

# ---------------------- Экспонат ----------------------

class Exhibit(models.Model):
    # Ссылки
    block = models.ForeignKey(MuseumBlock, on_delete=models.PROTECT, null=True,
                              related_name="exhibits", verbose_name=_("Блок"))
    section = models.ForeignKey(MuseumSection, on_delete=models.PROTECT, null=True,
                                related_name="exhibits", verbose_name=_("Экспозиция"))

    # Код и сервисные
    slug = models.SlugField(_("Код экспоната"), unique=True, max_length=64,
                            help_text=_("Формат: ISC-REN2-1.0001"))
    sequence_no = models.PositiveIntegerField(_("Порядковый номер"),
                                              default=0, editable=False)
    qr_code = models.ImageField(_("QR Code"), upload_to="exhibits/qr_codes/",
                                null=True, blank=True)

    # Заголовки
    title_ru = models.CharField(_("Заголовок (RU)"), max_length=255)
    title_uz = models.CharField(_("Название (UZ)"), max_length=255, blank=True, default="")
    title_en = models.CharField(_("Название (EN)"), max_length=255, blank=True, default="")
    sub_title_ru = models.CharField(_("Sub Title (RU)"), max_length=255, blank=True, default="")
    sub_title_uz = models.CharField(_("Sub Title (UZ)"), max_length=255, blank=True, default="")
    sub_title_en = models.CharField(_("Sub Title (EN)"), max_length=255, blank=True, default="")

    # Описания
    description_ru = models.TextField(_("Описание (RU)"), blank=True, default="")
    description_uz = models.TextField(_("Описание (UZ)"), blank=True, default="")
    description_en = models.TextField(_("Описание (EN)"), blank=True, default="")

    # Арабский язык
    title_ar = models.CharField(_("Название (AR)"), max_length=255, blank=True, default="")
    sub_title_ar = models.CharField(_("Sub Title (AR)"), max_length=255, blank=True, default="")
    description_ar = models.TextField(_("Описание (AR)"), blank=True, default="")

    # Аудио
    audio_ru = models.FileField(_("Аудио (RU)"), upload_to="exhibits/tmp", blank=True, null=True)
    audio_uz = models.FileField(_("Audio (UZ)"), upload_to="exhibits/tmp", blank=True, null=True)
    audio_en = models.FileField(_("Audio (EN)"), upload_to="exhibits/tmp", blank=True, null=True)

    single_image = models.ImageField(_("Фото (без 3D)"),
                                     upload_to=single_upload_to,
                                     blank=True, null=True)
    is_3d = models.BooleanField(_("3D вращение (360°)"), default=False)
    # 360
    frames_required = models.PositiveIntegerField(_("Требуемое число кадров"),
                         default=36, validators=[MinValueValidator(8)])
    is_published = models.BooleanField(_("Опубликован"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Экспонат")
        verbose_name_plural = _("Экспонаты")
        ordering = ["slug"]
        unique_together = (("block", "section", "sequence_no"),)

    def __str__(self):
        return self.slug or (self.title_ru or "Exhibit")

    # ---- Cloudimage-360 helpers (оставляем как у вас) ----
    def ci360_folder(self):
        return f"{settings.MEDIA_URL}exhibits/{self.slug}/frames/"

    def ci360_filename_pattern(self):
        return "frame-{index}.webp"

    def has_single_image(self) -> bool:
        return bool(self.single_image)

    def frames_qs(self):
        return self.photos.filter(is_active=True, kind="frame").order_by("frame_index")

    def gallery_qs(self):
        return self.photos.filter(is_active=True, kind="gallery").order_by("created_at", "id")

    def frames_count(self):
        return self.photos.filter(is_active=True, kind="frame").count()
    frames_count.short_description = _("Активные кадры")

    def first_frame_url(self) -> str:
        """
        Превью для списка:
        - если 3D — первый кадр 360;
        - если не 3D — первая фотка из галереи;
        - иначе — single_image (если задан).
        """
        if self.is_3d:
            filename = self.ci360_filename_pattern().replace("{index}", "001")
            return f"{self.ci360_folder()}{filename}"
        g = self.gallery_qs().first()
        if g and g.image:
            return g.image.url
        return self.single_image.url if self.has_single_image() else ""

    # ---- генерация кода и QR ----
    def _build_slug(self) -> str:
        museum_code = self.block.museum.slug
        block_code = self.block.slug
        section_code = self.section.code_num or 0
        seq = self.sequence_no or 0
        return f"{museum_code}-{block_code}-{section_code}.{seq:04d}"

    def get_qr_path(self) -> str:
        # /<museum>/<exhibit-code>
        return f"/{self.block.museum.slug}/{self.slug}"

    def _ensure_slug_and_sequence(self):
        # выставляем sequence_no, если ещё не задан
        if not self.sequence_no:
            last = Exhibit.objects.filter(block=self.block, section=self.section)\
                                  .order_by("-sequence_no").first()
            self.sequence_no = 1 if not last else last.sequence_no + 1
        self.slug = self._build_slug()

    def _generate_qr(self):
        """
        Генерируем QR-код (png) с абсолютной ссылкой BASE_URL + /<museum>/<slug>
        и подписью (код экспоната) под QR.
        Требуется pillow и qrcode[pil]
        """
        from django.conf import settings as dj_settings

        # 1) Адрес для QR
        base = getattr(dj_settings, "BASE_URL", "http://127.0.0.1:8000")
        url = f"{base}{self.get_qr_path()}"

        # 2) Сам QR (квадрат)
        qr = qrcode.QRCode(box_size=10, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

        qr_size = 700
        qr_img = qr_img.resize((qr_size, qr_size), Image.NEAREST)

        # 3) Подпись
        caption = self.slug  # например ISC-REN2-1.0001

        font_path = getattr(settings, "QR_TEXT_FONT_PATH", None)
        font = ImageFont.truetype(font=font_path, size=60)


        padding = 10
        caption_h = 70
        total_w = qr_size + padding * 2
        total_h = qr_size + padding * 2 + caption_h

        canvas = Image.new("RGB", (total_w, total_h), "white")
        draw = ImageDraw.Draw(canvas)

        canvas.paste(qr_img, (padding, padding))

        try:
            bbox = draw.textbbox((0, 0), caption, font=font)
            text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        except Exception:
            text_w, text_h = draw.textsize(caption, font=font)

        text_x = (total_w - text_w) // 2
        text_y = padding + qr_size + (caption_h - text_h) // 2
        draw.text((text_x, text_y), caption, fill="black", font=font)

        # 7) Сохраняем
        buf = BytesIO()
        canvas.save(buf, format="PNG")
        buf.seek(0)
        self.qr_code.save(f"{self.slug}.png", buf, save=False)

    def save(self, *args, **kwargs):

        self._ensure_slug_and_sequence()
        if not self.qr_code:
            self._generate_qr()
        super().save(*args, **kwargs)


class ExhibitPhoto(models.Model):
    KIND_CHOICES = (
        ("frame", _("Кадр 360°")),
        ("gallery", _("Фото галереи")),
    )
    exhibit = models.ForeignKey(Exhibit, on_delete=models.CASCADE,
                                related_name="photos", verbose_name=_("Экспонат"))
    kind = models.CharField(_("Тип"), max_length=16, choices=KIND_CHOICES, default="frame")
    frame_index = models.PositiveIntegerField(_("Номер кадра"), blank=True, null=True,
                   validators=[MinValueValidator(1)])
    image = models.ImageField(_("Изображение"), upload_to=frame_upload_to)
    is_active = models.BooleanField(_("Активен"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Фото экспоната")
        verbose_name_plural = _("Фото экспоната")
        # уникальность индекса только среди кадров 360
        constraints = [
            models.UniqueConstraint(
                fields=["exhibit", "frame_index"],
                condition=models.Q(kind="frame"),
                name="uniq_360_frame_per_exhibit"
            )
        ]
        ordering = ["exhibit", "kind", "frame_index", "id"]

    def clean(self):
        # если это кадр 360 — индекс обязателен
        if self.kind == "frame" and not self.frame_index:
            raise ValidationError({"frame_index": _("Для кадров 360 обязателен номер кадра.")})
        # если это галерея — индекс не нужен
        if self.kind == "gallery":
            self.frame_index = None

    def __str__(self):
        tag = "360" if self.kind == "frame" else "GAL"
        return f"{self.exhibit.slug} [{tag}] #{self.frame_index or '-'}"
