# apps/museum/autocomplete.py
from dal import autocomplete
from django.db.models import Q
from .models import MuseumSection

class SectionAutocomplete(autocomplete.Select2QuerySetView):
    """
    Возвращает список Экспозиций (MuseumSection) отфильтрованных по выбранному Блоку.
    DAL сам передаст значение поля 'block' через forward=['block'].
    """
    def get_queryset(self):
        qs = MuseumSection.objects.all()

        # фильтр по выбранному блоку (приходит в forwarded)
        block_id = self.forwarded.get('block')
        if block_id:
            qs = qs.filter(museum_block_id=block_id)

        # поиск по тексту
        if self.q:
            qs = qs.filter(
                Q(title_ru__icontains=self.q) |
                Q(title_uz__icontains=self.q) |
                Q(title_en__icontains=self.q)
            )

        return qs.order_by("code_num", "id")
