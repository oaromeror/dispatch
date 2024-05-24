import copy
from enum import Enum
from typing import List

from jinja2 import Template

from dispatch.config import (
    INCIDENT_RESOURCE_CONVERSATION_REFERENCE_DOCUMENT,
    INCIDENT_RESOURCE_EXECUTIVE_REPORT_DOCUMENT,
    INCIDENT_RESOURCE_INCIDENT_FAQ_DOCUMENT,
    INCIDENT_RESOURCE_INCIDENT_REVIEW_DOCUMENT,
    INCIDENT_RESOURCE_INVESTIGATION_DOCUMENT,
    INCIDENT_RESOURCE_INVESTIGATION_SHEET,
)
from dispatch.conversation.enums import ConversationButtonActions
from dispatch.incident.enums import IncidentStatus


class MessageType(str, Enum):
    document_evergreen_reminder = "document-evergreen-reminder"
    incident_closed_information_review_reminder = "incident-closed-information-review-reminder"
    incident_daily_report = "incident-daily-report"
    incident_executive_report = "incident-executive-report"
    incident_feedback_daily_report = "incident-feedback-daily-report"
    incident_management_help_tips = "incident-management-help-tips"
    incident_notification = "incident-notification"
    incident_participant_suggested_reading = "incident-participant-suggested-reading"
    incident_participant_welcome = "incident-participant-welcome"
    incident_rating_feedback = "incident-rating-feedback"
    incident_resources_message = "incident-resources-message"
    incident_status_reminder = "incident-status-reminder"
    incident_tactical_report = "incident-tactical-report"
    incident_task_list = "incident-task-list"
    incident_task_reminder = "incident-task-reminder"
    incident_timeline_new = "incident-timeline-new"


INCIDENT_STATUS_DESCRIPTIONS = {
    IncidentStatus.active.value: "This incident is under active investigation.",
    IncidentStatus.stable.value: "This incident is stable, the bulk of the investigation has been completed "
    "or most of the risk has been mitigated.",
    IncidentStatus.closed.value: "This no longer requires additional involvement, long term incident action "
    "items have been assigned to their respective owners.",
}

INCIDENT_MANAGEMENT_CREATED = """
#{{channel}} - {{team}}: {{title}}.
"""

INCIDENT_TASK_REMINDER_DESCRIPTION = """
You are assigned to the following incident tasks.
This is a reminder that these tasks have passed their due date.
Please review and update them as appropriate. Resolving them will stop the reminders.""".replace(
    "\n", " "
).strip()

INCIDENT_TASK_LIST_DESCRIPTION = """The following are open incident tasks."""

DOCUMENT_EVERGREEN_REMINDER_DESCRIPTION = """
You are the owner of the following incident documents.
This is a reminder that these documents should be kept up to date in order to effectively
respond to incidents. Please review them and update, or clearly mark the documents as deprecated.""".replace(
    "\n", " "
).strip()

INCIDENT_FEEDBACK_DAILY_REPORT_DESCRIPTION = """
This is a daily report of feedback about incidents handled by you.""".replace(
    "\n", " "
).strip()

INCIDENT_DAILY_REPORT_TITLE = """
Incidents Daily Report""".replace(
    "\n", " "
).strip()

INCIDENT_DAILY_REPORT_DESCRIPTION = """
This is a daily report of incidents that are currently active and incidents that have been marked as
stable or closed in the last 24 hours.""".replace(
    "\n", " "
).strip()

INCIDENT_DAILY_REPORT_FOOTER_CONTEXT = """
For questions about an incident, please reach out to the incident's commander.""".replace(
    "\n", " "
).strip()

INCIDENT_REPORTER_DESCRIPTION = """
The person who reported the incident.""".replace(
    "\n", " "
).strip()

INCIDENT_COMMANDER_DESCRIPTION = """
The Incident Commander (IC) is responsible for
knowing the full context of the incident.""".replace(
    "\n", " "
).strip()

