from collections import Counter
from datetime import datetime
from typing import List, Optional, Any

from pydantic import validator
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
    String,
    Table,
    select
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from sqlalchemy_utils import TSVectorType

from dispatch.conference.models import ConferenceRead
from dispatch.config import (
    INCIDENT_RESOURCE_INCIDENT_REVIEW_DOCUMENT,
    INCIDENT_RESOURCE_INVESTIGATION_DOCUMENT,
    INCIDENT_RESOURCE_NOTIFICATIONS_GROUP,
    INCIDENT_RESOURCE_TACTICAL_GROUP,
)
from dispatch.conversation.models import ConversationRead
from dispatch.database.core import Base
from dispatch.document.models import DocumentRead
from dispatch.enums import Visibility
from dispatch.event.models import EventRead
from dispatch.incident_cost.models import IncidentCostRead, IncidentCostUpdate
from dispatch.incident_priority.models import (
    IncidentPriorityBase,
    IncidentPriorityCreate,
    IncidentPriorityRead,
)
from dispatch.incident_type.models import IncidentTypeCreate, IncidentTypeRead, IncidentTypeBase
from dispatch.models import DispatchBase, ProjectMixin, TimeStampMixin
from dispatch.participant.models import Participant, ParticipantRead, ParticipantUpdate
from dispatch.participant_role.models import ParticipantRole, ParticipantRoleType
from dispatch.project.models import ProjectRead
from dispatch.report.enums import ReportTypes
from dispatch.report.models import ReportRead
from dispatch.storage.models import StorageRead
from dispatch.tag.models import TagRead
from dispatch.ticket.models import TicketRead
from dispatch.workflow.models import WorkflowInstanceRead
from .enums import IncidentStatus

assoc_incident_terms = Table(
    "assoc_incident_terms",
    Base.metadata,
    Column("incident_id", Integer, ForeignKey("incident.id", ondelete="CASCADE")),
    Column("term_id", Integer, ForeignKey("term.id", ondelete="CASCADE")),
    PrimaryKeyConstraint("incident_id", "term_id"),
)

assoc_incident_tags = Table(
    "assoc_incident_tags",
    Base.metadata,
    Column("incident_id", Integer, ForeignKey("incident.id", ondelete="CASCADE")),
    Column("tag_id", Integer, ForeignKey("tag.id", ondelete="CASCADE")),
    PrimaryKeyConstraint("incident_id", "tag_id"),
)


