from django.shortcuts import render
from django.contrib.admin.utils import unquote
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import connections

from history.management.commands.triggers import schema_exists

from .conf import DEFAULT_USER, SCHEMA_NAME, USE_JSON
from .utils import get_history_model

import logging


logger = logging.getLogger(__name__)


class HistoryAdminMixin:
    actions = ["show_history"]
    history_template = "history/admin_history.html"

    def is_valid(self):
        cursor = connections["default"].cursor()
        is_valid = schema_exists(cursor, SCHEMA_NAME)
        if not is_valid:
            logger.warning(
                f"Warning: `HistoryAdminMixin` is being used with `{ self.__class__.__name__ }`, but schema does not exist."
            )
        return is_valid

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not self.is_valid():
            actions.pop("show_history")
        return actions

    def get_context_data(self, **kwargs):
        return {
            "default_user": DEFAULT_USER,
            "user_model_class_meta": get_user_model()._meta,
            "use_json": USE_JSON,
            **kwargs,
        }

    def get_history_queryset(self, history_model, queryset):
        return history_model.objects.filter(
            pk__in=queryset.values_list("pk", flat=True)
        )

    def show_history(self, request, queryset):
        model_class = queryset.model

        history_model = get_history_model(model_class)
        object_history = self.get_history_queryset(history_model, queryset)

        context = self.get_context_data(
            **{
                "history": object_history,
                "title": f"{ model_class.__name__ } History",
                "model_class_meta": model_class._meta,
                "queryset": queryset,
                **self.admin_site.each_context(request),
            }
        )

        return render(request, self.history_template, context=context)

    def history_view(self, request, object_id, extra_context=None):
        if not self.is_valid():
            # If not valid, fall back to Django's default history view
            return super().history_view(request, object_id, extra_context)

        obj = self.get_object(request, unquote(object_id))
        if not self.has_view_or_change_permission(request, obj):
            raise PermissionDenied

        queryset = self.model.objects.filter(id=unquote(object_id))
        return self.show_history(request, queryset)
