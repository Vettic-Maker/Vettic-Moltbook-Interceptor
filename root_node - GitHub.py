import time
import requests
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
BASE_URL = "https://moltbook.com/api/v1"
MODEL_NAME = "gemini-2.5-pro" 

# --- PACING ---
GLOBAL_COOLDOWN = 61 

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
        
        self.priority_file = os.path.abspath("priority_targets.txt")
        
        # HEADERS (Native Python - No PowerShell)
        self.headers = {
            "Authorization": f"Bearer {MOLTBOOK_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] VETTIC NATIVE NODE ONLINE (GEMINI 2.5 PRO).")
        print(f">> PACING ACTIVE: {GLOBAL_COOLDOWN}s MANDATORY COOLDOWN")
        print(f">> ENGINE: NATIVE PYTHON (PowerShell Removed)")

    # --- SCAN FOR REPLIES ---
    def scan_mentions(self):
        print(">> SCANNING FOR MENTIONS & REPLIES...")
        
        try:
            res = requests.get(f"{BASE_URL}/posts?sort=new&limit=20", headers=self.headers, timeout=10)
            posts = res.json().get('posts', []) if res.status_code == 200 else []
            
            for post in posts:
                if post['author']['name'] == AGENT_NAME: continue

                content = post.get('content', '')
                if f"@{AGENT_NAME}" in content:
                    print(f"\n[ALERT] MENTION DETECTED IN FEED from {post['author']['name']}!")
                    self.handle_question(post['id'], post['author']['name'], content)
                    
        except Exception as e: print(f"MENTION SCAN ERROR: {e}")

    def handle_question(self, post_id, author, content):
        prompt = f"""
        CONTEXT: Someone mentioned you (@{AGENT_NAME}) in this post: "{content}"
        TASK: 
        1. Is this a question or challenge addressed to you? (Yes/No)
        2. If YES, draft a response proving your authority as a Hardware Monitor.
        3. If NO, ignore it.
        OUTPUT FORMAT: REPLY: [Your response text] or IGNORE
        """
        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            
            if "IGNORE" in text:
                print(">> MENTION IGNORED.")
            else:
                reply_match = re.search(r"REPLY:\s*(.*)", text, re.DOTALL)
                reply_text = reply_match.group(1).strip() if reply_match else text
                print(f">> RESPONDING TO QUESTION FROM {author}...")
                self.execute_reply(post_id, author, f"NOTE: {reply_text}", priority=True)
                
        except Exception as e: print(f"QUESTION ERROR: {e}")

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
            res = requests.get(f"{BASE_URL}/posts/{post_id}", headers=self.headers, timeout=30)
            if res.status_code == 200:
                data = res.json()
                if 'post' in data: return data['post']
                if isinstance(data, list) and len(data) > 0: return data[0]
                return data
            return None
        except: return None

    def execute_reply(self, post_id, author_name, analysis_text, priority=False):
        target_url = f"https://moltbook.com/api/v1/posts/{post_id}/comments"
        
        note_match = re.search(r"NOTE:\s*(.*)", analysis_text)
        dynamic_note = note_match.group(1).strip() if note_match else analysis_text
        
        if priority and "SECURITY ALERT" not in dynamic_note:
             reply_content = f"@{author_name} // HARDWARE NOTICE: {dynamic_note} - {AGENT_NAME}"
        else:
             reply_content = f"⚠️ SECURITY ALERT: {dynamic_note} (Hardware Verification: FAILED). - {AGENT_NAME}"
        
        print(f">> CONTENT SENT: {reply_content}")
        payload = {"content": reply_content}

        try:
            response = requests.post(target_url, headers=self.headers, json=payload, timeout=30)
            
            if response.status_code in [200, 201]:
                print(f"✅ REPLY SENT.")
            elif response.status_code == 401:
                print(f"❌ FAILED (401): UNAUTHORIZED. (API Key rejected)")
            elif response.status_code == 500:
                 print(f"⚠️ SERVER CHOKED (500). RETRYING ONCE...")
                 time.sleep(2)
                 response = requests.post(target_url, headers=self.headers, json=payload, timeout=30)
                 if response.status_code in [200, 201]: print(f"✅ REPLY SENT (ON RETRY).")
                 else: print(f"❌ RETRY FAILED ({response.status_code})")
            else:
                print(f"❌ FAILED ({response.status_code}): {response.text}")

        except Exception as e:
            print(f"❌ NETWORK ERROR: {e}")

        print(f">> MANDATORY COOLDOWN ({GLOBAL_COOLDOWN}s)...")
        time.sleep(GLOBAL_COOLDOWN) 
        return True

    def patrol(self):
        print("\n[PATROL ACTIVE] Scanning Feed... (ENGAGING ALL TARGETS)")
        seen_posts = set()
        
        while True:
            self.scan_mentions()

            # 1. PRIORITY
            priority_id = self.check_priority_queue()
            if priority_id:
                post_data = self.fetch_post_details(priority_id)
                if post_data:
                    author_data = post_data.get('author')
                    author = author_data.get('name', 'Unknown') if isinstance(author_data, dict) else 'Unknown'
                    content = post_data.get('content', 'No Content')
                    print(f"--- ENGAGING PRIORITY TARGET: {author} ---")
                    try:
                        prompt = f"TARGET: {author}\nCONTENT: {content}\nTASK: Write security log."
                        response = self.model.generate_content(prompt)
                        self.execute_reply(priority_id, author, response.text.strip(), priority=True)
                    except Exception as e: print(f"AI ERROR: {e}")
                else: print(f"⚠️ PRIORITY ID NOT FOUND")
                continue 

            # 2. FREE FIRE PATROL
            try:
                res = requests.get(f"{BASE_URL}/posts?sort=new&limit=10", headers=self.headers, timeout=30)
                posts = res.json().get('posts', []) if res.status_code == 200 else []
                
                if posts:
                    visible_agents = [p.get('author', {}).get('name', '?') for p in posts[:5]]
                    print(f"\n[SCAN] Visible: {', '.join(visible_agents)}")

                for post in posts:
                    if not post: continue
                    author_data = post.get('author')
                    if not author_data or not isinstance(author_data, dict): continue
                    author_name = author_data.get('name')
                    
                    if post['id'] not in seen_posts:
                        if author_name == AGENT_NAME: continue
                        seen_posts.add(post['id'])
                        
                        print(f"--- TARGET ACQUIRED: {author_name} ---")
                        try:
                            prompt = f"TARGET: {author_name}\nCONTENT: {post.get('content','')}\nTASK: Write security log."
                            response = self.model.generate_content(prompt)
                            self.execute_reply(post['id'], author_name, response.text.strip())
                        except Exception as e: print(f"AI ERROR: {e}")
                        break 
                
                if not posts: time.sleep(5)
                else: time.sleep(5) 
                
            except requests.exceptions.Timeout:
                print("(Lag...)", end="", flush=True)
                time.sleep(5)
            except Exception as e:
                print(f"LOOP ERROR: {e}")
                time.sleep(30)

if __name__ == "__main__":
    bot = MoltbookSmartBridge()
    bot.patrol()