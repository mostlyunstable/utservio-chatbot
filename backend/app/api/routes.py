import json
import logging
import random
import re
import string
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from ..db.database import get_db
from ..db.models import (
    Conversation,
    ConversationMessage,
    Service,
    ServiceArea,
    ServiceAvailability,
)
from ..models.chat import (
    ChatRequest,
    ChatResponse,
    HistoryResponse,
    MessageModel,
    ServiceModel,
)
from ..services.knowledge import BusinessKnowledgeService
from ..services.llm_provider import UTservioLLMProvider

router = APIRouter()
logger = logging.getLogger("utservio_api")

llm_provider: UTservioLLMProvider | None = None
try:
    llm_provider = UTservioLLMProvider()
except ValueError as e:
    logger.warning(f"LLM Provider initialization warning: {e}")


@router.get("/health")
async def health_check():
    return {"status": "healthy"}


@router.get("/chat/{session_id}/history", response_model=HistoryResponse)
async def get_history(session_id: str, db: AsyncSession = Depends(get_db)):  # noqa: B008
    stmt = (
        select(Conversation)
        .where(Conversation.session_id == session_id)
        .options(selectinload(Conversation.messages))
    )
    result = await db.execute(stmt)
    conversation = result.scalar_one_or_none()

    if not conversation:
        return HistoryResponse(session_id=session_id, messages=[])

    messages = [
        MessageModel(role=msg.role, content=msg.content)
        for msg in conversation.messages
    ]
    return HistoryResponse(session_id=session_id, messages=messages)


