# museum/management/commands/export_exhibits_excel.py

import os

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import models

from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment, Font

from museum.models import Exhibit


class Command(BaseCommand):
    help = "Экспорт экспонатов в Excel с картинками (QR и single_image)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            "-o",
            default="exhibits_export.xlsx",
            help="Путь к XLSX файлу (относительно BASE_DIR или абсолютный)",
        )
        parser.add_argument(
            "--only-with-photos",
            action="store_true",
            help="Выгружать только экспонаты, у которых есть QR или single_image",
        )

    def handle(self, *args, **options):
        output_path = options["output"]

        if not os.path.isabs(output_path):
            output_path = os.path.join(settings.BASE_DIR, output_path)

        qs = Exhibit.objects.select_related("block", "section")

        if options["only_with_photos"]:
            qs = qs.filter(
                models.Q(qr_code__isnull=False) | ~models.Q(single_image="")
            ).distinct()

        wb = Workbook()
        ws = wb.active
        ws.title = "Exhibits"

        # Заголовки колонок
        headers = [
            "block",
            "section",
            "title_ru",
            "title_uz",
            "title_en",
            "title_ar",
            "slug",
            "sub_title_ru",
            "sub_title_uz",
            "sub_title_en",
            "sub_title_ar",
            "description_ru",
            "description_uz",
            "description_en",
            "description_ar",
            "qr_code",
            "single_image",
        ]

        # Записываем шапку
        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        # Немного адекватной ширины колонок
        width_map = {
            "block": 20,
            "section": 25,
            "title_ru": 35,
            "title_uz": 35,
            "title_en": 35,
            "title_ar": 35,
            "slug": 25,
            "sub_title_ru": 35,
            "sub_title_uz": 35,
            "sub_title_en": 35,
            "sub_title_ar": 35,
            "description_ru": 60,
            "description_uz": 60,
            "description_en": 60,
            "description_ar": 60,
            "qr_code": 20,
            "single_image": 25,
        }

        for col_idx, header in enumerate(headers, start=1):
            col_letter = get_column_letter(col_idx)
            ws.column_dimensions[col_letter].width = width_map.get(header, 20)

        # Индексы колонок для картинок (для удобства)
        qr_col_idx = headers.index("qr_code") + 1
        single_img_col_idx = headers.index("single_image") + 1

        row_idx = 2
        for ex in qs:
            # Текстовые поля
            row_values = [
                ex.block.title_ru if ex.block else "",
                ex.section.title_ru if ex.section else "",
                ex.title_ru or "",
                ex.title_uz or "",
                ex.title_en or "",
                ex.title_ar or "",
                ex.slug or "",
                ex.sub_title_ru or "",
                ex.sub_title_uz or "",
                ex.sub_title_en or "",
                ex.sub_title_ar or "",
                ex.description_ru or "",
                ex.description_uz or "",
                ex.description_en or "",
                ex.description_ar or "",
                "",  # qr_code (картинка)
                "",  # single_image (картинка)
            ]

            for col_idx, value in enumerate(row_values, start=1):
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                # заворачиваем тексты, чтобы не улетало в космос по ширине
                cell.alignment = Alignment(
                    horizontal="left",
                    vertical="top",
                    wrap_text=True,
                )

            # Высота строки по умолчанию (если будут картинки – увеличим)
            ws.row_dimensions[row_idx].height = 40

            # Вставка QR-кода
            if ex.qr_code and ex.qr_code.name:
                qr_path = os.path.join(settings.MEDIA_ROOT, ex.qr_code.name)
                if os.path.exists(qr_path):
                    try:
                        img = XLImage(qr_path)
                        # Чуть уменьшим (openpyxl меряет в пикселях примерно)
                        img.width = 150
                        img.height = 150

                        cell_addr = f"{get_column_letter(qr_col_idx)}{row_idx}"
                        ws.add_image(img, cell_addr)

                        # увеличиваем высоту строки под картинку
                        ws.row_dimensions[row_idx].height = max(
                            ws.row_dimensions[row_idx].height, 120
                        )
                    except Exception as e:
                        self.stderr.write(f"Не удалось вставить QR для {ex.slug}: {e}")

            # Вставка single_image
            if ex.single_image and ex.single_image.name:
                img_path = os.path.join(settings.MEDIA_ROOT, ex.single_image.name)
                if os.path.exists(img_path):
                    try:
                        img = XLImage(img_path)
                        img.width = 200
                        img.height = 200

                        cell_addr = f"{get_column_letter(single_img_col_idx)}{row_idx}"
                        ws.add_image(img, cell_addr)

                        ws.row_dimensions[row_idx].height = max(
                            ws.row_dimensions[row_idx].height, 160
                        )
                    except Exception as e:
                        self.stderr.write(f"Не удалось вставить single_image для {ex.slug}: {e}")

            row_idx += 1

        # Создаём директорию, если её нет
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        wb.save(output_path)
        self.stdout.write(self.style.SUCCESS(f"Экспорт завершён: {output_path}"))