INCIDENT_COMMANDER_READDED_DESCRIPTION = """
{{ commander_fullname }} (Incident Commander) has been re-added to the conversation.
Please, handoff the Incident Commander role before leaving the conversation.""".replace(
    "\n", " "
).strip()

INCIDENT_TICKET_DESCRIPTION = """
Ticket for tracking purposes. It contains a description of
the incident and links to resources.""".replace(
    "\n", " "
).strip()

INCIDENT_CONVERSATION_DESCRIPTION = """
Private conversation for real-time discussion. All incident participants get added to it.
""".replace(
    "\n", " "
).strip()

INCIDENT_CONVERSATION_REFERENCE_DOCUMENT_DESCRIPTION = """
Document containing the list of slash commands available to the Incident Commander (IC)
and participants in the incident conversation.""".replace(
    "\n", " "
).strip()

INCIDENT_CONFERENCE_DESCRIPTION = """
Video conference and phone bridge to be used throughout the incident.
Password: {{conference_challenge if conference_challenge else 'N/A'}}
""".replace(
    "\n", ""
).strip()

INCIDENT_STORAGE_DESCRIPTION = """
Common storage for all incident artifacts and
documents. Add logs, screen captures, or any other data collected during the
investigation to this drive. It is shared with all incident participants.""".replace(
    "\n", " "
).strip()

INCIDENT_INVESTIGATION_DOCUMENT_DESCRIPTION = """
This is a document for all incident facts and context. All
incident participants are expected to contribute to this document.
It is shared with all incident participants.""".replace(
    "\n", " "
).strip()

INCIDENT_INVESTIGATION_SHEET_DESCRIPTION = """
This is a sheet for tracking impacted assets. All
incident participants are expected to contribute to this sheet.
It is shared with all incident participants.""".replace(
    "\n", " "
).strip()

INCIDENT_FAQ_DOCUMENT_DESCRIPTION = """
First time responding to an information security incident? This
document answers common questions encountered when
helping us respond to an incident.""".replace(
    "\n", " "
).strip()

INCIDENT_REVIEW_DOCUMENT_DESCRIPTION = """
This document will capture all lessons learned, questions, and action items raised during the incident.""".replace(
    "\n", " "
).strip()

INCIDENT_EXECUTIVE_REPORT_DOCUMENT_DESCRIPTION = """
This is a document that contains an executive report about the incident.""".replace(
    "\n", " "
).strip()

INCIDENT_DOCUMENT_DESCRIPTIONS = {
    INCIDENT_RESOURCE_CONVERSATION_REFERENCE_DOCUMENT: INCIDENT_CONVERSATION_REFERENCE_DOCUMENT_DESCRIPTION,
    INCIDENT_RESOURCE_EXECUTIVE_REPORT_DOCUMENT: INCIDENT_EXECUTIVE_REPORT_DOCUMENT_DESCRIPTION,
    INCIDENT_RESOURCE_INCIDENT_FAQ_DOCUMENT: INCIDENT_FAQ_DOCUMENT_DESCRIPTION,
    INCIDENT_RESOURCE_INCIDENT_REVIEW_DOCUMENT: INCIDENT_REVIEW_DOCUMENT_DESCRIPTION,
    INCIDENT_RESOURCE_INVESTIGATION_DOCUMENT: INCIDENT_INVESTIGATION_DOCUMENT_DESCRIPTION,
    INCIDENT_RESOURCE_INVESTIGATION_SHEET: INCIDENT_INVESTIGATION_SHEET_DESCRIPTION,
}

INCIDENT_PARTICIPANT_WELCOME_DESCRIPTION = """
You\'re being contacted because we think you may
be able to help us during this incident.
Please review the content below and join us in the
incident Slack channel.""".replace(
    "\n", " "
).strip()

