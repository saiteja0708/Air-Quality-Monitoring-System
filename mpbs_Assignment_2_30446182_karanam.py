# Import all necessary Libraries
import requests
import json
import time
from matplotlib import pyplot as plt
import numpy as np
import dht11
import RPi.GPIO as RPI
import thingspeak
from collections import deque
from Adafruit_LED_Backpack import SevenSegment
from luma.core.interface.serial import spi, noop
from luma.led_matrix.device import max7219
from luma.core.render import canvas


#  Thingspeak Channel id and key
channel_id = 2655368
write_key = 'G5AQQ6LNS3SDOL76'
read_key = 'POE3EBVUQYPJF2PC'


# GPIO Setup
R_button = 19
L_button = 25
gpio_list_inputs = [L_button , R_button]

temp_hum_sensor = 4

# Setting up GPIO Channel
RPI.setmode(RPI.BCM)  # GPIO numbering system
RPI.setup(gpio_list_inputs, RPI.IN, pull_up_down=RPI.PUD_OFF)

#  Setup 7-Segment Display
seven_sg =  SevenSegment.SevenSegment(address = 0x70)
seven_sg.begin()


# Setup LED Matrix Display
my_spi = spi(port=0, device=1, gpio=noop())
cascaded = 1
block_orientation = 90
rotate = 0
my_led = max7219(my_spi, cascaded=cascaded, block_orientation=block_orientation, rotate=rotate)


#  Initial Values for the program
graph_position = 0
graph_range = 100
start_time = time.time()
last_10_sec_check = 0  #  To store the last time the 10 function ran
last_60_sec_check = 0  # To store the last time the 60function ran

#   Temperature and Humidity values for 3.2
buffer_size = 100
buffer_temp = deque([18, 17, 19, 21, 20, 19, 18, 16, 17, 18, 19, 21, 23, 22, 21, 20, 22, 23,
                     22, 21, 19, 20, 19, 18, 17, 18, 20, 21, 23, 22, 20, 19, 18, 17, 19, 21,
                     22, 23, 24, 23, 22, 21, 20, 19, 18, 17, 16, 18, 17, 19, 20, 22, 21, 20,
                     19, 18, 17, 19, 21, 20, 23, 22, 21, 19, 20, 19, 18, 19, 20, 22, 21, 19,
                     18, 19, 21, 23, 22, 21, 19, 18, 17, 16, 18, 17, 20, 22, 21, 20, 19, 18,
                     17, 19, 20, 21, 23, 22, 24, 23, 22, 21], maxlen=buffer_size)

buffer_hum = deque([25, 27, 28, 30, 33, 33, 32, 31, 31, 26, 27, 29, 29, 27, 28, 27, 27, 26,
                    24, 25, 23, 24, 25, 23, 23, 22, 22, 24, 23, 20, 19, 21, 20, 22, 23, 21,
                    24, 24, 22, 23, 23, 26, 28, 25, 26, 28, 29, 28, 30, 29, 31, 30, 32, 31,
                    30, 33, 35, 32, 31, 34, 36, 35, 37, 37, 38, 35, 37, 38, 41, 43, 45, 44,
                    43, 46, 44, 45, 41, 42, 40, 40, 39, 41, 44, 45, 47, 50, 50, 54, 53, 57,
                    58, 60, 61, 61, 67, 65, 66, 70, 71, 67], maxlen=buffer_size)

def clear_seven_segment_display():  # Clears the 7-segment display
    seven_sg.clear()
    seven_sg.write_display()

def display_number_on_seven_segment(number):  # Displays a number on the 7-segment display
    clear_seven_segment_display()
    number = round(number, 2)
    seven_sg.print_number_str(str(number))
    seven_sg.write_display()


def filter_non_none_values(input_list):  # Filters out None values from a list and converts to integers
    filtered_list = list(filter(lambda x: x is not None, input_list))
    filtered_list = list(map(int, filtered_list))
    return filtered_list

def scale_values_for_bars(value_list):
    if not value_list or max(value_list) == 0:
        return [0] * len(value_list)  # Return a list of zeros if the input list is empty or contains only zeros
    max_value = max(value_list)
    return [int((value / max_value) * 6) for value in value_list]

