from fastapi import APIRouter

from Backend.services.prediction_service import (
    predict_latest_server
)

router = APIRouter()


@router.get("/predict")
def predict():

    return predict_latest_server()