INCIDENT_WELCOME_CONVERSATION_COPY = """
This is the incident conversation. Please pull in any
individuals you feel may be able to help resolve this incident.""".replace(
    "\n", " "
).strip()

INCIDENT_PARTICIPANT_SUGGESTED_READING_DESCRIPTION = """
Dispatch thinks the following documents might be
relevant to this incident.""".replace(
    "\n", " "
).strip()

INCIDENT_NOTIFICATION_PURPOSES_FYI = """
This message is for notification purposes only.""".replace(
    "\n", " "
).strip()

INCIDENT_CAN_REPORT_REMINDER = """
It's time to send a new CAN report. Go to the Demisto UI and run the
CAN Report playbook from the Playground Work Plan.""".replace(
    "\n", " "
).strip()

INCIDENT_VULNERABILITY_DESCRIPTION = """
We are tracking the details of the vulnerability that led to this incident
in the VUL Jira issue linked above.""".replace(
    "\n", " "
).strip()

INCIDENT_STABLE_DESCRIPTION = """
The risk has been contained and the incident marked as stable.""".replace(
    "\n", " "
).strip()

INCIDENT_CLOSED_DESCRIPTION = """
The incident has been resolved and marked as closed.""".replace(
    "\n", " "
).strip()

INCIDENT_TACTICAL_REPORT_DESCRIPTION = """
The following causes, actions, and consequences summarize the current status of the incident.""".replace(
    "\n", " "
).strip()

INCIDENT_NEW_ROLE_DESCRIPTION = """
{{assigner_fullname if assigner_fullname else assigner_email}} has assigned the role of {{assignee_role}}
 to {{assignee_fullname if assignee_fullname else assignee_email}}.
Please, contact {{assignee_fullname if assignee_fullname else assignee_email}}
about any questions or concerns.""".replace(
    "\n", " "
).strip()

INCIDENT_REPORT_REMINDER_DESCRIPTION = """You have not provided a {{report_type}} for this incident recently.
You can use `{{command}}` in the conversation to assist you in writing one.""".replace(
    "\n", " "
).strip()

INCIDENT_STATUS_REMINDER_DESCRIPTION = """You have not updated the status for this incident recently.
If the incident has been resolved,
you can use `{{command}}` in the conversation to assist you in closing your incident.""".replace(
    "\n", " "
).strip()

INCIDENT_TASK_NEW_DESCRIPTION = """
The following incident task has been created in the incident document.\n\n
*Description:* {{task_description}}\n\n
*Assignees:* {{task_assignees|join(',')}}"""

INCIDENT_TASK_RESOLVED_DESCRIPTION = """
The following incident task has been resolved in the incident document.\n\n
*Description:* {{task_description}}\n\n
*Assignees:* {{task_assignees|join(',')}}"""

INCIDENT_TIMELINE_NEW_DESCRIPTION = """
The following incident timeline event has been created in the incident document.\n\n
*Description:* {{timeline_description}}
*Creator:* {{creator}}
*Event date:* {{event_date}}
"""

INCIDENT_WORKFLOW_CREATED_DESCRIPTION = """
A new workflow instance has been created.
\n\n *Creator:* {{instance_creator_name}}
"""

INCIDENT_WORKFLOW_UPDATE_DESCRIPTION = """
This workflow's status has changed from *{{ instance_status_old }}* to *{{ instance_status_new }}*.
\n\n*Workflow Description*: {{workflow_description}}
\n\n *Creator:* {{instance_creator_name}}
"""

INCIDENT_WORKFLOW_COMPLETE_DESCRIPTION = """
This workflow's status has changed from *{{ instance_status_old }}* to *{{ instance_status_new }}*.
\n\n *Workflow Description:* {{workflow_description}}
\n\n *Creator:* {{instance_creator_name}}
{% if instance_artifacts %}
\n\n *Workflow Artifacts:*
\n\n {% for a in instance_artifacts %}- <{{a.weblink}}|{{a.name}}> \n\n{% endfor %}
{% endif %}
"""

