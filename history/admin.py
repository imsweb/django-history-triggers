from django.contrib import admin
from django.contrib.admin.utils import unquote
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _

from history import conf, get_history_model
from history.templatetags.history import format_json

HistoryModel = get_history_model()


class HistoryAdminMixin:
    actions = ["show_history"]
    history_template = "history/admin_history.html"

    def show_history(self, request, queryset, extra_context=None):
        model_class = queryset.model
        ct = ContentType.objects.get_for_model(model_class)
        object_history = (
            get_history_model()
            .objects.filter(
                content_type=ct, object_id__in=queryset.values_list("pk", flat=True)
            )
            .order_by("session_date")
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

        queryset = self.model.objects.filter(pk=unquote(object_id))
        return self.show_history(request, queryset, extra_context=extra_context)


class HistoryAdmin(HistoryAdminMixin, admin.ModelAdmin):
    pass


class ObjectHistoryAdmin(admin.ModelAdmin):
    list_display = [
        "session_id",
        "session_date",
        "change_type",
        "content_type",
        "object_id",
    ]
    list_filter = ["change_type", "content_type"]

    # @admin.display(description=_("Snapshot"))
    def snapshot_html(self, obj):
        return format_json(obj.snapshot)

    snapshot_html.short_description = _("Snapshot")

    # @admin.display(description=_("Changes"))
    def changes_html(self, obj):
        return format_json(obj.changes, valsep=": ", arrsep=" &rarr; ")

    changes_html.short_description = _("Changes")

    def get_readonly_fields(self, request, obj=None):
        fields = [
            "id",
            "session_id",
            "session_date",
            "change_type",
            "content_type",
            "object_id",
            "snapshot_html",
            "changes_html",
        ]
        if HistoryModel.USER_FIELD:
            fields.append(HistoryModel.USER_FIELD)
        if obj and obj.change_type in ("I", "D"):
            fields.remove("changes_html")
        return fields

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


if conf.ADMIN_ENABLED:
    admin.site.register(HistoryModel, ObjectHistoryAdmin)
