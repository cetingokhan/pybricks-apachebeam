import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
from redis import Redis
import time
import json
from influxdb_client import InfluxDBClient, Point, WriteOptions
import datetime

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

class WriteToInfluxDB(beam.DoFn):
    def __init__(self, influxdb_url, token, org, bucket):
        super(WriteToInfluxDB, self).__init__()
        self.influxdb_url = influxdb_url
        self.token = token
        self.org = org
        self.bucket = bucket

    def start_bundle(self):
        self.client = InfluxDBClient(url=self.influxdb_url, token=self.token, org=self.org)
        self.write_api = self.client.write_api(write_options=WriteOptions(batch_size=1))

    def process(self, element):
        distance = element[bytes("d","utf-8")].decode('utf-8')
        angle = element[bytes("a","utf-8")].decode('utf-8')
        
        point = Point("pybricks") \
            .field("distance", distance) \
            .field("angle",angle).time(datetime.datetime.utcnow())
        self.write_api.write(bucket=self.bucket, record=point)

    def finish_bundle(self):
        self.write_api.__del__()
        self.client.__del__()
        
class FilterAndRouteFn(beam.DoFn):
    def __init__(self):
        self.last_write_time = 0
            
    def process(self, element):
        distance = element[bytes("d","utf-8")].decode('utf-8')
        if int(distance) < 300:
            current_time = time.time()
            if current_time - self.last_write_time >= 20:
                self.last_write_time = current_time
                print(datetime.datetime.now())
                yield (b'action', b'stp')
        else:
            yield beam.pvalue.TaggedOutput('influx', element)

def run():

    options = PipelineOptions([
        "--streaming"])
    
    with beam.Pipeline(options=options, runner='DirectRunner') as pipeline:
        messages = (
            pipeline
            | 'Read from Redis Stream' >> beam.io.Read(ReadFromRedis(
                host='localhost', 
                port=6379, 
                stream_key='ble_to_redis',
                count=10))
            #| "PrintEncodedMessages" >> beam.Map(print)
            | 'FilterAndRoute' >> beam.ParDo(FilterAndRouteFn()).with_outputs('influx', main='redis')
        )
        
        redis_output = messages['redis'] | 'Write to Redis Stream' >> beam.ParDo(WriteToRedis(
            host='localhost',
            port=6379, 
            stream_key='redis_to_ble'))
        influx_output = messages['influx'] | "Write to Influx DB" >> beam.ParDo(WriteToInfluxDB(
                influxdb_url="http://localhost:8086",
                token="Fgfo4pfCk7IOeTbierjZpAWXwqg-GMHW7AbByeFDuUSMwpuX76MeWnG2w6fop1bukV_Q4_mglOLKsYMTqQh2HQ==",
                org="gokhancetin",
                bucket="pybricks"
            ))

if __name__ == '__main__':
    run()
