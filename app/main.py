"""
main.py - FastAPI app for penguin species prediction.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from enum import Enum
import pandas as pd
from xgboost import XGBClassifier
import json
import logging
from google.cloud import storage
import os, tempfile, json

bucket = os.getenv("GCS_BUCKET_NAME")
blob_name = os.getenv("GCS_BLOB_NAME")

import os
from dotenv import load_dotenv

load_dotenv()   


client = storage.Client()
bucket = client.bucket(bucket)
blob = bucket.blob(blob_name)

# download into memory or temp file
model_data = json.loads(blob.download_as_text())
# then reconstruct your XGBoost model from that JSON…

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Enums for valid values
class Island(str, Enum):
    Torgersen = "Torgersen"
    Biscoe = "Biscoe"
    Dream = "Dream"

class Sex(str, Enum):
    male = "male"
    female = "female"

# Pydantic input model
class PenguinFeatures(BaseModel):
    bill_length_mm: float
    bill_depth_mm: float
    flipper_length_mm: float
    body_mass_g: float
    year: int  # not used in model, but accepted as input
    sex: Sex
    island: Island

# Load the model and label map
model = XGBClassifier()
model.load_model("app/data/model.json")
logger.info("✅ Model loaded successfully.")

with open("app/data/label_map.json", "r") as f:
    label_map = json.load(f)
inv_label_map = {v: k for k, v in label_map.items()}

# Create FastAPI app
app = FastAPI()

@app.post("/predict")
def predict_penguin(features: PenguinFeatures):
    try:
        logger.info("Received input: %s", features.dict())

        # Extract values from enums using .value
        input_data = {
            "bill_length_mm": features.bill_length_mm,
            "bill_depth_mm": features.bill_depth_mm,
            "flipper_length_mm": features.flipper_length_mm,
            "body_mass_g": features.body_mass_g,
            "sex": features.sex.value,
            "island": features.island.value
        }

        # Manually apply one-hot encoding to match training
        sex_columns = {"sex_Female": 0, "sex_Male": 0}
        island_columns = {"island_Biscoe": 0, "island_Dream": 0, "island_Torgersen": 0}

        # Capitalize 'male' or 'female' to match training encoding
        sex_key = f"sex_{input_data['sex'].capitalize()}"
        island_key = f"island_{input_data['island']}"

        if sex_key not in sex_columns or island_key not in island_columns:
            raise ValueError("Invalid sex or island")

        sex_columns[sex_key] = 1
        island_columns[island_key] = 1

        # Final row (exclude 'year' since model didn't use it)
        row = {
            "bill_length_mm": input_data["bill_length_mm"],
            "bill_depth_mm": input_data["bill_depth_mm"],
            "flipper_length_mm": input_data["flipper_length_mm"],
            "body_mass_g": input_data["body_mass_g"],
            **sex_columns,
            **island_columns
        }

        df = pd.DataFrame([row])
        prediction = model.predict(df)[0]
        species = inv_label_map[prediction]

        logger.info(f"Predicted species: {species}")
        return {"prediction": species}

    except Exception as e:
        logger.exception("Prediction failed.")
        raise HTTPException(status_code=400, detail="Prediction failed.")