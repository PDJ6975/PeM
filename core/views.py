from django.shortcuts import render


def home(request):
    """Vista de la página de inicio"""
    return render(request, 'core/index.html')
