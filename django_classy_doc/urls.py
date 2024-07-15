from django.urls import path

from .views import ClassyView, ClassyIndexView


urlpatterns = [
    path('<str:klass>.html', ClassyView.as_view()),
    path('classify.html', ClassyIndexView.as_view()),
    path('', ClassyIndexView.as_view()),
]