class Incident(Base, TimeStampMixin, ProjectMixin):
    id = Column(Integer, primary_key=True)
    cf = Column(Boolean)
    description = Column(String, nullable=False)
    name = Column(String)
    platform = Column(String)
    product = Column(String)
    report_source = Column(String)
    status = Column(String, default=IncidentStatus.active.value)
    team_id = Column(String)
    team_name = Column(String)
    title = Column(String, nullable=False)
    visibility = Column(String, default=Visibility.open)

    # auto generated
    closed_at = Column(DateTime)
    reported_at = Column(DateTime, default=datetime.utcnow)
    stable_at = Column(DateTime)

    search_vector = Column(
        TSVectorType(
            "title", "description", "name", weights={"name": "A", "title": "B", "description": "C"}
        )
    )

    @hybrid_property
    def commander(self):
        commander = None
        if self.participants:
            most_recent_assumed_at = self.created_at
            for p in self.participants:
                for pr in p.participant_roles:
                    if pr.role == ParticipantRoleType.incident_commander.value:
                        if pr.assumed_at > most_recent_assumed_at:
                            most_recent_assumed_at = pr.assumed_at
                            commander = p
        return commander

    @commander.expression
    def commander(cls):
        return (
            select([Participant])
            .where(Participant.incident_id == cls.id)
            .where(ParticipantRole.role == ParticipantRoleType.incident_commander.value)
            .order_by(ParticipantRole.assumed_at.desc())
            .first()
        )

    @hybrid_property
    def reporter(self):
        reporter = None
        if self.participants:
            most_recent_assumed_at = self.created_at
            for p in self.participants:
                for pr in p.participant_roles:
                    if pr.role == ParticipantRoleType.reporter.value:
                        if pr.assumed_at > most_recent_assumed_at:
                            most_recent_assumed_at = pr.assumed_at
                            reporter = p
        return reporter

    @reporter.expression
    def reporter(cls):
        return (
            select([Participant])
            .where(Participant.incident_id == cls.id)
            .where(ParticipantRole.role == ParticipantRoleType.reporter.value)
            .order_by(ParticipantRole.assumed_at.desc())
            .first()
        )

    @hybrid_property
    def tactical_group(self):
        if self.groups:
            for g in self.groups:
                if g.resource_type == INCIDENT_RESOURCE_TACTICAL_GROUP:
                    return g

    @hybrid_property
    def notifications_group(self):
        if self.groups:
            for g in self.groups:
                if g.resource_type == INCIDENT_RESOURCE_NOTIFICATIONS_GROUP:
                    return g

    @hybrid_property
    def incident_document(self):
        if self.documents:
            for d in self.documents:
                if d.resource_type == INCIDENT_RESOURCE_INVESTIGATION_DOCUMENT:
                    return d

    @hybrid_property
    def incident_review_document(self):
        if self.documents:
            for d in self.documents:
                if d.resource_type == INCIDENT_RESOURCE_INCIDENT_REVIEW_DOCUMENT:
                    return d

    @hybrid_property
    def tactical_reports(self):
        if self.reports:
            tactical_reports = [
                report for report in self.reports if report.type == ReportTypes.tactical_report
            ]
            return tactical_reports

    @hybrid_property
    def last_tactical_report(self):
        if self.tactical_reports:
            return sorted(self.tactical_reports, key=lambda r: r.created_at)[-1]

    @hybrid_property
    def executive_reports(self):
        if self.reports:
            executive_reports = [
                report for report in self.reports if report.type == ReportTypes.executive_report
            ]
            return executive_reports

    @hybrid_property
    def last_executive_report(self):
        if self.executive_reports:
            return sorted(self.executive_reports, key=lambda r: r.created_at)[-1]

    @hybrid_property
    def primary_team(self):
        if self.participants:
            teams = [p.team for p in self.participants]
            return Counter(teams).most_common(1)[0][0]

    @hybrid_property
    def primary_location(self):
        if self.participants:
            locations = [p.location for p in self.participants]
            return Counter(locations).most_common(1)[0][0]

    @hybrid_property
    def total_cost(self):
        if self.incident_costs:
            total_cost = 0
            for cost in self.incident_costs:
                total_cost += cost.amount
            return total_cost

    # resources
    incident_costs = relationship(
        "IncidentCost",
        backref="incident",
        cascade="all, delete-orphan",
        order_by="IncidentCost.created_at",
    )

    incident_priority = relationship("IncidentPriority", backref="incident")
    incident_priority_id = Column(Integer, ForeignKey("incident_priority.id"))
    incident_type = relationship("IncidentType", backref="incident")
    incident_type_id = Column(Integer, ForeignKey("incident_type.id"))

    conference = relationship(
        "Conference", uselist=False, backref="incident", cascade="all, delete-orphan"
    )
    conversation = relationship(
        "Conversation", uselist=False, backref="incident", cascade="all, delete-orphan"
    )
    documents = relationship(
        "Document", lazy="subquery", backref="incident", cascade="all, delete-orphan"
    )
    events = relationship("Event", backref="incident", cascade="all, delete-orphan")
    feedback = relationship("Feedback", backref="incident", cascade="all, delete-orphan")
    groups = relationship(
        "Group", lazy="subquery", backref="incident", cascade="all, delete-orphan"
    )
    participants = relationship("Participant", backref="incident", cascade="all, delete-orphan")
    reports = relationship("Report", backref="incident", cascade="all, delete-orphan")
    storage = relationship(
        "Storage", uselist=False, backref="incident", cascade="all, delete-orphan"
    )
    tags = relationship("Tag", secondary=assoc_incident_tags, backref="incidents")
    tasks = relationship("Task", backref="incident", cascade="all, delete-orphan")
    terms = relationship("Term", secondary=assoc_incident_terms, backref="incidents", lazy="joined")
    ticket = relationship("Ticket", uselist=False, backref="incident", cascade="all, delete-orphan")
    workflow_instances = relationship(
        "WorkflowInstance", backref="incident", cascade="all, delete-orphan"
    )

    # allow incidents to be marked as duplicate
    duplicate_id = Column(Integer, ForeignKey("incident.id"))
    duplicates = relationship("Incident", remote_side=[id], uselist=True)


