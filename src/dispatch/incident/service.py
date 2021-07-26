import logging
from datetime import datetime, timedelta
from typing import List, Optional

import requests
from cachetools.func import lru_cache

from dispatch.database.core import SessionLocal
from dispatch.event import service as event_service
from dispatch.incident_cost import service as incident_cost_service
from dispatch.incident_priority import service as incident_priority_service
from dispatch.incident_type import service as incident_type_service
from dispatch.participant import flows as participant_flows
from dispatch.participant_role.models import ParticipantRoleType
from dispatch.plugin import service as plugin_service
from dispatch.project import service as project_service
from dispatch.tag import service as tag_service
from dispatch.tag.models import TagUpdate, TagCreate
from dispatch.term import service as term_service
from dispatch.term.models import TermUpdate
from .enums import IncidentStatus
from .models import Incident, IncidentUpdate
from ..config import INCIDENT_DEVOPS_ENDPOINT, FILTER_FUNCTIONAL_TEAMS

log = logging.getLogger(__name__)


def assign_incident_role(
    db_session: SessionLocal,
    incident: Incident,
    reporter_email: str,
    role: ParticipantRoleType,
):
    """Assigns incident roles."""
    # We resolve the incident role email
    # default to reporter if we don't have an oncall plugin enabled
    assignee_email = reporter_email

    oncall_plugin = plugin_service.get_active_instance(
        db_session=db_session, project_id=incident.project.id, plugin_type="oncall"
    )
    service_id = None
    if role == ParticipantRoleType.incident_commander:
        # default to reporter
        if incident.incident_type.commander_service:
            service = incident.incident_type.commander_service
            service_id = service.id
            if oncall_plugin:
                assignee_email = oncall_plugin.instance.get(service_id=service.external_id)
                if incident.incident_priority.page_commander:
                    oncall_plugin.instance.page(
                        service_id=service.external_id,
                        incident_name=incident.name,
                        incident_title=incident.title,
                        incident_description=incident.description,
                    )

    elif role == ParticipantRoleType.liaison.value:
        if incident.incident_type.liaison_service:
            service = incident.incident_type.liaison_service
            service_id = service.id
            if oncall_plugin:
                assignee_email = oncall_plugin.instance.get(service_id=service.external_id)

    # Add a new participant (duplicate participants with different roles will be updated)
    participant_flows.add_participant(
        assignee_email,
        incident,
        db_session,
        service_id=service_id,
        role=role,
    )


def get(*, db_session, incident_id: int) -> Optional[Incident]:
    """Returns an incident based on the given id."""
    return db_session.query(Incident).filter(Incident.id == incident_id).first()


def get_by_name(*, db_session, project_id: int, incident_name: str) -> Optional[Incident]:
    """Returns an incident based on the given name."""
    return (
        db_session.query(Incident)
            .filter(Incident.name == incident_name)
            .filter(Incident.project_id == project_id)
            .first()
    )


def get_all(*, db_session, project_id: int) -> List[Optional[Incident]]:
    """Returns all incidents."""
    return db_session.query(Incident).filter(Incident.project_id == project_id)


def get_all_by_status(
    *, db_session, status: str, project_id: int, skip=0, limit=100
) -> List[Optional[Incident]]:
    """Returns all incidents based on the given status."""
    return (
        db_session.query(Incident)
            .filter(Incident.status == status)
            .filter(Incident.project_id == project_id)
            .offset(skip)
            .limit(limit)
            .all()
    )


def get_all_last_x_hours_by_status(
    *, db_session, status: str, hours: int, project_id: int, skip=0, limit=100
) -> List[Optional[Incident]]:
    """Returns all incidents of a given status in the last x hours."""
    now = datetime.utcnow()

    if status == IncidentStatus.active.value:
        return (
            db_session.query(Incident)
                .filter(Incident.status == IncidentStatus.active.value)
                .filter(Incident.created_at >= now - timedelta(hours=hours))
                .filter(Incident.project_id == project_id)
                .offset(skip)
                .limit(limit)
                .all()
        )

    if status == IncidentStatus.stable.value:
        return (
            db_session.query(Incident)
                .filter(Incident.status == IncidentStatus.stable.value)
                .filter(Incident.stable_at >= now - timedelta(hours=hours))
                .filter(Incident.project_id == project_id)
                .offset(skip)
                .limit(limit)
                .all()
        )

    if status == IncidentStatus.closed.value:
        return (
            db_session.query(Incident)
                .filter(Incident.status == IncidentStatus.closed.value)
                .filter(Incident.closed_at >= now - timedelta(hours=hours))
                .filter(Incident.project_id == project_id)
                .offset(skip)
                .limit(limit)
                .all()
        )