def compress_data_list(data_list, number_of_points=8):
    if len(data_list) == 0:
        return [0] * number_of_points  # Return a list of zeros if the input list is empty

    segment_length = len(data_list) // number_of_points
    compressed_data = [int(round(sum(data_list[i * segment_length:(i + 1) * segment_length]) / segment_length)) for i in range(number_of_points)]
    return scale_values_for_bars(compressed_data)

def update_graph_position(direction):  # Updates the position of the graph based on direction
    global graph_position
    if direction == "right":
        if graph_position < 4:
            graph_position += 1
        else:
            graph_position = 0
    elif direction == "left":
        if graph_position > 0:
            graph_position -= 1
        else:
            graph_position = 4

def get_seven_segment_value():  # Determines which value to display on the 7-segment display
    if graph_position == 0:
        display_value = np.mean(pm1_values)
    elif graph_position == 1:
        display_value = np.mean(pm25_values)
    elif graph_position == 2:
        display_value = np.mean(pm10_values)
    elif graph_position == 3:
        display_value = np.mean(temperature_data)
    elif graph_position == 4:
        display_value = np.mean(humidity_data)
    return display_value


def render_led_plot(data_for_plot):  # Renders a plot of data on the LED matrix
    display_value = get_seven_segment_value()
    display_number_on_seven_segment(display_value)
    with canvas(my_led) as draw:
        draw.point((graph_position, 0), fill="white")
        for index, value in enumerate(data_for_plot):
            draw.point((index, 8 - value), fill="white")




#  3.1.1.Accessing ThinkSpeak Channel

url_feed = 'https://thingspeak.com/channels/343018/feeds.json?results=100'

#  //// Initializing arrays for each field ////
pm10_values = []
pm10_avg60_values = []
pm25_values = []
pm25_avg60_values = []
pm1_values = []
pm1_avg60_values = []
aqi_values = []
temperature_data = []
humidity_data = []


#  //// Extracting the last 100 readings for each field ////

def retrieve_sensor_data():  # Fetches and processes data from the API
    global pm10_values, pm10_avg60_values, pm25_values, pm25_avg60_values, pm1_values, pm1_avg60_values, aqi_values
    # Fetch data from the API
    response = requests.get(url_feed).json()  # Use url_feed here

    # Decode the cloud reading by JSON
    feed_data = response['feeds']

    # Clear previous lists to ensure they only hold the latest 100 values
    pm10_values.clear()
    pm10_avg60_values.clear()
    pm25_values.clear()
    pm25_avg60_values.clear()
    pm1_values.clear()
    pm1_avg60_values.clear()
    aqi_values.clear()

    for entry in feed_data:
        pm10_values.append(entry['field1'])
        pm10_avg60_values.append(entry['field2'])
        pm25_values.append(entry['field3'])
        pm25_avg60_values.append(entry['field4'])
        pm1_values.append(entry['field5'])
        pm1_avg60_values.append(entry['field6'])
        aqi_values.append(entry['field7'])

    clean_data_lists()  # Converts lists to integer type


def clean_data_lists():  # Cleans and converts all data lists
    global pm10_values, pm10_avg60_values, pm25_values, pm25_avg60_values, pm1_values, pm1_avg60_values, aqi_values
    pm10_values = filter_non_none_values(pm10_values)
    pm10_avg60_values = filter_non_none_values(pm10_avg60_values)
    pm25_values = filter_non_none_values(pm25_values)
    pm25_avg60_values = filter_non_none_values(pm25_avg60_values)
    pm1_values = filter_non_none_values(pm1_values)
    pm1_avg60_values = filter_non_none_values(pm1_avg60_values)
    aqi_values = filter_non_none_values(aqi_values)

retrieve_sensor_data()


# Visualizing the arrays
# print("PM10 Array =", pm10_array)
# print("PM10 avg60 Array =", pm10_avg60_array)
# print("PM2.5 Array =", pm25_array)
# print("PM2.5 avg60 Array =", pm25_avg60_array)
# print("PM1 Array =", pm1_array)
# print("PM1 avg60 Array =", pm1_avg60_array)
# print("AQI Array =", aqi_array)


#  //// Saving arrays to a separate JSON file ////
arrays_data = {
    "PM10": pm10_values,            # Array containing PM10 values
    "PM10_avg60": pm10_avg60_values,  # Array containing averaged PM10 values over 60 minutes
    "PM2.5": pm25_values,            # Array containing PM2.5 values
    "PM2.5_avg60": pm25_avg60_values,  # Array containing averaged PM2.5 values over 60 minutes
    "PM1": pm1_values,               # Array containing PM1 values
    "PM1_avg60": pm1_avg60_values,    # Array containing averaged PM1 values over 60 minutes
    "AQI": aqi_values                # Array containing AQI values
}

