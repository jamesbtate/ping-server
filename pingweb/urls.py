"""pingweb URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from pingweb import views, class_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('hello', views.hello),
    path('test', views.test),
    path('', views.index),
    path('graph/<int:pair_id>', views.graph_page, name="graph_page"),
    path('multigraph/<str:pair_ids_str>', views.multigraph_page, name='multigraph'),
    path('graph_image/<int:pair_id>', views.graph_image),
    path('about', views.about),
    path('gc', views.garbage_collect),
    path('cache_info/get_poll_data', views.cache_info_get_poll_data),
    path('configure', views.configure),
    path('configure/prober', views.list_prober, name='list_prober'),
    path('configure/prober/<int:id>', views.edit_prober, name='edit_prober'),
    path('configure/prober/<int:pk>/delete',
         class_views.ProberDelete.as_view(),
         name='delete_prober'),
    path('configure/target', views.list_target, name='list_target'),
    path('configure/target/<int:id>', views.edit_target, name='edit_target'),
    path('configure/target/<int:pk>/delete',
         class_views.TargetDelete.as_view(),
         name='delete_target'),
    path('configure/probe_group', views.list_probe_group,
         name='list_probe_group'),
    path('configure/probe_group/<int:id>', views.edit_probe_group,
         name='edit_probe_group'),
    path('configure/probe_group/<int:pk>/delete',
         class_views.ProbeGroupDelete.as_view(),
         name='delete_probe_group'),
    path('configure/settings', views.list_settings, name='list_settings'),
    path('configure/update_prober_targets', views.update_prober_targets,
         name='update_prober_targets'),
]
