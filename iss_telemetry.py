import threading
import time
import logging
from lightstreamer.client import LightstreamerClient, Subscription

# from: https://iss-mimic.github.io/Mimic/
iss_map = {
    "USLAB000039": "Total Mass",
    "USLAB000059": "Cabin Temperature",
    "NODE3000005": "Urine Tank",
    "USLAB000010": "Gyroscope Momentum"
}

class TelemetryListener:
    def __init__(self, data_store):
        self.data_store = data_store

    def onSubscription(self):
        pass

    def onUnsubscription(self):
        pass

    def onItemUpdate(self, update):
        item_id = update.getItemName()
        value = update.getValue("Value")
        readable_name = iss_map.get(item_id, item_id) # fetch name from map
        
        try:
            float_value = float(value)
            if "temperature" in readable_name.lower():
                self.data_store[readable_name] = f"{float_value:.1f}°"
            elif 0 <= float_value <= 100: # if it smells and looks like a percentage...
                self.data_store[readable_name] = f"{float_value:.1f}%"
            else:
                self.data_store[readable_name] = f"{float_value:.1f}"
        except ValueError:
            self.data_store[readable_name] = value # cant be converted into a float
    
class ISSTelemetryStreamer(threading.Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True # Ensure thread dies when app closes
        self.latest_data = {}
        self._stop_event = threading.Event()

    def run(self):
        logging.getLogger().setLevel(logging.CRITICAL) # only log when critical
        # subscribe to ISS telemetry
        client = LightstreamerClient("https://push.lightstreamer.com", "ISSLIVE")
        sub = Subscription(
            mode="MERGE",
            items=list(iss_map.keys()),
            fields=["TimeStamp", "Value"]
        )
        listener = TelemetryListener(self.latest_data)
        sub.addListener(listener)
        try:
            client.subscribe(sub)
            client.connect()
            while not self._stop_event.is_set():
                time.sleep(1)
        except Exception as e:
            self.latest_data["Status"] = "Connection Error"
        finally:
            client.disconnect()

    def stop(self):
        self._stop_event.set()

    def get_data(self):
        return self.latest_data