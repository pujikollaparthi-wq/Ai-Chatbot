import os
import django
import sys

# Setup Django environment
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'enterprise_platform.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from accounts.models import Department

User = get_user_model()

def run_tests():
    client = Client()
    print("=== STARTING AIOPS PORTAL AUTOMATED TESTS ===")

    # 1. Test Homepage
    print("\n[TEST] Accessing Homepage (/) as Anonymous User...")
    response = client.get('/')
    if response.status_code == 200:
        print("[OK] Homepage loaded successfully (HTTP 200)")
        if b"AIOPS Platform" in response.content:
            print("[OK] Homepage contains AIOPS Platform brand name")
        else:
            print("[ERROR] Homepage is missing AIOPS Platform brand name")
    else:
        print(f"[ERROR] Failed to load Homepage. Status code: {response.status_code}")

    # 2. Test Register Page GET
    print("\n[TEST] Accessing Register Page GET...")
    response = client.get('/accounts/register/', HTTP_ACCEPT='text/html')
    if response.status_code == 200:
        print("[OK] Register page GET loaded successfully (HTTP 200)")
    else:
        print(f"[ERROR] Failed to load Register Page. Status code: {response.status_code}")

    # 3. Test Register POST (Create test user)
    print("\n[TEST] Submitting Register form POST (creating user 'test_pujitha')...")
    # Clean up existing test user if present
    User.objects.filter(username='test_pujitha').delete()
    
    # Get a department if exists
    dept = Department.objects.first()
    dept_id = dept.id if dept else ""
    
    register_data = {
        'username': 'test_pujitha',
        'email': 'test_pujitha@enterprise.com',
        'first_name': 'Test',
        'last_name': 'Pujitha',
        'role': 'ADMIN',
        'department': dept_id,
        'employee_id': 'EMP9999',
        'phone_number': '+918179299999',
        'password': 'Password123',
        'password_confirm': 'Password123'
    }
    
    response = client.post('/accounts/register/', data=register_data, HTTP_ACCEPT='text/html')
    # Should redirect to login page (status code 302)
    if response.status_code == 302:
        print("[OK] Registration POST successful! Redirected to login page (HTTP 302)")
        user_created = User.objects.filter(username='test_pujitha').exists()
        if user_created:
            print("[OK] Verified: User 'test_pujitha' was successfully created in the database")
        else:
            print("[ERROR] User 'test_pujitha' was not found in the database!")
    else:
        print(f"[ERROR] Registration POST failed. Status code: {response.status_code}")
        if hasattr(response, 'context') and 'errors' in response.context:
            print(f"Validation errors: {response.context['errors']}")

    # 4. Test Login POST
    print("\n[TEST] Submitting Login form POST for 'test_pujitha'...")
    login_data = {
        'username': 'test_pujitha',
        'password': 'Password123'
    }
    response = client.post('/accounts/login/', data=login_data)
    # Redirects to dashboard-redirect (/) (status code 302)
    if response.status_code == 302:
        print("[OK] Login POST successful! Redirected to destination (HTTP 302)")
        
        # Follow redirect to homepage which should redirect to executive-dashboard because role is ADMIN
        response = client.get('/', follow=True)
        # Should end up on executive dashboard (HTTP 200)
        if response.status_code == 200 and (b"Executive Dashboard" in response.content or b"AI-Powered Enterprise Operations Platform" in response.content):
            print("[OK] Successfully redirected and loaded the Executive Dashboard (HTTP 200)!")
        else:
            print(f"[ERROR] Did not reach Executive Dashboard. Final status code: {response.status_code}")
    else:
        print(f"[ERROR] Login POST failed. Status: {response.status_code}")

    # 5. Test Logout
    print("\n[TEST] Accessing Logout view...")
    response = client.get('/accounts/logout/')
    if response.status_code == 302:
        print("[OK] Logout successful! Redirected to destination (HTTP 302)")
        # Check if homepage redirects to login now (meaning user is successfully logged out)
        response = client.get('/', follow=True)
        if b"Sign in to access your Enterprise Support Portal" in response.content or b"AIOPS Platform - AI-Powered Enterprise Operations" in response.content:
            print("[OK] Verified: User is fully logged out (returned to guest landing or login view)")
        else:
            print("[ERROR] User might still be logged in!")
    else:
        print(f"[ERROR] Logout failed. Status code: {response.status_code}")

    print("\n=== ALL TESTS FINISHED ===")

if __name__ == '__main__':
    run_tests()
