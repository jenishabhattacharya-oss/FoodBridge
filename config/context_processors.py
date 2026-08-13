from django.conf import settings


def map_settings(request):
    return {
        "MAP_TILE_URL": settings.MAP_TILE_URL,
        "MAP_TILE_ATTRIBUTION": settings.MAP_TILE_ATTRIBUTION,
        "PAYMENTS_ENABLED": settings.PAYMENTS_ENABLED,
    }
