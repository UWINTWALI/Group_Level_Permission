from django.shortcuts import redirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from .models import SystemConfig

class RegistrationAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip middleware for non-registration URLs
        if not request.path.startswith('/register/'):
            return self.get_response(request)

        try:
            config = SystemConfig.objects.first()
            if not config:
                # Create default config if none exists
                config = SystemConfig.objects.create()

            if config.registration_mode == 'disabled':
                messages.error(request, _('Registration is currently disabled.'))
                return redirect('home')
            elif config.registration_mode == 'invitation' and not request.user.is_staff:
                messages.error(request, _('Registration is currently invitation-only. Please contact an administrator.'))
                return redirect('home')

        except Exception as e:
            # Log error and allow access by default
            print(f"Error checking registration access: {e}")

        return self.get_response(request)
