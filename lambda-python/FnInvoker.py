import boto3
import jsonpickle,os
import json, logging, time, argparse

def handler(event,context):
    entry = time.time() * 1000
    logger = logging.getLogger()
    #hard code it in case its not available in the context for some reason
    me = 'unknown'
    reqID = 'unknown'
    if not context: #invoking from main
        boto3.setup_default_session(profile_name='cjk1')
    else:
        me = context.invoked_function_arn
        reqID = context.aws_request_id
        serialized = jsonpickle.encode(context)
        slist = ''
        for k in os.environ:
            slist += '{}:{};'.format(k,os.environ[k])
        print('context: {}\nenv: {}'.format(json.loads(serialized),slist))
      
    #time.sleep(330) for testing error reporting in AWS Lambda
    lambda_client = boto3.client('lambda')

    fn = None
    count = 1
    if event:
        print('event: ',event)
        if 'functionName' in event:
            fn = event['functionName']
        if 'count' in event:
            count = int(event['count'])
        a = b = 0
        if 'a' in event:
            a = int(event['a'])
        if 'b' in event:
            b = int(event['b'])
        if 'op' in event:
            op = event['op']
            res = 0
            if op == '+':
                res = a+b
            if op == '-':
                res = a-b
            if op == '*':
                res = a*b
            if op == '/':
                res = a/b
            print(res)
            

    #run_lambda does not support invoke via Payload arg
    invoke_response = None
    if fn and fn != me:
        msg = {}
        now = time.time() * 1000
        msg['msg'] = 'from:{}:at:{}'.format(me,now)
        msg['requestId'] = reqID
        if event and 'eventSource' in event and me == 'unknown': 
            msg['eventSource'] = event['eventSource']
        else:
            msg['eventSource'] = 'int:invokeCLI:{}'.format(me)
        #TODO: send remaining inputs
        #sending only the ones used in the other apps
        if 'tablename' in event: 
            msg['tablename'] = event['tablename']
        if 'mykey' in event: 
            msg['mykey'] = event['mykey']
        if 'myval' in event: 
            msg['myval'] = event['myval']
        if 'bkt' in event: 
            msg['bkt'] = event['bkt']
        if 'prefix' in event: 
            msg['prefix'] = event['prefix']
        if 'fname' in event: 
            msg['fname'] = event['fname']
        if 'file_content' in event: 
            msg['file_content'] = event['file_content']
        if 'topic' in event: 
            msg['topic'] = event['topic']
        if 'subject' in event: 
            msg['subject'] = event['subject']
        if 'msg' in event: 
            msg['msg'] += ":{}".format(event['msg'])

        for x in range(count):
            payload=json.dumps(msg)
            now = time.time() * 1000
            invoke_response = lambda_client.invoke(FunctionName=fn,
                InvocationType='Event', Payload=payload) #Event type says invoke asynchronously
            nowtmp = time.time() * 1000
            delta = nowtmp-now
            me_str = 'REQ:{}:{}:{}:TIMER:INVOKE:{}'.format(reqID,me,count,delta)
    else:
        me_str = 'No_context_functionName_or_recursion:{}:{}:{}:{}'.format(reqID,me,count,fn)
    
    if invoke_response:
        reqID = 'unknown'
        if 'ResponseMetadata' in invoke_response:
            meta = invoke_response['ResponseMetadata']
            if 'HTTPHeaders' in invoke_response['ResponseMetadata']:
                headers = meta['HTTPHeaders']
                if 'x-amzn-requestid' in headers:
                    reqID = headers['x-amzn-requestid']
                if 'x-amzn-trace-id' in headers:
                    reqID += ':{}'.format(headers['x-amzn-trace-id'])
        status = 'unknown'
        if 'StatusCode' in invoke_response:
            status = invoke_response['StatusCode']
        logger.warn('{} invoke_response: reqId:{} statusCode:{}'.format(me,reqID,status))

    exit = time.time() * 1000
    ms = exit-entry
    me_str += ':TIMER:CALL:{}'.format(ms)
    logger.warn(me_str)
    return me_str

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='invoke Test')
    # for this table, we assume key is name of type String
    parser.add_argument('functionName',action='store',help='ARN to invoke')
    parser.add_argument('eventSource',action='store',help='value')
    parser.add_argument('--count',action='store',default=1,type=int,help='value')
    args = parser.parse_args()
    event = {'functionName':args.functionName,'eventSource':args.eventSource,'count':args.count}
    handler(event,None)
