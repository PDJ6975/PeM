from django.conf import settings

def media_external_url(request):
    """
    Context processor para hacer disponible MEDIA_EXTERNAL_URL en todos los templates
    """
    return {
        'MEDIA_EXTERNAL_URL': getattr(settings, 'MEDIA_EXTERNAL_URL', '')
    }