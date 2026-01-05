"""
URL configuration for ShiGu project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
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
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.goods.views import GoodsViewSet
from apps.location.views import StorageNodeListCreateView, StorageNodeTreeView

router = DefaultRouter()
router.register("goods", GoodsViewSet, basename="goods")

urlpatterns = [
    path('admin/', admin.site.urls),
    # 核心检索接口
    path("api/", include(router.urls)),
    # 位置相关接口
    path("api/location/nodes/", StorageNodeListCreateView.as_view(), name="location-nodes"),
    path("api/location/tree/", StorageNodeTreeView.as_view(), name="location-tree"),
]
