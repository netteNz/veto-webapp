from django.urls import path
from dal import autocomplete
from .models import GameMode

class GameModeAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = GameMode.objects.all()
        if self.q:
            qs = qs.filter(name__icontains=self.q)
        return qs

urlpatterns = [
    path("gamemode-autocomplete/", GameModeAutocomplete.as_view(), name="gamemode-autocomplete"),
]