INCIDENT_CLOSED_INFORMATION_REVIEW_REMINDER_DESCRIPTION = """
Thanks for closing incident {{name}}. Please, take a minute to review and update the following incident information in the <{{dispatch_ui_url}}|Dispatch Web UI>, if necessary:
\n • Incident Title: {{title}}
\n • Incident Description: {{description}}
\n • Incident Type: {{type}}
\n • Incident Priority: {{priority}}
\n\n
Also, please consider taking the following actions:
\n • Update or add any relevant tags to the incident using the <{{dispatch_ui_url}}|Dispatch Web UI>.
\n • Add any relevant, non-operational costs to the incident using the <{{dispatch_ui_url}}|Dispatch Web UI>.
\n • Review and close any incident tasks that are no longer relevant or required.
"""

INCIDENT_CLOSED_RATING_FEEDBACK_DESCRIPTION = """
Thanks for participating in the {{name}} ("{{title}}") incident. We would appreciate
if you could rate your experience and provide feedback."""

INCIDENT_MANAGEMENT_HELP_TIPS_MESSAGE_DESCRIPTION = """
Hey, I see you're the Incident Commander for {{name}} ("{{title}}").
Here are a few things to consider when managing the incident:
\n • Keep the incident and its status up to date using the Slack `{{update_command}}` command.
\n • Invite incident participants and team oncalls by mentioning them in the incident channel or
using the Slack `{{engage_oncall_command}}` command.
\n • Keep incident participants and stakeholders informed using the `{{tactical_report_command}}`
and `{{executive_report_command}}` commands.
\n • Get links to all incident resources including the Slack commands reference sheet and Security
Incident Response FAQ by running the `{{list_resources_command}}` command.
\n
To find a Slack command, simply type `/` in the message field or click the lightning bolt icon
to the left of the message field.
"""

INCIDENT_TYPE_CHANGE_DESCRIPTION = """
The incident type has been changed from {{ incident_type_old }} to {{ incident_type_new }}.""".replace(
    "\n", " "
).strip()

INCIDENT_STATUS_CHANGE_DESCRIPTION = """
The incident status has been changed from {{ incident_status_old }} to {{ incident_status_new }}.""".replace(
    "\n", " "
).strip()

INCIDENT_PRIORITY_CHANGE_DESCRIPTION = """
The incident priority has been changed from {{ incident_priority_old }} to {{ incident_priority_new }}.""".replace(
    "\n", " "
).strip()

INCIDENT_TEAM_CHANGE_DESCRIPTION = """
The incident team has been changed from {{ incident_team_old }} to {{ incident_team_new }}.""".replace(
    "\n", " "
).strip()

INCIDENT_NAME_WITH_ENGAGEMENT = {
    "title": "{{name}} Incident Notification",
    "title_link": "{{ticket_weblink}}",
    "text": INCIDENT_NOTIFICATION_PURPOSES_FYI,
    "button_text": "Join Incident",
    "button_value": "{{incident_id}}",
    "button_action": ConversationButtonActions.invite_user.value,
}

INCIDENT_NAME_WITH_ENGAGEMENT_NO_DESCRIPTION = {
    "title": "{{name}}",
    "title_link": "{{ticket_weblink}}",
    "text": "{{ignore}}",
    "button_text": "{{button_text}}",
    "button_value": "{{button_value}}",
    "button_action": "{{button_action}}",
}

INCIDENT_NAME = {
    "title": "{{name}} Incident Notification",
    "title_link": "{{ticket_weblink}}",
    "text": INCIDENT_NOTIFICATION_PURPOSES_FYI,
}

INCIDENT_TITLE = {"title": "Title", "text": "{{title}}"}

INCIDENT_TITLE_ES = {"title": "Incidente", "text": "{{name}} - {{title}}"}

