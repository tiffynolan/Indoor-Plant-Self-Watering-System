// This #include statement was automatically added by the Particle IDE.
#include <JsonParserGeneratorRK.h>
#include <stdio.h>
#include <string.h>
#include <Wire.h>
//REFERENCES
//https://stackoverflow.com/questions/46738101/wire-onreceive-function-on-arduino
//https://arduino.stackexchange.com/questions/47947/sending-a-string-from-rpi-to-arduino-working-code

SYSTEM_THREAD(ENABLED); // To enable the system thread and have the device run your application regardless of cloud connection, add SYSTEM_THREAD(ENABLED); to your code

const int soilSensor = A5;	/* Soil moisture sensor O/P pin */

//Soil Moisture Variables
int drySoil = 2800; //Driest soil is 3030 roughly - Did have this at 2930 but felt too high. Changed on 7th day
int wetSoil = 1733; //Wet soil is 1733 roughly
int idealSoil = 2150; //What I think might be a good moisture for the plant to be at
int soilMoisture = 2150; //Current soil moisture variable
int plantWatered = 0; //between 0 and 2.. variable sent by RPi if plant watered
int needWatering = 0; //Variable sent to RPi to tell it when to water (when soil moisture too dry)
int data[5]; //Data array to hold variables received from RPi
bool dataPublish = false; //If data variables received from RPi, publish them
bool waterLevelPublish = false; //Alert user of water level bool

void setup()
{
    Wire.begin(0x10); // join i2c bus with address 10
    Wire.onRequest(sendEvent); // register wire.request interrupt event
    Wire.onReceive(receiveEvent); // Define callbacks for i2c communication
    Serial.begin(9600);
}

void loop()
{
    //Get the current soil moisture
    soilMoisture = analogRead(soilSensor);
    //Print the soil moisture reading to the console
    Serial.print("Moisture = "); 
    Serial.println(soilMoisture);
    
    // Set Need watering variable for sending to RPi
    if(soilMoisture >= drySoil)
    {
        needWatering = 1; // 1 means plant needs watering
    }
    else
    {
        needWatering = 0; // 0 means doesnt need watering
    }
    
    // Publish data and store it to google sheet
    if (dataPublish)
    {
        CreateString(data[1], data[2], data[3], soilMoisture);
        delay(1000); //Wait 1 sec
        
        // Notify user if plant was watered or needs watering and no water
        Watered(); 
        delay(1000); //Wait 1 sec
        
        //Notify user as water is getting lower (starting from 50%)
        CalcWaterLevel(); 
        delay(1000); //Wait 1 sec
        
        dataPublish = false;
    }
}

// Method to send data to the RPi
void sendEvent() 
{
    Serial.print("Sending to PI: ");
    Serial.println(needWatering);// print the data being sent
    Wire.write(needWatering);
}

// Method to receive data from the RPi
void receiveEvent(int howMany)
{
    for (int i = 0; i < howMany; i++) 
    {
        data[i] = Wire.read();
    }

    dataPublish = true; //If we received data from RPi, then want to publish to Google Sheet
}

//Method to Combine to objects into a key value pair
void CreateString(int temp, int hum, int water, int soil)
{
    JsonWriterStatic<256> jw;
    {
        JsonWriterAutoObject obj(&jw);
        jw.insertKeyValue("Temp", temp); //Note: “temp” is the name allocated to field1 in the webhook
        jw.insertKeyValue("Hum", hum); //Note: “hum” is the name allocated to field2 in the webhook
        jw.insertKeyValue("Water", water); //Note: “hum” is the name allocated to field2 in the webhook
        jw.insertKeyValue("Soil", soil); //Note: “temp” is the name allocated to field1 in the webhook
    }
    
    Particle.publish("PlantEnvData", jw.getBuffer(), PRIVATE); //Note: “temp” is the Event Name of the webhook that we chose when following along with the tutorial in stage 1.
}

// Method to Publish if the plant was watered or needs watering but not enough water
void Watered()
{
    // Send user notification when plant was/needs watering
    if(data[4] == 1)
    {
        Particle.publish("Watered", "Plant was watered", PRIVATE);
    }
    else if(data[4] == 2)
    {
        Particle.publish("Watered", "PLANT NEEDS WATERING BUT WATER TOO LOW", PRIVATE);
    }
}

//Method to determine if water level low enough to notify user
void CalcWaterLevel()
{
    // Notify user of water level
    if(data[3] == 50)
    {
        Particle.publish("WaterLvl", "Water Level at 50%", PRIVATE);
    }
    else if(data[3] == 25)
    {
        Particle.publish("WaterLvl", "Water Level at 25%", PRIVATE);
    }
    else if(data[3] >= 0 && data[3] <= 5) //Give water pump 5% buffer
    {
        Particle.publish("WaterLvl", "WATER IS EMPTY, PLEASE REFILL", PRIVATE); // WATER LVL empty
    }
}
