from sqlalchemy import Column, Integer, LargeBinary, String, DateTime, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from database import Base


class Image(Base):
    """Represents an uploaded image and its metadata in the database.
    Attributes:
        id (int): Unique identifier for the image record.
        filename (str): Unique filename assigned to the stored image.
        upload_time (datetime): Timestamp automatically set to the current UTC time via :func:`datetime.utcnow`.
        classifications (list[Classification]): Related classification results for the image.
        data (bytes): Binary image content retained for processing or retrieval.
        content_type (str): MIME type describing the nature of the image data.
    """
    __tablename__ = "images"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True, nullable=False)
    upload_time = Column(DateTime, default=datetime.utcnow)
    classifications = relationship(
        "Classification",
        back_populates="image",
        cascade="all, delete-orphan",
    )
    data = Column(LargeBinary, nullable=False)
    content_type = Column(String, nullable=False)
    path_found = Column(JSON, nullable=True)


class Classification(Base):
    """Individual classification result linked to an uploaded image."""

    __tablename__ = "classifications"

    id = Column(Integer, primary_key=True, index=True)
    image_id = Column(Integer, ForeignKey("images.id", ondelete="CASCADE"), nullable=False)
    label = Column(String, nullable=False)
    confidence = Column(Float)
    image = relationship("Image", back_populates="classifications")

