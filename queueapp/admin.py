from django.contrib import admin
from django.contrib.admin import AdminSite
from django.http import HttpResponseRedirect
from django.urls import path
from django.template.response import TemplateResponse
from .models import Queue, QueueItem, Agent

class MultiQueueAdminSite(AdminSite):
    site_header = 'Multi-Queue administration'
    site_title = 'Multi-Queue Admin'
    index_title = 'Accueil Multi-Queue'

    def has_permission(self, request):
        # Seul le super-utilisateur peut accéder à l'administration
        # et donc consulter directement toutes les données stockées dans Supabase.
        return request.user.is_active and request.user.is_superuser

    def index(self, request, extra_context=None):
        return HttpResponseRedirect('/')

    def app_index(self, request, app_label, extra_context=None):
        return HttpResponseRedirect('/')

admin_site = MultiQueueAdminSite(name='admin')

class QueueAdmin(admin.ModelAdmin):
    list_display = ['name', 'service_type', 'max_capacity', 'is_active', 'created_at']
    list_filter = ['service_type', 'is_active', 'created_at']
    search_fields = ['name']
    ordering = ['-created_at']

class QueueItemAdmin(admin.ModelAdmin):
    list_display = ['queue', 'position', 'served', 'created_at']
    list_filter = ['served', 'created_at', 'queue__service_type']
    search_fields = ['queue__name']
    ordering = ['-created_at']

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('qr-parser/', self.admin_site.admin_view(self.qr_parser_view), name='queueitem-qr-parser'),
        ]
        return custom_urls + urls

    def qr_parser_view(self, request):
        context = dict(self.admin_site.each_context(request))
        return TemplateResponse(request, 'admin/queueapp/qr_parser.html', context)

admin_site.register(Queue, QueueAdmin)
admin_site.register(QueueItem, QueueItemAdmin)

class AgentAdmin(admin.ModelAdmin):
    list_display = ['queue', 'agent_number', 'name', 'status', 'current_ticket', 'is_active']
    list_filter = ['status', 'queue', 'is_active']
    search_fields = ['name', 'queue__name']
    ordering = ['queue', 'agent_number']

admin_site.register(Agent, AgentAdmin)
