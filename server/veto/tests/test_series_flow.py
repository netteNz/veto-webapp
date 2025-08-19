from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from veto.models import Series, Map, GameMode, Action

class VetoSeriesFlowTests(APITestCase):
    def setUp(self):
        self.series = Series.objects.create(team_a="Alpha", team_b="Bravo")
        self.state_url = reverse("series-series-state", args=[self.series.id])
        self.veto_url = reverse("series-series-veto", args=[self.series.id])
        self.undo_url = reverse("series-series-undo", args=[self.series.id])
        self.reset_url = reverse("series-series-reset", args=[self.series.id])

        self.obj_mode = GameMode.objects.create(name="Capture the Flag", is_objective=True)
        self.map1 = Map.objects.create(name="Streets")
        self.map1.modes.add(self.obj_mode)

    def test_create_series_and_check_state(self):
        response = self.client.get(self.state_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("state", response.data)

    def test_perform_valid_objective_veto(self):
        data = {
            "team": "Alpha",
            "map": self.map1.id,
            "mode": self.obj_mode.id
        }
        response = self.client.post(self.veto_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Action.objects.filter(series=self.series).count(), 1)

    def test_invalid_veto_wrong_team(self):
        data = {
            "team": "Charlie",  # Invalid team
            "map": self.map1.id,
            "mode": self.obj_mode.id
        }
        response = self.client.post(self.veto_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_undo_action(self):
        veto_response = self.client.post(self.veto_url, {
            "team": "Alpha",
            "map": self.map1.id,
            "mode": self.obj_mode.id
        })
        self.assertEqual(veto_response.status_code, status.HTTP_201_CREATED)
        response = self.client.post(self.undo_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Action.objects.filter(series=self.series).count(), 0)

    def test_reset_series(self):
        veto_response = self.client.post(self.veto_url, {
            "team": "Alpha",
            "map": self.map1.id,
            "mode": self.obj_mode.id
        })
        self.assertEqual(veto_response.status_code, status.HTTP_201_CREATED)
        response = self.client.post(self.reset_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Action.objects.filter(series=self.series).count(), 0)

    def test_invalid_series_returns_404(self):
        bad_url = reverse("series-series-state", args=[999999])
        response = self.client.get(bad_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)