def get_all_by_incident_type(
    *, db_session, incident_type: str, project_id: int, skip=0, limit=100
) -> List[Optional[Incident]]:
    """Returns all incidents with the given incident type."""
    return (
        db_session.query(Incident)
            .filter(Incident.incident_type.name == incident_type)
            .filter(Incident.project_id == project_id)
            .offset(skip)
            .limit(limit)
            .all()
    )


def create(
    *,
    db_session,
    incident_priority: str,
    incident_type: str,
    reporter_email: str,
    title: str,
    status: str,
    description: str,
    tags: List[dict],
    team_id: str = None,
    team_name: str = None,
    report_source: str = None,
    project: str = None,
    visibility: str = None,
) -> Incident:
    """Creates a new incident."""
    if not project:
        project = project_service.get_default(db_session=db_session)
        if not project:
            raise Exception("No project specified and no default has been defined.")
    else:
        project = project_service.get_by_name(db_session=db_session, name=project["name"])

    # We get the incident type by name
    if not incident_type:
        incident_type = incident_type_service.get_default(db_session=db_session, project_id=project.id)
        if not incident_type:
            raise Exception("No incident type specified and no default has been defined.")
    else:
        incident_type = incident_type_service.get_by_name(
            db_session=db_session, project_id=project.id, name=incident_type["name"]
        )

        if not incident_type.enabled:
            raise Exception("Incident type must be enabled.")

    # We get the incident priority by name
    if not incident_priority:
        incident_priority = incident_priority_service.get_default(
            db_session=db_session, project_id=project.id
        )
        if not incident_priority:
            raise Exception("No incident priority specified and no default has been defined.")
    else:
        incident_priority = incident_priority_service.get_by_name(
            db_session=db_session, project_id=project.id, name=incident_priority["name"]
        )

        if not incident_priority.enabled:
            raise Exception("Incident priority must be enabled.")

    if not visibility:
        visibility = incident_type.visibility

    tag_objs = []
    for t in tags:
        tag_objs.append(tag_service.get_or_create(db_session=db_session, tag_in=TagCreate(**t)))

    # We create the incident
    incident = Incident(
        title=title,
        description=description,
        status=status,
        incident_type=incident_type,
        incident_priority=incident_priority,
        visibility=visibility,
        tags=tag_objs,
        report_source=report_source,
        team_id=team_id,
        team_name=team_name,
        project=project,
    )
    db_session.add(incident)
    db_session.commit()

    event_service.log(
        db_session=db_session,
        source="Dispatch Core App",
        description="Incident created",
        incident_id=incident.id,
    )

    # Add other incident roles (e.g. commander and liaison)
    assign_incident_role(db_session, incident, reporter_email, ParticipantRoleType.reporter)

    assign_incident_role(
        db_session, incident, reporter_email, ParticipantRoleType.incident_commander
    )

    assign_incident_role(db_session, incident, reporter_email, ParticipantRoleType.liaison)

    return incident


