import sys
sys.path.insert(0, '.')

try:
    from backend.app.db.models import User, OTPVerification, Session, AuditEvent, Conversation, ExperimentRun
    print('Models OK')
except Exception as e:
    print(f'Models FAIL: {e}')

try:
    from backend.app.integrity import hash_password, compute_sha256
    print('Integrity OK')
except Exception as e:
    print(f'Integrity FAIL: {e}')

try:
    from backend.app.core.otp_service import generate_otp_code, should_expose_dev_otp
    print('OTP service OK')
except Exception as e:
    print(f'OTP service FAIL: {e}')

try:
    from backend.app.api.auth import router
    print('Auth router OK')
except Exception as e:
    print(f'Auth router FAIL: {e}')

try:
    from backend.app.main import create_app
    app = create_app()
    print('App creation OK')
except Exception as e:
    print(f'App creation FAIL: {e}')
