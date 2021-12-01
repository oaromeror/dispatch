import base64
import json

from fastapi import BackgroundTasks

from dispatch.conversation import service as conversation_service
from dispatch.conversation.enums import ConversationButtonActions
from dispatch.conversation.messaging import send_feedack_to_user
from dispatch.database.core import SessionLocal
from dispatch.feedback import service as feedback_service
from dispatch.incident import flows as incident_flows
from dispatch.incident import service as incident_service
from dispatch.incident.enums import IncidentStatus
from dispatch.plugin import service as plugin_service
from dispatch.plugins.dispatch_slack import service as dispatch_slack_service
from dispatch.report import flows as report_flows
from dispatch.report.models import ExecutiveReportCreate, TacticalReportCreate
from dispatch.task import service as task_service
from dispatch.task.models import TaskStatus, TaskCreate, Task, TaskUpdate
from .config import (
    SLACK_COMMAND_ASSIGN_ROLE_SLUG,
    SLACK_COMMAND_ENGAGE_ONCALL_SLUG,
    SLACK_COMMAND_REPORT_EXECUTIVE_SLUG,
    SLACK_COMMAND_REPORT_TACTICAL_SLUG,
    SLACK_COMMAND_ASSIGN_TASK_SLUG, SLACK_COMMAND_ADD_LEARNED_LESSON_SLUG,
)
from .decorators import slack_background_task
from .modals.feedback.handlers import (
    rating_feedback_from_submitted_form,
    create_rating_feedback_modal,
)
from .modals.feedback.views import RatingFeedbackCallbackId
from .modals.incident.enums import (
    AddTimelineEventCallbackId,
    UpdateIncidentCallbackId,
    ReportIncidentCallbackId,
    UpdateParticipantCallbackId,
    UpdateNotificationsGroupCallbackId,
)
from .modals.incident.handlers import (
    report_incident_from_submitted_form,
    add_timeline_event_from_submitted_form,
    update_incident_from_submitted_form,
    update_notifications_group_from_submitted_form,
    update_participant_from_submitted_form,
    update_report_incident_modal,
    update_update_participant_modal,
)
from .modals.workflow.handlers import run_workflow_submitted_form, update_workflow_modal
from .modals.workflow.views import RunWorkflowCallbackId
from .service import get_user_email, send_message, get_user_info_by_id
from ...feedback.enums import FeedbackRating
from ...feedback.messaging import send_learned_lesson_notification
from ...feedback.models import FeedbackCreate
from ...incident.models import IncidentUpdate, IncidentRead
from ...messaging.strings import INCIDENT_TASK_NEW_NOTIFICATION
from ...task.flows import send_task_notification


def base64_decode(input: str):
    """Returns a b64 decoded string."""
    return base64.b64decode(input.encode("ascii")).decode("ascii")


def handle_modal_action(action: dict, background_tasks: BackgroundTasks):
    """Handles all modal actions."""
    view_data = action["view"]
    view_data["private_metadata"] = json.loads(view_data["private_metadata"])

    action_id = view_data["callback_id"]
    incident_id = view_data["private_metadata"].get("incident_id")

    channel_id = view_data["private_metadata"].get("channel_id")
    user_id = action["user"]["id"]
    user_email = action["user"]["email"]

    for f in action_functions(action_id):
        background_tasks.add_task(f, user_id, user_email, channel_id, incident_id, action)


def action_functions(action_id: str):
    """Determines which function needs to be run."""
    action_mappings = {
        AddTimelineEventCallbackId.submit_form: [add_timeline_event_from_submitted_form],
        ReportIncidentCallbackId.submit_form: [report_incident_from_submitted_form],
        UpdateParticipantCallbackId.submit_form: [update_participant_from_submitted_form],
        UpdateIncidentCallbackId.submit_form: [update_incident_from_submitted_form],
        UpdateNotificationsGroupCallbackId.submit_form: [
            update_notifications_group_from_submitted_form
        ],
        RunWorkflowCallbackId.submit_form: [run_workflow_submitted_form],
        RatingFeedbackCallbackId.submit_form: [rating_feedback_from_submitted_form],
    }

    # this allows for unique action blocks e.g. invite-user or invite-user-1, etc
    for key in action_mappings.keys():
        if key in action_id:
            return action_mappings[key]
    return []


