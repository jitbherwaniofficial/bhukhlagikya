# orders/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Order, OrderItem
from menu.models import Product
from stores.models import Store
from django.conf import settings
import razorpay
from django.utils import timezone
from datetime import time, timedelta
from geopy.distance import geodesic
import logging

logger = logging.getLogger(__name__)

@login_required
def checkout(request):
    now = timezone.localtime().time()
    start_time = time(10, 0)
    end_time = time(22, 0)
    if not (start_time <= now <= end_time):
        logger.warning(f"Checkout attempted outside operating hours: {now}")
        return render(request, 'menu/cart.html', {'error': 'Orders are only accepted between 10 AM and 10 PM'})

    profile = request.user.userprofile
    store_id = request.session.get('selected_store')
    if not store_id:
        logger.warning(f"No selected store in session for user {request.user}")
        return redirect('profile')

    try:
        store = Store.objects.get(id=store_id)
    except Store.DoesNotExist:
        logger.error(f"Store with id {store_id} not found")
        return render(request, 'menu/cart.html', {'error': 'Selected store not found'})

    cart = request.session.get('cart', {})
    if not cart:
        logger.warning(f"Empty cart for user {request.user}")
        return redirect('cart')

    try:
        total_price = sum(Product.objects.get(id=int(pid)).price * qty for pid, qty in cart.items())
    except Product.DoesNotExist as e:
        logger.error(f"Product not found in cart: {str(e)}")
        return render(request, 'menu/cart.html', {'error': 'One or more products in your cart are no longer available'})

    try:
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        payment_data = {
            'amount': int(total_price * 100),  # Convert to paise
            'currency': 'INR',
            'payment_capture': '1'
        }
        payment = client.order.create(data=payment_data)
    except Exception as e:
        logger.error(f"Razorpay order creation failed: {str(e)}")
        return render(request, 'orders/checkout.html', {'error': f'Payment initialization failed: {str(e)}'})

    if request.method == 'POST':
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        if not (latitude and longitude):
            logger.warning(f"Missing location data for user {request.user}")
            return render(request, 'orders/checkout.html', {'error': 'Location is required'})

        try:
            user_location = (float(latitude), float(longitude))
            store_location = (store.latitude, store.longitude)
            distance = geodesic(user_location, store_location).km
        except ValueError as e:
            logger.error(f"Invalid location data: {str(e)}")
            return render(request, 'orders/checkout.html', {'error': 'Invalid location data'})

        if distance > 5:
            logger.warning(f"User {request.user} too far from store {store_id}: {distance}km")
            return render(request, 'orders/checkout.html', {'error': 'You are too far from the selected store (more than 5km)'})

        try:
            estimated_delivery = timezone.now() + timedelta(minutes=30)
            order = Order.objects.create(
                user=request.user,
                total_price=total_price,
                latitude=latitude,
                longitude=longitude,
                store=store,
                estimated_delivery_time=estimated_delivery
            )
            for product_id, quantity in cart.items():
                product = Product.objects.get(id=product_id)
                OrderItem.objects.create(order=order, product=product, quantity=quantity)
            request.session['cart'] = {}
            logger.info(f"Order {order.id} created for user {request.user}")
            return redirect('order_success', order_id=order.id)
        except Exception as e:
            logger.error(f"Order creation failed for user {request.user}: {str(e)}")
            return render(request, 'orders/checkout.html', {'error': f'Order creation failed: {str(e)}'})

    stores = Store.objects.all()
    selected_store = store_id
    return render(request, 'orders/checkout.html', {
        'total_price': total_price,
        'razorpay_order_id': payment['id'],
        'razorpay_key': settings.RAZORPAY_KEY_ID,
        'stores': stores,
        'selected_store': selected_store
    })

@login_required
def order_success(request, order_id):
    order = Order.objects.get(id=order_id)
    stores = Store.objects.all()
    selected_store = request.session.get('selected_store')
    return render(request, 'orders/success.html', {
        'order': order,
        'stores': stores,
        'selected_store': selected_store
    })

@login_required
def order_tracking(request, order_id):
    order = Order.objects.get(id=order_id, user=request.user)
    show_delivery_boy = order.status == 'out_for_delivery' and order.delivery_boy
    stores = Store.objects.all()
    selected_store = request.session.get('selected_store')
    return render(request, 'orders/tracking.html', {
        'order': order,
        'show_delivery_boy': show_delivery_boy,
        'stores': stores,
        'selected_store': selected_store
    })