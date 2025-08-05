"""ETL script to build feature matrices for centres and courses."""
import os
import numpy as np
import joblib
from scipy.sparse import hstack, csr_matrix
from sqlalchemy.orm import joinedload
from sklearn.feature_extraction import DictVectorizer
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .database import SessionLocal, init_db
from .models import Centre, Course


def run_etl(output_dir: str = None):
    output_dir = output_dir or os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(output_dir, exist_ok=True)

    # Ensure database schema exists before querying
    init_db()

    session = SessionLocal()
    try:
        centres = (
            session.query(Centre)
            .options(joinedload(Centre.labs), joinedload(Centre.skills))
            .all()
        )
        courses = session.query(Course).all()

        centre_lab_dicts, centre_skill_dicts, centre_ratings, centre_meta = [], [], [], []
        course_lab_dicts, course_skill_dicts, course_meta = [], [], []

        for c in centres:
            lab_dict = {lab.lab_type: lab.capability for lab in c.labs}
            skill_dict = {s.skill: s.level for s in c.skills}
            centre_lab_dicts.append(lab_dict)
            centre_skill_dicts.append(skill_dict)
            rating = c.online_rating or 0.0
            centre_ratings.append(rating)
            centre_meta.append(
                {
                    "id": c.id,
                    "name": c.name,
                    "lab_capabilities": lab_dict,
                    "skill_levels": skill_dict,
                    "labs": list(lab_dict.keys()),
                    "skills": list(skill_dict.keys()),
                    "online_rating": rating,
                }
            )

        for crs in courses:
            lab_req = crs.min_lab_req or []
            skill_req = crs.skill_prereqs or []
            course_lab_dicts.append({lab: 1.0 for lab in lab_req})
            course_skill_dicts.append({sk: 1.0 for sk in skill_req})
            course_meta.append(
                {
                    "id": crs.id,
                    "title": crs.title,
                    "delivery_mode": crs.delivery_mode,
                    "min_lab_req": lab_req,
                    "skill_prereqs": skill_req,
                    "online_content_ok": crs.online_content_ok,
                }
            )

        lab_vec = DictVectorizer()
        lab_vec.fit(centre_lab_dicts + course_lab_dicts)
        skill_vec = DictVectorizer()
        skill_vec.fit(centre_skill_dicts + course_skill_dicts)

        delivery_enc = OneHotEncoder(handle_unknown="ignore")
        delivery_enc.fit([[c["delivery_mode"]] for c in course_meta])

        rating_scaler = StandardScaler().fit(np.array(centre_ratings).reshape(-1, 1))

        centre_lab_matrix = lab_vec.transform(centre_lab_dicts)
        centre_skill_matrix = skill_vec.transform(centre_skill_dicts)
        centre_rating_matrix = rating_scaler.transform(np.array(centre_ratings).reshape(-1, 1))
        centre_delivery_zeros = csr_matrix(
            np.zeros((centre_lab_matrix.shape[0], len(delivery_enc.categories_[0])))
        )
        centre_online_zeros = csr_matrix(np.zeros((centre_lab_matrix.shape[0], 1)))
        centre_features = hstack(
            [centre_lab_matrix, centre_skill_matrix, centre_rating_matrix, centre_delivery_zeros, centre_online_zeros]
        ).toarray()

        course_lab_matrix = lab_vec.transform(course_lab_dicts)
        course_skill_matrix = skill_vec.transform(course_skill_dicts)
        course_delivery_matrix = delivery_enc.transform(
            [[c["delivery_mode"]] for c in course_meta]
        )
        course_online_matrix = csr_matrix(
            np.array([[1.0 if c["online_content_ok"] else 0.0] for c in course_meta])
        )
        course_rating_zeros = csr_matrix(np.zeros((len(course_meta), 1)))
        course_features = hstack(
            [course_lab_matrix, course_skill_matrix, course_rating_zeros, course_delivery_matrix, course_online_matrix]
        ).toarray()

        joblib.dump(centre_features, os.path.join(output_dir, "centre_feature_matrix.pkl"))
        joblib.dump(course_features, os.path.join(output_dir, "course_feature_matrix.pkl"))
        joblib.dump(centre_meta, os.path.join(output_dir, "centre_metadata.pkl"))
        joblib.dump(course_meta, os.path.join(output_dir, "course_metadata.pkl"))
    finally:
        session.close()


if __name__ == "__main__":
    run_etl()
