import asyncio
from bleak import BleakClient,BleakScanner
import time
from redis import asyncio as aioredis
from redis import connection
import json

HUB_NAME = "Pybricks Hub"
TOPIC_PRODUCE = 'ble_to_redis'
TOPIC_CONSUME = 'redis_to_ble'
BLE_DEVICE_ADDRESS = 'XX:XX:XX:XX:XX:XX'
PYBRICKS_COMMAND_EVENT_CHAR_UUID = "c5f50002-8280-46da-89f4-6d8051e4aeef"

redis_client_pool = None
hub_client = None

async def connect_ble_device():
    global hub_client
    hub_client = BleakClient(BLE_DEVICE_ADDRESS,handle_disconnect)
    await hub_client.connect()
    print("Connected to BLE device")

async def send_to_redis(redis_client_pool,message):
    try:
        print(message)
        await redis_client_pool.xtrim(TOPIC_PRODUCE,maxlen=10)
        await redis_client_pool.xadd(TOPIC_PRODUCE, json.loads(message.encode('utf-8')))
    except Exception as ex:
        print(ex)

async def handle_ble_notifications(sender, data):
    if data[0] == 0x01:  # "write stdout" event (0x01)
        payload = data[1:]
        print(f"Received data from BLE: {payload}")
        await send_to_redis(redis_client_pool,payload.decode("utf-8"))

async def ble_task():
    global hub_client
    await hub_client.start_notify(PYBRICKS_COMMAND_EVENT_CHAR_UUID, handle_ble_notifications)
    try:
        while True:
            await asyncio.sleep(0.5)
    finally:
        await hub_client.stop_notify(PYBRICKS_COMMAND_EVENT_CHAR_UUID)

async def redis_task():
    global hub_client
    while True:
        data = await redis_client_pool.xrevrange(TOPIC_CONSUME,count=1)
        if data:
            for item in data:                
                print(f"Received message from Redis: {item[1]}")
                if item[1]:
                    command = item[1][bytes("action","utf-8")].decode("utf-8")
                    print(bytes(command,"UTF-8"))
                    await hub_client.write_gatt_char(PYBRICKS_COMMAND_EVENT_CHAR_UUID, 
                                                    b"\x06" + bytes(command,"UTF-8"), 
                                                    response=True)
                    print("Command Sent!")
                    await redis_client_pool.xtrim(TOPIC_CONSUME,maxlen=0)
        else:
            time.sleep(0.1)            
        
def handle_disconnect(_):
    print("Hub was disconnected.")
    if not main_task.done():
        main_task.cancel()

async def main():
    global redis_client_pool
    global BLE_DEVICE_ADDRESS
    global hub_client
    
    BLE_DEVICE_ADDRESS = await BleakScanner.find_device_by_name(HUB_NAME)
    if BLE_DEVICE_ADDRESS is None:
        print(f"could not find hub with name: {HUB_NAME}")
        return
    
    pool = aioredis.ConnectionPool.from_url("redis://localhost:6379",max_connections=50)
    
    redis_client_pool = await aioredis.Redis(connection_pool=pool)

    await connect_ble_device()
    
    await asyncio.gather(
        ble_task(),
        redis_task()
    )

if __name__ == '__main__':
    asyncio.run(main())
