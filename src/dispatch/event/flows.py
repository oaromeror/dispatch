from dispatch.plugin import service as plugin_service


def send_timeline_event_notification(conversation_id, message_template, db_session, project_id, **kwargs):
    """Sends a workflow notification."""
    notification_text = "Incident Notification"
    notification_type = "incident-timeline-new"

    plugin = plugin_service.get_active_instance(db_session=db_session,
                                                project_id=project_id,
                                                plugin_type="conversation")
    plugin.instance.send(
        conversation_id, notification_text, message_template, notification_type, **kwargs
    )
