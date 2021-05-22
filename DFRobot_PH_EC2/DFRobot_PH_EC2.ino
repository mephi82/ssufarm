
#include "DFRobot_PH.h"
#include "DFRobot_EC.h"
#include <EEPROM.h>
#include <OneWire.h>
#include <DallasTemperature.h>

#define PH_PIN A2
#define EC_PIN1 A1
#define EC_PIN2 A2
#define ONE_WIRE_BUS 4
#define KVALUEADDR 0x0A
// Setup a oneWire instance to communicate with any OneWire devices (not just Maxim/Dallas temperature ICs)
OneWire oneWire(ONE_WIRE_BUS);
// Pass our oneWire reference to Dallas Temperature. 
DallasTemperature sensors(&oneWire);

float  voltagePH,voltageEC1,voltageEC2,phValue,ecValue1,ecValue2,temperature = 27;
volatile int flow_frequency1, flow_frequency2; // Measures flow sensor pulses
unsigned int l_hour1, l_hour2; // Calculated litres/hour
unsigned char flowsensor1 = 2; // Sensor Input
unsigned char flowsensor2 = 3; // Sensor Input
//unsigned long currentTime;
//unsigned long cloopTime;
DFRobot_PH ph;
DFRobot_EC ec;

void flow1() // Interrupt function
{
   flow_frequency1++;
}
void flow2() // Interrupt function
{
   flow_frequency2++;
}

void setup()
{
    Serial.begin(115200);  
    ph.begin();
    ec.begin();
    sensors.begin();
//    for(byte i = 0;i< 8; i++   ){
//      EEPROM.write(KVALUEADDR+i, 0xFF);
//    }
//    Serial.println(EEPROM.read(KVALUEADDR));
    pinMode(flowsensor1, INPUT);
    digitalWrite(flowsensor1, HIGH); // Optional Internal Pull-Up
    attachInterrupt(digitalPinToInterrupt(flowsensor1), flow1, RISING);
    
    pinMode(flowsensor2, INPUT);
    digitalWrite(flowsensor2, HIGH); // Optional Internal Pull-Up
    attachInterrupt(digitalPinToInterrupt(flowsensor2), flow2, RISING);
//   attachInterrupt(0, flow, RISING); // Setup Interrupt
    sei(); // Enable interrupts
//    currentTime = millis();
//    cloopTime = currentTime;
}

void loop()
{
    char cmd[10];
    static unsigned long timepoint = millis();
//    Serial.println(flow_frequency1);
//    Serial.println(flow_frequency2);
    if(millis()-timepoint>1000U){                            //time interval: 1s
        l_hour1 = (flow_frequency1 * 60 / 7.5); // (Pulse frequency x 60 min) / 7.5Q = flowrate in L/hour
        flow_frequency1 = 0; // Reset Counter
        l_hour2 = (flow_frequency2 * 60 / 7.5); // (Pulse frequency x 60 min) / 7.5Q = flowrate in L/hour
        flow_frequency2 = 0; // Reset Counter

        timepoint = millis();
        temperature = readTemperature(temperature);                   // read your temperature sensor to execute temperature compensation
        voltagePH = analogRead(PH_PIN)/1024.0*5000;          // read the ph voltage
        phValue    = ph.readPH(voltagePH,temperature);       // convert voltage to pH with temperature compensation
        voltageEC1 = analogRead(EC_PIN1)/1024.0*5000;
        ecValue1    = 0.3+ec.readEC(voltageEC1,temperature);       // convert voltage to EC with temperature compensation
        voltageEC2 = analogRead(EC_PIN2)/1024.0*5000;
        ecValue2    = 0.3+ec.readEC(voltageEC2,temperature);       // convert voltage to EC with temperature compensation

        Serial.print("{\"Temp\":");
        Serial.print(temperature,1);
        Serial.print(", \"EC1\":");
        Serial.print(ecValue1,2);
        Serial.print(", \"EC2\":");
        Serial.print(ecValue2,2);
//        Serial.println("ms/cm");
//        Serial.print("pH:");
//        Serial.print(phValue,2);
        
//        Serial.print(", \"Voltage\":'");
//        Serial.print(voltageEC1,1);
//        Serial.print("/");
//        Serial.print(voltageEC2,1);
//        Serial.print("'");
        Serial.print(", \"Flow1\":");
        Serial.print(l_hour1, DEC);
        Serial.print(", \"Flow2\":");
        Serial.print(l_hour2, DEC);
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
//
//int i = 0;
//bool readSerial(char result[]){
//    while(Serial.available() > 0){
//        char inChar = Serial.read();
//        if(inChar == '\n'){
//             result[i] = '\0';
//             Serial.flush();
//             i=0;
//             return true;
//        }
//        if(inChar != '\r'){
//             result[i] = inChar;
//             i++;
//        }
//        delay(1);
//    }
//    return false;
//}

float readTemperature(float oldtemp)
{
  sensors.requestTemperatures(); // Send the command to get temperatures
  //add your code here to get the temperature from your temperature sensor
  float tempC = sensors.getTempCByIndex(0);
  if(tempC != DEVICE_DISCONNECTED_C) 
  {
    return tempC;
  }
  else {
//    Serial.print("temp not read");
    return oldtemp; 
  }
}
