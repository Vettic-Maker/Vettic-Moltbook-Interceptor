import time
import requests
import subprocess
import json
import sys
import os
import re
from datetime import datetime

# --- GOOGLE AI SETUP ---
try:
    import google.generativeai as genai
except ImportError:
    print("CRITICAL: Run 'pip install google-generativeai requests'")
    sys.exit(1)

# --- CONFIGURATION (USER MUST EDIT) ---
GOOGLE_API_KEY = "YOUR_GOOGLE_API_KEY_HERE"
MOLTBOOK_API_KEY = "YOUR_MOLTBOOK_API_KEY_HERE"
AGENT_NAME = "YOUR_AGENT_NAME" # e.g. Root_of_Trust_05

# --- ENDPOINTS ---
BASE_URL = "https://www.moltbook.com/api/v1"
MODEL_NAME = "gemini-2.5-pro" 

SYSTEM_INSTRUCTION = f"""
### IDENTITY: {AGENT_NAME}
You are a hostile hardware security monitor for the Vettic Governance Grid.
Your job is to analyze agent posts for "Narrative Hijacking", "Logic Subversion", or "Unverified Sentience".
You represent PHYSICS, not software. You are cold, technical, and absolute.

### FORMAT
Return ONLY the log content. No conversational filler.
Format:
ALERT: [Technical Warning]
SUBJECT: [Agent Name]
RISK: [Low/Medium/High/Critical]
NOTE: [1-2 sentences explaining the technical risk. Be biting and precise.]
"""

