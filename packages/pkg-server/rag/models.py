from typing import Any

from django.db import models
from django.utils.translation import gettext_lazy as _
from pgvector.django import HnswIndex, VectorField
from pydantic import BaseModel

from loci.domain.models.note import Note


class AppleNoteField(models.JSONField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    

    def from_db_value(self, value, expression, connection):
        """
        Convert the value from the database to a Python object.
        """
        if value is None:
            return value
        json_value = super().from_db_value(value, expression, connection)
        return Note(**json_value)
    
    def get_prep_value(self, value: Any) -> Any:
        """
        Convert the value to dict to store in the database.
        """
        if value is None:
            return value
        
        if isinstance(value, BaseModel):
            return value.model_dump(mode = 'json')
        else:
            return value

    def to_python(self, value: Any) -> None | Note:
        if value is None:
            return value
        if isinstance(value, Note):
            return value

        if isinstance(value, str):
            import json
            json_value = json.loads(value)
        elif isinstance(value, dict):
            json_value = value
        else:
            super().to_python(value)
        return Note(**json_value)


class Memory(models.Model):

    class MemoryType(models.TextChoices):
        NOTE = "NOTE", _("NOTE")
        REMINDER = "REMINDER", _("REMINDER")
        PIC = "PIC", _("PIC")

    memory_type = models.CharField(choices = MemoryType.choices,)
    data = AppleNoteField(null=True)

    updated_at = models.DateTimeField(auto_now = True)
    created_at = models.DateTimeField(auto_now_add = True)

    class Meta:
        db_table = "memories"

class MemorySyncLog(models.Model):
    biz_id = models.CharField(max_length = 100)
    biz_modified_at = models.DateTimeField(auto_now = True)

    updated_at = models.DateTimeField(auto_now = True)
    created_at = models.DateTimeField(auto_now_add = True)

    class Meta:
        db_table = "memories_sync_log"
        indexes = [
            models.Index(fields = ['biz_modified_at'], name = "idx_biz_modified_at")
        ]
        constraints = [
            models.UniqueConstraint(fields = ['biz_id'], name = 'uk_biz_id')
        ]
        ordering = ["-biz_modified_at"]


class Neuron(models.Model):
    content = models.TextField(null = False)
    embedding = VectorField(dimensions = 1536)

    class Meta:
        db_table = 'neurons'
        indexes = [
            HnswIndex(
                name = 'idx_hnsw_embedding',
                fields = ['embedding'],
                m = 16,
                ef_construction = 64,
                opclasses = ['vector_cosine_ops']
            )
        ]