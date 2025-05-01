from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Order, OrderItem, DeliveryBoy

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'total_price', 'delivery_boy', 'latitude', 'longitude', 'estimated_delivery_time')
    list_filter = ('status', 'store')
    search_fields = ('user__username', 'id')
    list_editable = ('status', 'delivery_boy')

admin.site.register(OrderItem)
admin.site.register(DeliveryBoy)