INCIDENT_DESCRIPTION = {"title": "Description", "text": "{{description}}"}

INCIDENT_STATUS = {
    "title": "Status - {{status}}",
    "status_mapping": INCIDENT_STATUS_DESCRIPTIONS,
}

INCIDENT_TYPE = {"title": "Type - {{type}}", "text": "{{type_description}}"}

INCIDENT_PRIORITY = {
    "title": "Priority - {{priority}}",
    "text": "{{priority_description}}",
}

INCIDENT_PRIORITY_FYI = {
    "title": "Priority - {{priority}}",
    "text": "{{priority_description}}",
}

INCIDENT_REPORTER = {
    "title": "Reporter - {{reporter_fullname}}",
    "text": INCIDENT_REPORTER_DESCRIPTION,
}

INCIDENT_COMMANDER = {
    "title": "Commander - {{commander_fullname}}",
    "text": INCIDENT_COMMANDER_DESCRIPTION,
}

INCIDENT_TEAM = {
    "title": "Team",
    "text": "{{ team_name }}",
}

INCIDENT_REPORT_SOURCE = {
    "title": "Report source",
    "text": "{{ report_source }}",
}

INCIDENT_CONVERSATION = {
    "title": "Conversation",
    "title_link": "{{conversation_weblink}}",
    "text": "{{conversation}}.\n" + INCIDENT_CONVERSATION_DESCRIPTION,
}

INCIDENT_CONFERENCE = {
    "title": "Conference",
    "title_link": "{{conference_weblink}}",
    "text": INCIDENT_CONFERENCE_DESCRIPTION,
}

INCIDENT_STORAGE = {
    "title": "Storage",
    "title_link": "{{storage_weblink}}",
    "text": INCIDENT_STORAGE_DESCRIPTION,
}

INCIDENT_CONVERSATION_COMMANDS_REFERENCE_DOCUMENT = {
    "title": "Incident Conversation Commands Reference Document",
    "title_link": "{{conversation_commands_reference_document_weblink}}",
    "text": INCIDENT_CONVERSATION_REFERENCE_DOCUMENT_DESCRIPTION,
}

INCIDENT_INVESTIGATION_DOCUMENT = {
    "title": "Investigation Document",
    "title_link": "{{document_weblink}}",
    "text": INCIDENT_INVESTIGATION_DOCUMENT_DESCRIPTION,
}

INCIDENT_INVESTIGATION_SHEET = {
    "title": "Investigation Sheet",
    "title_link": "{{sheet_weblink}}",
    "text": INCIDENT_INVESTIGATION_SHEET_DESCRIPTION,
}

INCIDENT_REVIEW_DOCUMENT = {
    "title": "Review Document",
    "title_link": "{{review_document_weblink}}",
    "text": INCIDENT_REVIEW_DOCUMENT_DESCRIPTION,
}

INCIDENT_FAQ_DOCUMENT = {
    "title": "FAQ Document",
    "title_link": "{{faq_weblink}}",
    "text": INCIDENT_FAQ_DOCUMENT_DESCRIPTION,
}

INCIDENT_TYPE_CHANGE = {"title": "Incident Type Change", "text": INCIDENT_TYPE_CHANGE_DESCRIPTION}

INCIDENT_STATUS_CHANGE = {
    "title": "Status Change",
    "text": INCIDENT_STATUS_CHANGE_DESCRIPTION,
}

INCIDENT_PRIORITY_CHANGE = {
    "title": "Priority Change",
    "text": INCIDENT_PRIORITY_CHANGE_DESCRIPTION,
}

INCIDENT_TEAM_CHANGE = {
    "title": "Team Change",
    "text": INCIDENT_TEAM_CHANGE_DESCRIPTION,
}

INCIDENT_PARTICIPANT_SUGGESTED_READING_ITEM = {
    "title": "{{name}}",
    "title_link": "{{weblink}}",
    "text": "{{description}}",
}

