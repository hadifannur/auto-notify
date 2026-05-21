import os
import requests
from dotenv import load_dotenv
import subprocess
import json

load_dotenv()

SPREADSHEET_TOKEN = os.getenv('KL_TRACKER_SHEET').strip("'")
SHEET_ID = os.getenv('SHEET_ID').strip("'") if os.getenv('SHEET_ID') else None
APP_ID = os.getenv('APP_ID').strip("'")
APP_SECRET = os.getenv('APP_SECRET').strip("'")
QA_CHAT_ID = os.getenv('QA_CHAT_ID').strip("'")

BASE_URL = 'https://open.feishu.cn/open-apis/sheets/v3/spreadsheets'
BASE_URL_V2 = 'https://open.feishu.cn/open-apis/sheets/v2/spreadsheets'

def get_tenant_access_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    res = requests.post(url, json={"app_id": APP_ID, "app_secret": APP_SECRET})
    res.raise_for_status()
    data = res.json()
    if data["code"] != 0:
        raise Exception(f"Failed to get token: {data['msg']}")
    return data["tenant_access_token"]


def get_spreadsheet_metadata(token, spreadsheet_token):
    url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/metainfo"
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    data = res.json()
    if data["code"] != 0:
        raise Exception(f"Failed to get metadata: {data['msg']}")
    return data["data"]

def get_headers():
	token = get_tenant_access_token()
	return {
		'Authorization': f'Bearer {token}',
		'Content-Type': 'application/json; charset=utf-8',
	}


def get_sheet_values(sheet_id):
	# Get all values in the sheet
	# Use a large range to get all data, e.g., A1:Z1000
	range_str = f"{sheet_id}!A1:Z1000"
	url = f"{BASE_URL_V2}/{SPREADSHEET_TOKEN}/values/{range_str}?valueRenderOption=ToString"
	resp = requests.get(url, headers=get_headers())
	try:
		resp.raise_for_status()
	except requests.HTTPError as e:
		print("API Error Response:")
		print(resp.text)
		raise
	data = resp.json()
	if data.get('code') != 0:
		print("API Error Response:")
		print(data)
		raise Exception(f"Error fetching values: {data}")
	return data['data']['valueRange']['values']

def get_lark_chat_messages_until_tasks_found(user_access_token, chat_id, task_targets):
	"""
	Fetch messages from a Lark chat until all task targets are found in messages or messages are exhausted.
	A task target can match by Task Name/Doc first, then fallback to Extracted/Appeal Doc.
	Returns a list of (task_label, message_content) tuples for matches found.
	"""
	url = "https://open.larksuite.com/open-apis/im/v1/messages"
	headers = {
		"Authorization": f"Bearer {user_access_token}",
		"Content-Type": "application/json"
	}
	params = {
		"container_id_type": "chat",
		"container_id": chat_id,
		"page_size": 50
	}
	found = set()
	results = []
	has_more = True
	page_token = None
	while has_more and len(found) < len(task_targets):
		if page_token:
			params["page_token"] = page_token
		response = requests.get(url, headers=headers, params=params)
		response.raise_for_status()
		data = response.json().get("data", {})
		items = data.get("items", [])
		for msg in items:
			content = msg.get("title") or msg.get("body", {}).get("content", "")
			if "Mission Completion" in content:
				for idx, target in enumerate(task_targets):
					if idx in found:
						continue
					task_name = (target.get("task_name") or "").strip()
					appeal_doc = (target.get("appeal_doc") or "").strip()
					is_match = (task_name and task_name in content) or (appeal_doc and appeal_doc in content)
					if is_match:
						task_label = task_name or appeal_doc
						results.append((task_label, content))
						found.add(idx)
						if len(found) == len(task_targets):
							break
			if len(found) == len(task_targets):
				break
		has_more = data.get("has_more", False)
		page_token = data.get("page_token")
	return results

def send_qa_notification(token, message, chat_id=None):
    """
    Send a notification to a Lark group chat as an interactive card.
    If chat_id is not provided, use QA_CHAT_ID from env.
    """
    if chat_id is None:
        chat_id = QA_CHAT_ID
    card = {
        "config": {"wide_screen_mode": True},
        "elements": [
            {"tag": "div", "text": {"tag": "lark_md", "content": message}}
        ],
    }
    content = json.dumps(card)
    try:
        mr = requests.post(
            "https://open.feishu.cn/open-apis/im/v1/messages",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"},
            params={"receive_id_type": "chat_id"},
            json={"receive_id": chat_id, "msg_type": "interactive", "content": content}
        )
        mr.raise_for_status()
        md = mr.json()
        if md.get("code", 1) != 0:
            print(f"  WARN: Notification failed: {md.get('msg', 'Unknown error')}")
        else:
            print(f"  OK: Notification sent to group {chat_id}.")
    except Exception as e:
        print(f"  ERROR: Failed to send notification: {e}")

def main():
	if not SHEET_ID:
		print("SHEET_ID not set in .env")
		return
	values = get_sheet_values(SHEET_ID)
	if not values or len(values) < 2:
		print("No data found.")
		return
	headers = values[0]
	try:
		status_idx = headers.index('Task Status')
		name_idx = headers.index('Task Name/Doc')
		appeal_idx = headers.index('Extracted/Appeal Doc')
	except ValueError:
		print("Required columns not found.")
		return
	task_targets = []
	for row in values[1:]:
		raw_status = row[status_idx] if len(row) > status_idx else ''
		status = raw_status.strip() if raw_status is not None else ''
		name = row[name_idx] if len(row) > name_idx else ''
		appeal_doc = row[appeal_idx] if len(row) > appeal_idx else ''
		if (status == 'POC Round' or status == '') and (name or appeal_doc):
			task_targets.append({"task_name": name, "appeal_doc": appeal_doc})
			print(name or appeal_doc)


	def fetch_and_notify():
		# Fetch and filter Lark chat messages
		user_access_token = os.getenv("USER_ACCESS_TOKEN")
		chat_id = os.getenv("CHAT_ID")
		if user_access_token and chat_id:
			print("\n--- Lark Chat Messages containing Task Names ---")
			try:
				results = get_lark_chat_messages_until_tasks_found(user_access_token, chat_id, task_targets)
				print(f"Total matches found: {len(results)}")
				for task_name, content in results:
					print(task_name)
				# Send notification to group with summary
				if results:
					summary = (
						"**The following tasks have been found to be completed in the POC Round:**\n\n"
						+ "\n".join(f"{task_name}" for task_name, _ in results)
						+ "\n\nPlease check and update accordingly."
					)
				else:
					summary = "All tasks has been updated"
				# Use tenant access token for group notification
				group_token = get_tenant_access_token()
				send_qa_notification(group_token, summary)
			except requests.HTTPError as e:
				if e.response.status_code == 401:
					print("User access token expired or invalid. Launching OAuth flow...")
					import subprocess
					subprocess.run(["python", "lark_oauth_localhost.py"])
					# Reload .env and retry
					from dotenv import load_dotenv
					load_dotenv(override=True)
					fetch_and_notify()
					return
				else:
					print(f"Error fetching chat messages: {e}")
		else:
			print("USER_ACCESS_TOKEN or CHAT_ID not set in .env")

	fetch_and_notify()

if __name__ == "__main__":
	main()
