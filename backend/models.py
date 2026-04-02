from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, ARRAY, Text
from sqlalchemy.orm import relationship

from .database import Base


class Centre(Base):
    __tablename__ = "centres"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    location = Column(String)
    capacity = Column(Integer)
    online_rating = Column(Float)
    years_operating = Column(Integer, default=0)
    offers_similar_courses = Column(Boolean, default=False)
    standards_verification = Column(String, default="unknown")
    years_known_ao = Column(Integer, default=0)
    late_payment_history = Column(Boolean, default=False)

    labs = relationship("CentreLab", back_populates="centre", cascade="all, delete-orphan")
    skills = relationship("CentreStaffSkill", back_populates="centre", cascade="all, delete-orphan")


class CentreLab(Base):
    __tablename__ = "centre_labs"
    id = Column(Integer, primary_key=True)
    centre_id = Column(Integer, ForeignKey("centres.id"))
    lab_type = Column(String, nullable=False)
    capability = Column(Float, default=0.0)

    centre = relationship("Centre", back_populates="labs")


class CentreStaffSkill(Base):
    __tablename__ = "centre_staff_skills"
    id = Column(Integer, primary_key=True)
    centre_id = Column(Integer, ForeignKey("centres.id"))
    skill = Column(String, nullable=False)
    level = Column(Float, default=0.0)

    centre = relationship("Centre", back_populates="skills")


class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    delivery_mode = Column(String, nullable=False)
    min_lab_req = Column(ARRAY(String), default=list)
    skill_prereqs = Column(ARRAY(String), default=list)
    online_content_ok = Column(Boolean, default=False)

    tags = relationship("CourseTag", back_populates="course", cascade="all, delete-orphan")


class CourseTag(Base):
    __tablename__ = "course_tags"
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    tag = Column(String, nullable=False)

    course = relationship("Course", back_populates="tags")
