# server/veto/views.py
from django.utils import timezone
from .machine_tsd import TSDMachine, GuardError, TurnError
from django.utils.text import slugify
from rest_framework.decorators import action
from collections import defaultdict
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.shortcuts import get_object_or_404

from .models import Map, GameMode, Series, Action
from .serializers import (
    MapSerializer, MapWriteSerializer,
    GameModeSerializer, SeriesSerializer, ActionSerializer
)

class HealthView(APIView):
    def get(self, request):
        return Response({
            "status": "ok",
            "service": "veto-api",
            "timestamp": timezone.now().isoformat(),
            "maps": Map.objects.count(),
            "modes": GameMode.objects.count(),
            "series": Series.objects.count(),
            "actions": Action.objects.count(),
        }, status=status.HTTP_200_OK)


class MapViewSet(viewsets.ModelViewSet):
    """
    GET /api/maps/           -> list maps (with modes)
    POST /api/maps/          -> create (use mode_ids)
    PATCH/PUT /api/maps/:id  -> update (use mode_ids)
    """
    queryset = Map.objects.all().prefetch_related('modes')

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return MapWriteSerializer
        return MapSerializer


class SeriesViewSet(viewsets.ModelViewSet):
    """
    Basic CRUD for series. Actions are nested via ActionViewSet.
    """
    queryset = Series.objects.all().prefetch_related('actions')
    serializer_class = SeriesSerializer
    # --- New minimal actions ---

    @action(detail=True, methods=["get"], url_path="state", url_name="series-state")
    def state(self, request, pk=None):
        s = get_object_or_404(Series, pk=pk)
        return Response({"state": s.state}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="veto", url_name="series-veto")
    def veto(self, request, pk=None):
        """
        Minimal placeholder endpoint to record a veto/pick action for tests.
        Accepts: {"team": str, "map": int, "mode": int}
        Creates an Action and returns 201.
        """
        s = get_object_or_404(Series, pk=pk)
        team_label = (request.data.get("team") or "").strip()
        team_code = ""
        if team_label:
            if s.team_a and team_label.lower() == s.team_a.lower():
                team_code = "A"
            elif s.team_b and team_label.lower() == s.team_b.lower():
                team_code = "B"
        # Strict: no fallback to first letter, ensure team matches one of the series teams
        if not team_code:
            return Response({"detail": "Invalid or missing team"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            map_obj = Map.objects.get(pk=request.data.get("map"))
            mode_obj = GameMode.objects.get(pk=request.data.get("mode"))
        except (Map.DoesNotExist, GameMode.DoesNotExist):
            return Response({"detail": "Invalid map or mode"}, status=status.HTTP_400_BAD_REQUEST)

        step = (s.actions.aggregate_max_step() if hasattr(s.actions, 'aggregate_max_step') else None)
        # simple incremental step based on count
        step = (s.actions.count() or 0) + 1

        act = Action.objects.create(
            series=s,
            step=step,
            action_type=Action.BAN,
            team=team_code,
            map=map_obj,
            mode=mode_obj,
        )
        return Response(ActionSerializer(act).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def assign_roles(self, request, pk=None):
        m = TSDMachine(pk)
        team_a = request.data.get("team_a")
        team_b = request.data.get("team_b")
        try:
            s = m.assign_roles(team_a, team_b)
            return Response(SeriesSerializer(s).data)
        except (GuardError, TurnError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def confirm_tsd(self, request, pk=None):
        m = TSDMachine(pk)
        series_type = request.data.get("series_type")
        try:
            s = m.confirm_tsd(series_type)
            return Response(SeriesSerializer(s).data)
        except (GuardError, TurnError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def ban_objective(self, request, pk=None):
        m = TSDMachine(pk)
        try:
            s = m.ban_objective_combo(
                team=request.data.get("team"),
                objective_mode_id=request.data.get("objective_mode_id"),
                map_id=request.data.get("map_id"),
            )
            return Response(SeriesSerializer(s).data)
        except (GuardError, TurnError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def ban_slayer(self, request, pk=None):
        m = TSDMachine(pk)
        try:
            s = m.ban_slayer_map(
                team=request.data.get("team"),
                map_id=request.data.get("map_id"),
            )
            return Response(SeriesSerializer(s).data)
        except (GuardError, TurnError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def pick_objective(self, request, pk=None):
        m = TSDMachine(pk)
        try:
            s = m.pick_objective_combo(
                team=request.data.get("team"),
                objective_mode_id=request.data.get("objective_mode_id"),
                map_id=request.data.get("map_id"),
            )
            return Response(SeriesSerializer(s).data)
        except (GuardError, TurnError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def pick_slayer(self, request, pk=None):
        m = TSDMachine(pk)
        try:
            s = m.pick_slayer_map(
                team=request.data.get("team"),
                map_id=request.data.get("map_id"),
            )
            return Response(SeriesSerializer(s).data)
        except (GuardError, TurnError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_name="series-undo")
    def undo(self, request, pk=None):
        m = TSDMachine(pk)
        try:
            s = m.undo_last()
            return Response(SeriesSerializer(s).data)
        except (GuardError, TurnError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_name="series-reset")
    def reset(self, request, pk=None):
        m = TSDMachine(pk)
        try:
            s = m.reset()
            return Response(SeriesSerializer(s).data)
        except (GuardError, TurnError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ActionViewSet(viewsets.ModelViewSet):
    """
    CRUD for actions. On create/update, ensure the chosen mode is valid for the chosen map.
    """
    queryset = Action.objects.select_related('series', 'map', 'mode')
    serializer_class = ActionSerializer

    def _validate_map_mode(self, serializer):
        map_obj = serializer.validated_data.get('map')
        mode_obj = serializer.validated_data.get('mode')
        if map_obj and mode_obj and not map_obj.modes.filter(pk=mode_obj.pk).exists():
            raise ValidationError({"mode": "Selected mode is not allowed on this map."})

    def perform_create(self, serializer):
        self._validate_map_mode(serializer)
        serializer.save()

    def perform_update(self, serializer):
        self._validate_map_mode(serializer)
        serializer.save()


class MapModeComboView(APIView):
    """
    Flat list of allowed Map × Mode combos.

    Filters:
      ?mode=Slayer                -> only that mode
      ?type=objective|slayer      -> objective excludes Slayer (by flag), slayer == Slayer only
    """
    def get(self, request):
        q_mode = request.GET.get("mode")
        q_type = request.GET.get("type")  # objective | slayer

        combos = []
        maps = Map.objects.all().prefetch_related("modes")

        for m in maps:
            for gm in m.modes.all():
                if q_mode and gm.name.lower() != q_mode.lower():
                    continue

                # determine objective vs slayer
                # prefer the flag; fall back to name check if ever missing
                is_obj = getattr(gm, "is_objective", None)
                if is_obj is None:
                    is_obj = (gm.name != "Slayer")

                if q_type:
                    want_obj = (q_type.lower() == "objective")
                    if want_obj != bool(is_obj):
                        continue

                combos.append({
                    "map_id": m.id,
                    "map": m.name,
                    "mode_id": gm.id,
                    "mode": gm.name,
                    "is_objective": bool(is_obj),
                    "slug": f"{slugify(m.name)}--{slugify(gm.name)}"
                })

        combos.sort(key=lambda x: (x["mode"], x["map"]))
        return Response(combos, status=status.HTTP_200_OK)

class MapModeGroupedView(APIView):
    """
    Returns combos grouped by Objective vs Slayer, then by Mode.

    GET /api/maps/combos/grouped/
      ?type=objective|slayer   # optional
      ?mode=Slayer             # optional (filters to a single mode)
    Response shape:
    {
      "objective": [
        { "mode_id": 4, "mode": "King of the Hill", "combos": [ {map_id, map, slug}, ... ] },
        ...
      ],
      "slayer": [
        { "mode_id": 1, "mode": "Slayer", "combos": [ ... ] }
      ]
    }
    """
    def get(self, request):
        q_type = (request.GET.get("type") or "").lower()  # objective|slayer|""(all)
        q_mode = request.GET.get("mode")

        maps = Map.objects.all().prefetch_related("modes")

        # mode_id -> {"mode_id", "mode", "is_objective", "combos":[{map_id,map,slug}]}
        bucket = {}

        for m in maps:
            for gm in m.modes.all():
                # filter by single mode (exact, case-insensitive)
                if q_mode and gm.name.lower() != q_mode.lower():
                    continue

                is_obj = bool(gm.is_objective) if gm.is_objective is not None else (gm.name != "Slayer")
                if q_type:
                    want_obj = (q_type == "objective")
                    if want_obj != is_obj:
                        continue

                if gm.id not in bucket:
                    bucket[gm.id] = {
                        "mode_id": gm.id,
                        "mode": gm.name,
                        "is_objective": is_obj,
                        "combos": []
                    }
                bucket[gm.id]["combos"].append({
                    "map_id": m.id,
                    "map": m.name,
                    "slug": f"{slugify(m.name)}--{slugify(gm.name)}"
                })

        # sort combos by map name
        for v in bucket.values():
            v["combos"].sort(key=lambda x: x["map"])

        # split into objective vs slayer arrays
        objective = []
        slayer = []
        for v in bucket.values():
            (objective if v["is_objective"] else slayer).append(v)

        # sort modes alphabetically within each group
        objective.sort(key=lambda x: x["mode"])
        slayer.sort(key=lambda x: x["mode"])

        return Response({"objective": objective, "slayer": slayer}, status=status.HTTP_200_OK)


class GameModeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GameMode.objects.all().order_by('name')
    serializer_class = GameModeSerializer