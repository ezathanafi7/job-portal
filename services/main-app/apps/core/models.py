from django.db import models


class TimeStampedModel(models.Model):
    """Adds created_at / updated_at to any model that inherits from it.

    Example (step 2):
        class Job(TimeStampedModel):
            title = models.CharField(max_length=200)
    """

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)  
    updated_at = models.DateTimeField(auto_now=True)                     

    class Meta:
        abstract = True  