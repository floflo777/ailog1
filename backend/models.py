from sqlalchemy import Column, Integer, String, Float, Table, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

user_collections = Table(
    'user_collections',
    Base.metadata,
    Column('user_id', ForeignKey('users.id'), primary_key=True),
    Column('collection_id', ForeignKey('collections.id'), primary_key=True)
)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    collections = relationship("Collection", secondary=user_collections, back_populates="users")

class Collection(Base):
    __tablename__ = "collections"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, default="")
    users = relationship("User", secondary=user_collections, back_populates="collections")

class GlobalSettings(Base):
    __tablename__ = "global_settings"
    id = Column(Integer, primary_key=True, index=True)
    chunk_size = Column(Integer, default=500)
    chunk_overlap = Column(Integer, default=50)
    temperature = Column(Float, default=0.3)
    similarity_threshold = Column(Float, default=0.79)
    rag_limit = Column(Integer, default=20)
    model_name = Column(String, default="gpt-3.5-turbo")
    top_p = Column(Float, default=1.0)
    presence_penalty = Column(Float, default=0.0)
    frequency_penalty = Column(Float, default=0.0)
    max_tokens = Column(Integer, default=512)
    system_message = Column(String, default="")
    expressions = Column(String, default="")
