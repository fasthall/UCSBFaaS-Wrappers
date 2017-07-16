from boto3 import client as boto3_client
from datetime import datetime
import json, logging, time, jsonpickle

def handler(event, context):
    start = datetime.now()
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    retn = 'nothing:returned'
    eventSource = 'unset'
    if context:
        serialized = jsonpickle.encode(context)
        logger.info('SpotTemplatePy::handler: context: {}'.format(json.loads(serialized)))
    if event:
        serialized = jsonpickle.encode(event)
        logger.info('SpotTemplatePy::handler: event: {}'.format(json.loads(serialized)))

        if eventSource in event:
            eventSource = event['eventSource']
        if 'requestContext' in event:
            #API Gateway
            logger.info('SpotTemplatePy::handler: API Gateway triggered')
        elif 'Records' in event:
            #S3 or DynamoDB or unknown
            if eventSource.startswith('aws:s3'):
                logger.info('SpotTemplatePy::handler: S3 triggered')
            elif eventSource.startswith('aws:dynamodb'):
                logger.info('SpotTemplatePy::handler: dynamoDB triggered')
            else:
                logger.info('SpotTemplatePy::handler: unknown Records trigger')
        elif 'invokeCLI' in eventSource:
            logger.info('SpotTemplatePy::handler: invoke trigger: {}'.format(eventSource))
        else:
            logger.info('SpotTemplatePy::handler: unknown trigger')

    inv = datetime.now()
    retn = invokeCLI(event,context,logger) #invoke the function passed in (or def_funcsB.py if none)
    invend = datetime.now()
    delta = invend-start
    ms = int(delta.total_seconds() * 1000)
    invdelta = inv-start
    invms = int(invdelta.total_seconds() * 1000)
    retn += ':SpotTemplatePy:setup:{}:invoke:{}'.format(ms,invms)
    logger.info('invokeCLI return: {}'.format(retn))
    return retn

def invokeCLI(event,context,logger):
    #hard code it in case its not available in the context for some reason
    me = "arn:aws:lambda:us-west-2:443592014519:function:dep_funcsA"
    reqID = "unknown"
    logger.info('{} handler'.format(me))
    if context:
        lambda_client = boto3_client('lambda')
        me = context.invoked_function_arn
        reqID = context.aws_request_id

    fn = None
    if event:
        if 'functionName' in event:
            fn = event['functionName']

    #run_lambda does not support invoke via Payload arg
    invoke_response = None
    if context:
        if fn is None:
            # no function specified, invoke dep_funcsB in this same region
            k = me.rfind(":") #use this function's arn an swap out the function name
            fn = me[:k+1]+"dep_funcsB" #replace this function's name with dep_funcsB

        #must convert (via str) datetime to string before calling serialize (dumps)
        #b/c datetime is not serializable/builtin
        now = datetime.now()
        #msg = {k: event[k] for k in event if k not in ('functionName', 'msg')}
        msg = {}
        msg['msg'] = 'from {} at {}'.format(me,str(now))
        msg['eventSource'] = 'int:invokeCLI'
        msg['requestId'] = reqID
        msg['functionName'] = me
        payload=json.dumps(msg)
        logger.info('dep_funcsA.handler sending payload to {}: {}'.format(fn,msg))

        invoke_response = lambda_client.invoke(FunctionName=fn, 
            InvocationType='Event', Payload=payload) #Event type says invoke asynchronously
        delta = datetime.now()-now
        ms = int(delta.total_seconds() * 1000)
        me_str = 'REQ:{}:TIMER:CALL:{}:{}'.format(reqID,me,ms)
    else:
        me_str = '{} no context'.format(me)

    if invoke_response:
        serialized = jsonpickle.encode(invoke_response)
        logger.info('{} invoke_response: {}'.format(me,json.loads(serialized)))

    return me_str

if __name__ == "__main__":
    handler({'test':'test'},None)