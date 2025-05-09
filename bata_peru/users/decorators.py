# users/decorators.py
from django.shortcuts import redirect

def role_required(required_role):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if request.user.is_authenticated and request.user.rol == required_role:
                return view_func(request, *args, **kwargs)
            return redirect('login')  # Redirige si no tiene el rol correcto
        return wrapper
    return decorator
