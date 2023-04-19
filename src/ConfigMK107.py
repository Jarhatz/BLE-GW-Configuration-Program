import simplepyble # pip install simplepyble
import codecs
import time

# # # MODIFY AND UPDATE CONSTANTS TO FIT YOUR NEEDS # # #
WIFI_SSID = "[NETWORK_NAME]"
WIFI_PASSWORD = "[NETWORK_PWD]"
SITE = "[PREFIX FOR DEVICE NAMING CONVENTION]"

SCAN_DURATION = 5000 # 5 sec
DEVICE_NAME = 'MK107'
MQTT_HOST = "[AWS_IOT_ENDPOINT]" # port (default): 8883

CA_FILE = r"\certs\AmazonRootCA1.pem"
CLIENT_CERTIFICATE_FILE = r"\certs\client-certificate.pem.crt"
CLIENT_KEY_FILE = r"\certs\client-key-private.pem.key"

def run():
    adapters = simplepyble.Adapter.get_adapters()
    if len(adapters) == 0:
        print("NO ADAPTERS FOUND.")
    else:
        adapter = adapters[0]
        devices = scan(adapter, SCAN_DURATION)
        if (len(devices)):
            filtered_devices = filter(devices)
            if (len(filtered_devices)):
                for i, device in enumerate(filtered_devices):
                    print(f"\n[{i}] CONFIGURING {device.identifier()} [{device.address()}]")
                    configDriver(device)
                    print(f"[{i}] CONFIGURED {device.identifier()} [{device.address()}]\n")
            else:
                print(f"NO CONNECTABLE {DEVICE_NAME} DEVICE FOUND.")
        else:
            print("NO DEVICES SCANNED.")
        

def scan(adapter, time):
    print(f"USING {adapter.identifier()} [{adapter.address()}]")
    adapter.set_callback_on_scan_start(lambda: print("SCAN STARTED."))
    adapter.set_callback_on_scan_stop(lambda: print("SCAN COMPLETE."))
    adapter.set_callback_on_scan_found(lambda device: print(
        f"\t(connectable) {device.identifier()} [{device.address()}]") 
        if device.is_connectable() else print(
        f"\t(not-connectable) {device.identifier()} [{device.address()}]"))
    adapter.scan_for(time)
    return adapter.scan_get_results()

def filter(devices):
    filtered_devices = []
    for i, device in enumerate(devices):
        if device.is_connectable() and device.identifier().startswith(DEVICE_NAME):
            filtered_devices.append(device)
        elif device.identifier().startswith(DEVICE_NAME):
            print(f"{device.identifier()} [{device.address()} DEVICE NOT CONNECTABLE.")
    return filtered_devices

def configDriver(device):
    print(f"CONNECTING TO {device.identifier()} [{device.address()}]")
    device.connect()
    print("CONNECTED.")
    
    services = device.services()
    scp = ServiceCharacteristicPair()
    for service in services:
        print(f"\tService: [{service.uuid()}]")
        for characteristic in service.characteristics():
            print(f"\t\tCharacteristic: [{characteristic.uuid()}]")
            scp.append(service.uuid(), characteristic.uuid())
    
    print("PASSWORD VERIFICATION: Moko4321")
    writeConfig(device, scp, "0000aa00", "ED0101084D6F6B6F34333231", notify=True)
    
    print(f"WIFI SSID {WIFI_SSID}")
    if len(WIFI_SSID) <= 32:
        payload = generatePayload(cmd_id="02", data_str=WIFI_SSID)
        writeConfig(device, scp, "0000aa03", payload, notify=True)
    else:
        print(f"\tWIFI SSID TOO LONG [{len(WIFI_SSID)}]")
    
    print(f"WIFI PASSWORD: {WIFI_PASSWORD}")
    if len(WIFI_PASSWORD) <= 64:
        payload = generatePayload(cmd_id="03", data_str=WIFI_PASSWORD)
        writeConfig(device, scp, "0000aa03", payload)
    else:
        print(f"\tWIFI PASSWORD TOO LONG [{len(WIFI_PASSWORD)}]")
    
    print("ENCRYPTION TYPE: Self Signed Certificates")
    writeConfig(device, scp, "0000aa03", "ED01040103")
    
    print(f"MQTT HOST: {MQTT_HOST}")
    if len(MQTT_HOST) <= 64:
        payload = generatePayload(cmd_id="05", data_str=MQTT_HOST)
        writeConfig(device, scp, "0000aa03", payload)
    else:
        print(f"\tHOSTNAME TOO LONG [{len(MQTT_HOST)}]")
        
    print("MQTT PORT: 8883")
    writeConfig(device, scp, "0000aa03", "ED01060222B3")
    
    print("MQTT CLEAN SESSION: 1")
    writeConfig(device, scp, "0000aa03", "ED01070101")
    
    print("MQTT KEEP ALIVE: 30")
    writeConfig(device, scp, "0000aa03", "ED0108011E")
    
    print("MQTT QOS: 1")
    writeConfig(device, scp, "0000aa03", "ED01090101")
    
    client_id = "GW_" + formatMAC(device.address())
    print(f"CLIENT ID: {client_id}")
    if len(client_id) <= 64:
        payload = generatePayload(cmd_id="0A", data_str=client_id)
        writeConfig(device, scp, "0000aa03", payload)
    else:
        print(f"\tCLIENT ID TOO LONG [{len(client_id)}]")
        
    device_id = "site-" + SITE + "-gw-" + formatMAC(device.address())[-4:]
    print(f"DEVICE ID: {device_id}")
    if len(device_id) <= 32:
        payload = generatePayload(cmd_id="0B", data_str=device_id)
        writeConfig(device, scp, "0000aa03", payload)
    else:
        print(f"\tDEVICE ID TOO LONG [{len(device_id)}]")
    
    subscribe_topic = "/gw/incoming/" + formatMAC(device.address())
    print(f"SUBSCRIBE TOPIC: {subscribe_topic}")
    if len(subscribe_topic) <= 128:
        payload = generatePayload(cmd_id="0C", data_str=subscribe_topic)
        writeConfig(device, scp, "0000aa03", payload)
    else:
        print(f"\tSUBSCRIBE TOPIC TOO LONG [{len(subscribe_topic)}]")
        
    publish_topic = "/gw/outgoing/" + formatMAC(device.address())
    print(f"PUBLISH TOPIC: {publish_topic}")
    if len(publish_topic) <= 128:
        payload = generatePayload(cmd_id="0D", data_str=publish_topic)
        writeConfig(device, scp, "0000aa03", payload)
    else:
        print(f"\tSUBSCRIBE TOPIC TOO LONG [{len(publish_topic)}]")
    
    print("NTP SERVER: time.windows.com")
    writeConfig(device, scp, "0000aa03", "ED010E0F74696D652E77696E646F77732E636F6D")
    
    print("TIMEZONE: UTC-7:00")
    writeConfig(device, scp, "0000aa03", "ED010F01F9")
    
    print("--- CA FILE ---")
    partitionFile(device, scp, "0000aa03", getFileBytes(CA_FILE), "03")
    
    print("--- CLIENT CERTIFICATE FILE ---")
    partitionFile(device, scp, "0000aa03", getFileBytes(CLIENT_CERTIFICATE_FILE), "04")
    
    print("--- CLIENT KEY FILE ---")
    partitionFile(device, scp, "0000aa03", getFileBytes(CLIENT_KEY_FILE), "05")
        
    print("EXIT CONFIGURATION MODE")
    writeConfig(device, scp, "0000aa03", "ED01010101")
    
    print("SLEEPING FOR 5 SECONDS...")
    time.sleep(5)
    
    print(f"DISCONNECTING FROM {device.identifier()} [{device.address()}]")
    device.disconnect()
    print("DISCONNECTED.")

