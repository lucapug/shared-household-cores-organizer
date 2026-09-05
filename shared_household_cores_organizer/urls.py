from django.urls import path

from . import views

app_name = "chore_wheel"

urlpatterns = [
    path("", views.board, name="board"),
    path("setup/", views.setup, name="setup"),
    path("states/<int:pk>/toggle/", views.toggle_done, name="toggle_done"),
    path("states/<int:pk>/note/", views.set_note, name="set_note"),
    path("members/add/", views.add_member, name="add_member"),
    path("members/<int:pk>/delete/", views.delete_member, name="delete_member"),
    path("members/<int:pk>/move/<str:direction>/", views.move_member, name="move_member"),
    path("chores/add/", views.add_chore, name="add_chore"),
    path("chores/<int:pk>/delete/", views.delete_chore, name="delete_chore"),
    path("chores/<int:pk>/move/<str:direction>/", views.move_chore, name="move_chore"),
]
