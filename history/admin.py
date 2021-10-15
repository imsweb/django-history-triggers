import logging

from django.contrib.admin.utils import unquote
from django.core.exceptions import PermissionDenied
from django.template.response import TemplateResponse

from .utils import get_history_model

logger = logging.getLogger(__name__)


class HistoryAdminMixin:
    actions = ["show_history"]
    history_template = "history/admin_history.html"

    def show_history(self, request, queryset, extra_context=None):
        model_class = queryset.model

        history_model = get_history_model(model_class)
        object_history = history_model.objects.filter(
            pk__in=queryset.values_list("pk", flat=True)
        )

        context = {
            **self.admin_site.each_context(request),
            "history": object_history,
            "title": f"{ model_class.__name__ } History",
            "opts": model_class._meta,
            "queryset": queryset,
            **(extra_context or {}),
        }

        request.current_app = self.admin_site.name
        return TemplateResponse(request, self.history_template, context)

    def history_view(self, request, object_id, extra_context=None):
        obj = self.get_object(request, unquote(object_id))
        if not self.has_view_or_change_permission(request, obj):
            raise PermissionDenied

        queryset = self.model.objects.filter(id=unquote(object_id))
        return self.show_history(request, queryset, extra_context=extra_context)
