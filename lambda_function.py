"""AWS Lambda Function URL adapter; configure authentication before deployment."""
import base64,json
from vision import analyze

def handler(event,context):
    try:
        method=event.get('requestContext',{}).get('http',{}).get('method','POST')
        if method!='POST':return {'statusCode':405,'body':json.dumps({'error':'POST required'})}
        body=event.get('body','')
        if len(body)>5700000:raise ValueError('Request too large')
        if event.get('isBase64Encoded'):body=base64.b64decode(body,validate=True).decode()
        data=json.loads(body)
        result=analyze(base64.b64decode(data['image'],validate=True))
        return {'statusCode':200,'headers':{'Content-Type':'application/json','Cache-Control':'no-store'},'body':json.dumps(result)}
    except (ValueError,TypeError,KeyError) as e:
        return {'statusCode':400,'headers':{'Content-Type':'application/json'},'body':json.dumps({'error':str(e)})}
