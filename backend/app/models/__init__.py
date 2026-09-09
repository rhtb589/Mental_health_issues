"""Model package: import all models so they register on the declarative Base
and metadata.create_all() / Alembic can discover them.
"""
from app.models.user import User  # noqa: F401
from app.models.consent import ConsentRecord  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.assessment import Assessment, ScreeningResponse  # noqa: F401
from app.models.assignment import Assignment  # noqa: F401
from app.models.retention_request import DataSubjectRequest  # noqa: F401
from app.models.conversation import Conversation, ChatMessage  # noqa: F401
