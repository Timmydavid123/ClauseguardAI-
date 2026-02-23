from django.urls import path
from . import views

urlpatterns = [
    path('<int:contract_id>/send/', views.send_message, name='chat_send'),
    path('<int:contract_id>/messages/', views.get_messages, name='chat_messages'),
]
