from django.contrib import admin

from .models import Ticket


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ["title", "priority", "open"]
    list_filter = ["open"]
    search_fields = ["title"]