# Write the arrays data to a JSON file
with open('field_arrays.json', 'w') as json_file:
    json.dump(arrays_data, json_file, indent=4)


# print("Field arrays saved to 'field_arrays.json'.")


def show_plots():
    plt.subplots(figsize=(10, 15))
    plt.subplots_adjust(hspace=0.5)

    def plot_data(x_axis, y_data, color, title):
        plt.plot(x_axis, y_data, color)
        y_mean = np.mean(y_data)
        y_mean_array = np.full(shape=len(x_axis), fill_value=y_mean)
        plt.plot(x_axis, y_mean_array, color[0], linestyle=':')
        plt.xlabel('Sample')
        plt.ylabel('ATM')
        plt.title(title)

    # --------------- PM1.0 ------------------ #
    y_pm1 = np.asarray(pm1_values, dtype=float)
    x_axis_pm1 = range(0, len(y_pm1))
    plt.subplot(5, 1, 1)
    plot_data(x_axis_pm1, y_pm1, 'rd-', 'PM1.0')

    # --------------- PM2.5 ------------------ #
    y_pm25 = np.asarray(pm25_values, dtype=float)
    x_axis_pm25 = range(0, len(y_pm25))
    plt.subplot(5, 1, 2)
    plot_data(x_axis_pm25, y_pm25, 'ko-', 'PM2.5')

    # --------------- PM10.0 ------------------ #
    y_pm10 = np.asarray(pm10_values, dtype=float)
    x_axis_pm10 = range(0, len(y_pm10))
    plt.subplot(5, 1, 3)
    plot_data(x_axis_pm10, y_pm10, 'bo-', 'PM10.0')

    # --------------- Temperature ------------------ #
    y_temp = np.asarray(temperature_data, dtype=float)
    x_axis_temp = range(0, len(y_temp))
    plt.subplot(5, 1, 4)
    plot_data(x_axis_temp, y_temp, 'bo-', 'Temperature')

    # --------------- Humidity ------------------ #
    y_hum = np.asarray(humidity_data, dtype=float)
    x_axis_hum = range(0, len(y_hum))
    plt.subplot(5, 1, 5)
    plot_data(x_axis_hum, y_hum, 'bo-', 'Humidity')
    plt.show()


#  ////  3.2 Local Temperature and Humidity Measurement  ////

temperature_buffer = list(buffer_temp)
humidity_buffer = list(buffer_hum)

def add_to_temperature(value_temp):
    buffer_temp.append(value_temp)
    return list(buffer_temp)

def add_to_humidity(value_hum):
    buffer_hum.append(value_hum)
    return list(buffer_hum)

def read_dht():
    global temperature_buffer, humidity_buffer
    instance = dht11.DHT11(pin=temp_hum_sensor)
    result = instance.read()
    while not result.is_valid():
        result = instance.read()
    # print("Temperature: %-3.1f C" % result.temperature)
    # print("Humidity: %-3.1f %%" % result.humidity)
    temperature_buffer = add_to_temperature(int(result.temperature))
    humidity_buffer = add_to_humidity(int(result.humidity))

#  ////  3.3. AQI Calculation  ////

#  //// Define PM2.5 breakpoints ////
PM25_range = [
    (0.0, 12.0, 0, 50),
    (12.1, 35.4, 51, 100),
    (35.5, 55.4, 101, 150),
    (55.5, 150.4, 151, 200),
    (150.5, 250.4, 201, 300),
    (250.5, 500.4, 301, 500)
]

#  //// Define PM10 breakpoints ////
PM10_range = [
    (0, 54, 0, 50),
    (55, 154, 51, 100),
    (155, 254, 101, 150),
    (255, 354, 151, 200),
    (355, 424, 201, 300),
    (425, 604, 301, 500)
]

def compute_aqi(concentration, breakpoints):
    concentration = float(concentration)
    for c_low, c_high, i_low, i_high in breakpoints:
        if c_low <= concentration <= c_high:
            aqi = i_low + ((i_high - i_low) * (concentration - c_low)) / (c_high - c_low)
            return aqi
    return None  # Out of range

