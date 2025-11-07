from django.db.models import OneToOneField
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget

from .models import Exhibit, MuseumBlock, MuseumSection


class ExhibitResource(resources.ModelResource):
    block = fields.Field(attribute='block', column_name='block',
                           widget=ForeignKeyWidget(MuseumBlock, 'title_ru'))
    section = fields.Field(attribute='section', column_name='section',
                           widget=ForeignKeyWidget(MuseumSection, 'title_ru'))
    class Meta:
        model = Exhibit