INCIDENT_PARTICIPANT_WELCOME = {
    "title": "Welcome to {{name}}",
    "title_link": "{{ticket_weblink}}",
    "text": INCIDENT_PARTICIPANT_WELCOME_DESCRIPTION,
}

INCIDENT_PARTICIPANT_WELCOME_MESSAGE = [
    INCIDENT_PARTICIPANT_WELCOME,
    INCIDENT_TITLE,
    INCIDENT_DESCRIPTION,
    INCIDENT_STATUS,
    INCIDENT_TYPE,
    INCIDENT_PRIORITY,
    INCIDENT_REPORTER,
    INCIDENT_COMMANDER,
    INCIDENT_INVESTIGATION_DOCUMENT,
    INCIDENT_STORAGE,
    INCIDENT_CONFERENCE,
    INCIDENT_CONVERSATION_COMMANDS_REFERENCE_DOCUMENT,
    INCIDENT_FAQ_DOCUMENT,
]

INCIDENT_RESOURCES_MESSAGE = [
    INCIDENT_TITLE,
    INCIDENT_DESCRIPTION,
    INCIDENT_REPORTER,
    INCIDENT_COMMANDER,
    INCIDENT_INVESTIGATION_DOCUMENT,
    INCIDENT_REVIEW_DOCUMENT,
    INCIDENT_STORAGE,
    INCIDENT_CONFERENCE,
    INCIDENT_CONVERSATION_COMMANDS_REFERENCE_DOCUMENT,
    INCIDENT_FAQ_DOCUMENT,
]

INCIDENT_NOTIFICATION_COMMON = [INCIDENT_TITLE]

INCIDENT_NOTIFICATION = INCIDENT_NOTIFICATION_COMMON.copy()
INCIDENT_NOTIFICATION.extend(
    [
        INCIDENT_DESCRIPTION,
        INCIDENT_STATUS,
        INCIDENT_TEAM,
        INCIDENT_TYPE,
        INCIDENT_PRIORITY_FYI,
        INCIDENT_COMMANDER,
        INCIDENT_REPORT_SOURCE,
    ]
)

INCIDENT_CREATED_WELCOME = {"type": "header", "text": "A new incident has been created"}

INCIDENT_CREATED_NOTIFICATION = [
    INCIDENT_CREATED_WELCOME,
    INCIDENT_TITLE,
    INCIDENT_DESCRIPTION,
    INCIDENT_STATUS,
    INCIDENT_TYPE,
    INCIDENT_PRIORITY,
    INCIDENT_REPORTER,
    # INCIDENT_COMMANDER,
    INCIDENT_TEAM,
    INCIDENT_REPORT_SOURCE,
    INCIDENT_CONVERSATION,
    # INCIDENT_STORAGE,
    INCIDENT_CONFERENCE,
]

LEARNED_LESSON_TITLE = {"type": "header", "text": "Nueva lección aprendida"}

LEARNED_LESSONS = {"title": "Lecciones aprendidas", "text": "{{lessons}}"}

LEARNED_LESSON_NOTIFICATION = [
    LEARNED_LESSON_TITLE,
    {"title": "Lecciones:", "text": "{{lessons}}\n     _- {{user}}_"},
]

INCIDENT_TACTICAL_REPORT = [
    {"title": "Incident Tactical Report", "text": INCIDENT_TACTICAL_REPORT_DESCRIPTION},
    {"title": "Product", "text": "{{product}}"},
    {"title": "Platform", "text": "{{platform}}"},
    {"title": "Causes", "text": "{{conditions}}"},
    {"title": "Actions", "text": "{{actions}}"},
    {"title": "Consequences", "text": "{{needs}}"},
]

INCIDENT_EXECUTIVE_REPORT = [
    {"title": "Incident Title", "text": "{{title}}"},
    {"title": "Current Status", "text": "{{current_status}}"},
    {"title": "Overview", "text": "{{overview}}"},
    {"title": "Next Steps", "text": "{{next_steps}}"},
]

