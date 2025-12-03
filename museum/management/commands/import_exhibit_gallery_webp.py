import os
from glob import glob

from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files import File
from django.db import transaction

from museum.models import Exhibit, ExhibitPhoto


class Command(BaseCommand):
    help = (
        "Импортирует webp-галереи из webp_output/<slug>/gallery/*.webp "
        "в ExhibitPhoto(kind='gallery') и обновляет single_image."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--input-dir",
            "-i",
            default="webp_output",
            help="Базовая папка с webp-галереями (по умолчанию: BASE_DIR/webp_output)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Ничего не сохранять в БД, только вывести, что бы было сделано.",
        )

    def handle(self, *args, **options):
        base_dir = options["input_dir"]
        dry_run = options["dry_run"]

        # Превращаем в абсолютный путь
        if not os.path.isabs(base_dir):
            base_dir = os.path.join(settings.BASE_DIR, base_dir)

        if not os.path.isdir(base_dir):
            self.stderr.write(self.style.ERROR(f"Папка не найдена: {base_dir}"))
            return

        self.stdout.write(self.style.WARNING(f"Базовая папка импорта: {base_dir}"))
        if dry_run:
            self.stdout.write(self.style.WARNING("РЕЖИМ dry-run: изменения НЕ будут сохранены."))

        # Список папок верхнего уровня — предполагаем, что это slug экспоната
        slug_dirs = [
            d for d in os.listdir(base_dir)
            if os.path.isdir(os.path.join(base_dir, d))
        ]

        if not slug_dirs:
            self.stdout.write("В папке нет подпапок с slug'ами. Нечего импортировать.")
            return

        total_exhibits = 0
        total_photos = 0
        skipped_no_exhibit = 0
        skipped_no_photos = 0

        for slug in sorted(slug_dirs):
            exhibit_dir = os.path.join(base_dir, slug)
            gallery_dir = os.path.join(exhibit_dir, "gallery")

            if not os.path.isdir(gallery_dir):
                self.stdout.write(f"[{slug}] пропущен: нет папки gallery/")
                continue

            # Собираем все .webp (можно расширить до любых картинок при желании)
            patterns = [
                os.path.join(gallery_dir, "*.webp"),
                os.path.join(gallery_dir, "*.WEBP"),
            ]
            image_paths = []
            for pattern in patterns:
                image_paths.extend(glob(pattern))

            image_paths = sorted(image_paths)

            if not image_paths:
                self.stdout.write(f"[{slug}] пропущен: нет файлов .webp в gallery/")
                skipped_no_photos += 1
                continue

            try:
                exhibit = Exhibit.objects.get(slug=slug)
            except Exhibit.DoesNotExist:
                self.stderr.write(self.style.ERROR(
                    f"[{slug}] Экспонат с таким slug не найден в БД, пропускаю."
                ))
                skipped_no_exhibit += 1
                continue

            self.stdout.write(self.style.SUCCESS(
                f"[{slug}] найден экспонат #{exhibit.id}, файлов в галерее: {len(image_paths)}"
            ))

            total_exhibits += 1

            if dry_run:
                # В режиме dry-run просто покажем, что планируем сделать
                self.stdout.write(f"  DRY-RUN: удалил бы старые gallery-фото и создал бы {len(image_paths)} новых.")
                continue

            with transaction.atomic():
                # 1) чистим старую галерею
                old_count = ExhibitPhoto.objects.filter(exhibit=exhibit, kind="gallery").count()
                ExhibitPhoto.objects.filter(exhibit=exhibit, kind="gallery").delete()
                self.stdout.write(f"  Удалено старых gallery-фото: {old_count}")

                # 2) создаём новые
                created_photos = 0
                first_image_for_single = None

                for idx, img_path in enumerate(image_paths, start=1):
                    if not os.path.isfile(img_path):
                        self.stderr.write(f"  [WARN] Файл не найден (пропускаю): {img_path}")
                        continue

                    filename = os.path.basename(img_path)

                    with open(img_path, "rb") as f:
                        photo = ExhibitPhoto(
                            exhibit=exhibit,
                            kind="gallery",
                            is_active=True,
                        )
                        # upload_to сам разрулит путь: exhibits/<slug>/gallery/uuid.ext
                        photo.image.save(filename, File(f), save=False)
                        photo.full_clean()
                        photo.save()

                    created_photos += 1

                    # первую нормальную картинку запомним для single_image
                    if first_image_for_single is None:
                        first_image_for_single = img_path

                self.stdout.write(f"  Создано gallery-фото: {created_photos}")
                total_photos += created_photos

                # 3) обновляем single_image первой картинкой
                if first_image_for_single:
                    with open(first_image_for_single, "rb") as f:
                        single_name = os.path.basename(first_image_for_single)
                        # upload_to: exhibits/<slug>/single/single.ext
                        exhibit.single_image.save(single_name, File(f), save=False)
                    exhibit.save(update_fields=["single_image"])
                    self.stdout.write("  single_image обновлён первой фотографией галереи.")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Импорт завершён."))
        self.stdout.write(f"  Экспонатов обработано: {total_exhibits}")
        self.stdout.write(f"  Фотографий создано: {total_photos}")
        self.stdout.write(f"  Пропущено (нет экспоната в БД): {skipped_no_exhibit}")
        self.stdout.write(f"  Пропущено (нет .webp в gallery/): {skipped_no_photos}")
