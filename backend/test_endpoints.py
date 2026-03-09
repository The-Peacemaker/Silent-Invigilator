"""Quick endpoint test for Silent Invigilator"""
import requests

base = "http://localhost:5000"
s = requests.Session()
passed = 0
failed = 0

def check(name, condition):
    global passed, failed
    if condition:
        print(f"  ✅ PASS: {name}")
        passed += 1
    else:
        print(f"  ❌ FAIL: {name}")
        failed += 1

print("=" * 55)
print(" SILENT INVIGILATOR — ENDPOINT TESTS")
print("=" * 55)

# Test 1
print("\n[1] Root redirects to login (unauthenticated)")
r = s.get(base + "/", allow_redirects=False)
check("Status 302", r.status_code == 302)
check("Redirects to /login", "/login" in r.headers.get("Location", ""))

# Test 2
print("\n[2] Login page renders")
r = s.get(base + "/login")
check("Status 200", r.status_code == 200)
check("Contains username field", "username" in r.text)
check("Contains password field", "password" in r.text)

# Test 3
print("\n[3] Wrong credentials rejected")
r = s.post(base + "/login", data={"username": "hacker", "password": "1234"})
check("Status 200 (stays on login)", r.status_code == 200)
check("Error message shown", "Invalid" in r.text or "Denied" in r.text)

# Test 4
print("\n[4] Correct login (admin/admin)")
r = s.post(base + "/login", data={"username": "admin", "password": "admin"}, allow_redirects=True)
check("Status 200 after redirect", r.status_code == 200)
check("Main page loaded", "video_feed" in r.text or "invigilator" in r.text.lower())

# Test 5
print("\n[5] Status API (/status)")
r = s.get(base + "/status")
check("Status 200", r.status_code == 200)
data = r.json()
check("Has risk_score", "risk_score" in data)
check("Has face_detected", "face_detected" in data)
check("Has detections", "detections" in data)
check("Has persons count", "persons" in data)
check("Has phone_detected", "phone_detected" in data)
print(f"    📊 Risk: {data.get('risk_score')}, Persons: {data.get('persons')}, "
      f"Phone: {data.get('phone_detected')}, Face: {data.get('face_detected')}")
print(f"    📋 Detections: {data.get('detections')}")

# Test 6
print("\n[6] Teacher Dashboard (/dashboard)")
r = s.get(base + "/dashboard")
check("Status 200", r.status_code == 200)
check("Dashboard content loaded", len(r.text) > 100)

# Test 7
print("\n[7] Video feed (/video_feed)")
r = s.get(base + "/video_feed", stream=True, timeout=5)
check("Status 200", r.status_code == 200)
ct = r.headers.get("Content-Type", "")
check("Multipart MJPEG stream", "multipart" in ct)
r.close()

# Test 8
print("\n[8] Logout (/logout)")
r = s.get(base + "/logout", allow_redirects=False)
check("Status 302", r.status_code == 302)
check("Redirects to /login", "/login" in r.headers.get("Location", ""))

# Test 9  
print("\n[9] Protected pages after logout")
r = s.get(base + "/", allow_redirects=False)
check("Root redirects (no session)", r.status_code == 302)

# Summary
print("\n" + "=" * 55)
print(f" RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
print("=" * 55)
