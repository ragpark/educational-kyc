from .database import SessionLocal, init_db
from .models import Centre, CentreLab, CentreStaffSkill, Course, CourseTag


def seed():
    """Populate the database with sample centres and courses."""
    init_db()
    db = SessionLocal()
    try:
        if db.query(Centre).first():
            print("Database already contains data; skipping seed.")
            return

        centre1 = Centre(
            name="Sample College",
            location="London",
            capacity=500,
            online_rating=4.5,
        )
        centre1.labs = [
            CentreLab(lab_type="IT Lab", capability=0.9),
        ]
        centre1.skills = [
            CentreStaffSkill(skill="Python", level=0.8),
        ]

        centre2 = Centre(
            name="City Training",
            location="Manchester",
            capacity=300,
            online_rating=4.0,
        )
        centre2.labs = [
            CentreLab(lab_type="Data Lab", capability=0.7),
        ]
        centre2.skills = [
            CentreStaffSkill(skill="Data Analysis", level=0.6),
        ]

        course1 = Course(
            title="Intro to Python",
            description="Learn the basics of Python programming",
            delivery_mode="online",
            min_lab_req=["IT Lab"],
            skill_prereqs=["Python"],
            online_content_ok=True,
        )
        course1.tags = [
            CourseTag(tag="programming"),
            CourseTag(tag="python"),
        ]

        course2 = Course(
            title="Data Science 101",
            description="Foundations of data science",
            delivery_mode="onsite",
            min_lab_req=["Data Lab"],
            skill_prereqs=["Python"],
            online_content_ok=False,
        )
        course2.tags = [
            CourseTag(tag="data"),
            CourseTag(tag="science"),
        ]

        db.add_all([centre1, centre2, course1, course2])
        db.commit()
        print("Seed data inserted.")
    finally:
        db.close()


def main():
    seed()


if __name__ == "__main__":
    main()
