from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json, os
PROJECT = json.loads(Path(__file__).with_name("project.json").read_text())
def respond(value):
    kind = PROJECT["slug"]
    text = str(value).lower()
    if kind == "linda-mtoto":
        urgent = any(w in text for w in ["threat", "blackmail", "demanding photos"])
        return {"mode": "Rules-based prototype; fictional examples only", "priority": "Seek trusted support promptly" if urgent else "Review and plan", "steps": ["Move to a safe place and speak to a trusted person.", "Preserve evidence only when safe; avoid forwarding private images.", "Use the platform reporting and blocking tools.", "Contact a verified local support service."], "stored": False}
    if kind == "agrof-vision":
        data = json.loads(value)
        brightness, blur, coverage = float(data["brightness"]), float(data["blur_score"]), float(data["leaf_coverage"])
        if not 0 <= brightness <= 255 or blur < 0 or not 0 <= coverage <= 1: raise ValueError("Measurements are out of range")
        issues = []
        if brightness < 45 or brightness > 225: issues.append("Adjust lighting")
        if blur < 70: issues.append("Retake with steadier focus")
        if coverage < .25: issues.append("Move closer to the leaf")
        return {"mode": "Quality-gate prototype using supplied measurements; no image model yet", "ready_for_analysis": not issues, "issues": issues, "diagnosis": "Not performed"}
    if kind == "sqoop-merchant":
        data = json.loads(value)
        stores, users, orders = (int(data[k]) for k in ["stores", "users", "orders"])
        if min(stores, users) < 1 or orders < 0: raise ValueError("Stores/users must be positive and orders nonnegative")
        monthly = 25000 + max(stores-1,0)*10000 + max(users-3,0)*3000 + max(orders-100,0)*100
        return {"mode": "Demo quote; no charge or payment taken", "currency": "UGX", "monthly_total": monthly, "stores": stores, "users": users, "orders": orders}
    return {"mode": "Rules-based preparation prototype; AI integration pending", "questions": ["What would I like to discuss at this appointment?", "What changes have I noticed and when did they start?", "Which medicines or supplements should I bring a list of?", "What follow-up should I arrange?"], "note": value[:1500], "diagnosis": "Not provided", "stored": False}
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(b'{"status":"ok"}'); return
        if self.path != "/": self.send_error(404); return
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers(); self.wfile.write(Path(__file__).with_name("index.html").read_bytes())
    def do_POST(self):
        if self.path != "/api/demo": self.send_error(404); return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 10000: raise ValueError("Request must be 1-10000 bytes")
            data = json.loads(self.rfile.read(length)); value=data.get("input", "")
            if not isinstance(value,str) or not value.strip(): raise ValueError("Input is required")
            result=respond(value); status=200
        except (ValueError, KeyError, TypeError) as error: result={"error":str(error)}; status=400
        self.send_response(status); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(json.dumps(result).encode())
if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", int(os.getenv("PORT", "8000"))), Handler).serve_forever()
