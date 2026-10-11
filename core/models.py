
from django.db import models
from django.utils.text import slugify
 
 
class EventType(models.Model):
   
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    icon = models.ImageField(upload_to='event_icons/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
 
    class Meta:
        ordering = ['name']
 
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
 
    def __str__(self):
        return self.name