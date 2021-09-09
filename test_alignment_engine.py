import time
import xmlrpc.client

IP = "localhost"
ALIGNMENT_ENGINE_PORT = 8002

def save_picture(filename, content):
    with open(filename, "wb") as f:
        f.write(content)

alignment_engine_proxy = xmlrpc.client.ServerProxy(f"http://{IP}:{ALIGNMENT_ENGINE_PORT}", allow_none=True)  # create client proxy to alignment engine
primary, secondary = alignment_engine_proxy.initialize()

time.sleep(1)
print(f"Taking picture on primary unit")
start_time = time.time()
picture = alignment_engine_proxy.get_picture(primary)
print(f"Done receiving picture in {time.time() - start_time}")

# NOTE: XMLRPC receives a Binary object, to get contents of the object use obj.data -> important for other languages
if picture is not None:
    save_picture("test.jpg", picture.data)