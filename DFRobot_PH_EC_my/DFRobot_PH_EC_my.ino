
#include "DFRobot_PH.h"
#include "DFRobot_EC.h"
#include <EEPROM.h>
#include <OneWire.h>
#include <DallasTemperature.h>

#define PH_PIN A1
#define EC_PIN1 A2
#define EC_PIN2 A3
// Data wire is plugged into port 2 on the Arduino
#define ONE_WIRE_BUS 2
// Setup a oneWire instance to communicate with any OneWire devices (not just Maxim/Dallas temperature ICs)
OneWire oneWire(ONE_WIRE_BUS);
// Pass our oneWire reference to Dallas Temperature. 
DallasTemperature sensors(&oneWire);


float  voltagePH, voltageEC_A, voltageEC_B,phValue,ecValue_A, ecValue_B,temperature =29;
DFRobot_PH ph;
DFRobot_EC ec;

void setup()
{
    Serial.begin(115200);  
    ph.begin();
    ec.begin();
    sensors.begin();
}

void loop()
{
    char cmd[10];
    static unsigned long timepoint = millis();
    if(millis()-timepoint>1000U){                            //time interval: 1s
        timepoint = millis();
//        temperature = readTemperature();                   // read your temperature sensor to execute temperature compensation
        voltagePH = analogRead(PH_PIN)/1024.0*5000;          // read the ph voltage
        phValue    = ph.readPH(voltagePH,temperature);       // convert voltage to pH with temperature compensation
        Serial.print("{\"pH\":");
        Serial.print(phValue,2);
        voltageEC_A = analogRead(EC_PIN1)/1024.0*5000;
        ecValue_A    = ec.readEC(voltageEC_A,temperature);       // convert voltage to EC with temperature compensation
        voltageEC_B = analogRead(EC_PIN2)/1024.0*5000;
        ecValue_B    = ec.readEC(voltageEC_B,temperature);       // convert voltage to EC with temperature compensation
        Serial.print(voltageEC_A);
        Serial.print(", \"EC_A\":");
        Serial.print(ecValue_A,3);
        Serial.print(", \"EC_B\":");
        Serial.print(ecValue_B,3);
        Serial.print(", \"Temp\":");
        Serial.print(temperature,1);
        Serial.println("}");
    }
//    if(readSerial(cmd)){
//        strupr(cmd);
//        if(strstr(cmd,"PH")){
//            ph.calibration(voltagePH,temperature,cmd);       //PH calibration process by Serail CMD
//        }
//        if(strstr(cmd,"EC")){
//            ec.calibration(voltageEC,temperature,cmd);       //EC calibration process by Serail CMD
//        }
//    }
}

int i = 0;
bool readSerial(char result[]){
    while(Serial.available() > 0){
        char inChar = Serial.read();
        if(inChar == '\n'){
             result[i] = '\0';
             Serial.flush();
             i=0;
             return true;
        }
        if(inChar != '\r'){
             result[i] = inChar;
             i++;
        }
        delay(1);
    }
    return false;
}

float readTemperature()
{
  sensors.requestTemperatures(); // Send the command to get temperatures
  //add your code here to get the temperature from your temperature sensor
  float tempC = sensors.getTempCByIndex(0);
  return tempC;
}
