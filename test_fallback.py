import sys
sys.path.append('audit_html')
from modules.database import init_database, create_user, login_user, get_connection

print("Init DB:", init_database())
conn = get_connection()
print("CURRENT_DB_TYPE from conn:", conn)
ok, msg = create_user("offlinetest", "offline@test.com", "123456", "Offline User")
print("Create User:", ok, msg)
user, msg = login_user("offlinetest", "123456")
print("Login User:", user["username"] if user else None, msg)