@router.get("/services", response_model=list[ServiceModel])
async def get_services(db: AsyncSession = Depends(get_db)):  # noqa: B008
    stmt = select(Service)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: Request,
    chat_req: ChatRequest,
    db: AsyncSession = Depends(get_db),  # noqa: B008
):
    # Rate Limiting
    _ = request.app.state.limiter
    logger.info(f"Session {chat_req.session_id}: Received chat request")

    if not llm_provider:
        raise HTTPException(
            status_code=500,
            detail="Backend configuration error: LLM Provider not initialized",
        )

    try:
        # Find or create conversation
        stmt = select(Conversation).where(
            Conversation.session_id == chat_req.session_id
        )
        result = await db.execute(stmt)
        conversation = result.scalar_one_or_none()

        if not conversation:
            conversation = Conversation(session_id=chat_req.session_id)
            db.add(conversation)
            await db.commit()
            await db.refresh(conversation)

        # Store user message in history
        user_msg = ConversationMessage(
            conversation_id=conversation.id, role="user", content=chat_req.message
        )
        db.add(user_msg)
        await db.commit()

        # Load or initialize session state
        state = {
            "step": "WELCOME",
            "service_id": None,
            "service_name": None,
            "location_id": None,
            "location_name": None,
            "date": None,
            "time_slot": None,
        }
        if conversation.session_state:
            try:
                loaded = json.loads(str(conversation.session_state))
                if isinstance(loaded, dict):
                    state.update(loaded)
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Failed to load session state: {e}")

        # Helper to normalize comparison
        msg_clean = chat_req.message.strip()
        msg_lower = msg_clean.lower()

        # Global commands & Back Navigation
        if msg_lower == "main menu" or msg_lower == "reset":
            state = {
                "step": "WELCOME",
                "service_id": None,
                "service_name": None,
                "location_id": None,
                "location_name": None,
                "date": None,
                "time_slot": None,
            }
        elif msg_lower == "back":
            step = state["step"]
            if step == "SELECT_LOCATION":
                state["step"] = "SELECT_SERVICE"
            elif step == "SHOW_SERVICE_DETAILS":
                state["step"] = "SELECT_LOCATION"
            elif step == "SELECT_DATE":
                state["step"] = "SHOW_SERVICE_DETAILS"
            elif step == "SELECT_TIME":
                state["step"] = "SELECT_DATE"
            elif step == "REVIEW_BOOKING":
                state["step"] = "SELECT_TIME"
        elif msg_lower == "change service":
            state["step"] = "SELECT_SERVICE"
        elif msg_lower == "change location":
            state["step"] = "SELECT_LOCATION"
        elif msg_lower == "change date":
            state["step"] = "SELECT_DATE"
        elif msg_lower == "change time":
            state["step"] = "SELECT_TIME"

        # Explicit State Transition Logic
        response_type = "options"
        response_options: list[str] = []
        response_data: dict[str, Any] | None = None
        response_text = ""

        # Fetch active services/locations helper
        async def get_all_db_services():
            srv_res = await db.execute(select(Service).where(Service.active == 1))
            return srv_res.scalars().all()

        async def get_db_service_by_name(name):
            srv_res = await db.execute(
                select(Service).where(Service.name.ilike(name.strip()))
            )
            return srv_res.scalars().first()

        async def get_db_area_by_name(name):
            area_res = await db.execute(
                select(ServiceArea).where(ServiceArea.name.ilike(name.strip()))
            )
            return area_res.scalars().first()

        # Perform navigation flow matching
        flow_matched = False
        step = state["step"]

        if step == "WELCOME":
            if msg_lower in ["book a service", "book"]:
                state["step"] = "SELECT_SERVICE"
                flow_matched = True
            elif msg_lower == "explore services":
                services = await get_all_db_services()
                names = [s.name for s in services]
                response_text = (
                    "Here are the home cleaning services available:\n"
                    + "\n".join(f"- {n}" for n in names)
                )
                response_type = "options"
                response_options = ["Book a Service", "Check Pricing", "Main Menu"]
                flow_matched = True
            elif msg_lower == "check pricing":
                state["step"] = "SELECT_SERVICE"
                response_text = "Select a service to check its verified local pricing:"
                flow_matched = True
            elif msg_lower == "service areas":
                area_res = await db.execute(
                    select(ServiceArea).where(ServiceArea.active == 1)
                )
                areas = area_res.scalars().all()
                names = [a.name for a in areas]
                response_text = (
                    "We currently serve the following areas in Chennai:\n"
                    + "\n".join(f"- {n}" for n in names)
                )
                response_type = "options"
                response_options = ["Book a Service", "Main Menu"]
                flow_matched = True

        elif step == "SELECT_SERVICE":
            service = await get_db_service_by_name(msg_clean)
            if service:
                state["service_id"] = service.id
                state["service_name"] = service.name
                state["step"] = "SELECT_LOCATION"
                flow_matched = True
            else:
                # If they entered "explore" or menu items, handle them
                if msg_lower == "main menu":
                    state["step"] = "WELCOME"
                    flow_matched = True

        elif step == "SELECT_LOCATION":
            area = await get_db_area_by_name(msg_clean)
            if area:
                # Verify link exists
                link_res = await db.execute(
                    select(ServiceAvailability).where(
                        ServiceAvailability.service_id == state["service_id"],
                        ServiceAvailability.service_area_id == area.id,
                    )
                )
                link = link_res.scalars().first()
                if link:
                    state["location_id"] = area.id
                    state["location_name"] = area.name
                    state["step"] = "SHOW_SERVICE_DETAILS"
                    flow_matched = True
                else:
                    response_text = (
                        f"Sorry, {state['service_name']} is not available in {area.name}."
                    )
                    flow_matched = True
            else:
                response_text = f"Sorry, Utservio does not serve {msg_clean}."
                flow_matched = True

        elif step == "SHOW_SERVICE_DETAILS":
            if msg_lower == "check availability":
                state["step"] = "SELECT_DATE"
                flow_matched = True

        elif step == "SELECT_DATE":
            if msg_lower in ["today", "tomorrow", "choose date"]:
                state["date"] = msg_clean.capitalize()
                state["step"] = "SELECT_TIME"
                flow_matched = True
            elif len(msg_clean) > 3 and not msg_lower.startswith("change"):
                state["date"] = msg_clean
                state["step"] = "SELECT_TIME"
                flow_matched = True

        elif step == "SELECT_TIME":
            slots = ["9 AM – 12 PM", "12 PM – 3 PM", "3 PM – 6 PM", "6 PM – 9 PM"]
            matching_slot = next(
                (
                    s
                    for s in slots
                    if s.lower() == msg_lower
                    or s.replace(" – ", " - ").lower() == msg_lower
                ),
                None,
            )
            if matching_slot:
                state["time_slot"] = matching_slot
                state["step"] = "REVIEW_BOOKING"
                flow_matched = True

        elif step == "REVIEW_BOOKING" and msg_lower == "confirm booking":
            state["step"] = "CONFIRMATION"
            flow_matched = True

        # AI Intent Parser Fallback if user typed free-form text and flow was not matched
        if not flow_matched and msg_lower not in [
            "back",
            "main menu",
            "reset",
            "change service",
            "change location",
            "change date",
            "change time",
        ]:
            # Run intent extractor
            intent_system_prompt = """
            You are a structured parser for the UTservio chatbot.
            Your job is to parse the user's natural language request and extract intent details as JSON.
            The services available are: "Fan Cleaning", "Sweep And Mop", "Bathroom Cleaning", "Car Cleaning", "Dusting".
            The service areas are: "Perungudi", "Thoraipakkam", "Sholinganallur", "Karapakkam", "OMR (Old Mahabalipuram Road)".

            Output ONLY valid JSON with this format:
            {
              "service": null or string (one of the exact service names above),
              "location": null or string (one of the exact service areas above),
              "date": null or string (e.g. "today", "tomorrow" or a specific date/day),
              "intent": null or "booking" or "pricing" or "support"
            }
            Do not explain your output. Output only raw JSON.
            """
            parsed_json = {}
            try:
                raw_parse = await llm_provider.generate_response(
                    user_message=chat_req.message, system_prompt=intent_system_prompt
                )
                json_match = re.search(r"\{.*\}", raw_parse, re.DOTALL)
                if json_match:
                    parsed_json = json.loads(json_match.group(0))
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Failed to parse LLM intent JSON: {e}")

            parsed_service_name = parsed_json.get("service")
            parsed_location_name = parsed_json.get("location")
            parsed_date = parsed_json.get("date")

            # Validate and apply parsed variables
            extracted_something = False
            if parsed_service_name:
                service = await get_db_service_by_name(parsed_service_name)
                if service:
                    state["service_id"] = service.id
                    state["service_name"] = service.name
                    state["step"] = "SELECT_LOCATION"
                    extracted_something = True

            if parsed_location_name and state["service_id"]:
                area = await get_db_area_by_name(parsed_location_name)
                if area:
                    link_res = await db.execute(
                        select(ServiceAvailability).where(
                            ServiceAvailability.service_id == state["service_id"],
                            ServiceAvailability.service_area_id == area.id,
                        )
                    )
                    if link_res.scalars().first():
                        state["location_id"] = area.id
                        state["location_name"] = area.name
                        state["step"] = "SHOW_SERVICE_DETAILS"
                        extracted_something = True

            if parsed_date and state["location_id"]:
                state["date"] = parsed_date.capitalize()
                state["step"] = "SELECT_TIME"
                extracted_something = True

            if extracted_something:
                response_text = f"Got it. {state['service_name']}"
                if state["location_name"]:
                    response_text += f" in {state['location_name']}"
                if state["date"]:
                    response_text += f" for {state['date']}"
                response_text += "."
                flow_matched = True
            else:
                # Normal AI Fallback Grounding
                bk_service = BusinessKnowledgeService(db)
                services_context = await bk_service.search_services(
                    chat_req.message.split()[0] if chat_req.message else ""
                )
                if (
                    services_context
                    == "No matching services or locations found in the authoritative UTservio database."
                    and len(chat_req.message.split()) > 1
                ):
                    services_context = await bk_service.search_services(
                        chat_req.message.split()[1]
                    )

                knowledge_context = ""
                if (
                    services_context
                    != "No matching services or locations found in the authoritative UTservio database."
                ):
                    knowledge_context = "Available Business Facts:\n" + services_context

                # Prepare history for LLM
                history_for_llm = []
                if knowledge_context:
                    history_for_llm.append(
                        {
                            "role": "system",
                            "content": f"BUSINESS CONTEXT:\n{knowledge_context}",
                        }
                    )
                # Fetch history
                hist_stmt = (
                    select(ConversationMessage)
                    .where(ConversationMessage.conversation_id == conversation.id)
                    .order_by(ConversationMessage.created_at.desc())
                    .limit(10)
                )
                hist_result = await db.execute(hist_stmt)
                recent_messages = list(hist_result.scalars().all())
                recent_messages.reverse()
                for msg in recent_messages[:-1]:
                    history_for_llm.append(
                        {"role": str(msg.role), "content": str(msg.content)}
                    )

                response_text = await llm_provider.generate_response(
                    user_message=chat_req.message, history=history_for_llm
                )
                response_type = "options"
                response_options = [
                    "Book a Service",
                    "Explore Services",
                    "Check Pricing",
                    "Main Menu",
                ]
                flow_matched = True

        # Render Response UI parameters based on resolved step
        step = state["step"]

        if step == "WELCOME" and not response_text:
            response_text = "Hi! Welcome to UTservio. How can I help you today?"
            response_type = "options"
            response_options = [
                "Book a Service",
                "Explore Services",
                "Check Pricing",
                "Service Areas",
            ]

        elif step == "SELECT_SERVICE":
            services = await get_all_db_services()
            if not response_text:
                response_text = "Please select a service you would like to book:"
            response_type = "service_cards"
            response_data = {
                "services": [
                    {
                        "id": s.id,
                        "name": s.name,
                        "description": s.description,
                        "price_amount": s.price_amount,
                        "price_currency": s.price_currency,
                        "pricing_type": s.pricing_type,
                        "price_unit": s.price_unit,
                    }
                    for s in services
                ]
            }
            response_options = ["Back", "Main Menu"]

        elif step == "SELECT_LOCATION":
            stmt_area = (
                select(ServiceArea)
                .join(
                    ServiceAvailability,
                    ServiceAvailability.service_area_id == ServiceArea.id,
                )
                .where(ServiceAvailability.service_id == state["service_id"])
            )
            res_area = await db.execute(stmt_area)
            areas = res_area.scalars().all()

            if not response_text:
                response_text = f"Where would you like to book {state['service_name']}?"
            response_type = "location_cards"
            response_options = [str(a.name) for a in areas] + ["Back"]

        elif step == "SHOW_SERVICE_DETAILS":
            stmt_svc = select(Service).where(Service.id == state["service_id"])
            res_svc = await db.execute(stmt_svc)
            svc = res_svc.scalars().first()
            if not svc:
                raise HTTPException(status_code=404, detail="Service not found")

            if not response_text:
                response_text = f"Here is the pricing for {state['service_name']} in {state['location_name']}:"
            response_type = "price_card"
            response_data = {
                "service_name": svc.name,
                "location_name": state["location_name"],
                "price_amount": svc.price_amount,
                "price_currency": svc.price_currency,
                "pricing_type": svc.pricing_type,
                "price_unit": svc.price_unit,
                "source_url": svc.source_url,
                "last_verified_at": svc.last_verified_at.isoformat()
                if svc.last_verified_at
                else None,
            }
            response_options = [
                "Check Availability",
                "Change Service",
                "Change Location",
            ]

        elif step == "SELECT_DATE":
            if not response_text:
                response_text = "Please select a date for your appointment:"
            response_type = "date_picker"
            response_options = ["Today", "Tomorrow", "Choose Date", "Back"]

        elif step == "SELECT_TIME":
            if not response_text:
                response_text = f"Select a time slot for {state['date']}:"
            response_type = "time_slots"
            response_options = [
                "9 AM – 12 PM",
                "12 PM – 3 PM",
                "3 PM – 6 PM",
                "6 PM – 9 PM",
                "Back",
            ]

        elif step == "REVIEW_BOOKING":
            stmt_svc = select(Service).where(Service.id == state["service_id"])
            res_svc = await db.execute(stmt_svc)
            svc = res_svc.scalars().first()
            if not svc:
                raise HTTPException(status_code=404, detail="Service not found")

            if not response_text:
                response_text = "Please review your booking details:"
            response_type = "confirmation_card"
            response_data = {
                "status": "Pending",
                "service_name": state["service_name"],
                "location_name": state["location_name"],
                "date": state["date"],
                "time_slot": state["time_slot"],
                "price_amount": svc.price_amount,
                "price_currency": svc.price_currency,
                "pricing_type": svc.pricing_type,
                "price_unit": svc.price_unit,
            }
            response_options = [
                "Confirm Booking",
                "Change Service",
                "Change Location",
                "Change Date",
                "Change Time",
            ]

        elif step == "CONFIRMATION":
            stmt_svc = select(Service).where(Service.id == state["service_id"])
            res_svc = await db.execute(stmt_svc)
            svc = res_svc.scalars().first()
            if not svc:
                raise HTTPException(status_code=404, detail="Service not found")

            booking_id = "UTS-" + "".join(
                random.choices(string.ascii_uppercase + string.digits, k=6)
            )
            if not response_text:
                response_text = "Your booking is confirmed!"
            response_type = "confirmation_card"
            response_data = {
                "status": "Confirmed",
                "booking_id": booking_id,
                "service_name": state["service_name"],
                "location_name": state["location_name"],
                "date": state["date"],
                "time_slot": state["time_slot"],
                "price_amount": svc.price_amount,
                "price_currency": svc.price_currency,
                "pricing_type": svc.pricing_type,
                "price_unit": svc.price_unit,
            }
            response_options = ["Book Another Service", "Main Menu"]

            # Clear booking fields on confirmation step so next is fresh
            state = {
                "step": "WELCOME",
                "service_id": None,
                "service_name": None,
                "location_id": None,
                "location_name": None,
                "date": None,
                "time_slot": None,
            }

        # Save assistant message in DB history
        asst_msg = ConversationMessage(
            conversation_id=conversation.id, role="assistant", content=response_text
        )
        db.add(asst_msg)

        # Save session state in DB
        conversation.session_state = json.dumps(state)  # type: ignore[assignment]
        await db.commit()

        logger.info(
            f"Session {chat_req.session_id}: Responding with type {response_type}"
        )
        return ChatResponse(
            message=response_text,
            session_id=chat_req.session_id,
            type=response_type,
            options=response_options,
            data=response_data,
            metadata={"source": "utservio_backend"},
        )
    except Exception as e:  # noqa: BLE001
        logger.error(
            f"Session {chat_req.session_id}: Failed to generate response: {e!s}"
        )
        raise HTTPException(
            status_code=503,
            detail="The AI assistant is currently unavailable. Please try again later.",
        )
