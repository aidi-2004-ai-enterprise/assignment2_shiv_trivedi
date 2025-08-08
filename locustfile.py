from locust import HttpUser, task, between

class PenguinUser(HttpUser):
    # Users wait between 1–5 seconds between tasks to simulate real traffic
    wait_time = between(1, 5)

    @task
    def predict(self):
        self.client.post(
            "/predict",
            json={
                "bill_length_mm": 39.1,
                "bill_depth_mm": 18.7,
                "flipper_length_mm": 181,
                "body_mass_g": 3750,
                "year": 2007,
                "sex": "male",
                "island": "Biscoe"
            },
            headers={"Content-Type": "application/json"}
        )