async def handle_slack_action(*, db_session, client, request, background_tasks):
    """Handles slack action message."""
    # We resolve the user's email
    user_id = request["user"]["id"]
    user_email = await dispatch_slack_service.get_user_email_async(client, user_id)

    request["user"]["email"] = user_email

    # When there are no exceptions within the dialog submission, your app must respond with 200 OK with an empty body.
    response_body = {}
    if request["type"] == "view":
        handle_modal_action(request, background_tasks)
    if request["type"] == "view_submission":
        handle_modal_action(request, background_tasks)
        # For modals we set "response_action" to "clear" to close all views in the modal.
        # An empty body is currently not working.
        response_body = {"response_action": "clear"}
    elif request["type"] == "dialog_submission":
        handle_dialog_action(request, background_tasks, db_session=db_session)
    elif request["type"] == "block_actions":
        handle_block_action(request, background_tasks)

    return response_body


def block_action_functions(action: str):
    """Interprets the action and routes it to the appropriate function."""
    action_mappings = {
        ConversationButtonActions.invite_user.value: [add_user_to_conversation],
        ConversationButtonActions.provide_feedback.value: [create_rating_feedback_modal],
        ConversationButtonActions.update_task_status.value: [update_task_status],
        # Note these are temporary for backward compatibility of block ids and should be remove in a future release
        "ConversationButtonActions.invite_user": [add_user_to_conversation],
        "ConversationButtonActions.provide_feedback": [create_rating_feedback_modal],
        "ConversationButtonActions.update_task_status": [
            update_task_status,
        ],
        UpdateParticipantCallbackId.update_view: [update_update_participant_modal],
        ReportIncidentCallbackId.update_view: [update_report_incident_modal],
        RunWorkflowCallbackId.update_view: [update_workflow_modal],
    }

    # this allows for unique action blocks e.g. invite-user or invite-user-1, etc
    for key in action_mappings.keys():
        if key in action:
            return action_mappings[key]
    return []


def handle_dialog_action(action: dict, background_tasks: BackgroundTasks, db_session: SessionLocal):
    """Handles all dialog actions."""
    channel_id = action["channel"]["id"]
    conversation = conversation_service.get_by_channel_id_ignoring_channel_type(
        db_session=db_session, channel_id=channel_id
    )
    incident_id = conversation.incident_id

    user_id = action["user"]["id"]
    user_email = action["user"]["email"]

    action_id = action["callback_id"]

    for f in dialog_action_functions(action_id):
        background_tasks.add_task(f, user_id, user_email, channel_id, incident_id, action)


def handle_block_action(action: dict, background_tasks: BackgroundTasks):
    """Handles a standalone block action."""
    # TODO (kglisson) align our use of action_ids and block_ids
    if action.get("view"):
        view_data = action["view"]
        view_data["private_metadata"] = json.loads(view_data["private_metadata"])

        incident_id = view_data["private_metadata"].get("incident_id")
        channel_id = view_data["private_metadata"].get("channel_id")
        action_id = action["actions"][0]["action_id"]
    else:
        incident_id = action["actions"][0]["value"]
        channel_id = action["channel"]["id"]
        action_id = action["actions"][0]["block_id"]

    user_id = action["user"]["id"]
    user_email = action["user"]["email"]

    for f in block_action_functions(action_id):
        background_tasks.add_task(f, user_id, user_email, channel_id, incident_id, action)


@slack_background_task
def add_user_to_conversation(
    user_id: str,
    user_email: str,
    channel_id: str,
    incident_id: int,
    action: dict,
    db_session=None,
    slack_client=None,
):
    """Adds a user to a conversation."""
    incident = incident_service.get(db_session=db_session, incident_id=incident_id)
    if not incident:
        message = "Sorry, we cannot add you to this incident it does not exist."
        dispatch_slack_service.send_ephemeral_message(slack_client, channel_id, user_id, message)
    elif incident.status == IncidentStatus.closed:
        message = f"Sorry, we cannot add you to a closed incident. " \
                  f"Please reach out to the incident commander ({incident.commander.individual.name}) for details."
        dispatch_slack_service.send_ephemeral_message(slack_client, channel_id, user_id, message)
    else:
        dispatch_slack_service.add_users_to_conversation(
            slack_client, incident.conversation.channel_id, [user_id]
        )
        message = f"Success! We've added you to incident {incident.name}. " \
                  f"Please check your side bar for the new channel."
        dispatch_slack_service.send_ephemeral_message(slack_client, channel_id, user_id, message)


