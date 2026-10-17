from http.server import BaseHTTPRequestHandler, HTTPServer
from http.cookies import SimpleCookie
from urllib.parse import parse_qs
import secrets
from pathlib import Path

ROOT = Path(__file__).parent

SESSIONS = set()

HTML = '''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Pulse CRM</title>
<style>
*{box-sizing:border-box}body{margin:0;font-family:Inter,system-ui,-apple-system,sans-serif;color:#172033;background:#f6f8fb}button,input{font:inherit}.shell{display:flex;min-height:100vh}.sidebar{width:248px;background:#111a2e;color:#aeb8cc;padding:24px 16px;display:flex;flex-direction:column}.brand{color:white;font-size:22px;font-weight:750;padding:0 12px 28px}.brand span{color:#7c8cff}.nav a{display:block;text-decoration:none;color:#aeb8cc;padding:12px;border-radius:10px;margin:4px 0}.nav a.active,.nav a:hover{background:#263353;color:#fff}.user{margin-top:auto;border-top:1px solid #2a3550;padding:18px 12px;color:#fff}.user small{display:block;color:#8e9ab2;margin-top:4px}.main{flex:1;padding:28px 38px;max-width:1400px}.top{display:flex;justify-content:space-between;align-items:center;margin-bottom:30px}.eyebrow{color:#7c8cff;font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:.08em}.title{font-size:30px;margin:5px 0 0}.muted{color:#768199}.btn{border:0;border-radius:9px;padding:11px 16px;background:#5967f2;color:#fff;font-weight:700;cursor:pointer}.btn.secondary{background:#edf0ff;color:#4d5be4}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}.card{background:#fff;border:1px solid #e7eaf1;border-radius:14px;padding:20px;box-shadow:0 3px 10px #17203308}.metric{font-size:30px;font-weight:760;margin:10px 0 4px}.trend{font-size:13px;color:#21a276}.section{margin-top:26px}.section-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px}.section h2{font-size:18px;margin:0}.table{width:100%;border-collapse:collapse;background:#fff;border:1px solid #e7eaf1;border-radius:14px;overflow:hidden}.table th,.table td{text-align:left;padding:15px 18px;border-bottom:1px solid #eef0f5;font-size:14px}.table th{color:#768199;font-size:12px;text-transform:uppercase}.pill{padding:5px 9px;border-radius:999px;font-size:12px;font-weight:700;background:#e9f8f2;color:#18815e}.pill.blue{background:#eef0ff;color:#5361dc}.login{width:100%;display:grid;place-items:center;background:linear-gradient(135deg,#f5f6ff,#eef7ff)}.login-card{width:min(430px,calc(100% - 36px));background:#fff;border:1px solid #e5e8f1;border-radius:18px;padding:38px;box-shadow:0 16px 50px #26365a18}.login-card h1{margin:8px 0}.login-card input{width:100%;border:1px solid #dbe0eb;border-radius:9px;padding:12px;margin:7px 0 14px}.login-card .btn{width:100%;margin-top:8px}.error{color:#c44b67;font-size:13px}.kpi-note{font-size:13px;color:#768199}.mobile{display:none}@media(max-width:850px){.sidebar{width:70px;padding:20px 8px}.brand{font-size:0;padding:0 12px 28px}.brand span{font-size:22px}.nav a{font-size:0;text-align:center}.nav a:first-letter{font-size:20px}.user{font-size:0}.main{padding:22px 16px}.grid{grid-template-columns:repeat(2,1fr)}}
</style></head><body>{body}</body></html>'''

def render(name, **context):
    body = (ROOT / 'templates' / name).read_text(encoding='utf-8').format(**context)
    return HTML.replace('{body}', body)

def dashboard():
    return render('dashboard.html')

def login(error=''):
    return render('login.html', error=f'<p class="error">{error}</p>' if error else '')

class Handler(BaseHTTPRequestHandler):
    def send(self, body, code=200, headers=None):
        self.send_response(code); self.send_header('Content-Type','text/html; charset=utf-8');
        for k,v in (headers or {}).items(): self.send_header(k,v)
        self.end_headers(); self.wfile.write(body.encode())
    def authed(self):
        c=SimpleCookie(self.headers.get('Cookie','')); return c.get('sid') and c['sid'].value in SESSIONS
    def do_GET(self):
        if self.path == '/logout':
            c=SimpleCookie(self.headers.get('Cookie','')); sid=c.get('sid'); SESSIONS.discard(sid.value if sid else ''); self.send(login(),headers={'Set-Cookie':'sid=; Max-Age=0; Path=/'}); return
        self.send(dashboard() if self.authed() else login())
    def do_POST(self):
        data=parse_qs(self.rfile.read(int(self.headers.get('Content-Length',0))).decode());
        if data.get('email',[''])[0]=='demo@pulse.crm' and data.get('password',[''])[0]=='demo123':
            sid=secrets.token_urlsafe(18); SESSIONS.add(sid); self.send(dashboard(),headers={'Set-Cookie':f'sid={sid}; HttpOnly; Path=/'})
        else: self.send(login('Проверьте email и пароль'),401)

if __name__=='__main__':
    print('Pulse CRM: http://127.0.0.1:8000'); HTTPServer(('127.0.0.1',8000),Handler).serve_forever()