def update(*, db_session, incident: Incident, incident_in: IncidentUpdate) -> Incident:
    """Updates an existing incident."""
    incident_priority = incident_priority_service.get_by_name(
        db_session=db_session,
        project_id=incident.project.id,
        name=incident_in.incident_priority.name,
    )

    if not incident_priority.enabled:
        raise Exception("Incident priority must be enabled.")

    incident_type = incident_type_service.get_by_name(
        db_session=db_session, project_id=incident.project.id, name=incident_in.incident_type.name
    )

    if not incident_type.enabled:
        raise Exception("Incident type must be enabled.")

    tags = []
    for t in incident_in.tags:
        tags.append(tag_service.get_or_create(db_session=db_session, tag_in=TagUpdate(**t)))

    terms = []
    for t in incident_in.terms:
        terms.append(term_service.get_or_create(db_session=db_session, term_in=TermUpdate(**t)))

    duplicates = []
    for d in incident_in.duplicates:
        duplicates.append(get(db_session=db_session, incident_id=d.id))

    incident_costs = []
    for incident_cost in incident_in.incident_costs:
        incident_costs.append(
            incident_cost_service.get_or_create(
                db_session=db_session, incident_cost_in=incident_cost
            )
        )

    update_data = incident_in.dict(
        skip_defaults=True,
        exclude={
            "commander",
            "duplicates",
            "incident_costs",
            "incident_priority",
            "incident_type",
            "reporter",
            "status",
            "tags",
            "terms",
            "visibility",
            "report_source",
            "team",
            "project",
        },
    )

    for field in update_data.keys():
        setattr(incident, field, update_data[field])

    incident.duplicates = duplicates
    incident.incident_costs = incident_costs
    incident.incident_priority = incident_priority
    incident.incident_type = incident_type
    incident.status = incident_in.status
    incident.tags = tags
    incident.terms = terms
    incident.visibility = incident_in.visibility

    db_session.add(incident)
    db_session.commit()

    return incident


def delete(*, db_session, incident_id: int):
    """Deletes an existing incident."""
    db_session.query(Incident).filter(Incident.id == incident_id).delete()
    db_session.commit()


class CommunicationError(Exception):
    ...


def send_created_incident_quality_event(incident: Incident):
    try:
        events_url = f"{INCIDENT_DEVOPS_ENDPOINT}/incidents/dispatch"
        data = {
            "id": incident.name,
            "reporter_email": incident.reporter.individual.email,
            "report_source": incident.report_source,
            "creation_time": incident.created_at.strftime('%Y-%m-%dT%H:%M:%S%Z'),
            "team_id": incident.team_id
        }
        response = requests.post(url=events_url, json=data)
        if not response.ok:
            log.error(f"Error posting to bold API: {response.text}")
    except ConnectionError:
        log.error(f"Error posting to bold API")


def send_stabilized_incident_quality_event(incident: Incident):
    try:
        events_url = f"{INCIDENT_DEVOPS_ENDPOINT}/incidents/dispatch"
        data = {
            "id": incident.name,
            "stabilization_time": incident.stable_at.strftime('%Y-%m-%dT%H:%M:%S%Z')
        }
        response = requests.patch(url=events_url, json=data)
        if not response.ok:
            log.error(f"Error posting to bold API: {response.text}")
    except ConnectionError:
        log.error(f"Error posting to bold API")


def send_closed_incident_quality_event(incident: Incident):
    try:
        events_url = f"{INCIDENT_DEVOPS_ENDPOINT}/incidents/dispatch"
        events = sorted(incident.events, key=lambda x: x.started_at, reverse=False)
        initial_event_time = events[0].started_at
        data = {
            "id": incident.name,
            "close_time": incident.closed_at.strftime('%Y-%m-%dT%H:%M:%S%Z'),
            "outage_start_time": initial_event_time.strftime('%Y-%m-%dT%H:%M:%S%Z')
        }
        response = requests.patch(url=events_url, json=data)
        if not response.ok:
            log.error(f"Error posting to bold API: {response.text}")
    except ConnectionError:
        log.error(f"Error posting to bold API")


@lru_cache(maxsize=32)
def get_teams():
    try:
        teams_url = f"{INCIDENT_DEVOPS_ENDPOINT}/teams/azure-devops"
        response = requests.get(url=teams_url)

        if not response.ok:
            log.error(f"Error posting to bold API: {response.text}")
            return []

        teams = response.json()["teams"]

        if FILTER_FUNCTIONAL_TEAMS:
            teams = filter(lambda x: not x.get("is_functional"), teams)

        return sorted(teams, key=lambda x: x.get("name"), reverse=False)
    except ConnectionError:
        log.error(f"Error posting to bold API")
