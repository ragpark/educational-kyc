"""Recommendation API using precomputed feature matrices."""
import os
from typing import List

import joblib
import numpy as np
from fastapi import FastAPI, HTTPException
from sklearn.metrics.pairwise import cosine_similarity

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

centre_features = joblib.load(os.path.join(DATA_DIR, "centre_feature_matrix.pkl"))
course_features = joblib.load(os.path.join(DATA_DIR, "course_feature_matrix.pkl"))
centre_meta = joblib.load(os.path.join(DATA_DIR, "centre_metadata.pkl"))
course_meta = joblib.load(os.path.join(DATA_DIR, "course_metadata.pkl"))
centre_index = {c["id"]: idx for idx, c in enumerate(centre_meta)}

app = FastAPI()


@app.get("/recommend/{centre_id}")
def recommend(centre_id: int, top_n: int = 10):
    if centre_id not in centre_index:
        raise HTTPException(status_code=404, detail="Centre not found")

    idx = centre_index[centre_id]
    centre_vec = centre_features[idx : idx + 1]
    centre_info = centre_meta[idx]
    owned_labs = set(centre_info["labs"])
    rating = centre_info["online_rating"]

    sims = cosine_similarity(centre_vec, course_features)[0]
    results: List[dict] = []
    for j, course in enumerate(course_meta):
        if not set(course["min_lab_req"]).issubset(owned_labs):
            continue
        if course["online_content_ok"] and rating < 3.0:
            continue
        results.append(
            {
                "id": course["id"],
                "title": course["title"],
                "delivery_mode": course["delivery_mode"],
                "min_lab_req": course["min_lab_req"],
                "skill_prereqs": course["skill_prereqs"],
                "score": float(sims[j]),
            }
        )

    results.sort(key=lambda x: x["score"], reverse=True)
    return {
        "centre": {
            "id": centre_id,
            "lab_capabilities": centre_info["lab_capabilities"],
            "skill_levels": centre_info["skill_levels"],
        },
        "recommendations": results[:top_n],
    }
