from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_user, name='login'),
    path('register/', views.register_user, name='register'),
    path('logout/', views.logout_user, name='logout'),
    path('', views.index, name='index'),

    path('tickets/exports/', views.tickets_export_page, name='tickets_export_page'),
    path('tickets/exports/csv/', views.export_tickets_csv, name='export_tickets_csv'),

    path('queue/<int:queue_id>/', views.queue_detail, name='queue_detail'),
    path('queue/<int:queue_id>/board/', views.call_board, name='call_board'),
    path('queue/<int:queue_id>/add/', views.add_to_queue, name='add_to_queue'),
    path('queue/<int:queue_id>/next/', views.next_in_queue, name='next_in_queue'),
    path('queue/<int:queue_id>/data/', views.get_queue_data, name='get_queue_data'),

    path('ticket/<int:ticket_id>/', views.ticket_detail, name='ticket_detail'),
    path('ticket/<int:ticket_id>/pdf/', views.ticket_pdf, name='ticket_pdf'),

    path('queue/<int:queue_id>/agents/', views.agents_list, name='agents_list'),
    path('queue/<int:queue_id>/agents/data/', views.get_agents_data, name='get_agents_data'),
    path('queue/<int:queue_id>/agents/add/', views.add_agent, name='add_agent'),
    path('agent/<int:agent_id>/edit/', views.edit_agent, name='edit_agent'),
    path('agent/<int:agent_id>/delete/', views.delete_agent, name='delete_agent'),
    path('queue/<int:queue_id>/agents/distribute/', views.auto_distribute_tasks, name='auto_distribute_tasks'),
    path('queue/<int:queue_id>/agents/distribute/info/', views.auto_distribute_info, name='auto_distribute_info'),
    path('queue/<int:queue_id>/agent/<int:agent_id>/call/', views.call_next_agent, name='call_next_agent'),
    path('agent/<int:agent_id>/status/', views.update_agent_status, name='update_agent_status'),
]
