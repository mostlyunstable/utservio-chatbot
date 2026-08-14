import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, index=True, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    session_state = Column(Text, nullable=True)

    messages = relationship(
        "ConversationMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ConversationMessage.created_at",
    )


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(
        String, ForeignKey("conversations.id"), index=True, nullable=False
    )
    role = Column(String, nullable=False)  # user, assistant, system, tool
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")


class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    category = Column(String)
    description = Column(Text)

    # Pricing Semantics
    price_amount = Column(
        String
    )  # Storing as String to prevent float rounding, or could be numeric
    price_currency = Column(String)
    pricing_type = Column(String)  # e.g. starting_from, fixed, per_unit
    price_unit = Column(String)  # e.g. per fan, per room

    active = Column(Integer, default=1)  # 1 for active, 0 for inactive

    # Provenance
    source_url = Column(String)
    source_domain = Column(String)
    retrieved_at = Column(DateTime)
    last_verified_at = Column(DateTime)
    content_hash = Column(String)
    extraction_method = Column(String)

    areas = relationship(
        "ServiceArea", secondary="service_availability", back_populates="services"
    )


class ServiceArea(Base):
    __tablename__ = "service_areas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    city = Column(String)
    state = Column(String)
    pincode = Column(String)
    active = Column(Integer, default=1)

    # Provenance
    source_url = Column(String)
    source_domain = Column(String)
    retrieved_at = Column(DateTime)
    last_verified_at = Column(DateTime)
    extraction_method = Column(String)

    services = relationship(
        "Service", secondary="service_availability", back_populates="areas"
    )


class ServiceAvailability(Base):
    __tablename__ = "service_availability"
    service_id = Column(
        Integer, ForeignKey("services.id", ondelete="CASCADE"), primary_key=True
    )
    service_area_id = Column(
        Integer, ForeignKey("service_areas.id", ondelete="CASCADE"), primary_key=True
    )
