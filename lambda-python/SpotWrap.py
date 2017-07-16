import boto3,json,logging,jsonpickle
from datetime import datetime
import uuid
sessionID = str(uuid.uuid4())

def callIt(event,context):
    #replace your import and handler method (replacing "handler") here:
    import SpotTemplate
    return SpotTemplate.handler(event,context)

def handleRequest(event, context):
    logger = logging.getLogger()
    ERR = False
    entry = 0 #all ints in Python3 are longs
    #for debugging
    #serialized = jsonpickle.encode(event)
    #logger.info('SpotWrapPython::handleRequest: event: {}'.format(json.loads(serialized)))
    #serialized = jsonpickle.encode(context)
    #logger.info('SpotWrapPython::handleRequest: context: {}'.format(json.loads(serialized)))

    errorstr = "SpotWrapPython"
    makeRecord(context,event,0,errorstr)
    entry = datetime.now()
    respObj = {}
    returnObj = {}
    status = '200'
    try: 
        respObj = callIt(event,context)
        if 'statusCode' in respObj:
            status = respObj['statusCode']
            if status != '200':
                ERR = True
                if 'exception' in respObj:
                    errorstr += ':{}:status:{}'.format(respObj['exception'],errcode)
                else:
                    errorstr += ':error_unknown:status:{}'.format(errcode)
    except Exception as e:
        errorstr += ':SpotWrap_exception:{}:status:400'.format(e)
        ERR = True
    finally: 
        delta = datetime.now()-entry
        duration = delta.total_seconds() * 1000
        makeRecord(context,None,duration,errorstr) #end event (event arg = null)

    if ERR:
        status = '400'
        respObj['SpotWrapError']=errorstr
    returnObj['statusCode'] = status
    returnObj['body'] = respObj
    logger.info('SpotWrapPython::handleRequest: returning: {}:{}'.format(status,respObj))
    return returnObj
    

#def logFn(start,msg,context,caller=None):
def makeRecord(context,event,duration,errorstr): 
    logger = logging.getLogger()
    #setup record defaults
    eventSource = "unknown"
    eventOp = "unknown"
    caller = "unknown"
    sourceIP = "000.000.000.000"
    msg = "unset" #random info
    requestID = sessionID #reqID of this aws lambda function set random as default
    functionName = "unset" #this aws lambda function name
    arn = "unset"
    region = "unset"
    accountID = "unset"
    APIGW = 1
    DYNDB = 2
    S3 = 3
    INVCLI = 4
    UNKNOWN = 0
    flag = UNKNOWN

    if context:
        arn = context.invoked_function_arn
        arns = arn.split(":")
        accountID = arns[4]
        region = arns[3]
        requestID = context.aws_request_id
        functionName = context.function_name

    if event:
        if 'requestId' in event:
            caller = event['requestId']
        if 'eventSource' in event:
            eventSource = event['eventSource']

        #figure out source and process appropriately
        if 'requestContext' in event:
            #API Gateway
            flag = APIGW
            req = event['requestContext']
            eventSource = 'aws:APIGateway:{}'.format(req['apiId'])
            msg = req['resourceId']
            acct = req['accountId']
            if accountID == 'unset':
                accountID = acct
            elif acct != accountID:
                accountID +=':{}'.format(acct)
            eventOp = req['path']
            tmpObj = req['identity']
            sourceIP = tmpObj['sourceIp']
            req = event['queryStringParameters']
            if 'msg' in req:
                msg += ':{}'.format(req['msg'])
        elif 'Records' in event:
            #S3 or DynamoDB or unknown
            recs = event['Records']
            obj = recs[0]
            eventSource = obj['eventSource']
            if eventSource.startswith('aws:s3'):
                flag = S3
                s3obj = obj['s3']
                s3bkt = s3obj['bucket']
                s3bktobj = s3obj['object']
                if 'responseElements' in obj:
                    caller = obj['responseElements']['x-amz-request-id']
                if 'requestParameters' in obj:
                    sourceIP = obj['requestParameters']['sourceIPAddress']
                if 'userIdentity' in obj:
                    accountID = obj['userIdentity']['principalId']
                if s3bkt and s3bktobj:
                    reg = obj['awsRegion']
                    if region != reg:
                        region +=':{}'.format(reg)
                    size = 0
                    if 'size' in s3bktobj:
                        size = s3bktobj['size']
                    eventOp = obj['eventName']
                    msg = '{}:{}:{}:{}:{}'.format(s3bkt['name'],s3bktobj['key'],size,s3bktobj['sequencer'],obj['eventTime'])
                else:
                    msg = 'Error, unexpected JSON object and bucket'
            elif eventSource.startswith('aws:dynamodb'):
                flag = DYNDB
                caller = obj['eventID']
                ev = obj['eventName']
                ddbobj = obj['dynamodb']
                mod = ''
                if ev == 'MODIFY':
                    mod = ddbobj['NewImage']
                    mod += ':{}'.format(ddbobj['OldImage'])
                elif ev == 'INSERT':
                    mod += ':{}'.format(ddbobj['NewImage'])
                elif ev == 'REMOVE':
                    mod += ':{}'.format(ddbobj['OldImage'])
                msg = '{}:{}:OP:{}'.format(ev,ddbobj['SequenceNumber'],mod)
                arn = obj['eventSourceARN']
                arns = arn.split(":")
                acct = arns[4]
                if accountID == 'unset':
                    accountID = acct
                elif acct != accountID:
                    accountID +=':{}'.format(acct)
                reg = arns[3]
                if region == 'unset':
                    region = reg
                elif reg != region:              
                    region += ':{}'.format(reg)
                rest = ''
                for i in range(5,len(arns)):
                    rest+=':{}'.format(arns[i])
                eventOp = rest
            else:
                flag = UNKNOWN
        elif eventSource.startswith('ext:invokeCLI'):
            flag = INVCLI
        elif eventSource.startswith('int:invokeCLI'):
            flag = INVCLI
        else:
            flag = UNKNOWN

        if flag == INVCLI:
            eventSource = 'aws:CLIInvoke:{}'.format(event['eventSource']);
            #caller set above ('requestId')
            if 'msg' in event:
                msg = event['msg']
            if 'accountId' in event:
                acct = event['accountId']
                if accountID == 'unset':
                    accountID = acct
                elif acct != accountID:
                    accountID +=':{}'.format(acct)
            if 'functionName' in event:
                eventOp = event['functionName']
            else:
                eventOp = event['eventSource']
            

        if flag == UNKNOWN:
            eventSource = 'unknown_source:{}'.format(functionName)
    #else: #event is None

    if eventSource == 'unset':
        #if functionName is "unset" then context is null!
        eventSource = 'unknown_source:{}'.format(functionName)

    dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
    table = dynamodb.Table('spotFnTable')
    table.put_item( Item={
        'requestID': requestID,
        'ts': int(round(datetime.now().timestamp())),
        'thisFnARN': arn,
        'caller': caller,
        'eventSource': eventSource,
        'eventOp': eventOp,
        'region': region,
        'accountID': accountID,
        'sourceIP': 'unknown',
        'message': msg,
        'duration': int(round(duration)),
        'start': str(event != None),
        'error': errorstr,
        }
    )

