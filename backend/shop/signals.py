from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import Category, Product, Rests


@receiver([post_save, post_delete], sender=Category)
@receiver([post_save, post_delete], sender=Product)
@receiver([post_save, post_delete], sender=Rests)
def clear_category_cache(sender, instance, **kwargs):
    cache.delete('categories_tree_data')