# Pydantic models...
class IncidentBase(DispatchBase):
    title: str
    description: str
    status: Optional[IncidentStatus] = IncidentStatus.active
    visibility: Optional[Visibility]

    @validator("title")
    def title_required(cls, v):
        if not v:
            raise ValueError("must not be empty string")
        return v

    @validator("description")
    def description_required(cls, v):
        if not v:
            raise ValueError("must not be empty string")
        return v


class IncidentReadNested(IncidentBase):
    id: int
    cf: Optional[bool] = False
    closed_at: Optional[datetime] = None
    commander: Optional[ParticipantRead]
    created_at: Optional[datetime] = None
    incident_priority: IncidentPriorityRead
    incident_type: IncidentTypeRead
    name: str = None
    platform: Optional[str] = None
    product: Optional[str] = None
    report_source: Optional[str] = None
    reported_at: Optional[datetime] = None
    reporter: Optional[ParticipantRead]
    stable_at: Optional[datetime] = None
    team_id: Optional[str] = None
    team_name: Optional[str] = None


class IncidentCreate(IncidentBase):
    cf: Optional[bool] = False
    incident_priority: Optional[IncidentPriorityCreate]
    incident_type: Optional[IncidentTypeCreate]
    team_id: Optional[str] = None
    team_name: Optional[str] = None
    product: Optional[str] = None
    platform: Optional[str] = None
    project: ProjectRead
    report_source: Optional[str] = None
    tags: Optional[List[Any]] = []  # any until we figure out circular imports


class IncidentUpdate(IncidentBase):
    cf: Optional[bool] = False
    commander: Optional[ParticipantUpdate]
    duplicates: Optional[List[IncidentReadNested]] = []
    incident_costs: Optional[List[IncidentCostUpdate]] = []
    incident_priority: IncidentPriorityBase
    incident_type: IncidentTypeBase
    platform: Optional[str] = None
    product: Optional[str] = None
    report_source: Optional[str] = None
    reported_at: Optional[datetime] = None
    reporter: Optional[ParticipantUpdate]
    stable_at: Optional[datetime] = None
    tags: Optional[List[Any]] = []  # any until we figure out circular imports
    team_id: Optional[str] = None
    team_name: Optional[str] = None
    terms: Optional[List[Any]] = []  # any until we figure out circular imports


class IncidentRead(IncidentBase):
    id: int
    cf: Optional[bool] = False
    commander: Optional[ParticipantRead]
    conference: Optional[ConferenceRead] = None
    conversation: Optional[ConversationRead] = None
    created_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    documents: Optional[List[DocumentRead]] = []
    duplicates: Optional[List[IncidentReadNested]] = []
    events: Optional[List[EventRead]] = []
    incident_costs: Optional[List[IncidentCostRead]] = []
    incident_priority: IncidentPriorityRead
    incident_type: IncidentTypeRead
    name: str = None
    last_tactical_report: Optional[ReportRead]
    last_executive_report: Optional[ReportRead]
    participants: Optional[List[ParticipantRead]] = []
    platform: Optional[str] = None
    primary_team: Any
    primary_location: Any
    project: ProjectRead
    product: Optional[str] = None
    reporter: Optional[ParticipantRead]
    report_source: Optional[str] = None
    reported_at: Optional[datetime] = None
    stable_at: Optional[datetime] = None
    storage: Optional[StorageRead] = None
    tags: Optional[List[TagRead]] = []
    team_id: Optional[str] = None
    team_name: Optional[str] = None
    terms: Optional[List[Any]] = []  # any until we figure out circular imports
    ticket: Optional[TicketRead] = None
    total_cost: Optional[float]
    workflow_instances: Optional[List[WorkflowInstanceRead]] = []


class IncidentPagination(DispatchBase):
    items: List[IncidentRead] = []
    itemsPerPage: int
    page: int
    total: int
