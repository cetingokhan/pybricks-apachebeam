import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
from redis import Redis
import time
import json

class ReadFromRedis(beam.PTransform):
    def __init__(self, host, port, stream_key,count):
        super().__init__()
        self.redis_client = Redis(host=host, 
                                  port=port)
        self.stream_key = stream_key
        self.count = count
        

    def expand(self, p):
        return (
            p
            | beam.Create([None])
            | beam.FlatMap(self._read_from_redis)
        )
    def _read_from_redis(self, element):
        while True:
            data = self.redis_client.xrevrange(self.stream_key,count=self.count)
            if data:
                for item in data:
                    self.redis_client.xtrim(self.stream_key,maxlen=0)
                    yield item[1]
            else:
                time.sleep(0.1)
        

class WriteToRedis(beam.DoFn):
    def __init__(self, host, port, stream_key):
        self.redis_client = Redis(host=host, 
                            port=port)
        self.stream_key = stream_key

    def process(self, element):
        import json
        #print(element)
               
        print(f"Value: {element[1]}")
        data = {"action":element[1].decode("utf-8")}
        self.redis_client.xtrim(self.stream_key,maxlen=0)
        self.redis_client.xadd(self.stream_key, data)

class FilterAndRouteFn(beam.DoFn):
    def process(self, element):
        distance = element[bytes("distance","utf-8")].decode('utf-8')
        if int(distance) < 300:
            yield (b'action', b'stp')
        else:
            yield beam.pvalue.TaggedOutput('elasticsearch', distance)

class ExtractMeasure(beam.DoFn):
    def process(self, element):
        msg = element[bytes("distance","utf-8")].decode('utf-8')
        return msg

def run():

    options = PipelineOptions([
        "--streaming"])
    
    with beam.Pipeline(options=options, runner='DirectRunner') as pipeline:
        messages = (
            pipeline
            | 'Read from Redis Stream' >> beam.io.Read(ReadFromRedis(host='localhost', port=6379, stream_key='ble_to_redis',count=10))
            #| "PrintEncodedMessages" >> beam.Map(print)
            | 'FilterAndRoute' >> beam.ParDo(FilterAndRouteFn()).with_outputs('elasticsearch', main='redis')
        )
        
        redis_output = messages['redis'] | 'Write to Redis Stream' >> beam.ParDo(WriteToRedis(host='localhost', port=6379, stream_key='redis_to_ble'))
        elasticsearch_output = messages['elasticsearch'] | "PrintElasticMessages" >> beam.Map(print)

if __name__ == '__main__':
    run()
