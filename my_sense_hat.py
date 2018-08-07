#!/usr/bin/env python
import json
import signal
import sys
import time
from ConfigParser import ConfigParser
import paho.mqtt.client as mqtt
from sense_hat import SenseHat


config = ConfigParser()
config.read('sense.ini')


OG_HOST = config.get('opengate', 'host')
OG_MQTT_PORT = config.getint('opengate', 'mqtt_port')
MQTT_KEEPALIVE = 60
OG_API_KEY = config.get('opengate', 'apikey')
OG_DEVICE_ID = config.get('opengate', 'deviceid')

OG_SUBSCRIBE_TOPIC = 'odm/request/{0}'
OG_PUBLISH_RESPONSE_TOPIC = 'odm/response/{0}'
OG_PUBLISH_DMM_TOPIC = 'odm/dmm/{0}'
OG_PUBLISH_IOT_TOPIC = 'odm/iot/{0}'

COLOR_BLACK = [0, 0, 0]
COLOR_WHITE = [255, 255, 255]
COLOR_BLUE = [0, 0, 255]
COLOR_RED = [255, 0, 0]

sense = SenseHat()
sense.set_rotation(180)
bg_color = COLOR_BLACK
text_color = COLOR_BLUE
text_scroll_speed = 0.075

sampling_loop_enabled = True
mqtt_enabled = False
mqtt_client = None


def signal_handler(signal, frame):
    '''
    Handler to manage Ctrl-C
    '''
    global sampling_loop_enabled
    sampling_loop_enabled = False
    print('Sampling loop disabled')


def on_connect(caller_mqtt_client, userdata, flags, result_code):
    '''`on_connect` callback implementation'''
    print 'OpenGate MQTT client connected with result code ' + str(result_code)

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    caller_mqtt_client.subscribe(OG_SUBSCRIBE_TOPIC.format(OG_DEVICE_ID), qos=1)


def on_message(caller_mqtt_client, userdata, message):
    pass


def on_publish(caller_mqtt_client, userdata, result): #create function for callback
    print("Data published \n")


def enable_mqtt(mqtt_user, mqtt_password, mqtt_host, mqtt_port, mqtt_keepalive=MQTT_KEEPALIVE):
    global mqtt_client
    global mqtt_enabled
    mqtt_client = mqtt.Client(client_id=mqtt_user)
    mqtt_client.username_pw_set(mqtt_user, mqtt_password)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.on_publish = on_publish
    while not mqtt_enabled:
        try:
            print 'Connecting to {}:{}'.format(mqtt_host, mqtt_port)
            mqtt_client.connect(mqtt_host, mqtt_port, mqtt_keepalive)
            mqtt_enabled = True
        except:
            show_message('MQTT connect error', _text_color=COLOR_RED)
            time.sleep(2)

    # Blocking call that processes network traffic, dispatches callbacks and handles reconnecting.
    # Other loop*() functions are available that give a threaded interface and a manual interface.
    # mqtt_client.loop_forever()

def show_message(message, _text_color=text_color):
    print message
    sense.show_message(message, text_scroll_speed, text_color, bg_color)

def get_data_points_template(data_stream_id, value):
    data_points_dict = {
                'version': '1.0.0',
                'device': OG_DEVICE_ID,
                'datastreams': [
                    {
                        'id': data_stream_id,
                        'datapoints': [
                            { 'at': int(round(time.time())), 'value': round(value, 2) }
                        ]
                    }
                        
                ]
            }
    return data_points_dict

def single_value_sampling(sampling_function, message_template, data_stream_id):
    if sampling_loop_enabled:
        value = sampling_function()
        message = message_template % value
        show_message(message)
        data_points = get_data_points_template(data_stream_id, value)
        data_points_json = json.dumps(data_points, indent=2)
        print 'Publishing %s: %s' % (message, data_points_json)
        ret= mqtt_client.publish(OG_PUBLISH_IOT_TOPIC, data_points_json) #publish
 

def main():
    enable_mqtt(OG_DEVICE_ID, OG_API_KEY, OG_HOST, OG_MQTT_PORT)
    while sampling_loop_enabled:

        single_value_sampling(sense.get_temperature_from_pressure, 'Temperature from pressure %.2f C', 'temperature.from.pressure')
        single_value_sampling(sense.get_temperature_from_humidity, 'Temperature from humidity %.2f C', 'temperature.from.humidity')
        single_value_sampling(sense.get_humidity, 'Humidity %.2f %%', 'humidity')
        single_value_sampling(sense.get_pressure, 'Pressupre %.2f mbar', 'pressure')

        #compass = sense.get_compass()
        #gyroscope = sense.get_gyroscope()

        sense.clear()
        sense.load_image('smily.png')
        time.sleep(2)
        sense.clear()

    print 'Bye'

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    main()

