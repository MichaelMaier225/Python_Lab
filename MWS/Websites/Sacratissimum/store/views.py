from django.http import HttpResponse


def home(request):
    return HttpResponse(
        "<h1>Sacratissimum</h1>"
        "<p>Most sacred. Coming soon.</p>"
    )