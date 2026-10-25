from django.conf import settings


def brand_context(request):
    return {"demo_mode": settings.DEMO_MODE}