aqi_pm25_values = []
aqi_pm10_values = []
aqi_max_values = []

def calculate_aqi():
    global aqi_pm25_values, aqi_pm10_values, aqi_max_values
    aqi_pm25_values = []
    aqi_pm10_values = []
    aqi_max_values = []
    for value_pm25, value_pm10 in zip(pm25_values, pm10_values):  # FIFO arrays receiving values from cloud
        aqi_pm25 = compute_aqi(value_pm25, PM25_range)  # Calculate AQI for PM2.5
        aqi_pm25_values.append(aqi_pm25)
        aqi_pm10 = compute_aqi(value_pm10, PM10_range)  # Calculate AQI for PM10
        aqi_pm10_values.append(aqi_pm10)
        print(aqi_pm25_values)
        print(aqi_pm10_values)

        max_aqi = max(aqi_pm10, aqi_pm25)
        aqi_max_values.append(max_aqi)


def send_to_thingspeak():
    global aqi_pm25_values, aqi_pm10_values, aqi_max_values
    # ----------- Transfer AQI levels to a new cloud channel ------------ #
    # Prepare data for ThingSpeak
    thingspeak_url = "https://api.thingspeak.com/update"
    thingspeak_write_key = "G5AQQ6LNS3SDOL76"  # Your write API key for the public channel

    # Loop through the arrays and send the data to ThingSpeak
    for i in range(len(aqi_pm25_values)):  # Assuming all arrays have the same length (100)
        # Prepare the payload
        payload = {
            'api_key': thingspeak_write_key,  # ThingSpeak API key for authorization
            'field1': aqi_pm25_values[i],  # i-th entry from PM2.5 array
            'field2': aqi_pm10_values[i],  # i-th entry from PM10 array
            'field3': aqi_max_values[i]     # i-th entry from max_AQI array
        }

        # Send the request to ThingSpeak
        response = requests.post(thingspeak_url, params=payload)
        # Optionally, you can check the response status
        if response.status_code == 200:
            print(f"Data sent successfully: {payload}")
        else:
            print(f"Failed to send data: {response.status_code}, {response.text}")


# -------------------------------------------------------------------------------------------------------------------


# plot_list_pm1 = compress_list(pm1_array)
# plot_list_pm25 = compress_list(pm25_array)
# plot_list_pm10 = compress_list(pm10_array)
# plot_list_temp = compress_list(temp)
# plot_list_hum = compress_list(humidity)
# plots = [plot_list_pm1, plot_list_pm25, plot_list_pm10,plot_list_temp, plot_list_hum]

def create_plots(*data_arrays):
    return [compress_data_list(arr) for arr in data_arrays]

# Create plots using the updated function
plots = create_plots(pm1_values, pm25_values, pm10_values, temperature_data, humidity_data)


# ---------------------- Main Program ------------------- #

while True:
    duration = int(time.time() - start_time)

    if duration % 10 == 0 and duration != last_10_sec_check:
        read_dht()
        temperature_data.extend(buffer_temp)  # Update temperature_data with new values
        humidity_data.extend(buffer_hum)  # Update humidity_data with new values
        temperature_data = temperature_data[-buffer_size:]  # Ensure size consistency
        humidity_data = humidity_data[-buffer_size:]  # Ensure size consistency
        show_plots()
        last_10_sec_check = duration

        if duration % 60 == 0 and duration != last_60_sec_check:
            retrieve_sensor_data()
            calculate_aqi()  # Update this to use the correct function for AQI calculation
            send_to_thingspeak()

            # Update plots with the latest data
            plots = create_plots(pm1_values, pm25_values, pm10_values, temperature_data, humidity_data)
            last_60_sec_check = duration

    # Iterate through all input pins
    for gpio_pin in gpio_list_inputs:
        state = RPI.input(gpio_pin)
        time.sleep(0.2)  # Check button state every 0.2 seconds
        if not state:  # Button was pressed
            if gpio_pin == R_button:
                update_graph_position("right")
            elif gpio_pin == L_button:
                update_graph_position("left")

    # Draw the LED plot for the current graph position
    render_led_plot(plots[graph_position])

   # This project concept and code was co - created as a group with the following members:
    #Karanam Sai Teja
    #Muhammad Saad Majeed
    #Umar Bin Ghayas
    #Mohammad Imran

