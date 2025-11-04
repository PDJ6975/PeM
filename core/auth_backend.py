from django.contrib.auth.backends import ModelBackend
from core.models.cliente import Cliente

class EmailBackend(ModelBackend):

# Permite logear utilizando email en lugar de username

    def authenticate(self, request, email=None, password=None, **kwargs):
        if email is None or password is None:
            return None

        try:
            user = Cliente.objects.get(email=email)
        except Cliente.DoesNotExist:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