def writeConfig(device, scp, search_characteristic, payload, notify=False):
    i = scp.find(search_characteristic)
    if i:
        service_uuid, characteristic_uuid = scp.get(i)
        print(f"\tService: [{service_uuid}]")
        print(f"\tCharacteristic: [{characteristic_uuid}]")
        print(f"\tHEX: `{payload}`")
        device.write_request(service_uuid, characteristic_uuid, bytes.fromhex(payload))
        if notify:
            response = device.notify(service_uuid, characteristic_uuid, lambda data: print(f"\tResponse: {codecs.encode(data, 'hex').decode('utf-8').upper()}"))
    else:
        print(f"CHARACTERISTIC [{search_characteristic}] NOT FOUND.")

def generatePayload(cmd_id, data_str):
    length = "{:02X}".format(len(data_str))
    data = codecs.encode(data_str.encode(), 'hex').decode().upper()
    return "ED01" + cmd_id + length + data

def partitionFile(device, scp, search_characteristic, file_bytes, cmd_id):
    i = scp.find(search_characteristic)
    if i:
        service_uuid, characteristic_uuid = scp.get(i)
        print(f"\tService: [{service_uuid}]")
        print(f"\tCharacteristic: [{characteristic_uuid}]")

        num_packets = int(len(file_bytes) / 238)
        for i in range(0, len(file_bytes), 238):
            file_chunk = file_bytes[i : i + 238]
            packet_payload = generateFilePayload(cmd_id, file_chunk, num_packets, first=not bool(i))
            print(f"\t\t[{num_packets}] HEX (header): `{packet_payload[:12]} + data`")
            device.write_request(service_uuid, characteristic_uuid, bytes.fromhex(packet_payload))
            num_packets -= 1
    else:
        print(f"CHARACTERISTIC [{search_characteristic}] NOT FOUND.")

def generateFilePayload(cmd_id, file_chunk, num_packets, first=False):
    flag = "{:02X}".format(int(first))
    remaining_packets = "{:02X}".format(num_packets)
    length = "{:02X}".format(len(file_chunk))
    data = codecs.encode(file_chunk, 'hex').decode().upper()
    return "EE01" + cmd_id + flag + remaining_packets + length + data

def getFileBytes(filename):
    with open(filename, 'rb') as file:
        file_bytes = file.read()
    return file_bytes

def formatMAC(address):
    return address.replace(":", "").upper()

class ServiceCharacteristicPair:
    def __init__(self):
        self.list = []
    
    def append(self, service_uuid, characteristic_uuid):
        self.list.append((service_uuid, characteristic_uuid))
    
    def get(self, i):
        return self.list[i]
    
    def find(self, search_uuid):
        for i, (_, characteristic_uuid) in enumerate(self.list):
            if characteristic_uuid.startswith(search_uuid):
                return i

if __name__ == '__main__':
    print(f"RUNNING ON {simplepyble.get_operating_system()}")
    run()
