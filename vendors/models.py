from django.db import models

from accounts.models import User
from categories.models import Category
from locations.models import State, City


class VendorProfile(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='vendor_profile'
    )

    business_name = models.CharField(max_length=200)

    state = models.ForeignKey(
        State,
        on_delete=models.PROTECT,
        related_name='vendors',
        blank=True,
        null=True
    )

    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        related_name='vendors',
        blank=True,
        null=True
    )

    is_featured = models.BooleanField(
        default=False,
        verbose_name="Featured on Homepage"
    )

    featured_order = models.PositiveIntegerField(
        default=0,
        verbose_name="Featured Display Order"
    )

    categories = models.ManyToManyField(Category)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.business_name