INCIDENT_REPORT_REMINDER = [
    {
        "title": "{{name}} Incident - {{report_type}} Reminder",
        "title_link": "{{ticket_weblink}}",
        "text": INCIDENT_REPORT_REMINDER_DESCRIPTION,
    },
    INCIDENT_TITLE,
]

INCIDENT_CREATED_MANAGER_REPORT = [
    {
        "title": "Se ha creado un nuevo incidente.",
        "text": INCIDENT_MANAGEMENT_CREATED,
    }
]

INCIDENT_STATUS_REMINDER = [
    {
        "title": "{{name}} Incident - Status Reminder",
        "title_link": "{{ticket_weblink}}",
        "text": INCIDENT_STATUS_REMINDER_DESCRIPTION,
    },
    INCIDENT_TITLE,
    INCIDENT_STATUS,
]

INCIDENT_TASK_REMINDER = [
    {"title": "Incident - {{ name }}", "text": "{{ title }}"},
    {"title": "Creator", "text": "{{ creator }}"},
    {"title": "Description", "text": "{{ description }}"},
    {"title": "Priority", "text": "{{ priority }}"},
    {"title": "Created At", "text": "", "datetime": "{{ created_at}}"},
    {"title": "Resolve By", "text": "", "datetime": "{{ resolve_by }}"},
    {"title": "Link", "text": "{{ weblink }}"},
]

DOCUMENT_EVERGREEN_REMINDER = [
    {"title": "Document", "text": "{{ name }}"},
    {"title": "Description", "text": "{{ description }}"},
    {"title": "Link", "text": "{{ weblink }}"},
]

INCIDENT_NEW_ROLE_NOTIFICATION = [
    {
        "title": "New {{assignee_role}} - {{assignee_fullname if assignee_fullname else assignee_email}}",
        "title_link": "{{assignee_weblink}}",
        "text": INCIDENT_NEW_ROLE_DESCRIPTION,
    }
]

INCIDENT_TASK_NEW_NOTIFICATION = [
    {
        "title": "New Incident Task",
        "text": INCIDENT_TASK_NEW_DESCRIPTION,
    }
]

INCIDENT_TASK_RESOLVED_NOTIFICATION = [
    {
        "title": "Resolved Incident Task",
        "title_link": "{{task_weblink}}",
        "text": INCIDENT_TASK_RESOLVED_DESCRIPTION,
    }
]

INCIDENT_TIMELINE_NEW_NOTIFICATION = [
    {
        "title": "New Timeline Event",
        "text": INCIDENT_TIMELINE_NEW_DESCRIPTION,
    }
]

INCIDENT_WORKFLOW_CREATED_NOTIFICATION = [
    {
        "title": "Workflow Created - {{workflow_name}}",
        "text": INCIDENT_WORKFLOW_CREATED_DESCRIPTION,
    }
]

INCIDENT_WORKFLOW_UPDATE_NOTIFICATION = [
    {
        "title": "Workflow Status Change - {{workflow_name}}",
        "title_link": "{{instance_weblink}}",
        "text": INCIDENT_WORKFLOW_UPDATE_DESCRIPTION,
    }
]

INCIDENT_WORKFLOW_COMPLETE_NOTIFICATION = [
    {
        "title": "Workflow Completed - {{workflow_name}}",
        "title_link": "{{instance_weblink}}",
        "text": INCIDENT_WORKFLOW_COMPLETE_DESCRIPTION,
    }
]

INCIDENT_COMMANDER_READDED_NOTIFICATION = [
    {"title": "Incident Commander Re-Added", "text": INCIDENT_COMMANDER_READDED_DESCRIPTION}
]

