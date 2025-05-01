# accounts/views.py
import random
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.models import User
from .models import UserProfile
from django.conf import settings
from django.core.cache import cache
from django_ratelimit.decorators import ratelimit
from .tasks import send_otp_task, send_email_otp_task
from stores.models import Store
from geopy.distance import geodesic
from django.http import JsonResponse
from bhukhlagikya.celery import app as celery_app 
import logging

logger = logging.getLogger(__name__)

@ratelimit(key='ip', rate='5/m', method='POST')
def auth_view(request):
    if request.method == 'POST':
        auth_type = request.POST.get('auth_type')  # 'phone' or 'email'
        identifier = request.POST.get('identifier')  # Phone or email
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        store_id = request.POST.get('store')

        if not (latitude and longitude and store_id):
            return JsonResponse({'error': 'Location and store selection are required'}, status=400)

        try:
            store = Store.objects.get(id=store_id)
        except Store.DoesNotExist:
            return JsonResponse({'error': 'Invalid store selected'}, status=400)

        user_location = (float(latitude), float(longitude))
        store_location = (store.latitude, store.longitude)
        distance = geodesic(user_location, store_location).km

        if distance > 5:
            return JsonResponse({'error': 'You are outside the 5km delivery radius of the selected store'}, status=400)

        # Check if user exists
        is_signup = False
        if auth_type == 'phone':
            if UserProfile.objects.filter(phone=identifier).exists():
                user = UserProfile.objects.get(phone=identifier).user
            else:
                is_signup = True
                user = User.objects.create(username=identifier)
                UserProfile.objects.create(user=user, phone=identifier, latitude=latitude, longitude=longitude)
        else:  # email
            if UserProfile.objects.filter(email=identifier).exists():
                user = UserProfile.objects.get(email=identifier).user
            else:
                is_signup = True
                user = User.objects.create(username=identifier)
                UserProfile.objects.create(user=user, email=identifier, latitude=latitude, longitude=longitude)

        # Send OTP
        otp = random.randint(100000, 999999)
        try:
            cache.set(f'otp_{identifier}', otp, timeout=300)
            if auth_type == 'phone':
                send_otp_task.delay(identifier, otp)
            else:
                send_email_otp_task.delay(identifier, otp)
            logger.info(f"Queued OTP task for {identifier}")
            request.session['auth_data'] = {
                'identifier': identifier,
                'auth_type': auth_type,
                'latitude': latitude,
                'longitude': longitude,
                'store_id': store_id,
                'is_signup': is_signup
            }
            return JsonResponse({'success': True, 'redirect': 'verify_otp'})
        except Exception as e:
            logger.error(f"Failed to send OTP to {identifier}: {str(e)}")
            return JsonResponse({'error': f'Failed to send OTP: {str(e)}'}, status=500)

    return render(request, 'base.html')  # Modal is in base.html

def verify_otp(request):
    if request.method == 'POST':
        otp = request.POST.get('otp')
        auth_data = request.session.get('auth_data')
        if not auth_data:
            return JsonResponse({'error': 'Session expired'}, status=400)

        identifier = auth_data['identifier']
        cached_otp = cache.get(f'otp_{identifier}')
        if str(cached_otp) == otp:
            user = User.objects.get(username=identifier)
            login(request, user)
            profile = user.userprofile
            profile.latitude = float(auth_data['latitude'])
            profile.longitude = float(auth_data['longitude'])
            profile.save()
            request.session['selected_store'] = auth_data['store_id']
            return JsonResponse({'success': True, 'redirect': 'home'})
        return JsonResponse({'error': 'Invalid OTP'}, status=400)
    return render(request, 'base.html')

from django.contrib.auth.decorators import login_required

@login_required
def profile(request):
    if request.method == 'POST':
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        store_id = request.POST.get('store')
        profile = request.user.userprofile
        profile.latitude = float(latitude) if latitude else None
        profile.longitude = float(longitude) if longitude else None
        profile.save()
        request.session['selected_store'] = store_id
        return redirect('profile')
    stores = Store.objects.all()
    return render(request, 'accounts/profile.html', {'profile': request.user.userprofile, 'stores': stores})