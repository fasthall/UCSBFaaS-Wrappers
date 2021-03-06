'''
Python reducer function

* Copyright 2016, Amazon.com, Inc. or its affiliates. All Rights Reserved.
*
* Licensed under the Amazon Software License (the "License").
* You may not use this file except in compliance with the License.
* A copy of the License is located at
*
* http://aws.amazon.com/asl/
*
* or in the "license" file accompanying this file. This file is distributed
* on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
* express or implied. See the License for the specific language governing
* permissions and limitations under the License. 

'''

import boto3
import json
import random
import resource
from io import StringIO
#import StringIO
#import urllib2
import time

# create an S3 & Dynamo session
s3 = boto3.resource('s3')
s3_client = boto3.client('s3')

# constants
TASK_MAPPER_PREFIX = "task/mapper/";
TASK_REDUCER_PREFIX = "task/reducer/";

def write_to_s3(bucket, key, data, metadata):
    # Write to S3 Bucket
    s3.Bucket(bucket).put_object(Key=key, Body=data, Metadata=metadata)

def handler(event, context):
    
    start_time = time.time()
    
    job_bucket = event['jobBucket']
    bucket = event['bucket']
    reducer_keys = event['keys']
    job_id = event['jobId']
    r_id = event['reducerId']
    step_id = event['stepId']
    n_reducers = event['nReducers']
    
    # aggr 
    results = {}
    line_count = 0

    # INPUT JSON => OUTPUT JSON

    # Download and process all keys
    #print("HERE1 in reducer")
    for key in reducer_keys:
        response = s3_client.get_object(Bucket=job_bucket, Key=key)
        contents = response['Body'].read()

        try:
            #for srcIp, val in json.loads(contents).iteritems():
            for srcIp, val in json.loads(contents).items():
                line_count +=1
                if srcIp not in results:
                    results[srcIp] = 0
                results[srcIp] += float(val)
        except Exception as e:
            print(e)

    time_in_secs = (time.time() - start_time)
    pret = [len(reducer_keys), line_count, time_in_secs]
    print("Reducer output", pret)

    if n_reducers == 1:
        # Last reducer file, final result
        fname = "%s/result" % job_id
    else:
        fname = "%s/%s%s/%s" % (job_id, TASK_REDUCER_PREFIX, step_id, r_id)
    
    metadata = {
                    "linecount":  '%s' % line_count,
                    "processingtime": '%s' % time_in_secs,
                    "memoryUsage": '%s' % resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
               }

    write_to_s3(job_bucket, fname, json.dumps(results), metadata)
    if n_reducers == 1: #final reducer
        #need to let coordinator know by writing to the TASK_REDUCER_PREFIX
        fname = "%s/%sdone" % (job_id, TASK_REDUCER_PREFIX)
        metadata = {
                    "linecount":  '%s' % line_count,
                    "processingtime": '%s' % time_in_secs,
                    "memoryUsage": '%s' % resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
               }
        write_to_s3(job_bucket, fname, json.dumps(results), metadata)
    return pret