@slack_background_task
def update_task_status(
    user_id: str,
    user_email: str,
    channel_id: str,
    incident_id: int,
    action: dict,
    db_session=None,
    slack_client=None,
):
    """Updates a task based on user input."""
    action_type, external_task_id_b64 = action["actions"][0]["value"].split("-")
    external_task_id = base64_decode(external_task_id_b64)

    resolve = True
    task_status = TaskStatus.resolved
    if action_type == "reopen":
        resolve = False
        task_status = TaskStatus.open

    # we only update the external task allowing syncing to care of propagation to dispatch
    task = task_service.get(db_session=db_session, task_id=external_task_id)

    # avoid external calls if we are already in the desired state
    if resolve and task.status == TaskStatus.resolved:
        message = "Task is already resolved."
        dispatch_slack_service.send_ephemeral_message(slack_client, channel_id, user_id, message)
        return

    if not resolve and task.status == TaskStatus.open:
        message = "Task is already open."
        dispatch_slack_service.send_ephemeral_message(slack_client, channel_id, user_id, message)
        return

    if task.incident.incident_review_document:
        # we don't currently have a good way to get the correct file_id (we don't store a task <-> relationship)
        # lets try in both the incident doc and PIR doc
        drive_task_plugin = plugin_service.get_active_instance(
            db_session=db_session, project_id=task.incident.project.id, plugin_type="task"
        )

        try:
            file_id = task.incident.incident_document.resource_id
            drive_task_plugin.instance.update(file_id, external_task_id, resolved=resolve)
        except Exception:
            file_id = task.incident.incident_review_document.resource_id
            drive_task_plugin.instance.update(file_id, external_task_id, resolved=resolve)
    else:
        task_in = TaskUpdate(**{'status': task_status, 'assignees': []})
        task_service.update(db_session=db_session, task_in=task_in, task=task)

    status = "resolved" if task_status == TaskStatus.resolved else "re-opened"
    message = f"Task successfully {status}."
    dispatch_slack_service.send_ephemeral_message(slack_client, channel_id, user_id, message)


@slack_background_task
def handle_engage_oncall_action(
    user_id: str,
    user_email: str,
    channel_id: str,
    incident_id: int,
    action: dict,
    db_session=None,
    slack_client=None,
):
    """Adds and pages based on the oncall modal."""
    oncall_service_external_id = action["submission"]["oncall_service_external_id"]
    page = action["submission"]["page"]

    oncall_individual, oncall_service = incident_flows.incident_engage_oncall_flow(
        user_email, incident_id, oncall_service_external_id, page=page, db_session=db_session
    )

    if not oncall_individual and not oncall_service:
        message = "Could not engage oncall. Oncall service plugin not enabled."

    if not oncall_individual and oncall_service:
        message = f"A member of {oncall_service.name} is already in the conversation."

    if oncall_individual and oncall_service:
        message = f"You have successfully engaged {oncall_individual.name} from the {oncall_service.name} oncall rotation."

    dispatch_slack_service.send_ephemeral_message(slack_client, channel_id, user_id, message)


@slack_background_task
def handle_tactical_report_create(
    user_id: str,
    user_email: str,
    channel_id: str,
    incident_id: int,
    action: dict,
    db_session=None,
    slack_client=None,
):
    """Handles the creation of a tactical report."""
    tactical_report_in = TacticalReportCreate(
        conditions=action["submission"]["conditions"],
        actions=action["submission"]["actions"],
        needs=action["submission"]["needs"],
    )

    incident = incident_service.get(db_session=db_session, incident_id=incident_id)

    incident_in = IncidentUpdate(
        title=incident.title,
        description=incident.description,
        incident_type=incident.incident_type,
        incident_priority=incident.incident_priority,
        status=incident.status,
        team_id=incident.team_id,
        team_name=incident.team_name,
        tags=incident.tags,
        platform=action["submission"]["platform"],
        product=action["submission"]["product"],
    )

    # we don't allow visibility to be set in slack so we copy it over
    incident_in.visibility = incident.visibility
    incident_service.update(
        db_session=db_session, incident=incident, incident_in=incident_in
    )

    report_flows.create_tactical_report(
        user_email=user_email,
        incident_id=incident_id,
        tactical_report_in=tactical_report_in,
        db_session=db_session,
    )

    # we let the user know that the report has been sent to the tactical group
    send_feedack_to_user(
        incident.conversation.channel_id,
        incident.project.id,
        user_id,
        f"The tactical report has been emailed to the incident tactical group ({incident.tactical_group.email}).",
        db_session,
    )


