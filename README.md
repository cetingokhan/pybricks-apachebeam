
# Remote-Controlled Car Project with Lego Spike, Pybricks, and Apache Beam

Using Lego Spike and a Lego remote controller, I built a remote-controlled car with the Pybricks library. The car is equipped with a distance sensor at the front, allowing it to continuously collect distance data while driving.

This data is sent via Bluetooth to a proxy running on my PC, which then forwards the data to a Redis stream. With an Apache Beam stream pipeline I developed, I monitor these data in real-time. When the distance drops below 300 cm, Apache Beam sends a "stop" message to another Redis stream topic. The proxy on my PC listens for this message and sends a command to the Pybricks hub to stop the car, preventing it from colliding with obstacles. Beam also sends all the received data to Influxdb.



![alt text](docs/beam_pybricks_arch.drawio.svg)


### Create python virtual environment
```
python -m venv venv
./venv/Scripts/activate

pip install -r requirements.txt
```

### Start Redis and InfluxDB with docker-compose
```
docker compose up
```
InfluxDB UI: http://localhost:8086/


### Deploy Pybriks Code into Hub

```
cd .\pybricks
pybricksdev run ble --name "Pybricks Hub" .\car_hubv2.py
```

### Start Proxy
```
cd .\hub_proxy
python .\proxy.py
```
start hub after Hub Connected message and then
press remote controller green button for connect to hub

### Start Beam Pipeline
```
cd .\beam_pipeline
python .\pipeline.py
```

![alt text](docs/beam_spike.gif)



