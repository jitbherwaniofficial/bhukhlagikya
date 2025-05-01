from django.db import models

# Create your models here.
class Store(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    contact = models.CharField(max_length=15)
    latitude = models.FloatField()
    longitude = models.FloatField()
    opening_time = models.TimeField(default='10:00')
    closing_time = models.TimeField(default='22:00')

    def __str__(self):
        return f"{self.name} - {self.city}"