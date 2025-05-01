# menu/views.py
from django.views.generic import ListView
from django.shortcuts import render, redirect
from .models import Product, Category
from django.utils import timezone
from datetime import time
from geopy.distance import geodesic
from django.contrib.auth.decorators import login_required
from stores.models import Store

class MenuView(ListView):
    model = Product
    template_name = 'menu/menu.html'
    context_object_name = 'products'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['stores'] = Store.objects.all()
        context['selected_store'] = self.request.session.get('selected_store')
        return context

@login_required
def add_to_cart(request, product_id):
    now = timezone.localtime().time()
    start_time = time(10, 0)
    end_time = time(22, 0)
    if not (start_time <= now <= end_time):
        return render(request, 'menu/menu.html', {'error': 'Orders are only accepted between 10 AM and 10 PM'})

    profile = request.user.userprofile
    store_id = request.session.get('selected_store')
    if not (profile.latitude and profile.longitude and store_id):
        return redirect('profile')

    try:
        store = Store.objects.get(id=store_id)
    except Store.DoesNotExist:
        return render(request, 'menu/menu.html', {'error': 'Selected store not found'})

    user_location = (profile.latitude, profile.longitude)
    store_location = (store.latitude, store.longitude)
    distance = geodesic(user_location, store_location).km

    if distance > 5:
        return render(request, 'menu/menu.html', {'error': 'You are too far from the selected store (more than 5km)'})

    product = Product.objects.get(id=product_id)
    cart = request.session.get('cart', {})
    cart[product_id] = cart.get(product_id, 0) + 1
    request.session['cart'] = cart
    return redirect('cart')

@login_required
def cart_view(request):
    cart = request.session.get('cart', {})
    cart_items = []
    total_price = 0
    for product_id, quantity in cart.items():
        product = Product.objects.get(id=product_id)
        subtotal = product.price * quantity
        total_price += subtotal
        cart_items.append({'product': product, 'quantity': quantity, 'subtotal': subtotal})
    stores = Store.objects.all()
    selected_store = request.session.get('selected_store')
    return render(request, 'menu/cart.html', {
        'cart_items': cart_items,
        'total_price': total_price,
        'stores': stores,
        'selected_store': selected_store
    })