INCIDENT_CLOSED_INFORMATION_REVIEW_REMINDER_NOTIFICATION = [
    {
        "title": "{{name}} Incident - Information Review Reminder",
        "title_link": "{{dispatch_ui_url}}",
        "text": INCIDENT_CLOSED_INFORMATION_REVIEW_REMINDER_DESCRIPTION,
    }
]

INCIDENT_CLOSED_RATING_FEEDBACK_NOTIFICATION = [
    {
        "title": "{{name}} Incident - Rating and Feedback",
        "title_link": "{{ticket_weblink}}",
        "text": INCIDENT_CLOSED_RATING_FEEDBACK_DESCRIPTION,
        "button_text": "Provide Feeback",
        "button_value": "{{incident_id}}",
        "button_action": ConversationButtonActions.provide_feedback.value,
    }
]

INCIDENT_FEEDBACK_DAILY_REPORT = [
    {"title": "Incident", "text": "{{ name }}"},
    {"title": "Incident Title", "text": "{{ title }}"},
    {"title": "Rating", "text": "{{ rating }}"},
    {"title": "Feedback", "text": "{{ feedback }}"},
    {"title": "Participant", "text": "{{ participant }}"},
    {"title": "Created At", "text": "", "datetime": "{{ created_at}}"},
]

INCIDENT_DAILY_REPORT_HEADER = {
    "type": "header",
    "text": INCIDENT_DAILY_REPORT_TITLE,
}

INCIDENT_DAILY_REPORT_HEADER_DESCRIPTION = {
    "text": INCIDENT_DAILY_REPORT_DESCRIPTION,
}

INCIDENT_DAILY_REPORT_FOOTER = {
    "type": "context",
    "text": INCIDENT_DAILY_REPORT_FOOTER_CONTEXT,
}

INCIDENT_DAILY_REPORT = [
    INCIDENT_DAILY_REPORT_HEADER,
    INCIDENT_DAILY_REPORT_HEADER_DESCRIPTION,
    INCIDENT_DAILY_REPORT_FOOTER,
]

INCIDENT = [
    INCIDENT_NAME_WITH_ENGAGEMENT_NO_DESCRIPTION,
    INCIDENT_TITLE,
    INCIDENT_STATUS,
    INCIDENT_TYPE,
    INCIDENT_PRIORITY,
    INCIDENT_COMMANDER,
]

INCIDENT_MANAGEMENT_HELP_TIPS_MESSAGE = [
    {
        "title": "{{name}} Incident - Management Help Tips",
        "text": INCIDENT_MANAGEMENT_HELP_TIPS_MESSAGE_DESCRIPTION,
    }
]


def render_message_template(message_template: List[dict], **kwargs):
    """Renders the jinja data included in the template itself."""
    data = []
    new_copy = copy.deepcopy(message_template)
    for d in new_copy:
        if d.get("header"):
            d["header"] = Template(d["header"]).render(**kwargs)

        if d.get("title"):
            d["title"] = Template(d["title"]).render(**kwargs)

        if d.get("title_link"):
            d["title_link"] = Template(d["title_link"]).render(**kwargs)

            if d["title_link"] == "None":  # skip blocks with no content
                continue

            # skip blocks that do not have new links rendered, as no real value was provided
            if not d["title_link"]:
                continue

        if d.get("text"):
            d["text"] = Template(d["text"]).render(**kwargs)

        if d.get("button_text"):
            d["button_text"] = Template(d["button_text"]).render(**kwargs)

        if d.get("button_value"):
            d["button_value"] = Template(d["button_value"]).render(**kwargs)

        if d.get("button_action"):
            d["button_action"] = Template(d["button_action"]).render(**kwargs)

        if d.get("status_mapping"):
            d["text"] = d["status_mapping"][kwargs["status"]]

        if d.get("datetime"):
            d["datetime"] = Template(d["datetime"]).render(**kwargs)

        if d.get("context"):
            d["context"] = Template(d["context"]).render(**kwargs)

        data.append(d)
    return data
