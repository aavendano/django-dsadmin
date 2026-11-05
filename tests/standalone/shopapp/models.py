from django.db import models


class Ticket(models.Model):
    title = models.CharField(max_length=100)
    priority = models.IntegerField(default=1)
    open = models.BooleanField(default=True)

    def __str__(self):
        return self.title
