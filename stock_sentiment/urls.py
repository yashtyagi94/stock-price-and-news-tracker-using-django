from django.contrib import admin
from django.urls import path
from tracker import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.home, name="home"),
    path('download/csv/', views.download_csv, name='download_csv'),
    path('download/pdf/', views.download_pdf, name='download_pdf'),
]
