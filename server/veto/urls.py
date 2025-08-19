# server/veto/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MapViewSet, SeriesViewSet, ActionViewSet,
    HealthView, MapModeComboView, MapModeGroupedView, GameModeViewSet
)

router = DefaultRouter()
router.register(r'maps', MapViewSet, basename='maps')
router.register(r'series', SeriesViewSet, basename='series')
router.register(r'actions', ActionViewSet, basename='actions')
router.register(r'gamemodes', GameModeViewSet, basename='gamemode')
router.trailing_slash = '/?'   # makes trailing slash optional


urlpatterns = [
    path('', include(router.urls)),
    path('health/', HealthView.as_view(), name='health'),
    path('maps/combos/', MapModeComboView.as_view(), name='map-mode-combos'),
    path('maps/combos/grouped/', MapModeGroupedView.as_view(), name='map-mode-combos-grouped'),
]