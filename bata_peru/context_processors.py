from django.contrib.auth import get_user_model

def admin_user_context(request):
    User = get_user_model()
    admin_user = User.objects.filter(rol='admin').first()
    return {'admin_user': admin_user}
