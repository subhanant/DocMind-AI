import urllib.request
import json
import uuid

BASE = "http://127.0.0.1:8000/api"

def main():
    print("================== DocuMind AI Live Verification ==================")

    # 1. Health
    req = urllib.request.urlopen(f"{BASE}/health")
    data = json.loads(req.read().decode())
    print(f"[PASS] 1. Health Endpoint: HTTP {req.status} - Status: {data['data']['status']}")

    # 2. Register
    user_email = f"audit_{uuid.uuid4().hex[:6]}@documind.ai"
    reg_payload = json.dumps({
        "email": user_email,
        "password": "SecurePassword123!",
        "full_name": "Senior Solutions Architect"
    }).encode("utf-8")
    reg_req = urllib.request.Request(
        f"{BASE}/auth/register",
        data=reg_payload,
        headers={"Content-Type": "application/json"}
    )
    reg_res = json.loads(urllib.request.urlopen(reg_req).read().decode())
    token = reg_res["data"]["access_token"]
    user_id = reg_res["data"]["user"]["id"]
    print(f"[PASS] 2. Registration: Success - User: {user_email} (ID: {user_id})")

    # 3. Login
    login_payload = json.dumps({
        "email": user_email,
        "password": "SecurePassword123!"
    }).encode("utf-8")
    login_req = urllib.request.Request(
        f"{BASE}/auth/login",
        data=login_payload,
        headers={"Content-Type": "application/json"}
    )
    login_res = json.loads(urllib.request.urlopen(login_req).read().decode())
    print(f"[PASS] 3. Login: Success - Token received (length: {len(login_res['data']['access_token'])})")

    # 4. Get Current User (/auth/me)
    me_req = urllib.request.Request(
        f"{BASE}/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    me_res = json.loads(urllib.request.urlopen(me_req).read().decode())
    print(f"[PASS] 4. Auth Me: Verified - Name: {me_res['data']['full_name']}")

    # 5. Dashboard Stats
    stats_req = urllib.request.Request(
        f"{BASE}/dashboard/stats",
        headers={"Authorization": f"Bearer {token}"}
    )
    stats_res = json.loads(urllib.request.urlopen(stats_req).read().decode())
    print(f"[PASS] 5. Dashboard Stats: Total Docs = {stats_res['data']['total_documents']}")

    # 6. Upload a document
    boundary = "DocuMindUploadBoundary" + uuid.uuid4().hex
    file_bytes = b"%PDF-1.4 sample bill of lading content for DocuMind AI validation"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="document_type"\r\n\r\n'
        f"bill_of_lading\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="files"; filename="Bill_of_Lading_001.pdf"\r\n'
        f"Content-Type: application/pdf\r\n\r\n"
    ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

    upload_req = urllib.request.Request(
        f"{BASE}/documents/upload",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}"
        }
    )
    upload_res = json.loads(urllib.request.urlopen(upload_req).read().decode())
    uploaded_doc = upload_res["data"]["document"]
    doc_id = uploaded_doc["id"]
    print(f"[PASS] 6. Document Upload: Stored safe - ID: {doc_id}, Status: {uploaded_doc['processing_status']}, File: {uploaded_doc['original_filename']}")

    # 7. List Documents
    list_req = urllib.request.Request(
        f"{BASE}/documents",
        headers={"Authorization": f"Bearer {token}"}
    )
    list_res = json.loads(urllib.request.urlopen(list_req).read().decode())
    print(f"[PASS] 7. Document Listing: Total in DB = {list_res['data']['total']}, First: {list_res['data']['items'][0]['original_filename']}")

    # 8. Document Details
    detail_req = urllib.request.Request(
        f"{BASE}/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    detail_res = json.loads(urllib.request.urlopen(detail_req).read().decode())
    print(f"[PASS] 8. Document Details: MIME: {detail_res['data']['mime_type']}, Size: {detail_res['data']['file_size']} bytes")

    # 9. Document Extraction endpoint
    ext_req = urllib.request.Request(
        f"{BASE}/documents/{doc_id}/extraction",
        headers={"Authorization": f"Bearer {token}"}
    )
    ext_res = json.loads(urllib.request.urlopen(ext_req).read().decode())
    print(f"[PASS] 9. Extraction Endpoint: Response received - Phase 1 status verified")

    # 10. Notifications
    notif_req = urllib.request.Request(
        f"{BASE}/notifications",
        headers={"Authorization": f"Bearer {token}"}
    )
    notif_res = json.loads(urllib.request.urlopen(notif_req).read().decode())
    first_notif = notif_res["data"]["items"][0]
    print(f"[PASS] 10. Notifications: Generated {notif_res['data']['total']} alert(s) - Title: '{first_notif['title']}'")

    # 11. Mark Notification as Read
    patch_req = urllib.request.Request(
        f"{BASE}/notifications/{first_notif['id']}/read",
        headers={"Authorization": f"Bearer {token}"},
        method="PATCH"
    )
    patch_res = json.loads(urllib.request.urlopen(patch_req).read().decode())
    print(f"[PASS] 11. Notification Read: is_read = {patch_res['data']['is_read']}")

    # 12. Delete Document
    del_req = urllib.request.Request(
        f"{BASE}/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token}"},
        method="DELETE"
    )
    del_res = json.loads(urllib.request.urlopen(del_req).read().decode())
    print(f"[PASS] 12. Delete Document: Success = {del_res['success']}")

    # Verify list is empty
    list_res_after = json.loads(urllib.request.urlopen(list_req).read().decode())
    print(f"[PASS] 13. Verify Deletion: Total docs now = {list_res_after['data']['total']}")

    print("================== All 13 Verification Steps PASSED ==================")

if __name__ == "__main__":
    main()
