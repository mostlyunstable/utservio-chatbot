import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.db.database import AsyncSessionLocal
from app.db.models import Service, ServiceArea, ServiceAvailability
from app.main import app

client = TestClient(app)


async def setup_test_db_data():
    """Ensure test data exists in DB before running tests."""
    async with AsyncSessionLocal() as session:
        # Clear existing availabilities
        await session.execute(ServiceAvailability.__table__.delete())
        await session.execute(ServiceArea.__table__.delete())
        await session.execute(Service.__table__.delete())
        await session.commit()

        # Add test service
        svc = Service(
            name="Fan Cleaning",
            category="Cleaning",
            description="Deep cleaning of ceiling fans",
            price_amount="149",
            price_currency="INR",
            pricing_type="starting_from",
            price_unit="per fan",
            active=1,
        )
        session.add(svc)
        await session.commit()
        await session.refresh(svc)

        # Add test area
        area = ServiceArea(name="Perungudi", active=1)
        session.add(area)
        await session.commit()
        await session.refresh(area)

        # Map them
        mapping = ServiceAvailability(service_id=svc.id, service_area_id=area.id)
        session.add(mapping)
        await session.commit()


@pytest.mark.asyncio
async def test_state_machine_happy_path():
    await setup_test_db_data()
    sess_id = f"test-happy-{uuid.uuid4()}"

    # 1. Welcome Step
    response = client.post(
        "/api/chat", json={"session_id": sess_id, "message": "reset"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "options"
    assert "Book a Service" in data["options"]

    # 2. Select Service Step
    response = client.post(
        "/api/chat", json={"session_id": sess_id, "message": "Book a Service"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "service_cards"
    assert len(data["data"]["services"]) > 0
    assert data["data"]["services"][0]["name"] == "Fan Cleaning"

    # 3. Select Location Step
    response = client.post(
        "/api/chat", json={"session_id": sess_id, "message": "Fan Cleaning"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "location_cards"
    assert "Perungudi" in data["options"]

    # 4. Show Details Step
    response = client.post(
        "/api/chat", json={"session_id": sess_id, "message": "Perungudi"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "price_card"
    assert data["data"]["service_name"] == "Fan Cleaning"
    assert data["data"]["price_amount"] == "149"
    assert data["data"]["pricing_type"] == "starting_from"

    # 5. Select Date Step
    response = client.post(
        "/api/chat", json={"session_id": sess_id, "message": "Check Availability"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "date_picker"
    assert "Tomorrow" in data["options"]

    # 6. Select Time Step
    response = client.post(
        "/api/chat", json={"session_id": sess_id, "message": "Tomorrow"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "time_slots"
    assert "3 PM – 6 PM" in data["options"]

    # 7. Review Booking Step
    response = client.post(
        "/api/chat", json={"session_id": sess_id, "message": "3 PM – 6 PM"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "confirmation_card"
    assert data["data"]["status"] == "Pending"
    assert data["data"]["service_name"] == "Fan Cleaning"
    assert data["data"]["location_name"] == "Perungudi"
    assert data["data"]["date"] == "Tomorrow"
    assert data["data"]["time_slot"] == "3 PM – 6 PM"

    # 8. Confirmation Step
    response = client.post(
        "/api/chat", json={"session_id": sess_id, "message": "Confirm Booking"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "confirmation_card"
    assert data["data"]["status"] == "Confirmed"
    assert data["data"]["booking_id"].startswith("UTS-")


@pytest.mark.asyncio
async def test_invalid_service_and_location():
    await setup_test_db_data()
    sess_id = f"test-invalid-{uuid.uuid4()}"

    # Go to select service
    client.post("/api/chat", json={"session_id": sess_id, "message": "Book a Service"})

    # Send invalid service
    response = client.post(
        "/api/chat", json={"session_id": sess_id, "message": "Invalid Service Name"}
    )
    assert response.status_code == 200
    data = response.json()
    # It should ask to select a service again
    assert data["type"] == "service_cards"

    # Send valid service to go to select location
    client.post("/api/chat", json={"session_id": sess_id, "message": "Fan Cleaning"})

    # Send invalid location
    response = client.post(
        "/api/chat", json={"session_id": sess_id, "message": "Velachery"}
    )
    assert response.status_code == 200
    data = response.json()
    # It should say not available in Velachery and prompt location again
    assert "does not serve Velachery" in data["message"]


@pytest.mark.asyncio
async def test_back_navigation():
    await setup_test_db_data()
    sess_id = f"test-back-{uuid.uuid4()}"

    # Welcome -> SELECT_SERVICE -> SELECT_LOCATION
    client.post("/api/chat", json={"session_id": sess_id, "message": "Book a Service"})
    client.post("/api/chat", json={"session_id": sess_id, "message": "Fan Cleaning"})

    # Go back to SELECT_SERVICE
    response = client.post("/api/chat", json={"session_id": sess_id, "message": "Back"})
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "service_cards"


@pytest.mark.asyncio
async def test_change_flow_commands():
    await setup_test_db_data()
    sess_id = f"test-change-{uuid.uuid4()}"

    # Book Service -> Fan Cleaning -> Perungudi -> Check Availability -> Tomorrow -> 3 PM – 6 PM
    client.post("/api/chat", json={"session_id": sess_id, "message": "Book a Service"})
    client.post("/api/chat", json={"session_id": sess_id, "message": "Fan Cleaning"})
    client.post("/api/chat", json={"session_id": sess_id, "message": "Perungudi"})
    client.post(
        "/api/chat", json={"session_id": sess_id, "message": "Check Availability"}
    )
    client.post("/api/chat", json={"session_id": sess_id, "message": "Tomorrow"})
    client.post("/api/chat", json={"session_id": sess_id, "message": "3 PM – 6 PM"})

    # Change Location
    response = client.post(
        "/api/chat", json={"session_id": sess_id, "message": "Change Location"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "location_cards"


@pytest.mark.asyncio
@patch(
    "app.services.llm_provider.UTservioLLMProvider.generate_response",
    new_callable=AsyncMock,
)
async def test_natural_language_to_guided_flow(mock_generate_response):
    await setup_test_db_data()
    sess_id = f"test-nl-{uuid.uuid4()}"

    # Mock the intent extractor response
    mock_generate_response.return_value = json.dumps(
        {
            "service": "Fan Cleaning",
            "location": "Perungudi",
            "date": "tomorrow",
            "intent": "booking",
        }
    )

    # Send natural language query
    response = client.post(
        "/api/chat",
        json={
            "session_id": sess_id,
            "message": "I want to book fan cleaning in Perungudi for tomorrow",
        },
    )
    assert response.status_code == 200
    data = response.json()
    # It should process the intents and jump straight to time slots selection since date is tomorrow
    assert data["type"] == "time_slots"
    assert "3 PM – 6 PM" in data["options"]


@pytest.mark.asyncio
async def test_empty_database():
    sess_id = f"test-empty-{uuid.uuid4()}"

    # Clear DB data
    async with AsyncSessionLocal() as session:
        await session.execute(ServiceAvailability.__table__.delete())
        await session.execute(ServiceArea.__table__.delete())
        await session.execute(Service.__table__.delete())
        await session.commit()

    # Request services
    response = client.post(
        "/api/chat", json={"session_id": sess_id, "message": "Book a Service"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "service_cards"
    assert len(data["data"]["services"]) == 0


@pytest.mark.asyncio
@patch(
    "app.services.llm_provider.UTservioLLMProvider.generate_response",
    new_callable=AsyncMock,
)
async def test_llm_failure_during_intent_parsing(mock_generate_response):
    await setup_test_db_data()
    sess_id = f"test-llm-fail-{uuid.uuid4()}"

    # Mock generator raising error on first call (intent parsing), succeeding on second
    mock_generate_response.side_effect = [
        Exception("Intent parser failed"),
        "I can help you book a service. Please select from the menu below."
    ]

    # This should not crash the endpoint, it should fall back to general database error response
    # or polite fallback handler
    response = client.post(
        "/api/chat", json={"session_id": sess_id, "message": "I need cleaning"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "options"
    assert "Book a Service" in data["options"]
