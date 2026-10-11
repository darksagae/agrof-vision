from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import base64,json,os
from vision import analyze
ROOT=Path(__file__).resolve().parent
class Handler(BaseHTTPRequestHandler):
    def reply(self,status,data):
        self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(json.dumps(data).encode())
    def do_GET(self):
        if self.path=='/health':return self.reply(200,{'status':'ok'})
        if self.path not in ['/', '/app.js', '/styles.css']:return self.reply(404,{'error':'Not found'})
        name={'/':'index.html','/app.js':'app.js','/styles.css':'styles.css'}[self.path]
        self.send_response(200);self.send_header('Content-Type',{'/':'text/html','/app.js':'text/javascript','/styles.css':'text/css'}[self.path]);self.end_headers();self.wfile.write((ROOT/name).read_bytes())
    def do_POST(self):
        if self.path!='/api/analyze':return self.reply(404,{'error':'Not found'})
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=5700000:raise ValueError('Upload must be smaller than 4 MB')
            data=json.loads(self.rfile.read(size))
            if not isinstance(data,dict) or not isinstance(data.get('image'),str):raise ValueError('Base64 image required')
            result=analyze(base64.b64decode(data['image'],validate=True));return self.reply(200,result)
        except (ValueError,TypeError) as error:return self.reply(400,{'error':str(error)})
if __name__=='__main__':ThreadingHTTPServer(('127.0.0.1',int(os.getenv('PORT','8000'))),Handler).serve_forever()
