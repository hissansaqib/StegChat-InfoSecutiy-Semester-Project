import os, secrets, base64
key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
print(key)

