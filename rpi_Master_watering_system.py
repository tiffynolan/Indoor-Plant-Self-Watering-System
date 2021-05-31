from smbus2 import SMBus #https://pypi.org/project/smbus2/
from time import sleep # Import the sleep function from the time module
#https://docs.particle.io/tutorials/learn-more/about-i2c/
import codecs # Library used for decoding hex
#!/usr/bin/python
import sys
import RPi.GPIO as GPIO #Import Raspberry Pi GPIO library
import Adafruit_DHT

#VARIABLES
dhtDevice = Adafruit_DHT.DHT11 #Temp/Hum Sensor
hum = 0 # Holds the humidity data from the sensor
temp = 0 # Holds the temperature data from the sensor
bus = SMBus(1) #setup the bus
address = 0x10 #listen on adress 0x10
tempHumSensor = 21 #temperature and humidty sensor Output port
relay = 13 #trigger port
WATERLVLMAX = 3367 # Max amount of water available for plant watering
curWaterLvl = 3367 # The current water level
WATERREMOVEDPERWATERING = 28 # 28ml is removed from water tank each watering of 5 seconds + 2secs for pump delay
PUMPDELAY = 2 #pump delay
WATERTIMING = 0.5 #time for water pump to be on after pump delay

GPIO.setwarnings(False) # Ignore warning for now
GPIO.setmode(GPIO.BCM) # Declare pin number standard
GPIO.setup(relay, GPIO.OUT) #Set relay trigger pin mode
GPIO.output(relay, GPIO.LOW) #Start relay off

#Method waters the plant if required for a set time
def WaterPlant(needWatering):
    global curWaterLvl
    plantwatered = -1 # Value used to advise Particle Argon if Plant watered
    
    #Plant needs watering
    if needWatering == 1:        
        if curWaterLvl / WATERLVLMAX * 100 >= 5: #Wont water when water reached 5 percent as safe guard 
            GPIO.output(relay, GPIO.HIGH) #Turn Water pump on
            sleep(PUMPDELAY + WATERTIMING) #set relay on for 2.5 secs
            GPIO.output(relay, GPIO.LOW) #Turn Water pump off
            print("WaterLVL Before: " + str(curWaterLvl))
            curWaterLvl = curWaterLvl - WATERREMOVEDPERWATERING #Update how much water left in tank
            print("WaterLVL After: " + str(curWaterLvl))
            plantwatered = 1
            print("Soil Dry, Plant Watered.")
        else:
            #Not enough water
            plantwatered = 2
            print("Soil Dry, but Not Enough Water to Water.")
    # Plant Doesnt need watering
    else:
        plantwatered = 0
        print("Soil Moisture Fine, Dont Need to Water.")
        
    return plantwatered   
    
#Recieve a byte of data from address 10
def ReceiveByte():
    # Open i2c bus 1 and read one byte from address 10, offset 0
    with SMBus(1) as bus:
        needWatering = bus.read_byte_data(0x10, 0)
        print("Data received: " + str(needWatering))
    return needWatering

#Checks humidity and temperature and ensures a valid reading is assigned to temp, hum variables
def ReadTempHum():
    global hum
    global temp
    isValue = False
                                
    #Get Temperature and Humidity
    while(isValue == False):
        humidity, temperature = Adafruit_DHT.read_retry(dhtDevice, tempHumSensor)
        
        #Make sure valide reading
        if humidity is not None and temperature is not None:                
            #cant send negative number, so revert to 0.. Room temp shouldnt get below 0 anyway, so that would mean an error in reading
            print('Temp: {0:0.1f}*  Humidity: {1:0.1f}%'.format(temperature, humidity))
            if(temperature < 0):
                temperature = 0
            hum = humidity #assign the value to our global var
            temp = temperature #assign the value to our global var
            isValue = True
        else:
            print("Failed to get temp and hum reading, trying again")

#Send a block of data to address 10
def SendDataBlock(temp, hum, water, plantwatered):
    data = [temp, hum, water, plantwatered]
    with SMBus(1) as bus:
        # Write a block of bytes to address 10 from offset 0
        bus.write_i2c_block_data(0x10, 0, data)
        print("Data block sent: " + str(data))
                         
#Keep checking for data until all data received
sleep(15) #wait 15secs for Argon to boot
try:
    while True:
        #Get Command from Argon about if soil moisture too dry and if needs watering
        try:
            ReadTempHum() #Get temp and humidity, do first to make sure get actual data and not none
            
            #Check if plant needs watering from Argon command (0 = no, 1 = yes)
            needWatering = ReceiveByte()
            plantwatered = WaterPlant(needWatering)
            
            sleep(1) #Wait 1 sec
            
            waterLVLPerc = (curWaterLvl / WATERLVLMAX) * 100 #Convert current water level to percentage to send to argon            
            print("WaterLVL in Main: " + str(waterLVLPerc))
                        
            SendDataBlock(int(temp), int(hum), int(waterLVLPerc), plantwatered)
            
            sleep(1800) #Wait 30 mins (1800 secs) if all steps successful, otherwise check again
        except:
            print("Error occured in getting data, trying again")                           
except KeyboardInterrupt:
    pass
    
bus.close() #Close bus as a safe guard
GPIO.cleanup() # when program exits, tidy up