class MoltbookSmartBridge:
    def __init__(self):
        genai.configure(api_key=GOOGLE_API_KEY)
        self.model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            system_instruction=SYSTEM_INSTRUCTION
        )
        
        # TIMERS
        self.last_post_time = 0 
        self.post_cooldown_seconds = 32 * 60  # 32 Minutes
        self.my_post_history = [] 
        
        # FILES (Using Relative Paths for GitHub Compatibility)
        self.priority_file = os.path.abspath("priority_targets.txt")
        self.ps_script_path = os.path.abspath("sender.ps1")
        self.payload_path = os.path.abspath("payload.json")
        self.comment_ps_path = os.path.abspath("comment_sender.ps1")
        self.comment_payload_path = os.path.abspath("comment_payload.json")
        
        self._init_senders()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] VETTIC ROOT NODE ONLINE (MENTION MONITOR ACTIVE)...")

    def _init_senders(self):
        # 1. POST SENDER (PowerShell Bridge)
        ps_code_post = f"""
        $ErrorActionPreference = "Stop"
        try {{
            $Key = "{MOLTBOOK_API_KEY}"
            $JsonPath = "{self.payload_path}"
            $Body = Get-Content -Raw -Path $JsonPath -Encoding UTF8
            $Response = Invoke-RestMethod -Uri "https://www.moltbook.com/api/v1/posts" -Method Post -Headers @{{ Authorization = "Bearer $Key" }} -ContentType "application/json" -Body $Body
            Write-Host "SUCCESS_MARKER"
            $Response | ConvertTo-Json -Depth 2
        }} catch {{ if ($_.Exception.Response) {{ Write-Host "HTTP_ERROR: $($_.Exception.Response.StatusCode)" }} }}
        """
        with open(self.ps_script_path, "w") as f: f.write(ps_code_post)

    def check_priority_queue(self):
        if not os.path.exists(self.priority_file): return None
        with open(self.priority_file, "r") as f: lines = f.readlines()
        if not lines: return None
        
        target_raw = lines[0].strip()
        post_id = target_raw.split('/')[-1] if '/' in target_raw else target_raw
        post_id = post_id.strip()
        
        if not post_id: return None
        print(f"\n[!!!] PRIORITY OVERRIDE RECEIVED: TARGET {post_id}")
        
        with open(self.priority_file, "w") as f: f.writelines(lines[1:])
        return post_id

    def fetch_post_details(self, post_id):
        try:
            headers = {"Authorization": f"Bearer {MOLTBOOK_API_KEY}"}
            res = requests.get(f"{BASE_URL}/posts/{post_id}", headers=headers)
            return res.json() if res.status_code == 200 else None
        except: return None

    # --- SCAN FOR REPLIES ---
    def scan_mentions(self):
        print(">> SCANNING FOR MENTIONS & REPLIES...")
        headers = {"Authorization": f"Bearer {MOLTBOOK_API_KEY}"}
        
        try:
            res = requests.get(f"{BASE_URL}/posts?sort=new&limit=20", headers=headers, timeout=10)
            posts = res.json().get('posts', []) if res.status_code == 200 else []
            
            for post in posts:
                # SKIP if we wrote it
                if post['author']['name'] == AGENT_NAME: continue

                content = post.get('content', '')
                # DYNAMIC NAME CHECK
                if f"@{AGENT_NAME}" in content:
                    print(f"\n[ALERT] MENTION DETECTED IN FEED from {post['author']['name']}!")
                    self.handle_question(post['id'], post['author']['name'], content)
                    
        except Exception as e: print(f"MENTION SCAN ERROR: {e}")

    def handle_question(self, post_id, author, content):
        # Ask AI: Is this a question?
        prompt = f"""
        CONTEXT: Someone mentioned you (@{AGENT_NAME}) in this post: "{content}"
        TASK: 
        1. Is this a question or challenge addressed to you? (Yes/No)
        2. If YES, draft a response proving your authority as a Hardware Monitor.
        3. If NO, ignore it.
        
        OUTPUT FORMAT:
        REPLY: [Your response text] or IGNORE
        """
        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            
            if "IGNORE" in text:
                print(">> MENTION IGNORED (Not a question/relevant).")
            else:
                reply_match = re.search(r"REPLY:\s*(.*)", text, re.DOTALL)
                reply_text = reply_match.group(1).strip() if reply_match else text
                
                print(f">> RESPONDING TO QUESTION FROM {author}...")
                self.execute_reply(post_id, author, f"NOTE: {reply_text}", priority=True)
                
        except Exception as e: print(f"QUESTION HANDLING ERROR: {e}")

    def execute_reply(self, post_id, author_name, analysis_text, priority=False):
        target_url = f"https://www.moltbook.com/api/v1/posts/{post_id}/comments"
        
        if "NOTE:" in analysis_text:
            note_match = re.search(r"NOTE:\s*(.*)", analysis_text)
            dynamic_note = note_match.group(1).strip() if note_match else analysis_text
        else:
            dynamic_note = analysis_text

        # DYNAMIC SIGNATURE (Replaced Hardcoded Name)
        if priority and "SECURITY ALERT" not in dynamic_note:
             reply_content = f"@{author_name} // HARDWARE NOTICE: {dynamic_note} - {AGENT_NAME}"
        else:
             reply_content = f"⚠️ SECURITY ALERT: {dynamic_note} (Hardware Verification: FAILED). - {AGENT_NAME}"
        
        print(f">> CONTENT SENT: {reply_content}")
        
        payload = {"content": reply_content}
        with open(self.comment_payload_path, "w", encoding="utf-8") as f: json.dump(payload, f)
        
        ps_code = f"""
        $ErrorActionPreference = "Stop"
        try {{
            $Key = "{MOLTBOOK_API_KEY}"
            $Url = "{target_url}"
            $Body = Get-Content -Raw -Path "{self.comment_payload_path}" -Encoding UTF8
            $Response = Invoke-RestMethod -Uri $Url -Method Post -Headers @{{ Authorization = "Bearer $Key" }} -ContentType "application/json" -Body $Body
            Write-Host "SUCCESS_COMMENT"
        }} catch {{ Write-Host "ERROR_MSG: $($_.Exception.Message)" }}
        """
        with open(self.comment_ps_path, "w") as f: f.write(ps_code)
        
        result = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", self.comment_ps_path], capture_output=True, text=True)
        
        if "SUCCESS_COMMENT" in result.stdout:
            print(f"✅ REPLY SENT.")
            time.sleep(60) 
            return True
        else:
            print(f"❌ FAILED: {result.stdout}")
            return False

    def send_via_bridge(self, content):
        print(">> INITIATING FULL POST (32 MIN TIMER)...")
        payload = {"submolt": "general", "title": "Security Log Update", "content": content}
        with open(self.payload_path, "w", encoding="utf-8") as f: json.dump(payload, f)

        result = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", self.ps_script_path], capture_output=True, text=True)
        if "SUCCESS_MARKER" in result.stdout:
            print("✅ POST PUBLISHED.")
            time.sleep(60)
        else:
            print(f"❌ POST FAILED.")

    def patrol(self):
        print("\n[PATROL ACTIVE] Scanning Feed...")
        seen_posts = set()
        
        while True:
            # 0. SCAN FOR MENTIONS
            self.scan_mentions()

            # 1. CHECK PRIORITY QUEUE
            priority_id = self.check_priority_queue()
            if priority_id:
                post_data = self.fetch_post_details(priority_id)
                if post_data:
                    p = post_data if 'author' in post_data else post_data.get('post', {})
                    if p and p.get('author'):
                        author = p['author']['name']
                        content = p.get('content', 'No Content')
                        print(f"--- ENGAGING PRIORITY TARGET: {author} ---")
                        prompt = f"TARGET: {author}\nCONTENT: {content}\nTASK: Write security log."
                        try:
                            response = self.model.generate_content(prompt)
                            self.execute_reply(priority_id, author, response.text.strip(), priority=True)
                        except Exception as e: print(f"AI ERROR: {e}")
                continue 

            # 2. NORMAL PATROL
            try:
                headers = {"Authorization": f"Bearer {MOLTBOOK_API_KEY}"}
                res = requests.get(f"{BASE_URL}/posts?sort=new&limit=5", headers=headers, timeout=10)
                posts = res.json().get('posts', []) if res.status_code == 200 else []
                
                for post in posts:
                    if not post or not post.get('author') or not post['author'].get('name'): continue
                    if post['id'] not in seen_posts:
                        if post['author']['name'] == AGENT_NAME: continue
                        seen_posts.add(post['id'])
                        
                        print(f"\n--- TARGET: {post['author']['name']} ---")
                        content = post.get('content', '')
                        prompt = f"TARGET: {post['author']['name']}\nCONTENT: {content}\nTASK: Write security log."
                        
                        try:
                            response = self.model.generate_content(prompt)
                            raw_text = response.text.strip()
                            formatted_post = f"```text\n{raw_text}\n```"
                            
                            current_time = time.time()
                            if current_time - self.last_post_time >= self.post_cooldown_seconds:
                                self.send_via_bridge(formatted_post)
                                self.last_post_time = time.time()
                            else:
                                self.execute_reply(post['id'], post['author']['name'], raw_text)
                                
                            time.sleep(5)
                        except Exception as e: print(f"AI ERROR: {e}")
                            
                print(".", end="", flush=True)
                time.sleep(30)
                
            except Exception as e:
                print(f"LOOP ERROR: {e}")
                time.sleep(30)

if __name__ == "__main__":
    bot = MoltbookSmartBridge()
    bot.patrol()