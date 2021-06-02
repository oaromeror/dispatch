import logging
from typing import Any, List

from codaio import Coda, Document, Cell

from dispatch.common.utils.date import date_to_tz
from dispatch.config import INCIDENT_TRACKING_SHEET_RANGE
from ..config import CODA_API_KEY, CODA_TEMPLATE_ID

log = logging.getLogger(__name__)


def set_row_values(doc: Document, table_id: str, value_map: dict):

    try:
        table = doc.get_table(table_id)
        cells = []
        row = table.rows()[0]
        for key in value_map.keys():
            cell = row[key]
            cell.value_storage = value_map[key]
            cells.append(cell)
        # Update rows
        table.update_row(row=row, cells=cells)
    except Exception as e:
        log.exception(e)


def set_column_values(doc: Document, table_id: str, value_map: dict, column_id: int):
    try:
        table = doc.get_table(table_id)
        for key in value_map.keys():
            row = table[key]
            cell = row[f"Column {column_id}"]
            cell.value_storage = value_map[key]
            # Update rows
            table.update_row(row=row, cells=[cell])
    except Exception as e:
        log.exception(e)


def create_coda_review(document_id: str, **kwargs):
    coda = Coda(CODA_API_KEY)
    incident = kwargs["incident"]

    log.info("**************** CODA ****************")

    try:

        name = incident.name
        title = incident.title
        priority = incident.incident_priority.name
        status = incident.status
        type = incident.incident_type.name
        description = incident.description
        commander_fullname = incident.commander.individual.name
        stable_at = incident.stable_at
        reported_at = incident.reported_at

        events = sorted(incident.events, key=lambda x: x.started_at, reverse=False)
        tasks = incident.tasks
        feedback = incident.feedback
        participants = '\n'.join([x.individual.name for x in incident.participants])

        impact = get_impact(incident=incident)

        incident_title = f"{date_to_tz(reported_at)} / {name}: {title}"
        ref = coda.create_doc(title=incident_title, source_doc=CODA_TEMPLATE_ID)
        doc = Document(ref["id"], coda=coda)

        # Title table
        title_map = {
            'Id incidente': name,
            'Título': f"{type} - {title}",
            'Fecha': date_to_tz(reported_at)
        }

        print(f"Title map: \n {type} - {title}  \n {date_to_tz(reported_at)}")

        set_row_values(doc=doc, table_id='Title', value_map=title_map)

        # Status
        status_map = {
            'Prioridad': priority,
            'Estado': status
        }

        print(f"Estado: \n {priority} - {status}")

        set_row_values(doc=doc, table_id='Estado', value_map=status_map)

        # Resolution time
        status_map = {
            'Fecha del evento': date_to_tz(events[0].started_at),
            'Fecha de detección': date_to_tz(reported_at),
            'Fecha de resolución': date_to_tz(stable_at)
        }

        set_row_values(doc=doc, table_id='Tiempo de resolución', value_map=status_map)

        # Description
        description_map = {
            'Comandante': commander_fullname,
            'Participantes': participants,
            'Resumen ejecutivo': description,
            'Impacto': impact,
            'Servicios afectados': "",  # incident['services'],
            'Cuentas AWS afectadas': "",  # incident['aws_accounts'],
            'Incidentes relacionados': "",  # incident['related_incidents']
        }

        set_column_values(doc=doc, table_id="Descripción", value_map=description_map, column_id=2)

        # Chronology
        update_timeline(doc=doc, events=events)

        # Tasks
        update_tasks(doc=doc, tasks=tasks)

        # Feedback
        update_feedback(doc=doc, feedback=feedback)

    except Exception as e:
        log.exception(e)


def update_timeline(doc, events):
    try:
        table = doc.get_table("Cronología")
        cells = []
        for event in events:
            date = Cell(column='Fecha', value_storage=date_to_tz(event.started_at))
            value = Cell(column='Descripción', value_storage=event.description)
            cells.append([date, value])
        table.upsert_rows(cells)
    except Exception as e:
        log.exception(e)


def update_tasks(doc, tasks):
    try:
        table = doc.get_table("Tareas")
        cells = []
        for task in tasks:
            check = Cell(column='Column 1', value_storage=(task.status == "Resolved"))
            value = Cell(column='Column 2', value_storage=task.description)
            cells.append([check, value])
        table.upsert_rows(cells)
    except Exception as e:
        log.exception(e)


def get_impact(incident):
    impact = ""
    try:
        if incident.executive_reports and incident.executive_reports[0]:
            impact = list(incident.executive_reports[0].details.values())[1]
    except Exception as e:
        log.exception(e)
    return impact


def update_feedback(doc, feedback):
    try:
        table = doc.get_table("Lecciones aprendidas")
        cells = []
        for lesson in feedback:
            check = Cell(column='Column 1', value_storage=lesson.feedback)
            cells.append([check])
        table.upsert_rows(cells)
    except Exception as e:
        log.exception(e)


def replace_text(client: Any, document_id: str, replacements: List[str]):
    """Replaces text in specified document."""
    requests = []
    for k, v in replacements.items():
        requests.append(
            {"replaceAllText": {"containsText": {"text": k, "matchCase": "true"}, "replaceText": v}}
        )

    body = {"requests": requests}
    return client.batchUpdate(documentId=document_id, body=body).execute()


def add_row(client: Any, document_id: str, params: List[List[str]]):
    """Add row in specified document."""
    try:
        resource = {
            "majorDimension": "COLUMNS",
            "values": params
        }

        client.values().append(
            spreadsheetId=document_id,
            range=INCIDENT_TRACKING_SHEET_RANGE,
            body=resource,
            valueInputOption="USER_ENTERED"
        ).execute()
    except Exception as e:
        log.exception(e)
