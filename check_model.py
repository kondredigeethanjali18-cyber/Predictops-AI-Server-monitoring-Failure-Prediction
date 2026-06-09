import joblib

model = joblib.load("ML/models/anomaly_model.pkl")

print("Model type:", type(model))

if hasattr(model, "feature_names_in_"):
    print("Features:")
    print(model.feature_names_in_)
else:
    print("feature_names_in_ not available")