@slack_background_task
def handle_executive_report_create(
    user_id: str,
    user_email: str,
    channel_id: str,
    incident_id: int,
    action: dict,
    db_session=None,
    slack_client=None,
):
    """Handles the creation of executive reports."""
    executive_report_in = ExecutiveReportCreate(
        current_status=action["submission"]["current_status"],
        overview=action["submission"]["overview"],
        next_steps=action["submission"]["next_steps"],
    )
    incident = incident_service.get(db_session=db_session, incident_id=incident_id)
    executive_report = report_flows.create_executive_report(
        user_email=user_email,
        incident_id=incident_id,
        executive_report_in=executive_report_in,
        db_session=db_session,
    )

    # we let the user know that the report has been created
    send_feedack_to_user(
        incident.conversation.channel_id,
        incident.project.id,
        user_id,
        f"The executive report document has been created and can be found in the incident storage here: {executive_report.document.weblink}",
        db_session,
    )

    # we let the user know that the report has been sent to the notifications group
    send_feedack_to_user(
        incident.conversation.channel_id,
        incident.project.id,
        user_id,
        f"The executive report has been emailed to the incident notifications group ({incident.notifications_group.email}).",
        db_session,
    )


@slack_background_task
def handle_assign_role_action(
    user_id: str,
    user_email: str,
    channel_id: str,
    incident_id: int,
    action: dict,
    db_session=None,
    slack_client=None,
):
    """Massages slack dialog data into something that Dispatch can use."""
    assignee_user_id = action["submission"]["participant"]
    assignee_role = action["submission"]["role"]
    assignee_email = get_user_email(client=slack_client, user_id=assignee_user_id)
    incident_flows.incident_assign_role_flow(user_email, incident_id, assignee_email, assignee_role)


@slack_background_task
def handle_assign_task_action(
    user_id: str,
    user_email: str,
    channel_id: str,
    incident_id: int,
    action: dict,
    db_session=None,
    slack_client=None,
):
    """Massages slack dialog data into something that Dispatch can use."""
    assignee_user_id = action["submission"]["participant"]
    description = action["submission"]["task"]
    assignee_email = get_user_email(client=slack_client, user_id=assignee_user_id)

    incident = incident_service.get(db_session=db_session, incident_id=incident_id)

    task = TaskCreate()
    task.tickets = []
    task.incident = incident
    task.creator = {"individual": {"email": user_email}}
    task.owner = {"individual": {"email": assignee_email}}
    task.assignees = [
        {"individual": {"email": assignee_email}}
    ]
    task.description = description

    task_service.create(db_session=db_session, task_in=task)
    send_task_notification(
        incident,
        INCIDENT_TASK_NEW_NOTIFICATION,
        task.assignees,
        task.description,
        task.weblink,
        db_session,
    )


@slack_background_task
def handle_add_learned_lesson(
    user_id: str,
    user_email: str,
    channel_id: str,
    incident_id: int,
    action: dict,
    db_session=None,
    slack_client=None,
):
    """Massages slack dialog data into something that Dispatch can use."""
    feedback = action["submission"]["lesson"]

    incident = incident_service.get(db_session=db_session, incident_id=incident_id)
    rating = FeedbackRating.neither_satisfied_nor_dissatisfied.value

    feedback_in = FeedbackCreate(rating=rating, feedback=feedback, project=incident.project)
    feedback = feedback_service.create(db_session=db_session, feedback_in=feedback_in)

    incident.feedback.append(feedback)
    db_session.add(incident)
    db_session.commit()

    send_message(
        client=slack_client,
        conversation_id=user_id,
        text="Thank you for your feedback!",
    )

    user = get_user_info_by_id(client=slack_client, user_id=user_id)["real_name"]

    send_learned_lesson_notification(incident=incident, feedback=feedback, db_session=db_session, user=user)


def dialog_action_functions(action: str):
    """Interprets the action and routes it to the appropriate function."""
    action_mappings = {
        SLACK_COMMAND_ASSIGN_ROLE_SLUG: [handle_assign_role_action],
        SLACK_COMMAND_ENGAGE_ONCALL_SLUG: [handle_engage_oncall_action],
        SLACK_COMMAND_REPORT_EXECUTIVE_SLUG: [handle_executive_report_create],
        SLACK_COMMAND_REPORT_TACTICAL_SLUG: [handle_tactical_report_create],
        SLACK_COMMAND_ASSIGN_TASK_SLUG: [handle_assign_task_action],
        SLACK_COMMAND_ADD_LEARNED_LESSON_SLUG: [handle_add_learned_lesson]
    }

    # this allows for unique action blocks e.g. invite-user or invite-user-1, etc
    for key in action_mappings.keys():
        if key in action:
            return action_mappings[key]
    return []
