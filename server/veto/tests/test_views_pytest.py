class TestVetoSeriesFlow:
    def test_reset_series(self):
        # Setup the necessary conditions for the test
        # Ensure that the series is created and no actions are associated with it
        self.series = Series.objects.create(name="Test Series")
        Action.objects.filter(series=self.series).delete()
        
        self.assertEqual(Action.objects.filter(series=self.series).count(), 0)

    def test_undo_action(self):
        # Setup the necessary conditions for the test
        # Ensure that an action is created and the response is as expected
        action = Action.objects.create(series=self.series, type='undo')
        response = self.client.post('/undo-action-url/', {'action_id': action.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)