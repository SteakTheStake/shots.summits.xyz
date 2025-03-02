# models.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, create_engine
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

class Screenshot(Base):
    __tablename__ = 'screenshots'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String, nullable=False)
    discord_username = Column(String, nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow)
    group_id = Column(Integer, ForeignKey('screenshot_groups.id'))
    
    # Relationships
    group = relationship("ScreenshotGroup", back_populates="screenshots")
    tags = relationship("Tag", secondary="screenshot_tags", back_populates="screenshots")

class ScreenshotGroup(Base):
    __tablename__ = 'screenshot_groups'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    created_by = Column(String, nullable=False)
    created_date = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    screenshots = relationship("Screenshot", back_populates="group")

class Tag(Base):
    __tablename__ = 'tags'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    
    # Relationship
    screenshots = relationship("Screenshot", secondary="screenshot_tags", back_populates="tags")

class ScreenshotTag(Base):
    __tablename__ = 'screenshot_tags'
    
    screenshot_id = Column(Integer, ForeignKey('screenshots.id'), primary_key=True)
    tag_id = Column(Integer, ForeignKey('tags.id'), primary_key=True)

class UserRole(Base):
    __tablename__ = 'user_roles'
    
    discord_id = Column(String, primary_key=True)
    role = Column(String, nullable=False, default='user')
    assigned_by = Column(String)
    assigned_date = Column(DateTime, default=datetime.utcnow)

class DeletionLog(Base):
    __tablename__ = 'deletion_log'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String, nullable=False)
    deleted_by = Column(String, nullable=False)
    original_uploader = Column(String, nullable=False)
    deletion_date = Column(DateTime, default=datetime.utcnow)
    reason = Column(String)

class Report(Base):
    __tablename__ = 'reports'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String, nullable=False)
    reported_by = Column(String, nullable=False)
    reason = Column(String, nullable=False)
    report_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default='pending')
