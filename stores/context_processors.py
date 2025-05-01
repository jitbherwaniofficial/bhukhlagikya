# stores/context_processors.py
from .models import Store

def stores_context(request):
    return {
        'stores': Store.objects.all(),
        'selected_store': request.session.get('selected_store')
    }